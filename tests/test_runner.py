"""Tests for the runner module (no API calls)."""

from __future__ import annotations

import pytest

from noxaudit.config import NoxauditConfig, normalize_focus
from noxaudit.runner import _focus_label, _resolve_focus_names


class TestFocusLabel:
    def test_single(self):
        assert _focus_label(["security"]) == "security"

    def test_multiple(self):
        assert _focus_label(["security", "performance"]) == "security+performance"

    def test_all(self):
        label = _focus_label(normalize_focus("all"))
        assert "+" in label
        assert "security" in label


class TestResolveFocusNames:
    def test_override_single(self):
        config = NoxauditConfig()
        names = _resolve_focus_names("security", config)
        assert names == ["security"]

    def test_override_comma_separated(self):
        config = NoxauditConfig()
        names = _resolve_focus_names("security,docs", config)
        assert names == ["security", "docs"]

    def test_override_all(self):
        config = NoxauditConfig()
        names = _resolve_focus_names("all", config)
        assert len(names) == 7

    def test_off_returns_empty(self):
        config = NoxauditConfig(schedule={"monday": "off"})
        # When override is None, uses today's schedule.
        # We test the "off" path by passing it as override.
        names = _resolve_focus_names("off", config)
        assert names == []

    def test_unknown_focus_raises(self):
        config = NoxauditConfig()
        with pytest.raises(ValueError, match="Unknown focus area"):
            _resolve_focus_names("nonexistent", config)

    def test_unknown_in_list_raises(self):
        config = NoxauditConfig()
        with pytest.raises(ValueError, match="Unknown focus area"):
            _resolve_focus_names("security,bogus", config)
