"""Tests for the Anthropic provider (no API calls)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from noxaudit.models import Severity
from noxaudit.providers.anthropic import AnthropicProvider, FINDING_SCHEMA


class TestFindingSchema:
    def test_has_focus_field(self):
        props = FINDING_SCHEMA["properties"]["findings"]["items"]["properties"]
        assert "focus" in props
        assert props["focus"]["type"] == ["string", "null"]

    def test_focus_not_required(self):
        required = FINDING_SCHEMA["properties"]["findings"]["items"]["required"]
        assert "focus" not in required


class TestMakeFindingId:
    @pytest.fixture
    def provider(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        p = AnthropicProvider.__new__(AnthropicProvider)
        return p

    def test_stable_hash(self, provider):
        raw = {"file": "src/app.py", "title": "SQL injection", "line": 42}
        id1 = provider._make_finding_id(raw)
        id2 = provider._make_finding_id(raw)
        assert id1 == id2
        assert len(id1) == 12

    def test_different_inputs_different_ids(self, provider):
        a = {"file": "a.py", "title": "Bug A", "line": 1}
        b = {"file": "b.py", "title": "Bug B", "line": 2}
        assert provider._make_finding_id(a) != provider._make_finding_id(b)

    def test_focus_changes_id(self, provider):
        base = {"file": "a.py", "title": "Bug", "line": 1}
        with_focus = {"file": "a.py", "title": "Bug", "line": 1, "focus": "security"}
        id_without = provider._make_finding_id(base)
        id_with = provider._make_finding_id(with_focus)
        assert id_without != id_with

    def test_no_line_still_works(self, provider):
        raw = {"file": "a.py", "title": "Bug"}
        fid = provider._make_finding_id(raw)
        assert len(fid) == 12


class TestParseResponse:
    @pytest.fixture
    def provider(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        p = AnthropicProvider.__new__(AnthropicProvider)
        return p

    def _make_message(self, findings_data):
        """Create a mock Anthropic message with JSON response."""
        msg = MagicMock()
        content = MagicMock()
        content.text = json.dumps({"findings": findings_data})
        msg.content = [content]
        return msg

    def test_basic_parsing(self, provider):
        msg = self._make_message(
            [
                {
                    "severity": "high",
                    "file": "a.py",
                    "line": 1,
                    "title": "Bug",
                    "description": "A bug",
                },
            ]
        )
        findings = provider._parse_response(msg)
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH
        assert findings[0].file == "a.py"
        assert findings[0].focus is None

    def test_focus_extracted(self, provider):
        msg = self._make_message(
            [
                {
                    "severity": "medium",
                    "file": "b.py",
                    "line": 5,
                    "title": "Issue",
                    "description": "An issue",
                    "focus": "security",
                },
            ]
        )
        findings = provider._parse_response(msg)
        assert findings[0].focus == "security"

    def test_default_focus_backfill(self, provider):
        msg = self._make_message(
            [
                {
                    "severity": "low",
                    "file": "c.py",
                    "line": None,
                    "title": "Hint",
                    "description": "A hint",
                },
            ]
        )
        findings = provider._parse_response(msg, default_focus="docs")
        assert findings[0].focus == "docs"

    def test_explicit_focus_overrides_default(self, provider):
        msg = self._make_message(
            [
                {
                    "severity": "low",
                    "file": "c.py",
                    "line": None,
                    "title": "Hint",
                    "description": "A hint",
                    "focus": "security",
                },
            ]
        )
        findings = provider._parse_response(msg, default_focus="docs")
        assert findings[0].focus == "security"

    def test_markdown_code_block(self, provider):
        msg = MagicMock()
        content = MagicMock()
        content.text = '```json\n{"findings": [{"severity": "high", "file": "x.py", "title": "T", "description": "D"}]}\n```'
        msg.content = [content]
        findings = provider._parse_response(msg)
        assert len(findings) == 1

    def test_multiple_findings(self, provider):
        msg = self._make_message(
            [
                {"severity": "high", "file": "a.py", "title": "A", "description": "D1"},
                {
                    "severity": "low",
                    "file": "b.py",
                    "title": "B",
                    "description": "D2",
                    "focus": "perf",
                },
            ]
        )
        findings = provider._parse_response(msg, default_focus="security")
        assert len(findings) == 2
        assert findings[0].focus == "security"  # backfilled
        assert findings[1].focus == "perf"  # explicit


class TestSubmitBatchMaxTokens:
    def test_scales_with_focus_areas(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.model = "claude-sonnet-4-5-20250929"
        provider.client = MagicMock()

        mock_batch = MagicMock()
        mock_batch.id = "batch_123"
        provider.client.messages.batches.create.return_value = mock_batch

        from noxaudit.models import FileContent

        files = [FileContent(path="a.py", content="x = 1")]

        provider.submit_batch(files, "prompt", "", num_focus_areas=3)

        call_args = provider.client.messages.batches.create.call_args
        params = call_args[1]["requests"][0]["params"]
        assert params["max_tokens"] == 4096 * 3
