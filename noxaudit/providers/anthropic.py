"""Anthropic (Claude) provider — uses Message Batches API (50% off)."""

from __future__ import annotations

import json
import os

import anthropic

from noxaudit.models import FileContent, Finding, Severity
from noxaudit.providers.base import BaseProvider

FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "file": {"type": "string"},
                    "line": {"type": ["integer", "null"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "suggestion": {"type": ["string", "null"]},
                    "focus": {"type": ["string", "null"]},
                },
                "required": ["severity", "file", "title", "description"],
            },
        }
    },
    "required": ["findings"],
}


# Output budget per focus area. Thinking counts against max_tokens on models that
# always think, so 4096/area truncated multi-focus runs. Capped at 64K, the
# smallest max output among supported Claude models (Haiku 4.5, Sonnet 4.6).
MAX_TOKENS_PER_FOCUS = 16384
MAX_TOKENS_CAP = 64000


def _max_tokens(num_focus_areas: int) -> int:
    return min(MAX_TOKENS_PER_FOCUS * num_focus_areas, MAX_TOKENS_CAP)


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-6"):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self._last_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }

    def submit_batch(
        self,
        files: list[FileContent],
        system_prompt: str,
        decision_context: str,
        custom_id: str = "noxaudit-audit",
        num_focus_areas: int = 1,
    ) -> str:
        """Submit a batch request. Returns the batch ID."""
        user_message = self._build_user_message(files, decision_context)
        max_tokens = _max_tokens(num_focus_areas)

        batch = self.client.messages.batches.create(
            requests=[
                {
                    "custom_id": custom_id,
                    "params": {
                        "model": self.model,
                        "max_tokens": max_tokens,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": user_message}],
                    },
                }
            ]
        )

        return batch.id

    def retrieve_batch(
        self,
        batch_id: str,
        default_focus: str | None = None,
    ) -> dict:
        """Check batch status. Returns dict with status and results if done."""
        batch = self.client.messages.batches.retrieve(batch_id)

        result = {
            "batch_id": batch_id,
            "status": batch.processing_status,
            "request_counts": {
                "processing": batch.request_counts.processing,
                "succeeded": batch.request_counts.succeeded,
                "errored": batch.request_counts.errored,
            },
        }

        if batch.processing_status == "ended":
            findings = []
            for entry in self.client.messages.batches.results(batch_id):
                if entry.result.type == "succeeded":
                    message = entry.result.message
                    # Store usage information for later retrieval
                    if hasattr(message, "usage") and message.usage:
                        self._last_usage = {
                            "input_tokens": message.usage.input_tokens or 0,
                            "output_tokens": message.usage.output_tokens or 0,
                            "cache_read_tokens": getattr(
                                message.usage, "cache_read_input_tokens", 0
                            )
                            or 0,
                            "cache_write_tokens": getattr(
                                message.usage, "cache_creation_input_tokens", 0
                            )
                            or 0,
                        }
                    findings = self._parse_response(message, default_focus=default_focus)
            result["findings"] = findings

        return result

    def run_audit(
        self,
        files: list[FileContent],
        system_prompt: str,
        decision_context: str,
        num_focus_areas: int = 1,
        default_focus: str | None = None,
    ) -> list[Finding]:
        """Synchronous audit (for local CLI use). Submits batch and polls."""
        batch_id = self.submit_batch(
            files,
            system_prompt,
            decision_context,
            num_focus_areas=num_focus_areas,
        )
        print(f"  Batch submitted: {batch_id}")
        return self._poll_batch(batch_id, default_focus=default_focus)

    def run_sync(
        self,
        files: list[FileContent],
        system_prompt: str,
        decision_context: str,
        num_focus_areas: int = 1,
        default_focus: str | None = None,
    ) -> list[Finding]:
        """Direct message API — no batch queue."""
        user_message = self._build_user_message(files, decision_context)
        max_tokens = _max_tokens(num_focus_areas)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        usage = message.usage
        self._last_usage = {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
            "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        }

        return self._parse_response(message, default_focus=default_focus)

    def _build_user_message(self, files: list[FileContent], decision_context: str) -> str:
        file_contents = self._format_files(files)
        return f"""Review the following codebase files and report any findings.

{decision_context}

## Files

{file_contents}

Respond with a JSON object matching this schema:
```json
{json.dumps(FINDING_SCHEMA, indent=2)}
```

Return ONLY the JSON object, no other text."""

    def _format_files(self, files: list[FileContent]) -> str:
        parts = []
        for f in files:
            parts.append(f"### `{f.path}`\n```\n{f.content}\n```")
        return "\n\n".join(parts)

    def _parse_response(
        self,
        message: anthropic.types.Message,
        default_focus: str | None = None,
    ) -> list[Finding]:
        # Adaptive-thinking models (Opus 5.5, Sonnet 5.5) return thinking blocks
        # ahead of the text block, so join text blocks rather than taking content[0].
        text = "".join(
            block.text
            for block in message.content
            if getattr(block, "type", None) not in ("thinking", "redacted_thinking")
        )

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        data = json.loads(text.strip())
        findings = []

        for f in data.get("findings", []):
            focus = f.get("focus") or default_focus
            finding = Finding(
                id=self.make_finding_id(f),
                severity=Severity(f["severity"]),
                file=f["file"],
                line=f.get("line"),
                title=f["title"],
                description=f["description"],
                suggestion=f.get("suggestion"),
                focus=focus,
            )
            findings.append(finding)

        return findings

    def get_last_usage(self) -> dict:
        """Return token usage from the last API call."""
        return self._last_usage
