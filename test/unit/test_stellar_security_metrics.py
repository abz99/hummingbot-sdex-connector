"""
Unit tests for Stellar Security Metrics and Requirements Tracking.
"""

import json
import tempfile
import time
from pathlib import Path
import pytest

from hummingbot.connector.exchange.stellar.stellar_security_metrics import (
    SecurityRequirement,
    SecurityMetrics,
    SecurityRequirementsTracker,
    RequirementStatus,
    RequirementPriority,
    RequirementCategory,
    get_security_tracker,
    update_security_requirement,
    get_security_posture_score,
    generate_security_status_report,
    export_security_dashboard_section,
)


class TestSecurityRequirement:
    """Test SecurityRequirement class."""

    def test_requirement_creation(self):
        """Test basic requirement creation."""
        req = SecurityRequirement(
            id="TEST-001",
            title="Test Requirement",
            description="Test description",
            category=RequirementCategory.AUTHENTICATION,
            priority=RequirementPriority.P0_CRITICAL,
        )

        assert req.id == "TEST-001"
        assert req.title == "Test Requirement"
        assert req.status == RequirementStatus.NOT_STARTED
        assert req.completion_percentage == 0
        assert req.created_date > 0
        assert req.last_updated > 0

    def test_requirement_status_update(self):
        """Test requirement status updates."""
        req = SecurityRequirement(
            id="TEST-002",
            title="Test Requirement 2",
            description="Test description",
            category=RequirementCategory.KEY_MANAGEMENT,
            priority=RequirementPriority.P1_HIGH,
        )

        # Update to in progress
        req.update_status(RequirementStatus.IN_PROGRESS, "Starting work", "test_user")
        assert req.status == RequirementStatus.IN_PROGRESS
        assert req.update_count == 1

        # Update to completed
        req.update_status(RequirementStatus.COMPLETED, "Work finished", "test_user")
        assert req.status == RequirementStatus.COMPLETED
        assert req.completion_percentage == 100
        assert req.completed_date > 0
        assert req.update_count == 2

    def test_completion_score_calculation(self):
        """Test completion score calculation."""
        req = SecurityRequirement(
            id="TEST-003",
            title="Test Requirement 3",
            description="Test description",
            category=RequirementCategory.ENCRYPTION,
            priority=RequirementPriority.P2_MEDIUM,
        )

        # Not started
        assert req.calculate_completion_score() == 0.0

        # In progress
        req.status = RequirementStatus.IN_PROGRESS
        req.completion_percentage = 50
        assert req.calculate_completion_score() == 0.5

        # Completed
        req.status = RequirementStatus.COMPLETED
        assert req.calculate_completion_score() == 1.0

    def test_overdue_calculation(self):
        """Test overdue requirement detection."""
        req = SecurityRequirement(
            id="TEST-004",
            title="Test Requirement 4",
            description="Test description",
            category=RequirementCategory.MONITORING,
            priority=RequirementPriority.P0_CRITICAL,
            due_date=time.time() - 86400,  # Yesterday
        )

        assert req.is_overdue() is True
        assert req.days_until_due() < 0

        # Not overdue if completed
        req.status = RequirementStatus.COMPLETED
        assert req.is_overdue() is False


