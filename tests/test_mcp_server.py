"""Tests for MCP server tools."""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import patch

import pytest

from noxaudit.mcp.server import (
    get_findings,
    get_findings_for_diff,
    get_health_summary,
    record_decision,
)
from noxaudit.mcp.state import save_latest_findings
from noxaudit.models import Finding, Severity


@pytest.fixture
def findings():
    return [
        Finding(
            id="aaa111",
            severity=Severity.HIGH,
            file="src/auth.py",
            line=42,
            title="SQL injection",
            description="User input interpolated into query",
            suggestion="Use parameterized queries",
            focus="security",
        ),
        Finding(
            id="bbb222",
            severity=Severity.MEDIUM,
            file="src/api.ts",
            line=10,
            title="Missing rate limit",
            description="Endpoint has no rate limiting",
            focus="security",
        ),
        Finding(
            id="ccc333",
            severity=Severity.LOW,
            file="README.md",
            line=None,
            title="Stale install instructions",
            description="README references deprecated CLI flag",
            focus="docs",
        ),
    ]


@pytest.fixture
def mcp_state(tmp_path, findings):
    """Set up MCP state in a temp dir and chdir there."""
    save_latest_findings(
        findings,
        repo="my-app",
        focus="security+docs",
        timestamp="2026-02-18T10:00:00",
        resolved_count=2,
        base_path=tmp_path,
    )
    original_dir = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_dir)


class TestGetFindings:
    def test_returns_all_findings(self, mcp_state):
        result = asyncio.run(get_findings())
        assert "3 finding(s)" in result
        assert "SQL injection" in result
        assert "Missing rate limit" in result
        assert "Stale install instructions" in result

    def test_filter_by_file(self, mcp_state):
        result = asyncio.run(get_findings(file="auth.py"))
        assert "1 finding(s)" in result
        assert "SQL injection" in result
        assert "Missing rate limit" not in result

    def test_filter_by_severity(self, mcp_state):
        result = asyncio.run(get_findings(severity="high"))
        assert "1 finding(s)" in result
        assert "SQL injection" in result

    def test_filter_by_focus(self, mcp_state):
        result = asyncio.run(get_findings(focus="docs"))
        assert "1 finding(s)" in result
        assert "Stale install instructions" in result

    def test_limit(self, mcp_state):
        result = asyncio.run(get_findings(limit=1))
        assert "1 finding(s)" in result

    def test_no_matches(self, mcp_state):
        result = asyncio.run(get_findings(file="nonexistent.py"))
        assert "No findings" in result

    def test_no_findings_file(self, tmp_path):
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = asyncio.run(get_findings())
            assert "No findings" in result
        finally:
            os.chdir(original_dir)


class TestGetHealthSummary:
    def test_returns_score(self, mcp_state):
        result = asyncio.run(get_health_summary())
        # score = 100 - 1*15 - 1*5 - 1*1 = 79
        assert "Health Score: 79/100" in result

    def test_severity_counts(self, mcp_state):
        result = asyncio.run(get_health_summary())
        assert "High:   1" in result
        assert "Medium: 1" in result
        assert "Low:    1" in result
        assert "Total:  3" in result

    def test_worst_files(self, mcp_state):
        result = asyncio.run(get_health_summary())
        assert "src/auth.py" in result
        assert "src/api.ts" in result

    def test_focus_areas(self, mcp_state):
        result = asyncio.run(get_health_summary())
        assert "docs" in result
        assert "security" in result

    def test_resolved_count(self, mcp_state):
        result = asyncio.run(get_health_summary())
        assert "Resolved count: 2" in result

    def test_timestamp(self, mcp_state):
        result = asyncio.run(get_health_summary())
        assert "2026-02-18T10:00:00" in result

    def test_repo(self, mcp_state):
        result = asyncio.run(get_health_summary())
        assert "my-app" in result

    def test_score_clamped_at_zero(self, tmp_path):
        """Score can't go below 0 with many findings."""
        many_findings = [
            Finding(
                id=f"f{i}",
                severity=Severity.HIGH,
                file=f"f{i}.py",
                line=1,
                title=f"Finding {i}",
                description="desc",
            )
            for i in range(10)
        ]
        save_latest_findings(many_findings, repo="r", focus="f", timestamp="t", base_path=tmp_path)
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = asyncio.run(get_health_summary())
            assert "Health Score: 0/100" in result
        finally:
            os.chdir(original_dir)


