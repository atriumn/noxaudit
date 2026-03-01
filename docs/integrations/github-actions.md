# GitHub Actions

Noxaudit includes a GitHub Action for automated nightly audits with batch API support.

## Basic Workflow

Create `.github/workflows/noxaudit.yml`:

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

## Submit/Retrieve Workflow

For Anthropic's batch API (50% cost savings), use the two-step workflow:

```yaml
name: Noxaudit Audit
on:
  schedule:
    - cron: '0 6 * * *'  # Submit at 6am UTC
  workflow_dispatch:
    inputs:
      focus:
        description: 'Focus area(s)'
        type: string
      mode:
        description: 'Mode: submit or retrieve'
        type: choice
        options: [submit, retrieve]
        default: submit

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: atriumn/noxaudit/action@main
        with:
          mode: ${{ inputs.mode || 'submit' }}
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          focus: ${{ inputs.focus }}
          telegram-bot-token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          telegram-chat-id: ${{ secrets.TELEGRAM_CHAT_ID }}
```

Then schedule a second workflow to retrieve results:

```yaml
name: Noxaudit Retrieve
on:
  schedule:
    - cron: '0 8 * * *'  # Retrieve at 8am UTC (2 hours later)

jobs:
  retrieve:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: atriumn/noxaudit/action@main
        with:
          mode: retrieve
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          telegram-bot-token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          telegram-chat-id: ${{ secrets.TELEGRAM_CHAT_ID }}
```

## Action Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `mode` | `submit` or `retrieve` | no | `submit` |
| `focus` | Focus area(s): name, comma-separated, or `all` | no | `all` |
| `config` | Path to `noxaudit.yml` | no | `noxaudit.yml` |
| `anthropic-api-key` | Anthropic API key | no | — |
| `openai-api-key` | OpenAI API key | no | — |
| `google-api-key` | Google API key | no | — |
| `output-format` | `markdown` or `sarif` | no | `markdown` |
| `upload-sarif` | Upload SARIF to GitHub Code Scanning | no | `false` |
| `telegram-bot-token` | Telegram bot token | no | — |
| `telegram-chat-id` | Telegram chat ID | no | — |

## SARIF Upload

Generate SARIF output and upload to GitHub Code Scanning:

```yaml
- uses: atriumn/noxaudit/action@main
  with:
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    output-format: sarif
    upload-sarif: true
```

This creates alerts in your repository's Security tab. See [SARIF & Code Scanning](sarif.md) for details.

## Artifacts

The action uploads audit reports and SARIF files as workflow artifacts with 30-day retention. Pending batch state is cached between submit and retrieve runs.

## Secrets Setup

Add these secrets to your repository (Settings → Secrets → Actions):

| Secret | Provider |
|--------|----------|
| `ANTHROPIC_API_KEY` | Anthropic |
| `OPENAI_API_KEY` | OpenAI |
| `GOOGLE_API_KEY` | Google Gemini |
| `TELEGRAM_BOT_TOKEN` | Telegram notifications |
| `TELEGRAM_CHAT_ID` | Telegram notifications |
