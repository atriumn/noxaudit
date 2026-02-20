"""CLI integration tests — end-to-end through the CLI entry point.

These tests verify that features are correctly wired into the CLI, not just
tested in isolation. Every significant new feature must have at least one
test in this module (or in a similarly structured integration test file).

See CONTRIBUTING.md for the policy.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from noxaudit.cli import main
from noxaudit.cost_ledger import CostLedger
from noxaudit.decisions import save_decision
from noxaudit.models import Decision, DecisionType, Finding, Severity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(tmp_path: Path, provider: str = "gemini") -> str:
    """Write a minimal noxaudit.yml and return its path."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "app.py").write_text("x = 1\n")

    config = {
        "repos": [{"name": "test-repo", "path": str(repo_path), "provider": provider}],
        "schedule": {"monday": "security"},
        "reports_dir": str(tmp_path / "reports"),
    }
    cfg_path = tmp_path / "noxaudit.yml"
    cfg_path.write_text(yaml.dump(config))
    return str(cfg_path)


def _make_mock_provider(findings=None):
    """Return (provider_class_mock, provider_instance_mock)."""
    if findings is None:
        findings = []
    instance = MagicMock()
    instance.run_audit.return_value = findings
    instance.get_last_usage.return_value = {
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
    }
    cls = MagicMock(return_value=instance)
    return cls, instance


# ---------------------------------------------------------------------------
# Issue #46: Pre-pass wired into CLI
# ---------------------------------------------------------------------------


