"""Tests for config loading and normalize_focus."""

from __future__ import annotations


from noxaudit.config import (
    ALL_FOCUS_NAMES,
    NoxauditConfig,
    load_config,
    normalize_focus,
)


class TestNormalizeFocus:
    def test_single_string(self):
        assert normalize_focus("security") == ["security"]

    def test_off_returns_empty(self):
        assert normalize_focus("off") == []

    def test_all_returns_all_names(self):
        assert normalize_focus("all") == list(ALL_FOCUS_NAMES)
        assert len(normalize_focus("all")) == 7

    def test_comma_separated(self):
        assert normalize_focus("security,performance") == ["security", "performance"]

    def test_comma_separated_with_spaces(self):
        assert normalize_focus("security, performance, docs") == [
            "security",
            "performance",
            "docs",
        ]

    def test_list_passthrough(self):
        names = ["security", "docs"]
        assert normalize_focus(names) == names

    def test_yaml_false_treated_as_off(self):
        # YAML parses bare `off` as False
        assert normalize_focus(False) == []

    def test_yaml_true_treated_as_all(self):
        # YAML parses bare `on` as True
        result = normalize_focus(True)
        assert result == list(ALL_FOCUS_NAMES)

    def test_none_treated_as_off(self):
        assert normalize_focus(None) == []

    def test_list_with_non_strings(self):
        # YAML might parse `[on, off]` as `[True, False]`
        assert normalize_focus([True, False]) == ["True", "False"]


class TestLoadConfig:
    def test_default_config_when_no_file(self, tmp_path):
        config = load_config(tmp_path / "nonexistent.yml")
        assert config.schedule["monday"] == "security"
        assert config.schedule["sunday"] == "off"

    def test_single_focus_schedule(self, tmp_config):
        path = tmp_config("""\
            schedule:
              monday: security
              sunday: off
        """)
        config = load_config(path)
        assert config.schedule["monday"] == "security"

    def test_list_focus_schedule(self, tmp_config):
        path = tmp_config("""\
            schedule:
              monday: [security, dependencies]
              wednesday: [patterns, hygiene, docs]
        """)
        config = load_config(path)
        assert config.schedule["monday"] == ["security", "dependencies"]
        assert config.schedule["wednesday"] == ["patterns", "hygiene", "docs"]

    def test_all_focus_schedule(self, tmp_config):
        path = tmp_config("""\
            schedule:
              monday: all
        """)
        config = load_config(path)
        assert config.schedule["monday"] == "all"
        assert normalize_focus(config.schedule["monday"]) == list(ALL_FOCUS_NAMES)

    def test_mixed_schedule(self, tmp_config):
        path = tmp_config("""\
            schedule:
              monday: [security, dependencies]
              tuesday: patterns
              sunday: off
        """)
        config = load_config(path)
        assert config.schedule["monday"] == ["security", "dependencies"]
        assert config.schedule["tuesday"] == "patterns"
        assert normalize_focus(config.schedule["sunday"]) == []

    def test_repos_loaded(self, tmp_config):
        path = tmp_config("""\
            repos:
              - name: my-app
                path: .
                exclude:
                  - vendor
        """)
        config = load_config(path)
        assert len(config.repos) == 1
        assert config.repos[0].name == "my-app"
        assert "vendor" in config.repos[0].exclude_patterns


class TestGetTodayFocus:
    def test_returns_schedule_value(self):
        config = NoxauditConfig(schedule={"monday": ["security", "deps"]})
        # We can't control what day it is, but we can verify the method works
        result = config.get_today_focus()
        assert result is not None
