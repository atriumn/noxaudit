---
title: Configuration Reference
---

# Configuration Reference

All configuration lives in `noxaudit.yml` in your project root.

## Complete Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `repos` | list | `[]` | List of repositories to audit |
| `repos[].name` | string | — | Repository display name |
| `repos[].path` | string | — | Path to repository root |
| `repos[].provider_rotation` | list[string] | `[gemini]` | AI providers to rotate through |
| `repos[].exclude` | list[string] | `[]` | Additional directory names to exclude from file gathering (see default excludes below) |
| `model` | string | `claude-sonnet-4-6` | AI model to use (any supported model ID) |
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
| `dedup` | mapping | — | Post-audit deduplication settings |
| `dedup.enabled` | bool | `true` | Enable LLM-based finding title normalization |
| `dedup.provider` | string | `gemini` | Provider for dedup calls: `gemini`, `openai`, or `anthropic` |
| `dedup.model` | string | `""` | Model for dedup (empty = provider default) |
| `validate` | mapping | — | Post-audit finding validation settings |
| `validate.enabled` | bool | `false` | Enable LLM validation of findings against source code |
| `validate.provider` | string | `gemini` | Provider for validation calls |
| `validate.model` | string | `""` | Model for validation (empty = provider default) |
| `validate.drop_false_positives` | bool | `true` | Remove findings classified as false positives |
| `validate.min_confidence` | string | `""` | Minimum confidence to keep: `""`, `low`, `medium`, or `high` |
| `chunk_size` | int | `0` | Files per chunk (0 = no chunking). Splits large audits into smaller batches for thorough coverage. |

## Default Excludes

The following paths are **always excluded** from file gathering, regardless of config:

`node_modules`, `.git`, `__pycache__`, `.venv`, `venv`, `dist`, `build`, `site`, `.noxaudit`, `.env`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `benchmark/results`, `htmlcov`, `egg-info`

Use `repos[].exclude` to add project-specific exclusions on top of these:

```yaml
repos:
  - name: my-app
    path: .
    exclude:
      - vendor       # your vendored deps
      - generated    # code-gen output
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

model: claude-sonnet-4-6

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

## Deprecated Keys

The `schedule` and `frames` config keys are deprecated and ignored. If present, a deprecation warning is emitted. Use `--focus` on the command line or set up cron-based scheduling instead. See [Usage Patterns](../guides/scheduling.md) for examples.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API key for Anthropic Claude |
| `OPENAI_API_KEY` | API key for OpenAI GPT |
| `GOOGLE_API_KEY` | API key for Google Gemini |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for notifications |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for notifications |
| `GITHUB_TOKEN` | GitHub token for issue creation |
