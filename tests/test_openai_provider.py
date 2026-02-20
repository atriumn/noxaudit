"""Tests for the OpenAI provider (no API calls)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from noxaudit.models import Severity
from noxaudit.providers.openai import FINDING_SCHEMA, OpenAIProvider


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
    def provider(self):
        p = OpenAIProvider.__new__(OpenAIProvider)
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
        assert provider._make_finding_id(base) != provider._make_finding_id(with_focus)

    def test_no_line_still_works(self, provider):
        raw = {"file": "a.py", "title": "Bug"}
        fid = provider._make_finding_id(raw)
        assert len(fid) == 12

    def test_matches_anthropic_id_logic(self, provider):
        """Finding IDs should use the same SHA-256 logic as Anthropic provider."""
        import hashlib

        raw = {"file": "src/main.py", "title": "SQL injection", "line": 10}
        expected_key = "src/main.py:SQL injection:10"
        expected_id = hashlib.sha256(expected_key.encode()).hexdigest()[:12]
        assert provider._make_finding_id(raw) == expected_id


class TestParseText:
    @pytest.fixture
    def provider(self):
        p = OpenAIProvider.__new__(OpenAIProvider)
        return p

    def test_basic_parsing(self, provider):
        text = json.dumps(
            {
                "findings": [
                    {
                        "severity": "high",
                        "file": "a.py",
                        "line": 1,
                        "title": "Bug",
                        "description": "A bug",
                    }
                ]
            }
        )
        findings = provider._parse_text(text)
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH
        assert findings[0].file == "a.py"
        assert findings[0].focus is None

    def test_focus_extracted(self, provider):
        text = json.dumps(
            {
                "findings": [
                    {
                        "severity": "medium",
                        "file": "b.py",
                        "line": 5,
                        "title": "Issue",
                        "description": "An issue",
                        "focus": "security",
                    }
                ]
            }
        )
        findings = provider._parse_text(text)
        assert findings[0].focus == "security"

    def test_default_focus_backfill(self, provider):
        text = json.dumps(
            {
                "findings": [
                    {
                        "severity": "low",
                        "file": "c.py",
                        "line": None,
                        "title": "Hint",
                        "description": "A hint",
                    }
                ]
            }
        )
        findings = provider._parse_text(text, default_focus="docs")
        assert findings[0].focus == "docs"

    def test_explicit_focus_overrides_default(self, provider):
        text = json.dumps(
            {
                "findings": [
                    {
                        "severity": "low",
                        "file": "c.py",
                        "line": None,
                        "title": "Hint",
                        "description": "A hint",
                        "focus": "security",
                    }
                ]
            }
        )
        findings = provider._parse_text(text, default_focus="docs")
        assert findings[0].focus == "security"

    def test_markdown_code_block(self, provider):
        text = '```json\n{"findings": [{"severity": "high", "file": "x.py", "title": "T", "description": "D"}]}\n```'
        findings = provider._parse_text(text)
        assert len(findings) == 1

    def test_multiple_findings(self, provider):
        text = json.dumps(
            {
                "findings": [
                    {"severity": "high", "file": "a.py", "title": "A", "description": "D1"},
                    {
                        "severity": "low",
                        "file": "b.py",
                        "title": "B",
                        "description": "D2",
                        "focus": "perf",
                    },
                ]
            }
        )
        findings = provider._parse_text(text, default_focus="security")
        assert len(findings) == 2
        assert findings[0].focus == "security"  # backfilled
        assert findings[1].focus == "perf"  # explicit


class TestSubmitBatch:
    @pytest.fixture
    def provider(self):
        p = OpenAIProvider.__new__(OpenAIProvider)
        p.model = "gpt-5.2"
        p.client = MagicMock()
        mock_file = MagicMock()
        mock_file.id = "file-abc123"
        p.client.files.create.return_value = mock_file
        mock_batch = MagicMock()
        mock_batch.id = "batch_xyz789"
        p.client.batches.create.return_value = mock_batch
        return p

    def test_returns_batch_id(self, provider):
        from noxaudit.models import FileContent

        files = [FileContent(path="a.py", content="x = 1")]
        batch_id = provider.submit_batch(files, "system prompt", "context")
        assert batch_id == "batch_xyz789"

    def test_uploads_file_then_creates_batch(self, provider):
        from noxaudit.models import FileContent

        files = [FileContent(path="a.py", content="x = 1")]
        provider.submit_batch(files, "prompt", "ctx")

        assert provider.client.files.create.called
        call_kwargs = provider.client.files.create.call_args[1]
        assert call_kwargs["purpose"] == "batch"

        assert provider.client.batches.create.called
        batch_kwargs = provider.client.batches.create.call_args[1]
        assert batch_kwargs["input_file_id"] == "file-abc123"
        assert batch_kwargs["endpoint"] == "/v1/chat/completions"
        assert batch_kwargs["completion_window"] == "24h"

    def test_jsonl_has_correct_structure(self, provider):

        from noxaudit.models import FileContent

        files = [FileContent(path="a.py", content="x = 1")]
        provider.submit_batch(files, "sys", "ctx", custom_id="my-audit")

        file_create_kwargs = provider.client.files.create.call_args[1]
        file_data = file_create_kwargs["file"]
        if hasattr(file_data, "read"):
            jsonl_text = file_data.read().decode("utf-8")
        else:
            jsonl_text = (
                file_data.decode("utf-8") if isinstance(file_data, bytes) else str(file_data)
            )

        entry = json.loads(jsonl_text.strip())
        assert entry["custom_id"] == "my-audit"
        assert entry["method"] == "POST"
        assert entry["url"] == "/v1/chat/completions"
        assert entry["body"]["model"] == "gpt-5.2"
        assert entry["body"]["response_format"]["type"] == "json_schema"

    def test_scales_max_tokens_with_focus_areas(self, provider):
        from noxaudit.models import FileContent

        files = [FileContent(path="a.py", content="x = 1")]
        provider.submit_batch(files, "prompt", "", num_focus_areas=3)

        file_create_kwargs = provider.client.files.create.call_args[1]
        file_data = file_create_kwargs["file"]
        if hasattr(file_data, "read"):
            jsonl_text = file_data.read().decode("utf-8")
        else:
            jsonl_text = (
                file_data.decode("utf-8") if isinstance(file_data, bytes) else str(file_data)
            )

        entry = json.loads(jsonl_text.strip())
        assert entry["body"]["max_tokens"] == 4096 * 3


class TestRetrieveBatch:
    @pytest.fixture
    def provider(self):
        p = OpenAIProvider.__new__(OpenAIProvider)
        p.model = "gpt-5.2"
        p.client = MagicMock()
        p._last_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }
        return p

    def _make_batch(self, status, output_file_id=None, total=1, completed=0, failed=0):
        batch = MagicMock()
        batch.status = status
        batch.output_file_id = output_file_id
        counts = MagicMock()
        counts.total = total
        counts.completed = completed
        counts.failed = failed
        batch.request_counts = counts
        return batch

    def _make_output_line(self, findings_data):
        body = {
            "choices": [{"message": {"content": json.dumps({"findings": findings_data})}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "prompt_tokens_details": {"cached_tokens": 10},
            },
        }
        entry = {
            "custom_id": "noxaudit-audit",
            "response": {"status_code": 200, "body": body},
        }
        return json.dumps(entry)

    def test_in_progress_returns_non_ended_status(self, provider):
        provider.client.batches.retrieve.return_value = self._make_batch(
            "in_progress", total=1, completed=0, failed=0
        )
        result = provider.retrieve_batch("batch_123")
        assert result["status"] != "ended"
        assert result["request_counts"]["processing"] == 1

    def test_completed_returns_ended_status(self, provider):
        batch = self._make_batch(
            "completed", output_file_id="file-out", total=1, completed=1, failed=0
        )
        provider.client.batches.retrieve.return_value = batch

        output_line = self._make_output_line(
            [{"severity": "high", "file": "a.py", "title": "Bug", "description": "Desc"}]
        )
        mock_content = MagicMock()
        mock_content.read.return_value = output_line.encode("utf-8")
        provider.client.files.content.return_value = mock_content

        result = provider.retrieve_batch("batch_123")
        assert result["status"] == "ended"
        assert len(result["findings"]) == 1
        assert result["findings"][0].severity == Severity.HIGH

    def test_failed_batch_returns_ended_with_no_findings(self, provider):
        batch = self._make_batch("failed", total=1, completed=0, failed=1)
        provider.client.batches.retrieve.return_value = batch

        result = provider.retrieve_batch("batch_123")
        assert result["status"] == "ended"
        assert result.get("findings", []) == []

    def test_tracks_token_usage(self, provider):
        batch = self._make_batch("completed", output_file_id="file-out", total=1, completed=1)
        provider.client.batches.retrieve.return_value = batch

        output_line = self._make_output_line([])
        mock_content = MagicMock()
        mock_content.read.return_value = output_line.encode("utf-8")
        provider.client.files.content.return_value = mock_content

        provider.retrieve_batch("batch_123")
        usage = provider.get_last_usage()
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50
        assert usage["cache_read_tokens"] == 10

    def test_default_focus_applied(self, provider):
        batch = self._make_batch("completed", output_file_id="file-out", total=1, completed=1)
        provider.client.batches.retrieve.return_value = batch

        output_line = self._make_output_line(
            [{"severity": "low", "file": "a.py", "title": "T", "description": "D"}]
        )
        mock_content = MagicMock()
        mock_content.read.return_value = output_line.encode("utf-8")
        provider.client.files.content.return_value = mock_content

        result = provider.retrieve_batch("batch_123", default_focus="security")
        assert result["findings"][0].focus == "security"


class TestRunAudit:
    def test_polls_until_complete(self):
        p = OpenAIProvider.__new__(OpenAIProvider)
        p.model = "gpt-5.2"
        p.client = MagicMock()
        p._last_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }

        mock_file = MagicMock()
        mock_file.id = "file-abc"
        p.client.files.create.return_value = mock_file
        mock_batch_obj = MagicMock()
        mock_batch_obj.id = "batch_poll_test"
        p.client.batches.create.return_value = mock_batch_obj

        call_count = 0

        def retrieve_side_effect(batch_id, default_focus=None):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return {
                    "batch_id": batch_id,
                    "status": "in_progress",
                    "request_counts": {"processing": 1, "succeeded": 0, "errored": 0},
                }
            return {
                "batch_id": batch_id,
                "status": "ended",
                "findings": [],
                "request_counts": {"processing": 0, "succeeded": 1, "errored": 0},
            }

        import unittest.mock as mock

        from noxaudit.models import FileContent

        with (
            mock.patch.object(p, "retrieve_batch", side_effect=retrieve_side_effect),
            mock.patch("time.sleep"),
        ):
            findings = p.run_audit([FileContent(path="a.py", content="x = 1")], "prompt", "ctx")

        assert findings == []
        assert call_count == 3


class TestImportError:
    def test_missing_openai_raises_import_error(self, monkeypatch):
        import noxaudit.providers.openai as openai_mod

        monkeypatch.setattr(openai_mod, "openai", None)
        with pytest.raises(ImportError, match="openai is not installed"):
            OpenAIProvider()