class TestGetFindingsForDiff:
    def test_matching_files(self, mcp_state):
        mock_unstaged = type("R", (), {"stdout": "src/auth.py\n"})()
        mock_staged = type("R", (), {"stdout": ""})()
        with patch("noxaudit.mcp.server.subprocess.run", side_effect=[mock_unstaged, mock_staged]):
            result = asyncio.run(get_findings_for_diff())
        assert "1 finding(s)" in result
        assert "SQL injection" in result

    def test_no_changes(self, mcp_state):
        mock_empty = type("R", (), {"stdout": ""})()
        with patch("noxaudit.mcp.server.subprocess.run", side_effect=[mock_empty, mock_empty]):
            result = asyncio.run(get_findings_for_diff())
        assert "No uncommitted changes" in result

    def test_clean_files_listed(self, mcp_state):
        mock_unstaged = type("R", (), {"stdout": "src/auth.py\nclean_file.py\n"})()
        mock_staged = type("R", (), {"stdout": ""})()
        with patch("noxaudit.mcp.server.subprocess.run", side_effect=[mock_unstaged, mock_staged]):
            result = asyncio.run(get_findings_for_diff())
        assert "clean_file.py" in result
        assert "Clean changed files" in result

    def test_no_findings_for_changed_files(self, mcp_state):
        mock_unstaged = type("R", (), {"stdout": "clean_only.py\n"})()
        mock_staged = type("R", (), {"stdout": ""})()
        with patch("noxaudit.mcp.server.subprocess.run", side_effect=[mock_unstaged, mock_staged]):
            result = asyncio.run(get_findings_for_diff())
        assert "No findings in changed files" in result

    def test_staged_changes_included(self, mcp_state):
        mock_unstaged = type("R", (), {"stdout": ""})()
        mock_staged = type("R", (), {"stdout": "src/api.ts\n"})()
        with patch("noxaudit.mcp.server.subprocess.run", side_effect=[mock_unstaged, mock_staged]):
            result = asyncio.run(get_findings_for_diff())
        assert "Missing rate limit" in result


class TestRecordDecision:
    def test_valid_decision(self, mcp_state):
        result = asyncio.run(
            record_decision(
                finding_id="aaa111",
                action="dismiss",
                reason="Not relevant",
            )
        )
        assert "Decision recorded" in result
        assert "dismiss" in result

        # Verify persisted
        decisions_path = mcp_state / ".noxaudit" / "decisions.jsonl"
        assert decisions_path.exists()
        data = json.loads(decisions_path.read_text().strip())
        assert data["finding_id"] == "aaa111"
        assert data["decision"] == "dismissed"

    def test_invalid_action(self, mcp_state):
        result = asyncio.run(
            record_decision(
                finding_id="aaa111",
                action="invalid",
                reason="test",
            )
        )
        assert "Invalid action" in result

    def test_unknown_finding(self, mcp_state):
        result = asyncio.run(
            record_decision(
                finding_id="zzz999",
                action="dismiss",
                reason="test",
            )
        )
        assert "not found" in result

    def test_accept_action(self, mcp_state):
        result = asyncio.run(
            record_decision(
                finding_id="bbb222",
                action="accept",
                reason="Fixed",
            )
        )
        assert "Decision recorded" in result
        assert "accept" in result

    def test_intentional_action(self, mcp_state):
        result = asyncio.run(
            record_decision(
                finding_id="ccc333",
                action="intentional",
                reason="By design",
            )
        )
        assert "Decision recorded" in result
