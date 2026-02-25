# Noxaudit

[![PyPI](https://img.shields.io/pypi/v/noxaudit)](https://pypi.org/project/noxaudit/)
[![Python 3.11+](https://img.shields.io/pypi/pyversions/noxaudit)](https://pypi.org/project/noxaudit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Nightly AI-powered codebase audits with rotating focus areas, multi-provider support, and decision memory.

**The problem**: Codebases drift. Security issues creep in, docs go stale, patterns diverge, dead code accumulates. Linters catch syntax — they miss semantics.

**The solution**: Noxaudit runs a focused AI audit every night, rotating through different concerns. It remembers what you've already reviewed so only genuinely new findings surface.

## How It Works

```
Mon: Security → Tue: Patterns → Wed: Docs → Thu: Hygiene → Fri: Performance → Sat: Dependencies
```

You can also group multiple focus areas into a single API call to save on input tokens (source files are sent once instead of repeated per focus area):

```yaml
# ~80% savings on input tokens vs running each separately
schedule:
  monday: [security, dependencies]
  wednesday: [patterns, hygiene, docs]
  friday: [performance, testing]
```

Or run everything at once: `noxaudit run --focus all`

Each night, Noxaudit:
1. Picks today's focus area(s) from the schedule
2. Gathers relevant files from your codebase (deduped across focus areas)
3. Sends them to an AI provider (Claude, GPT, Gemini) with a focused prompt
4. Filters results against your decision history (so resolved issues don't resurface)
5. Generates a report and sends you a notification

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

# See the schedule
noxaudit schedule

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

      - uses: atriumn/noxaudit/action@main
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          focus: ${{ inputs.focus }}
          telegram-bot-token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          telegram-chat-id: ${{ secrets.TELEGRAM_CHAT_ID }}
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

### 🔴 HIGH: Hardcoded API key in test fixture
**File:** tests/fixtures/config.py:12
The string `sk-proj-abc123` is committed to the repo. Even in test fixtures,
real credentials in source control are a liability.
**Suggestion:** Replace with `os.environ.get("TEST_API_KEY", "sk-test-placeholder")`.

### 🟡 MEDIUM: SQL string interpolation in query builder
**File:** src/db/queries.py:87
`cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")` is vulnerable
to SQL injection. Use parameterized queries.
**Suggestion:** `cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))`

### 🟡 MEDIUM: Permissive CORS in production config
**File:** src/config/cors.py:23
`allow_origins=["*"]` in the production config allows any origin.
**Suggestion:** Restrict to known domains before shipping.

---
3 new findings (1 high, 2 medium) | 5 findings suppressed by decisions
```

### Telegram notification

```
🔒 Security Audit — my-app
3 new findings: 🔴 1 high, 🟡 2 medium

🔴 Hardcoded API key in test fixture
   tests/fixtures/config.py
🟡 SQL string interpolation in query builder
   src/db/queries.py
🟡 Permissive CORS in production config
   src/config/cors.py

✅ 5 previous findings still resolved
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
| `schedule` | Day-of-week to focus area(s) — single name, list, or `all` | Security Mon, Patterns Tue, ... |
| `model` | AI model to use (see [Providers](#providers) section for provider-specific setup) | `claude-sonnet-4-5-20250929` |
| `providers.<name>.model` | Override model for a specific provider (e.g., `providers.gemini.model`) | (uses global `model`) |
| `prepass` | Pre-pass filtering configuration (see [Providers](#providers) section) | disabled |
| `decisions.expiry_days` | Days before a decision expires | `90` |
| `notifications` | Where to send summaries | (none) |

## Focus Areas

| Area | What It Checks |
|------|---------------|
| **security** | Secrets, injection vulnerabilities, permissions, dependency CVEs |
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

Noxaudit supports multiple AI providers. Rotate between them to get different perspectives, or choose one per your preference and budget.

**Provider strengths:**

| Provider | Strength | Best For |
|----------|----------|----------|
| **Anthropic** | Stronger security reasoning, native batch API support | Security-focused audits, batch processing |
| **Gemini** | Larger context window, lower cost | Large repos, cost optimization |
| **OpenAI** | Fast, structured analysis | Quick turnarounds, diverse analysis |

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
model: claude-sonnet-4-5-20250929

# Optional: Set provider-specific models (overrides `model` for that provider)
providers:
  gemini:
    model: gemini-2.0-flash
  openai:
    model: gpt-5-mini

# Pre-pass: automatically filter large repos before sending to AI
prepass:
  enabled: true
  threshold_tokens: 600_000  # Auto-enable if codebase exceeds this
  auto: true

# Rotate through different providers each audit run
schedule:
  monday: does_it_work      # security + testing
  wednesday: does_it_work   # second run with different provider
  friday: can_we_prove_it   # performance check
```

Each audit will cycle through `provider_rotation`: first run uses Anthropic (with default model), second uses Gemini (with `gemini-2.0-flash`), third uses OpenAI (with `gpt-5-mini`), then repeat. Use `providers.<name>.model` to set provider-specific models that override the global `model` setting. See [Key Options](#key-options) for all configuration.

### Supported Models

| Provider | Model | Input/M | Output/M |
|----------|-------|---------|----------|
| **Anthropic** | `claude-sonnet-4-5-20250929` | $3.00 | $15.00 |
| **OpenAI** | `gpt-5.2` | $1.75 | $7.00 |
| **OpenAI** | `gpt-5-mini` | $0.25 | $1.00 |
| **OpenAI** | `gpt-5-nano` | $0.05 | $0.15 |
| **Gemini** | `gemini-2.0-flash` | $0.10 | $0.40 |

## License

MIT
