# Contributing to Noxaudit

Thank you for your interest in contributing to Noxaudit! This document provides guidelines for contributing to the project.

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
- pre-commit hooks (ruff format + lint on every commit)
- pre-push hook (pytest runs before every push)

## Running Tests

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=noxaudit --cov-report=term-missing

# Run specific test file
pytest tests/test_config.py -v
```

## Code Quality

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for linting issues
ruff check noxaudit/ tests/

# Automatically fix linting issues
ruff check --fix noxaudit/ tests/

# Format code
ruff format noxaudit/ tests/

# Check formatting without modifying files
ruff format --check noxaudit/ tests/
```

Before submitting a PR, ensure both linting and formatting pass:

```bash
ruff check noxaudit/ tests/ && ruff format --check noxaudit/ tests/
```

## Adding a New Focus Area

Focus areas are the core audit types (security, patterns, docs, etc.). To add a new one:

1. **Create the focus area class** in `noxaudit/focus/yourarea.py`:
   ```python
   from noxaudit.focus.base import FocusArea

   class YourAreaFocus(FocusArea):
       name = "yourarea"
       description = "Brief description of what this audit looks for"

       def get_prompt(self, context: dict) -> str:
           # Load and customize the prompt template
           return super().get_prompt(context)
   ```

2. **Add prompt template** in `focus_prompts/yourarea.md`:
   - Write clear instructions for the AI auditor
   - Include examples of what to look for
   - Specify output format expectations

3. **Register the focus area** in `noxaudit/focus/__init__.py`:
   ```python
   from noxaudit.focus.yourarea import YourAreaFocus

   FOCUS_AREAS = {
       "yourarea": YourAreaFocus,
       # ... other focus areas
   }
   ```

4. **Add tests** in `tests/test_focus.py`:
   ```python
   def test_yourarea_focus():
       focus = YourAreaFocus()
       assert focus.name == "yourarea"
       prompt = focus.get_prompt({})
       assert "expected content" in prompt
   ```

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
├── config.py          # Configuration handling
├── runner.py          # Main audit runner
└── cli.py             # CLI entry point

tests/                  # Test suite
action/                 # GitHub Action definition
focus_prompts/          # Prompt templates for focus areas
```

## Pull Request Guidelines

1. **Keep changes focused**: One PR should address one issue or feature
2. **Write tests**: Add tests for new features or bug fixes
3. **Update documentation**: Update README.md if adding user-facing features
4. **Follow code style**: Run `ruff format` before committing
5. **Write clear commit messages**: Use conventional commits format:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `refactor:` for code refactoring
   - `test:` for test additions/changes

## Testing Your Changes

Before submitting a PR, test your changes locally:

```bash
# Install your local version
pip install -e .

# Test the CLI
noxaudit --help
noxaudit schedule

# Run the full test suite
pytest tests/ -v

# Check code quality
ruff check noxaudit/ tests/
ruff format --check noxaudit/ tests/
```

## Configuration for Testing

Create a test configuration file `noxaudit.yml`:

```yaml
ai_provider: anthropic  # or gemini
anthropic_api_key: your-test-key
model: claude-sonnet-4.5

focus_schedule:
  security: 0
  patterns: 1
  # ... other focus areas

# Optional: Test notifications
telegram:
  enabled: false  # Set to true for testing
  bot_token: your-bot-token
  chat_id: your-chat-id
```

## Getting Help

- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/atriumn/noxaudit/issues)
- **Discussions**: Ask questions or share ideas in [GitHub Discussions](https://github.com/atriumn/noxaudit/discussions)

## License

By contributing to Noxaudit, you agree that your contributions will be licensed under the project's license.
