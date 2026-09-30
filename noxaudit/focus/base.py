"""Base focus area."""

from __future__ import annotations

from abc import ABC, abstractmethod
from fnmatch import fnmatch
from pathlib import Path, PurePath

from noxaudit.models import FileContent


# Max file size to include (skip large generated/vendored files)
MAX_FILE_SIZE = 50_000  # ~50KB

# Directories and path fragments that should never be audited
DEFAULT_EXCLUDES = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "site",
    ".noxaudit",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "benchmark/results",
    "htmlcov",
    "egg-info",
}

# Files that hold secrets are never sent to a provider, whatever the focus or config.
# Matched against the file name (case-insensitive).
SECRET_FILE_PATTERNS = (
    ".env",
    ".env.*",
    "*.env",
    ".envrc",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.jks",
    "*.keystore",
    "id_rsa*",
    "id_dsa*",
    "id_ecdsa*",
    "id_ed25519*",
    ".npmrc",
    ".pypirc",
    ".netrc",
    ".pgpass",
    ".htpasswd",
    "credentials",
    "credentials.json",
    "service-account*.json",
    "secrets.yml",
    "secrets.yaml",
    "secrets.json",
    "secrets.toml",
    "*.tfvars",
    "*.tfstate",
    "*.tfstate.*",
)

# Env templates are committed on purpose and hold no values, so they stay auditable.
SECRET_FILE_ALLOW = (
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env.dist",
    "*.env.example",
    "*.env.sample",
    "*.env.template",
)

# Directories whose contents are secrets (or a virtualenv named .env).
SECRET_DIRS = {".env", ".envs", ".ssh", ".gnupg", ".aws"}


def is_secret_file(rel_path: str) -> bool:
    """Whether a repo-relative path is a secrets file that must never leave the machine."""
    parts = PurePath(rel_path).parts
    if any(part in SECRET_DIRS for part in parts[:-1]):
        return True
    name = parts[-1].lower()
    if any(fnmatch(name, pattern) for pattern in SECRET_FILE_ALLOW):
        return False
    return any(fnmatch(name, pattern) for pattern in SECRET_FILE_PATTERNS)


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
        exclude.update(DEFAULT_EXCLUDES)

        files = []
        for pattern in self.get_file_patterns():
            for path in sorted(repo.glob(pattern)):
                if not path.is_file():
                    continue
                if path.stat().st_size > MAX_FILE_SIZE:
                    continue
                rel = str(path.relative_to(repo))
                if any(ex in rel for ex in exclude) or is_secret_file(rel):
                    continue
                try:
                    content = path.read_text(errors="replace")
                    files.append(FileContent(path=rel, content=content))
                except (PermissionError, OSError):
                    continue

        return files

    def get_prompt_from_file(self, prompt_name: str) -> str:
        """Load a prompt template from the focus_prompts directory."""
        prompt_file = Path(__file__).parent.parent / "focus_prompts" / f"{prompt_name}.md"
        if prompt_file.exists():
            return prompt_file.read_text()
        # No file found — subclass must override get_prompt() directly
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")


def extract_file_snippets(file: FileContent, max_lines: int = 50) -> FileContent:
    """Extract a representative snippet from a file for pre-pass enrichment.

    Returns the first and last portions of the file (each max_lines/2 lines)
    with a truncation marker in between. Files already within max_lines are
    returned unchanged.
    """
    lines = file.content.splitlines()
    if len(lines) <= max_lines:
        return file

    half = max_lines // 2
    omitted = len(lines) - max_lines
    snippet_lines = lines[:half] + [f"# ... [{omitted} lines omitted] ..."] + lines[-half:]
    return FileContent(path=file.path, content="\n".join(snippet_lines))


def extract_file_map(file: FileContent) -> FileContent:
    """Extract a structural map from a file for pre-pass enrichment.

    Retains only top-level definitions (classes, functions, constants) and
    their docstrings/comments. Useful for giving the main audit model context
    about a file's structure without the full implementation.
    """
    import re

    lines = file.content.splitlines()
    map_lines: list[str] = []

    # Patterns that signal a top-level definition line worth keeping
    _DEF_RE = re.compile(
        r"^(class |def |async def |function |export\s+(default\s+)?(class|function|const|let|var)\s)"
    )
    _COMMENT_RE = re.compile(r'^\s*(#|//|/\*|"""|\'\'\')')

    for line in lines:
        stripped = line.strip()
        if _DEF_RE.match(stripped) or _COMMENT_RE.match(line):
            map_lines.append(line)

    if not map_lines:
        # Fallback: return first 20 lines to avoid sending empty content
        map_lines = lines[:20]

    return FileContent(
        path=file.path,
        content="# [file map — definitions only]\n" + "\n".join(map_lines),
    )


def gather_files_combined(
    focus_areas: list[BaseFocus],
    repo_path: str | Path,
    exclude_patterns: list[str] | None = None,
) -> list[FileContent]:
    """Gather files from repo matching the union of all focus areas' patterns, deduped by path."""
    repo = Path(repo_path)
    exclude = set(exclude_patterns or [])
    exclude.update(DEFAULT_EXCLUDES)

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
            if any(ex in rel for ex in exclude) or is_secret_file(rel):
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
