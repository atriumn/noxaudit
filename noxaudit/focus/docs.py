"""Documentation drift focus area."""

from __future__ import annotations

from noxaudit.focus.base import BaseFocus


class DocsFocus(BaseFocus):
    name = "docs"
    description = "Documentation accuracy, staleness, drift from actual code"

    def get_file_patterns(self) -> list[str]:
        return [
            # Documentation files
            "**/README*",
            "**/CHANGELOG*",
            "**/CONTRIBUTING*",
            "**/*.md",
            "**/*.mdx",
            "**/*.rst",
            # Config that documents behavior
            "**/*.yml",
            "**/*.yaml",
            "**/*.toml",
            # Source code (to compare against docs)
            "**/*.py",
            "**/*.ts",
            "**/*.tsx",
            "**/*.js",
            "**/*.jsx",
            "**/*.go",
            "**/*.rs",
        ]

    def get_prompt(self) -> str:
        return self.get_prompt_from_file("docs")
