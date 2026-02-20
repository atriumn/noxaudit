"""Integration tests for SARIF output — end-to-end from runner and CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from noxaudit.cli import main
from noxaudit.config import NoxauditConfig, RepoConfig
from noxaudit.runner import retrieve_audit, run_audit


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_config(tmp_path, provider="anthropic"):
    """Return a NoxauditConfig pointing at tmp_path for both repo and reports."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "app.py").write_text("x = 1\n")

    return NoxauditConfig(
        repos=[RepoConfig(name="test-repo", path=str(repo_path), provider_rotation=[provider])],
        reports_dir=str(tmp_path / "reports"),
        schedule={"monday": "security"},
    )


def _make_mock_provider(findings):
    """Return a (provider_class_mock, provider_instance_mock) pair."""
    instance = MagicMock()
    instance.run_audit.return_value = findings
    instance.get_last_usage.return_value = {"input_tokens": 100, "output_tokens": 50}
    cls = MagicMock(return_value=instance)
    return cls, instance


def _sarif_files(reports_dir):
    return list(Path(reports_dir).rglob("*.sarif"))


def _markdown_files(reports_dir):
    return list(Path(reports_dir).rglob("*.md"))


# ---------------------------------------------------------------------------
# Runner integration: run_audit with format="sarif"
# ---------------------------------------------------------------------------


class TestRunAuditSarifOutput:
    def test_sarif_file_created_when_format_sarif(self, tmp_path, sample_findings):
        """run_audit with output_format='sarif' saves a .sarif file."""
        config = _make_config(tmp_path)
        provider_cls, _ = _make_mock_provider(sample_findings)

        with (
            patch.dict("noxaudit.runner.PROVIDERS", {"anthropic": provider_cls}),
            patch("noxaudit.runner.save_latest_findings"),
        ):
            results = run_audit(config, focus_name="security", output_format="sarif")

        assert results
        sarif_files = _sarif_files(config.reports_dir)
        assert len(sarif_files) == 1, f"Expected 1 .sarif file, found: {sarif_files}"
        assert sarif_files[0].suffix == ".sarif"

    def test_markdown_also_saved_when_format_sarif(self, tmp_path, sample_findings):
        """run_audit with format='sarif' ALSO saves the markdown report."""
        config = _make_config(tmp_path)
        provider_cls, _ = _make_mock_provider(sample_findings)

        with (
            patch.dict("noxaudit.runner.PROVIDERS", {"anthropic": provider_cls}),
            patch("noxaudit.runner.save_latest_findings"),
        ):
            run_audit(config, focus_name="security", output_format="sarif")

        md_files = _markdown_files(config.reports_dir)
        assert len(md_files) == 1, "Markdown report should still be saved"

    def test_no_sarif_file_without_format_sarif(self, tmp_path, sample_findings):
        """run_audit with default format does NOT produce a .sarif file."""
        config = _make_config(tmp_path)
        provider_cls, _ = _make_mock_provider(sample_findings)

        with (
            patch.dict("noxaudit.runner.PROVIDERS", {"anthropic": provider_cls}),
            patch("noxaudit.runner.save_latest_findings"),
        ):
            run_audit(config, focus_name="security")  # default format="markdown"

        sarif_files = _sarif_files(config.reports_dir)
        assert sarif_files == [], f"No .sarif file should be created: {sarif_files}"

    def test_sarif_contents_are_valid_json(self, tmp_path, sample_findings):
        """SARIF file contains valid JSON."""
        config = _make_config(tmp_path)
        provider_cls, _ = _make_mock_provider(sample_findings)

        with (
            patch.dict("noxaudit.runner.PROVIDERS", {"anthropic": provider_cls}),
            patch("noxaudit.runner.save_latest_findings"),
        ):
            run_audit(config, focus_name="security", output_format="sarif")

        sarif_file = _sarif_files(config.reports_dir)[0]
        data = json.loads(sarif_file.read_text())
        assert data["version"] == "2.1.0"
        assert "runs" in data
        assert len(data["runs"]) == 1

    def test_sarif_contains_all_findings(self, tmp_path, sample_findings):
        """SARIF file contains all findings from the audit."""
        config = _make_config(tmp_path)
        provider_cls, _ = _make_mock_provider(sample_findings)

        with (
            patch.dict("noxaudit.runner.PROVIDERS", {"anthropic": provider_cls}),
            patch("noxaudit.runner.save_latest_findings"),
        ):
            run_audit(config, focus_name="security", output_format="sarif")

        sarif_file = _sarif_files(config.reports_dir)[0]
        data = json.loads(sarif_file.read_text())
        results = data["runs"][0]["results"]
        assert len(results) == len(sample_findings)


# ---------------------------------------------------------------------------
# Runner integration: retrieve_audit with format="sarif"
# ---------------------------------------------------------------------------