@pytest.mark.cli_integration
class TestPrepassCLIIntegration:
    """Pre-pass classification is executed when triggered by config or provider economics."""

    def test_prepass_runs_when_enabled_via_config(self, tmp_path, sample_findings):
        """When prepass.enabled=True and tokens exceed threshold, pre-pass executes."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / "app.py").write_text("x = 1\n")

        # Write config with prepass explicitly enabled (low threshold so it triggers)
        config = {
            "repos": [{"name": "test-repo", "path": str(repo_path)}],
            "schedule": {"monday": "security"},
            "reports_dir": str(tmp_path / "reports"),
            "model": "claude-opus-4-6",
            "prepass": {"enabled": True, "threshold_tokens": 0},
        }
        cfg_path = tmp_path / "noxaudit.yml"
        cfg_path.write_text(yaml.dump(config))

        # Provider returns classification findings first (pre-pass), then audit findings
        prepass_findings = [
            Finding(
                id="x1",
                severity=Severity.LOW,
                file="app.py",
                line=None,
                title="audit-relevant",
                description="relevant to security",
                focus="security",
            )
        ]
        provider_cls, provider_instance = _make_mock_provider(sample_findings)
        # First call = prepass classification, second call = main audit
        provider_instance.run_audit.side_effect = [prepass_findings, sample_findings]

        runner = CliRunner()
        with (
            patch.dict(
                "noxaudit.runner.PROVIDERS", {"anthropic": provider_cls, "gemini": provider_cls}
            ),
            patch("noxaudit.runner.save_latest_findings"),
        ):
            result = runner.invoke(
                main,
                ["--config", str(cfg_path), "run", "--focus", "security"],
            )

        assert result.exit_code == 0, result.output
        # Pre-pass was triggered — run_audit called twice (pre-pass + main audit)
        assert provider_instance.run_audit.call_count == 2

    def test_prepass_filters_files_before_main_audit(self, tmp_path):
        """Pre-pass result is used to filter files — main audit gets fewer files."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / "app.py").write_text("x = 1\n")
        (repo_path / "unused.py").write_text("pass\n")

        config = {
            "repos": [{"name": "test-repo", "path": str(repo_path)}],
            "schedule": {"monday": "security"},
            "reports_dir": str(tmp_path / "reports"),
            "model": "claude-opus-4-6",
            "prepass": {"enabled": True, "threshold_tokens": 0},
        }
        cfg_path = tmp_path / "noxaudit.yml"
        cfg_path.write_text(yaml.dump(config))

        # Pre-pass returns only app.py as relevant
        prepass_findings = [
            Finding(
                id="x1",
                severity=Severity.LOW,
                file="app.py",
                line=None,
                title="audit-relevant",
                description="relevant",
            )
        ]
        main_findings: list[Finding] = []

        provider_cls, provider_instance = _make_mock_provider([])
        provider_instance.run_audit.side_effect = [prepass_findings, main_findings]

        runner = CliRunner()
        with (
            patch.dict(
                "noxaudit.runner.PROVIDERS", {"anthropic": provider_cls, "gemini": provider_cls}
            ),
            patch("noxaudit.runner.save_latest_findings"),
        ):
            result = runner.invoke(
                main,
                ["--config", str(cfg_path), "run", "--focus", "security"],
            )

        assert result.exit_code == 0, result.output
        # Main audit call should only receive app.py (unused.py filtered out)
        main_audit_call = provider_instance.run_audit.call_args_list[1]
        files_sent = main_audit_call[0][0]  # first positional arg = files
        file_paths = [f.path for f in files_sent]
        assert "app.py" in file_paths
        assert "unused.py" not in file_paths

    def test_prepass_not_triggered_for_gemini(self, tmp_path, sample_findings):
        """Gemini (flat pricing) does NOT auto-trigger pre-pass."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / "app.py").write_text("x = 1\n")

        config = {
            "repos": [{"name": "test-repo", "path": str(repo_path), "provider": "gemini"}],
            "schedule": {"monday": "security"},
            "reports_dir": str(tmp_path / "reports"),
            "model": "gemini-2.5-flash",
        }
        cfg_path = tmp_path / "noxaudit.yml"
        cfg_path.write_text(yaml.dump(config))

        provider_cls, provider_instance = _make_mock_provider(sample_findings)

        runner = CliRunner()
        with (
            patch.dict("noxaudit.runner.PROVIDERS", {"gemini": provider_cls}),
            patch("noxaudit.runner.save_latest_findings"),
        ):
            result = runner.invoke(
                main,
                ["--config", str(cfg_path), "run", "--focus", "security"],
            )

        assert result.exit_code == 0, result.output
        # No pre-pass triggered — run_audit called exactly once
        assert provider_instance.run_audit.call_count == 1


# ---------------------------------------------------------------------------
# Issue #47: Cost tracking wired into CLI
# ---------------------------------------------------------------------------


@pytest.mark.cli_integration
class TestCostTrackingCLIIntegration:
    """Cost tracking data is correctly displayed in noxaudit status."""

    def test_status_shows_no_history_when_ledger_empty(self, tmp_path):
        """status command shows 'No audit history yet' when ledger is empty."""
        cfg = _write_config(tmp_path)
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"

        with patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            result = CliRunner().invoke(main, ["--config", cfg, "status"])

        assert result.exit_code == 0, result.output
        assert "No audit history yet" in result.output

    def test_status_shows_spend_and_projections(self, tmp_path):
        """status command shows spend, avg, and projected monthly."""
        cfg = _write_config(tmp_path)
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"

        with patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            CostLedger.append_entry(
                repo="test-repo",
                focus="security",
                provider="gemini",
                model="gemini-2.0-flash",
                input_tokens=10_000,
                output_tokens=5_000,
                cache_read_tokens=0,
                cache_write_tokens=0,
                file_count=5,
            )
            result = CliRunner().invoke(main, ["--config", cfg, "status"])

        assert result.exit_code == 0, result.output
        assert "Estimated spend:" in result.output
        assert "Avg per audit:" in result.output
        assert "Projected monthly:" in result.output

    def test_status_shows_cache_tokens_when_present(self, tmp_path):
        """status command shows cache read/write tokens when non-zero."""
        cfg = _write_config(tmp_path)
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"

        with patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            CostLedger.append_entry(
                repo="test-repo",
                focus="security",
                provider="anthropic",
                model="claude-sonnet-4-5",
                input_tokens=10_000,
                output_tokens=5_000,
                cache_read_tokens=50_000,
                cache_write_tokens=10_000,
                file_count=5,
            )
            result = CliRunner().invoke(main, ["--config", cfg, "status"])

        assert result.exit_code == 0, result.output
        assert "Cache read tokens:" in result.output
        assert "Cache write tokens:" in result.output
        assert "Cache savings:" in result.output

    def test_status_projected_monthly_uses_actual_days(self, tmp_path):
        """Projected monthly is scaled by actual days with data, not hardcoded 30."""
        cfg = _write_config(tmp_path)
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        now = datetime.now()

        with patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            # Two entries: today and 9 days ago → 9 days span
            CostLedger.append_entry(
                repo="test-repo",
                focus="security",
                provider="gemini",
                model="gemini-2.0-flash",
                input_tokens=1_000_000,
                output_tokens=100_000,
                cache_read_tokens=0,
                cache_write_tokens=0,
                file_count=10,
                timestamp=(now - timedelta(days=9)).isoformat(),
            )
            CostLedger.append_entry(
                repo="test-repo",
                focus="security",
                provider="gemini",
                model="gemini-2.0-flash",
                input_tokens=1_000_000,
                output_tokens=100_000,
                cache_read_tokens=0,
                cache_write_tokens=0,
                file_count=10,
                timestamp=now.isoformat(),
            )
            entries = CostLedger.get_last_n_days(30)
            total_cost = sum(e.get("cost_estimate_usd", 0) for e in entries)

            result = CliRunner().invoke(main, ["--config", cfg, "status"])

        assert result.exit_code == 0, result.output
        assert "Projected monthly:" in result.output
        # Extract projected value from output
        for line in result.output.splitlines():
            if "Projected monthly:" in line:
                # Should be significantly higher than total (9-day data projected to 30 days)
                assert f"${total_cost:.2f}" not in line, (
                    "Projected monthly must differ from total when data spans < 30 days"
                )
                break

    def test_status_reprices_cache_costs_for_anthropic(self, tmp_path):
        """status command reprices costs including cache tokens for Anthropic entries."""
        cfg = _write_config(tmp_path)
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"

        with patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            # An entry with cache write tokens — cost must include cache write charges
            CostLedger.append_entry(
                repo="test-repo",
                focus="security",
                provider="anthropic",
                model="claude-sonnet-4-5",
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_write_tokens=1_000_000,
                file_count=5,
            )
            result = CliRunner().invoke(main, ["--config", cfg, "status"])

        assert result.exit_code == 0, result.output
        # 1M cache write * $3.75/M * 50% batch discount = $1.875, rounds to $1.88
        assert "$0.00" not in result.output or "Estimated spend:     $0.00" not in result.output
        assert "Estimated spend:" in result.output
        # The cost should be non-zero (cache writes have a real cost)
        for line in result.output.splitlines():
            if "Estimated spend:" in line:
                assert "$0.00" not in line, "Cache write tokens must be included in cost"
                break


# ---------------------------------------------------------------------------
# Issue #48: Baseline --undo with filters wired into CLI
# ---------------------------------------------------------------------------


@pytest.mark.cli_integration
class TestBaselineUndoFiltersCLIIntegration:
    """baseline --undo with filters uses stored decisions, not latest-findings.json."""

    def test_undo_with_focus_filter_uses_stored_decisions(self, tmp_path, monkeypatch):
        """--undo --focus filters baseline decisions by stored focus field."""
        monkeypatch.chdir(tmp_path)
        decisions_path = tmp_path / ".noxaudit" / "decisions.jsonl"
        decisions_path.parent.mkdir(parents=True, exist_ok=True)

        # Create baseline decisions WITH focus stored (new format)
        from datetime import date

        save_decision(
            decisions_path,
            Decision(
                finding_id="aaa",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
                focus="security",
                severity="high",
                repo=None,
            ),
        )
        save_decision(
            decisions_path,
            Decision(
                finding_id="bbb",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
                focus="docs",
                severity="low",
                repo=None,
            ),
        )

        result = CliRunner().invoke(main, ["baseline", "--undo", "--focus", "security"])

        assert result.exit_code == 0, result.output
        assert "Removed 1 baseline decisions" in result.output

        # Only "docs" baseline should remain
        from noxaudit.decisions import load_decisions

        remaining = load_decisions(decisions_path)
        assert len(remaining) == 1
        assert remaining[0].finding_id == "bbb"

    def test_undo_with_severity_filter_uses_stored_decisions(self, tmp_path, monkeypatch):
        """--undo --severity filters baseline decisions by stored severity field."""
        monkeypatch.chdir(tmp_path)
        decisions_path = tmp_path / ".noxaudit" / "decisions.jsonl"
        decisions_path.parent.mkdir(parents=True, exist_ok=True)

        from datetime import date

        save_decision(
            decisions_path,
            Decision(
                finding_id="aaa",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
                focus="security",
                severity="high",
                repo=None,
            ),
        )
        save_decision(
            decisions_path,
            Decision(
                finding_id="bbb",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
                focus="security",
                severity="low",
                repo=None,
            ),
        )

        result = CliRunner().invoke(main, ["baseline", "--undo", "--severity", "high"])

        assert result.exit_code == 0, result.output
        assert "Removed 1 baseline decisions" in result.output

        from noxaudit.decisions import load_decisions

        remaining = load_decisions(decisions_path)
        assert len(remaining) == 1
        assert remaining[0].finding_id == "bbb"

    def test_undo_with_repo_filter_uses_stored_decisions(self, tmp_path, monkeypatch):
        """--undo --repo filters baseline decisions by stored repo field."""
        monkeypatch.chdir(tmp_path)
        decisions_path = tmp_path / ".noxaudit" / "decisions.jsonl"
        decisions_path.parent.mkdir(parents=True, exist_ok=True)

        from datetime import date

        save_decision(
            decisions_path,
            Decision(
                finding_id="aaa",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
                focus="security",
                severity="high",
                repo="my-app",
            ),
        )
        save_decision(
            decisions_path,
            Decision(
                finding_id="bbb",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
                focus="security",
                severity="high",
                repo="other-app",
            ),
        )

        result = CliRunner().invoke(main, ["baseline", "--undo", "--repo", "my-app"])

        assert result.exit_code == 0, result.output
        assert "Removed 1 baseline decisions" in result.output

        from noxaudit.decisions import load_decisions

        remaining = load_decisions(decisions_path)
        assert len(remaining) == 1
        assert remaining[0].finding_id == "bbb"

    def test_undo_filters_work_without_latest_findings_json(self, tmp_path, monkeypatch):
        """--undo --focus works even when latest-findings.json does not exist."""
        monkeypatch.chdir(tmp_path)
        decisions_path = tmp_path / ".noxaudit" / "decisions.jsonl"
        decisions_path.parent.mkdir(parents=True, exist_ok=True)

        from datetime import date

        save_decision(
            decisions_path,
            Decision(
                finding_id="aaa",
                decision=DecisionType.DISMISSED,
                reason="baseline",
                date=date.today().isoformat(),
                by="baseline",
                focus="security",
                severity="high",
                repo=None,
            ),
        )

        # No latest-findings.json exists — old code would return 0 removals
        assert not (tmp_path / ".noxaudit" / "latest-findings.json").exists()

        result = CliRunner().invoke(main, ["baseline", "--undo", "--focus", "security"])

        assert result.exit_code == 0, result.output
        # Fixed code filters from stored decisions — finds and removes the security baseline
        assert "Removed 1 baseline decisions" in result.output

    def test_baseline_create_stores_focus_severity_repo(self, tmp_path, monkeypatch):
        """baseline command stores focus/severity/repo in decisions for later filtering."""
        monkeypatch.chdir(tmp_path)

        # Write latest-findings.json with a finding
        noxaudit_dir = tmp_path / ".noxaudit"
        noxaudit_dir.mkdir(exist_ok=True)
        import json

        data = {
            "repo": "my-app",
            "focus": "security",
            "timestamp": "2026-02-19T10:00:00",
            "resolved_count": 0,
            "findings": [
                {
                    "id": "abc123",
                    "severity": "high",
                    "file": "app.py",
                    "line": 1,
                    "title": "Test finding",
                    "description": "Test desc",
                    "focus": "security",
                }
            ],
        }
        (noxaudit_dir / "latest-findings.json").write_text(json.dumps(data))

        result = CliRunner().invoke(main, ["baseline"])

        assert result.exit_code == 0, result.output
        assert "Baselined 1" in result.output

        from noxaudit.decisions import load_decisions

        decisions = load_decisions(tmp_path / ".noxaudit" / "decisions.jsonl")
        assert len(decisions) == 1
        d = decisions[0]
        assert d.focus == "security"
        assert d.severity == "high"
