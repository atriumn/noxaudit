# Cost Management

Noxaudit is designed to be cheap enough to run daily. This guide covers estimation, budget controls, cost tracking, and optimization strategies.

## Estimating Cost

Before running an audit, estimate the cost locally — no API key needed:

```bash
noxaudit estimate --focus security
```

```
  my-app — security

  Files:     42 files, 87K tokens
  Provider:  anthropic (claude-sonnet-4-5)

  Cost estimate: ~$0.14
    Batch API 50% discount applied.

  Alternatives:
    gemini (gemini-2.0-flash)                ~$0.01   93% cheaper — recommended for daily audits
    openai (gpt-5-nano)                      ~$0.01   95% cheaper
    gemini (gemini-2.5-flash)                ~$0.03   79% cheaper

  Monthly estimate: ~$0.84 (6 runs/week at current schedule)
  Monthly with gemini-2.0-flash: ~$0.06
```

The estimate includes:

- File and token counts
- Cost with your current model (including batch discounts)
- Cheaper alternatives with savings percentages
- Monthly projection based on your schedule
- Pre-pass potential for large codebases

## Budget Controls

Set maximum cost per run and alert thresholds:

```yaml
budget:
  max_per_run_usd: 2.00
  alert_threshold_usd: 1.50
```

## Cost Tracking

The `status` command shows cost history for the last 30 days:

```bash
noxaudit status
```

```
Cost (last 30 days):
  Audits run:          12
  Total input tokens:  1.2M
  Total output tokens: 96K
  Cache read tokens:   800K
  Cache write tokens:  400K
  Cache savings:       40.0% served from cache
  Estimated spend:     $1.68
  Avg per audit:       $0.14
  Projected monthly:   ~$4.20

  Last 5 audits:
    Feb 27  security           claude-sonnet-4-5     42 files    95K tok  $0.14
    Feb 26  patterns,hygiene   claude-sonnet-4-5     67 files   142K tok  $0.21
    ...
```

Cost tracking uses retroactive repricing — stored token counts are recalculated with current pricing, so costs remain accurate even when pricing changes.

## Optimization Strategies

### 1. Use Gemini for Daily Audits

Gemini 2.0 Flash costs ~$0.01 per run vs ~$0.14 for Claude Sonnet. For daily monitoring, the cheaper model catches most issues:

```yaml
repos:
  - name: my-app
    provider_rotation: [gemini]
model: gemini-2.0-flash
```

Reserve Claude for periodic deep dives:

```bash
noxaudit run --focus all --provider anthropic
```

### 2. Group Focus Areas

Running multiple focus areas together deduplicates source files, saving ~80% on input tokens:

```yaml
schedule:
  monday: [security, dependencies]      # 1 API call
  wednesday: [patterns, hygiene, docs]   # 1 API call
  friday: [performance, testing]         # 1 API call
```

### 3. Use Batch API

Anthropic's batch API provides a 50% discount. Use the submit/retrieve workflow:

```bash
noxaudit submit --focus security
# ... wait ...
noxaudit retrieve
```

The GitHub Actions workflow uses this pattern automatically.

### 4. Exclude Irrelevant Directories

Reduce file count by excluding generated code, vendor directories, and other noise:

```yaml
repos:
  - name: my-app
    path: .
    exclude:
      - vendor
      - node_modules
      - generated
      - dist
      - build
      - .git
```

### 5. Pre-pass Triage

For large codebases that exceed Anthropic's 200K token tier threshold, the pre-pass uses a cheap model (Gemini Flash) to classify files before the main audit:

```yaml
prepass:
  enabled: true
  threshold_tokens: 600000
```

The pre-pass classifies each file as:

| Priority | Treatment |
|----------|-----------|
| **High** | Full file content sent to main audit |
| **Medium** | Code snippets (key functions, classes) |
| **Low** | Structural map only (file outline) |
| **Skip** | Excluded entirely |

This typically reduces token count by ~50%, keeping the main audit under the tiered pricing threshold.

When `auto: true` (default), the pre-pass activates automatically when token count exceeds `threshold_tokens`.

The `estimate` command shows pre-pass savings when applicable:

```
  Pre-pass estimate:
    Gemini Flash triage: ~$0.02
    Expected reduction: 450K → ~200K tokens (high: 12 files, medium: 25, low/skip: 45)
    With pre-pass, claude-sonnet-4-5 stays in standard pricing tier ($3.00/M vs $6.00/M)
```

## Cost Comparison

Estimated cost per audit for a medium-sized codebase (~100 files, ~100K tokens):

| Model | Per Run | Monthly (6x/week) |
|-------|---------|-------------------|
| `gemini-2.0-flash` | ~$0.01 | ~$0.26 |
| `gpt-5-nano` | ~$0.01 | ~$0.26 |
| `gpt-5-mini` | ~$0.04 | ~$1.04 |
| `gemini-2.5-flash` | ~$0.05 | ~$1.30 |
| `gemini-2.5-pro` | ~$0.19 | ~$4.94 |
| `claude-sonnet-4-5` | ~$0.14 | ~$3.64 |
| `gpt-5.2` | ~$0.22 | ~$5.72 |
| `claude-opus-4-6` | ~$0.38 | ~$9.88 |

All Anthropic costs include 50% batch API discount.
