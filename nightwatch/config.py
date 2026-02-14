"""Configuration loading and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


DEFAULT_SCHEDULE = {
    "monday": "security",
    "tuesday": "patterns",
    "wednesday": "docs",
    "thursday": "hygiene",
    "friday": "performance",
    "saturday": "dependencies",
    "sunday": "off",
}

WEEKDAY_NAMES = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


@dataclass
class RepoConfig:
    name: str
    path: str
    provider_rotation: list[str] = field(default_factory=lambda: ["anthropic"])
    exclude_patterns: list[str] = field(default_factory=list)


@dataclass
class BudgetConfig:
    max_per_run_usd: float = 2.0
    alert_threshold_usd: float = 1.5


@dataclass
class NotificationConfig:
    channel: str = "telegram"
    target: str = ""
    webhook: str = ""


@dataclass
class DecisionConfig:
    expiry_days: int = 90
    path: str = ".nightwatch/decisions.jsonl"


@dataclass
class IssuesConfig:
    enabled: bool = False
    severity_threshold: str = "medium"  # "low", "medium", or "high"
    labels: list[str] = field(default_factory=lambda: ["nightwatch"])
    assignees: list[str] = field(default_factory=list)


@dataclass
class NightwatchConfig:
    repos: list[RepoConfig] = field(default_factory=list)
    schedule: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_SCHEDULE))
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    notifications: list[NotificationConfig] = field(default_factory=list)
    decisions: DecisionConfig = field(default_factory=DecisionConfig)
    issues: IssuesConfig = field(default_factory=IssuesConfig)
    reports_dir: str = ".nightwatch/reports"
    model: str = "claude-sonnet-4-5-20250929"

    def get_today_focus(self) -> str:
        import datetime

        day = WEEKDAY_NAMES[datetime.date.today().weekday()]
        return self.schedule.get(day, "off")

    def get_provider_for_repo(self, repo_name: str, run_index: int = 0) -> str:
        for repo in self.repos:
            if repo.name == repo_name:
                providers = repo.provider_rotation
                return providers[run_index % len(providers)]
        return "anthropic"


def load_config(config_path: str | Path | None = None) -> NightwatchConfig:
    """Load config from nightwatch.yml, falling back to defaults."""
    if config_path is None:
        config_path = Path("nightwatch.yml")
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        return NightwatchConfig()

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    repos = []
    for r in raw.get("repos", []):
        repos.append(
            RepoConfig(
                name=r["name"],
                path=os.path.expanduser(r["path"]),
                provider_rotation=r.get("provider_rotation", ["anthropic"]),
                exclude_patterns=r.get("exclude", []),
            )
        )

    schedule = dict(DEFAULT_SCHEDULE)
    schedule.update(raw.get("schedule", {}))

    budget_raw = raw.get("budget", {})
    budget = BudgetConfig(
        max_per_run_usd=budget_raw.get("max_per_run_usd", 2.0),
        alert_threshold_usd=budget_raw.get("alert_threshold_usd", 1.5),
    )

    notifications = []
    for n in raw.get("notifications", []):
        notifications.append(
            NotificationConfig(
                channel=n.get("channel", "telegram"),
                target=n.get("target", ""),
                webhook=n.get("webhook", ""),
            )
        )

    decisions_raw = raw.get("decisions", {})
    decisions = DecisionConfig(
        expiry_days=decisions_raw.get("expiry_days", 90),
        path=decisions_raw.get("path", ".nightwatch/decisions.jsonl"),
    )

    issues_raw = raw.get("issues", {})
    issues = IssuesConfig(
        enabled=issues_raw.get("enabled", False),
        severity_threshold=issues_raw.get("severity_threshold", "medium"),
        labels=issues_raw.get("labels", ["nightwatch"]),
        assignees=issues_raw.get("assignees", []),
    )

    return NightwatchConfig(
        repos=repos,
        schedule=schedule,
        budget=budget,
        notifications=notifications,
        decisions=decisions,
        issues=issues,
        reports_dir=raw.get("reports_dir", ".nightwatch/reports"),
        model=raw.get("model", "claude-sonnet-4-5-20250929"),
    )
