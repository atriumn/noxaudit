# Provider Reference

Noxaudit supports three AI providers. You can rotate between them to get different perspectives on your codebase.

## Provider Comparison

| Provider | Model | Input $/M | Output $/M | Context | Batch Discount | Notes |
|----------|-------|-----------|------------|---------|---------------|-------|
| **Anthropic** | `claude-opus-4-6` | $5.00 | $25.00 | 200K | 50% | Most findings, best depth. Tiered pricing above 200K |
| **Anthropic** | `claude-sonnet-4-6` | $3.00 | $15.00 | 200K | 50% | Best precision (6/6 consensus). Tiered pricing above 200K |
| **Anthropic** | `claude-haiku-4-5` | $1.00 | $5.00 | 200K | 50% | Budget Anthropic option |
| **Google** | `gemini-2.5-pro` | $1.25 | $10.00 | 1M | 50% | Large context, tiered pricing above 200K |
| **Google** | `gemini-3-flash-preview` | $0.50 | $3.00 | 1M | 50% | Latest Gemini flash (preview) |
| **Google** | `gemini-2.5-flash` | $0.30 | $2.50 | 1M | 50% | Pre-pass triage model |
| **OpenAI** | `gpt-5.4` | $2.50 | $15.00 | 1M | 50% | Best mid-tier value (84 findings in benchmark) |
| **OpenAI** | `o4-mini` | $1.10 | $4.40 | 200K | 50% | Reasoning model — poor cost efficiency for auditing |
| **OpenAI** | `gpt-5-mini` | $0.25 | $2.00 | 400K | 50% | Best daily value ($0.03/run, 5/6 consensus) |
| **OpenAI** | `gpt-5-nano` | $0.05 | $0.40 | 400K | 50% | Cheapest — too shallow for most use cases |

## Benchmark-Informed Recommendations

We benchmarked all 10 models against two repos (python-dotenv + noxaudit itself) and validated quality using cross-model consensus. See the full [Benchmark Results](../benchmark.md) for details.

**Key findings:**

- **gpt-5-mini** ($0.03/run) hits 5/6 consensus issues with minimal noise — best daily value
- **gpt-5.4** ($0.26/run) found 84 total findings and beats Sonnet quality at 68% the cost
- **claude-opus-4-6** ($0.65/run) found the most findings overall — best for maximum depth
- **claude-sonnet-4-6** ($0.38/run) hit 6/6 consensus with the lowest noise — best precision
- **Gemini models** had lower consensus scores (2-3/6) but offer 1M context for large codebases
- **o3** was dropped entirely (0 findings on the canary repo)

## Tiered Pricing

Anthropic and Gemini 2.5 Pro use tiered pricing — input tokens above 200K are billed at 2x the standard rate, and output tokens also switch to the higher tier:

| Model | Standard Input | High-Tier Input (>200K) | Standard Output | High-Tier Output |
|-------|---------------|------------------------|-----------------|-----------------|
| `claude-opus-4-6` | $5.00/M | $10.00/M | $25.00/M | $37.50/M |
| `claude-sonnet-4-6` | $3.00/M | $6.00/M | $15.00/M | $22.50/M |
| `gemini-2.5-pro` | $1.25/M | $2.50/M | $10.00/M | $15.00/M |

!!! tip
    Use `noxaudit estimate` to check if your codebase exceeds the 200K tier threshold. If it does, consider using the [pre-pass](../guides/cost-management.md) to reduce token count, or switch to a Gemini model with a 1M context window.

## Cache Token Pricing (Anthropic)

Anthropic supports prompt caching, which reduces costs on repeated runs:

| Model | Cache Read $/M | Cache Write $/M |
|-------|---------------|-----------------|
| `claude-opus-4-6` | $0.50 | $6.25 |
| `claude-sonnet-4-6` | $0.30 | $3.75 |
| `claude-haiku-4-5` | $0.10 | $1.25 |

Cache read tokens cost 10% of standard input price. Cache write tokens cost 125% of standard input price.

## Setup per Provider

### Anthropic

```bash
pip install noxaudit  # included by default
export ANTHROPIC_API_KEY=sk-ant-...
```

```yaml
repos:
  - name: my-app
    provider_rotation: [anthropic]
model: claude-sonnet-4-6
```

Anthropic uses the batch API by default, which provides a 50% discount. Use `noxaudit submit` / `noxaudit retrieve` for the batch workflow.

### OpenAI

```bash
pip install 'noxaudit[openai]'
export OPENAI_API_KEY=sk-...
```

```yaml
repos:
  - name: my-app
    provider_rotation: [openai]
model: gpt-5-mini
```

### Google Gemini

```bash
pip install 'noxaudit[google]'
export GOOGLE_API_KEY=...
```

```yaml
repos:
  - name: my-app
    provider_rotation: [gemini]
model: gemini-2.5-flash
```

Gemini's 1M context window makes it ideal for large codebases where Anthropic would hit tiered pricing.

## Multi-Provider Rotation

Rotate between providers to get different perspectives:

```yaml
repos:
  - name: my-app
    provider_rotation: [anthropic, openai, gemini]
```

Noxaudit cycles through the list on each run. Different models catch different things — our benchmark showed only 6 issues had consensus across models, confirming that rotation improves coverage.

## Recommended Setup

Based on our [benchmark results](../benchmark.md), a tiered approach works best:

| Use Case | Provider | Model | Cost/Run | Why |
|----------|----------|-------|----------|-----|
| Daily audits | OpenAI | `gpt-5-mini` | ~$0.03 | 5/6 consensus, minimal noise |
| Deep dives | OpenAI | `gpt-5.4` | ~$0.26 | 84 findings, beats Sonnet at 68% cost |
| Premium analysis | Anthropic | `claude-opus-4-6` | ~$0.65 | Most findings, best for max depth |
