"""Shared fixtures for noxaudit tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from noxaudit.models import AuditResult, Finding, Severity


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a minimal repo structure for file-gathering tests."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hello')")
    (tmp_path / "src" / "utils.ts").write_text("export const x = 1;")
    (tmp_path / "README.md").write_text("# My App")
    (tmp_path / "package.json").write_text('{"name": "test"}')
    (tmp_path / "config.yml").write_text("key: value")
    (tmp_path / "Dockerfile").write_text("FROM python:3.12")
    (tmp_path / "setup.sh").write_text("#!/bin/bash\necho hi")
    # Files that should be excluded
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("module.exports = {}")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]")
    return tmp_path


@pytest.fixture
def sample_findings():
    """A list of findings across severities."""
    return [
        Finding(
            id="aaa111",
            severity=Severity.HIGH,
            file="src/auth.py",
            line=42,
            title="SQL injection",
            description="User input interpolated into query",
            suggestion="Use parameterized queries",
            focus="security",
        ),
        Finding(
            id="bbb222",
            severity=Severity.MEDIUM,
            file="src/api.ts",
            line=10,
            title="Missing rate limit",
            description="Endpoint has no rate limiting",
            focus="security",
        ),
        Finding(
            id="ccc333",
            severity=Severity.LOW,
            file="README.md",
            line=None,
            title="Stale install instructions",
            description="README references deprecated CLI flag",
            focus="docs",
        ),
    ]


@pytest.fixture
def sample_result(sample_findings):
    """An AuditResult with findings."""
    return AuditResult(
        repo="my-app",
        focus="security",
        provider="anthropic",
        findings=sample_findings,
        new_findings=sample_findings,
        resolved_count=2,
        timestamp="2026-02-14T10:00:00",
    )


@pytest.fixture
def combined_result(sample_findings):
    """An AuditResult from a combined run."""
    return AuditResult(
        repo="my-app",
        focus="security+docs",
        provider="anthropic",
        findings=sample_findings,
        new_findings=sample_findings,
        resolved_count=1,
        timestamp="2026-02-14T10:00:00",
    )


@pytest.fixture
def tmp_config(tmp_path):
    """Write a noxaudit.yml and return its path."""

    def _write(content: str) -> Path:
        p = tmp_path / "noxaudit.yml"
        p.write_text(textwrap.dedent(content))
        return p

    return _write
