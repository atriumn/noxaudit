"""Tests for SARIF output format."""

from __future__ import annotations

import json
from pathlib import Path

from noxaudit.models import Finding, Severity
from noxaudit.sarif import findings_to_sarif, save_sarif


class TestFindingsToSarif:
    def test_empty_findings(self):
        """Empty findings → valid SARIF with no results."""
        sarif = findings_to_sarif([], "security", "my-app")
        assert sarif["version"] == "2.1.0"
        assert len(sarif["runs"]) == 1
        assert sarif["runs"][0]["results"] == []

    def test_single_finding(self):
        """Single finding → correct rule, level, location, fingerprint."""
        findings = [
            Finding(
                id="aaa111",
                severity=Severity.HIGH,
                file="src/auth.py",
                line=42,
                title="SQL injection",
                description="User input interpolated into query",
                focus="security",
            )
        ]
        sarif = findings_to_sarif(findings, "security", "my-app")

        # Check structure
        assert len(sarif["runs"][0]["results"]) == 1
        result = sarif["runs"][0]["results"][0]

        # Check rule
        assert result["ruleId"] == "noxaudit/security"
        assert result["level"] == "error"

        # Check message includes title and description
        assert "SQL injection" in result["message"]["text"]
        assert "User input interpolated into query" in result["message"]["text"]

        # Check location
        assert (
            result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "src/auth.py"
        )
        assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 42

        # Check fingerprint
        assert result["fingerprints"]["noxauditFindingId"] == "aaa111"

    def test_severity_mapping(self, sample_findings):
        """HIGH/MEDIUM/LOW → error/warning/note."""
        sarif = findings_to_sarif(sample_findings, "security", "my-app")
        results = sarif["runs"][0]["results"]

        high_result = next(r for r in results if r["fingerprints"]["noxauditFindingId"] == "aaa111")
        medium_result = next(
            r for r in results if r["fingerprints"]["noxauditFindingId"] == "bbb222"
        )
        low_result = next(r for r in results if r["fingerprints"]["noxauditFindingId"] == "ccc333")

        assert high_result["level"] == "error"
        assert medium_result["level"] == "warning"
        assert low_result["level"] == "note"

    def test_finding_without_line_number(self):
        """Finding without line number → location without region."""
        findings = [
            Finding(
                id="xxx123",
                severity=Severity.MEDIUM,
                file="README.md",
                line=None,
                title="Stale docs",
                description="README is outdated",
                focus="docs",
            )
        ]
        sarif = findings_to_sarif(findings, "docs", "my-app")
        result = sarif["runs"][0]["results"][0]

        # Should not have region
        assert "region" not in result["locations"][0]["physicalLocation"]
        assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "README.md"

    def test_finding_with_suggestion(self):
        """Finding with suggestion → SARIF fix object."""
        findings = [
            Finding(
                id="fix123",
                severity=Severity.MEDIUM,
                file="src/app.py",
                line=10,
                title="Use constants",
                description="Magic number should be a constant",
                suggestion="Replace with TIMEOUT_SECONDS = 30",
                focus="style",
            )
        ]
        sarif = findings_to_sarif(findings, "style", "my-app")
        result = sarif["runs"][0]["results"][0]

        # Should have fixes
        assert "fixes" in result
        assert len(result["fixes"]) == 1
        assert result["fixes"][0]["description"]["text"] == "Replace with TIMEOUT_SECONDS = 30"

    def test_multiple_focus_areas(self):
        """Multiple focus areas → multiple rules."""
        findings = [
            Finding(
                id="f1",
                severity=Severity.HIGH,
                file="a.py",
                line=1,
                title="Security issue",
                description="Has a security problem",
                focus="security",
            ),
            Finding(
                id="f2",
                severity=Severity.MEDIUM,
                file="b.py",
                line=2,
                title="Performance issue",
                description="Slow performance detected",
                focus="performance",
            ),
        ]
        sarif = findings_to_sarif(findings, "security+performance", "my-app")

        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        rule_ids = {r["id"] for r in rules}

        assert "noxaudit/security" in rule_ids
        assert "noxaudit/performance" in rule_ids

    def test_valid_json_structure(self, sample_findings):
        """Output is valid JSON matching SARIF 2.1.0 schema structure."""
        sarif = findings_to_sarif(sample_findings, "security", "my-app")

        # Should be serializable to JSON
        json_str = json.dumps(sarif)
        assert isinstance(json_str, str)

        # Should have all required SARIF fields
        assert "version" in sarif
        assert "runs" in sarif
        assert len(sarif["runs"]) > 0

        run = sarif["runs"][0]
        assert "tool" in run
        assert "results" in run
        assert "tool" in run
        assert "driver" in run["tool"]
        assert "name" in run["tool"]["driver"]
        assert "rules" in run["tool"]["driver"]

    def test_tool_information(self):
        """Tool section has correct information."""
        sarif = findings_to_sarif([], "security", "my-app")
        driver = sarif["runs"][0]["tool"]["driver"]

        assert driver["name"] == "noxaudit"
        assert "0." in driver["version"]  # Should have a version like 0.2.0
        assert driver["informationUri"] == "https://github.com/atriumn/noxaudit"

    def test_properties_metadata(self):
        """SARIF includes repo and focus in properties."""
        sarif = findings_to_sarif([], "security+docs", "my-app")
        props = sarif["runs"][0].get("properties", {})

        assert props.get("repo") == "my-app"
        assert props.get("focus") == "security+docs"

    def test_uribaseId_srcroot(self, sample_findings):
        """All file URIs use %SRCROOT% as base."""
        sarif = findings_to_sarif(sample_findings, "security", "my-app")
        results = sarif["runs"][0]["results"]

        for result in results:
            for location in result["locations"]:
                artifact = location["physicalLocation"]["artifactLocation"]
                assert artifact["uriBaseId"] == "%SRCROOT%"


class TestSaveSarif:
    def test_creates_file(self, tmp_path, sample_findings):
        """Save creates a file with correct naming."""
        sarif = findings_to_sarif(sample_findings, "security", "my-app")
        path = save_sarif(sarif, tmp_path / "reports", "my-app", "security")

        assert Path(path).exists()
        assert "my-app" in path
        assert "security" in path
        assert path.endswith(".sarif")

    def test_file_contains_valid_json(self, tmp_path, sample_findings):
        """Saved file contains valid JSON."""
        sarif = findings_to_sarif(sample_findings, "security", "my-app")
        path = save_sarif(sarif, tmp_path / "reports", "my-app", "security")

        content = Path(path).read_text()
        parsed = json.loads(content)

        assert parsed["version"] == "2.1.0"
        assert len(parsed["runs"][0]["results"]) == len(sample_findings)

    def test_combined_focus_in_filename(self, tmp_path, sample_findings):
        """Combined focus areas in filename."""
        sarif = findings_to_sarif(sample_findings, "security+docs", "my-app")
        path = save_sarif(sarif, tmp_path / "reports", "my-app", "security+docs")

        assert "security+docs" in path

    def test_creates_repo_directory(self, tmp_path):
        """Creates repo subdirectory if it doesn't exist."""
        findings = []
        sarif = findings_to_sarif(findings, "security", "my-app")
        path = save_sarif(sarif, tmp_path / "reports", "my-app", "security")

        assert Path(path).parent.parent == tmp_path / "reports"
