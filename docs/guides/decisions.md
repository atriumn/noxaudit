# Decision Memory

Noxaudit's decision memory system prevents resolved findings from resurfacing in future audits. When you record a decision about a finding, noxaudit remembers it and filters it from future results.

## How It Works

1. Noxaudit runs an audit and produces findings
2. You review each finding and record a decision
3. On subsequent runs, noxaudit checks each new finding against the decision history
4. Matching findings are filtered out and reported as "resolved"

Decisions are stored in `.noxaudit/decisions.jsonl` as one JSON object per line.

## Decision Types

| Type | Meaning | Use When |
|------|---------|----------|
| `accept` | You fixed the issue | The finding is resolved by a code change |
| `dismiss` | Not a real issue | False positive, test code, or not applicable |
| `intentional` | Deliberate choice | You know about it and it's by design |

## Recording Decisions

```bash
# You fixed the issue
noxaudit decide abc123 --action accept --reason "Fixed in PR #42"

# It's a false positive
noxaudit decide def456 --action dismiss --reason "Test fixture, not real credentials"

# It's intentional
noxaudit decide ghi789 --action intentional --reason "Permissive CORS for dev environment"
```

The `--reason` flag is required — it documents *why* the decision was made for your future self and teammates.

You can optionally record who made the decision:

```bash
noxaudit decide abc123 --action accept --reason "Fixed" --by "alice"
```

## Decision Expiry

Decisions expire after a configurable number of days (default: 90). This ensures that old decisions are periodically re-evaluated.

```yaml
decisions:
  expiry_days: 90
```

When a decision expires, the finding will resurface in the next audit, giving you a chance to confirm it's still resolved.

## File Change Detection

Decisions are linked to the file they apply to. If the file changes (content hash differs), the decision is invalidated and the finding resurfaceeven if the decision hasn't expired.

This prevents situations where a finding is dismissed but the file is later modified in a way that re-introduces the issue.

## Baselining

When adding noxaudit to an existing project, you may have dozens of known issues. Instead of deciding on each one individually, baseline them all:

```bash
# Run an audit first
noxaudit run --focus all

# Baseline all findings
noxaudit baseline
```

This creates `dismiss` decisions for every current finding. Future runs will only show *new* issues.

### Filtered Baselines

Baseline specific subsets:

```bash
# Only security findings
noxaudit baseline --focus security

# Only high-severity findings
noxaudit baseline --severity high

# Specific repo
noxaudit baseline --repo my-app

# Combine filters
noxaudit baseline --repo my-app --focus security --severity high
```

### Managing Baselines

```bash
# See what's baselined
noxaudit baseline --list

# Remove all baselines
noxaudit baseline --undo

# Remove baselines with filters
noxaudit baseline --undo --repo my-app
noxaudit baseline --undo --focus security
noxaudit baseline --undo --severity low
```

## Sharing Decisions

Commit `.noxaudit/decisions.jsonl` to your repository to share decisions across the team. Everyone gets the same filtered view.

```bash
git add .noxaudit/decisions.jsonl
git commit -m "Add noxaudit baseline decisions"
```

## MCP Integration

If you use the [MCP server](../integrations/mcp-server.md), you can record decisions directly from your AI coding tool:

```
Record decision: dismiss finding abc123 because "test fixture"
```

The MCP `record_decision` tool accepts the same parameters as the CLI.
