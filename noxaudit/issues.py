"""Auto-create GitHub issues for findings above severity threshold."""

from __future__ import annotations

import json
import shutil
import subprocess
import time

from noxaudit.config import IssuesConfig
from noxaudit.models import AuditResult, Finding

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def create_issues_for_findings(
    result: AuditResult,
    issues_config: IssuesConfig,
) -> list[str]:
    """Create GitHub issues for new findings at or above the severity threshold.

    Returns list of created issue URLs.
    """
    if not issues_config.enabled:
        return []

    if not _gh_available():
        print(f"[{result.repo}] gh CLI not available — skipping issue creation")
        return []

    if not _gh_authenticated():
        print(f"[{result.repo}] gh not authenticated — skipping issue creation")
        return []

    threshold = SEVERITY_ORDER.get(issues_config.severity_threshold, 1)
    qualifying = [
        f for f in result.new_findings if SEVERITY_ORDER.get(f.severity.value, 0) >= threshold
    ]

    if not qualifying:
        return []

    print(f"[{result.repo}] Creating issues for {len(qualifying)} findings...")
    created = []

    for finding in qualifying:
        if _issue_exists(finding):
            print(f"[{result.repo}]   Skipping {finding.id[:8]} (issue exists)")
            continue

        url = _create_issue(finding, result, issues_config)
        if url:
            created.append(url)
            print(f"[{result.repo}]   Created: {url}")

        # Rate limit courtesy
        if qualifying.index(finding) < len(qualifying) - 1:
            time.sleep(1)

    return created


def _gh_available() -> bool:
    return shutil.which("gh") is not None


def _gh_authenticated() -> bool:
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _issue_exists(finding: Finding) -> bool:
    """Check if an issue already exists for this finding via marker comment."""
    marker = f"noxaudit-finding-id: {finding.id}"
    try:
        result = subprocess.run(
            ["gh", "issue", "list", "--search", marker, "--state", "open", "--json", "number"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return False
        issues = json.loads(result.stdout)
        return len(issues) > 0
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
        return False


def _create_issue(
    finding: Finding,
    result: AuditResult,
    config: IssuesConfig,
) -> str | None:
    """Create a single GitHub issue. Returns issue URL or None."""
    severity = finding.severity.value
    title = f"[noxaudit/{severity}] {finding.title}"

    location = finding.file
    if finding.line:
        location = f"{finding.file}:{finding.line}"

    body_parts = [
        f"**Severity:** {severity}",
        f"**Location:** `{location}`",
        f"**Focus area:** {result.focus.replace('+', ' + ')}",
        "",
        "### Description",
        finding.description,
    ]

    if finding.suggestion:
        body_parts.extend(["", "### Suggestion", finding.suggestion])

    body_parts.extend(
        [
            "",
            "---",
            f"*Found by [Noxaudit]({config.repository_url}) ({result.provider}, {result.timestamp})*",
            "",
            f"<!-- noxaudit-finding-id: {finding.id} -->",
        ]
    )

    body = "\n".join(body_parts)

    labels = list(config.labels) + [f"noxaudit:{severity}"]

    cmd = [
        "gh",
        "issue",
        "create",
        "--title",
        title,
        "--body",
        body,
    ]

    for label in labels:
        cmd.extend(["--label", label])

    for assignee in config.assignees:
        cmd.extend(["--assignee", assignee])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            print(f"  Warning: gh issue create failed: {stderr}")
            return None
        return proc.stdout.strip()
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"  Warning: gh issue create error: {e}")
        return None
