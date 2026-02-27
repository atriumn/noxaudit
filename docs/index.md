---
hide:
  - navigation
---

<div align="center" markdown>

![Noxaudit](assets/logo.png){ width="160" }

# Noxaudit

**Nightly AI-powered codebase audits with rotating focus areas, multi-provider support, and decision memory.**

[Get Started](getting-started/installation.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/atriumn/noxaudit){ .md-button }

</div>

---

## The Problem

Codebases drift. Docs go stale, security issues creep in, patterns diverge, dead code accumulates. Manual reviews are expensive and inconsistent. Linters catch syntax but miss semantics.

## The Solution

Noxaudit runs a focused AI audit every night, rotating through different concerns. It remembers what you've already reviewed so it only surfaces genuinely new findings.

```
Mon: Security → Tue: Patterns → Wed: Docs → Thu: Hygiene → Fri: Performance → Sat: Dependencies
```

Each night, Noxaudit:

1. Picks today's focus area(s) from the schedule
2. Gathers relevant files from your codebase (deduped across focus areas)
3. Sends them to an AI provider (Claude, GPT, Gemini) with a focused prompt
4. Filters results against your decision history (so resolved issues don't resurface)
5. Generates a report and sends you a notification

---

## Key Features

<div class="grid cards" markdown>

-   :material-shield-check:{ .lg .middle } **7 Focus Areas**

    ---

    Security, patterns, docs, hygiene, performance, dependencies, and testing — each with specialized prompts.

-   :material-brain:{ .lg .middle } **Decision Memory**

    ---

    Record decisions about findings so they don't resurface. Decisions expire after 90 days or when the file changes.

-   :material-swap-horizontal:{ .lg .middle } **Multi-Provider**

    ---

    Rotate between Anthropic Claude, OpenAI GPT, and Google Gemini. Different models catch different things.

-   :material-currency-usd:{ .lg .middle } **Cost Controls**

    ---

    Budget limits, cost estimation before running, batch API discounts, and pre-pass token optimization.

-   :material-github:{ .lg .middle } **GitHub Integration**

    ---

    GitHub Actions workflow, automatic issue creation, and SARIF upload for Code Scanning alerts.

-   :material-bell-outline:{ .lg .middle } **Notifications**

    ---

    Get summaries via Telegram with severity counts and finding details.

</div>

---

## Quick Install

```bash
pip install noxaudit
```

```bash
export ANTHROPIC_API_KEY=sk-ant-...
noxaudit run --focus security
```

See the full [Installation Guide](getting-started/installation.md) and [Quick Start](getting-started/quickstart.md).

---

## Example Output

```
🔒 Security Audit — my-app
3 new findings: 🔴 1 high, 🟡 2 medium

⚠️ SQL interpolation in query builder
   src/db/queries.ts
ℹ️ Console.log with request body
   src/middleware/auth.ts
ℹ️ Permissive CORS in production config
   src/config/cors.ts

✅ 5 previous findings still resolved
```

---

## License

MIT
