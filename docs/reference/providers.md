# Provider Reference

Noxaudit supports three AI providers. You can rotate between them to get different perspectives on your codebase.

## Provider Comparison

| Provider | Model | Input $/M | Output $/M | Context | Batch Discount | Notes |
|----------|-------|-----------|------------|---------|---------------|-------|
| **Anthropic** | `claude-opus-4-6` | $5.00 | $25.00 | 200K | 50% | Deep analysis, tiered pricing above 200K |
| **Anthropic** | `claude-sonnet-4-5` | $3.00 | $15.00 | 200K | 50% | Default. Strong security reasoning |
| **Google** | `gemini-2.5-pro` | $1.25 | $10.00 | 1M | 50% | Large context, tiered pricing above 200K |
| **Google** | `gemini-2.5-flash` | $0.30 | $2.50 | 1M | 50% | Pre-pass triage model |
| **Google** | `gemini-3-flash` | $0.50 | $3.00 | 1M | 50% | Next-gen flash |
| **Google** | `gemini-2.0-flash` | $0.10 | $0.40 | 1M | 50% | Cheapest. Recommended for daily audits |
| **OpenAI** | `gpt-5.2` | $1.75 | $14.00 | 400K | 50% | Latest GPT |
| **OpenAI** | `gpt-5` | $1.25 | $10.00 | 400K | 50% | Previous generation |
| **OpenAI** | `gpt-5-mini` | $0.25 | $2.00 | 400K | 50% | Budget option |
| **OpenAI** | `gpt-5-nano` | $0.05 | $0.40 | 400K | 50% | Cheapest OpenAI option |

## Tiered Pricing

Anthropic and Gemini 2.5 Pro use tiered pricing — input tokens above 200K are billed at 2x the standard rate, and output tokens also switch to the higher tier:

| Model | Standard Input | High-Tier Input (>200K) | Standard Output | High-Tier Output |
|-------|---------------|------------------------|-----------------|-----------------|
| `claude-opus-4-6` | $5.00/M | $10.00/M | $25.00/M | $37.50/M |
| `claude-sonnet-4-5` | $3.00/M | $6.00/M | $15.00/M | $22.50/M |
| `gemini-2.5-pro` | $1.25/M | $2.50/M | $10.00/M | $15.00/M |

!!! tip
    Use `noxaudit estimate` to check if your codebase exceeds the 200K tier threshold. If it does, consider using the [pre-pass](../guides/cost-management.md) to reduce token count, or switch to a Gemini model with a 1M context window.

## Cache Token Pricing (Anthropic)

Anthropic supports prompt caching, which reduces costs on repeated runs:

| Model | Cache Read $/M | Cache Write $/M |
|-------|---------------|-----------------|
| `claude-opus-4-6` | $0.50 | $6.25 |
| `claude-sonnet-4-5` | $0.30 | $3.75 |

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
model: claude-sonnet-4-5-20250929
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
model: gpt-5.2
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
model: gemini-2.0-flash
```

Gemini's 1M context window makes it ideal for large codebases where Anthropic would hit tiered pricing.

## Multi-Provider Rotation

Rotate between providers to get different perspectives:

```yaml
repos:
  - name: my-app
    provider_rotation: [anthropic, openai, gemini]
```

Noxaudit cycles through the list on each run. Different models catch different things — Claude is strong on security reasoning, GPT excels at structured analysis, and Gemini can ingest massive codebases in a single pass.

## Recommended Setup

For most teams, a tiered approach works best:

| Use Case | Provider | Model | Cost/Run |
|----------|----------|-------|----------|
| Daily audits | Gemini | `gemini-2.0-flash` | ~$0.01 |
| Weekly deep dives | Anthropic | `claude-sonnet-4-5` | ~$0.50 |
| Monthly comprehensive | Anthropic | `claude-opus-4-6` | ~$2.00 |
