"""Google Gemini provider — uses synchronous API calls and Batch API (50% off)."""

from __future__ import annotations

import hashlib
import io
import json
import os

try:
    import google.genai as genai
except ImportError:
    genai = None

from noxaudit.models import FileContent, Finding, Severity
from noxaudit.providers.base import BaseProvider

# Terminal batch states
_GEMINI_TERMINAL_STATES = frozenset(
    {"JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED"}
)

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


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash"):
        if genai is None:
            raise ImportError(
                "google-genai is not installed. Install with: pip install google-genai"
            )
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        self.model = model
        self._api_client = genai.Client(api_key=api_key)
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
        """Submit a batch request via Gemini Batch API. Returns the batch job name."""
        user_message = self._build_user_message(files, decision_context)

        request = {
            "key": custom_id,
            "request": {
                "contents": [{"role": "user", "parts": [{"text": user_message}]}],
                "system_instruction": {"parts": [{"text": system_prompt}]},
            },
        }
        jsonl_bytes = (json.dumps(request) + "\n").encode("utf-8")

        buf = io.BytesIO(jsonl_bytes)
        buf.name = "batch_request.jsonl"
        uploaded = self._api_client.files.upload(
            file=buf,
            config={"mime_type": "application/jsonl"},
        )

        batch_job = self._api_client.batches.create(
            model=self.model,
            src=uploaded.name,
            config={"display_name": f"noxaudit-{custom_id}"},
        )

        return batch_job.name

    def retrieve_batch(
        self,
        batch_id: str,
        default_focus: str | None = None,
    ) -> dict:
        """Check batch status. Returns dict with status and results if done."""
        batch_job = self._api_client.batches.get(name=batch_id)
        state_name = batch_job.state.name

        is_done = state_name in _GEMINI_TERMINAL_STATES
        status = "ended" if is_done else "processing"

        succeeded = 1 if state_name == "JOB_STATE_SUCCEEDED" else 0
        errored = 1 if state_name in ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED") else 0
        processing = 0 if is_done else 1

        result = {
            "batch_id": batch_id,
            "status": status,
            "request_counts": {
                "processing": processing,
                "succeeded": succeeded,
                "errored": errored,
            },
        }

        if state_name == "JOB_STATE_SUCCEEDED":
            findings = []
            content = self._api_client.files.download(file=batch_job.dest.file_name)
            raw_text = (
                content.decode("utf-8")
                if isinstance(content, bytes)
                else content.read().decode("utf-8")
            )
            result["raw_response"] = raw_text

            for line in raw_text.splitlines():
                if not line.strip():
                    continue
                entry = json.loads(line)

                # Check for error responses (e.g. deprecated models)
                if "error" in entry and "response" not in entry:
                    err_msg = entry["error"].get("message", "unknown error")
                    raise RuntimeError(f"Gemini batch error: {err_msg}")

                response = entry.get("response", {})
                candidates = response.get("candidates", [])
                if candidates:
                    content_parts = candidates[0].get("content", {}).get("parts", [])
                    if content_parts:
                        response_text = content_parts[0].get("text", "")
                        findings = self._parse_text(response_text, default_focus=default_focus)

                usage = response.get("usageMetadata", {})
                if usage:
                    self._last_usage = {
                        "input_tokens": usage.get("promptTokenCount", 0) or 0,
                        "output_tokens": usage.get("candidatesTokenCount", 0) or 0,
                        "cache_read_tokens": usage.get("cachedContentTokenCount", 0) or 0,
                        "cache_write_tokens": 0,
                    }

            result["findings"] = findings

        elif is_done:
            result["findings"] = []

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

        data = self._safe_json_loads(text.strip())
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

    def _parse_response(
        self,
        response,
        default_focus: str | None = None,
    ) -> list[Finding]:
        text = response.text

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

    def get_last_usage(self) -> dict:
        """Return token usage from the last API call."""
        return self._last_usage
