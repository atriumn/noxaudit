"""MCP server for noxaudit — exposes audit findings to AI coding tools."""

from __future__ import annotations

import subprocess
from datetime import date

from mcp.server.fastmcp import FastMCP

from noxaudit.decisions import save_decision
from noxaudit.mcp.state import load_latest_findings, load_latest_metadata
from noxaudit.models import Decision, DecisionType, Severity

mcp = FastMCP("noxaudit")


@mcp.tool()
async def get_findings(
    file: str | None = None,
    severity: str | None = None,
    focus: str | None = None,
    limit: int = 20,
) -> str:
    """Get open findings from the most recent audit.

    Args:
        file: Filter by file path (substring match)
        severity: Filter by severity level (high, medium, low)
        focus: Filter by focus area (security, docs, patterns, etc.)
        limit: Maximum number of findings to return (default 20)
    """
    findings = load_latest_findings()

    if file:
        findings = [f for f in findings if file in f.file]
    if severity:
        findings = [f for f in findings if f.severity.value == severity.lower()]
    if focus:
        findings = [f for f in findings if f.focus == focus.lower()]

    findings = findings[:limit]

    if not findings:
        return "No findings match the given filters."

    lines = [f"Found {len(findings)} finding(s):\n"]
    for f in findings:
        sev = f.severity.value.upper()
        loc = f"{f.file}:{f.line}" if f.line else f.file
        focus_tag = f" [{f.focus}]" if f.focus else ""
        lines.append(f"[{sev}]{focus_tag} {f.id} — {f.title}")
        lines.append(f"  Location: {loc}")
        lines.append(f"  {f.description}")
        if f.suggestion:
            lines.append(f"  Suggestion: {f.suggestion}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def get_health_summary() -> str:
    """Get a health summary for the current repository.

    Returns score (0-100), open finding counts by severity, worst files,
    last audit timestamp, focus areas covered, and trend.
    """
    findings = load_latest_findings()
    metadata = load_latest_metadata()

    high = sum(1 for f in findings if f.severity == Severity.HIGH)
    medium = sum(1 for f in findings if f.severity == Severity.MEDIUM)
    low = sum(1 for f in findings if f.severity == Severity.LOW)
    score = max(0, min(100, 100 - high * 15 - medium * 5 - low * 1))

    # Worst files by finding count
    file_counts: dict[str, int] = {}
    for f in findings:
        file_counts[f.file] = file_counts.get(f.file, 0) + 1
    worst_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Focus areas covered
    focus_areas = sorted({f.focus for f in findings if f.focus})

    resolved_count = metadata.get("resolved_count", 0)

    lines = [
        f"Health Score: {score}/100",
        "",
        "Findings by severity:",
        f"  High:   {high}",
        f"  Medium: {medium}",
        f"  Low:    {low}",
        f"  Total:  {len(findings)}",
        "",
    ]

    if worst_files:
        lines.append("Worst files:")
        for path, count in worst_files:
            lines.append(f"  {path}: {count} finding(s)")
        lines.append("")

    if focus_areas:
        lines.append(f"Focus areas covered: {', '.join(focus_areas)}")

    lines.append(f"Resolved count: {resolved_count}")

    if metadata.get("timestamp"):
        lines.append(f"Last audit: {metadata['timestamp']}")

    if metadata.get("repo"):
        lines.append(f"Repository: {metadata['repo']}")

    return "\n".join(lines)


@mcp.tool()
async def get_findings_for_diff() -> str:
    """Get findings for files that have uncommitted changes.

    Cross-references git working tree (staged + unstaged) with latest findings.
    """
    try:
        unstaged = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "Error: Could not run git diff. Are you in a git repository?"

    changed_files = set()
    for output in (unstaged.stdout, staged.stdout):
        for line in output.strip().splitlines():
            if line.strip():
                changed_files.add(line.strip())

    if not changed_files:
        return "No uncommitted changes detected."

    findings = load_latest_findings()
    matched = [f for f in findings if f.file in changed_files]
    clean_files = sorted(changed_files - {f.file for f in matched})

    lines = []
    if matched:
        lines.append(f"Found {len(matched)} finding(s) in changed files:\n")
        for f in matched:
            sev = f.severity.value.upper()
            loc = f"{f.file}:{f.line}" if f.line else f.file
            focus_tag = f" [{f.focus}]" if f.focus else ""
            lines.append(f"[{sev}]{focus_tag} {f.id} — {f.title}")
            lines.append(f"  Location: {loc}")
            lines.append(f"  {f.description}")
            if f.suggestion:
                lines.append(f"  Suggestion: {f.suggestion}")
            lines.append("")
    else:
        lines.append("No findings in changed files.")

    if clean_files:
        lines.append(f"Clean changed files ({len(clean_files)}):")
        for path in clean_files:
            lines.append(f"  {path}")

    return "\n".join(lines)


@mcp.tool()
async def record_decision(
    finding_id: str,
    action: str,
    reason: str,
) -> str:
    """Record a decision about a finding.

    Args:
        finding_id: The ID of the finding to decide on
        action: Decision type: "accept", "dismiss", or "intentional"
        reason: Why this decision was made
    """
    valid_actions = {
        "accept": DecisionType.ACCEPTED,
        "dismiss": DecisionType.DISMISSED,
        "intentional": DecisionType.INTENTIONAL,
    }
    if action.lower() not in valid_actions:
        return f"Invalid action: {action}. Must be one of: accept, dismiss, intentional"

    # Validate finding exists
    findings = load_latest_findings()
    finding = next((f for f in findings if f.id == finding_id), None)
    if finding is None:
        return f"Finding {finding_id} not found in latest findings."

    # Compute file hash for change detection
    file_hash = None
    if finding.file:
        from noxaudit.decisions import _hash_file
        from pathlib import Path

        file_hash = _hash_file(Path(finding.file))

    decision = Decision(
        finding_id=finding_id,
        decision=valid_actions[action.lower()],
        reason=reason,
        date=date.today().isoformat(),
        by="mcp",
        file=finding.file,
        file_hash=file_hash,
    )

    save_decision(".noxaudit/decisions.jsonl", decision)
    return f"Decision recorded: {action} finding {finding_id} — {reason}"


@mcp.tool()
async def run_audit(
    focus: str = "security",
    dry_run: bool = False,
) -> str:
    """Run an on-demand audit and return findings.

    Note: This requires API keys and may take 1-3 minutes.

    Args:
        focus: Focus area for the audit (e.g. security, docs, patterns)
        dry_run: If True, show what would be audited without calling AI
    """
    from noxaudit.config import load_config
    from noxaudit.runner import run_audit as runner_run_audit

    try:
        config = load_config()
    except Exception as e:
        return f"Error loading config: {e}"

    try:
        results = runner_run_audit(config, focus_name=focus, dry_run=dry_run)
    except Exception as e:
        return f"Error running audit: {e}"

    if not results:
        return "No results. Check that focus area is valid."

    lines = []
    for result in results:
        lines.append(f"Repo: {result.repo}")
        lines.append(f"Focus: {result.focus}")
        lines.append(f"Provider: {result.provider}")
        lines.append(f"Total findings: {len(result.findings)}")
        lines.append(f"New findings: {len(result.new_findings)}")
        lines.append(f"Resolved: {result.resolved_count}")
        lines.append("")
        for f in result.new_findings[:20]:
            sev = f.severity.value.upper()
            loc = f"{f.file}:{f.line}" if f.line else f.file
            lines.append(f"  [{sev}] {f.title} @ {loc}")
            lines.append(f"    {f.description}")
            lines.append("")

    return "\n".join(lines) if lines else "Audit completed with no findings."


def run_server() -> None:
    """Start the MCP server via stdio transport."""
    mcp.run(transport="stdio")
