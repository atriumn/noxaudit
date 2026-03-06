# Benchmark Phase 1 Results

**Date**: 2026-03-06
**Repos**: python-dotenv (34 files, ~52K tokens), noxaudit (88 files, ~126K tokens)
**Focus**: all (7 areas: security, docs, patterns, testing, hygiene, dependencies, performance)
**Method**: Batch API on all providers (50% discount), 1 run per model per repo

## Scorecard

| Model | dotenv | noxaudit | Total | Cost | $/finding |
|---|---:|---:|---:|---:|---:|
| openai/gpt-5-nano | 4 | 6 | 10 | $0.01 | $0.0014 |
| openai/gpt-5-mini | 15 | 24 | 39 | $0.03 | $0.0008 |
| gemini/gemini-2.5-flash | 18 | 16 | 34 | $0.07 | $0.0021 |
| gemini/gemini-3-flash-preview | 8 | 10 | 18 | $0.10 | $0.0054 |
| anthropic/claude-haiku-4-5 | 24 | 15 | 39 | $0.11 | $0.0028 |
| openai/o4-mini | 8 | 6 | 14 | $0.20 | $0.0143 |
| openai/gpt-5.4 | 32 | 52 | 84 | $0.26 | $0.0030 |
| gemini/gemini-2.5-pro | 17 | 21 | 38 | $0.33 | $0.0086 |
| anthropic/claude-sonnet-4-6 | 30 | 48 | 78 | $0.38 | $0.0049 |
| anthropic/claude-opus-4-6 | 40 | 51 | 91 | $0.65 | $0.0071 |

**Total spend**: $2.13 | **Dropped**: o3 (0 findings on dotenv, 7 on noxaudit at $0.33 — useless for this task)

## Quality Analysis (python-dotenv canary)

Cross-model consensus on python-dotenv — issues found by 4+ models are likely real:

| Issue | Models (of 10) | Verdict |
|---|---|---|
| `get_cli_string` shell injection risk | 8 | Real — genuine security concern |
| `test_list` uses builtin `format` instead of `output_format` | 6 | Real — actual code bug |
| Duplicate files (README/CHANGELOG/CONTRIBUTING in docs/) | 6 | Real — maintenance burden |
| Broken mkdocs link (empty href) | 5 | Real — broken documentation |
| Unpinned dev dependencies | 5 | Real — reproducibility issue |
| Incorrect pre-commit command (`precommit` vs `pre-commit`) | 4 | Real — wrong package name |

### Per-model quality assessment

| Model | Consensus (of 6) | Unique real finds | Noise level | Cost | Verdict |
|---|---|---|---|---|---|
| claude-sonnet-4-6 | 6/6 | Good | Low | $0.38 | Best precision |
| gpt-5.4 | 5/6 | Good (os.chdir, unused params) | Low | $0.26 | Best mid-tier |
| gpt-5-mini | 5/6 | Moderate | Low | $0.03 | Best daily value |
| claude-opus-4-6 | 6/6 | Excellent (dict caching, changelog links) | Moderate | $0.65 | Overkill for most uses |
| claude-haiku-4-5 | 4/6 | Low (pads with docstring nits) | Moderate | $0.11 | Decent but noisy |
| gemini-2.5-flash | 2/6 | Mediocre | Moderate | $0.07 | Cheap but misses too much |
| gemini-3-flash-preview | 2/6 | Moderate (broad exception, return type) | Low | $0.10 | Preview — fewer findings than 2.5-flash |
| gemini-2.5-pro | 3/6 | Moderate | Low | $0.33 | Poor value vs gpt-5.4 |
| o4-mini | 3/6 | Low (vague findings) | Moderate | $0.20 | Weak for auditing |
| gpt-5-nano | 2/6 | Low | Low | $0.01 | Too shallow |

## Tiered Strategy Recommendation

Based on quality-adjusted cost:

- **Daily tier**: gpt-5-mini ($0.03/run) — hits 5/6 consensus issues with minimal noise
- **Deep dive tier**: gpt-5.4 ($0.26/run) — 84 findings, beats Sonnet quality at 68% the cost
- **Premium tier**: claude-opus-4-6 ($0.65/run) — most findings, best for maximum depth

Previous assumption of "Gemini Flash for daily" is challenged — gpt-5-mini is cheaper AND finds more real issues.

## Dropped Models

- **o3**: 0 findings on python-dotenv, 7 on noxaudit at $0.33. Reasoning tokens wasted. Removed from pricing.py.
- **gemini-2.0-flash**: Deprecated. Returns error in batch API.
- **gemini-3-flash** (non-preview): Not yet available in API. `gemini-3-flash-preview` used instead.

## Notes

- All costs include 50% batch API discount
- OpenAI reasoning models (o3, o4-mini) bill hidden reasoning tokens as output — poor cost efficiency
- python-dotenv serves as a "canary" — it's small and clean, so high finding counts may indicate hallucination
- Gemini batch jobs took significantly longer to complete than Anthropic/OpenAI
- Raw results in `benchmark/results/{repo}/{provider}-{model}-all-run1.json`
