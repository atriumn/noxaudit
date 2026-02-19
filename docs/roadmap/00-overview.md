# Noxaudit Product Roadmap

## Vision

Noxaudit becomes the standard way teams keep codebases **and products** healthy — a nightly AI reviewer that finds what's drifting, fixes what it can, and proves compliance to anyone who asks.

## Where we are today (v0.1.0)

A working CLI that runs scheduled AI audits across 7 focus areas using Anthropic's Batch API. It remembers prior decisions, generates markdown reports, sends Telegram notifications, creates GitHub issues, and exposes an MCP server for AI tool integration. Single provider (Anthropic). No web presence. No auto-remediation. No dashboard.

## Where we're going

Five phases, each building demand for the next:

| Phase | Name | Outcome | Depends on |
|-------|------|---------|------------|
| 1 | [OSS Foundation](./01-oss-foundation.md) | Tool people actually adopt and keep installed | — |
| 2 | [Product-Market Fit](./02-product-market-fit.md) | Tool that saves measurable time every week | Phase 1 |
| 3 | [Web Presence](./03-web-presence.md) | noxaudit.com drives awareness, docs, and signups | Phases 1–2 |
| 3.5 | [SaaS Application](./03.5-saas-application.md) | Dashboard, user flows, and product architecture users log into | Phases 2–3 |
| 4 | [Monetization](./04-monetization.md) | Sustainable revenue from teams and orgs | Phases 1–3.5 |
| 5 | [Enterprise](./05-enterprise.md) | Procurement-ready product for regulated industries | Phases 1–4 |

## Guiding principles

**Outcomes over outputs.** Each phase is defined by what changes for the user, not what we ship. "Users can baseline existing findings in under a minute" matters. "Implement baseline command" doesn't — that's a task.

**OSS-first.** The open-source package is the product. SaaS and enterprise layers are acceleration on top. If the CLI stops being the best free option, the business fails.

**Fix > Find.** Detection is a commodity. Every SAST tool finds issues. The value is in resolution — auto-fixes, triage automation, and proof that things got better. Every feature decision should bias toward closing the loop.

**Cost-transparent.** Users are spending their own API budget. Every feature that reduces token usage or increases finding quality per dollar is a competitive advantage. Never hide costs.

**Earn the right to each phase.** Phase 3 only works if Phases 1–2 created something worth talking about. Phase 4 only works if Phase 3 built an audience. Don't skip ahead.

## Revenue model summary

Detailed in [Phase 4](./04-monetization.md), but the short version:

- **Free forever**: OSS CLI, all focus areas, auto-fix for hygiene/docs, community support
- **Pro** ($29/mo per repo): Auto-fix for all focus areas, PR comments, dashboard, priority support
- **Team** ($99/mo, 10 repos): Custom focus areas, Slack/Jira, trend analytics, team triage
- **Enterprise** (custom): Compliance frameworks, audit trails, SSO, self-hosted, SLA

The website strategy is detailed in [Phase 3](./03-web-presence.md).

## Cross-cutting: Product Quality Focus Areas

In addition to the phase-based roadmap, [Product Quality Focus Areas](./06-product-quality-focus-areas.md) describes the expansion from 7 engineer-facing focus areas to 17 total — adding UX copy, user flow coherence, accessibility, cross-browser compatibility, help content accuracy, error state handling, UI clarity, internationalization, design system consistency, and performance UX. These land mid-Phase 2 and reshape the value proposition: from "keep your codebase healthy" to "keep your product healthy." This also informs the free/paid boundary — engineer focus areas stay free, product focus areas become the paid differentiator.

## How to read these docs

Each phase doc follows the same structure:

1. **What success looks like** — the observable outcomes when this phase is done
2. **What exists today** — current state relevant to this phase
3. **What needs to exist** — capabilities, not tasks
4. **Dependencies & sequencing** — what blocks what
5. **Risks** — what could make this phase fail
6. **How we'll know it's working** — metrics, not milestones
