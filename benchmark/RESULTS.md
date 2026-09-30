# Benchmark Results

- [Phase 3 — September 2026 refresh](#phase-3--september-2026-refresh) (current)
- [Phase 1 — March 2026 baseline](#phase-1--march-2026-baseline)
- Phase 2 consistency analysis: [`phase2-consistency.md`](phase2-consistency.md)

## Phase 3 — September 2026 refresh

**Date**: 2026-09-29/30
**Repos**: same as Phase 1, same pinned commits — python-dotenv (`da0c820`, 34 files) and noxaudit (`1503cbf`, 88 files)
**Focus**: all 7 areas in one combined prompt
**Method**: Batch API on all providers, 1 run per model per repo, LLM dedup and validation off (raw model output)
**Config**: [`corpus-phase3.yml`](corpus-phase3.yml) — raw results in `results-phase3/{repo}/`

### Scorecard

Cost is computed from recorded tokens at batch prices (50% off). Sorted by cost.

| Model | dotenv | noxaudit | Total | Cost | $/finding | Canary (of 6) |
|---|---:|---:|---:|---:|---:|:-:|
| openai/gpt-6-luna | 10 | 18 | 28 | $0.01 | $0.0004 | 2/6 |
| openai/gpt-5-mini † | 18 | 16 | 34 | $0.03 | $0.0009 | 5/6 |
| anthropic/claude-haiku-4-5 † | 30 | 16 | 46 | $0.11 | $0.0024 | 2/6 |
| gemini/gemini-3.8-flash | 20 | 17 | 37 | $0.17 | $0.0046 | 5/6 |
| openai/gpt-6-sol | 30 | 70 | 100 | $0.21 | $0.0021 | 5/6 |
| openai/gpt-5.4 † | 37 | 51 | 88 | $0.26 | $0.0030 | 5/6 |
| anthropic/claude-sonnet-4-6 † | 31 | 38 | 69 | $0.37 | $0.0053 | 6/6 |
| gemini/gemini-3.1-pro-preview | 10 | 15 | 25 | $0.39 | $0.0155 | 3/6 |
| anthropic/claude-sonnet-5-5 | 20 | 47 | 67 | $0.39 | $0.0058 | 6/6 |
| anthropic/claude-opus-5-5 | 39 | 81 | 120 | $0.79 | $0.0066 | 6/6 |

† Continuity anchor — same model as Phase 1.

**Total spend**: $2.73 for the 20 scored runs, plus ~$0.08 for one duplicate Anthropic batch
that finished before it could be cancelled. ≈ $2.81.

### Canary: the six Phase 1 consensus issues

Scored by hand from each model's python-dotenv findings (title + description), not by keyword.
A model gets credit only if it identifies the actual defect.

| Model | Shell injection in `get_cli_string` | `test_list` checks builtin `format` | Duplicated docs | Empty mkdocs link | Unpinned dev deps | `precommit` vs `pre-commit` | Score |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| claude-opus-5-5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6/6 |
| claude-sonnet-5-5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6/6 |
| claude-sonnet-4-6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 6/6 |
| gpt-6-sol | ✓ | ✓ | – | ✓ | ✓ | ✓ | 5/6 |
| gpt-5.4 | ✓ | ✓ | ✓ | ✓ | ✓ | – | 5/6 |
| gpt-5-mini | ✓ | ✓ | ✓ | ✓ | ✓ | – | 5/6 |
| gemini-3.8-flash | ✓ | ✓ | ✓ | ✓ | – | ✓ | 5/6 |
| gemini-3.1-pro-preview | ✓ | – | ✓ | – | – | ✓ | 3/6 |
| claude-haiku-4-5 | – | ✓ | – | ✓ | – | – | 2/6 |
| gpt-6-luna | ✓ | ✓ | – | – | – | – | 2/6 |

### New consensus issues

Issues Phase 1 didn't list that 4+ of the 10 Phase 3 models reported, each verified against the source:

| Issue | Models | Verified |
|---|:-:|---|
| `CONTRIBUTING.md` tells you to run `uv ruff check .` / `uv format .` (not uv subcommands; should be `uv run ruff ...`) | 6 | Yes — lines 13–14 |
| `requirements.txt` pulls in unmaintained `bumpversion` | 5 | Yes |
| `dotenv get` exits 1 for a key whose value is the empty string (`if stored_value:`) | 5 | Yes — `cli.py:145` |
| `DotEnv.dict()` cache is bypassed when the file is empty (`if self._dict:`) | 4 | Yes — `main.py:77` |

### False positives worth noting

- **gpt-5-mini** claimed `uv` "is not a standard command and appears to be a typo" and flagged every
  `uv` line in `CONTRIBUTING.md`. The real defect was two specific wrong subcommands; the finding
  was high severity and wrong.
- **claude-haiku-4-5** produced the most dotenv findings of any cheap model (30) but only 2/6 canary
  hits. It rated two changelog dates "high" severity and flagged a deprecated Click `BOOL` type that
  isn't deprecated.
- **gpt-6-sol** and **gpt-5.4** report the same defect once per copy when a file is duplicated
  (`CONTRIBUTING.md` and `docs/contributing.md`), which inflates their dotenv counts by 10–20%.

### Dogfood: what the models said about noxaudit itself

Issues on the pinned noxaudit commit reported by 3+ models and still present on `main` as of this run:

| Issue | Models |
|---|:-:|
| `action/action.yml` doesn't expose `openai-api-key` / `google-api-key` inputs that the docs describe | 7 |
| Integration-test fixture uses a `provider:` repo key that doesn't exist (the real key is `provider_rotation`); `CONTRIBUTING.md`'s sample config has the same kind of drift | 7 |
| Security focus gathers `.env` files and sends their contents to the model provider | 4 |
| Telegram bot token sits in the request URL and can surface in exception messages | 4 |
| `action/action.yml` interpolates `${{ inputs.* }}` straight into a `run:` script | 3 |

### What changed since March

- **Anchors held steady.** Same four models, same repos, same commits: Sonnet 4.6 6/6 → 6/6, gpt-5.4
  5/6 → 5/6, gpt-5-mini 5/6 → 5/6, Haiku 4.5 4/6 → 2/6. Costs were within a cent. Finding counts
  moved (Sonnet 4.6 noxaudit 48 → 38, gpt-5.4 dotenv 32 → 37), but Phase 2 measured run-to-run
  swings of 39–48 and 52–84 for these models, so this is noise, not a regression from prompt changes.
- **Frontier quality got cheaper, not better on the canary.** Three models hit 6/6 in March and three
  do now. Opus 5.5 finds the most (120 vs Opus 4.6's 91) for $0.79 vs $0.65, and 81 on noxaudit
  against Opus 4.6's 49–54 range. Sonnet 5.5 matches Sonnet 4.6's 6/6 at the same price.
- **Gemini Flash caught up.** gemini-3.8-flash scores 5/6 where gemini-2.5-flash scored 2/6. It is
  still 6x the price of gpt-5-mini for the same score, largely because it thinks for 14–34K tokens
  per run.
- **Newest isn't always better.** gpt-6-luna is a third of gpt-5-mini's price and scores 2/6 against 5/6.
  gemini-3.1-pro-preview costs the same as Sonnet 5.5 and scores 3/6.
- **Recommended tiers are unchanged at the cheap end.** gpt-5-mini ($0.03 for both repos, 5/6) is still
  the daily default. For deep dives, gpt-6-sol (5/6, 100 findings, $0.21) replaces gpt-5.4 (5/6, 88,
  $0.26). Opus 5.5 is the premium tier.

### Pipeline changes made for this run

- `claude-opus-5-5` / `claude-sonnet-5-5` always think, and return a thinking block ahead of the text
  block. The Anthropic parser now joins text blocks instead of reading `content[0]`.
- Anthropic `max_tokens` raised from 4096 to 16384 per focus area (capped at 64K), since thinking counts
  against it. Opus 5.5 and Sonnet 5.5 used 25–27K output tokens on noxaudit, just under the old 28,672
  ceiling for 7 focus areas.
- Gemini usage now includes `thoughtsTokenCount`. Before, thinking tokens (billed as output) weren't
  recorded, which understated gemini-3.x cost by 1.5–3.5x. The four Gemini results here were corrected from
  the batch output files.
- An OpenAI batch rejected at validation now raises instead of reporting zero findings.
  `gpt-6.1-sol` isn't available on the Batch API, so it silently "found nothing" until this fix;
  `gpt-6-sol` ran in its place.
- `scripts/benchmark.py` disables LLM dedup so counts reflect the audited model alone.

### Notes

- `cost_usd` in the result JSONs is recomputed from tokens at batch prices. The cost ledger applies the
  batch discount only for Anthropic, so it records OpenAI and Gemini batch runs at double their price.
- Claude 5.5 models use a newer tokenizer: the same files are ~30% more input tokens (242K vs 186K).
- Batch latency ranged from 1 minute (gpt-5-mini on dotenv) to 81 minutes (gpt-5.4 on dotenv).
  Gemini batches, the slowest in March, were the fastest this time (3–5 minutes).
- Single run per model. Phase 2 showed finding sets overlap by only 12–36% run to run, so treat
  per-model counts as ±20% and canary scores as ±1.

## Phase 1 — March 2026 baseline

**Date**: 2026-03-06
**Repos**: python-dotenv (34 files, ~52K tokens), noxaudit (88 files, ~126K tokens)
**Focus**: all (7 areas: security, docs, patterns, testing, hygiene, dependencies, performance)
**Method**: Batch API on all providers (50% discount), 1 run per model per repo

### Scorecard

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

### Quality Analysis (python-dotenv canary)

Cross-model consensus on python-dotenv — issues found by 4+ models are likely real:

| Issue | Models (of 10) | Verdict |
|---|---|---|
| `get_cli_string` shell injection risk | 8 | Real — genuine security concern |
| `test_list` uses builtin `format` instead of `output_format` | 6 | Real — actual code bug |
| Duplicate files (README/CHANGELOG/CONTRIBUTING in docs/) | 6 | Real — maintenance burden |
| Broken mkdocs link (empty href) | 5 | Real — broken documentation |
| Unpinned dev dependencies | 5 | Real — reproducibility issue |
| Incorrect pre-commit command (`precommit` vs `pre-commit`) | 4 | Real — wrong package name |

#### Per-model quality assessment

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

### Tiered Strategy Recommendation

Based on quality-adjusted cost:

- **Daily tier**: gpt-5-mini ($0.03/run) — hits 5/6 consensus issues with minimal noise
- **Deep dive tier**: gpt-5.4 ($0.26/run) — 84 findings, beats Sonnet quality at 68% the cost
- **Premium tier**: claude-opus-4-6 ($0.65/run) — most findings, best for maximum depth

Previous assumption of "Gemini Flash for daily" is challenged — gpt-5-mini is cheaper AND finds more real issues.

### Dropped Models

- **o3**: 0 findings on python-dotenv, 7 on noxaudit at $0.33. Reasoning tokens wasted. Removed from pricing.py.
- **gemini-2.0-flash**: Deprecated. Returns error in batch API.
- **gemini-3-flash** (non-preview): Not yet available in API. `gemini-3-flash-preview` used instead.

### Notes

- All costs include 50% batch API discount
- OpenAI reasoning models (o3, o4-mini) bill hidden reasoning tokens as output — poor cost efficiency
- python-dotenv serves as a "canary" — it's small and clean, so high finding counts may indicate hallucination
- Gemini batch jobs took significantly longer to complete than Anthropic/OpenAI
- Raw results in `benchmark/results/{repo}/{provider}-{model}-all-run1.json`
