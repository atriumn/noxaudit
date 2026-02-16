"""Report generation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from noxaudit.models import AuditResult, Severity


def _focus_display(focus: str) -> str:
    """Format focus string for display: 'security+performance' → 'Security + Performance'."""
    return focus.replace("+", " + ").title()


def generate_report(result: AuditResult) -> str:
    """Generate a markdown report from audit results."""
    lines = [
        f"# Nightwatch Report: {_focus_display(result.focus)}",
        "",
        f"- **Repo**: {result.repo}",
        f"- **Focus**: {_focus_display(result.focus)}",
        f"- **Provider**: {result.provider}",
        f"- **Date**: {result.timestamp}",
        "",
        "## Summary",
        "",
        f"- **New findings**: {len(result.new_findings)}",
        f"- **Total findings**: {len(result.findings)}",
        f"- **Previously resolved**: {result.resolved_count}",
        "",
    ]

    if not result.new_findings:
        lines.append("No new findings. Looking good!")
        lines.append("")
    else:
        # Group by severity
        for severity in [Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            findings = [f for f in result.new_findings if f.severity == severity]
            if not findings:
                continue

            icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}[severity.value]
            lines.append(f"## {icon} {severity.value.upper()} ({len(findings)})")
            lines.append("")

            for f in findings:
                loc = f"`{f.file}"
                if f.line:
                    loc += f":{f.line}"
                loc += "`"

                lines.append(f"### {f.title}")
                lines.append("")
                lines.append(f"**Location**: {loc}  ")
                lines.append(f"**ID**: `{f.id}`")
                lines.append("")
                lines.append(f"{f.description}")
                if f.suggestion:
                    lines.append("")
                    lines.append(f"**Suggestion**: {f.suggestion}")
                lines.append("")

    return "\n".join(lines)


def save_report(report: str, reports_dir: str | Path, repo: str, focus: str) -> Path:
    """Save a report to disk."""
    reports_path = Path(reports_dir) / repo
    reports_path.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    report_file = reports_path / f"{date_str}-{focus}.md"
    report_file.write_text(report)
    return report_file


def format_notification(result: AuditResult) -> str:
    """Format a short notification message."""
    focus_icons = {
        "security": "🔒",
        "docs": "📝",
        "patterns": "🏗️",
        "performance": "⚡",
        "hygiene": "🧹",
        "dependencies": "📦",
    }
    # Use specific icon for single focus, generic for combined
    icon = focus_icons.get(result.focus, "🔍")

    lines = [
        f"{icon} {_focus_display(result.focus)} Audit — {result.repo}",
    ]

    if not result.new_findings:
        lines.append("✅ No new findings")
    else:
        high = sum(1 for f in result.new_findings if f.severity == Severity.HIGH)
        medium = sum(1 for f in result.new_findings if f.severity == Severity.MEDIUM)
        low = sum(1 for f in result.new_findings if f.severity == Severity.LOW)

        parts = []
        if high:
            parts.append(f"🔴 {high} high")
        if medium:
            parts.append(f"🟡 {medium} medium")
        if low:
            parts.append(f"🔵 {low} low")
        lines.append(f"{len(result.new_findings)} new findings: {', '.join(parts)}")
        lines.append("")

        # Show top 3 findings
        for f in result.new_findings[:3]:
            sev = {"high": "⚠️", "medium": "ℹ️", "low": "💡"}[f.severity.value]
            lines.append(f"{sev} {f.title}")
            lines.append(f"   {f.file}")

    if result.resolved_count:
        lines.append("")
        lines.append(f"✅ {result.resolved_count} previous findings still resolved")

    return "\n".join(lines)
