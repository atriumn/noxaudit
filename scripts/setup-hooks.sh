#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Installing pre-commit hooks..."
uv run pre-commit install

echo "Installing pre-push hook..."
ln -sf "$SCRIPT_DIR/pre-push.sh" "$REPO_ROOT/.git/hooks/pre-push"
chmod +x "$REPO_ROOT/.git/hooks/pre-push"

echo "Done! Hooks installed:"
echo "  - pre-commit: ruff format + lint on every commit"
echo "  - pre-push: pytest runs before every push"
