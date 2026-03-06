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
  Provider:  openai (gpt-5-mini)

  Cost estimate: ~$0.03
    Batch API 50% discount applied.

  Alternatives:
    openai (gpt-5-nano)                      ~$0.01   67% cheaper
    gemini (gemini-2.5-flash)                ~$0.03   similar cost
    anthropic (claude-sonnet-4-6)            ~$0.14   more expensive — deeper analysis

  Monthly estimate: ~$0.90 (assuming daily runs)
  Monthly with gpt-5-nano: ~$0.30
```

The estimate includes:

- File and token counts
- Cost with your current model (including batch discounts)
- Cheaper alternatives with savings percentages
- Monthly projection assuming daily runs
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
  Estimated spend:     $0.36
  Avg per audit:       $0.03
  Projected monthly:   ~$0.90

  Last 5 audits:
    Feb 27  security           gpt-5-mini            42 files    95K tok  $0.03
    Feb 26  patterns,hygiene   gpt-5-mini            67 files   142K tok  $0.04
    ...
```

Cost tracking uses retroactive repricing — stored token counts are recalculated with current pricing, so costs remain accurate even when pricing changes.

## Optimization Strategies

### 1. Use gpt-5-mini for Daily Audits

Our [benchmark](../benchmark.md) showed gpt-5-mini ($0.03/run) hits 5/6 cross-model consensus issues with minimal noise — the best daily value of all 10 models tested:

```yaml
repos:
  - name: my-app
    provider_rotation: [openai]
model: gpt-5-mini
```

Reserve deeper models for periodic deep dives:

```bash
noxaudit run --focus all --provider anthropic --model claude-opus-4-6
```

### 2. Group Focus Areas

Running multiple focus areas together deduplicates source files, saving ~80% on input tokens:

```bash
noxaudit run --focus security,dependencies      # 1 API call
noxaudit run --focus patterns,hygiene,docs       # 1 API call
noxaudit run --focus performance,testing         # 1 API call
```

### 3. Use Batch API

All three providers support batch API with a 50% discount. Use the submit/retrieve workflow:

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
    With pre-pass, claude-sonnet-4-6 stays in standard pricing tier ($3.00/M vs $6.00/M)
```

## Cost Comparison

Estimated cost per audit for a medium-sized codebase (~100 files, ~100K tokens), with batch API discount:

| Model | Per Run | Monthly (daily) |
|-------|---------|-----------------|
| `gpt-5-nano` | ~$0.01 | ~$0.30 |
| `gpt-5-mini` | ~$0.03 | ~$0.90 |
| `gemini-2.5-flash` | ~$0.05 | ~$1.50 |
| `gemini-3-flash-preview` | ~$0.06 | ~$1.80 |
| `claude-haiku-4-5` | ~$0.11 | ~$3.30 |
| `o4-mini` | ~$0.20 | ~$6.00 |
| `gpt-5.4` | ~$0.26 | ~$7.80 |
| `gemini-2.5-pro` | ~$0.33 | ~$9.90 |
| `claude-sonnet-4-6` | ~$0.38 | ~$11.40 |
| `claude-opus-4-6` | ~$0.65 | ~$19.50 |
