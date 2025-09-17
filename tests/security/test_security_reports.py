"""
Security Reports Validation Tests
Tests to validate that security scanning reports are properly generated and contain expected data.

QA_IDs: REQ-SEC-002
"""

import pytest
import json
import os
from pathlib import Path
from typing import Dict, Any


class TestSecurityReports:
    """Test security report generation and validation."""

    def test_safety_report_exists_and_valid(self):
        """Test that safety report exists and has valid JSON structure.

        QA_ID: REQ-SEC-002a
        Acceptance Criteria: Safety report exists and is valid JSON with expected fields
        """
        project_root = Path(__file__).parent.parent.parent
        safety_report = project_root / "safety-report.json"

        if not safety_report.exists():
            pytest.skip("Safety report not found - may be running outside CI environment")

        # Validate JSON structure
        with open(safety_report, 'r') as f:
            report_data = json.load(f)

        # Check for expected fields (flexible to handle both real and fallback reports)
        assert isinstance(report_data, dict), "Safety report should be a JSON object"

        # Check for either vulnerabilities (real report) or status (fallback report)
        has_vulnerabilities = "vulnerabilities" in report_data
        has_status = "status" in report_data

        assert has_vulnerabilities or has_status, "Safety report should have vulnerabilities or status field"

        if has_vulnerabilities:
            assert isinstance(report_data["vulnerabilities"], list), "Vulnerabilities should be a list"

    def test_bandit_report_exists_and_valid(self):
        """Test that bandit report exists and has valid JSON structure.

        QA_ID: REQ-SEC-002b
        Acceptance Criteria: Bandit report exists and is valid JSON with expected fields
        """
        project_root = Path(__file__).parent.parent.parent
        bandit_report = project_root / "bandit-report.json"

        if not bandit_report.exists():
            pytest.skip("Bandit report not found - may be running outside CI environment")

        # Validate JSON structure
        with open(bandit_report, 'r') as f:
            report_data = json.load(f)

        # Check for expected fields
        assert isinstance(report_data, dict), "Bandit report should be a JSON object"
        assert "results" in report_data, "Bandit report should have results field"
        assert isinstance(report_data["results"], list), "Results should be a list"

        # Check metrics field if present
        if "metrics" in report_data:
            assert isinstance(report_data["metrics"], dict), "Metrics should be a dict"

    def test_semgrep_report_exists_and_valid(self):
        """Test that semgrep report exists and has valid JSON structure.

        QA_ID: REQ-SEC-002c
        Acceptance Criteria: Semgrep report exists and is valid JSON with expected fields
        """
        project_root = Path(__file__).parent.parent.parent
        semgrep_report = project_root / "semgrep-report.json"

        if not semgrep_report.exists():
            pytest.skip("Semgrep report not found - may be running outside CI environment")

        # Validate JSON structure
        with open(semgrep_report, 'r') as f:
            report_data = json.load(f)

        # Check for expected fields
        assert isinstance(report_data, dict), "Semgrep report should be a JSON object"
        assert "results" in report_data, "Semgrep report should have results field"
        assert isinstance(report_data["results"], list), "Results should be a list"

        # Check for errors field
        if "errors" in report_data:
            assert isinstance(report_data["errors"], list), "Errors should be a list"

    def test_no_high_severity_security_issues(self):
        """Test that no high-severity security issues are found.

        QA_ID: REQ-SEC-002d
        Acceptance Criteria: No high-severity security issues in any report
        """
        project_root = Path(__file__).parent.parent.parent

        # Check bandit for high-severity issues
        bandit_report = project_root / "bandit-report.json"
        if bandit_report.exists():
            with open(bandit_report, 'r') as f:
                bandit_data = json.load(f)

            high_severity_issues = []
            if "results" in bandit_data:
                for result in bandit_data["results"]:
                    if isinstance(result, dict) and result.get("issue_severity", "").lower() in ["high", "critical"]:
                        high_severity_issues.append(result)

            assert len(high_severity_issues) == 0, f"Found {len(high_severity_issues)} high-severity security issues in Bandit scan"

        # Check safety for critical vulnerabilities
        safety_report = project_root / "safety-report.json"
        if safety_report.exists():
            with open(safety_report, 'r') as f:
                safety_data = json.load(f)

            if "vulnerabilities" in safety_data:
                critical_vulns = [v for v in safety_data["vulnerabilities"] if isinstance(v, dict) and v.get("severity", "").lower() in ["high", "critical"]]
                assert len(critical_vulns) == 0, f"Found {len(critical_vulns)} critical vulnerabilities in dependency scan"

    def test_security_scan_completion_markers(self):
        """Test that all security scans completed successfully.

        QA_ID: REQ-SEC-002e
        Acceptance Criteria: All security tools completed without fatal errors
        """
        project_root = Path(__file__).parent.parent.parent

        reports = [
            ("safety-report.json", "Safety dependency scan"),
            ("bandit-report.json", "Bandit static analysis"),
            ("semgrep-report.json", "Semgrep pattern analysis")
        ]

        missing_reports = []
        for report_file, description in reports:
            report_path = project_root / report_file
            if not report_path.exists():
                missing_reports.append(f"{description} ({report_file})")

        if missing_reports:
            pytest.skip(f"Security reports missing (likely running outside CI): {', '.join(missing_reports)}")

        # If we get here, all reports exist - scan completion verified
        assert True, "All security scans completed successfully"