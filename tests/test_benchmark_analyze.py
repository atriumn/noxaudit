"""Tests for scripts/benchmark_analyze.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Import the script via importlib (same pattern as test_benchmark.py)
# ---------------------------------------------------------------------------

_ANALYZE_PATH = Path(__file__).parent.parent / "scripts" / "benchmark_analyze.py"


def _import_analyze():
    spec = importlib.util.spec_from_file_location("benchmark_analyze", _ANALYZE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["benchmark_analyze"] = mod  # must register before exec for @dataclass
    spec.loader.exec_module(mod)
    return mod


analyze = _import_analyze()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_result(
    repo="noxaudit",
    provider="gemini",
    model="gemini-2.5-flash",
    focus="security",
    run=1,
    findings=None,
    cost_usd=0.01,
    wall_clock_seconds=30.0,
    error=None,
    input_tokens=1000,
    output_tokens=200,
):
    if findings is None:
        findings = []
    return {
        "meta": {
            "repo": repo,
            "repo_commit": "abc123",
            "provider": provider,
            "model": model,
            "focus": focus,
            "run": run,
            "started_at": "2026-03-01T10:00:00",
            "completed_at": "2026-03-01T10:00:30",
            "wall_clock_seconds": wall_clock_seconds,
            "error": error,
        },
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "cache_read": 0,
            "cache_write": 0,
        },
        "cost_usd": cost_usd,
        "findings_count": len(findings),
        "findings": findings,
    }


def _make_finding(fid="f001", severity="high", file="src/app.py"):
    return {
        "id": fid,
        "severity": severity,
        "file": file,
        "line": 10,
        "title": f"Issue {fid}",
        "description": "A finding",
        "suggestion": "Fix it",
    }


# ---------------------------------------------------------------------------
# load_results
# ---------------------------------------------------------------------------


class TestLoadResults:
    def test_loads_json_files(self, tmp_path):
        result = _make_result()
        (tmp_path / "noxaudit").mkdir()
        (tmp_path / "noxaudit" / "gemini-gemini-2.5-flash-security-run1.json").write_text(
            json.dumps(result)
        )
        loaded = analyze.load_results(tmp_path)
        assert len(loaded) == 1
        assert loaded[0]["meta"]["repo"] == "noxaudit"

    def test_loads_nested_subdirectories(self, tmp_path):
        (tmp_path / "repo1").mkdir()
        (tmp_path / "repo2").mkdir()
        (tmp_path / "repo1" / "result1.json").write_text(json.dumps(_make_result(repo="repo1")))
        (tmp_path / "repo2" / "result2.json").write_text(json.dumps(_make_result(repo="repo2")))
        loaded = analyze.load_results(tmp_path)
        assert len(loaded) == 2

    def test_skips_invalid_json(self, tmp_path, capsys):
        (tmp_path / "bad.json").write_text("not json {{")
        (tmp_path / "good.json").write_text(json.dumps(_make_result()))
        loaded = analyze.load_results(tmp_path)
        assert len(loaded) == 1
        assert "Warning" in capsys.readouterr().err

    def test_returns_empty_for_empty_dir(self, tmp_path):
        assert analyze.load_results(tmp_path) == []

    def test_partial_results_ok(self, tmp_path):
        """Works with partial results (not full matrix)."""
        (tmp_path / "result.json").write_text(json.dumps(_make_result(model="model-a")))
        loaded = analyze.load_results(tmp_path)
        assert len(loaded) == 1


# ---------------------------------------------------------------------------
# _jaccard
# ---------------------------------------------------------------------------


class TestJaccard:
    def test_identical_sets(self):
        assert analyze._jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self):
        assert analyze._jaccard({"a"}, {"b"}) == 0.0

    def test_partial_overlap(self):
        # |{a,b} ∩ {b,c}| / |{a,b} ∪ {b,c}| = 1/3
        result = analyze._jaccard({"a", "b"}, {"b", "c"})
        assert abs(result - 1 / 3) < 1e-9

    def test_both_empty(self):
        assert analyze._jaccard(set(), set()) == 1.0

    def test_one_empty(self):
        assert analyze._jaccard({"a"}, set()) == 0.0


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------


class TestComputeMetrics:
    def test_empty_returns_empty(self):
        assert analyze.compute_metrics([]) == {}

    def test_basic_model_detected(self):
        results = [_make_result(model="gemini-2.5-flash")]
        m = analyze.compute_metrics(results)
        assert "gemini-2.5-flash" in m

    def test_run_count(self):
        results = [_make_result(run=1), _make_result(run=2)]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].run_count == 2

    def test_findings_per_run_mean(self):
        findings_a = [_make_finding("f1"), _make_finding("f2")]
        findings_b = [_make_finding("f3")]
        results = [
            _make_result(run=1, findings=findings_a),
            _make_result(run=2, findings=findings_b),
        ]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].findings_per_run == 1.5  # mean([2, 1])

    def test_high_sev_rate(self):
        findings = [
            _make_finding("f1", severity="high"),
            _make_finding("f2", severity="low"),
            _make_finding("f3", severity="medium"),
            _make_finding("f4", severity="high"),
        ]
        results = [_make_result(findings=findings)]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].high_sev_rate == 0.5  # 2/4

    def test_critical_severity_counted_as_high(self):
        findings = [
            _make_finding("f1", severity="critical"),
            _make_finding("f2", severity="low"),
        ]
        results = [_make_result(findings=findings)]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].high_sev_rate == 0.5

    def test_wall_clock_mean(self):
        results = [
            _make_result(run=1, wall_clock_seconds=10.0),
            _make_result(run=2, wall_clock_seconds=20.0),
        ]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].wall_clock_seconds == 15.0

    def test_error_count(self):
        results = [
            _make_result(run=1, error=None),
            _make_result(run=2, error="Rate limit exceeded"),
        ]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].errors == 1

    def test_error_results_excluded_from_metrics(self):
        """Error results don't pollute findings/run count."""
        results = [
            _make_result(run=1, findings=[_make_finding("f1")], error=None),
            _make_result(run=2, findings=[], error="boom"),
        ]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].findings_per_run == 1.0  # only run1 counts

    def test_consistency_same_findings(self):
        findings = [_make_finding("f1"), _make_finding("f2")]
        results = [
            _make_result(run=1, findings=findings),
            _make_result(run=2, findings=findings),
        ]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].consistency == 1.0

    def test_consistency_different_findings(self):
        results = [
            _make_result(run=1, findings=[_make_finding("f1")]),
            _make_result(run=2, findings=[_make_finding("f2")]),
        ]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].consistency == 0.0

    def test_consistency_none_for_single_run(self):
        """Consistency is None when only 1 run per (repo, focus) combo."""
        results = [_make_result(run=1)]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].consistency is None

    def test_consistency_partial_overlap(self):
        """Jaccard of {f1,f2} and {f1,f3} = 1/3."""
        results = [
            _make_result(run=1, findings=[_make_finding("f1"), _make_finding("f2")]),
            _make_result(run=2, findings=[_make_finding("f1"), _make_finding("f3")]),
        ]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].consistency is not None
        assert abs(m["gemini-2.5-flash"].consistency - 1 / 3) < 1e-9

    def test_canary_repo_metrics(self):
        results = [
            _make_result(
                repo=analyze.CANARY_REPO,
                findings=[_make_finding("f1", severity="low")],
            )
        ]
        m = analyze.compute_metrics(results)
        mm = m["gemini-2.5-flash"]
        assert mm.canary_findings == 1
        assert mm.canary_high_sev == 0

    def test_canary_high_sev_flagged(self):
        results = [
            _make_result(
                repo=analyze.CANARY_REPO,
                findings=[_make_finding("f1", severity="high")],
            )
        ]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].canary_high_sev == 1

    def test_canary_not_tested_is_minus_one(self):
        results = [_make_result(repo="some-other-repo")]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].canary_findings == -1
        assert m["gemini-2.5-flash"].canary_high_sev == -1

    def test_unique_findings_cross_model(self):
        results = [
            _make_result(
                model="model-a",
                findings=[_make_finding("f-unique-a"), _make_finding("f-shared")],
            ),
            _make_result(
                model="model-b",
                findings=[_make_finding("f-unique-b"), _make_finding("f-shared")],
            ),
        ]
        m = analyze.compute_metrics(results)
        assert m["model-a"].unique_findings == 1
        assert m["model-b"].unique_findings == 1

    def test_unique_findings_all_shared(self):
        findings = [_make_finding("f1"), _make_finding("f2")]
        results = [
            _make_result(model="model-a", findings=findings),
            _make_result(model="model-b", findings=findings),
        ]
        m = analyze.compute_metrics(results)
        assert m["model-a"].unique_findings == 0
        assert m["model-b"].unique_findings == 0

    def test_multiple_models(self):
        results = [
            _make_result(model="model-a", provider="gemini"),
            _make_result(model="model-b", provider="anthropic"),
        ]
        m = analyze.compute_metrics(results)
        assert len(m) == 2
        assert "model-a" in m
        assert "model-b" in m

    def test_cost_per_finding_zero_when_no_findings(self):
        results = [_make_result(findings=[], cost_usd=0.01)]
        m = analyze.compute_metrics(results)
        assert m["gemini-2.5-flash"].cost_per_finding == 0.0

    def test_partial_results_different_repos(self):
        """Works when only some repos have results (partial matrix)."""
        results = [_make_result(repo="repo-a")]
        m = analyze.compute_metrics(results)
        assert "gemini-2.5-flash" in m

    def test_all_errors_model_still_present(self):
        """A model with only errors still appears in metrics with run_count set."""
        results = [_make_result(error="boom")]
        m = analyze.compute_metrics(results)
        assert "gemini-2.5-flash" in m
        assert m["gemini-2.5-flash"].run_count == 1
        assert m["gemini-2.5-flash"].errors == 1


