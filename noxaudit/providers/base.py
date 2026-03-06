"""Abstract base provider."""

from __future__ import annotations

import json
import re
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

    def get_last_usage(self) -> dict:
        """Return token usage from the last API call.

        Returns dict with keys: input_tokens, output_tokens, cache_read_tokens, cache_write_tokens.
        """
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }

    @staticmethod
    def _safe_json_loads(text: str) -> dict:
        """Parse JSON from LLM output, handling common malformation issues."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Fix invalid backslash escapes (e.g. \n inside already-quoted strings
        # that the LLM didn't properly escape)
        try:
            fixed = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r"\\\\", text)
            return json.loads(fixed)
        except (json.JSONDecodeError, re.error):
            pass

        # Fix unterminated strings by removing control characters
        try:
            cleaned = text.replace("\r\n", "\\n").replace("\r", "\\n")
            # Replace literal newlines inside JSON string values
            cleaned = re.sub(
                r'(?<=": ")(.*?)(?="[,}\]])',
                lambda m: m.group().replace("\n", "\\n"),
                cleaned,
                flags=re.DOTALL,
            )
            return json.loads(cleaned)
        except (json.JSONDecodeError, re.error):
            pass

        # Last resort: return empty findings
        return {"findings": []}
