<p align="center">
  <img src="docs/assets/logo.png" alt="Noxaudit" width="200">
</p>

<h1 align="center">Noxaudit</h1>

<p align="center">
  <a href="https://pypi.org/project/noxaudit/"><img src="https://img.shields.io/pypi/v/noxaudit" alt="PyPI"></a>
  <a href="https://pypi.org/project/noxaudit/"><img src="https://img.shields.io/pypi/pyversions/noxaudit" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

<p align="center">Nightly AI-powered codebase audits with rotating focus areas, multi-provider support, and decision memory.</p>

**The problem**: Codebases drift. Security issues creep in, docs go stale, patterns diverge, dead code accumulates. Linters catch syntax — they miss semantics.

**The solution**: Noxaudit runs a focused AI audit every night, rotating through different concerns. It remembers what you've already reviewed so only genuinely new findings surface.

## How It Works

Tell noxaudit what to audit — it does the rest. Default is all 7 focus areas:

```bash
noxaudit run                              # all focus areas (default)
noxaudit run --focus security             # single area
noxaudit run --focus security,performance # multiple areas (files deduped, ~80% token savings)
```

Each run, Noxaudit:
1. Gathers relevant files from your codebase (deduped across focus areas)
2. Sends them to an AI provider (Claude, GPT, Gemini) with focused prompts
3. Filters results against your decision history (so resolved issues don't resurface)
4. Generates a report and sends you a notification

## Quick Start

### Local CLI

```bash
pip install noxaudit

# Create config (edit to match your project)
cp noxaudit.yml.example noxaudit.yml

# Run a security audit
export ANTHROPIC_API_KEY=sk-...
noxaudit run --focus security

# Run multiple focus areas in one call
noxaudit run --focus security,performance

# Run all focus areas at once
noxaudit run --focus all

# Review a finding and dismiss it
noxaudit decide abc123def456 --action dismiss --reason "This is test code"
```

### GitHub Actions

Add to `.github/workflows/noxaudit.yml`:

```yaml
name: Noxaudit Audit
on:
  schedule:
    - cron: '0 6 * * *'  # 6am UTC daily
  workflow_dispatch:
    inputs:
      focus:
        description: 'Focus area(s) — name, comma-separated, or "all"'
        type: string

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v7

      - run: uv pip install 'noxaudit[openai]'

      - run: noxaudit run --focus ${{ inputs.focus || 'all' }}
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## What It Looks Like

### Running an audit

```
$ noxaudit run --focus security

my-app: 3 new findings
```

```
$ noxaudit report

# Security Audit — my-app
## 2025-01-14

### HIGH: Hardcoded API key in test fixture
**File:** tests/fixtures/config.py:12
The string `sk-proj-abc123` is committed to the repo. Even in test fixtures,
real credentials in source control are a liability.
**Suggestion:** Replace with `os.environ.get("TEST_API_KEY", "sk-test-placeholder")`.

### MEDIUM: SQL string interpolation in query builder
**File:** src/db/queries.py:87
`cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")` is vulnerable
to SQL injection. Use parameterized queries.
**Suggestion:** `cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))`

### MEDIUM: Permissive CORS in production config
**File:** src/config/cors.py:23
`allow_origins=["*"]` in the production config allows any origin.
**Suggestion:** Restrict to known domains before shipping.

---
3 new findings (1 high, 2 medium) | 5 findings suppressed by decisions
```

### Telegram notification

```
Security Audit — my-app
3 new findings: 1 high, 2 medium

Hardcoded API key in test fixture
   tests/fixtures/config.py
SQL string interpolation in query builder
   src/db/queries.py
Permissive CORS in production config
   src/config/cors.py

5 previous findings still resolved
```

### MCP server (Cursor / Claude / Windsurf)

Add to your editor's MCP config, then ask your AI assistant directly:

```
You: What security findings are open in this repo?

Claude: I found 3 open security findings:

[HIGH] [security] a1b2c3d4 — Hardcoded API key in test fixture
  Location: tests/fixtures/config.py:12
  A real API key `sk-proj-abc123` is committed in a test fixture.
  Suggestion: Use an environment variable or a clearly fake placeholder.

[MEDIUM] [security] e5f6g7h8 — SQL string interpolation in query builder
  Location: src/db/queries.py:87
  f-string used in cursor.execute() — vulnerable to SQL injection.
  Suggestion: Switch to parameterized queries.
  ...
```

### `.noxaudit/` directory layout

```
.noxaudit/
├── decisions.jsonl          # Team decisions — commit this
├── latest-findings.json     # Latest findings (for MCP server)
└── reports/
    └── my-app/
        ├── 2025-01-13-security.md
        ├── 2025-01-14-patterns.md
        └── 2025-01-15-docs.md
```

## Configuration

Create a `noxaudit.yml` in your project root. See [noxaudit.yml.example](noxaudit.yml.example) for all options.

### Key Options

| Option | Description | Default |
|--------|-------------|---------|
| `repos[].path` | Path to repository | `.` |
| `repos[].provider_rotation` | AI providers to rotate through (see [Providers](#providers) section) | `[anthropic]` |
| `model` | AI model to use (see [Providers](#providers) section for provider-specific setup) | `claude-sonnet-4-6` |
| `providers.<name>.model` | Override model for a specific provider (e.g., `providers.openai.model`) | (uses global `model`) |
| `prepass` | Pre-pass filtering configuration (see [Providers](#providers) section) | disabled |
| `decisions.expiry_days` | Days before a decision expires | `90` |
| `notifications` | Where to send summaries | (none) |

## Focus Areas

| Area | What It Checks |
|------|---------------|
| **security** | Secrets, injection vulnerabilities, permissions, dependency CVEs |
| **testing** | Missing coverage, edge cases, test quality, flaky tests |
| **docs** | README accuracy, stale comments, API doc drift |
| **patterns** | Naming conventions, architecture consistency, duplicated logic |
| **performance** | Missing caching, expensive patterns, bundle size |
| **hygiene** | Dead code, orphaned files, stale config |
| **dependencies** | Outdated packages, security advisories |

## Decision Memory

When noxaudit finds something you've already addressed, you can record a decision:

```bash
# "We fixed this"
noxaudit decide abc123 --action accept --reason "Fixed in PR #42"

# "This is fine, stop flagging it"
noxaudit decide def456 --action dismiss --reason "Test fixture, not real credentials"

# "We know, it's on purpose"
noxaudit decide ghi789 --action intentional --reason "Intentionally permissive CORS for dev"
```

Decisions are stored in `.noxaudit/decisions.jsonl` and fed to future runs. A finding won't resurface unless:
- The file it's in changes
- The decision expires (default: 90 days)

Commit your decisions file to share across the team.

Reports are saved as markdown in `.noxaudit/reports/{repo}/{date}-{focus}.md`.

## Providers

Noxaudit supports three AI providers with 10 models. We [benchmarked all of them](https://noxaudit.com/benchmark/) against real repos to find which ones actually deliver.

**Benchmark-informed tiers:**

| Tier | Model | Cost/Run | Why |
|------|-------|----------|-----|
| **Daily** | `gpt-5-mini` | ~$0.03 | 5/6 consensus issues, minimal noise — best value |
| **Deep dive** | `gpt-5.4` | ~$0.26 | 84 findings, beats Sonnet at 68% the cost |
| **Premium** | `claude-opus-4-6` | ~$0.65 | Most findings overall, maximum depth |

### Basic Setup

Set your API keys:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GOOGLE_API_KEY=...
```

Install optional provider dependencies (Anthropic is built-in):
```bash
pip install 'noxaudit[openai]'   # OpenAI
pip install 'noxaudit[google]'   # Gemini
```

### Example: Multi-Provider Setup with Pre-pass

Rotate between providers and enable pre-pass filtering:

```yaml
repos:
  - name: my-app
    path: .
    provider_rotation: [anthropic, gemini, openai]
    exclude: [vendor, generated, node_modules]

# Use Anthropic by default
model: claude-sonnet-4-6

# Optional: Set provider-specific models (overrides `model` for that provider)
providers:
  gemini:
    model: gemini-2.5-flash
  openai:
    model: gpt-5-mini

# Pre-pass: automatically filter large repos before sending to AI
prepass:
  enabled: true
  threshold_tokens: 600_000  # Auto-enable if codebase exceeds this
  auto: true
```

Each audit will cycle through `provider_rotation`: first run uses Anthropic (with default model), second uses Gemini (with `gemini-2.5-flash`), third uses OpenAI (with `gpt-5-mini`), then repeat. Use `providers.<name>.model` to set provider-specific models that override the global `model` setting. See [Key Options](#key-options) for all configuration.

### Supported Models

| Provider | Model | Input/M | Output/M | Batch |
|----------|-------|---------|----------|-------|
| **Anthropic** | `claude-opus-4-6` | $5.00 | $25.00 | 50% off |
| **Anthropic** | `claude-sonnet-4-6` | $3.00 | $15.00 | 50% off |
| **Anthropic** | `claude-haiku-4-5` | $1.00 | $5.00 | 50% off |
| **Google** | `gemini-2.5-pro` | $1.25 | $10.00 | 50% off |
| **Google** | `gemini-3-flash-preview` | $0.50 | $3.00 | 50% off |
| **Google** | `gemini-2.5-flash` | $0.30 | $2.50 | 50% off |
| **OpenAI** | `gpt-5.4` | $2.50 | $15.00 | 50% off |
| **OpenAI** | `o4-mini` | $1.10 | $4.40 | 50% off |
| **OpenAI** | `gpt-5-mini` | $0.25 | $2.00 | 50% off |
| **OpenAI** | `gpt-5-nano` | $0.05 | $0.40 | 50% off |

Full pricing details, tiered rates, and cache pricing in the [Provider Reference](https://noxaudit.com/reference/providers/).

## License

MIT
