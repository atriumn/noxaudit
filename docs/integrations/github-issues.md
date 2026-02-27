# GitHub Issues

Noxaudit can automatically create GitHub issues for audit findings, making it easy to track and assign remediation work.

## Setup

Enable issue creation in `noxaudit.yml`:

```yaml
issues:
  enabled: true
  severity_threshold: medium
  labels: [noxaudit]
  assignees: [octocat]
```

Set the `GITHUB_TOKEN` environment variable (automatically available in GitHub Actions):

```bash
export GITHUB_TOKEN=ghp_...
```

## Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `issues.enabled` | bool | `false` | Enable auto-creation of issues |
| `issues.severity_threshold` | string | `medium` | Minimum severity: `low`, `medium`, or `high` |
| `issues.labels` | list | `[noxaudit]` | Labels applied to created issues |
| `issues.assignees` | list | `[]` | GitHub users to assign |
| `issues.repository_url` | string | — | Repository URL for issue footer |

## How It Works

After an audit completes, noxaudit:

1. Checks each finding against the severity threshold
2. Searches for existing issues with the same finding ID (to avoid duplicates)
3. Creates new issues for findings that don't have one yet
4. Applies configured labels and assignees

### Deduplication

Each issue includes a marker comment with the finding ID. Before creating a new issue, noxaudit checks if an issue with that marker already exists. This prevents duplicate issues across runs.

### Rate Limiting

Issue creation includes a 1-second delay between API calls to avoid hitting GitHub's rate limits.

## Issue Format

Created issues include:

- **Title**: Finding title with severity indicator
- **Body**: Full finding description, affected file, and suggested fix
- **Labels**: Configured labels (default: `noxaudit`)
- **Assignees**: Configured assignees
- **Footer**: Link back to the noxaudit repository

## GitHub Actions

In GitHub Actions, the `GITHUB_TOKEN` is automatically available:

```yaml
jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      issues: write
    steps:
      - uses: actions/checkout@v4

      - uses: atriumn/noxaudit/action@main
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Make sure the job has `issues: write` permission.
