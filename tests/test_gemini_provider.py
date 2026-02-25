"""Tests for the Gemini provider batch API (no API calls)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from noxaudit.models import FileContent, Severity
from noxaudit.providers.gemini import GeminiProvider, FINDING_SCHEMA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider():
    """Create a GeminiProvider instance bypassing __init__."""
    p = GeminiProvider.__new__(GeminiProvider)
    p.model = "gemini-2.5-flash"
    p._api_client = MagicMock()
    p._last_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
    }
    return p


def _make_output_line(findings_data, usage=None):
    """Create a JSONL response line matching Gemini batch output format."""
    response_text = json.dumps({"findings": findings_data})
    if usage is None:
        usage = {
            "promptTokenCount": 100,
            "candidatesTokenCount": 50,
            "cachedContentTokenCount": 10,
        }
    entry = {
        "key": "noxaudit-audit",
        "response": {
            "candidates": [{"content": {"role": "model", "parts": [{"text": response_text}]}}],
            "usageMetadata": usage,
        },
    }
    return json.dumps(entry)


# ---------------------------------------------------------------------------
# TestFindingSchema
# ---------------------------------------------------------------------------


class TestFindingSchema:
    def test_has_focus_field(self):
        props = FINDING_SCHEMA["properties"]["findings"]["items"]["properties"]
        assert "focus" in props
        assert props["focus"]["type"] == ["string", "null"]

    def test_focus_not_required(self):
        required = FINDING_SCHEMA["properties"]["findings"]["items"]["required"]
        assert "focus" not in required


# ---------------------------------------------------------------------------
# TestSubmitBatch
# ---------------------------------------------------------------------------


class TestSubmitBatch:
    @pytest.fixture
    def provider(self):
        p = _make_provider()
        mock_file = MagicMock()
        mock_file.name = "files/abc123"
        p._api_client.files.upload.return_value = mock_file
        mock_batch = MagicMock()
        mock_batch.name = "batches/job456"
        p._api_client.batches.create.return_value = mock_batch
        return p

    def test_returns_batch_job_name(self, provider):
        files = [FileContent(path="a.py", content="x = 1")]
        batch_id = provider.submit_batch(files, "system prompt", "context")
        assert batch_id == "batches/job456"

    def test_uploads_file_then_creates_batch(self, provider):
        files = [FileContent(path="a.py", content="x = 1")]
        provider.submit_batch(files, "prompt", "ctx")

        assert provider._api_client.files.upload.called
        assert provider._api_client.batches.create.called

        batch_kwargs = provider._api_client.batches.create.call_args[1]
        assert batch_kwargs["model"] == "gemini-2.5-flash"
        assert batch_kwargs["src"] == "files/abc123"

    def test_jsonl_has_correct_structure(self, provider):
        files = [FileContent(path="a.py", content="x = 1")]
        provider.submit_batch(files, "sys", "ctx", custom_id="my-audit")

        upload_kwargs = provider._api_client.files.upload.call_args[1]
        file_obj = upload_kwargs["file"]
        if hasattr(file_obj, "read"):
            jsonl_text = file_obj.read().decode("utf-8")
        else:
            jsonl_text = file_obj.decode("utf-8") if isinstance(file_obj, bytes) else str(file_obj)

        entry = json.loads(jsonl_text.strip())
        assert entry["key"] == "my-audit"
        assert "request" in entry
        assert "contents" in entry["request"]
        assert "system_instruction" in entry["request"]
        # system prompt is in system_instruction
        assert entry["request"]["system_instruction"]["parts"][0]["text"] == "sys"
        # user message is in contents
        assert entry["request"]["contents"][0]["role"] == "user"

    def test_batch_display_name_includes_custom_id(self, provider):
        files = [FileContent(path="a.py", content="x = 1")]
        provider.submit_batch(files, "prompt", "ctx", custom_id="repo-security")

        batch_kwargs = provider._api_client.batches.create.call_args[1]
        assert "noxaudit-repo-security" in batch_kwargs["config"]["display_name"]


# ---------------------------------------------------------------------------
# TestRetrieveBatch
# ---------------------------------------------------------------------------


class TestRetrieveBatch:
    @pytest.fixture
    def provider(self):
        return _make_provider()

    def _make_batch_job(self, state_name, file_name=None):
        batch_job = MagicMock()
        state = MagicMock()
        state.name = state_name
        batch_job.state = state
        if file_name:
            dest = MagicMock()
            dest.file_name = file_name
            batch_job.dest = dest
        return batch_job

    def test_pending_returns_processing_status(self, provider):
        provider._api_client.batches.get.return_value = self._make_batch_job("JOB_STATE_PENDING")
        result = provider.retrieve_batch("batches/abc123")
        assert result["status"] == "processing"
        assert result["request_counts"]["processing"] == 1

    def test_running_returns_processing_status(self, provider):
        provider._api_client.batches.get.return_value = self._make_batch_job("JOB_STATE_RUNNING")
        result = provider.retrieve_batch("batches/abc123")
        assert result["status"] == "processing"
        assert result["request_counts"]["processing"] == 1

    def test_succeeded_returns_ended_with_findings(self, provider):
        batch_job = self._make_batch_job("JOB_STATE_SUCCEEDED", file_name="files/out123")
        provider._api_client.batches.get.return_value = batch_job

        output_line = _make_output_line(
            [{"severity": "high", "file": "a.py", "title": "Bug", "description": "Desc"}]
        )
        provider._api_client.files.download.return_value = output_line.encode("utf-8")

        result = provider.retrieve_batch("batches/abc123")
        assert result["status"] == "ended"
        assert result["request_counts"]["succeeded"] == 1
        assert result["request_counts"]["errored"] == 0
        assert len(result["findings"]) == 1
        assert result["findings"][0].severity == Severity.HIGH
        assert result["findings"][0].file == "a.py"

    def test_failed_returns_ended_with_empty_findings(self, provider):
        provider._api_client.batches.get.return_value = self._make_batch_job("JOB_STATE_FAILED")
        result = provider.retrieve_batch("batches/abc123")
        assert result["status"] == "ended"
        assert result["request_counts"]["errored"] == 1
        assert result.get("findings", []) == []

    def test_cancelled_returns_ended_with_empty_findings(self, provider):
        provider._api_client.batches.get.return_value = self._make_batch_job("JOB_STATE_CANCELLED")
        result = provider.retrieve_batch("batches/abc123")
        assert result["status"] == "ended"
        assert result["request_counts"]["errored"] == 1
        assert result.get("findings", []) == []

    def test_token_usage_extracted_from_succeeded(self, provider):
        batch_job = self._make_batch_job("JOB_STATE_SUCCEEDED", file_name="files/out123")
        provider._api_client.batches.get.return_value = batch_job

        output_line = _make_output_line(
            [],
            usage={
                "promptTokenCount": 200,
                "candidatesTokenCount": 80,
                "cachedContentTokenCount": 30,
            },
        )
        provider._api_client.files.download.return_value = output_line.encode("utf-8")

        provider.retrieve_batch("batches/abc123")
        usage = provider.get_last_usage()
        assert usage["input_tokens"] == 200
        assert usage["output_tokens"] == 80
        assert usage["cache_read_tokens"] == 30
        assert usage["cache_write_tokens"] == 0

    def test_default_focus_applied_to_findings(self, provider):
        batch_job = self._make_batch_job("JOB_STATE_SUCCEEDED", file_name="files/out123")
        provider._api_client.batches.get.return_value = batch_job

        output_line = _make_output_line(
            [{"severity": "low", "file": "a.py", "title": "T", "description": "D"}]
        )
        provider._api_client.files.download.return_value = output_line.encode("utf-8")

        result = provider.retrieve_batch("batches/abc123", default_focus="security")
        assert result["findings"][0].focus == "security"

    def test_explicit_focus_overrides_default(self, provider):
        batch_job = self._make_batch_job("JOB_STATE_SUCCEEDED", file_name="files/out123")
        provider._api_client.batches.get.return_value = batch_job

        output_line = _make_output_line(
            [
                {
                    "severity": "low",
                    "file": "a.py",
                    "title": "T",
                    "description": "D",
                    "focus": "performance",
                }
            ]
        )
        provider._api_client.files.download.return_value = output_line.encode("utf-8")

        result = provider.retrieve_batch("batches/abc123", default_focus="security")
        assert result["findings"][0].focus == "performance"

    def test_batch_id_preserved_in_result(self, provider):
        provider._api_client.batches.get.return_value = self._make_batch_job("JOB_STATE_RUNNING")
        result = provider.retrieve_batch("batches/my-job")
        assert result["batch_id"] == "batches/my-job"

    def test_download_called_with_dest_file_name(self, provider):
        batch_job = self._make_batch_job("JOB_STATE_SUCCEEDED", file_name="files/result-xyz")
        provider._api_client.batches.get.return_value = batch_job

        output_line = _make_output_line([])
        provider._api_client.files.download.return_value = output_line.encode("utf-8")

        provider.retrieve_batch("batches/abc123")
        download_kwargs = provider._api_client.files.download.call_args[1]
        assert download_kwargs["file"] == "files/result-xyz"


# ---------------------------------------------------------------------------
# TestParseText
# ---------------------------------------------------------------------------


class TestParseText:
    @pytest.fixture
    def provider(self):
        return _make_provider()

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

    def test_markdown_code_block(self, provider):
        text = '```json\n{"findings": [{"severity": "high", "file": "x.py", "title": "T", "description": "D"}]}\n```'
        findings = provider._parse_text(text)
        assert len(findings) == 1

    def test_default_focus_backfill(self, provider):
        text = json.dumps(
            {
                "findings": [
                    {
                        "severity": "low",
                        "file": "c.py",
                        "title": "Hint",
                        "description": "A hint",
                    }
                ]
            }
        )
        findings = provider._parse_text(text, default_focus="docs")
        assert findings[0].focus == "docs"
