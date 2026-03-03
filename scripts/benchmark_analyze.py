#!/usr/bin/env python3
"""Benchmark result analysis script for noxaudit.

Reads structured JSON results from benchmark/results/ and produces
a scorecard markdown report.

Usage:
    # Generate scorecard from results
    python scripts/benchmark_analyze.py scorecard benchmark/results/ -o benchmark/scorecard.md

    # Quick summary to stdout
    python scripts/benchmark_analyze.py summary benchmark/results/
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean

try:
    from noxaudit.pricing import MODEL_PRICING, estimate_cost, resolve_model_key

    _HAS_PRICING = True
except ImportError:
    _HAS_PRICING = False

CANARY_REPO = "python-dotenv"
CANARY_MAX_EXPECTED = 2


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_results(results_dir: Path) -> list[dict]:
    """Load all JSON result files from the results directory."""
    results = []
    for path in sorted(results_dir.glob("**/*.json")):
        try:
            data = json.loads(path.read_text())
            results.append(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: could not read {path}: {e}", file=sys.stderr)
    return results


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------


@dataclass
class ModelMetrics:
    model: str
    provider: str
    run_count: int = 0
    findings_per_run: float = 0.0
    high_sev_rate: float = 0.0
    cost_sync: float = 0.0
    cost_batch: float = 0.0
    cost_per_finding: float = 0.0
    wall_clock_seconds: float = 0.0
    consistency: float | None = None  # Jaccard; None if only 1 run per combo
    unique_findings: int = 0
    canary_findings: int = -1  # -1 means not tested
    canary_high_sev: int = -1
    errors: int = 0


def _jaccard(set_a: set, set_b: set) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    union = len(set_a | set_b)
    return len(set_a & set_b) / union if union > 0 else 1.0


def _compute_sync_cost(result: dict) -> float:
    """Compute sync (non-batch) cost from tokens, falling back to recorded cost_usd."""
    meta = result.get("meta", {})
    tokens = result.get("tokens", {})
    if not _HAS_PRICING or not tokens:
        return result.get("cost_usd", 0.0)
    try:
        model_key = resolve_model_key(meta.get("provider", ""), meta.get("model", ""))
        pricing = MODEL_PRICING[model_key]
        return estimate_cost(
            tokens.get("input", 0),
            tokens.get("output", 0),
            pricing,
            use_batch=False,
            cache_read_tokens=tokens.get("cache_read", 0),
            cache_write_tokens=tokens.get("cache_write", 0),
        )
    except (KeyError, TypeError):
        return result.get("cost_usd", 0.0)


def _compute_batch_cost(result: dict) -> float:
    """Compute batch cost from tokens (50% discount), falling back to cost_usd * 0.5."""
    meta = result.get("meta", {})
    tokens = result.get("tokens", {})
    if not _HAS_PRICING or not tokens:
        return result.get("cost_usd", 0.0) * 0.5
    try:
        model_key = resolve_model_key(meta.get("provider", ""), meta.get("model", ""))
        pricing = MODEL_PRICING[model_key]
        return estimate_cost(
            tokens.get("input", 0),
            tokens.get("output", 0),
            pricing,
            use_batch=True,
            cache_read_tokens=tokens.get("cache_read", 0),
            cache_write_tokens=tokens.get("cache_write", 0),
        )
    except (KeyError, TypeError):
        return result.get("cost_usd", 0.0) * 0.5


def compute_metrics(results: list[dict]) -> dict[str, ModelMetrics]:
    """Compute per-model aggregated metrics from all benchmark results."""
    if not results:
        return {}

    # Group results by model
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        model = r.get("meta", {}).get("model", "unknown")
        by_model[model].append(r)

    # Build cross-model unique-findings index.
    # combo_findings: {(repo, focus): {model: set_of_ids}}
    combo_findings: dict[tuple, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for r in results:
        meta = r.get("meta", {})
        if meta.get("error"):
            continue
        repo = meta.get("repo", "")
        focus = meta.get("focus", "")
        model = meta.get("model", "unknown")
        ids = {f.get("id", "") for f in r.get("findings", [])}
        combo_findings[(repo, focus)][model].update(ids)

    # Per-model unique finding IDs (not found by any other model in same combo)
    model_unique: dict[str, set] = defaultdict(set)
    for model_ids in combo_findings.values():
        all_models = list(model_ids.keys())
        for model in all_models:
            other_ids: set = set()
            for other, ids in model_ids.items():
                if other != model:
                    other_ids.update(ids)
            model_unique[model].update(model_ids[model] - other_ids)

    metrics: dict[str, ModelMetrics] = {}

    for model, model_results in by_model.items():
        provider = model_results[0].get("meta", {}).get("provider", "unknown")
        m = ModelMetrics(model=model, provider=provider)
        m.run_count = len(model_results)
        m.errors = sum(1 for r in model_results if r.get("meta", {}).get("error"))

        good = [r for r in model_results if not r.get("meta", {}).get("error")]
        if not good:
            metrics[model] = m
            continue

        # Findings per run
        counts = [r.get("findings_count", 0) for r in good]
        m.findings_per_run = mean(counts)

        # High severity rate
        all_findings = [f for r in good for f in r.get("findings", [])]
        if all_findings:
            high = sum(
                1 for f in all_findings if f.get("severity", "").lower() in ("high", "critical")
            )
            m.high_sev_rate = high / len(all_findings)

        # Cost (sync and batch, mean per run)
        sync_costs = [_compute_sync_cost(r) for r in good]
        batch_costs = [_compute_batch_cost(r) for r in good]
        m.cost_sync = mean(sync_costs)
        m.cost_batch = mean(batch_costs)

        # Cost per finding
        total_findings = sum(counts)
        total_sync = sum(sync_costs)
        m.cost_per_finding = total_sync / total_findings if total_findings > 0 else 0.0

        # Wall clock time
        wall_clocks = [r.get("meta", {}).get("wall_clock_seconds", 0.0) for r in good]
        m.wall_clock_seconds = mean(wall_clocks)

        # Consistency: mean Jaccard across repeat runs of the same (repo, focus) combo
        combo_runs: dict[tuple, list[set]] = defaultdict(list)
        for r in good:
            meta = r.get("meta", {})
            key = (meta.get("repo", ""), meta.get("focus", ""))
            ids = {f.get("id", "") for f in r.get("findings", [])}
            combo_runs[key].append(ids)

        jaccards = []
        for run_sets in combo_runs.values():
            for i in range(len(run_sets)):
                for j in range(i + 1, len(run_sets)):
                    jaccards.append(_jaccard(run_sets[i], run_sets[j]))
        if jaccards:
            m.consistency = mean(jaccards)

        # Unique findings count
        m.unique_findings = len(model_unique.get(model, set()))

        # Canary repo metrics
        canary = [r for r in good if r.get("meta", {}).get("repo") == CANARY_REPO]
        if canary:
            canary_findings = [f for r in canary for f in r.get("findings", [])]
            m.canary_findings = len(canary_findings)
            m.canary_high_sev = sum(
                1 for f in canary_findings if f.get("severity", "").lower() in ("high", "critical")
            )

        metrics[model] = m

    return metrics


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def build_recommendations(metrics: dict[str, ModelMetrics]) -> str:
    """Generate recommendation text based on aggregated metrics."""
    if not metrics:
        return "_Insufficient data for recommendations. Run the full benchmark matrix._\n"

    # Best for daily batch: lowest batch cost among models with results
    with_cost = [
        (m, m.cost_batch) for m in metrics.values() if m.run_count > 0 and m.cost_batch > 0
    ]
    best_daily = min(with_cost, key=lambda x: x[1])[0] if with_cost else None

    # Best for monthly deep dives: highest findings/run
    by_depth = sorted(
        (m for m in metrics.values() if m.run_count > 0),
        key=lambda m: m.findings_per_run,
        reverse=True,
    )
    best_deep = by_depth[0] if by_depth else None

    lines = []
    if best_daily:
        lines.append(
            f"- **Daily batch audits**: use `{best_daily.model}` ({best_daily.provider})"
            f" — ${best_daily.cost_batch:.4f}/run batch cost"
        )
    if best_deep and (not best_daily or best_deep.model != best_daily.model):
        lines.append(
            f"- **Monthly deep dives**: use `{best_deep.model}` ({best_deep.provider})"
            f" — {best_deep.findings_per_run:.1f} findings/run"
        )
    elif best_deep and best_daily and best_deep.model == best_daily.model:
        lines.append(f"- **Monthly deep dives**: `{best_deep.model}` also leads on finding depth")

    if not lines:
        return "_Insufficient data for recommendations. Run the full benchmark matrix._\n"
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _fmt_cost(cost: float) -> str:
    if cost <= 0:
        return "n/a"
    if cost < 0.0001:
        return f"${cost:.6f}"
    return f"${cost:.4f}"


def _fmt_pct(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def _fmt_time(seconds: float) -> str:
    if seconds <= 0:
        return "n/a"
    return f"{seconds:.1f}s"


def _fmt_consistency(c: float | None) -> str:
    return "n/a" if c is None else f"{c:.2f}"


def _canary_status(findings: int, high_sev: int) -> str:
    if findings < 0:
        return "—"
    if high_sev > 0:
        return "⚠ HIGH SEV"
    if findings > CANARY_MAX_EXPECTED:
        return "⚠ WARN"
    return "OK"


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_scorecard(metrics: dict[str, ModelMetrics], generated_at: str = "") -> str:
    """Generate the markdown scorecard from aggregated metrics."""
    if not generated_at:
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Noxaudit Benchmark Scorecard",
        "",
        f"Generated: {generated_at}",
        "",
        f"Canary repo: `{CANARY_REPO}` (expected ≤ {CANARY_MAX_EXPECTED} low-severity findings"
        " — higher counts or high severity may indicate hallucinations)",
        "",
    ]

    if not metrics:
        lines.append("_No benchmark results found._")
        return "\n".join(lines)

    sorted_models = sorted(metrics.values(), key=lambda m: (m.provider, m.model))

    # --- Comparison matrix ---
    lines += [
        "## Comparison Matrix",
        "",
        "| Model | Provider | Runs | Findings/run | High sev% | Cost/run (sync) | Cost/run (batch) | Cost/finding | Wall clock | Consistency | Unique finds |",
        "|-------|----------|------|-------------|-----------|-----------------|------------------|-------------|------------|-------------|--------------|",
    ]
    for m in sorted_models:
        row = " | ".join(
            [
                m.model,
                m.provider,
                str(m.run_count),
                f"{m.findings_per_run:.1f}",
                _fmt_pct(m.high_sev_rate),
                _fmt_cost(m.cost_sync),
                _fmt_cost(m.cost_batch),
                _fmt_cost(m.cost_per_finding),
                _fmt_time(m.wall_clock_seconds),
                _fmt_consistency(m.consistency),
                str(m.unique_findings),
            ]
        )
        lines.append(f"| {row} |")

    lines += ["", ""]

    # --- Hallucination canary ---
    lines += [
        f"## Hallucination Canary (`{CANARY_REPO}`)",
        "",
        "| Model | Provider | Findings | High sev | Status |",
        "|-------|----------|----------|----------|--------|",
    ]
    for m in sorted_models:
        count = "—" if m.canary_findings < 0 else str(m.canary_findings)
        high = "—" if m.canary_high_sev < 0 else str(m.canary_high_sev)
        status = _canary_status(m.canary_findings, m.canary_high_sev)
        lines.append(f"| {m.model} | {m.provider} | {count} | {high} | {status} |")

    lines += ["", ""]

    # --- Recommendations ---
    lines += [
        "## Recommendations",
        "",
        build_recommendations(metrics),
    ]

    return "\n".join(lines)


def print_summary(metrics: dict[str, ModelMetrics]) -> None:
    """Print a quick summary table to stdout."""
    if not metrics:
        print("No benchmark results found.")
        return

    sorted_models = sorted(metrics.values(), key=lambda m: (m.provider, m.model))

    print(f"\nBenchmark Summary — {len(sorted_models)} models\n")
    header = (
        f"{'Model':<30} {'Provider':<12} {'Runs':>4} {'Findings/run':>12}"
        f" {'Cost/run(batch)':>15} {'Consistency':>12}"
    )
    print(header)
    print("-" * len(header))

    for m in sorted_models:
        cons = f"{m.consistency:.2f}" if m.consistency is not None else "n/a"
        print(
            f"{m.model:<30} {m.provider:<12} {m.run_count:>4}"
            f" {m.findings_per_run:>12.1f} {_fmt_cost(m.cost_batch):>15} {cons:>12}"
        )

    print()
    print(build_recommendations(metrics))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Noxaudit benchmark result analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    scorecard_cmd = sub.add_parser(
        "scorecard",
        help="Generate scorecard markdown from benchmark results",
    )
    scorecard_cmd.add_argument(
        "results_dir",
        help="Directory containing benchmark result JSON files",
    )
    scorecard_cmd.add_argument(
        "-o",
        "--output",
        default="benchmark/scorecard.md",
        help="Output path for scorecard markdown (default: benchmark/scorecard.md)",
    )

    summary_cmd = sub.add_parser(
        "summary",
        help="Print quick summary to stdout",
    )
    summary_cmd.add_argument(
        "results_dir",
        help="Directory containing benchmark result JSON files",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "scorecard":
        results_dir = Path(args.results_dir)
        if not results_dir.exists():
            print(f"Error: results directory does not exist: {results_dir}", file=sys.stderr)
            sys.exit(1)
        results = load_results(results_dir)
        metrics = compute_metrics(results)
        scorecard = generate_scorecard(metrics)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(scorecard)
        print(f"Scorecard written to {output_path}")
        print(f"({len(results)} result files, {len(metrics)} models)")

    elif args.command == "summary":
        results_dir = Path(args.results_dir)
        if not results_dir.exists():
            print(f"Error: results directory does not exist: {results_dir}", file=sys.stderr)
            sys.exit(1)
        results = load_results(results_dir)
        metrics = compute_metrics(results)
        print_summary(metrics)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
