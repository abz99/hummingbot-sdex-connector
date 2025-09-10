"""
Stellar Security Metrics and Requirements Tracking Dashboard
Automated tracking and reporting for security requirements and compliance.
"""

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import auto, Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .stellar_logging import get_stellar_logger, LogCategory
from decimal import Decimal


class RequirementStatus(Enum):
    """Security requirement status states."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


class RequirementPriority(Enum):
    """Security requirement priority levels."""

    P0_CRITICAL = "P0"
    P1_HIGH = "P1"
    P2_MEDIUM = "P2"
    P3_LOW = "P3"
    REG_REGULATORY = "REG"


class RequirementCategory(Enum):
    """Security requirement categories."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ENCRYPTION = "encryption"
    KEY_MANAGEMENT = "key_management"
    MONITORING = "monitoring"
    COMPLIANCE = "compliance"
    NETWORK_SECURITY = "network_security"
    DATA_PROTECTION = "data_protection"
    INCIDENT_RESPONSE = "incident_response"


@dataclass
class SecurityRequirement:
    """Individual security requirement definition."""

    id: str
    title: str
    description: str
    category: RequirementCategory
    priority: RequirementPriority
    status: RequirementStatus = RequirementStatus.NOT_STARTED

    # Implementation details
    owner: str = "Security Team"
    assignee: Optional[str] = None
    implementation_file: Optional[str] = None
    test_file: Optional[str] = None
    config_file: Optional[str] = None

    # Timeline
    created_date: float = 0.0
    due_date: Optional[float] = None
    completed_date: Optional[float] = None

    # Compliance
    threat_addressed: List[str] = None
    regulatory_mapping: List[str] = None
    acceptance_criteria: List[str] = None

    # Metrics
    completion_percentage: int = 0
    effort_estimate_days: int = 0
    actual_effort_days: int = 0

    # Tracking
    last_updated: float = 0.0
    update_count: int = 0
    blocked_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.created_date == 0.0:
            self.created_date = time.time()
        if self.last_updated == 0.0:
            self.last_updated = time.time()
        if self.threat_addressed is None:
            self.threat_addressed = []
        if self.regulatory_mapping is None:
            self.regulatory_mapping = []
        if self.acceptance_criteria is None:
            self.acceptance_criteria = []

    def update_status(self, status: RequirementStatus, notes: str = "", user: str = "system") -> None:
        """Update requirement status with audit trail."""
        self.status = status
        self.last_updated = time.time()
        self.update_count += 1

        if status == RequirementStatus.COMPLETED:
            self.completed_date = time.time()
            self.completion_percentage = 100

        # Log status change
        logger = get_stellar_logger()
        logger.info(
            f"Security requirement status updated: {self.id}",
            category=LogCategory.SECURITY,
            requirement_id=self.id,
            old_status=self.status.value if hasattr(self, "_previous_status") else None,
            new_status=status.value,
            user=user,
            notes=notes,
        )

    def calculate_completion_score(self) -> float:
        """Calculate weighted completion score based on priority."""
        if self.status == RequirementStatus.COMPLETED:
            return 1.0
        elif self.status == RequirementStatus.IN_PROGRESS:
            return self.completion_percentage / 100.0
        else:
            return 0.0

    def is_overdue(self) -> bool:
        """Check if requirement is overdue."""
        if not self.due_date:
            return False
        return time.time() > self.due_date and self.status != RequirementStatus.COMPLETED

    def days_until_due(self) -> Optional[int]:
        """Calculate days until due date."""
        if not self.due_date:
            return None
        days = (self.due_date - time.time()) / (24 * 3600)
        return int(days)


@dataclass
class SecurityMetrics:
    """Security metrics and KPIs."""

    # Overall scores
    security_posture_score: float = 0.0
    compliance_score: float = 0.0
    risk_score: float = 0.0

    # Requirement completion rates
    critical_completion_rate: float = 0.0
    high_completion_rate: float = 0.0
    medium_completion_rate: float = 0.0
    regulatory_completion_rate: float = 0.0

    # Operational metrics
    security_incidents: int = 0
    vulnerability_response_time_days: float = 0.0
    hsm_operation_success_rate: float = 0.0
    authentication_failure_rate: float = 0.0
    security_training_completion: float = 0.0

    # Compliance metrics
    pci_compliance_score: float = 0.0
    aml_kyc_compliance_score: float = 0.0
    gdpr_compliance_score: float = 0.0

    # Performance metrics
    mean_time_to_detection_minutes: float = 0.0
    mean_time_to_response_minutes: float = 0.0
    false_positive_rate: float = 0.0

    # Calculated at runtime
    calculation_timestamp: float = 0.0

    def __post_init__(self) -> None:
        self.calculation_timestamp = time.time()