class TestRetrieveAuditSarifOutput:
    def _make_pending_file(self, tmp_path, provider="anthropic"):
        """Write a fake pending-batch.json and return its path."""
        pending = {
            "submitted_at": "2026-02-20T10:00:00",
            "focus": "security",
            "focus_names": ["security"],
            "batches": [
                {
                    "repo": "test-repo",
                    "batch_id": "batch_abc123",
                    "provider": provider,
                    "file_count": 1,
                }
            ],
        }
        p = tmp_path / "pending-batch.json"
        p.write_text(json.dumps(pending))
        return str(p)

    def _make_retrieve_provider(self, findings):
        """Mock provider for retrieve_batch."""
        instance = MagicMock()
        instance.retrieve_batch.return_value = {
            "status": "ended",
            "findings": findings,
            "request_counts": {"processing": 0},
        }
        instance.get_last_usage.return_value = {"input_tokens": 200, "output_tokens": 80}
        cls = MagicMock(return_value=instance)
        return cls

    def test_sarif_file_created_when_format_sarif(self, tmp_path, sample_findings):
        """retrieve_audit with format='sarif' saves a .sarif file."""
        config = _make_config(tmp_path)
        pending_path = self._make_pending_file(tmp_path)
        provider_cls = self._make_retrieve_provider(sample_findings)

        with (
            patch.dict("noxaudit.runner.PROVIDERS", {"anthropic": provider_cls}),
            patch("noxaudit.runner.save_latest_findings"),
            patch("noxaudit.runner._mark_retrieved"),
        ):
            results = retrieve_audit(config, pending_path=pending_path, output_format="sarif")

        assert results
        sarif_files = _sarif_files(config.reports_dir)
        assert len(sarif_files) == 1
        assert sarif_files[0].suffix == ".sarif"

    def test_no_sarif_without_format_sarif(self, tmp_path, sample_findings):
        """retrieve_audit with default format does NOT produce a .sarif file."""
        config = _make_config(tmp_path)
        pending_path = self._make_pending_file(tmp_path)
        provider_cls = self._make_retrieve_provider(sample_findings)

        with (
            patch.dict("noxaudit.runner.PROVIDERS", {"anthropic": provider_cls}),
            patch("noxaudit.runner.save_latest_findings"),
            patch("noxaudit.runner._mark_retrieved"),
        ):
            retrieve_audit(config, pending_path=pending_path)  # default format

        sarif_files = _sarif_files(config.reports_dir)
        assert sarif_files == []

    def test_sarif_contents_valid(self, tmp_path, sample_findings):
        """retrieve_audit SARIF file has valid SARIF 2.1.0 structure."""
        config = _make_config(tmp_path)
        pending_path = self._make_pending_file(tmp_path)
        provider_cls = self._make_retrieve_provider(sample_findings)

        with (
            patch.dict("noxaudit.runner.PROVIDERS", {"anthropic": provider_cls}),
            patch("noxaudit.runner.save_latest_findings"),
            patch("noxaudit.runner._mark_retrieved"),
        ):
            retrieve_audit(config, pending_path=pending_path, output_format="sarif")

        sarif_file = _sarif_files(config.reports_dir)[0]
        data = json.loads(sarif_file.read_text())
        assert data["version"] == "2.1.0"
        assert len(data["runs"][0]["results"]) == len(sample_findings)


# ---------------------------------------------------------------------------
# CLI tests: --format sarif option
# ---------------------------------------------------------------------------


def _write_cli_config(tmp_path):
    """Write a minimal noxaudit.yml and return its path."""
    import yaml

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "app.py").write_text("x = 1\n")

    config = {
        "repos": [{"name": "test-repo", "path": str(repo_path)}],
        "schedule": {"monday": "security"},
        "reports_dir": str(tmp_path / "reports"),
    }
    cfg_path = tmp_path / "noxaudit.yml"
    cfg_path.write_text(yaml.dump(config))
    return str(cfg_path)


