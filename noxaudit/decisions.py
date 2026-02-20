"""Decision memory: track accepted/dismissed/intentional findings."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from noxaudit.models import Decision, DecisionType, Finding


def load_decisions(decisions_path: str | Path) -> list[Decision]:
    """Load decisions from a JSONL file."""
    path = Path(decisions_path)
    if not path.exists():
        return []

    decisions = []
    for line in path.read_text().strip().splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        decisions.append(
            Decision(
                finding_id=raw["finding_id"],
                decision=DecisionType(raw["decision"]),
                reason=raw.get("reason", ""),
                date=raw.get("date", ""),
                by=raw.get("by", ""),
                file=raw.get("file"),
                file_hash=raw.get("file_hash"),
                focus=raw.get("focus"),
                severity=raw.get("severity"),
                repo=raw.get("repo"),
            )
        )
    return decisions


def save_decision(decisions_path: str | Path, decision: Decision) -> None:
    """Append a decision to the JSONL file."""
    path = Path(decisions_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(decision.to_dict()) + "\n")


def filter_findings(
    findings: list[Finding],
    decisions: list[Decision],
    repo_path: str | Path,
    expiry_days: int = 90,
) -> tuple[list[Finding], int]:
    """Filter findings against decision history.

    Returns (new_findings, resolved_count) where resolved_count is
    how many previous findings are still resolved.
    """
    # Build lookup: finding_id -> most recent decision
    decision_map: dict[str, Decision] = {}
    for d in decisions:
        if d.finding_id not in decision_map or d.date > decision_map[d.finding_id].date:
            decision_map[d.finding_id] = d

    today = date.today()
    new_findings = []
    resolved_count = 0

    for finding in findings:
        decision = decision_map.get(finding.id)
        if decision is None:
            new_findings.append(finding)
            continue

        # Check expiry
        if decision.date:
            decision_date = date.fromisoformat(decision.date)
            if today - decision_date > timedelta(days=expiry_days):
                # Decision expired, resurface
                new_findings.append(finding)
                continue

        # Check if file changed since decision
        if decision.file_hash and finding.file:
            current_hash = _hash_file(Path(repo_path) / finding.file)
            if current_hash != decision.file_hash:
                # File changed, resurface
                new_findings.append(finding)
                continue

        # Decision still valid
        if decision.decision in (DecisionType.ACCEPTED, DecisionType.DISMISSED):
            resolved_count += 1
        elif decision.decision == DecisionType.INTENTIONAL:
            resolved_count += 1

    return new_findings, resolved_count


def format_decision_context(decisions: list[Decision]) -> str:
    """Format decisions as context for the AI provider."""
    if not decisions:
        return ""

    lines = [
        "## Previously Reviewed Findings",
        "",
        "The following findings have already been reviewed. Do NOT report these again",
        "unless the code has materially changed in a way that invalidates the decision.",
        "",
    ]
    for d in decisions:
        status = d.decision.value.upper()
        lines.append(f"- [{status}] finding_id={d.finding_id}: {d.reason}")

    return "\n".join(lines)


def create_baseline_decisions(
    findings: list[Finding],
    repo_path: str | Path,
    by: str = "baseline",
    repo_name: str | None = None,
) -> list[Decision]:
    """Create DISMISSED decisions for each finding with reason='baseline'.

    Computes file hashes so that file changes will resurface the findings.
    Stores focus, severity, and repo_name for later filtering with --undo.
    Returns list of Decision objects (not yet persisted).
    """
    today = date.today().isoformat()
    result = []
    for finding in findings:
        file_hash = _hash_file(Path(repo_path) / finding.file) if finding.file else None
        result.append(
            Decision(
                finding_id=finding.id,
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=today,
                by=by,
                file=finding.file,
                file_hash=file_hash,
                focus=finding.focus,
                severity=finding.severity.value if finding.severity else None,
                repo=repo_name,
            )
        )
    return result


def remove_baseline_decisions(
    decisions_path: str | Path,
    finding_ids: set[str] | None = None,
) -> int:
    """Remove baseline decisions from the JSONL file.

    If finding_ids is given, only removes baselines for those IDs.
    Returns count of removed decisions.
    """
    path = Path(decisions_path)
    if not path.exists():
        return 0

    all_decisions = load_decisions(path)
    kept = []
    removed = 0
    for d in all_decisions:
        is_baseline = d.reason == "baseline"
        matches_filter = finding_ids is None or d.finding_id in finding_ids
        if is_baseline and matches_filter:
            removed += 1
        else:
            kept.append(d)

    path.write_text("".join(json.dumps(d.to_dict()) + "\n" for d in kept))
    return removed


def list_baseline_decisions(decisions_path: str | Path) -> list[Decision]:
    """Return all baseline decisions."""
    return [d for d in load_decisions(decisions_path) if d.reason == "baseline"]


def _hash_file(path: Path) -> str | None:
    """Hash a file's contents for change detection."""
    try:
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]
    except (FileNotFoundError, PermissionError):
        return None
