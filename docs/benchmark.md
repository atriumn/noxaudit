# Benchmark Results

We benchmarked all 10 supported models to understand which ones actually find real issues vs. generate noise. This data directly informs our [recommended model tiers](reference/providers.md#recommended-setup).

## Methodology

- **Repos**: python-dotenv (34 files, ~52K tokens) and noxaudit itself (88 files, ~126K tokens)
- **Focus**: All 7 areas (security, docs, patterns, testing, hygiene, dependencies, performance)
- **Method**: Batch API on all providers (50% discount), 1 run per model per repo
- **Quality validation**: Cross-model consensus — issues found by 4+ models (out of 10) are considered "real"
- **Total spend**: $2.13

## Scorecard

| Model | dotenv | noxaudit | Total Findings | Cost | $/finding |
|---|---:|---:|---:|---:|---:|
| gpt-5-nano | 4 | 6 | 10 | $0.01 | $0.001 |
| gpt-5-mini | 15 | 24 | 39 | $0.03 | $0.001 |
| gemini-2.5-flash | 18 | 16 | 34 | $0.07 | $0.002 |
| gemini-3-flash-preview | 8 | 10 | 18 | $0.10 | $0.005 |
| claude-haiku-4-5 | 24 | 15 | 39 | $0.11 | $0.003 |
| o4-mini | 8 | 6 | 14 | $0.20 | $0.014 |
| gpt-5.4 | 32 | 52 | 84 | $0.26 | $0.003 |
| gemini-2.5-pro | 17 | 21 | 38 | $0.33 | $0.009 |
| claude-sonnet-4-6 | 30 | 48 | 78 | $0.38 | $0.005 |
| claude-opus-4-6 | 40 | 51 | 91 | $0.65 | $0.007 |

## Quality Analysis

python-dotenv served as a "canary" — it's a small, well-maintained package, so we can manually verify whether findings are real. We identified **6 confirmed real issues** via cross-model consensus (found by 4+ models):

| Issue | Models (of 10) | Verdict |
|---|---|---|
| `get_cli_string` shell injection risk | 8 | Real — genuine security concern |
| `test_list` uses builtin `format` instead of `output_format` | 6 | Real — actual code bug |
| Duplicate files (README/CHANGELOG/CONTRIBUTING in docs/) | 6 | Real — maintenance burden |
| Broken mkdocs link (empty href) | 5 | Real — broken documentation |
| Unpinned dev dependencies | 5 | Real — reproducibility issue |
| Incorrect pre-commit command (`precommit` vs `pre-commit`) | 4 | Real — wrong package name |

## Per-Model Quality

| Model | Consensus (of 6) | Noise Level | Cost | Verdict |
|---|---|---|---|---|
| claude-sonnet-4-6 | 6/6 | Low | $0.38 | **Best precision** |
| gpt-5.4 | 5/6 | Low | $0.26 | **Best mid-tier** |
| gpt-5-mini | 5/6 | Low | $0.03 | **Best daily value** |
| claude-opus-4-6 | 6/6 | Moderate | $0.65 | Most findings overall |
| claude-haiku-4-5 | 4/6 | Moderate | $0.11 | Decent but pads with nits |
| gemini-2.5-pro | 3/6 | Low | $0.33 | Poor value vs gpt-5.4 |
| o4-mini | 3/6 | Moderate | $0.20 | Reasoning tokens wasted |
| gemini-2.5-flash | 2/6 | Moderate | $0.07 | Misses too much |
| gemini-3-flash-preview | 2/6 | Low | $0.10 | Preview — fewer findings than 2.5-flash |
| gpt-5-nano | 2/6 | Low | $0.01 | Too shallow |

## Recommended Tiers

Based on quality-adjusted cost:

| Tier | Model | Cost/Run | Rationale |
|------|-------|----------|-----------|
| **Daily** | `gpt-5-mini` | $0.03 | 5/6 consensus issues, minimal noise, cheapest viable model |
| **Deep dive** | `gpt-5.4` | $0.26 | 84 findings total, beats Sonnet quality at 68% the cost |
| **Premium** | `claude-opus-4-6` | $0.65 | Most findings overall, best for maximum depth |

!!! note
    Our initial assumption was "Gemini Flash for daily audits" — the benchmark disproved this. gpt-5-mini is cheaper AND finds more real issues.

## Dropped Models

- **o3**: 0 findings on python-dotenv, 7 on noxaudit at $0.33. Reasoning tokens wasted on non-reasoning task. Removed from supported models.
- **gemini-2.0-flash**: Deprecated. Returns errors in batch API.

## Notes

- All costs include 50% batch API discount
- OpenAI reasoning models (o3, o4-mini) bill hidden reasoning tokens as output — poor cost efficiency for auditing tasks
- python-dotenv's small size makes it a good canary: high finding counts on a clean repo may indicate hallucination
- Different models genuinely find different things — only 6 issues had cross-model consensus, confirming the value of provider rotation
