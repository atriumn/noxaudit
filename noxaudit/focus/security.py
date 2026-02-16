"""Security focus area."""

from __future__ import annotations

from noxaudit.focus.base import BaseFocus


class SecurityFocus(BaseFocus):
    name = "security"
    description = "Security vulnerabilities, secrets, permissions, dependency issues"

    def get_file_patterns(self) -> list[str]:
        return [
            # Config and environment
            "**/*.yml",
            "**/*.yaml",
            "**/*.toml",
            "**/*.json",
            "**/*.env*",
            "**/.env*",
            "**/Dockerfile*",
            "**/docker-compose*",
            "**/.dockerignore",
            # Scripts
            "**/*.sh",
            "**/*.bash",
            # Source code (common languages)
            "**/*.py",
            "**/*.ts",
            "**/*.tsx",
            "**/*.js",
            "**/*.jsx",
            "**/*.go",
            "**/*.rs",
            "**/*.rb",
            # Git and CI
            "**/.gitignore",
            "**/.github/**/*.yml",
            # Dependency manifests
            "**/package.json",
            "**/package-lock.json",
            "**/requirements*.txt",
            "**/Pipfile",
            "**/Cargo.toml",
            "**/go.mod",
            "**/Gemfile",
        ]

    def get_prompt(self) -> str:
        return self.get_prompt_from_file("security")
