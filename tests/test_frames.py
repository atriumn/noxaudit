"""Tests for frames.py — frame definitions and resolution helpers."""

from __future__ import annotations

from noxaudit.frames import (
    FRAME_LABELS,
    FRAMES,
    get_enabled_focus_areas,
    get_frame_for_focus,
    resolve_schedule_entry,
)


class TestResolveScheduleEntry:
    def test_frame_name_returns_focus_areas(self):
        assert resolve_schedule_entry("does_it_work") == ["security", "testing"]

    def test_frame_name_does_it_last(self):
        assert resolve_schedule_entry("does_it_last") == [
            "patterns",
            "hygiene",
            "docs",
            "dependencies",
        ]

    def test_frame_name_can_we_prove_it(self):
        assert resolve_schedule_entry("can_we_prove_it") == ["performance"]

    def test_empty_frame_returns_empty_list(self):
        assert resolve_schedule_entry("does_it_feel_right") == []
        assert resolve_schedule_entry("can_everyone_use_it") == []

    def test_focus_name_returns_single_item_list(self):
        assert resolve_schedule_entry("security") == ["security"]
        assert resolve_schedule_entry("performance") == ["performance"]

    def test_off_returns_empty(self):
        assert resolve_schedule_entry("off") == []

    def test_all_returns_all_focus_names(self):
        from noxaudit.config import ALL_FOCUS_NAMES

        result = resolve_schedule_entry("all")
        assert result == list(ALL_FOCUS_NAMES)
        assert len(result) == 7

    def test_comma_separated_focus_names(self):
        assert resolve_schedule_entry("security,testing") == ["security", "testing"]

    def test_comma_separated_with_spaces(self):
        assert resolve_schedule_entry("security, testing") == ["security", "testing"]

    def test_comma_separated_frame_names(self):
        result = resolve_schedule_entry("does_it_work,can_we_prove_it")
        assert result == ["security", "testing", "performance"]

    def test_comma_separated_mixed(self):
        result = resolve_schedule_entry("does_it_work,performance")
        assert result == ["security", "testing", "performance"]

    def test_unknown_entry_passes_through(self):
        assert resolve_schedule_entry("unknown_focus") == ["unknown_focus"]


class TestGetFrameForFocus:
    def test_security_is_in_does_it_work(self):
        assert get_frame_for_focus("security") == "does_it_work"

    def test_testing_is_in_does_it_work(self):
        assert get_frame_for_focus("testing") == "does_it_work"

    def test_patterns_is_in_does_it_last(self):
        assert get_frame_for_focus("patterns") == "does_it_last"

    def test_hygiene_is_in_does_it_last(self):
        assert get_frame_for_focus("hygiene") == "does_it_last"

    def test_docs_is_in_does_it_last(self):
        assert get_frame_for_focus("docs") == "does_it_last"

    def test_dependencies_is_in_does_it_last(self):
        assert get_frame_for_focus("dependencies") == "does_it_last"

    def test_performance_is_in_can_we_prove_it(self):
        assert get_frame_for_focus("performance") == "can_we_prove_it"

    def test_unknown_focus_returns_none(self):
        assert get_frame_for_focus("unknown") is None
        assert get_frame_for_focus("does_it_work") is None  # frame name is not a focus

    def test_all_focus_names_have_a_frame(self):
        from noxaudit.config import ALL_FOCUS_NAMES

        for name in ALL_FOCUS_NAMES:
            assert get_frame_for_focus(name) is not None, f"{name} has no frame"


class TestGetEnabledFocusAreas:
    def test_no_overrides_returns_all_in_frame(self):
        result = get_enabled_focus_areas("does_it_work", None)
        assert result == ["security", "testing"]

    def test_empty_overrides_returns_all_in_frame(self):
        result = get_enabled_focus_areas("does_it_work", {})
        assert result == ["security", "testing"]

    def test_disable_one_focus(self):
        overrides = {"dependencies": False}
        result = get_enabled_focus_areas("does_it_last", overrides)
        assert "dependencies" not in result
        assert "patterns" in result
        assert "hygiene" in result
        assert "docs" in result

    def test_explicit_true_keeps_focus(self):
        overrides = {"patterns": True, "hygiene": True, "docs": True, "dependencies": True}
        result = get_enabled_focus_areas("does_it_last", overrides)
        assert result == ["patterns", "hygiene", "docs", "dependencies"]

    def test_disable_all_returns_empty(self):
        overrides = {"security": False, "testing": False}
        result = get_enabled_focus_areas("does_it_work", overrides)
        assert result == []

    def test_unknown_frame_returns_empty(self):
        result = get_enabled_focus_areas("unknown_frame", None)
        assert result == []


class TestFrameNamesInNormalizeFocus:
    """Frame names work in --focus flag via normalize_focus."""

    def test_frame_name_resolves_to_focuses(self):
        from noxaudit.config import normalize_focus

        assert normalize_focus("does_it_work") == ["security", "testing"]

    def test_frame_name_does_it_last(self):
        from noxaudit.config import normalize_focus

        assert normalize_focus("does_it_last") == [
            "patterns",
            "hygiene",
            "docs",
            "dependencies",
        ]

    def test_frame_name_in_comma_separated(self):
        from noxaudit.config import normalize_focus

        result = normalize_focus("does_it_work,performance")
        assert result == ["security", "testing", "performance"]


class TestBackwardCompat:
    """Old flat schedule still works unchanged."""

    def test_flat_schedule_single_focus(self, tmp_config):
        from noxaudit.config import load_config, normalize_focus

        path = tmp_config("""\
            schedule:
              monday: security
              tuesday: patterns
              sunday: off
        """)
        config = load_config(path)
        assert normalize_focus(config.schedule["monday"]) == ["security"]
        assert normalize_focus(config.schedule["tuesday"]) == ["patterns"]
        assert normalize_focus(config.schedule["sunday"]) == []

    def test_flat_schedule_list_format(self, tmp_config):
        from noxaudit.config import load_config, normalize_focus

        path = tmp_config("""\
            schedule:
              monday: [security, dependencies]
        """)
        config = load_config(path)
        assert normalize_focus(config.schedule["monday"]) == ["security", "dependencies"]

    def test_frame_schedule_resolves(self, tmp_config):
        from noxaudit.config import load_config, normalize_focus

        path = tmp_config("""\
            schedule:
              monday: does_it_work
              tuesday: does_it_last
        """)
        config = load_config(path)
        assert normalize_focus(config.schedule["monday"]) == ["security", "testing"]
        assert normalize_focus(config.schedule["tuesday"]) == [
            "patterns",
            "hygiene",
            "docs",
            "dependencies",
        ]


class TestScheduleDisplay:
    """Schedule display shows frame labels."""

    def test_frame_labels_exist_for_all_frames(self):
        for frame_name in FRAMES:
            assert frame_name in FRAME_LABELS, f"{frame_name} missing from FRAME_LABELS"

    def test_frame_labels_are_human_readable(self):
        assert FRAME_LABELS["does_it_work"] == "Does it work?"
        assert FRAME_LABELS["does_it_last"] == "Does it last?"
        assert FRAME_LABELS["can_we_prove_it"] == "Can we prove it?"
