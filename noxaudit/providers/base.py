"""Abstract base provider."""

from __future__ import annotations

from abc import ABC, abstractmethod

from noxaudit.models import FileContent, Finding


class BaseProvider(ABC):
    """Base class for AI providers."""

    name: str = "base"

    @abstractmethod
    def run_audit(
        self,
        files: list[FileContent],
        system_prompt: str,
        decision_context: str,
    ) -> list[Finding]:
        """Run an audit and return findings."""
        ...
