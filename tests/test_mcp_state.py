"""Tests for MCP state module — latest-findings.json read/write."""

from __future__ import annotations

import json

import pytest

from noxaudit.mcp.state import (
    FINDINGS_HISTORY_FILE,
    LATEST_FINDINGS_FILE,
    append_findings_history,
    load_latest_findings,
    load_latest_metadata,
    save_latest_findings,
)
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
    ]


class TestSaveLatestFindings:
    def test_creates_file(self, tmp_path, findings):
        path = save_latest_findings(
            findings,
            repo="my-app",
            focus="security",
            timestamp="2026-02-18T10:00:00",
            base_path=tmp_path,
        )
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["repo"] == "my-app"
        assert data["focus"] == "security"
        assert len(data["findings"]) == 2

    def test_creates_parent_dirs(self, tmp_path, findings):
        base = tmp_path / "nested" / "dir"
        save_latest_findings(findings, repo="r", focus="f", timestamp="t", base_path=base)
        assert (base / LATEST_FINDINGS_FILE).exists()

    def test_includes_resolved_count(self, tmp_path, findings):
        save_latest_findings(
            findings,
            repo="r",
            focus="f",
            timestamp="t",
            resolved_count=5,
            base_path=tmp_path,
        )
        data = json.loads((tmp_path / LATEST_FINDINGS_FILE).read_text())
        assert data["resolved_count"] == 5

    def test_includes_provider(self, tmp_path, findings):
        save_latest_findings(
            findings,
            repo="r",
            focus="f",
            timestamp="t",
            provider="anthropic",
            base_path=tmp_path,
        )
        data = json.loads((tmp_path / LATEST_FINDINGS_FILE).read_text())
        assert data["provider"] == "anthropic"

    def test_includes_new_findings_count(self, tmp_path, findings):
        save_latest_findings(
            findings,
            repo="r",
            focus="f",
            timestamp="t",
            base_path=tmp_path,
        )
        data = json.loads((tmp_path / LATEST_FINDINGS_FILE).read_text())
        assert data["new_findings_count"] == len(findings)

    def test_provider_defaults_to_empty_string(self, tmp_path, findings):
        save_latest_findings(findings, repo="r", focus="f", timestamp="t", base_path=tmp_path)
        data = json.loads((tmp_path / LATEST_FINDINGS_FILE).read_text())
        assert data["provider"] == ""


class TestAppendFindingsHistory:
    def test_creates_file(self, tmp_path, findings):
        path = append_findings_history(
            findings,
            repo="my-app",
            focus="security",
            timestamp="2026-02-18T10:00:00",
            provider="anthropic",
            base_path=tmp_path,
        )
        assert path.exists()
        lines = path.read_text().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["repo"] == "my-app"
        assert record["focus"] == "security"
        assert record["timestamp"] == "2026-02-18T10:00:00"
        assert record["provider"] == "anthropic"
        assert len(record["findings"]) == 2

    def test_appends_multiple_runs(self, tmp_path, findings):
        append_findings_history(
            findings, repo="r", focus="security", timestamp="t1", base_path=tmp_path
        )
        append_findings_history(
            findings[:1], repo="r", focus="patterns", timestamp="t2", base_path=tmp_path
        )
        lines = (tmp_path / FINDINGS_HISTORY_FILE).read_text().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["focus"] == "security"
        assert json.loads(lines[1])["focus"] == "patterns"

    def test_creates_parent_dirs(self, tmp_path, findings):
        base = tmp_path / "nested" / "dir"
        path = append_findings_history(findings, repo="r", focus="f", timestamp="t", base_path=base)
        assert path.exists()


class TestLoadLatestFindings:
    def test_empty_when_no_file(self, tmp_path):
        assert load_latest_findings(tmp_path) == []

    def test_roundtrip(self, tmp_path, findings):
        save_latest_findings(
            findings,
            repo="my-app",
            focus="security",
            timestamp="2026-02-18T10:00:00",
            base_path=tmp_path,
        )
        loaded = load_latest_findings(tmp_path)
        assert len(loaded) == 2
        assert loaded[0].id == "aaa111"
        assert loaded[0].severity == Severity.HIGH
        assert loaded[0].file == "src/auth.py"
        assert loaded[0].line == 42
        assert loaded[0].title == "SQL injection"
        assert loaded[0].focus == "security"
        assert loaded[0].suggestion == "Use parameterized queries"

    def test_handles_corrupt_json(self, tmp_path):
        (tmp_path / ".noxaudit").mkdir()
        (tmp_path / LATEST_FINDINGS_FILE).write_text("not json")
        assert load_latest_findings(tmp_path) == []

    def test_finding_without_optional_fields(self, tmp_path):
        finding = Finding(
            id="xxx",
            severity=Severity.LOW,
            file="f.py",
            line=None,
            title="T",
            description="D",
        )
        save_latest_findings([finding], repo="r", focus="f", timestamp="t", base_path=tmp_path)
        loaded = load_latest_findings(tmp_path)
        assert loaded[0].line is None
        assert loaded[0].suggestion is None
        assert loaded[0].focus is None


class TestLoadLatestMetadata:
    def test_empty_when_no_file(self, tmp_path):
        assert load_latest_metadata(tmp_path) == {}

    def test_returns_metadata(self, tmp_path, findings):
        save_latest_findings(
            findings,
            repo="my-app",
            focus="security+docs",
            timestamp="2026-02-18T10:00:00",
            resolved_count=3,
            base_path=tmp_path,
        )
        meta = load_latest_metadata(tmp_path)
        assert meta["repo"] == "my-app"
        assert meta["focus"] == "security+docs"
        assert meta["timestamp"] == "2026-02-18T10:00:00"
        assert meta["resolved_count"] == 3
