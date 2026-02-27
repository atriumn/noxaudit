# Contributing

Thank you for your interest in contributing to Noxaudit!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/atriumn/noxaudit.git
cd noxaudit

# Install in development mode with dev dependencies
uv pip install -e ".[dev]"

# Install git hooks
./scripts/setup-hooks.sh
```

This installs:

- **Pre-commit hooks**: ruff format + lint on every commit
- **Pre-push hook**: pytest runs before every push

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=noxaudit --cov-report=term-missing

# Run a specific test file
pytest tests/test_config.py -v

# Run only CLI integration tests
pytest tests/ -m cli_integration -v
```

## Code Quality

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for linting issues
ruff check noxaudit/ tests/

# Auto-fix linting issues
ruff check --fix noxaudit/ tests/

# Format code
ruff format noxaudit/ tests/

# Check formatting without modifying
ruff format --check noxaudit/ tests/
```

Before submitting a PR:

```bash
ruff check noxaudit/ tests/ && ruff format --check noxaudit/ tests/
```

## CLI Integration Tests

**Every new feature must have at least one CLI integration test.**

We've seen features pass unit tests but never get wired into the CLI. To prevent this, all features must be tested end-to-end through the CLI entry point.

### The Pattern

```python
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from noxaudit.cli import main

@pytest.mark.cli_integration
def test_my_feature_through_cli(tmp_path):
    cfg = _write_config(tmp_path)
    provider_cls, provider_instance = _make_mock_provider(findings=[...])

    with patch.dict("noxaudit.runner.PROVIDERS", {"gemini": provider_cls}):
        result = CliRunner().invoke(main, ["--config", cfg, "run", "--focus", "security"])

    assert result.exit_code == 0
    assert "my feature output" in result.output
```

A CLI integration test:

1. Invokes the CLI through `click.testing.CliRunner` (not runner functions directly)
2. Mocks the AI provider so no real API calls are made
3. Asserts that the feature's output/side-effects are observable from the CLI layer

Mark integration tests with `@pytest.mark.cli_integration` and place them in:

- `tests/test_cli_integration.py` — general CLI integration tests
- `tests/test_sarif_integration.py` — SARIF-specific integration tests

## Adding a New Focus Area

1. **Create the focus area class** in `noxaudit/focus/yourarea.py`:

    ```python
    from noxaudit.focus.base import FocusArea

    class YourAreaFocus(FocusArea):
        name = "yourarea"
        description = "Brief description of what this audit looks for"

        def get_prompt(self, context: dict) -> str:
            return super().get_prompt(context)
    ```

2. **Add a prompt template** in `focus_prompts/yourarea.md` with audit instructions, examples, and severity guidelines.

3. **Register it** in `noxaudit/focus/__init__.py`:

    ```python
    from noxaudit.focus.yourarea import YourAreaFocus

    FOCUS_AREAS = {
        "yourarea": YourAreaFocus,
        # ... other focus areas
    }
    ```

4. **Add tests** in `tests/test_focus.py`.

## Project Structure

```
noxaudit/
├── focus/              # Focus area implementations
│   ├── base.py        # Base FocusArea class
│   ├── security.py    # Security audit focus
│   └── ...
├── providers/          # AI provider integrations
│   ├── anthropic.py   # Anthropic Claude
│   └── gemini.py      # Google Gemini
├── notifications/      # Notification handlers
│   ├── telegram.py    # Telegram notifications
│   └── github.py      # GitHub issue creation
├── mcp/               # MCP server
│   └── server.py      # 5 exposed tools
├── config.py          # Configuration handling
├── runner.py          # Main audit runner
├── decisions.py       # Decision memory
├── pricing.py         # Cost estimation
├── sarif.py           # SARIF output
├── prepass.py         # Pre-pass file triage
└── cli.py             # CLI entry point

tests/                  # Test suite
action/                 # GitHub Action definition
focus_prompts/          # Prompt templates for focus areas
docs/                   # Documentation (this site)
```

## Pull Request Guidelines

1. **Keep changes focused** — one PR per issue or feature
2. **Write tests** — including at least one CLI integration test for new features
3. **Update documentation** — update docs if adding user-facing features
4. **Follow code style** — run `ruff format` before committing
5. **Use conventional commits**:
    - `feat:` new features
    - `fix:` bug fixes
    - `docs:` documentation changes
    - `refactor:` code refactoring
    - `test:` test additions/changes

## Getting Help

- [GitHub Issues](https://github.com/atriumn/noxaudit/issues) — report bugs or request features
- [GitHub Discussions](https://github.com/atriumn/noxaudit/discussions) — ask questions or share ideas