class TestSecurityRequirementsTracker:
    """Test SecurityRequirementsTracker class."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = SecurityRequirementsTracker(data_dir=self.temp_dir)

    def test_tracker_initialization(self):
        """Test tracker initialization with default requirements."""
        assert len(self.tracker.requirements) > 0
        assert self.tracker.data_dir.exists()
        assert self.tracker.requirements_file.exists()

    def test_requirement_status_update(self):
        """Test updating requirement status."""
        # Get a requirement ID from defaults
        req_id = list(self.tracker.requirements.keys())[0]

        # Update status
        self.tracker.update_requirement_status(
            req_id,
            RequirementStatus.IN_PROGRESS,
            completion_percentage=75,
            notes="Test update",
            user="test_user",
        )

        # Verify update
        req = self.tracker.requirements[req_id]
        assert req.status == RequirementStatus.IN_PROGRESS
        assert req.completion_percentage == 75
        assert req.update_count > 0

    def test_metrics_calculation(self):
        """Test security metrics calculation."""
        metrics = self.tracker.calculate_security_metrics()

        assert isinstance(metrics, SecurityMetrics)
        assert metrics.security_posture_score >= 0.0
        assert metrics.security_posture_score <= 100.0
        assert metrics.critical_completion_rate >= 0.0
        assert metrics.critical_completion_rate <= 100.0
        assert metrics.calculation_timestamp > 0

    def test_overdue_requirements(self):
        """Test overdue requirements detection."""
        # Add an overdue requirement
        overdue_req = SecurityRequirement(
            id="TEST-OVERDUE",
            title="Overdue Test Requirement",
            description="Test overdue detection",
            category=RequirementCategory.COMPLIANCE,
            priority=RequirementPriority.P1_HIGH,
            due_date=time.time() - 86400,  # Yesterday
        )
        self.tracker.requirements[overdue_req.id] = overdue_req

        overdue_reqs = self.tracker.get_overdue_requirements()
        assert len(overdue_reqs) > 0
        assert any(req.id == "TEST-OVERDUE" for req in overdue_reqs)

    def test_requirements_filtering(self):
        """Test requirement filtering by status and priority."""
        # Filter by status
        completed_reqs = self.tracker.get_requirements_by_status(RequirementStatus.COMPLETED)
        assert all(req.status == RequirementStatus.COMPLETED for req in completed_reqs)

        # Filter by priority
        critical_reqs = self.tracker.get_requirements_by_priority(RequirementPriority.P0_CRITICAL)
        assert all(req.priority == RequirementPriority.P0_CRITICAL for req in critical_reqs)

    def test_status_report_generation(self):
        """Test comprehensive status report generation."""
        report = self.tracker.generate_status_report()

        assert "timestamp" in report
        assert "overall_security_score" in report
        assert "requirement_summary" in report
        assert "completion_rates" in report
        assert "operational_metrics" in report
        assert "active_requirements" in report

        # Verify structure
        summary = report["requirement_summary"]
        assert "total" in summary
        assert "completed" in summary
        assert "in_progress" in summary
        assert "not_started" in summary

        rates = report["completion_rates"]
        assert "critical" in rates
        assert "high" in rates
        assert "medium" in rates
        assert "regulatory" in rates

    def test_project_status_export(self):
        """Test PROJECT_STATUS.md section export."""
        section = self.tracker.export_project_status_section()

        assert "🔒 SECURITY REQUIREMENTS TRACKING" in section
        assert "Security Posture Dashboard" in section
        assert "Active Security Requirements" in section
        assert "Security Metrics (Current Period)" in section

        # Check for markdown table structure
        assert "| ID | Priority | Title | Status | Owner | Target Date |" in section
        assert "|----|----------|-------|--------|-------|-------------|" in section

    def test_persistence(self):
        """Test requirement and metrics persistence."""
        # Modify a requirement
        req_id = list(self.tracker.requirements.keys())[0]
        self.tracker.update_requirement_status(
            req_id, RequirementStatus.COMPLETED, completion_percentage=100, user="test_persistence"
        )

        # Create new tracker instance (should load from disk)
        new_tracker = SecurityRequirementsTracker(data_dir=self.temp_dir)

        # Verify data was loaded
        assert len(new_tracker.requirements) == len(self.tracker.requirements)
        assert new_tracker.requirements[req_id].status == RequirementStatus.COMPLETED
        assert new_tracker.requirements[req_id].completion_percentage == 100

    def test_audit_trail(self):
        """Test audit trail functionality."""
        req_id = list(self.tracker.requirements.keys())[0]

        # Make several updates
        self.tracker.update_requirement_status(
            req_id, RequirementStatus.IN_PROGRESS, 25, "Started work", "user1"
        )
        self.tracker.update_requirement_status(
            req_id, RequirementStatus.IN_PROGRESS, 75, "Making progress", "user1"
        )
        self.tracker.update_requirement_status(
            req_id, RequirementStatus.COMPLETED, 100, "Work complete", "user2"
        )

        # Check audit file exists and has entries
        assert self.tracker.audit_file.exists()

        with open(self.tracker.audit_file, "r") as f:
            audit_log = json.load(f)

        assert len(audit_log) >= 3
        assert all("timestamp" in entry for entry in audit_log)
        assert all("requirement_id" in entry for entry in audit_log)
        assert all("user" in entry for entry in audit_log)


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_get_security_tracker(self):
        """Test global tracker access."""
        tracker = get_security_tracker()
        assert isinstance(tracker, SecurityRequirementsTracker)

        # Should return same instance
        tracker2 = get_security_tracker()
        assert tracker is tracker2

    def test_update_security_requirement(self):
        """Test convenience function for updating requirements."""
        tracker = get_security_tracker()
        req_id = list(tracker.requirements.keys())[0]

        update_security_requirement(
            req_id,
            RequirementStatus.IN_PROGRESS,
            completion_percentage=60,
            notes="Test convenience function",
        )

        req = tracker.requirements[req_id]
        assert req.status == RequirementStatus.IN_PROGRESS
        assert req.completion_percentage == 60

    def test_get_security_posture_score(self):
        """Test convenience function for getting security score."""
        score = get_security_posture_score()
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    def test_generate_security_status_report(self):
        """Test convenience function for generating reports."""
        report = generate_security_status_report()
        assert isinstance(report, dict)
        assert "overall_security_score" in report
        assert "requirement_summary" in report

    def test_export_security_dashboard_section(self):
        """Test convenience function for exporting dashboard section."""
        section = export_security_dashboard_section()
        assert isinstance(section, str)
        assert "🔒 SECURITY REQUIREMENTS TRACKING" in section


class TestIntegration:
    """Integration tests for security metrics system."""

    def test_full_requirement_lifecycle(self):
        """Test complete requirement lifecycle."""
        tracker = SecurityRequirementsTracker()

        # Add new requirement
        new_req = SecurityRequirement(
            id="INT-TEST-001",
            title="Integration Test Requirement",
            description="Test full lifecycle",
            category=RequirementCategory.DATA_PROTECTION,
            priority=RequirementPriority.P1_HIGH,
            due_date=time.time() + (30 * 24 * 3600),  # 30 days
        )
        tracker.requirements[new_req.id] = new_req

        # Progress through lifecycle
        tracker.update_requirement_status(
            new_req.id, RequirementStatus.IN_PROGRESS, 25, "Started", "dev_team"
        )

        tracker.update_requirement_status(
            new_req.id, RequirementStatus.IN_PROGRESS, 75, "Nearly done", "dev_team"
        )

        tracker.update_requirement_status(
            new_req.id, RequirementStatus.COMPLETED, 100, "Finished", "dev_team"
        )

        # Verify final state
        final_req = tracker.requirements[new_req.id]
        assert final_req.status == RequirementStatus.COMPLETED
        assert final_req.completion_percentage == 100
        assert final_req.completed_date > 0
        assert final_req.update_count == 3

        # Verify metrics reflect the change
        metrics = tracker.calculate_security_metrics()
        assert metrics.security_posture_score > 0

    def test_metrics_accuracy(self):
        """Test metrics calculation accuracy."""
        tracker = SecurityRequirementsTracker()

        # Get baseline metrics
        initial_metrics = tracker.calculate_security_metrics()
        initial_score = initial_metrics.security_posture_score

        # Complete a high-priority requirement
        high_priority_reqs = [
            req
            for req in tracker.requirements.values()
            if req.priority == RequirementPriority.P1_HIGH
            and req.status != RequirementStatus.COMPLETED
        ]

        if high_priority_reqs:
            req = high_priority_reqs[0]
            tracker.update_requirement_status(
                req.id, RequirementStatus.COMPLETED, 100, "Test completion", "test"
            )

            # Verify metrics improved
            new_metrics = tracker.calculate_security_metrics()
            assert new_metrics.security_posture_score >= initial_score
            assert new_metrics.high_completion_rate >= initial_metrics.high_completion_rate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
