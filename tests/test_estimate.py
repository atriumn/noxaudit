"""Tests for noxaudit/pricing.py and the estimate CLI command."""

from __future__ import annotations

import yaml
from click.testing import CliRunner

from noxaudit.cli import main
from noxaudit.config import DEFAULT_SCHEDULE
from noxaudit.models import FileContent
from noxaudit.pricing import (
    MODEL_PRICING,
    count_weekly_runs,
    estimate_cost,
    estimate_output_tokens,
    estimate_prepass_reduction,
    get_frame_label,
)


# ---------------------------------------------------------------------------
# estimate_cost
# ---------------------------------------------------------------------------


class TestEstimateCost:
    def test_zero_tokens(self):
        pricing = MODEL_PRICING["gemini-2.0-flash"]
        assert estimate_cost(0, 0, pricing, use_batch=False) == 0.0

    def test_flat_pricing(self):
        pricing = MODEL_PRICING["gemini-2.0-flash"]  # $0.10/M input, $0.40/M output
        cost = estimate_cost(1_000_000, 100_000, pricing, use_batch=False)
        expected = 0.10 + 0.04  # $0.10 * (1M/1M) + $0.40 * (100K/1M)
        assert abs(cost - expected) < 0.001

    def test_below_tier_threshold_no_batch(self):
        pricing = MODEL_PRICING["claude-opus-4-6"]  # threshold 200K
        cost = estimate_cost(100_000, 1_000, pricing, use_batch=False)
        expected = (100_000 / 1_000_000) * 5.0 + (1_000 / 1_000_000) * 25.0
        assert abs(cost - expected) < 0.001

    def test_tiered_pricing(self):
        pricing = MODEL_PRICING["claude-opus-4-6"]
        # 300K input: 200K at $5/M + 100K at $10/M; output at high tier $37.50/M; 50% batch
        input_cost = (200_000 / 1_000_000) * 5.0 + (100_000 / 1_000_000) * 10.0
        output_cost = (10_000 / 1_000_000) * 37.50
        expected = (input_cost + output_cost) * 0.5
        cost = estimate_cost(300_000, 10_000, pricing, use_batch=True)
        assert abs(cost - expected) < 0.001

    def test_batch_discount_halves_cost(self):
        pricing = MODEL_PRICING["claude-opus-4-6"]
        cost_batch = estimate_cost(100_000, 1_000, pricing, use_batch=True)
        cost_no_batch = estimate_cost(100_000, 1_000, pricing, use_batch=False)
        assert abs(cost_no_batch - cost_batch * 2) < 0.0001

    def test_no_batch_discount_for_gemini(self):
        """Gemini has batch_discount=0 so use_batch flag has no effect."""
        pricing = MODEL_PRICING["gemini-2.5-flash"]
        cost_batch = estimate_cost(100_000, 10_000, pricing, use_batch=True)
        cost_no_batch = estimate_cost(100_000, 10_000, pricing, use_batch=False)
        assert cost_batch == cost_no_batch

    def test_exactly_at_tier_threshold_no_tiered(self):
        pricing = MODEL_PRICING["claude-sonnet-4-5"]  # threshold 200K
        cost = estimate_cost(200_000, 1_000, pricing, use_batch=False)
        # Exactly at threshold → standard rate
        expected = (200_000 / 1_000_000) * 3.0 + (1_000 / 1_000_000) * 15.0
        assert abs(cost - expected) < 0.001


# ---------------------------------------------------------------------------
# estimate_output_tokens
# ---------------------------------------------------------------------------


class TestEstimateOutputTokens:
    def test_small_repo_uncapped(self):
        tokens = estimate_output_tokens(10_000, 1)
        assert tokens == 1_000  # 10% of 10K

    def test_large_repo_capped_at_16384(self):
        tokens = estimate_output_tokens(500_000, 1)
        assert tokens == 16_384

    def test_scales_linearly_with_focus_areas(self):
        tokens_1 = estimate_output_tokens(10_000, 1)
        tokens_3 = estimate_output_tokens(10_000, 3)
        assert tokens_3 == tokens_1 * 3

    def test_cap_applies_per_focus_area(self):
        tokens = estimate_output_tokens(500_000, 4)
        assert tokens == 16_384 * 4


