"""SARIF 2.1.0 output format for GitHub Code Scanning integration."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from noxaudit.models import Finding, Severity


def findings_to_sarif(findings: list[Finding], focus: str, repo: str) -> dict:
    """Convert findings to a SARIF 2.1.0 document.

    Args:
        findings: List of Finding objects
        focus: Focus area label(s) (e.g., 'security' or 'security+performance')
        repo: Repository name

    Returns:
        A SARIF 2.1.0 run object as a dict
    """
    # Build rules from unique focus areas
    rule_ids = set()
    for finding in findings:
        if finding.focus:
            rule_ids.add(finding.focus)

    # If no explicit focus in findings, use the focus parameter
    if not rule_ids:
        rule_ids = {f.strip() for f in focus.split("+") if f.strip()}

    rules = []
    for rule_id in sorted(rule_ids):
        rules.append(
            {
                "id": f"noxaudit/{rule_id}",
                "name": rule_id.capitalize(),
                "shortDescription": {"text": f"{rule_id.capitalize()} audit"},
                "defaultConfiguration": {"level": "warning"},
            }
        )

    # Convert findings to results
    results = []
    for finding in findings:
        result = _finding_to_sarif_result(finding)
        results.append(result)

    # Build the SARIF run object
    return {
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "noxaudit",
                        "version": _get_noxaudit_version(),
                        "informationUri": "https://github.com/atriumn/noxaudit",
                        "rules": rules,
                    }
                },
                "results": results,
                "properties": {
                    "repo": repo,
                    "focus": focus,
                },
            }
        ],
    }


def _finding_to_sarif_result(finding: Finding) -> dict:
    """Convert a single Finding to a SARIF result object."""
    # Map severity to SARIF level
    level_map = {
        Severity.HIGH: "error",
        Severity.MEDIUM: "warning",
        Severity.LOW: "note",
    }
    level = level_map.get(finding.severity, "warning")

    # Use focus area as rule ID, default to 'general' if not set
    rule_id = f"noxaudit/{finding.focus}" if finding.focus else "noxaudit/general"

    # Build message with title and description
    message_text = finding.title
    if finding.description:
        message_text = f"{finding.title}: {finding.description}"

    result: dict = {
        "ruleId": rule_id,
        "level": level,
        "message": {"text": message_text},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": finding.file,
                        "uriBaseId": "%SRCROOT%",
                    },
                    **({"region": {"startLine": finding.line}} if finding.line else {}),
                }
            }
        ],
        "fingerprints": {
            "noxauditFindingId": finding.id,
        },
    }

    # Add fix suggestion if present
    if finding.suggestion:
        result["fixes"] = [
            {
                "description": {"text": finding.suggestion},
                "artifactChanges": [
                    {
                        "artifactLocation": {
                            "uri": finding.file,
                            "uriBaseId": "%SRCROOT%",
                        },
                        "replacements": [
                            {
                                "deletedRegion": {
                                    "startLine": finding.line or 1,
                                },
                                "insertedContent": {
                                    "text": finding.suggestion,
                                },
                            }
                        ],
                    }
                ],
            }
        ]

    return result


def save_sarif(sarif: dict, reports_dir: str | Path, repo: str, focus: str) -> str:
    """Save SARIF JSON to file, return path.

    Args:
        sarif: SARIF document (from findings_to_sarif)
        reports_dir: Directory to save reports
        repo: Repository name
        focus: Focus area label

    Returns:
        Path to the saved SARIF file
    """
    reports_path = Path(reports_dir) / repo
    reports_path.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    sarif_file = reports_path / f"{date_str}-{focus}.sarif"
    sarif_file.write_text(json.dumps(sarif, indent=2))
    return str(sarif_file)


def _get_noxaudit_version() -> str:
    """Get noxaudit version from package."""
    try:
        from noxaudit import __version__

        return __version__
    except (ImportError, AttributeError):
        return "0.2.0"