class SecurityRequirementsTracker:
    """Main security requirements tracking and metrics system."""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.logger = get_stellar_logger()
        self.data_dir = Path(data_dir or "security_tracking")
        self.data_dir.mkdir(exist_ok=True)

        self.requirements_file = self.data_dir / "security_requirements.json"
        self.metrics_file = self.data_dir / "security_metrics.json"
        self.audit_file = self.data_dir / "requirement_audit_log.json"

        # Load existing data
        self.requirements: Dict[str, SecurityRequirement] = {}
        self.metrics: Optional[SecurityMetrics] = None
        self._load_requirements()
        self._load_metrics()

        # Initialize with default requirements if empty
        if not self.requirements:
            self._initialize_default_requirements()

    def _load_requirements(self) -> None:
        """Load requirements from persistent storage."""
        if self.requirements_file.exists():
            try:
                with open(self.requirements_file, "r") as f:
                    data = json.load(f)
                    for req_id, req_data in data.items():
                        # Convert enums back from strings
                        req_data["category"] = RequirementCategory(req_data["category"])
                        req_data["priority"] = RequirementPriority(req_data["priority"])
                        req_data["status"] = RequirementStatus(req_data["status"])

                        self.requirements[req_id] = SecurityRequirement(**req_data)

                self.logger.info(
                    f"Loaded {len(self.requirements)} security requirements",
                    category=LogCategory.SECURITY,
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to load security requirements: {e}",
                    category=LogCategory.SECURITY,
                    exception=e,
                )

    def _load_metrics(self) -> None:
        """Load metrics from persistent storage."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, "r") as f:
                    data = json.load(f)
                    self.metrics = SecurityMetrics(**data)

                self.logger.info(
                    "Loaded security metrics",
                    category=LogCategory.SECURITY,
                    security_score=self.metrics.security_posture_score,
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to load security metrics: {e}",
                    category=LogCategory.SECURITY,
                    exception=e,
                )

    def _save_requirements(self) -> None:
        """Save requirements to persistent storage."""
        try:
            # Convert to serializable format
            data = {}
            for req_id, req in self.requirements.items():
                req_dict = asdict(req)
                # Convert enums to strings
                req_dict["category"] = req.category.value
                req_dict["priority"] = req.priority.value
                req_dict["status"] = req.status.value
                data[req_id] = req_dict

            with open(self.requirements_file, "w") as f:
                json.dump(data, f, indent=2)

            self.logger.debug(
                f"Saved {len(self.requirements)} security requirements",
                category=LogCategory.SECURITY,
            )
        except Exception as e:
            self.logger.error(
                f"Failed to save security requirements: {e}",
                category=LogCategory.SECURITY,
                exception=e,
            )

    def _save_metrics(self) -> None:
        """Save metrics to persistent storage."""
        if self.metrics:
            try:
                with open(self.metrics_file, "w") as f:
                    json.dump(asdict(self.metrics), f, indent=2)

                self.logger.debug(
                    "Saved security metrics",
                    category=LogCategory.SECURITY,
                    security_score=self.metrics.security_posture_score,
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to save security metrics: {e}",
                    category=LogCategory.SECURITY,
                    exception=e,
                )

    def _initialize_default_requirements(self) -> None:
        """Initialize with default security requirements."""
        default_requirements = [
            # Critical Requirements (P0)
            {
                "id": "SR-CRIT-001",
                "title": "Private Key Protection",
                "description": "All private keys MUST be protected using Hardware Security Modules (HSM)",
                "category": RequirementCategory.KEY_MANAGEMENT,
                "priority": RequirementPriority.P0_CRITICAL,
                "status": RequirementStatus.COMPLETED,
                "threat_addressed": ["Private Key Compromise"],
                "implementation_file": "stellar_security_manager.py",
                "completion_percentage": 100,
            },
            {
                "id": "SR-CRIT-002",
                "title": "Multi-Factor Authentication",
                "description": "All privileged operations MUST require multi-factor authentication",
                "category": RequirementCategory.AUTHENTICATION,
                "priority": RequirementPriority.P0_CRITICAL,
                "status": RequirementStatus.IN_PROGRESS,
                "threat_addressed": ["API Key Exploitation"],
                "completion_percentage": 60,
                "due_date": time.time() + (9 * 24 * 3600),  # 9 days from now
            },
            {
                "id": "SR-CRIT-003",
                "title": "Transaction Signing Security",
                "description": "All transaction signing MUST implement secure signing workflows",
                "category": RequirementCategory.KEY_MANAGEMENT,
                "priority": RequirementPriority.P0_CRITICAL,
                "status": RequirementStatus.COMPLETED,
                "threat_addressed": ["Trading Algorithm Manipulation"],
                "implementation_file": "stellar_hardware_wallets.py",
                "completion_percentage": 100,
            },
            {
                "id": "SR-CRIT-004",
                "title": "Zero Trust Architecture",
                "description": "System MUST implement zero-trust architecture with continuous verification",
                "category": RequirementCategory.NETWORK_SECURITY,
                "priority": RequirementPriority.P0_CRITICAL,
                "status": RequirementStatus.IN_PROGRESS,
                "threat_addressed": ["System-wide Security"],
                "completion_percentage": 80,
                "due_date": time.time() + (14 * 24 * 3600),  # 14 days from now
            },
            # High Priority Requirements (P1)
            {
                "id": "SR-HIGH-005",
                "title": "Real-time Threat Detection",
                "description": "System MUST implement real-time threat detection with automated response",
                "category": RequirementCategory.MONITORING,
                "priority": RequirementPriority.P1_HIGH,
                "status": RequirementStatus.NOT_STARTED,
                "threat_addressed": ["Multiple threat vectors"],
                "completion_percentage": 0,
                "due_date": time.time() + (24 * 24 * 3600),  # 24 days from now
            },
            {
                "id": "SR-HIGH-006",
                "title": "Data Encryption Standards",
                "description": "All sensitive data MUST be encrypted at rest and in transit",
                "category": RequirementCategory.ENCRYPTION,
                "priority": RequirementPriority.P1_HIGH,
                "status": RequirementStatus.COMPLETED,
                "threat_addressed": ["Data Breach"],
                "implementation_file": "stellar_vault_integration.py",
                "completion_percentage": 100,
            },
            {
                "id": "SR-HIGH-007",
                "title": "Audit Logging Framework",
                "description": "System MUST maintain comprehensive audit logs",
                "category": RequirementCategory.MONITORING,
                "priority": RequirementPriority.P1_HIGH,
                "status": RequirementStatus.COMPLETED,
                "threat_addressed": ["Compliance and Forensics"],
                "implementation_file": "stellar_logging.py",
                "completion_percentage": 100,
            },
            # Regulatory Requirements
            {
                "id": "SR-REG-010",
                "title": "PCI DSS Compliance",
                "description": "System MUST achieve and maintain PCI DSS Level 1 compliance",
                "category": RequirementCategory.COMPLIANCE,
                "priority": RequirementPriority.REG_REGULATORY,
                "status": RequirementStatus.NOT_STARTED,
                "regulatory_mapping": ["PCI DSS"],
                "completion_percentage": 0,
                "due_date": time.time() + (39 * 24 * 3600),  # 39 days from now
            },
            {
                "id": "SR-REG-011",
                "title": "AML/KYC Integration",
                "description": "System MUST integrate with AML/KYC systems for transaction monitoring",
                "category": RequirementCategory.COMPLIANCE,
                "priority": RequirementPriority.REG_REGULATORY,
                "status": RequirementStatus.NOT_STARTED,
                "regulatory_mapping": ["BSA/AML", "Travel Rule"],
                "completion_percentage": 0,
                "due_date": time.time() + (54 * 24 * 3600),  # 54 days from now
            },
        ]

        for req_data in default_requirements:
            req = SecurityRequirement(**req_data)
            self.requirements[req.id] = req

        self._save_requirements()

        self.logger.info(
            f"Initialized {len(default_requirements)} default security requirements",
            category=LogCategory.SECURITY,
        )

    def update_requirement_status(
        self,
        req_id: str,
        status: RequirementStatus,
        completion_percentage: Optional[int] = None,
        notes: str = "",
        user: str = "system",
    ) -> None:
        """Update requirement status with full audit trail."""
        if req_id not in self.requirements:
            raise ValueError(f"Requirement not found: {req_id}")

        requirement = self.requirements[req_id]
        old_status = requirement.status

        requirement.update_status(status, notes, user)

        if completion_percentage is not None:
            requirement.completion_percentage = completion_percentage

        # Save changes
        self._save_requirements()

        # Log audit trail
        audit_entry = {
            "timestamp": time.time(),
            "requirement_id": req_id,
            "old_status": old_status.value,
            "new_status": status.value,
            "completion_percentage": requirement.completion_percentage,
            "user": user,
            "notes": notes,
        }

        self._log_audit_event(audit_entry)

        # Recalculate metrics
        self.calculate_security_metrics()

        self.logger.info(
            f"Updated security requirement: {req_id}",
            category=LogCategory.SECURITY,
            requirement_id=req_id,
            new_status=status.value,
            completion=requirement.completion_percentage,
        )

    def _log_audit_event(self, audit_entry: Dict[str, Any]) -> None:
        """Log audit event to persistent audit trail."""
        try:
            audit_log = []
            if self.audit_file.exists():
                with open(self.audit_file, "r") as f:
                    audit_log = json.load(f)

            audit_log.append(audit_entry)

            # Keep only last 1000 entries
            if len(audit_log) > 1000:
                audit_log = audit_log[-1000:]

            with open(self.audit_file, "w") as f:
                json.dump(audit_log, f, indent=2)

        except Exception as e:
            self.logger.error(
                f"Failed to log audit event: {e}", category=LogCategory.SECURITY, exception=e
            )

    def calculate_security_metrics(self) -> SecurityMetrics:
        """Calculate comprehensive security metrics."""
        if not self.requirements:
            return SecurityMetrics()

        # Categorize requirements by priority
        critical_reqs = [
            r for r in self.requirements.values() if r.priority == RequirementPriority.P0_CRITICAL
        ]
        high_reqs = [
            r for r in self.requirements.values() if r.priority == RequirementPriority.P1_HIGH
        ]
        medium_reqs = [
            r for r in self.requirements.values() if r.priority == RequirementPriority.P2_MEDIUM
        ]
        regulatory_reqs = [
            r
            for r in self.requirements.values()
            if r.priority == RequirementPriority.REG_REGULATORY
        ]

        # Calculate completion rates
        def completion_rate(reqs: List[SecurityRequirement]) -> float:
            if not reqs:
                return 0.0
            completed = sum(1 for r in reqs if r.status == RequirementStatus.COMPLETED)
            return (completed / len(reqs)) * 100.0

        # Calculate weighted security posture score
        weights = {
            RequirementPriority.P0_CRITICAL: 0.4,
            RequirementPriority.P1_HIGH: 0.3,
            RequirementPriority.P2_MEDIUM: 0.2,
            RequirementPriority.REG_REGULATORY: 0.1,
        }

        # Calculate weighted score by category, normalized by number of requirements in each category
        category_scores = {}
        category_counts = {}

        for req in self.requirements.values():
            completion_score = req.calculate_completion_score()
            priority = req.priority

            if priority not in category_scores:
                category_scores[priority] = 0.0
                category_counts[priority] = 0

            category_scores[priority] += completion_score
            category_counts[priority] += 1

        # Calculate average completion score for each priority level
        weighted_score = 0.0
        for priority, weight in weights.items():
            if priority in category_scores and category_counts[priority] > 0:
                avg_completion = category_scores[priority] / category_counts[priority]
                weighted_score += avg_completion * weight

        security_posture_score = weighted_score * 100.0

        # Mock operational metrics (would be collected from monitoring systems)
        metrics = SecurityMetrics(
            security_posture_score=security_posture_score,
            compliance_score=(completion_rate(regulatory_reqs) + completion_rate(critical_reqs))
            / 2,
            critical_completion_rate=completion_rate(critical_reqs),
            high_completion_rate=completion_rate(high_reqs),
            medium_completion_rate=completion_rate(medium_reqs),
            regulatory_completion_rate=completion_rate(regulatory_reqs),
            # Mock operational metrics (would come from monitoring)
            security_incidents=0,
            vulnerability_response_time_days=2.3,
            hsm_operation_success_rate=99.8,
            authentication_failure_rate=0.3,
            security_training_completion=85.0,
            # Mock performance metrics
            mean_time_to_detection_minutes=15.0,
            mean_time_to_response_minutes=45.0,
            false_positive_rate=1.8,
            # Mock compliance scores
            pci_compliance_score=75.0,
            aml_kyc_compliance_score=60.0,
            gdpr_compliance_score=88.0,
        )

        self.metrics = metrics
        self._save_metrics()

        self.logger.info(
            f"Calculated security metrics - Overall score: {security_posture_score:.1f}",
            category=LogCategory.SECURITY,
            security_posture_score=security_posture_score,
            critical_completion=metrics.critical_completion_rate,
            high_completion=metrics.high_completion_rate,
        )

        return metrics

    def get_overdue_requirements(self) -> List[SecurityRequirement]:
        """Get list of overdue requirements."""
        return [req for req in self.requirements.values() if req.is_overdue()]

    def get_requirements_by_status(self, status: RequirementStatus) -> List[SecurityRequirement]:
        """Get requirements filtered by status."""
        return [req for req in self.requirements.values() if req.status == status]

    def get_requirements_by_priority(
        self, priority: RequirementPriority
    ) -> List[SecurityRequirement]:
        """Get requirements filtered by priority."""
        return [req for req in self.requirements.values() if req.priority == priority]

    def generate_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive security status report."""
        if not self.metrics:
            self.calculate_security_metrics()

        active_requirements = []
        for req in self.requirements.values():
            if req.status in [RequirementStatus.IN_PROGRESS, RequirementStatus.NOT_STARTED]:
                active_requirements.append(
                    {
                        "id": req.id,
                        "title": req.title,
                        "priority": req.priority.value,
                        "status": req.status.value,
                        "owner": req.owner,
                        "due_date": (
                            datetime.fromtimestamp(req.due_date).strftime("%Y-%m-%d")
                            if req.due_date
                            else None
                        ),
                        "completion_percentage": req.completion_percentage,
                        "days_until_due": req.days_until_due(),
                    }
                )

        # Ensure metrics are calculated
        if not self.metrics:
            self.calculate_security_metrics()

        metrics = self.metrics or SecurityMetrics()  # Fallback to default

        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_security_score": metrics.security_posture_score,
            "requirement_summary": {
                "total": len(self.requirements),
                "completed": len(self.get_requirements_by_status(RequirementStatus.COMPLETED)),
                "in_progress": len(self.get_requirements_by_status(RequirementStatus.IN_PROGRESS)),
                "not_started": len(self.get_requirements_by_status(RequirementStatus.NOT_STARTED)),
                "blocked": len(self.get_requirements_by_status(RequirementStatus.BLOCKED)),
                "overdue": len(self.get_overdue_requirements()),
            },
            "completion_rates": {
                "critical": metrics.critical_completion_rate,
                "high": metrics.high_completion_rate,
                "medium": metrics.medium_completion_rate,
                "regulatory": metrics.regulatory_completion_rate,
            },
            "operational_metrics": {
                "security_incidents": metrics.security_incidents,
                "vulnerability_response_time_days": metrics.vulnerability_response_time_days,
                "hsm_success_rate": metrics.hsm_operation_success_rate,
                "auth_failure_rate": metrics.authentication_failure_rate,
            },
            "active_requirements": active_requirements[:10],  # Top 10
            "overdue_requirements": [
                {"id": req.id, "title": req.title, "days_overdue": -req.days_until_due()}
                for req in self.get_overdue_requirements()
            ],
        }

        return report

    def export_project_status_section(self) -> str:
        """Export security section for PROJECT_STATUS.md integration."""
        if not self.metrics:
            self.calculate_security_metrics()

        active_reqs = [
            req
            for req in self.requirements.values()
            if req.status in [RequirementStatus.IN_PROGRESS, RequirementStatus.NOT_STARTED]
        ][
            :5
        ]  # Top 5 active

        # Generate status indicators based on scores
        def status_indicator(score: float) -> str:
            if score >= 90:
                return "✅"
            elif score >= 70:
                return "🟡"
            else:
                return "🔴"

        section = f"""### 🔒 SECURITY REQUIREMENTS TRACKING

#### Security Posture Dashboard
- **Overall Security Score**: {self.metrics.security_posture_score:.0f}/100 (Target: >90) {status_indicator(self.metrics.security_posture_score)}
- **Critical Requirements (P0)**: {len(self.get_requirements_by_status(RequirementStatus.COMPLETED))} of {len(self.get_requirements_by_priority(RequirementPriority.P0_CRITICAL))} Complete ({self.metrics.critical_completion_rate:.0f}%) {status_indicator(self.metrics.critical_completion_rate)}
- **High Priority Requirements (P1)**: {self.metrics.high_completion_rate:.0f}% Complete {status_indicator(self.metrics.high_completion_rate)}
- **Medium Priority Requirements (P2)**: {self.metrics.medium_completion_rate:.0f}% Complete {status_indicator(self.metrics.medium_completion_rate)}
- **Regulatory Compliance (REG)**: {self.metrics.regulatory_completion_rate:.0f}% Complete {status_indicator(self.metrics.regulatory_completion_rate)}

#### Active Security Requirements
| ID | Priority | Title | Status | Owner | Target Date |
|----|----------|-------|--------|-------|-------------|"""

        for req in active_reqs:
            status_emoji = "🔄" if req.status == RequirementStatus.IN_PROGRESS else "📋"
            due_date = (
                datetime.fromtimestamp(req.due_date).strftime("%Y-%m-%d") if req.due_date else "TBD"
            )
            section += f"\n| {req.id} | {req.priority.value} | {req.title} | {status_emoji} {req.status.value.replace('_', ' ').title()} | {req.owner} | {due_date} |"

        section += f"""

#### Security Metrics (Current Period)
- **Security Incidents**: {self.metrics.security_incidents} (Target: 0) {"✅" if self.metrics.security_incidents == 0 else "🔴"}
- **Vulnerability Response Time**: {self.metrics.vulnerability_response_time_days:.1f} days (Target: <7 days) {"✅" if self.metrics.vulnerability_response_time_days < 7 else "🔴"}
- **HSM Operation Success Rate**: {self.metrics.hsm_operation_success_rate:.1f}% (Target: >99.9%) {status_indicator(self.metrics.hsm_operation_success_rate)}
- **Authentication Failure Rate**: {self.metrics.authentication_failure_rate:.1f}% (Target: <0.5%) {"✅" if self.metrics.authentication_failure_rate < 0.5 else "🟡"}
- **Security Training Completion**: {self.metrics.security_training_completion:.0f}% (Target: 100%) {status_indicator(self.metrics.security_training_completion)}"""

        return section


# Global security requirements tracker instance
_security_tracker: Optional[SecurityRequirementsTracker] = None


def get_security_tracker() -> SecurityRequirementsTracker:
    """Get global security requirements tracker instance."""
    global _security_tracker
    if _security_tracker is None:
        _security_tracker = SecurityRequirementsTracker()
    return _security_tracker


# Convenience functions for common operations
def update_security_requirement(
    req_id: str,
    status: RequirementStatus,
    completion_percentage: Optional[int] = None,
    notes: str = "",
    user: str = "system",
) -> None:
    """Update a security requirement status."""
    tracker = get_security_tracker()
    tracker.update_requirement_status(req_id, status, completion_percentage, notes, user)


def get_security_posture_score() -> float:
    """Get current security posture score."""
    tracker = get_security_tracker()
    metrics = tracker.calculate_security_metrics()
    return metrics.security_posture_score


def generate_security_status_report() -> Dict[str, Any]:
    """Generate comprehensive security status report."""
    tracker = get_security_tracker()
    return tracker.generate_status_report()


def export_security_dashboard_section() -> str:
    """Export security dashboard section for PROJECT_STATUS.md."""
    tracker = get_security_tracker()
    return tracker.export_project_status_section()
