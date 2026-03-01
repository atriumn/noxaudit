# SaaS Scheduling & Frames

**Status**: Future SaaS feature — removed from OSS CLI in v0.2.0.

The OSS CLI is intentionally simple: you tell it what to audit, it audits. Scheduling, frame taxonomy, and smart rotation are SaaS features where they can deliver real value through zero-config automation and a visual dashboard.

## What Moves to SaaS

### Day-of-Week Scheduling

The OSS CLI previously shipped a `DEFAULT_SCHEDULE` mapping weekdays to focus areas (Mon→security, Tue→patterns, etc.). This was confusing for new users and overly prescriptive. In the SaaS product, we pick the schedule — users never configure it.

### Frame Taxonomy

The five frames (`does_it_work`, `does_it_last`, `does_it_feel_right`, `can_everyone_use_it`, `can_we_prove_it`) organize focus areas into high-level quality questions. In the CLI, this added complexity without visual payoff. In the SaaS dashboard, frames structure health scores, trend views, and navigation.

### Smart Rotation

Intelligent scheduling based on repository activity:

- Skip audits when no commits since last run
- Increase frequency when code velocity is high
- Spread expensive models across the billing period
- Budget-aware scheduling: stay within monthly spend targets

### Budget-Aware Scheduling

The SaaS product manages spend automatically. It knows the user's tier, tracks cumulative cost, and adjusts audit frequency and model selection to stay within budget. This requires persistent state that a CLI can't maintain.

## Why It's a SaaS Feature

**Zero-config**: Users connect a repo and get audits. We pick the schedule, model, and rotation strategy. No YAML to write.

**Cost optimization**: We manage the spend. Daily Flash audits cost ~$0.35/day across all 7 focus areas. Monthly Opus deep dives cost ~$2/run. The SaaS product balances these automatically.

**Persistent state**: Scheduling requires tracking what ran when, what changed since, and how to allocate the budget across time. This needs a database and a dashboard — not a config file.

## How It Works in the Product

1. User connects a repo (GitHub App install)
2. We run daily Gemini Flash audits, rotating through focus areas
3. Monthly Opus deep dive across all areas
4. Dashboard shows trends by frame, health scores, finding history
5. User never configures a schedule — they just see results

See [SaaS Application](03.5-saas-application.md) for dashboard wireframes and architecture. The dashboard already uses frames in its information architecture (frame scores, drill-down to focus areas, trend views by frame).

## Smart Scheduling Logic

```
on_commit:
  if hours_since_last_audit < 12: skip
  if commit_touches_security_files: prioritize security
  else: run next_in_rotation

on_schedule (daily):
  if no_commits_since_last_audit: skip
  run next_focus_area_in_rotation

on_schedule (monthly):
  run all_focus_areas with opus model

budget_check:
  if monthly_spend > 80% of budget:
    switch to cheaper model for remaining days
  if monthly_spend > 95% of budget:
    skip non-critical audits
```

## Frame-Based Organization in Dashboard

The 5 frames organize the dashboard, not the CLI:

| Frame | Question | Focus Areas | Dashboard Widget |
|-------|----------|-------------|-----------------|
| `does_it_work` | Does it work? | security, testing | Safety score |
| `does_it_feel_right` | Does it feel right? | ux-copy, help-content | UX score |
| `can_everyone_use_it` | Can everyone use it? | a11y, i18n | Accessibility score |
| `does_it_last` | Does it last? | patterns, hygiene, docs, dependencies | Maintainability score |
| `can_we_prove_it` | Can we prove it? | performance | Performance score |

This taxonomy adds value in a visual UI but is unnecessary complexity for a CLI tool.

## Prompt Strategy (Hybrid Model)

The OSS CLI ships functional starter prompts that work well across models. The SaaS product will use enhanced, per-model-tuned prompts iterated across many repos. This is a separate body of work — noted here as a future SaaS differentiator.

- **OSS prompts**: Good enough for all models, open source, user-modifiable
- **SaaS prompts**: Optimized per model (Flash vs Opus), A/B tested across repos, continuously improved

## References

- [Strategy & Pricing](../STRATEGY.md) — tiered pricing model (Flash daily + Opus monthly)
- [SaaS Application](03.5-saas-application.md) — dashboard wireframes (frames in information architecture)
- [Product Quality Focus Areas](06-product-quality-focus-areas.md) — frame definitions and expansion roadmap
