# Configuration Reference

All configuration lives in `noxaudit.yml` in your project root.

## Complete Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `repos` | list | `[]` | List of repositories to audit |
| `repos[].name` | string | — | Repository display name |
| `repos[].path` | string | — | Path to repository root |
| `repos[].provider_rotation` | list[string] | `[gemini]` | AI providers to rotate through |
| `repos[].exclude` | list[string] | `[]` | Directory names to exclude from file gathering |
| `schedule` | mapping | see below | Day-of-week to focus area(s) mapping |
| `schedule.<day>` | string \| list | — | Focus area name, frame name, comma-separated list, `all`, or `off` |
| `frames` | mapping | `{}` | Per-frame focus area overrides |
| `frames.<frame>.<focus>` | bool | `true` | Enable/disable a focus area within a frame |
| `model` | string | `claude-sonnet-4-5-20250929` | AI model to use (any supported model ID) |
| `budget` | mapping | — | Cost control settings |
| `budget.max_per_run_usd` | float | `2.00` | Maximum cost per audit run in USD |
| `budget.alert_threshold_usd` | float | `1.50` | Cost threshold that triggers a warning |
| `decisions` | mapping | — | Decision memory settings |
| `decisions.expiry_days` | int | `90` | Days before a decision expires |
| `decisions.path` | string | `.noxaudit/decisions.jsonl` | Path to decision storage file |
| `reports_dir` | string | `.noxaudit/reports` | Directory for saved reports |
| `notifications` | list | `[]` | Notification channel configurations |
| `notifications[].channel` | string | `telegram` | Notification channel type |
| `notifications[].target` | string | `""` | Channel-specific target (e.g., Telegram chat ID) |
| `notifications[].webhook` | string | `""` | Webhook URL (for webhook-based channels) |
| `issues` | mapping | — | GitHub issue creation settings |
| `issues.enabled` | bool | `false` | Enable auto-creation of GitHub issues |
| `issues.severity_threshold` | string | `medium` | Minimum severity for issue creation: `low`, `medium`, or `high` |
| `issues.labels` | list[string] | `[noxaudit]` | Labels to apply to created issues |
| `issues.assignees` | list[string] | `[]` | GitHub users to assign to created issues |
| `issues.repository_url` | string | `https://github.com/atriumn/noxaudit` | Repository URL for issue footer links |
| `prepass` | mapping | — | Pre-pass file filtering settings |
| `prepass.enabled` | bool | `false` | Enable pre-pass file classification |
| `prepass.threshold_tokens` | int | `600000` | Token count above which pre-pass activates |
| `prepass.auto` | bool | `true` | Auto-enable pre-pass when token count exceeds threshold |

## Default Schedule

When no `schedule` is specified, noxaudit uses:

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

## Example Configuration

```yaml
repos:
  - name: my-app
    path: .
    provider_rotation: [anthropic]
    exclude:
      - vendor
      - generated

schedule:
  monday: does_it_work        # → security + testing
  tuesday: does_it_last       # → patterns + hygiene + docs + dependencies
  wednesday: does_it_work
  thursday: does_it_last
  friday: can_we_prove_it     # → performance
  saturday: off
  sunday: off

model: claude-sonnet-4-5-20250929

budget:
  max_per_run_usd: 2.00
  alert_threshold_usd: 1.50

decisions:
  expiry_days: 90
  path: .noxaudit/decisions.jsonl

reports_dir: .noxaudit/reports

notifications:
  - channel: telegram
    target: "YOUR_CHAT_ID"

issues:
  enabled: false
  severity_threshold: medium
  labels: [noxaudit]
  assignees: []
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API key for Anthropic Claude |
| `OPENAI_API_KEY` | API key for OpenAI GPT |
| `GOOGLE_API_KEY` | API key for Google Gemini |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for notifications |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for notifications |
| `GITHUB_TOKEN` | GitHub token for issue creation |
