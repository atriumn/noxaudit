"""Tests for cost tracking functionality."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest import mock


from noxaudit.cost_ledger import CostLedger


class TestCostLedgerAppend:
    """Test ledger append operations."""

    def test_creates_file_if_missing(self, tmp_path):
        """Ledger file is created if it doesn't exist."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            CostLedger.append_entry(
                repo="test-repo",
                focus="security",
                provider="gemini",
                model="gemini-2.0-flash",
                input_tokens=1000,
                output_tokens=500,
                cache_read_tokens=0,
                cache_write_tokens=0,
                file_count=10,
            )
            assert ledger_path.exists()

    def test_appends_to_existing_file(self, tmp_path):
        """Entries are appended to existing ledger file."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            # First entry
            CostLedger.append_entry(
                repo="test-repo",
                focus="security",
                provider="gemini",
                model="gemini-2.0-flash",
                input_tokens=1000,
                output_tokens=500,
                cache_read_tokens=0,
                cache_write_tokens=0,
                file_count=10,
            )
            # Second entry
            CostLedger.append_entry(
                repo="test-repo",
                focus="performance",
                provider="gemini",
                model="gemini-2.0-flash",
                input_tokens=2000,
                output_tokens=1000,
                cache_read_tokens=0,
                cache_write_tokens=0,
                file_count=20,
            )

            entries = CostLedger.read_entries()
            assert len(entries) == 2
            assert entries[0]["focus"] == "security"
            assert entries[1]["focus"] == "performance"

    def test_entry_format_is_correct(self, tmp_path):
        """Ledger entry has all required fields."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        timestamp = "2026-02-18T10:00:00"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            CostLedger.append_entry(
                repo="my-app",
                focus="security",
                provider="gemini",
                model="gemini-2.5-flash",
                input_tokens=287000,
                output_tokens=16200,
                cache_read_tokens=0,
                cache_write_tokens=0,
                file_count=142,
                timestamp=timestamp,
            )

            entry = CostLedger.read_entries()[0]
            assert entry["timestamp"] == timestamp
            assert entry["repo"] == "my-app"
            assert entry["focus"] == "security"
            assert entry["provider"] == "gemini"
            assert entry["model"] == "gemini-2.5-flash"
            assert entry["input_tokens"] == 287000
            assert entry["output_tokens"] == 16200
            assert entry["cache_read_tokens"] == 0
            assert entry["cache_write_tokens"] == 0
            assert entry["file_count"] == 142
            assert "cost_estimate_usd" in entry

    def test_cost_calculation_uses_pricing(self, tmp_path):
        """Cost is calculated correctly using pricing data."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            # Gemini pricing: $0.10/M input, $0.40/M output
            CostLedger.append_entry(
                repo="test",
                focus="security",
                provider="gemini",
                model="gemini-2.0-flash",
                input_tokens=1_000_000,
                output_tokens=1_000_000,
                cache_read_tokens=0,
                cache_write_tokens=0,
                file_count=100,
            )

            entry = CostLedger.read_entries()[0]
            # 1M input * $0.10 + 1M output * $0.40 = $0.50
            expected_cost = 0.10 + 0.40
            assert abs(entry["cost_estimate_usd"] - expected_cost) < 0.01

    def test_batch_discount_applied_for_anthropic(self, tmp_path):
        """Batch discount is applied for Anthropic provider."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            # Anthropic with batch discount (50%)
            # Using 1M tokens exceeds tier threshold (200K), so tiered pricing applies
            CostLedger.append_entry(
                repo="test",
                focus="security",
                provider="anthropic",
                model="claude-sonnet-4-5",
                input_tokens=1_000_000,
                output_tokens=1_000_000,
                cache_read_tokens=0,
                cache_write_tokens=0,
                file_count=100,
            )

            entry = CostLedger.read_entries()[0]
            # Tier threshold is 200K:
            # Input: 200K * $3.00/M + 800K * $6.00/M = 0.60 + 4.80 = $5.40
            # Output (all high tier): 1M * $22.50/M = $22.50
            # Total: $27.90, with 50% batch discount = $13.95
            expected_cost = 13.95
            assert abs(entry["cost_estimate_usd"] - expected_cost) < 0.01

    def test_cache_read_tokens_included_in_cost(self, tmp_path):
        """Cache read tokens are included in cost calculation."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            # Anthropic Sonnet: cache read = $0.30/M, with 50% batch discount = $0.15/M
            CostLedger.append_entry(
                repo="test",
                focus="security",
                provider="anthropic",
                model="claude-sonnet-4-5",
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=1_000_000,
                cache_write_tokens=0,
                file_count=10,
            )
            entry = CostLedger.read_entries()[0]
            # 1M cache read * $0.30/M * 50% batch discount = $0.15
            expected_cost = 0.15
            assert abs(entry["cost_estimate_usd"] - expected_cost) < 0.001

    def test_cache_write_tokens_included_in_cost(self, tmp_path):
        """Cache write tokens are included in cost calculation."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            # Anthropic Sonnet: cache write = $3.75/M, with 50% batch discount = $1.875/M
            CostLedger.append_entry(
                repo="test",
                focus="security",
                provider="anthropic",
                model="claude-sonnet-4-5",
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_write_tokens=1_000_000,
                file_count=10,
            )
            entry = CostLedger.read_entries()[0]
            # 1M cache write * $3.75/M * 50% batch discount = $1.875
            expected_cost = 1.875
            assert abs(entry["cost_estimate_usd"] - expected_cost) < 0.001


