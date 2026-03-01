# Your First Audit

This walkthrough takes you through a complete audit cycle: estimating cost, running the audit, interpreting findings, recording decisions, and generating a report.

## Step 1: Estimate the Cost

Before spending any API credits, see what the audit will cost:

```bash
noxaudit estimate --focus security
```

```
  my-app — security

  Files:     42 files, 87K tokens
  Provider:  anthropic (claude-sonnet-4-5)

  Cost estimate: ~$0.14
    Batch API 50% discount applied.

  Alternatives:
    gemini (gemini-2.0-flash)                ~$0.01   93% cheaper — recommended for daily audits

  Monthly estimate: ~$4.20 (assuming daily runs)
```

No API key is needed for estimation — it counts files and tokens locally.

!!! tip
    Use `--focus all` to see the cost for all 7 focus areas combined.

## Step 2: Run the Audit

```bash
noxaudit run --focus security
```

Noxaudit gathers security-relevant files, sends them to the AI provider, and filters the results against your decision history.

```
my-app: 3 new findings
```

## Step 3: Read the Report

```bash
noxaudit report
```

This shows the latest report. You can also find reports in `.noxaudit/reports/my-app/`.

Each finding includes:

- **Severity** — high, medium, or low
- **Title** — short description of the issue
- **File** — where the issue was found
- **Description** — what the AI found and why it matters
- **Suggestion** — recommended fix

## Step 4: Make Decisions

For each finding, decide what to do:

```bash
# You fixed it
noxaudit decide abc123 --action accept --reason "Fixed in PR #42"

# It's not a real issue
noxaudit decide def456 --action dismiss --reason "Test fixture, not real credentials"

# It's intentional
noxaudit decide ghi789 --action intentional --reason "Permissive CORS for dev environment"
```

Decisions are stored in `.noxaudit/decisions.jsonl`. A finding won't resurface unless:

- The file it's in changes
- The decision expires (default: 90 days)

!!! tip
    Commit `.noxaudit/decisions.jsonl` to share decisions across your team.

## Step 5: Baseline Existing Findings

If you're adding noxaudit to an existing project with many known issues, baseline them all at once:

```bash
noxaudit baseline
```

This creates `dismiss` decisions for every current finding. Future runs will only show *new* issues.

Undo anytime:

```bash
noxaudit baseline --undo
```

## Step 6: Check Status

See your configuration and cost history:

```bash
noxaudit status
```

```
Noxaudit v0.1.0

Repos:
  my-app: . (anthropic)

Focus areas:
  security: Secrets, injection, auth, and configuration vulnerabilities
  docs: README accuracy, stale comments, API doc drift
  ...

Model: claude-sonnet-4-5-20250929
Decisions: .noxaudit/decisions.jsonl
Reports: .noxaudit/reports

Cost (last 30 days):
  Audits run:          1
  Total input tokens:  87K
  Total output tokens: 8K
  Estimated spend:     $0.14
  Avg per audit:       $0.14
  Projected monthly:   ~$4.20
```

## Step 7: Set Up Nightly Runs

Once you're happy with the results, automate it. See the [GitHub Actions integration](../integrations/github-actions.md) or set up a cron job:

```bash
# Run all focus areas daily at 6 AM
0 6 * * * cd /path/to/project && noxaudit run
```

## What's Next

- [Usage Patterns](../guides/scheduling.md) — on-demand, CI, and rotation examples
- [Cost Management](../guides/cost-management.md) — budget controls and optimization
- [Decision Memory](../guides/decisions.md) — advanced decision management
