"""OpenAI provider — uses Batch API for async, standard API for sync."""

from __future__ import annotations

import hashlib
import io
import json
import os
import time

try:
    import openai
except ImportError:
    openai = None

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

# Terminal batch statuses
_BATCH_TERMINAL = frozenset({"completed", "failed", "expired", "cancelled"})


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, model: str = "gpt-5.2"):
        if openai is None:
            raise ImportError(
                "openai is not installed. Install with: pip install 'noxaudit[openai]'"
            )
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = openai.OpenAI(api_key=api_key)
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
        """Submit a batch request via OpenAI Batch API. Returns the batch ID."""
        user_message = self._build_user_message(files, decision_context)
        max_tokens = 4096 * num_focus_areas

        request = {
            "custom_id": custom_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "audit_findings",
                        "schema": FINDING_SCHEMA,
                    },
                },
            },
        }
        jsonl_bytes = (json.dumps(request) + "\n").encode("utf-8")

        batch_file = self.client.files.create(
            file=io.BytesIO(jsonl_bytes),
            purpose="batch",
        )

        batch = self.client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
        )

        return batch.id

    def retrieve_batch(
        self,
        batch_id: str,
        default_focus: str | None = None,
    ) -> dict:
        """Check batch status. Returns dict with status and results if done."""
        batch = self.client.batches.retrieve(batch_id)

        is_done = batch.status in _BATCH_TERMINAL
        status = "ended" if is_done else batch.status

        counts = batch.request_counts
        total = counts.total if counts else 0
        completed = counts.completed if counts else 0
        failed = counts.failed if counts else 0

        result = {
            "batch_id": batch_id,
            "status": status,
            "request_counts": {
                "processing": max(0, total - completed - failed),
                "succeeded": completed,
                "errored": failed,
            },
        }

        if is_done and batch.output_file_id:
            findings = []
            content = self.client.files.content(batch.output_file_id)
            text = content.read().decode("utf-8")
            for line in text.splitlines():
                if not line.strip():
                    continue
                entry = json.loads(line)
                response = entry.get("response", {})
                if response.get("status_code") == 200:
                    body = response["body"]
                    usage = body.get("usage", {})
                    details = usage.get("prompt_tokens_details") or {}
                    self._last_usage = {
                        "input_tokens": usage.get("prompt_tokens", 0),
                        "output_tokens": usage.get("completion_tokens", 0),
                        "cache_read_tokens": details.get("cached_tokens", 0),
                        "cache_write_tokens": 0,
                    }
                    choices = body.get("choices", [])
                    if choices:
                        message_content = choices[0]["message"]["content"]
                        findings = self._parse_text(message_content, default_focus=default_focus)
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
        """Synchronous audit: submit batch and poll until done."""
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

    def _parse_text(
        self,
        text: str,
        default_focus: str | None = None,
    ) -> list[Finding]:
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
        if raw.get("focus"):
            key = f"{raw['focus']}:{key}"
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    def get_last_usage(self) -> dict:
        """Return token usage from the last API call."""
        return self._last_usage
