#!/usr/bin/env python3
"""Benchmark runner for noxaudit.

Runs noxaudit across a matrix of provider × model × repo × focus combinations
and writes structured JSON results to benchmark/results/.

Usage:
    # Run full matrix from corpus config:
    python scripts/benchmark.py matrix benchmark/corpus.yml

    # Run a single combination:
    python scripts/benchmark.py single \\
        --repo noxaudit --repo-path /path/to/noxaudit \\
        --provider gemini --model gemini-2.0-flash \\
        --focus security --run 1

    # Resume a partial run (automatically skips completed combos):
    python scripts/benchmark.py matrix benchmark/corpus.yml
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Result schema helpers
# ---------------------------------------------------------------------------


def result_path(
    output_dir: Path, repo: str, provider: str, model: str, focus: str, run: int
) -> Path:
    """Return the output path for a single benchmark result file."""
    model_safe = model.replace("/", "-").replace(":", "-")
    filename = f"{provider}-{model_safe}-{focus}-run{run}.json"
    return output_dir / repo / filename


def build_result_record(
    *,
    repo: str,
    repo_commit: str,
    provider: str,
    model: str,
    focus: str,
    run: int,
    started_at: datetime,
    completed_at: datetime,
    wall_clock_seconds: float,
    error: str | None,
    tokens: dict,
    cost_usd: float,
    findings: list[dict],
) -> dict:
    """Return a structured benchmark result dict (the JSON schema)."""
    return {
        "meta": {
            "repo": repo,
            "repo_commit": repo_commit,
            "provider": provider,
            "model": model,
            "focus": focus,
            "run": run,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "wall_clock_seconds": round(wall_clock_seconds, 2),
            "error": error,
        },
        "tokens": tokens,
        "cost_usd": cost_usd,
        "findings_count": len(findings),
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Matrix expansion
# ---------------------------------------------------------------------------


def build_combinations(matrix: dict) -> list[dict]:
    """Expand a matrix config dict into a flat list of run parameter dicts."""
    output_dir = Path(matrix.get("output_dir", "benchmark/results"))
    rate_limit = matrix.get("rate_limit", {})
    sleep_s = float(rate_limit.get("sleep_between_runs", 3))
    backoff_s = float(rate_limit.get("backoff_on_error", 30))

    combos = []
    for repo_cfg in matrix.get("repos", []):
        for provider_cfg in matrix.get("providers", []):
            for model in provider_cfg.get("models", []):
                for focus in matrix.get("focus", ["all"]):
                    for run in range(1, int(matrix.get("runs", 1)) + 1):
                        combos.append(
                            {
                                "repo_name": repo_cfg["name"],
                                "repo_path": repo_cfg["path"],
                                "repo_commit": repo_cfg.get("commit", ""),
                                "provider": provider_cfg["name"],
                                "model": model,
                                "focus": focus,
                                "run": run,
                                "output_dir": output_dir,
                                "exclude_patterns": repo_cfg.get("exclude", []),
                                "sleep_s": sleep_s,
                                "backoff_s": backoff_s,
                            }
                        )
    return combos


# ---------------------------------------------------------------------------
# Single-combination runner
# ---------------------------------------------------------------------------


def run_one(
    repo_name: str,
    repo_path: str,
    repo_commit: str,
    provider: str,
    model: str,
    focus: str,
    run: int,
    output_dir: Path,
    exclude_patterns: list[str] | None = None,
) -> bool:
    """Run one benchmark combination and write a result JSON file.

    Returns True if the run executed, False if it was skipped (already done).
    Raises on unrecoverable errors so callers can apply backoff.
    """
    from noxaudit.config import NoxauditConfig, RepoConfig
    from noxaudit.cost_ledger import CostLedger
    from noxaudit.runner import run_audit

    out_path = result_path(output_dir, repo_name, provider, model, focus, run)
    if out_path.exists():
        print(f"  [SKIP] {repo_name} | {provider}/{model} | {focus} | run{run} — result exists")
        return False

    print(f"  [RUN ] {repo_name} | {provider}/{model} | focus={focus} | run={run}")

    config = NoxauditConfig(
        repos=[
            RepoConfig(
                name=repo_name,
                path=repo_path,
                provider_rotation=[provider],
                exclude_patterns=exclude_patterns or [],
            )
        ],
        model=model,
    )

    # Snapshot ledger length so we can isolate the new entry after the run.
    before_entries = CostLedger.read_entries()
    before_count = len(before_entries)

    started_at = datetime.now()
    t0 = time.monotonic()
    error: str | None = None
    results = []

    try:
        results = run_audit(
            config,
            repo_name=repo_name,
            focus_name=focus,
            provider_name=provider,
        )
    except Exception as exc:
        error = str(exc)
        print(f"         [ERROR] {error}")

    wall_clock = time.monotonic() - t0
    completed_at = datetime.now()

    # Read the new ledger entry appended by run_audit (if any).
    all_entries = CostLedger.read_entries()
    new_entries = all_entries[before_count:]
    last_entry = new_entries[-1] if new_entries else {}

    audit_result = results[0] if results else None
    findings = [f.to_dict() for f in audit_result.findings] if audit_result else []

    record = build_result_record(
        repo=repo_name,
        repo_commit=repo_commit,
        provider=provider,
        model=model,
        focus=focus,
        run=run,
        started_at=started_at,
        completed_at=completed_at,
        wall_clock_seconds=wall_clock,
        error=error,
        tokens={
            "input": last_entry.get("input_tokens", 0),
            "output": last_entry.get("output_tokens", 0),
            "cache_read": last_entry.get("cache_read_tokens", 0),
            "cache_write": last_entry.get("cache_write_tokens", 0),
        },
        cost_usd=last_entry.get("cost_estimate_usd", 0.0),
        findings=findings,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2))

    status = "ERROR" if error else "OK"
    cost = record["cost_usd"]
    print(
        f"         [{status}] {len(findings)} findings, {wall_clock:.1f}s, ${cost:.4f} → {out_path}"
    )

    if error:
        raise RuntimeError(error)

    return True


# ---------------------------------------------------------------------------
# Matrix runner
# ---------------------------------------------------------------------------


def run_matrix(config_path: Path) -> None:
    """Run the full benchmark matrix defined in a YAML config file.

    Skips combinations whose output file already exists, enabling resume.
    """
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # Support both top-level matrix key and flat config
    matrix = cfg.get("matrix", cfg)
    combos = build_combinations(matrix)
    total = len(combos)
    output_dir = matrix.get("output_dir", "benchmark/results")

    print(f"Benchmark matrix: {total} combinations")
    print(f"Output dir:       {output_dir}")
    print()

    completed = skipped = errors = 0

    for i, combo in enumerate(combos, 1):
        sleep_s = combo.pop("sleep_s")
        backoff_s = combo.pop("backoff_s")
        print(f"[{i}/{total}]", end=" ", flush=True)
        try:
            ran = run_one(**combo)
            if ran:
                completed += 1
                if sleep_s > 0:
                    time.sleep(sleep_s)
            else:
                skipped += 1
        except Exception as exc:
            errors += 1
            print(f"         Unhandled error: {exc}")
            if backoff_s > 0:
                print(f"         Backing off {backoff_s}s...")
                time.sleep(backoff_s)

    print()
    print(f"Done: {completed} completed, {skipped} skipped, {errors} errors")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Noxaudit benchmark runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # --- matrix subcommand ---
    matrix_cmd = sub.add_parser(
        "matrix",
        help="Run full benchmark matrix from a YAML config",
    )
    matrix_cmd.add_argument(
        "config",
        help="Path to matrix YAML config (e.g. benchmark/corpus.yml)",
    )

    # --- single subcommand ---
    single_cmd = sub.add_parser(
        "single",
        help="Run a single provider × repo × focus combination",
    )
    single_cmd.add_argument("--repo", required=True, help="Repo name (label)")
    single_cmd.add_argument(
        "--repo-path", required=True, dest="repo_path", help="Local path to repo"
    )
    single_cmd.add_argument(
        "--repo-commit", default="", dest="repo_commit", help="Pinned commit SHA"
    )
    single_cmd.add_argument(
        "--provider", required=True, help="Provider name (anthropic, gemini, openai)"
    )
    single_cmd.add_argument("--model", required=True, help="Model name")
    single_cmd.add_argument("--focus", default="security", help="Focus area(s): name or 'all'")
    single_cmd.add_argument("--run", type=int, default=1, help="Run number (default: 1)")
    single_cmd.add_argument(
        "--output-dir",
        default="benchmark/results",
        dest="output_dir",
        help="Output directory (default: benchmark/results)",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "matrix":
        run_matrix(Path(args.config))
    elif args.command == "single":
        try:
            run_one(
                repo_name=args.repo,
                repo_path=args.repo_path,
                repo_commit=args.repo_commit,
                provider=args.provider,
                model=args.model,
                focus=args.focus,
                run=args.run,
                output_dir=Path(args.output_dir),
            )
        except RuntimeError:
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
