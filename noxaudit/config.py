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
    provider_rotation: list[str] = field(default_factory=lambda: ["gemini"])
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
    path: str = ".noxaudit/decisions.jsonl"


@dataclass
class IssuesConfig:
    enabled: bool = False
    severity_threshold: str = "medium"  # "low", "medium", or "high"
    labels: list[str] = field(default_factory=lambda: ["noxaudit"])
    assignees: list[str] = field(default_factory=list)
    repository_url: str = "https://github.com/atriumn/noxaudit"


@dataclass
class PrepassConfig:
    """Pre-pass configuration for file filtering before main audit."""

    enabled: bool = False
    threshold_tokens: int = 600_000
    auto_disable: bool = False


@dataclass
class FrameConfig:
    """Per-focus boolean overrides for a frame."""

    overrides: dict[str, bool] = field(default_factory=dict)


ALL_FOCUS_NAMES = [
    "security",
    "docs",
    "patterns",
    "testing",
    "hygiene",
    "dependencies",
    "performance",
]


def normalize_focus(raw: str | list[str] | bool) -> list[str]:
    """Normalize a focus value to a list of focus area names.

    "off"/False → [], "all" → all names, "security" → ["security"],
    "does_it_work" → ["security", "testing"] (frame name expansion),
    "security,performance" → ["security", "performance"], list passthrough.
    """
    from noxaudit.frames import resolve_schedule_entry

    # YAML parses bare `off` as False, `on` as True
    if isinstance(raw, bool) or raw is None:
        return [] if not raw else list(ALL_FOCUS_NAMES)
    if isinstance(raw, list):
        return [str(item) for item in raw]
    raw = str(raw)
    if raw == "off":
        return []
    if raw == "all":
        return list(ALL_FOCUS_NAMES)
    # Support comma-separated string from CLI (may include frame names)
    if "," in raw:
        result: list[str] = []
        for s in raw.split(","):
            s = s.strip()
            if s:
                result.extend(resolve_schedule_entry(s))
        return result
    # Single entry — may be a frame name or a focus area name
    return resolve_schedule_entry(raw)


@dataclass
class NoxauditConfig:
    repos: list[RepoConfig] = field(default_factory=list)
    schedule: dict[str, str | list[str]] = field(default_factory=lambda: dict(DEFAULT_SCHEDULE))
    frames: dict[str, FrameConfig] = field(default_factory=dict)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    notifications: list[NotificationConfig] = field(default_factory=list)
    decisions: DecisionConfig = field(default_factory=DecisionConfig)
    issues: IssuesConfig = field(default_factory=IssuesConfig)
    prepass: PrepassConfig = field(default_factory=PrepassConfig)
    reports_dir: str = ".noxaudit/reports"
    model: str = "claude-sonnet-4-5-20250929"

    def get_today_focus(self) -> str | list[str]:
        import datetime

        from noxaudit.frames import FRAMES, get_enabled_focus_areas

        day = WEEKDAY_NAMES[datetime.date.today().weekday()]
        entry = self.schedule.get(day, "off")

        # If the schedule entry is a frame name, apply per-focus overrides
        if isinstance(entry, str) and entry in FRAMES:
            fc = self.frames.get(entry)
            overrides = fc.overrides if fc else None
            return get_enabled_focus_areas(entry, overrides)

        return entry

    def get_provider_for_repo(self, repo_name: str, run_index: int = 0) -> str:
        for repo in self.repos:
            if repo.name == repo_name:
                providers = repo.provider_rotation
                return providers[run_index % len(providers)]
        return "gemini"


def load_config(config_path: str | Path | None = None) -> NoxauditConfig:
    """Load config from noxaudit.yml, falling back to defaults."""
    if config_path is None:
        config_path = Path("noxaudit.yml")
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        return NoxauditConfig()

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    repos = []
    for r in raw.get("repos", []):
        repos.append(
            RepoConfig(
                name=r["name"],
                path=os.path.expanduser(r["path"]),
                provider_rotation=r.get("provider_rotation", ["gemini"]),
                exclude_patterns=r.get("exclude", []),
            )
        )

    schedule = dict(DEFAULT_SCHEDULE)
    schedule.update(raw.get("schedule", {}))

    frames: dict[str, FrameConfig] = {}
    for frame_name, overrides in raw.get("frames", {}).items():
        if isinstance(overrides, dict):
            frames[frame_name] = FrameConfig(overrides=overrides)

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
        path=decisions_raw.get("path", ".noxaudit/decisions.jsonl"),
    )

    issues_raw = raw.get("issues", {})
    issues = IssuesConfig(
        enabled=issues_raw.get("enabled", False),
        severity_threshold=issues_raw.get("severity_threshold", "medium"),
        labels=issues_raw.get("labels", ["noxaudit"]),
        assignees=issues_raw.get("assignees", []),
        repository_url=issues_raw.get("repository_url", "https://github.com/atriumn/noxaudit"),
    )

    prepass_raw = raw.get("prepass", {})
    prepass = PrepassConfig(
        enabled=prepass_raw.get("enabled", False),
        threshold_tokens=prepass_raw.get("threshold_tokens", 600_000),
        auto_disable=not prepass_raw.get("auto", True),
    )

    return NoxauditConfig(
        repos=repos,
        schedule=schedule,
        frames=frames,
        budget=budget,
        notifications=notifications,
        decisions=decisions,
        issues=issues,
        prepass=prepass,
        reports_dir=raw.get("reports_dir", ".noxaudit/reports"),
        model=raw.get("model", "claude-sonnet-4-5-20250929"),
    )