# ---------------------------------------------------------------------------
# generate_scorecard
# ---------------------------------------------------------------------------


class TestGenerateScorecard:
    def _two_model_metrics(self):
        results = [
            _make_result(
                model="gemini-2.5-flash",
                provider="gemini",
                repo=analyze.CANARY_REPO,
                findings=[_make_finding("f1", severity="low")],
                cost_usd=0.01,
            ),
            _make_result(
                model="claude-opus-4-6",
                provider="anthropic",
                repo=analyze.CANARY_REPO,
                findings=[_make_finding("f2", severity="high")],
                cost_usd=0.50,
            ),
        ]
        return analyze.compute_metrics(results)

    def test_returns_string(self):
        sc = analyze.generate_scorecard(self._two_model_metrics())
        assert isinstance(sc, str)

    def test_contains_header(self):
        sc = analyze.generate_scorecard(self._two_model_metrics())
        assert "# Noxaudit Benchmark Scorecard" in sc

    def test_contains_model_names(self):
        sc = analyze.generate_scorecard(self._two_model_metrics())
        assert "gemini-2.5-flash" in sc
        assert "claude-opus-4-6" in sc

    def test_contains_comparison_matrix_section(self):
        sc = analyze.generate_scorecard(self._two_model_metrics())
        assert "## Comparison Matrix" in sc

    def test_contains_canary_section(self):
        sc = analyze.generate_scorecard(self._two_model_metrics())
        assert "## Hallucination Canary" in sc

    def test_contains_recommendations_section(self):
        sc = analyze.generate_scorecard(self._two_model_metrics())
        assert "## Recommendations" in sc

    def test_canary_warn_for_high_sev(self):
        sc = analyze.generate_scorecard(self._two_model_metrics())
        assert "⚠" in sc

    def test_canary_ok_status(self):
        results = [
            _make_result(
                model="gemini-2.5-flash",
                repo=analyze.CANARY_REPO,
                findings=[_make_finding("f1", severity="low")],
            )
        ]
        m = analyze.compute_metrics(results)
        sc = analyze.generate_scorecard(m)
        assert "OK" in sc

    def test_empty_metrics_handled(self):
        sc = analyze.generate_scorecard({})
        assert "No benchmark results found" in sc

    def test_generated_at_included(self):
        sc = analyze.generate_scorecard(self._two_model_metrics(), generated_at="2026-03-01")
        assert "2026-03-01" in sc

    def test_both_sync_and_batch_cost_columns(self):
        sc = analyze.generate_scorecard(self._two_model_metrics())
        assert "sync" in sc.lower()
        assert "batch" in sc.lower()

    def test_not_tested_canary_shows_dash(self):
        """Models that didn't run against the canary show '—'."""
        results = [_make_result(model="model-a", repo="other-repo")]
        m = analyze.compute_metrics(results)
        sc = analyze.generate_scorecard(m)
        assert "—" in sc


