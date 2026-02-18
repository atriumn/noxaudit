# CLAUDE.md

## Setup

After cloning or creating a worktree, run:

```bash
./scripts/setup-hooks.sh
```

This installs pre-commit hooks (ruff format + lint) and a pre-push hook (pytest).

## Development

- Use `uv` for package management
- Run tests: `uv run pytest`
- Lint: `uv run ruff check noxaudit/ tests/`
- Format: `uv run ruff format noxaudit/ tests/`
