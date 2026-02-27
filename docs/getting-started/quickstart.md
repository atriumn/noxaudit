# Quick Start

Get your first audit running in under a minute.

## 1. Create a Config File

Create a `noxaudit.yml` in your project root:

```yaml
repos:
  - name: my-app
    path: .
    provider_rotation: [anthropic]

model: claude-sonnet-4-5-20250929
```

Or copy the example config:

```bash
cp noxaudit.yml.example noxaudit.yml
```

## 2. Set Your API Key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## 3. Run an Audit

```bash
noxaudit run --focus security
```

This sends your codebase's security-relevant files to the AI provider and returns a list of findings.

## 4. Read the Output

Noxaudit prints a summary to the terminal:

```
my-app: 3 new findings
```

The full report is saved to `.noxaudit/reports/my-app/{date}-security.md`.

View it with:

```bash
noxaudit report
```

## 5. Run Multiple Focus Areas

Combine focus areas in a single API call to save on input tokens (files are sent once, deduplicated):

```bash
# Comma-separated
noxaudit run --focus security,performance

# All 7 focus areas at once
noxaudit run --focus all
```

## What's Next

- [Your First Audit](first-audit.md) — end-to-end walkthrough with cost estimation, decisions, and reporting
- [Configuration](../guides/configuration.md) — full `noxaudit.yml` reference
- [Focus Areas](../guides/focus-areas.md) — what each audit checks
