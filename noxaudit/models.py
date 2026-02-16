"""Core data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionType(str, Enum):
    ACCEPTED = "accepted"  # Finding was valid, fix was applied
    DISMISSED = "dismissed"  # Finding is not relevant / won't fix
    INTENTIONAL = "intentional"  # Code is correct as-is, don't flag again


@dataclass
class FileContent:
    path: str  # Relative to repo root
    content: str


@dataclass
class Finding:
    id: str  # Stable hash for decision matching
    severity: Severity
    file: str
    line: int | None
    title: str
    description: str
    suggestion: str | None = None
    focus: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "severity": self.severity.value,
            "file": self.file,
            "line": self.line,
            "title": self.title,
            "description": self.description,
            "suggestion": self.suggestion,
        }
        if self.focus:
            d["focus"] = self.focus
        return d


@dataclass
class Decision:
    finding_id: str
    decision: DecisionType
    reason: str
    date: str
    by: str
    file: str | None = None  # File the finding was in (for change detection)
    file_hash: str | None = None  # Hash of file at decision time

    def to_dict(self) -> dict[str, Any]:
        d = {
            "finding_id": self.finding_id,
            "decision": self.decision.value,
            "reason": self.reason,
            "date": self.date,
            "by": self.by,
        }
        if self.file:
            d["file"] = self.file
        if self.file_hash:
            d["file_hash"] = self.file_hash
        return d


@dataclass
class AuditResult:
    repo: str
    focus: str
    provider: str
    findings: list[Finding] = field(default_factory=list)
    new_findings: list[Finding] = field(default_factory=list)  # After decision filtering
    resolved_count: int = 0
    timestamp: str = ""
