"""Google Gemini provider — uses synchronous API calls."""

from __future__ import annotations

import hashlib
import json
import os

try:
    import google.genai as genai
except ImportError:
    genai = None

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


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, model: str = "gemini-2.0-flash"):
        if genai is None:
            raise ImportError(
                "google-genai is not installed. Install with: pip install google-genai"
            )
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        genai.configure(api_key=api_key)
        self.model = model
        self.client = genai.GenerativeModel(model)

    def run_audit(
        self,
        files: list[FileContent],
        system_prompt: str,
        decision_context: str,
        num_focus_areas: int = 1,
        default_focus: str | None = None,
    ) -> list[Finding]:
        """Run an audit synchronously and return findings."""
        user_message = self._build_user_message(files, decision_context)

        response = self.client.generate_content(
            [system_prompt, user_message],
        )

        return self._parse_response(response, default_focus=default_focus)

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
