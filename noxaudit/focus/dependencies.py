"""Dependency health focus area."""

from __future__ import annotations

from noxaudit.focus.base import BaseFocus


class DependenciesFocus(BaseFocus):
    name = "dependencies"
    description = "Outdated packages, security advisories, unused deps, version conflicts"

    def get_file_patterns(self) -> list[str]:
        return [
            # JS/TS
            "**/package.json",
            "**/package-lock.json",
            "**/pnpm-lock.yaml",
            "**/yarn.lock",
            # Python
            "**/requirements*.txt",
            "**/Pipfile",
            "**/Pipfile.lock",
            "**/pyproject.toml",
            "**/poetry.lock",
            # Rust
            "**/Cargo.toml",
            "**/Cargo.lock",
            # Go
            "**/go.mod",
            "**/go.sum",
            # Ruby
            "**/Gemfile",
            "**/Gemfile.lock",
            # Source (to check for unused imports)
            "**/*.py",
            "**/*.ts",
            "**/*.tsx",
            "**/*.js",
            "**/*.jsx",
        ]

    def get_prompt(self) -> str:
        return self.get_prompt_from_file("dependencies")
