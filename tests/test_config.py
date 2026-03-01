"""Tests for config loading and normalize_focus."""

from __future__ import annotations

import warnings

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
        assert isinstance(config, NoxauditConfig)

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


class TestDeprecationWarnings:
    def test_schedule_key_emits_warning(self, tmp_config):
        path = tmp_config("""\
            schedule:
              monday: security
        """)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_config(path)
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 1
        assert "schedule" in str(deprecation_warnings[0].message)

    def test_frames_key_emits_warning(self, tmp_config):
        path = tmp_config("""\
            frames:
              does_it_last:
                dependencies: false
        """)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_config(path)
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 1
        assert "frames" in str(deprecation_warnings[0].message)

    def test_both_keys_emit_two_warnings(self, tmp_config):
        path = tmp_config("""\
            schedule:
              monday: security
            frames:
              does_it_last:
                dependencies: false
        """)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_config(path)
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 2

    def test_no_warning_without_schedule_or_frames(self, tmp_config):
        path = tmp_config("""\
            repos:
              - name: my-app
                path: .
        """)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_config(path)
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 0
