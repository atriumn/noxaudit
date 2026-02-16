"""Tests for data models."""

from __future__ import annotations

from noxaudit.models import AuditResult, Decision, DecisionType, Finding, Severity


class TestFinding:
    def test_to_dict_without_focus(self):
        f = Finding(
            id="abc123",
            severity=Severity.HIGH,
            file="test.py",
            line=10,
            title="Bug",
            description="A bug",
        )
        d = f.to_dict()
        assert d["id"] == "abc123"
        assert d["severity"] == "high"
        assert "focus" not in d

    def test_to_dict_with_focus(self):
        f = Finding(
            id="abc123",
            severity=Severity.HIGH,
            file="test.py",
            line=10,
            title="Bug",
            description="A bug",
            focus="security",
        )
        d = f.to_dict()
        assert d["focus"] == "security"

    def test_to_dict_with_suggestion(self):
        f = Finding(
            id="abc123",
            severity=Severity.LOW,
            file="test.py",
            line=None,
            title="Hint",
            description="A hint",
            suggestion="Do this",
        )
        d = f.to_dict()
        assert d["suggestion"] == "Do this"
        assert d["line"] is None

    def test_focus_defaults_to_none(self):
        f = Finding(
            id="x",
            severity=Severity.LOW,
            file="a.py",
            line=1,
            title="t",
            description="d",
        )
        assert f.focus is None


class TestDecision:
    def test_to_dict_minimal(self):
        d = Decision(
            finding_id="abc",
            decision=DecisionType.DISMISSED,
            reason="not relevant",
            date="2026-01-01",
            by="user",
        )
        result = d.to_dict()
        assert result["decision"] == "dismissed"
        assert "file" not in result
        assert "file_hash" not in result

    def test_to_dict_with_file_info(self):
        d = Decision(
            finding_id="abc",
            decision=DecisionType.ACCEPTED,
            reason="fixed",
            date="2026-01-01",
            by="user",
            file="src/auth.py",
            file_hash="abcd1234",
        )
        result = d.to_dict()
        assert result["file"] == "src/auth.py"
        assert result["file_hash"] == "abcd1234"


class TestAuditResult:
    def test_defaults(self):
        r = AuditResult(repo="test", focus="security", provider="anthropic")
        assert r.findings == []
        assert r.new_findings == []
        assert r.resolved_count == 0
        assert r.timestamp == ""
