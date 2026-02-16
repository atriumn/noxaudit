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


def _hash_file(path: Path) -> str | None:
    """Hash a file's contents for change detection."""
    try:
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]
    except (FileNotFoundError, PermissionError):
        return None
