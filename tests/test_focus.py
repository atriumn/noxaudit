"""Tests for focus area gathering and prompt building."""

from __future__ import annotations

import pytest

from noxaudit.focus import FOCUS_AREAS
from noxaudit.focus.base import (
    BaseFocus,
    build_combined_prompt,
    gather_files_combined,
    is_secret_file,
)


class StubFocusA(BaseFocus):
    name = "alpha"
    description = "Test focus A"

    def get_file_patterns(self):
        return ["**/*.py", "**/*.yml"]

    def get_prompt(self):
        return "Check for alpha issues."


class StubFocusB(BaseFocus):
    name = "beta"
    description = "Test focus B"

    def get_file_patterns(self):
        return ["**/*.py", "**/*.md"]  # *.py overlaps with A

    def get_prompt(self):
        return "Check for beta issues."


class TestGatherFilesCombined:
    def test_single_focus(self, tmp_repo):
        focus = StubFocusA()
        files = gather_files_combined([focus], tmp_repo)
        paths = {f.path for f in files}
        assert "src/app.py" in paths
        assert "config.yml" in paths

    def test_deduplicates_across_focus_areas(self, tmp_repo):
        a = StubFocusA()
        b = StubFocusB()
        combined = gather_files_combined([a, b], tmp_repo)
        separate_a = gather_files_combined([a], tmp_repo)
        separate_b = gather_files_combined([b], tmp_repo)

        combined_paths = [f.path for f in combined]
        # No duplicates
        assert len(combined_paths) == len(set(combined_paths))
        # Combined is <= sum of separate (due to dedup)
        assert len(combined) <= len(separate_a) + len(separate_b)
        # Combined has union of all paths
        all_paths = {f.path for f in separate_a} | {f.path for f in separate_b}
        assert set(combined_paths) == all_paths

    def test_excludes_node_modules(self, tmp_repo):
        focus = StubFocusA()
        files = gather_files_combined([focus], tmp_repo)
        paths = {f.path for f in files}
        assert not any("node_modules" in p for p in paths)

    def test_excludes_git(self, tmp_repo):
        focus = StubFocusA()
        files = gather_files_combined([focus], tmp_repo)
        paths = {f.path for f in files}
        assert not any(".git" in p for p in paths)

    def test_excludes_custom_patterns(self, tmp_repo):
        (tmp_repo / "vendor").mkdir()
        (tmp_repo / "vendor" / "lib.py").write_text("x = 1")
        focus = StubFocusA()
        files = gather_files_combined([focus], tmp_repo, exclude_patterns=["vendor"])
        paths = {f.path for f in files}
        assert not any("vendor" in p for p in paths)

    def test_skips_large_files(self, tmp_repo):
        big = tmp_repo / "big.py"
        big.write_text("x" * 60_000)  # Over MAX_FILE_SIZE
        focus = StubFocusA()
        files = gather_files_combined([focus], tmp_repo)
        paths = {f.path for f in files}
        assert "big.py" not in paths

    def test_empty_repo(self, tmp_path):
        focus = StubFocusA()
        files = gather_files_combined([focus], tmp_path)
        assert files == []

    def test_with_real_focus_areas(self, tmp_repo):
        """Test with actual SecurityFocus + DocsFocus to ensure no errors."""
        sec = FOCUS_AREAS["security"]()
        docs = FOCUS_AREAS["docs"]()
        combined = gather_files_combined([sec, docs], tmp_repo)
        assert len(combined) > 0
        paths = [f.path for f in combined]
        assert len(paths) == len(set(paths))


SECRET_FILES = [
    ".env",
    ".env.local",
    ".env.production",
    "app/prod.env",
    ".envrc",
    ".envs/prod.json",
    "credentials.json",
    "service-account-prod.json",
    ".aws/credentials",
    ".ssh/config",
    "certs/server.key",
    "certs/server.pem",
    "id_rsa",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "config/secrets.yml",
    "infra/prod.tfvars",
    "infra/terraform.tfstate",
]


class TestSecretFiles:
    @pytest.mark.parametrize("path", SECRET_FILES)
    def test_is_secret_file(self, path):
        assert is_secret_file(path)

    @pytest.mark.parametrize(
        "path",
        [".env.example", ".env.sample", "app/.env.template", "src/environment.py", "config.yml"],
    )
    def test_not_secret_file(self, path):
        assert not is_secret_file(path)

    def test_never_gathered_by_any_focus(self, tmp_repo):
        for rel in SECRET_FILES + [".env.example"]:
            path = tmp_repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("TOKEN=hunter2\n")

        all_focus = [cls() for cls in FOCUS_AREAS.values()]
        combined = {f.path for f in gather_files_combined(all_focus, tmp_repo)}
        single = {f.path for focus in all_focus for f in focus.gather_files(tmp_repo)}

        for paths in (combined, single):
            assert not paths & set(SECRET_FILES)
            assert "src/app.py" in paths
        assert ".env.example" in combined


class TestBuildCombinedPrompt:
    def test_single_focus_returns_original(self):
        focus = StubFocusA()
        prompt = build_combined_prompt([focus])
        assert prompt == "Check for alpha issues."

    def test_multiple_adds_section_headers(self):
        a, b = StubFocusA(), StubFocusB()
        prompt = build_combined_prompt([a, b])
        assert "## Focus Area: alpha" in prompt
        assert "## Focus Area: beta" in prompt
        assert "Check for alpha issues." in prompt
        assert "Check for beta issues." in prompt

    def test_multiple_includes_tagging_instruction(self):
        a, b = StubFocusA(), StubFocusB()
        prompt = build_combined_prompt([a, b])
        assert "focus" in prompt.lower()
        assert "alpha" in prompt
        assert "beta" in prompt

    def test_real_focus_areas(self):
        """Combined prompt with real focus areas doesn't crash."""
        instances = [FOCUS_AREAS[name]() for name in ["security", "performance", "docs"]]
        prompt = build_combined_prompt(instances)
        assert "## Focus Area: security" in prompt
        assert "## Focus Area: performance" in prompt
        assert "## Focus Area: docs" in prompt