class TestCliFormatOption:
    def test_run_format_sarif_accepted(self, tmp_path):
        """`noxaudit run --format sarif --dry-run` is accepted without error."""
        cfg = _write_cli_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--config", cfg, "run", "--focus", "security", "--format", "sarif", "--dry-run"],
        )
        assert result.exit_code == 0, result.output

    def test_run_format_markdown_accepted(self, tmp_path):
        """`noxaudit run --format markdown --dry-run` is accepted without error."""
        cfg = _write_cli_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--config", cfg, "run", "--focus", "security", "--format", "markdown", "--dry-run"],
        )
        assert result.exit_code == 0

    def test_run_invalid_format_rejected(self, tmp_path):
        """`noxaudit run --format json` is rejected (invalid choice)."""
        cfg = _write_cli_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--config", cfg, "run", "--focus", "security", "--format", "json", "--dry-run"],
        )
        assert result.exit_code != 0

    def test_run_format_sarif_produces_sarif_file(self, tmp_path, sample_findings):
        """`noxaudit run --format sarif` produces a .sarif file (mocked provider)."""
        cfg = _write_cli_config(tmp_path)
        provider_cls, _ = _make_mock_provider(sample_findings)

        runner = CliRunner()
        with (
            patch.dict("noxaudit.runner.PROVIDERS", {"gemini": provider_cls}),
            patch("noxaudit.runner.save_latest_findings"),
        ):
            result = runner.invoke(
                main,
                ["--config", cfg, "run", "--focus", "security", "--format", "sarif"],
            )

        assert result.exit_code == 0, result.output
        reports_dir = tmp_path / "reports"
        sarif_files = list(reports_dir.rglob("*.sarif"))
        assert len(sarif_files) == 1, f"Expected 1 SARIF file: {sarif_files}"

    def test_run_without_format_no_sarif(self, tmp_path, sample_findings):
        """`noxaudit run` without --format does NOT produce a .sarif file."""
        cfg = _write_cli_config(tmp_path)
        provider_cls, _ = _make_mock_provider(sample_findings)

        runner = CliRunner()
        with (
            patch.dict("noxaudit.runner.PROVIDERS", {"gemini": provider_cls}),
            patch("noxaudit.runner.save_latest_findings"),
        ):
            result = runner.invoke(
                main,
                ["--config", cfg, "run", "--focus", "security"],
            )

        assert result.exit_code == 0, result.output
        reports_dir = tmp_path / "reports"
        sarif_files = list(reports_dir.rglob("*.sarif")) if reports_dir.exists() else []
        assert sarif_files == []

    def test_retrieve_format_sarif_accepted(self, tmp_path):
        """`noxaudit retrieve --format sarif` option is accepted."""
        cfg = _write_cli_config(tmp_path)
        runner = CliRunner()
        # No pending file exists — should print a message and exit 0
        result = runner.invoke(
            main,
            ["--config", cfg, "retrieve", "--format", "sarif"],
        )
        # No pending batch — prints a message but shouldn't error on the option
        assert result.exit_code == 0
        assert "sarif" not in result.output.lower() or "No results" in result.output


# ---------------------------------------------------------------------------
# Schema validation: SARIF output passes jsonschema against SARIF 2.1.0 schema
# ---------------------------------------------------------------------------

SARIF_MINIMAL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["version", "runs"],
    "properties": {
        "version": {"type": "string", "enum": ["2.1.0"]},
        "$schema": {"type": "string"},
        "runs": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["tool", "results"],
                "properties": {
                    "tool": {
                        "type": "object",
                        "required": ["driver"],
                        "properties": {
                            "driver": {
                                "type": "object",
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "rules": {"type": "array"},
                                },
                            }
                        },
                    },
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["ruleId", "message", "locations"],
                            "properties": {
                                "ruleId": {"type": "string"},
                                "level": {
                                    "type": "string",
                                    "enum": ["error", "warning", "note", "none"],
                                },
                                "message": {
                                    "type": "object",
                                    "required": ["text"],
                                    "properties": {"text": {"type": "string"}},
                                },
                                "locations": {"type": "array", "minItems": 1},
                            },
                        },
                    },
                },
            },
        },
    },
}


class TestSarifSchemaValidation:
    def test_empty_findings_pass_schema(self):
        """SARIF with no findings passes schema validation."""
        jsonschema = pytest.importorskip("jsonschema")
        from noxaudit.sarif import findings_to_sarif

        sarif = findings_to_sarif([], "security", "my-app")
        jsonschema.validate(sarif, SARIF_MINIMAL_SCHEMA)  # raises on failure

    def test_sample_findings_pass_schema(self, sample_findings):
        """SARIF with sample findings passes schema validation."""
        jsonschema = pytest.importorskip("jsonschema")
        from noxaudit.sarif import findings_to_sarif

        sarif = findings_to_sarif(sample_findings, "security", "my-app")
        jsonschema.validate(sarif, SARIF_MINIMAL_SCHEMA)

    def test_runner_sarif_output_passes_schema(self, tmp_path, sample_findings):
        """SARIF file saved by runner passes schema validation."""
        jsonschema = pytest.importorskip("jsonschema")
        config = _make_config(tmp_path)
        provider_cls, _ = _make_mock_provider(sample_findings)

        with (
            patch.dict("noxaudit.runner.PROVIDERS", {"anthropic": provider_cls}),
            patch("noxaudit.runner.save_latest_findings"),
        ):
            run_audit(config, focus_name="security", output_format="sarif")

        sarif_file = _sarif_files(config.reports_dir)[0]
        data = json.loads(sarif_file.read_text())
        jsonschema.validate(data, SARIF_MINIMAL_SCHEMA)
