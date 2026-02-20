## Summary

<!-- Describe what this PR does and why. -->

## Changes

<!-- List the main changes. -->

## CLI Integration Test Checklist

Every new feature must be verified end-to-end through the CLI entry point.
See [CONTRIBUTING.md](../CONTRIBUTING.md#mandatory-cli-integration-tests) for the policy.

- [ ] This PR adds no new user-facing features (skip below)
- [ ] New feature has at least one `@pytest.mark.cli_integration` test in `tests/test_cli_integration.py` (or a similarly structured integration test file)
- [ ] The integration test invokes the CLI via `click.testing.CliRunner` (not internal runner functions)
- [ ] The integration test mocks the AI provider (no real API calls)
- [ ] The integration test asserts the feature output/side-effects are observable from the CLI layer

## Test Plan

```bash
# Run all tests
uv run pytest

# Run only CLI integration tests
uv run pytest tests/ -m cli_integration -v

# Run lint + format check
uv run ruff check noxaudit/ tests/
uv run ruff format --check noxaudit/ tests/
```
