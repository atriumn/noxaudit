"""Tests for decision memory."""

from __future__ import annotations

from datetime import date, timedelta

from noxaudit.decisions import (
    filter_findings,
    format_decision_context,
    load_decisions,
    save_decision,
)
from noxaudit.models import Decision, DecisionType, Finding, Severity


def _make_finding(id: str = "abc123", file: str = "a.py") -> Finding:
    return Finding(
        id=id,
        severity=Severity.MEDIUM,
        file=file,
        line=1,
        title="Test",
        description="Test finding",
    )


def _make_decision(
    finding_id: str = "abc123",
    decision: DecisionType = DecisionType.DISMISSED,
    days_ago: int = 10,
) -> Decision:
    d = date.today() - timedelta(days=days_ago)
    return Decision(
        finding_id=finding_id,
        decision=decision,
        reason="test",
        date=d.isoformat(),
        by="user",
    )


class TestLoadSaveDecisions:
    def test_load_empty(self, tmp_path):
        decisions = load_decisions(tmp_path / "nope.jsonl")
        assert decisions == []

    def test_roundtrip(self, tmp_path):
        path = tmp_path / "decisions.jsonl"
        d = _make_decision()
        save_decision(path, d)
        loaded = load_decisions(path)
        assert len(loaded) == 1
        assert loaded[0].finding_id == "abc123"

    def test_multiple_decisions(self, tmp_path):
        path = tmp_path / "decisions.jsonl"
        save_decision(path, _make_decision("aaa"))
        save_decision(path, _make_decision("bbb"))
        loaded = load_decisions(path)
        assert len(loaded) == 2


class TestFilterFindings:
    def test_new_finding_passes(self, tmp_path):
        findings = [_make_finding("new1")]
        new, resolved = filter_findings(findings, [], str(tmp_path))
        assert len(new) == 1
        assert resolved == 0

    def test_dismissed_finding_filtered(self, tmp_path):
        findings = [_make_finding("abc")]
        decisions = [_make_decision("abc", DecisionType.DISMISSED)]
        new, resolved = filter_findings(findings, decisions, str(tmp_path))
        assert len(new) == 0
        assert resolved == 1

    def test_expired_decision_resurfaces(self, tmp_path):
        findings = [_make_finding("abc")]
        decisions = [_make_decision("abc", days_ago=100)]
        new, resolved = filter_findings(findings, decisions, str(tmp_path), expiry_days=90)
        assert len(new) == 1

    def test_intentional_counts_as_resolved(self, tmp_path):
        findings = [_make_finding("abc")]
        decisions = [_make_decision("abc", DecisionType.INTENTIONAL)]
        new, resolved = filter_findings(findings, decisions, str(tmp_path))
        assert len(new) == 0
        assert resolved == 1


class TestFormatDecisionContext:
    def test_empty(self):
        assert format_decision_context([]) == ""

    def test_includes_decision_info(self):
        decisions = [_make_decision("abc", DecisionType.DISMISSED)]
        ctx = format_decision_context(decisions)
        assert "DISMISSED" in ctx
        assert "abc" in ctx
