# Focus Areas

Noxaudit audits your codebase through 7 specialized focus areas. Each has its own prompt, file patterns, and severity guidelines.

## Overview

| Area | What It Checks |
|------|---------------|
| **security** | Secrets, injection, auth, configuration vulnerabilities |
| **testing** | Missing coverage, edge cases, test quality, flaky tests |
| **patterns** | Architecture consistency, naming, duplication |
| **hygiene** | Dead code, orphaned files, stale config, TODOs |
| **docs** | README accuracy, stale comments, API doc drift |
| **dependencies** | Vulnerabilities, phantom deps, version management |
| **performance** | N+1 queries, missing caching, memory leaks, bundle size |

## Security

**Prompt focus**: Secrets & credentials, injection & input handling, authentication & authorization, configuration & infrastructure, fail-open patterns, data exposure.

**Severity guide**:

- **HIGH** — Exploitable now: leaked secrets, SQL/command injection, broken auth, SSRF
- **MEDIUM** — Requires specific conditions: missing rate limiting, overly permissive CORS, partial input validation
- **LOW** — Defense-in-depth: missing security headers, verbose error messages, no request signing

**File patterns**: All source files, config files, environment templates.

## Testing

**Prompt focus**: Missing coverage for critical paths (auth, payments, data mutations), edge case gaps, test quality issues (flaky tests, meaningless assertions), test maintenance.

**Severity guide**:

- **HIGH** — Critical path with zero test coverage (auth, payments, data mutations)
- **MEDIUM** — Feature with tests but missing important edge cases
- **LOW** — Test quality issues (naming, organization, minor gaps)

**File patterns**: Test files, source files being tested.

## Patterns

**Prompt focus**: Architectural consistency, error handling patterns, naming & structure conventions, code duplication & abstraction opportunities.

**Severity guide**:

- **HIGH** — Inconsistency that could cause bugs (mixed error handling, conflicting patterns)
- **MEDIUM** — Inconsistency that hurts maintainability (naming drift, structural divergence)
- **LOW** — Style or organizational suggestions

**File patterns**: All source files.

## Hygiene

**Prompt focus**: Dead code & orphaned files, stale configuration, code debris (commented-out code, unresolved TODOs), unnecessary artifacts.

**Severity guide**:

- **HIGH** — Dead code that could mislead or cause bugs if accidentally activated
- **MEDIUM** — Orphaned files, stale config, significant commented-out code
- **LOW** — Minor cleanup (old TODOs, small commented blocks)

**File patterns**: All source files, config files.

## Docs

**Prompt focus**: README instructions that would fail if followed, code comments and docstrings that contradict the code, cross-reference validation, accuracy of API documentation.

**Severity guide**:

- **HIGH** — Docs that would cause users to fail (wrong install commands, incorrect API usage)
- **MEDIUM** — Stale comments or docstrings that mislead developers
- **LOW** — Minor inaccuracies, formatting issues

**File patterns**: Markdown files, source files with docstrings.

## Dependencies

**Prompt focus**: Known vulnerabilities & supply chain risk, phantom/dead dependencies in manifests, version management & lock file consistency, dependency weight & redundancy.

**Severity guide**:

- **HIGH** — Known vulnerability in a production dependency
- **MEDIUM** — Outdated dependency with available security patches, phantom dependency
- **LOW** — Minor version behind, dev dependency issues

**File patterns**: Package manifests (`package.json`, `pyproject.toml`, `Gemfile`, etc.), lock files.

## Performance

**Prompt focus**: Database & query patterns (N+1 queries, missing indexes), async & concurrency issues, memory & resource leaks, frontend & asset optimization, build & deploy performance.

**Severity guide**:

- **HIGH** — Performance issue affecting production (N+1 in hot path, memory leak, unbounded queries)
- **MEDIUM** — Inefficiency that scales poorly (missing pagination, sequential where parallel works)
- **LOW** — Optimization opportunity (unnecessary re-renders, oversized bundles)

**File patterns**: All source files, database migrations, build configs.

## Running Focus Areas

```bash
# Single focus area
noxaudit run --focus security

# Multiple areas in one API call (files deduplicated)
noxaudit run --focus security,performance

# All 7 areas at once (default when no --focus specified)
noxaudit run --focus all
noxaudit run
```

When multiple focus areas run together, source files are gathered and deduplicated across all areas, then sent in a single API call. This saves ~80% on input tokens compared to running each separately.
