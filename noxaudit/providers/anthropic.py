"""Anthropic (Claude) provider — uses Message Batches API (50% off)."""

from __future__ import annotations

import hashlib
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


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

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
        max_tokens = 4096 * num_focus_areas

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
                    findings = self._parse_response(
                        entry.result.message, default_focus=default_focus
                    )
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
        import time

        batch_id = self.submit_batch(
            files,
            system_prompt,
            decision_context,
            num_focus_areas=num_focus_areas,
        )
        print(f"  Batch submitted: {batch_id}")

        while True:
            result = self.retrieve_batch(batch_id, default_focus=default_focus)
            if result["status"] == "ended":
                return result.get("findings", [])

            processing = result["request_counts"]["processing"]
            print(f"  Waiting... ({processing} processing)")
            time.sleep(60)

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
        text = message.content[0].text

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
                id=self._make_finding_id(f),
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

    def _make_finding_id(self, raw: dict) -> str:
        key = f"{raw['file']}:{raw['title']}:{raw.get('line', '')}"
        # Include focus in hash when present for combined runs
        if raw.get("focus"):
            key = f"{raw['focus']}:{key}"
        return hashlib.sha256(key.encode()).hexdigest()[:12]
