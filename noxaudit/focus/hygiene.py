"""Code hygiene focus area."""

from __future__ import annotations

from noxaudit.focus.base import BaseFocus


class HygieneFocus(BaseFocus):
    name = "hygiene"
    description = "Dead code, orphaned files, stale config, cleanup opportunities"

    def get_file_patterns(self) -> list[str]:
        return [
            # All source and config
            "**/*.py",
            "**/*.ts",
            "**/*.tsx",
            "**/*.js",
            "**/*.jsx",
            "**/*.go",
            "**/*.rs",
            "**/*.yml",
            "**/*.yaml",
            "**/*.toml",
            "**/*.json",
            "**/*.sh",
            "**/*.md",
            # Git and CI
            "**/.gitignore",
            "**/.github/**",
            # Docker
            "**/Dockerfile*",
            "**/docker-compose*",
        ]

    def get_prompt(self) -> str:
        return self.get_prompt_from_file("hygiene")
