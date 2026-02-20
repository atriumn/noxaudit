"""Tests for noxaudit baseline command."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from click.testing import CliRunner

from noxaudit.cli import main
from noxaudit.decisions import (
    create_baseline_decisions,
    filter_findings,
    list_baseline_decisions,
    load_decisions,
    remove_baseline_decisions,
    save_decision,
)
from noxaudit.models import Decision, DecisionType, Finding, Severity


def _make_finding(
    id: str = "abc123",
    file: str = "a.py",
    focus: str | None = "security",
    severity: Severity = Severity.HIGH,
) -> Finding:
    return Finding(
        id=id,
        severity=severity,
        file=file,
        line=1,
        title="Test finding",
        description="Test description",
        focus=focus,
    )


def _write_latest_findings(
    base_path: Path,
    findings: list[Finding],
    repo: str = "my-app",
    focus: str = "security",
) -> None:
    noxaudit_dir = base_path / ".noxaudit"
    noxaudit_dir.mkdir(exist_ok=True)
    data = {
        "repo": repo,
        "focus": focus,
        "timestamp": "2026-02-19T10:00:00",
        "resolved_count": 0,
        "findings": [f.to_dict() for f in findings],
    }
    (noxaudit_dir / "latest-findings.json").write_text(json.dumps(data))


class TestCreateBaselineDecisions:
    def test_creates_dismissed_decisions(self, tmp_path):
        findings = [_make_finding("aaa"), _make_finding("bbb", file="b.py")]
        decisions = create_baseline_decisions(findings, tmp_path)
        assert len(decisions) == 2
        for d in decisions:
            assert d.decision == DecisionType.DISMISSED
            assert d.reason == "baseline"
            assert d.by == "baseline"
            assert d.date == date.today().isoformat()

    def test_stores_file_path(self, tmp_path):
        finding = _make_finding("aaa", file="src/app.py")
        decisions = create_baseline_decisions([finding], tmp_path)
        assert decisions[0].file == "src/app.py"

    def test_computes_file_hash_when_file_exists(self, tmp_path):
        (tmp_path / "a.py").write_text("print('hello')")
        finding = _make_finding("aaa", file="a.py")
        decisions = create_baseline_decisions([finding], tmp_path)
        assert decisions[0].file_hash is not None

    def test_no_hash_for_missing_file(self, tmp_path):
        finding = _make_finding("aaa", file="nonexistent.py")
        decisions = create_baseline_decisions([finding], tmp_path)
        assert decisions[0].file_hash is None

    def test_custom_by(self, tmp_path):
        finding = _make_finding()
        decisions = create_baseline_decisions([finding], tmp_path, by="ci-pipeline")
        assert decisions[0].by == "ci-pipeline"

    def test_empty_findings(self, tmp_path):
        decisions = create_baseline_decisions([], tmp_path)
        assert decisions == []


class TestRemoveBaselineDecisions:
    def test_removes_all_baselines(self, tmp_path):
        path = tmp_path / "decisions.jsonl"
        save_decision(
            path,
            Decision(
                finding_id="aaa",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
            ),
        )
        save_decision(
            path,
            Decision(
                finding_id="bbb",
                decision=DecisionType.DISMISSED,
                reason="user decision",
                date=date.today().isoformat(),
                by="user",
            ),
        )

        count = remove_baseline_decisions(path)
        assert count == 1

        remaining = load_decisions(path)
        assert len(remaining) == 1
        assert remaining[0].finding_id == "bbb"

    def test_removes_specific_finding_ids(self, tmp_path):
        path = tmp_path / "decisions.jsonl"
        save_decision(
            path,
            Decision(
                finding_id="aaa",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
            ),
        )
        save_decision(
            path,
            Decision(
                finding_id="bbb",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
            ),
        )

        count = remove_baseline_decisions(path, finding_ids={"aaa"})
        assert count == 1

        remaining = load_decisions(path)
        assert len(remaining) == 1
        assert remaining[0].finding_id == "bbb"

    def test_returns_zero_for_missing_file(self, tmp_path):
        count = remove_baseline_decisions(tmp_path / "nope.jsonl")
        assert count == 0

    def test_preserves_non_baseline_decisions(self, tmp_path):
        path = tmp_path / "decisions.jsonl"
        save_decision(
            path,
            Decision(
                finding_id="aaa",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
            ),
        )
        save_decision(
            path,
            Decision(
                finding_id="bbb",
                decision=DecisionType.INTENTIONAL,
                reason="by design",
                date=date.today().isoformat(),
                by="engineer",
            ),
        )

        remove_baseline_decisions(path)

        remaining = load_decisions(path)
        assert len(remaining) == 1
        assert remaining[0].finding_id == "bbb"
        assert remaining[0].reason == "by design"

    def test_empty_finding_ids_removes_nothing(self, tmp_path):
        path = tmp_path / "decisions.jsonl"
        save_decision(
            path,
            Decision(
                finding_id="aaa",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
            ),
        )

        count = remove_baseline_decisions(path, finding_ids=set())
        assert count == 0
        assert len(load_decisions(path)) == 1


class TestListBaselineDecisions:
    def test_returns_baseline_decisions_only(self, tmp_path):
        path = tmp_path / "decisions.jsonl"
        save_decision(
            path,
            Decision(
                finding_id="aaa",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
            ),
        )
        save_decision(
            path,
            Decision(
                finding_id="bbb",
                decision=DecisionType.DISMISSED,
                reason="user",
                date=date.today().isoformat(),
                by="user",
            ),
        )

        baselines = list_baseline_decisions(path)
        assert len(baselines) == 1
        assert baselines[0].finding_id == "aaa"

    def test_empty_for_no_baselines(self, tmp_path):
        baselines = list_baseline_decisions(tmp_path / "nope.jsonl")
        assert baselines == []

    def test_counts_multiple(self, tmp_path):
        path = tmp_path / "decisions.jsonl"
        for fid in ["a1", "b2", "c3"]:
            save_decision(
                path,
                Decision(
                    finding_id=fid,
                    decision=DecisionType.DISMISSED,
                    reason="baseline",
                    date=date.today().isoformat(),
                    by="baseline",
                ),
            )

        baselines = list_baseline_decisions(path)
        assert len(baselines) == 3


class TestBaselineIntegration:
    def test_baselined_findings_filtered_in_subsequent_audit(self, tmp_path):
        """Baselined findings are suppressed by filter_findings."""
        test_file = tmp_path / "src" / "app.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("print('hello')")

        finding = _make_finding("aaa", file="src/app.py")
        baseline_decisions = create_baseline_decisions([finding], tmp_path)

        new_findings, resolved = filter_findings([finding], baseline_decisions, tmp_path)
        assert len(new_findings) == 0
        assert resolved == 1

    def test_file_change_resurfaces_baselined_finding(self, tmp_path):
        """File change causes a baselined finding to resurface."""
        test_file = tmp_path / "src" / "app.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("original content")

        finding = _make_finding("aaa", file="src/app.py")
        baseline_decisions = create_baseline_decisions([finding], tmp_path)
        assert baseline_decisions[0].file_hash is not None

        # Modify the file — hash changes
        test_file.write_text("modified content — security fix applied")

        new_findings, resolved = filter_findings([finding], baseline_decisions, tmp_path)
        assert len(new_findings) == 1
        assert resolved == 0


class TestBaselineCLI:
    def test_baseline_creates_decisions(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        findings = [_make_finding("aaa"), _make_finding("bbb", file="b.py")]
        _write_latest_findings(tmp_path, findings)

        result = CliRunner().invoke(main, ["baseline"])

        assert result.exit_code == 0, result.output
        assert "Baselined 2 findings from latest audit." in result.output

        decisions_path = tmp_path / ".noxaudit" / "decisions.jsonl"
        decisions = load_decisions(decisions_path)
        assert len(decisions) == 2
        assert all(d.reason == "baseline" for d in decisions)
        assert all(d.decision == DecisionType.DISMISSED for d in decisions)

    def test_baseline_with_focus_filter(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        findings = [
            _make_finding("aaa", focus="security"),
            _make_finding("bbb", file="b.py", focus="docs"),
        ]
        _write_latest_findings(tmp_path, findings, focus="security+docs")

        result = CliRunner().invoke(main, ["baseline", "--focus", "security"])

        assert result.exit_code == 0, result.output
        assert "Baselined 1 findings from latest audit." in result.output

        decisions = load_decisions(tmp_path / ".noxaudit" / "decisions.jsonl")
        assert len(decisions) == 1
        assert decisions[0].finding_id == "aaa"

    def test_baseline_with_severity_filter(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        findings = [
            _make_finding("aaa", severity=Severity.HIGH),
            _make_finding("bbb", file="b.py", severity=Severity.LOW),
        ]
        _write_latest_findings(tmp_path, findings)

        result = CliRunner().invoke(main, ["baseline", "--severity", "low"])

        assert result.exit_code == 0, result.output
        assert "Baselined 1 findings from latest audit." in result.output

        decisions = load_decisions(tmp_path / ".noxaudit" / "decisions.jsonl")
        assert len(decisions) == 1
        assert decisions[0].finding_id == "bbb"

    def test_baseline_with_multiple_severities(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        findings = [
            _make_finding("aaa", severity=Severity.HIGH),
            _make_finding("bbb", file="b.py", severity=Severity.MEDIUM),
            _make_finding("ccc", file="c.py", severity=Severity.LOW),
        ]
        _write_latest_findings(tmp_path, findings)

        result = CliRunner().invoke(main, ["baseline", "--severity", "low,medium"])

        assert result.exit_code == 0, result.output
        assert "Baselined 2 findings from latest audit." in result.output

    def test_baseline_undo_all(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        decisions_path = tmp_path / ".noxaudit" / "decisions.jsonl"
        decisions_path.parent.mkdir(parents=True, exist_ok=True)
        for fid in ["aaa", "bbb"]:
            save_decision(
                decisions_path,
                Decision(
                    finding_id=fid,
                    decision=DecisionType.DISMISSED,
                    reason="baseline",
                    date=date.today().isoformat(),
                    by="baseline",
                ),
            )

        result = CliRunner().invoke(main, ["baseline", "--undo"])

        assert result.exit_code == 0, result.output
        assert "Removed 2 baseline decisions." in result.output
        assert load_decisions(decisions_path) == []

    def test_baseline_undo_with_repo_label(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        decisions_path = tmp_path / ".noxaudit" / "decisions.jsonl"
        decisions_path.parent.mkdir(parents=True, exist_ok=True)
        save_decision(
            decisions_path,
            Decision(
                finding_id="aaa",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
            ),
        )

        # With --repo but no latest-findings.json for that repo: removes all baselines
        result = CliRunner().invoke(main, ["baseline", "--undo", "--repo", "my-app"])

        assert result.exit_code == 0, result.output
        assert "for my-app" in result.output

    def test_baseline_list_shows_count(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        decisions_path = tmp_path / ".noxaudit" / "decisions.jsonl"
        decisions_path.parent.mkdir(parents=True, exist_ok=True)
        save_decision(
            decisions_path,
            Decision(
                finding_id="aaa",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
            ),
        )

        result = CliRunner().invoke(main, ["baseline", "--list"])

        assert result.exit_code == 0, result.output
        assert "1 baselined finding" in result.output

    def test_baseline_list_no_baselines(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        result = CliRunner().invoke(main, ["baseline", "--list"])

        assert result.exit_code == 0, result.output
        assert "No baselined findings." in result.output

    def test_baseline_no_findings_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        result = CliRunner().invoke(main, ["baseline"])

        assert result.exit_code == 0, result.output
        assert "No findings to baseline" in result.output
        assert "noxaudit run" in result.output

    def test_baseline_no_findings_with_repo(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        result = CliRunner().invoke(main, ["baseline", "--repo", "my-app"])

        assert result.exit_code == 0, result.output
        assert "No findings to baseline for my-app" in result.output

    def test_baseline_undo_preserves_non_baseline_decisions(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        decisions_path = tmp_path / ".noxaudit" / "decisions.jsonl"
        decisions_path.parent.mkdir(parents=True, exist_ok=True)
        save_decision(
            decisions_path,
            Decision(
                finding_id="aaa",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
            ),
        )
        save_decision(
            decisions_path,
            Decision(
                finding_id="bbb",
                decision=DecisionType.INTENTIONAL,
                reason="by design",
                date=date.today().isoformat(),
                by="engineer",
            ),
        )

        result = CliRunner().invoke(main, ["baseline", "--undo"])

        assert result.exit_code == 0, result.output
        remaining = load_decisions(decisions_path)
        assert len(remaining) == 1
        assert remaining[0].finding_id == "bbb"