# ---------------------------------------------------------------------------
# estimate_prepass_reduction
# ---------------------------------------------------------------------------


def _make_files(sizes_chars: list[int]) -> list[FileContent]:
    return [
        FileContent(path=f"file{i}.py", content="x" * size) for i, size in enumerate(sizes_chars)
    ]


class TestEstimatePrepassReduction:
    def test_empty_files(self):
        result = estimate_prepass_reduction([], 0)
        assert result == {
            "reduced_tokens": 0,
            "triage_cost": 0.0,
            "high": 0,
            "medium": 0,
            "low_skip": 0,
        }

    def test_file_distribution_100_files(self):
        files = _make_files([100] * 100)
        result = estimate_prepass_reduction(files, 10_000)
        assert result["high"] == 15
        assert result["medium"] == 30
        assert result["low_skip"] == 55
        assert result["high"] + result["medium"] + result["low_skip"] == 100

    def test_token_reduction_smaller_than_total(self):
        # Small files first (high/medium priority), large files last (low/skip)
        files = _make_files([400] * 10 + [40_000] * 10)  # 20 files
        total_tokens = sum(len(f.content) // 4 for f in files)
        result = estimate_prepass_reduction(files, total_tokens)
        assert result["reduced_tokens"] < total_tokens

    def test_triage_cost_positive(self):
        files = _make_files([1_000] * 10)
        result = estimate_prepass_reduction(files, 10_000)
        assert result["triage_cost"] > 0.0

    def test_triage_cost_scales_with_file_count(self):
        files_10 = _make_files([1_000] * 10)
        files_20 = _make_files([1_000] * 20)
        r10 = estimate_prepass_reduction(files_10, 10_000)
        r20 = estimate_prepass_reduction(files_20, 10_000)
        # More files → higher triage output tokens → higher cost
        assert r20["triage_cost"] > r10["triage_cost"]


# ---------------------------------------------------------------------------
# get_frame_label
# ---------------------------------------------------------------------------


class TestGetFrameLabel:
    def test_single_focus_security(self):
        assert get_frame_label(["security"]) == "Does it work?"

    def test_single_focus_patterns(self):
        assert get_frame_label(["patterns"]) == "Does it last?"

    def test_same_frame(self):
        assert get_frame_label(["security", "testing"]) == "Does it work?"

    def test_all_does_it_last(self):
        assert get_frame_label(["patterns", "hygiene", "docs", "dependencies"]) == "Does it last?"

    def test_mixed_frames_returns_none(self):
        assert get_frame_label(["security", "patterns"]) is None

    def test_empty_returns_none(self):
        assert get_frame_label([]) is None


# ---------------------------------------------------------------------------
# count_weekly_runs
# ---------------------------------------------------------------------------


class TestCountWeeklyRuns:
    def test_default_schedule(self):
        # monday–saturday active, sunday off → 6
        assert count_weekly_runs(DEFAULT_SCHEDULE) == 6

    def test_all_off(self):
        schedule = {
            d: "off"
            for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
        assert count_weekly_runs(schedule) == 0

    def test_two_active_days(self):
        schedule = {
            "monday": "security",
            "tuesday": "off",
            "wednesday": "patterns",
            "thursday": "off",
            "friday": "off",
            "saturday": "off",
            "sunday": "off",
        }
        assert count_weekly_runs(schedule) == 2


# ---------------------------------------------------------------------------
# CLI estimate command
# ---------------------------------------------------------------------------


def _write_config(tmp_path, schedule=None, model="gemini-2.0-flash", provider="gemini"):
    schedule = schedule or {"monday": "security", "sunday": "off"}
    config = {
        "repos": [{"name": "test-repo", "path": str(tmp_path), "provider_rotation": [provider]}],
        "schedule": schedule,
        "model": model,
    }
    cfg_path = tmp_path / "noxaudit.yml"
    cfg_path.write_text(yaml.dump(config))
    return str(cfg_path)


class TestEstimateCLI:
    def test_basic_output_gemini(self, tmp_path):
        (tmp_path / "app.py").write_text("x = 1\n" * 100)
        cfg = _write_config(tmp_path, model="gemini-2.0-flash", provider="gemini")
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "estimate", "--focus", "security"])
        assert result.exit_code == 0, result.output
        assert "Cost estimate" in result.output
        assert "test-repo" in result.output
        assert "gemini" in result.output

    def test_shows_files_and_tokens(self, tmp_path):
        (tmp_path / "app.py").write_text("x = 1\n" * 200)
        cfg = _write_config(tmp_path, model="gemini-2.0-flash", provider="gemini")
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "estimate", "--focus", "security"])
        assert result.exit_code == 0, result.output
        assert "files" in result.output
        assert "tokens" in result.output

    def test_shows_alternatives_for_expensive_provider(self, tmp_path):
        (tmp_path / "app.py").write_text("x = 1\n" * 1_000)
        cfg = _write_config(tmp_path, model="claude-opus-4-6", provider="anthropic")
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "estimate", "--focus", "security"])
        assert result.exit_code == 0, result.output
        assert "Alternatives" in result.output

    def test_no_files_graceful(self, tmp_path):
        """Empty repo directory (no matching files) should print 'No files found'."""
        repo_dir = tmp_path / "myrepo"
        repo_dir.mkdir()
        # Write only a file that security focus won't match (e.g. .png)
        (repo_dir / "image.png").write_bytes(b"\x89PNG")
        cfg_path = tmp_path / "noxaudit.yml"
        import yaml

        cfg_path.write_text(
            yaml.dump(
                {
                    "repos": [
                        {
                            "name": "test-repo",
                            "path": str(repo_dir),
                            "provider_rotation": ["gemini"],
                        }
                    ],
                    "schedule": {"monday": "security"},
                    "model": "gemini-2.0-flash",
                }
            )
        )
        runner = CliRunner()
        result = runner.invoke(main, ["--config", str(cfg_path), "estimate", "--focus", "security"])
        assert result.exit_code == 0, result.output
        assert "No files found" in result.output

    def test_no_api_keys_needed(self, tmp_path, monkeypatch):
        """Estimate should work even with no API key env vars set."""
        (tmp_path / "app.py").write_text("x = 1\n" * 100)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        cfg = _write_config(tmp_path, model="gemini-2.0-flash", provider="gemini")
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "estimate", "--focus", "security"])
        assert result.exit_code == 0, result.output
        assert "Cost estimate" in result.output

    def test_monthly_projection_shown(self, tmp_path):
        (tmp_path / "app.py").write_text("x = 1\n" * 100)
        cfg = _write_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "estimate", "--focus", "security"])
        assert result.exit_code == 0, result.output
        assert "Monthly" in result.output

    def test_no_repos_configured(self, tmp_path):
        cfg_path = tmp_path / "noxaudit.yml"
        cfg_path.write_text(yaml.dump({"schedule": {"monday": "security"}}))
        runner = CliRunner()
        result = runner.invoke(main, ["--config", str(cfg_path), "estimate", "--focus", "security"])
        assert result.exit_code == 0, result.output
        assert "No repos configured" in result.output

    def test_off_schedule_without_focus_override(self, tmp_path):
        """When today is off and no --focus given, show 'off' message."""
        (tmp_path / "app.py").write_text("x = 1")
        # Set all days to off
        schedule = {
            d: "off"
            for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        }
        cfg = _write_config(tmp_path, schedule=schedule)
        runner = CliRunner()
        result = runner.invoke(main, ["--config", cfg, "estimate"])
        assert result.exit_code == 0, result.output
        assert "off" in result.output.lower()

    def test_provider_override(self, tmp_path):
        """--provider flag overrides config provider."""
        (tmp_path / "app.py").write_text("x = 1\n" * 100)
        cfg = _write_config(tmp_path, model="gemini-2.0-flash", provider="gemini")
        runner = CliRunner()
        result = runner.invoke(
            main, ["--config", cfg, "estimate", "--focus", "security", "--provider", "gemini"]
        )
        assert result.exit_code == 0, result.output
        assert "gemini" in result.output
