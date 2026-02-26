"""Read-only state access for MCP tools — reads from .noxaudit/ directory."""

from __future__ import annotations

import json
from pathlib import Path

from noxaudit.models import Finding, Severity

LATEST_FINDINGS_FILE = ".noxaudit/latest-findings.json"
FINDINGS_HISTORY_FILE = ".noxaudit/findings-history.jsonl"


def load_latest_findings(base_path: str | Path = ".") -> list[Finding]:
    """Load findings from the latest-findings.json file."""
    path = Path(base_path) / LATEST_FINDINGS_FILE
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    return [_finding_from_dict(f) for f in data.get("findings", [])]


def load_latest_metadata(base_path: str | Path = ".") -> dict:
    """Load metadata (timestamp, repo, focus) from latest-findings.json."""
    path = Path(base_path) / LATEST_FINDINGS_FILE
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}

    return {
        "repo": data.get("repo", ""),
        "focus": data.get("focus", ""),
        "timestamp": data.get("timestamp", ""),
        "resolved_count": data.get("resolved_count", 0),
    }


def save_latest_findings(
    findings: list[Finding],
    repo: str,
    focus: str,
    timestamp: str,
    resolved_count: int = 0,
    provider: str = "",
    base_path: str | Path = ".",
) -> Path:
    """Serialize findings to latest-findings.json for MCP tools to query."""
    path = Path(base_path) / LATEST_FINDINGS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": timestamp,
        "repo": repo,
        "focus": focus,
        "provider": provider,
        "findings": [f.to_dict() for f in findings],
        "new_findings_count": len(findings),
        "resolved_count": resolved_count,
    }

    path.write_text(json.dumps(data, indent=2))
    return path


def append_findings_history(
    findings: list[Finding],
    repo: str,
    focus: str,
    timestamp: str,
    provider: str = "",
    base_path: str | Path = ".",
) -> Path:
    """Append a findings record to findings-history.jsonl for trend analysis."""
    path = Path(base_path) / FINDINGS_HISTORY_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": timestamp,
        "repo": repo,
        "focus": focus,
        "provider": provider,
        "findings": [f.to_dict() for f in findings],
    }

    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")

    return path


def _finding_from_dict(raw: dict) -> Finding:
    """Reconstruct a Finding from a serialized dict."""
    return Finding(
        id=raw["id"],
        severity=Severity(raw["severity"]),
        file=raw["file"],
        line=raw.get("line"),
        title=raw["title"],
        description=raw["description"],
        suggestion=raw.get("suggestion"),
        focus=raw.get("focus"),
    )
