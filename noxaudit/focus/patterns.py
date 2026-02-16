"""Code patterns and architecture focus area."""

from __future__ import annotations

from noxaudit.focus.base import BaseFocus


class PatternsFocus(BaseFocus):
    name = "patterns"
    description = "Architecture consistency, naming conventions, duplicated logic, pattern drift"

    def get_file_patterns(self) -> list[str]:
        return [
            # Source code
            "**/*.py",
            "**/*.ts",
            "**/*.tsx",
            "**/*.js",
            "**/*.jsx",
            "**/*.go",
            "**/*.rs",
            "**/*.rb",
            # Config that defines patterns
            "**/*.yml",
            "**/*.yaml",
            "**/*.toml",
            "**/*.json",
            # Project structure
            "**/package.json",
            "**/tsconfig*.json",
            "**/pyproject.toml",
            "**/Cargo.toml",
        ]

    def get_prompt(self) -> str:
        return self.get_prompt_from_file("patterns")
