# Infrastructure Health Check

## The idea

The 17 recurring focus areas audit application code on a weekly cycle. But there's a category of problems that lives in infrastructure code — CI/CD pipelines, deployment scripts, Dockerfiles, monitoring config — that changes slowly and doesn't need weekly attention. It needs a monthly check.

This is DORA flipped from measurement to prevention. DORA tells you your MTTR is 4 hours. This check tells you *why* — and catches it before it shows up in the metrics.

## How it differs from focus areas

| | Focus areas | Infrastructure health check |
|---|---|---|
| **Cadence** | Weekly (one frame per day) | Monthly |
| **File targets** | Application code, docs, configs | CI/CD, Docker, IaC, deploy scripts, monitoring |
| **Prompt style** | "Review this code for X" | "Assess this project's delivery infrastructure" |
| **Output** | Individual findings with severities | Summary assessment with recommendations |
| **Change frequency** | Code changes daily | Infrastructure changes monthly/quarterly |

Focus areas find bugs in code that changes constantly. The infrastructure health check finds drift in config that changes rarely — which is exactly why it drifts unnoticed.

## What it assesses

### Deployment confidence — can you ship without fear?

| Severity | Example |
|---|---|
| Critical | No rollback mechanism — deployment is one-way (no blue/green, no canary, no `kubectl rollout undo`, no revert workflow) |
| Critical | Production secrets referenced by name in CI config but not in secret manager — key rotation requires pipeline changes |
| High | CI pipeline has no caching — full dependency install on every run, 15-minute builds that could be 3 minutes |
| High | No staging/preview environment — code goes from PR to production with no intermediate validation |
| High | Deploy script has undocumented manual steps (comments like `# SSH into prod and run migrate`) |
| Medium | Flaky test detection absent — no retry mechanism, no quarantine, flaky tests silently block or silently pass |
| Medium | CI matrix doesn't cover all supported versions/platforms listed in project config |
| Medium | Feature flags exist but have no expiry or cleanup mechanism — 47 flags, 30 are stale |

### Incident response readiness — when things break, how fast can you respond?

| Severity | Example |
|---|---|
| Critical | No health check endpoint — orchestrator can't detect when the service is unhealthy |
| Critical | Error monitoring not configured (no Sentry, no error tracking integration in the codebase) |
| High | Alerting config references stale endpoints, channels, or thresholds that haven't been updated with recent changes |
| High | No runbook or incident response docs — or runbook references architecture/steps that no longer exist |
| High | Log messages don't include request/trace IDs — correlating logs across services during an incident is impossible |
| Medium | No graceful shutdown handling — in-flight requests are dropped on deploy |
| Medium | Database migration is not reversible — `down()` migration is empty or missing |
| Medium | Monitoring dashboards reference metrics that are no longer emitted |

### Delivery velocity — what's slowing you down?

| Severity | Example |
|---|---|
| High | Single monolithic CI job that runs everything sequentially — lint, test, build, deploy in one 25-minute job instead of parallel stages |
| High | No dependency lockfile — builds are non-deterministic, "works on my machine" is unsolvable |
| Medium | PR template/checklist is stale — references steps or tools that no longer apply |
| Medium | Branch protection rules referenced in docs don't match actual GitHub settings (detectable via config files) |
| Medium | Dockerfile not multi-stage — dev dependencies in production image, slow builds, large image size |
| Low | No build artifact caching between CI runs — rebuilding unchanged dependencies every time |
| Low | CI config duplicated across repos with no shared workflow/template |

## The DORA connection

DORA measures outcomes. This check audits the preconditions.

| DORA metric | What makes it bad (that noxaudit can detect) |
|---|---|
| **Deployment frequency** | Slow CI (no caching, sequential jobs), no automated deploy, manual approval bottlenecks |
| **Lead time for changes** | Long build times, no preview environments, heavyweight PR process |
| **Change failure rate** | No staging, missing tests in CI, no canary/gradual rollout, no feature flags |
| **Mean time to recovery** | No rollback mechanism, stale runbooks, no health checks, no error monitoring, no trace IDs in logs |

## File patterns

`.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `Dockerfile`, `docker-compose*.yml`, `terraform/`, `pulumi/`, `k8s/`, `deploy/`, `scripts/deploy*`, `Makefile`, `.env.example`, monitoring config, alerting rules, feature flag config, runbooks/playbooks.

## Execution model

Not a focus area. Not part of the daily frame rotation. A standalone monthly assessment that:

1. Runs on its own schedule (1st of the month, or configurable)
2. Produces a separate "Infrastructure Health" report distinct from the weekly audit reports
3. Uses the standard API (not Batch) since it's infrequent and the results are wanted promptly
4. Could also run on-demand: `noxaudit check infra` for a one-time assessment
5. Makes a natural onboarding step: run it when a repo is first connected to establish a baseline

## Output format

Unlike focus areas (which produce individual findings), this produces a summary assessment:

```
## Infrastructure Health — acme/api — February 2026

### Deployment Confidence: Medium
- ✓ CI pipeline exists with test + lint stages
- ✓ Lockfile present, builds are deterministic
- ✗ No rollback mechanism (deploy is one-way)
- ✗ No staging environment
- ✗ CI has no caching (avg build: ~12min based on workflow complexity)

### Incident Response: Low
- ✓ Health check endpoint exists (/healthz)
- ✗ No error monitoring integration found
- ✗ Runbook references removed service (payment-gateway-v1)
- ✗ Logs missing correlation IDs

### Delivery Velocity: High
- ✓ CI jobs parallelized (lint, test, build run concurrently)
- ✓ Multi-stage Dockerfile
- ✓ Preview environments via Vercel
- △ PR template references deprecated tool (mention of removed linter)

### Recommendations (prioritized)
1. Add error monitoring (Sentry, Datadog, etc.) — biggest incident response gap
2. Add rollback step to deploy workflow — currently no recovery path
3. Update runbook to reflect current architecture
4. Add CI caching for dependencies — estimated 60-70% build time reduction
```

## Considerations

- This reviews *infrastructure code*, not application code. The file patterns are completely disjoint from all 17 focus areas.
- Many findings are about *absence* rather than *presence* — "no health check endpoint exists" is harder to assert than "this SQL query is vulnerable." The prompt needs to guide the model to assess what *should* be there given the project's deployment model.
- Severity should scale with project maturity. A side project shouldn't get critical findings for lacking canary deployments. The model should infer project scale from signals (number of contributors, presence of IaC, deployment targets).
- Monthly cadence means the report should be more thorough and narrative than weekly findings. Users read this once a month, so it should be worth reading — not just a checklist.

## Pricing

Included in all tiers. Infrastructure health is a baseline concern, like `security` and `testing`. Gating it behind a paywall creates perverse incentives — "pay us or we won't tell you your deploy has no rollback."

The Pro/Team differentiation comes from:
- **Free**: Monthly check, summary report
- **Pro**: Monthly check + trend tracking (is your infra health improving or degrading?)
- **Team**: Monthly check + trend + cross-repo comparison (which repos have the weakest delivery infrastructure?)
