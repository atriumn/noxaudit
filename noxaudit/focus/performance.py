"""Performance focus area."""

from __future__ import annotations

from noxaudit.focus.base import BaseFocus


class PerformanceFocus(BaseFocus):
    name = "performance"
    description = "Missing caching, expensive patterns, bundle size, query efficiency"

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
            # Config that affects performance
            "**/*.yml",
            "**/*.yaml",
            "**/*.toml",
            "**/*.json",
            # Database
            "**/migrations/**",
            "**/*.sql",
            # Docker
            "**/Dockerfile*",
            "**/docker-compose*",
            # Bundler config
            "**/webpack.config.*",
            "**/vite.config.*",
            "**/next.config.*",
            "**/tsconfig*.json",
        ]

    def get_prompt(self) -> str:
        return self.get_prompt_from_file("performance")
