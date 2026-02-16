"""Base focus area."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from noxaudit.models import FileContent


# Max file size to include (skip large generated/vendored files)
MAX_FILE_SIZE = 50_000  # ~50KB


class BaseFocus(ABC):
    """Base class for audit focus areas."""

    name: str = "base"
    description: str = ""

    @abstractmethod
    def get_file_patterns(self) -> list[str]:
        """Return glob patterns for files to include."""
        ...

    @abstractmethod
    def get_prompt(self) -> str:
        """Return the system prompt for this focus area."""
        ...

    def gather_files(
        self,
        repo_path: str | Path,
        exclude_patterns: list[str] | None = None,
    ) -> list[FileContent]:
        """Gather files from repo matching this focus area's patterns."""
        repo = Path(repo_path)
        exclude = set(exclude_patterns or [])
        # Always exclude these
        exclude.update(["node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"])

        files = []
        for pattern in self.get_file_patterns():
            for path in sorted(repo.glob(pattern)):
                if not path.is_file():
                    continue
                if path.stat().st_size > MAX_FILE_SIZE:
                    continue
                rel = str(path.relative_to(repo))
                if any(ex in rel for ex in exclude):
                    continue
                try:
                    content = path.read_text(errors="replace")
                    files.append(FileContent(path=rel, content=content))
                except (PermissionError, OSError):
                    continue

        return files

    def get_prompt_from_file(self, prompt_name: str) -> str:
        """Load a prompt template from the focus_prompts directory."""
        prompt_file = Path(__file__).parent.parent.parent / "focus_prompts" / f"{prompt_name}.md"
        if prompt_file.exists():
            return prompt_file.read_text()
        return self.get_prompt()


def gather_files_combined(
    focus_areas: list[BaseFocus],
    repo_path: str | Path,
    exclude_patterns: list[str] | None = None,
) -> list[FileContent]:
    """Gather files from repo matching the union of all focus areas' patterns, deduped by path."""
    repo = Path(repo_path)
    exclude = set(exclude_patterns or [])
    exclude.update(["node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"])

    # Union all patterns across focus areas
    all_patterns: set[str] = set()
    for focus in focus_areas:
        all_patterns.update(focus.get_file_patterns())

    seen_paths: set[str] = set()
    files: list[FileContent] = []

    for pattern in sorted(all_patterns):
        for path in sorted(repo.glob(pattern)):
            if not path.is_file():
                continue
            if path.stat().st_size > MAX_FILE_SIZE:
                continue
            rel = str(path.relative_to(repo))
            if rel in seen_paths:
                continue
            if any(ex in rel for ex in exclude):
                continue
            try:
                content = path.read_text(errors="replace")
                files.append(FileContent(path=rel, content=content))
                seen_paths.add(rel)
            except (PermissionError, OSError):
                continue

    return files


def build_combined_prompt(focus_areas: list[BaseFocus]) -> str:
    """Build a combined system prompt from multiple focus areas.

    Single focus → that focus's prompt unchanged.
    Multiple → header with tagging instructions, then each prompt under a section header.
    """
    if len(focus_areas) == 1:
        return focus_areas[0].get_prompt()

    sections = []
    focus_names = [f.name for f in focus_areas]

    sections.append(
        "You are performing a combined codebase audit covering multiple focus areas. "
        "For each finding, include a `focus` field indicating which focus area "
        f"({', '.join(focus_names)}) the finding belongs to.\n"
    )

    for focus in focus_areas:
        sections.append(f"## Focus Area: {focus.name}\n")
        sections.append(focus.get_prompt())
        sections.append("")

    return "\n".join(sections)