# ---------------------------------------------------------------------------
# build_recommendations
# ---------------------------------------------------------------------------


class TestBuildRecommendations:
    def test_empty_metrics_returns_fallback(self):
        rec = analyze.build_recommendations({})
        assert "Insufficient" in rec

    def test_returns_string(self):
        results = [_make_result(cost_usd=0.01, findings=[_make_finding("f1")])]
        m = analyze.compute_metrics(results)
        rec = analyze.build_recommendations(m)
        assert isinstance(rec, str)

    def test_mentions_daily_batch(self):
        results = [
            _make_result(model="model-cheap", cost_usd=0.001, findings=[_make_finding("f1")]),
            _make_result(model="model-expensive", cost_usd=1.0, findings=[_make_finding("f2")]),
        ]
        m = analyze.compute_metrics(results)
        rec = analyze.build_recommendations(m)
        assert "daily" in rec.lower() or "batch" in rec.lower()

    def test_prefers_cheaper_for_daily(self):
        results = [
            _make_result(
                model="model-cheap",
                provider="gemini",
                cost_usd=0.001,
                input_tokens=100,
                output_tokens=10,
            ),
            _make_result(
                model="model-expensive",
                provider="anthropic",
                cost_usd=1.0,
                input_tokens=100,
                output_tokens=10,
            ),
        ]
        m = analyze.compute_metrics(results)
        rec = analyze.build_recommendations(m)
        assert "model-cheap" in rec