class TestCostLedgerRead:
    """Test ledger read operations."""

    def test_read_empty_ledger(self, tmp_path):
        """Reading non-existent ledger returns empty list."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            entries = CostLedger.read_entries()
            assert entries == []

    def test_read_multiple_entries(self, tmp_path):
        """Multiple entries are read correctly."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            for i in range(3):
                CostLedger.append_entry(
                    repo=f"repo-{i}",
                    focus="security",
                    provider="gemini",
                    model="gemini-2.0-flash",
                    input_tokens=1000,
                    output_tokens=500,
                    cache_read_tokens=0,
                    cache_write_tokens=0,
                    file_count=10,
                )

            entries = CostLedger.read_entries()
            assert len(entries) == 3
            assert entries[0]["repo"] == "repo-0"
            assert entries[2]["repo"] == "repo-2"

    def test_skips_malformed_lines(self, tmp_path):
        """Malformed JSON lines are skipped gracefully."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            # Write a valid entry
            CostLedger.append_entry(
                repo="test",
                focus="security",
                provider="gemini",
                model="gemini-2.0-flash",
                input_tokens=1000,
                output_tokens=500,
                cache_read_tokens=0,
                cache_write_tokens=0,
                file_count=10,
            )

            # Append a malformed line manually
            with open(ledger_path, "a") as f:
                f.write("{ invalid json }\n")
                f.write('{"valid": "entry"}\n')  # This won't have all fields but shouldn't crash

            # Reading should skip malformed line and read valid entries
            entries = CostLedger.read_entries()
            assert len(entries) >= 1  # At least the first valid entry

    def test_get_last_n(self, tmp_path):
        """Get last N entries works correctly."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            for i in range(5):
                CostLedger.append_entry(
                    repo=f"repo-{i}",
                    focus="security",
                    provider="gemini",
                    model="gemini-2.0-flash",
                    input_tokens=1000,
                    output_tokens=500,
                    cache_read_tokens=0,
                    cache_write_tokens=0,
                    file_count=10,
                )

            last_3 = CostLedger.get_last_n(3)
            assert len(last_3) == 3
            assert last_3[0]["repo"] == "repo-2"
            assert last_3[2]["repo"] == "repo-4"

    def test_get_last_n_days(self, tmp_path):
        """Get entries from last N days filters correctly."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            now = datetime.now()
            # Add entry from 5 days ago
            old_timestamp = (now - timedelta(days=5)).isoformat()
            CostLedger.append_entry(
                repo="old",
                focus="security",
                provider="gemini",
                model="gemini-2.0-flash",
                input_tokens=1000,
                output_tokens=500,
                cache_read_tokens=0,
                cache_write_tokens=0,
                file_count=10,
                timestamp=old_timestamp,
            )

            # Add entry from today
            recent_timestamp = now.isoformat()
            CostLedger.append_entry(
                repo="recent",
                focus="security",
                provider="gemini",
                model="gemini-2.0-flash",
                input_tokens=1000,
                output_tokens=500,
                cache_read_tokens=0,
                cache_write_tokens=0,
                file_count=10,
                timestamp=recent_timestamp,
            )

            # Get last 3 days should only include recent
            last_3_days = CostLedger.get_last_n_days(3)
            assert len(last_3_days) == 1
            assert last_3_days[0]["repo"] == "recent"

            # Get last 10 days should include both
            last_10_days = CostLedger.get_last_n_days(10)
            assert len(last_10_days) == 2


class TestStatusCommandCostDisplay:
    """Test cost display in status command."""

    def test_status_shows_no_history_when_empty(self, tmp_path, monkeypatch):
        """Status shows 'No audit history yet' when ledger is empty."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            from click.testing import CliRunner
            from noxaudit.cli import main

            # Create a minimal config
            config_file = tmp_path / "noxaudit.yml"
            config_file.write_text("repos: []\n")

            runner = CliRunner()
            result = runner.invoke(main, ["--config", str(config_file), "status"])
            assert result.exit_code == 0
            assert "No audit history yet" in result.output

    def test_status_shows_cost_summary(self, tmp_path):
        """Status shows cost summary when entries exist."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            from click.testing import CliRunner
            from noxaudit.cli import main

            # Add some entries
            for i in range(3):
                CostLedger.append_entry(
                    repo=f"repo-{i}",
                    focus="security",
                    provider="gemini",
                    model="gemini-2.0-flash",
                    input_tokens=1000,
                    output_tokens=500,
                    cache_read_tokens=0,
                    cache_write_tokens=0,
                    file_count=10,
                )

            # Create a minimal config
            config_file = tmp_path / "noxaudit.yml"
            config_file.write_text("repos: []\n")

            runner = CliRunner()
            result = runner.invoke(main, ["--config", str(config_file), "status"])
            assert result.exit_code == 0
            assert "Cost (last 30 days):" in result.output
            assert "Audits run:" in result.output

    def test_status_shows_last_5_audits(self, tmp_path):
        """Status shows last 5 audits in summary."""
        ledger_path = tmp_path / ".noxaudit" / "cost-ledger.jsonl"
        with mock.patch.object(CostLedger, "LEDGER_PATH", ledger_path):
            from click.testing import CliRunner
            from noxaudit.cli import main

            # Add 7 entries
            for i in range(7):
                CostLedger.append_entry(
                    repo=f"repo-{i}",
                    focus="security",
                    provider="gemini",
                    model="gemini-2.0-flash",
                    input_tokens=1000 * (i + 1),
                    output_tokens=500 * (i + 1),
                    cache_read_tokens=0,
                    cache_write_tokens=0,
                    file_count=10 + i,
                )

            # Create a minimal config
            config_file = tmp_path / "noxaudit.yml"
            config_file.write_text("repos: []\n")

            runner = CliRunner()
            result = runner.invoke(main, ["--config", str(config_file), "status"])
            assert result.exit_code == 0
            assert "Last 5 audits:" in result.output
            # Should show the last 5 entries (indices 2-6, file counts 12-16)
            assert "16 files" in result.output
            assert "12 files" in result.output


class TestProviderTokenTracking:
    """Test that providers track token usage."""

    def test_anthropic_provider_stores_usage(self):
        """AnthropicProvider stores token usage."""
        from noxaudit.providers.anthropic import AnthropicProvider

        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            provider = AnthropicProvider()
            assert provider._last_usage["input_tokens"] == 0

            # Simulate storing usage
            provider._last_usage = {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
            }

            usage = provider.get_last_usage()
            assert usage["input_tokens"] == 100
            assert usage["output_tokens"] == 50

    def test_gemini_provider_stores_usage(self):
        """GeminiProvider stores token usage."""
        with mock.patch("noxaudit.providers.gemini.genai"):
            with mock.patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
                from noxaudit.providers.gemini import GeminiProvider

                provider = GeminiProvider()
                assert provider._last_usage["input_tokens"] == 0

                # Simulate storing usage
                provider._last_usage = {
                    "input_tokens": 200,
                    "output_tokens": 100,
                    "cache_read_tokens": 0,
                    "cache_write_tokens": 0,
                }

                usage = provider.get_last_usage()
                assert usage["input_tokens"] == 200
                assert usage["output_tokens"] == 100
