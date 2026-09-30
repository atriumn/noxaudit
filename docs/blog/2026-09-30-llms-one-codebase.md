---
title: What 10 LLMs found auditing the same codebase, and what it cost
---

# What 10 LLMs found auditing the same codebase, and what it cost

*September 30, 2026*

Noxaudit sends a codebase to an LLM with a prompt that covers seven areas at once: security, docs, patterns, testing, hygiene, dependencies and performance. It gets back a list of findings. The question we keep coming back to is which model to send it to.

In March we ran ten models over two repos and picked a daily model and a deep-dive model from the results. Six months and a lot of model releases later, we ran it again: same repos, same pinned commits, ten current models, four of them carried over from March as a control. The whole run cost $2.81.

## The short version

- **Cheap and good is still gpt-5-mini.** Three cents audits both repos, and it catches 5 of the 6 issues we use as a quality check. Nothing new beat it on price at that quality.
- **Three models caught all six issues:** Claude Opus 5.5, Claude Sonnet 5.5 and Claude Sonnet 4.6. The same number did in March. Frontier models got cheaper per finding, not better on the check.
- **Gemini Flash caught up.** gemini-3.8-flash scores 5/6 where gemini-2.5-flash scored 2/6. It costs six times as much as gpt-5-mini to get there, because it thinks for 14–34K tokens a run.
- **New doesn't mean better.** gpt-6-luna is the cheapest model we've tested and scores 2/6. gemini-3.1-pro-preview costs as much as Sonnet 5.5 and scores 3/6.
- **Running the benchmark turned up three bugs in our own pipeline.** One made a model look like it found nothing. Another undercounted Gemini's cost by up to 3.5x.

## Setup

Two repos, pinned to the same commits as March:

