# CLI Reference

Noxaudit provides 9 commands. All commands accept a `--config` / `-c` flag to specify the path to `noxaudit.yml` (defaults to the current directory).

```bash
noxaudit [--config PATH] <command> [options]
```

## `run`

Run an audit synchronously. Sends files to the AI provider, waits for results, and prints a summary.

```bash
noxaudit run [options]
```

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--repo` | `-r` | Audit a specific repo | all repos |
| `--focus` | `-f` | Focus area(s): name, comma-separated, or `all` | `all` |
| `--provider` | `-p` | AI provider override | from config |
| `--dry-run` | | Show what would be audited without calling AI | off |
| `--format` | `-F` | Output format: `markdown` or `sarif` | `markdown` |

```bash
# Run all focus areas (default)
noxaudit run

# Security audit only
noxaudit run --focus security

# Multiple focus areas in one call
noxaudit run --focus security,performance

# All focus areas
noxaudit run --focus all

# Dry run to see file counts
noxaudit run --focus security --dry-run

# SARIF output for GitHub Code Scanning
noxaudit run --focus security --format sarif
```

## `submit`

Submit a batch audit. Returns immediately — results are retrieved later with `retrieve`. Useful for Anthropic's batch API which offers 50% cost savings.

```bash
noxaudit submit [options]
```

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--repo` | `-r` | Audit a specific repo | all repos |
| `--focus` | `-f` | Focus area(s): name, comma-separated, or `all` | `all` |
| `--provider` | `-p` | AI provider override | from config |
| `--dry-run` | | Show what would be submitted without calling AI | off |

```bash
noxaudit submit --focus security
# Submitted 1 batch(es). Run `noxaudit retrieve` to get results.
```

## `retrieve`

Retrieve results from a previously submitted batch audit.

```bash
noxaudit retrieve [options]
```

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--pending-file` | | Path to pending batch JSON file | auto-detect |
| `--format` | `-F` | Output format: `markdown` or `sarif` | `markdown` |

```bash
noxaudit retrieve
noxaudit retrieve --format sarif
```

## `decide`

Record a decision about a finding. Decisions prevent the finding from resurfacing in future audits.

```bash
noxaudit decide <finding_id> --action <type> --reason <text>
```

| Flag | Short | Description | Required |
|------|-------|-------------|----------|
| `--action` | `-a` | Decision type: `accept`, `dismiss`, or `intentional` | yes |
| `--reason` | `-r` | Why this decision was made | yes |
| `--by` | `-b` | Who made this decision | `user` |

```bash
noxaudit decide abc123 --action accept --reason "Fixed in PR #42"
noxaudit decide def456 --action dismiss --reason "Test fixture"
noxaudit decide ghi789 --action intentional --reason "Dev-only CORS"
```

## `baseline`

Baseline existing findings to suppress them in future audits. Useful when adding noxaudit to an existing project.

```bash
noxaudit baseline [options]
```

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--repo` | `-r` | Baseline a specific repo | all repos |
| `--focus` | `-f` | Baseline specific focus area(s) | all |
| `--severity` | `-s` | Baseline specific severities (comma-separated) | all |
| `--undo` | | Remove baseline decisions | off |
| `--list` | | Show baselined findings | off |

```bash
# Baseline all current findings
noxaudit baseline

# Baseline only high-severity security findings
noxaudit baseline --focus security --severity high

# See what's baselined
noxaudit baseline --list

# Remove all baselines
noxaudit baseline --undo

# Remove baselines for a specific repo
noxaudit baseline --undo --repo my-app
```

## `status`

Show current configuration, focus areas, decisions, and cost tracking.

```bash
noxaudit status
```

Displays:

- Configured repos and providers
- Available focus areas with descriptions
- Active model
- Decision and report paths
- Cost summary for the last 30 days (audits run, tokens, spend, projected monthly)
- Last 5 audit details

## `report`

Show the latest audit report.

```bash
noxaudit report [options]
```

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--repo` | `-r` | Show report for a specific repo | latest |
| `--focus` | `-f` | Show report for a specific focus area | latest |

```bash
noxaudit report
noxaudit report --repo my-app --focus security
```

## `estimate`

Estimate audit cost before running. No API keys needed — counts files and tokens locally.

```bash
noxaudit estimate [options]
```

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--repo` | `-r` | Estimate for a specific repo | all repos |
| `--focus` | `-f` | Focus area(s): name, comma-separated, or `all` | `all` |
| `--provider` | `-p` | AI provider override | from config |

```bash
noxaudit estimate --focus security
noxaudit estimate --focus all --provider gemini
```

The estimate includes:

- File and token counts
- Cost with current model
- Cheaper alternatives with savings percentages
- Pre-pass potential (for large codebases on Anthropic)
- Monthly projection assuming daily runs

## `mcp-server`

Start the MCP (Model Context Protocol) server for AI coding tool integration.

```bash
noxaudit mcp-server
```

Requires the `mcp` extra:

```bash
pip install 'noxaudit[mcp]'
```

See [MCP Server](../integrations/mcp-server.md) for details.

## Global Options

| Flag | Short | Description |
|------|-------|-------------|
| `--config` | `-c` | Path to `noxaudit.yml` |
| `--version` | | Show version |
| `--help` | | Show help |
