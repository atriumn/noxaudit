# Usage Patterns

Noxaudit is a simple tool: you tell it what to audit, it audits. The `--focus` flag controls which focus areas to run. With no `--focus`, it defaults to all 7 areas.

This guide shows common usage patterns from on-demand runs to automated CI schedules.

## On-Demand

Run a specific audit whenever you need it:

```bash
# Security audit
noxaudit run --focus security

# Multiple focus areas in one API call (files deduplicated)
noxaudit run --focus security,performance

# All 7 focus areas at once
noxaudit run --focus all

# Default: all focus areas
noxaudit run
```

## Full Audit

Run all focus areas in a single API call. Source files are gathered and deduplicated across all areas, saving ~80% on input tokens compared to running each separately:

```bash
noxaudit run
# or equivalently:
noxaudit run --focus all
```

## Daily CI with GitHub Actions

Run a full audit every morning:

```yaml
name: Noxaudit Audit
on:
  schedule:
    - cron: '0 6 * * *'  # 6am UTC daily

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: atriumn/noxaudit/action@main
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

See [GitHub Actions](../integrations/github-actions.md) for the full workflow including batch API support and SARIF upload.

## Weekly Rotation via Cron

Spread focus areas across the week using separate cron entries:

```bash
# Monday: security
0 6 * * 1 cd /path/to/project && noxaudit run --focus security

# Wednesday: patterns, hygiene, docs
0 6 * * 3 cd /path/to/project && noxaudit run --focus patterns,hygiene,docs

# Friday: performance, dependencies
0 6 * * 5 cd /path/to/project && noxaudit run --focus performance,dependencies
```

Or with GitHub Actions using multiple workflow files or workflow dispatch.

## Tiered Approach

Use a cheap model for daily monitoring and a more capable model for periodic deep dives:

```bash
# Daily: Gemini Flash (~$0.01/run)
noxaudit run --provider gemini

# Monthly deep dive: Claude (~$0.14/run)
noxaudit run --focus all --provider anthropic
```

See [Cost Management](cost-management.md) for model pricing comparisons.

## Combined Focus for Token Savings

When multiple focus areas run together, source files are sent once instead of repeated per area:

| Strategy | API Calls | Token Multiplier |
|----------|-----------|-----------------|
| One area per run | N runs | 1x per area |
| Grouped (2-3 areas) | fewer runs | ~1x total (files deduped) |
| All at once | 1 run | ~1x total |

The trade-off: combined runs produce more findings per notification, which can be harder to triage. Many teams find 2-3 areas per call to be the sweet spot.

```bash
# Group related areas
noxaudit run --focus security,dependencies
noxaudit run --focus patterns,hygiene,docs
```
