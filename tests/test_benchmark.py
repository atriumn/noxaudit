"""Tests for benchmark runner utility functions."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Import the benchmark script (not a package, so we use importlib)
# ---------------------------------------------------------------------------

_BENCHMARK_PATH = Path(__file__).parent.parent / "scripts" / "benchmark.py"


def _import_benchmark():
    spec = importlib.util.spec_from_file_location("benchmark", _BENCHMARK_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


benchmark = _import_benchmark()


# ---------------------------------------------------------------------------
# result_path
# ---------------------------------------------------------------------------


class TestResultPath:
    def test_basic(self, tmp_path):
        p = benchmark.result_path(tmp_path, "noxaudit", "gemini", "gemini-2.0-flash", "security", 1)
        assert p == tmp_path / "noxaudit" / "gemini-gemini-2.0-flash-security-run1.json"

    def test_model_with_slashes_sanitized(self, tmp_path):
        p = benchmark.result_path(tmp_path, "repo", "anthropic", "claude/sonnet:v1", "all", 2)
        assert "/" not in p.name
        assert ":" not in p.name
        assert p.name.endswith("-run2.json")

    def test_run_number_in_filename(self, tmp_path):
        p1 = benchmark.result_path(tmp_path, "repo", "gemini", "gemini-2.0-flash", "security", 1)
        p2 = benchmark.result_path(tmp_path, "repo", "gemini", "gemini-2.0-flash", "security", 2)
        assert p1 != p2
        assert "run1" in p1.name
        assert "run2" in p2.name

    def test_nested_under_repo_dir(self, tmp_path):
        p = benchmark.result_path(tmp_path, "my-repo", "gemini", "gemini-2.0-flash", "security", 1)
        assert p.parent == tmp_path / "my-repo"


# ---------------------------------------------------------------------------
# build_combinations
# ---------------------------------------------------------------------------


class TestBuildCombinations:
    def _matrix(self, **overrides):
        base = {
            "providers": [{"name": "gemini", "models": ["gemini-2.0-flash"]}],
            "repos": [{"name": "noxaudit", "path": "/tmp/noxaudit"}],
            "focus": ["security"],
            "runs": 1,
            "output_dir": "benchmark/results",
            "rate_limit": {"sleep_between_runs": 0, "backoff_on_error": 0},
        }
        base.update(overrides)
        return base

    def test_single_combination(self):
        combos = benchmark.build_combinations(self._matrix())
        assert len(combos) == 1
        c = combos[0]
        assert c["repo_name"] == "noxaudit"
        assert c["provider"] == "gemini"
        assert c["model"] == "gemini-2.0-flash"
        assert c["focus"] == "security"
        assert c["run"] == 1

    def test_multiple_runs(self):
        combos = benchmark.build_combinations(self._matrix(runs=3))
        assert len(combos) == 3
        assert [c["run"] for c in combos] == [1, 2, 3]

    def test_multiple_focus_areas(self):
        combos = benchmark.build_combinations(self._matrix(focus=["security", "all"]))
        assert len(combos) == 2
        foci = {c["focus"] for c in combos}
        assert foci == {"security", "all"}

    def test_multiple_providers_and_models(self):
        matrix = self._matrix(
            providers=[
                {"name": "gemini", "models": ["gemini-2.0-flash"]},
                {
                    "name": "anthropic",
                    "models": ["claude-haiku-4-5-20251001", "claude-sonnet-4-5-20250929"],
                },
            ]
        )
        combos = benchmark.build_combinations(matrix)
        assert len(combos) == 3  # 1 gemini model + 2 anthropic models
        providers = [c["provider"] for c in combos]
        assert providers.count("gemini") == 1
        assert providers.count("anthropic") == 2

    def test_full_matrix_expansion(self):
        matrix = self._matrix(
            providers=[
                {"name": "gemini", "models": ["gemini-2.0-flash"]},
                {"name": "anthropic", "models": ["claude-haiku-4-5-20251001"]},
            ],
            repos=[
                {"name": "noxaudit", "path": "/tmp/noxaudit"},
                {"name": "python-dotenv", "path": "/tmp/python-dotenv"},
            ],
            focus=["security", "all"],
            runs=2,
        )
        combos = benchmark.build_combinations(matrix)
        # 2 providers × 2 repos × 2 focus × 2 runs = 16
        assert len(combos) == 16

    def test_commit_sha_included(self):
        matrix = self._matrix(
            repos=[{"name": "noxaudit", "path": "/tmp/noxaudit", "commit": "abc123"}]
        )
        combos = benchmark.build_combinations(matrix)
        assert combos[0]["repo_commit"] == "abc123"

    def test_missing_commit_defaults_to_empty_string(self):
        combos = benchmark.build_combinations(self._matrix())
        assert combos[0]["repo_commit"] == ""

    def test_output_dir_in_combo(self):
        matrix = self._matrix(output_dir="my/output")
        combos = benchmark.build_combinations(matrix)
        assert combos[0]["output_dir"] == Path("my/output")

    def test_rate_limit_defaults(self):
        matrix = {
            "providers": [{"name": "gemini", "models": ["gemini-2.0-flash"]}],
            "repos": [{"name": "noxaudit", "path": "/tmp/noxaudit"}],
            "focus": ["security"],
            "runs": 1,
        }
        combos = benchmark.build_combinations(matrix)
        assert combos[0]["sleep_s"] == 3.0
        assert combos[0]["backoff_s"] == 30.0


# ---------------------------------------------------------------------------
# build_result_record
# ---------------------------------------------------------------------------


class TestBuildResultRecord:
    def _record(self, **overrides):
        from datetime import datetime

        base = dict(
            repo="noxaudit",
            repo_commit="abc123",
            provider="gemini",
            model="gemini-2.0-flash",
            focus="security",
            run=1,
            started_at=datetime(2026, 3, 1, 10, 0, 0),
            completed_at=datetime(2026, 3, 1, 10, 0, 42),
            wall_clock_seconds=42.0,
            error=None,
            tokens={"input": 1000, "output": 200, "cache_read": 0, "cache_write": 0},
            cost_usd=0.01,
            findings=[],
        )
        base.update(overrides)
        return benchmark.build_result_record(**base)

    def test_schema_keys(self):
        rec = self._record()
        assert set(rec.keys()) == {"meta", "tokens", "cost_usd", "findings_count", "findings"}

    def test_meta_fields(self):
        rec = self._record()
        meta = rec["meta"]
        assert meta["repo"] == "noxaudit"
        assert meta["provider"] == "gemini"
        assert meta["model"] == "gemini-2.0-flash"
        assert meta["focus"] == "security"
        assert meta["run"] == 1
        assert meta["repo_commit"] == "abc123"
        assert meta["wall_clock_seconds"] == 42.0
        assert meta["error"] is None

    def test_findings_count_matches_list(self):
        findings = [{"id": "x", "title": "test"}]
        rec = self._record(findings=findings)
        assert rec["findings_count"] == 1
        assert len(rec["findings"]) == 1

    def test_error_captured(self):
        rec = self._record(error="Rate limit exceeded")
        assert rec["meta"]["error"] == "Rate limit exceeded"

    def test_tokens_schema(self):
        rec = self._record(
            tokens={"input": 5000, "output": 300, "cache_read": 100, "cache_write": 50}
        )
        assert rec["tokens"]["input"] == 5000
        assert rec["tokens"]["cache_read"] == 100

    def test_json_serializable(self):
        rec = self._record()
        # Should not raise
        json.dumps(rec)


# ---------------------------------------------------------------------------
# run_one — skip logic (no actual API calls)
# ---------------------------------------------------------------------------


class TestRunOneSkipLogic:
    def test_skips_existing_result(self, tmp_path):
        # Pre-create the expected output file
        out = tmp_path / "noxaudit" / "gemini-gemini-2.0-flash-security-run1.json"
        out.parent.mkdir(parents=True)
        out.write_text("{}")

        ran = benchmark.run_one(
            repo_name="noxaudit",
            repo_path="/nonexistent",
            repo_commit="",
            provider="gemini",
            model="gemini-2.0-flash",
            focus="security",
            run=1,
            output_dir=tmp_path,
        )
        assert ran is False

    def test_writes_result_file_on_error(self, tmp_path, tmp_repo):
        """run_one writes a JSON result file even when the provider call fails."""
        with pytest.raises(RuntimeError):
            benchmark.run_one(
                repo_name="myrepo",
                repo_path=str(tmp_repo),
                repo_commit="deadbeef",
                provider="gemini",
                model="gemini-2.0-flash",
                focus="security",
                run=1,
                output_dir=tmp_path,
            )
        # The result file should still have been written with the error captured.
        out = tmp_path / "myrepo" / "gemini-gemini-2.0-flash-security-run1.json"
        assert out.exists()
        record = json.loads(out.read_text())
        assert record["meta"]["repo"] == "myrepo"
        assert record["meta"]["repo_commit"] == "deadbeef"
        assert record["meta"]["provider"] == "gemini"
        assert record["meta"]["error"] is not None
        assert "findings_count" in record
        assert "tokens" in record
