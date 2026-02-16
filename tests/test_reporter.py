"""Tests for report generation and notification formatting."""

from __future__ import annotations

from noxaudit.models import AuditResult
from noxaudit.reporter import (
    _focus_display,
    format_notification,
    generate_report,
    save_report,
)


class TestFocusDisplay:
    def test_single(self):
        assert _focus_display("security") == "Security"

    def test_combined(self):
        assert _focus_display("security+performance") == "Security + Performance"

    def test_triple(self):
        assert _focus_display("security+docs+patterns") == "Security + Docs + Patterns"


class TestGenerateReport:
    def test_single_focus_title(self, sample_result):
        report = generate_report(sample_result)
        assert "# Nightwatch Report: Security" in report

    def test_combined_focus_title(self, combined_result):
        report = generate_report(combined_result)
        assert "Security + Docs" in report

    def test_includes_findings(self, sample_result):
        report = generate_report(sample_result)
        assert "SQL injection" in report
        assert "src/auth.py" in report

    def test_no_findings(self):
        result = AuditResult(
            repo="test",
            focus="security",
            provider="anthropic",
            timestamp="2026-02-14T10:00:00",
        )
        report = generate_report(result)
        assert "No new findings" in report

    def test_severity_sections(self, sample_result):
        report = generate_report(sample_result)
        assert "HIGH" in report
        assert "MEDIUM" in report
        assert "LOW" in report


class TestFormatNotification:
    def test_single_focus_icon(self, sample_result):
        msg = format_notification(sample_result)
        assert "🔒" in msg  # security icon
        assert "Security Audit" in msg

    def test_combined_focus_icon(self, combined_result):
        msg = format_notification(combined_result)
        assert "🔍" in msg  # generic icon for combined
        assert "Security + Docs" in msg

    def test_severity_counts(self, sample_result):
        msg = format_notification(sample_result)
        assert "🔴" in msg  # high
        assert "🟡" in msg  # medium
        assert "🔵" in msg  # low

    def test_resolved_count(self, sample_result):
        msg = format_notification(sample_result)
        assert "2 previous findings still resolved" in msg

    def test_no_findings_message(self):
        result = AuditResult(
            repo="test",
            focus="hygiene",
            provider="anthropic",
            timestamp="2026-02-14T10:00:00",
        )
        msg = format_notification(result)
        assert "No new findings" in msg


class TestSaveReport:
    def test_creates_file(self, tmp_path, sample_result):
        report = generate_report(sample_result)
        path = save_report(report, tmp_path / "reports", "my-app", "security")
        assert path.exists()
        assert "security" in path.name
        assert path.read_text() == report

    def test_combined_focus_in_filename(self, tmp_path, combined_result):
        report = generate_report(combined_result)
        path = save_report(report, tmp_path / "reports", "my-app", "security+docs")
        assert "security+docs" in path.name