# ---------------------------------------------------------------------------
# _canary_status helper
# ---------------------------------------------------------------------------


class TestCanaryStatus:
    def test_not_tested(self):
        assert analyze._canary_status(-1, -1) == "—"

    def test_ok(self):
        assert analyze._canary_status(1, 0) == "OK"

    def test_warn_too_many(self):
        assert analyze._canary_status(analyze.CANARY_MAX_EXPECTED + 1, 0) == "⚠ WARN"

    def test_high_sev(self):
        assert analyze._canary_status(1, 1) == "⚠ HIGH SEV"


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------


class TestCLI:
    def _write_result(self, results_dir: Path, **kwargs) -> None:
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / "result.json"
        path.write_text(json.dumps(_make_result(**kwargs)))

    def _run_main(self, argv: list[str]) -> int | None:
        old_argv = sys.argv
        sys.argv = argv
        try:
            analyze.main()
            return 0
        except SystemExit as e:
            return e.code
        finally:
            sys.argv = old_argv

    def test_scorecard_command_writes_file(self, tmp_path):
        results_dir = tmp_path / "results"
        self._write_result(results_dir, findings=[_make_finding("f1")])
        output = tmp_path / "scorecard.md"

        code = self._run_main(
            ["benchmark_analyze.py", "scorecard", str(results_dir), "-o", str(output)]
        )
        assert code in (0, None)
        assert output.exists()
        assert "Noxaudit Benchmark Scorecard" in output.read_text()

    def test_scorecard_creates_parent_dirs(self, tmp_path):
        results_dir = tmp_path / "results"
        self._write_result(results_dir)
        output = tmp_path / "nested" / "deep" / "scorecard.md"

        self._run_main(["benchmark_analyze.py", "scorecard", str(results_dir), "-o", str(output)])
        assert output.exists()

    def test_scorecard_nonexistent_dir_exits(self, tmp_path):
        code = self._run_main(
            [
                "benchmark_analyze.py",
                "scorecard",
                str(tmp_path / "nonexistent"),
                "-o",
                str(tmp_path / "out.md"),
            ]
        )
        assert code not in (0, None)

    def test_summary_command_prints_output(self, tmp_path, capsys):
        results_dir = tmp_path / "results"
        self._write_result(results_dir, findings=[_make_finding("f1")])

        self._run_main(["benchmark_analyze.py", "summary", str(results_dir)])

        out = capsys.readouterr().out
        assert "gemini-2.5-flash" in out

    def test_summary_nonexistent_dir_exits(self, tmp_path):
        code = self._run_main(["benchmark_analyze.py", "summary", str(tmp_path / "nonexistent")])
        assert code not in (0, None)

    def test_no_command_exits_nonzero(self):
        code = self._run_main(["benchmark_analyze.py"])
        assert code not in (0, None)
