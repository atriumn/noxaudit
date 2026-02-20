"""Frame definitions — the five organizing lenses for code quality."""

from __future__ import annotations

FRAMES: dict[str, list[str]] = {
    "does_it_work": ["security", "testing"],
    "does_it_feel_right": [],  # Phase 2: ux-copy, help-content
    "can_everyone_use_it": [],  # Phase 2: a11y
    "does_it_last": ["patterns", "hygiene", "docs", "dependencies"],
    "can_we_prove_it": ["performance"],
}

FRAME_LABELS: dict[str, str] = {
    "does_it_work": "Does it work?",
    "does_it_feel_right": "Does it feel right?",
    "can_everyone_use_it": "Can everyone use it?",
    "does_it_last": "Does it last?",
    "can_we_prove_it": "Can we prove it?",
}


def resolve_schedule_entry(entry: str) -> list[str]:
    """Resolve a schedule entry to focus area names.

    Handles both frame names ('does_it_work') and focus names ('security').
    Handles comma-separated ('security,testing') and 'all'.
    """
    if entry == "off":
        return []
    if entry == "all":
        from noxaudit.config import ALL_FOCUS_NAMES  # lazy to avoid circular import

        return list(ALL_FOCUS_NAMES)
    if entry in FRAMES:
        return list(FRAMES[entry])
    if "," in entry:
        result: list[str] = []
        for part in entry.split(","):
            part = part.strip()
            if part:
                result.extend(resolve_schedule_entry(part))
        return result
    return [entry]


def get_frame_for_focus(focus_name: str) -> str | None:
    """Return the frame name for a focus area, or None."""
    for frame_name, focuses in FRAMES.items():
        if focus_name in focuses:
            return frame_name
    return None


def get_enabled_focus_areas(frame_name: str, frame_config: dict | None) -> list[str]:
    """Get enabled focus areas for a frame, applying per-focus overrides."""
    base = list(FRAMES.get(frame_name, []))
    if frame_config is None:
        return base
    return [f for f in base if frame_config.get(f, True)]
