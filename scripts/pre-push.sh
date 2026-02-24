#!/usr/bin/env bash
set -e
echo "Running tests before push..."
uv run --extra dev --extra mcp pytest