| Repo | Files | Input tokens | Role |
|---|---:|---:|---|
| [python-dotenv](https://github.com/theskumar/python-dotenv) @ `da0c820` | 34 | ~44–69K | Canary: small, clean, well maintained |
| noxaudit @ `1503cbf` | 88 | ~107–173K | Dogfood: our own code |

(Input tokens vary by model because each provider tokenizes differently. Claude's 5.5 models use a newer tokenizer that counts the same files as about 30% more tokens.)

Every model got the same combined seven-area prompt through its provider's batch API, which is half price. We turned off noxaudit's post-processing (LLM dedup and validation) so the counts reflect only the model under test. Each model ran once per repo.

The ten models:

| Provider | New | Carried over from March |
|---|---|---|
| Anthropic | claude-opus-5-5, claude-sonnet-5-5 | claude-sonnet-4-6, claude-haiku-4-5 |
| OpenAI | gpt-6-sol, gpt-6-luna | gpt-5.4, gpt-5-mini |
| Google | gemini-3.8-flash, gemini-3.1-pro-preview | — |

## How we score quality

Counting findings rewards verbosity. A model that reports the same typo in `README.md` and again in its copy at `docs/index.md` gets two points for one problem.

So we use python-dotenv as a canary. It's small enough to check every finding by hand. In March, six issues came up in the output of four or more models, and we confirmed each one against the source:

1. `get_cli_string` builds a shell command without escaping its arguments
2. `test_list` asserts against Python's builtin `format` instead of the `output_format` parameter, so the test checks nothing
3. `README.md`, `CHANGELOG.md` and `CONTRIBUTING.md` are copied by hand into `docs/`, where they'll drift
4. `CONTRIBUTING.md` links to `[mkdocs]()`, which has an empty target
5. Dev dependencies in `requirements.txt` are unpinned
6. `CONTRIBUTING.md` says `uv run precommit install`, but the tool is called `pre-commit`

A model's canary score is how many of those six it finds. We scored by reading each finding's title and description, not by matching keywords: a finding counts only if it names the actual defect.

## Results

Sorted by cost. Costs are at batch prices for both repos combined.

| Model | dotenv | noxaudit | Total | Cost | Canary |
|---|---:|---:|---:|---:|:-:|
| gpt-6-luna | 10 | 18 | 28 | $0.01 | 2/6 |
| gpt-5-mini † | 18 | 16 | 34 | $0.03 | **5/6** |
| claude-haiku-4-5 † | 30 | 16 | 46 | $0.11 | 2/6 |
| gemini-3.8-flash | 20 | 17 | 37 | $0.17 | 5/6 |
| gpt-6-sol | 30 | 70 | 100 | $0.21 | 5/6 |
| gpt-5.4 † | 37 | 51 | 88 | $0.26 | 5/6 |
| claude-sonnet-4-6 † | 31 | 38 | 69 | $0.37 | **6/6** |
| gemini-3.1-pro-preview | 10 | 15 | 25 | $0.39 | 3/6 |
| claude-sonnet-5-5 | 20 | 47 | 67 | $0.39 | **6/6** |
| claude-opus-5-5 | 39 | 81 | 120 | $0.79 | **6/6** |

† Also tested in March.

Which issues each model caught:

| Model | Shell escaping | `test_list` bug | Duplicated docs | Empty link | Unpinned deps | `precommit` |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| claude-opus-5-5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| claude-sonnet-5-5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| claude-sonnet-4-6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gpt-6-sol | ✓ | ✓ |  | ✓ | ✓ | ✓ |
| gpt-5.4 | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| gpt-5-mini | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| gemini-3.8-flash | ✓ | ✓ | ✓ | ✓ |  | ✓ |
| gemini-3.1-pro-preview | ✓ |  | ✓ |  |  | ✓ |
| claude-haiku-4-5 |  | ✓ |  | ✓ |  |  |
| gpt-6-luna | ✓ | ✓ |  |  |  |  |

Nine of ten models flagged the shell-escaping issue. The two lowest scorers failed in opposite ways: Haiku buried the real issues under 30 findings, and gpt-6-luna reported only 10 in total.

## What surprised us

### The control group barely moved

The four March models got the same prompts, repos and commits. Sonnet 4.6, gpt-5.4 and gpt-5-mini scored exactly what they scored in March, and all four cost within a cent of their March price. Haiku slipped from 4/6 to 2/6.

Finding counts moved more: Sonnet 4.6 went from 48 to 38 findings on noxaudit. But in March we ran these models three times each on the same input and saw Sonnet 4.6 range from 39 to 48, and gpt-5.4 from 52 to 84. A single run swings that much on its own. The practical conclusion is that the newer models' results can be compared with March's directly: our own prompt and pipeline changes over the six months didn't shift the baseline.

### More findings mostly means more output

Opus 5.5 found 81 issues in noxaudit. Opus 4.6 found 49 to 54 across three runs in March. Some of that is the model and some is headroom. Opus 5.5 always thinks before answering, and that thinking comes out of the same output budget as the findings. It used 25K output tokens on noxaudit, close to the 28K cap we used in March. We raised the cap for this run. Otherwise we would have been measuring our own limit rather than the model.

The per-copy counting mentioned earlier inflates totals too. gpt-6-sol and gpt-5.4 report issues once per copy when a file is duplicated, which adds 10–20% to their dotenv counts.

### A confident wrong answer from the cheap model

gpt-5-mini is our daily recommendation, and it earned that again. It also produced the run's clearest false positive. `CONTRIBUTING.md` has two wrong commands: `uv ruff check .` and `uv format .`. gpt-5-mini flagged every line that starts with `uv`, claiming that `uv` "is not a standard command and appears to be a typo," and rated it high severity. Six other models found the real problem.

This is why noxaudit validates findings against the source before they reach you, and why we turned that validation off for the benchmark: we wanted to see the raw model output, false positives included.

### Four issues nobody reported in March

With better models, python-dotenv gave up a few more real bugs. Each of these was reported by at least four of the ten models and confirmed in the source:

- The `uv ruff check .` / `uv format .` commands in `CONTRIBUTING.md` aren't real uv subcommands (6 models)
- `requirements.txt` depends on `bumpversion`, which is unmaintained (5)
- `dotenv get KEY` exits with an error when the key exists with an empty value, because of `if stored_value:` (5)
- `DotEnv.dict()` never caches an empty file's result, because of `if self._dict:` (4)

None of them is dramatic, which fits a well-maintained library. They're also the kind of issue a linter can't catch.

### What they found in our own code

We audit noxaudit with noxaudit, so the dogfood repo is a real check on our own code. Issues reported by three or more models that are still present on `main`:

- Our GitHub Action doesn't expose the `openai-api-key` and `google-api-key` inputs that our docs describe (7 models)
- An integration-test fixture uses a `provider:` config key that doesn't exist and is silently ignored (7)
- The security focus area collects `.env` files and sends their contents to the model provider (4)
- The Telegram bot token sits in the request URL, so it can show up in exception messages (4)
- The Action interpolates `${{ inputs.* }}` directly into a shell `run:` block (3)

The third one stings a little, since it's the kind of thing we tell other people to watch for.

## Bugs the benchmark found in the benchmark

Running new models through old code found three bugs in noxaudit's own pipeline:

1. **Silent zero.** `gpt-6.1-sol` isn't available on OpenAI's Batch API. OpenAI rejects the batch at validation and never writes an error file. Our code only checked the error file, so it reported "0 findings" as a success. We now raise on validation failures. `gpt-6-sol` ran in its place.
2. **Missing thinking tokens.** Gemini reports thinking tokens separately from answer tokens but bills both as output. We were recording only the answer tokens, which undercounted Gemini 3.x cost by 1.5–3.5x. gemini-3.8-flash thought for 34K tokens to produce a 3.7K-token answer on dotenv.
3. **Thinking blocks first.** Claude's 5.5 models always think and return a thinking block ahead of the answer. Our parser read the first block of the response and would have found no text.

All three are fixed in the same change as these results.

## What we'd use today

| Use | Model | Both repos | Canary |
|---|---|---:|:-:|
| Daily audits | gpt-5-mini | $0.03 | 5/6 |
| Weekly deep dive | gpt-6-sol | $0.21 | 5/6 |
| Maximum depth | claude-opus-5-5 | $0.79 | 6/6 |

gpt-6-sol hasn't had the repeat-run consistency test from March yet. gpt-5.4, the model it replaces, turned out to be the least stable in that test. If the misses from the 5/6 models matter to you, Sonnet 4.6 ($0.37) and Sonnet 5.5 ($0.39) are the cheapest models with a perfect canary score.

## Caveats

- One run per model per repo. From March's repeat runs, treat counts as ±20% and canary scores as ±1.
- The canary is six issues in one small Python library. It tests whether a model finds real problems, not whether it finds all of them.
- The six canary issues were chosen by consensus among the March models. That favors issues that model family was good at finding. The four new consensus issues are a partial correction.
- Prices are list prices at batch rates as of September 29, 2026.

Raw findings for every run are in [`benchmark/results-phase3/`](https://github.com/atriumn/noxaudit/tree/main/benchmark/results-phase3), with the full write-up in [`benchmark/RESULTS.md`](https://github.com/atriumn/noxaudit/blob/main/benchmark/RESULTS.md). The run config is [`benchmark/corpus-phase3.yml`](https://github.com/atriumn/noxaudit/blob/main/benchmark/corpus-phase3.yml).
