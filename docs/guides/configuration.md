# Configuration

Noxaudit is configured through a `noxaudit.yml` file in your project root.

## Getting Started

Copy the example config:

```bash
cp noxaudit.yml.example noxaudit.yml
```

Or create a minimal one:

```yaml
repos:
  - name: my-app
    path: .
```

## Repos

Define the repositories noxaudit should audit:

```yaml
repos:
  - name: my-app
    path: .
    provider_rotation: [anthropic]
    exclude:
      - vendor
      - generated
      - node_modules
```

| Field | Description |
|-------|-------------|
| `name` | Display name for the repo |
| `path` | Path to the repository root (`.` for current directory) |
| `provider_rotation` | AI providers to cycle through on each run |
| `exclude` | Directory names to skip during file gathering |

You can audit multiple repos in a single config:

```yaml
repos:
  - name: backend
    path: ../backend
    provider_rotation: [anthropic]
  - name: frontend
    path: ../frontend
    provider_rotation: [gemini]
```

## Model

Set the AI model to use:

```yaml
model: claude-sonnet-4-5-20250929
```

The model must match the provider. See [Providers](../reference/providers.md) for all available models.

## Schedule

Control which focus areas run on which days:

```yaml
schedule:
  monday: security
  tuesday: patterns
  wednesday: docs
  thursday: hygiene
  friday: performance
  saturday: dependencies
  sunday: off
```

You can use **frame names** to group related focus areas:

```yaml
schedule:
  monday: does_it_work        # → security + testing
  tuesday: does_it_last       # → patterns + hygiene + docs + dependencies
  friday: can_we_prove_it     # → performance
  saturday: off
  sunday: off
```

Or explicitly list multiple areas:

```yaml
schedule:
  monday: [security, dependencies]
  wednesday: [patterns, hygiene, docs]
  friday: [performance, testing]
```

See [Scheduling](scheduling.md) for the full guide.

## Budget

Set cost limits per run:

```yaml
budget:
  max_per_run_usd: 2.00
  alert_threshold_usd: 1.50
```

See [Cost Management](cost-management.md) for details.

## Decisions

Configure decision memory:

```yaml
decisions:
  expiry_days: 90
  path: .noxaudit/decisions.jsonl
```

Decisions expire after `expiry_days` so that previously dismissed findings get re-evaluated periodically. See [Decision Memory](decisions.md) for the full guide.

## Reports

Set the directory for saved reports:

```yaml
reports_dir: .noxaudit/reports
```

Reports are saved as markdown files at `{reports_dir}/{repo}/{date}-{focus}.md`.

## Notifications

Send summaries via Telegram:

```yaml
notifications:
  - channel: telegram
    target: "YOUR_CHAT_ID"
```

Requires `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` environment variables. See [Notifications](notifications.md).

## GitHub Issues

Auto-create GitHub issues for findings:

```yaml
issues:
  enabled: true
  severity_threshold: medium
  labels: [noxaudit]
  assignees: [octocat]
```

See [GitHub Issues](../integrations/github-issues.md).

## Pre-pass

For large codebases, pre-pass uses a cheap model to classify files before the main audit:

```yaml
prepass:
  enabled: true
  threshold_tokens: 600000
  auto: true
```

See [Cost Management](cost-management.md) for details.

## Full Example

See [`noxaudit.yml.example`](https://github.com/atriumn/noxaudit/blob/main/noxaudit.yml.example) or the [Configuration Reference](../reference/configuration.md) for every available option.
