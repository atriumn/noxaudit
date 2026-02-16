"""Tests for the CLI (via Click test runner, no API calls)."""

from __future__ import annotations


from click.testing import CliRunner

from noxaudit.cli import main


def _write_config(tmp_path, schedule=None):
    """Write a minimal config pointing at tmp_path as the repo."""
    schedule = schedule or {"monday": "security", "sunday": "off"}
    import yaml

    config = {
        "repos": [{"name": "test-repo", "path": str(tmp_path)}],
        "schedule": schedule,
    }
    cfg_path = tmp_path / "noxaudit.yml"
    cfg_path.write_text(yaml.dump(config))
    return str(cfg_path)


class TestScheduleCommand:
    def test_displays_single_focus(self, tmp_path):
        cfg = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "schedule"])
        assert result.exit_code == 0
        assert "security" in result.output
        assert "off" in result.output

    def test_displays_list_focus(self, tmp_path):
        cfg = _write_config(
            tmp_path,
            schedule={
                "monday": ["security", "dependencies"],
                "wednesday": ["patterns", "docs"],
                "sunday": "off",
            },
        )
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "schedule"])
        assert result.exit_code == 0
        assert "security, dependencies" in result.output
        assert "patterns, docs" in result.output


class TestStatusCommand:
    def test_shows_focus_areas(self, tmp_path):
        cfg = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "status"])
        assert result.exit_code == 0
        assert "Focus areas:" in result.output
        assert "test-repo" in result.output


class TestRunDryRun:
    def test_single_focus(self, tmp_path):
        (tmp_path / "app.py").write_text("x = 1")
        cfg = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "run", "--focus", "security", "--dry-run"])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "1 focus area" in result.output

    def test_combined_focus(self, tmp_path):
        (tmp_path / "app.py").write_text("x = 1")
        cfg = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["--config", cfg, "run", "--focus", "security,docs", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "2 focus area" in result.output
        assert "security+docs" in result.output

    def test_all_focus(self, tmp_path):
        (tmp_path / "app.py").write_text("x = 1")
        cfg = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "run", "--focus", "all", "--dry-run"])
        assert result.exit_code == 0
        assert "7 focus area" in result.output

    def test_unknown_focus_errors(self, tmp_path):
        cfg = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "run", "--focus", "bogus", "--dry-run"])
        assert result.exit_code != 0

    def test_off_focus(self, tmp_path):
        cfg = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "run", "--focus", "off", "--dry-run"])
        assert result.exit_code == 0
        assert "off" in result.output.lower()


class TestSubmitDryRun:
    def test_single_focus(self, tmp_path):
        (tmp_path / "app.py").write_text("x = 1")
        cfg = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["--config", cfg, "submit", "--focus", "security", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
