#!/usr/bin/env python3
"""
Verified Status System - Truth-Source Status Model with No Manual Overrides
All status claims are driven by verification protocols with zero manual override capability.
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Import enforcement protocols - handle both relative and absolute imports
try:
    from .claude_hard_enforcement_protocol import HardEnforcementProtocol, CriticalEnforcementError
    from .claude_mandatory_consensus_protocol import MandatoryConsensusProtocol, ConsensusRequiredError
except ImportError:
    # Fall back to importing from current directory
    import importlib.util

    # Import hard enforcement protocol
    spec = importlib.util.spec_from_file_location(
        "claude_hard_enforcement_protocol",
        ".claude_hard_enforcement_protocol.py"
    )
    hard_enforcement_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hard_enforcement_module)
    HardEnforcementProtocol = hard_enforcement_module.HardEnforcementProtocol
    CriticalEnforcementError = hard_enforcement_module.CriticalEnforcementError

    # Import consensus protocol
    spec = importlib.util.spec_from_file_location(
        "claude_mandatory_consensus_protocol",
        ".claude_mandatory_consensus_protocol.py"
    )
    consensus_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(consensus_module)
    MandatoryConsensusProtocol = consensus_module.MandatoryConsensusProtocol
    ConsensusRequiredError = consensus_module.ConsensusRequiredError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] VERIFIED_STATUS: %(message)s',
    handlers=[
        logging.FileHandler('logs/verified_status_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StatusLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class VerificationStatus(Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED_VERIFICATION = "failed_verification"
    ENFORCEMENT_BLOCKED = "enforcement_blocked"
    CONSENSUS_REQUIRED = "consensus_required"


@dataclass
class VerifiedStatusEntry:
    """Represents a verified status entry with enforcement backing"""
    component: str
    status_claim: str
    verification_status: VerificationStatus
    verification_timestamp: datetime
    verification_evidence: Dict[str, Any]
    enforcement_passed: bool
    consensus_achieved: bool
    status_level: StatusLevel
    manual_override_blocked: bool = True  # Always true - no overrides allowed


@dataclass
class SystemStatus:
    """Complete system status based on verification"""
    overall_status: str
    verification_timestamp: datetime
    component_statuses: List[VerifiedStatusEntry]
    enforcement_summary: str
    consensus_summary: str
    critical_violations: List[str]
    next_actions: List[str]


class VerifiedStatusSystem:
    """Truth-source status system with mandatory verification"""

    def __init__(self):
        self.enforcement_protocol = HardEnforcementProtocol()
        self.consensus_protocol = MandatoryConsensusProtocol()
        self.status_file = "logs/verified_system_status.json"
        self.critical_components = [
            "ci_pipelines",
            "production_deployment",
            "security_compliance",
            "quality_gates",
            "operational_readiness"
        ]

        # Ensure log directory exists
        os.makedirs("logs", exist_ok=True)

    def get_verified_ci_pipeline_status(self) -> VerifiedStatusEntry:
        """Get verified CI pipeline status with enforcement backing"""
        logger.info("🔍 VERIFYING CI PIPELINE STATUS")

        try:
            # Get enforcement result
            enforcement_result = self.enforcement_protocol.check_all_ci_pipelines_with_enforcement()

            # Determine verification status
            if enforcement_result.enforcement_passed:
                verification_status = VerificationStatus.VERIFIED
                status_claim = "CI Pipelines Operational"
                enforcement_passed = True
            else:
                verification_status = VerificationStatus.FAILED_VERIFICATION
                status_claim = f"CI Pipelines Failing ({len(enforcement_result.failing_pipelines)} issues)"
                enforcement_passed = False

            # Collect evidence
            verification_evidence = {
                "total_pipelines": len(enforcement_result.all_pipelines),
                "passing_pipelines": len(enforcement_result.all_pipelines) - len(enforcement_result.failing_pipelines),
                "failing_pipelines": len(enforcement_result.failing_pipelines),
                "enforcement_action": enforcement_result.enforcement_action,
                "pipeline_details": [
                    {
                        "name": p.name,
                        "status": p.status,
                        "conclusion": p.conclusion
                    } for p in enforcement_result.all_pipelines
                ]
            }

            return VerifiedStatusEntry(
                component="ci_pipelines",
                status_claim=status_claim,
                verification_status=verification_status,
                verification_timestamp=enforcement_result.timestamp,
                verification_evidence=verification_evidence,
                enforcement_passed=enforcement_passed,
                consensus_achieved=False,  # Will be set by consensus check
                status_level=StatusLevel.CRITICAL,
                manual_override_blocked=True
            )

        except Exception as e:
            logger.error(f"❌ CI Pipeline verification failed: {e}")
            return VerifiedStatusEntry(
                component="ci_pipelines",
                status_claim="CI Pipeline Verification Failed",
                verification_status=VerificationStatus.ENFORCEMENT_BLOCKED,
                verification_timestamp=datetime.now(),
                verification_evidence={"error": str(e)},
                enforcement_passed=False,
                consensus_achieved=False,
                status_level=StatusLevel.CRITICAL,
                manual_override_blocked=True
            )

    def get_verified_operational_readiness(self) -> VerifiedStatusEntry:
        """Get verified operational readiness status"""
        logger.info("🔍 VERIFYING OPERATIONAL READINESS")

        # Operational readiness depends on CI pipeline status
        ci_status = self.get_verified_ci_pipeline_status()

        if ci_status.enforcement_passed:
            return VerifiedStatusEntry(
                component="operational_readiness",
                status_claim="System Operationally Ready",
                verification_status=VerificationStatus.VERIFIED,
                verification_timestamp=datetime.now(),
                verification_evidence={"ci_pipelines": "operational", "dependencies": ci_status.verification_evidence},
                enforcement_passed=True,
                consensus_achieved=False,
                status_level=StatusLevel.HIGH,
                manual_override_blocked=True
            )
        else:
            return VerifiedStatusEntry(
                component="operational_readiness",
                status_claim="System Not Operationally Ready",
                verification_status=VerificationStatus.FAILED_VERIFICATION,
                verification_timestamp=datetime.now(),
                verification_evidence={"ci_pipelines": "failing", "blocking_issues": ci_status.verification_evidence},
                enforcement_passed=False,
                consensus_achieved=False,
                status_level=StatusLevel.CRITICAL,
                manual_override_blocked=True
            )

    def verify_status_claim_with_consensus(self, claim_type: str, claim_details: str) -> VerifiedStatusEntry:
        """Verify status claim requiring both enforcement and consensus"""
        logger.info(f"🔒 VERIFYING CLAIM WITH CONSENSUS: {claim_type}")

        # First check enforcement
        try:
            self.enforcement_protocol.enforce_success_claim_prohibition(claim_details)
            enforcement_passed = True
        except CriticalEnforcementError:
            enforcement_passed = False

        # Then check consensus
        try:
            self.consensus_protocol.enforce_consensus_requirement(claim_type, claim_details)
            consensus_achieved = True
        except ConsensusRequiredError:
            consensus_achieved = False

        # Determine final verification status
        if enforcement_passed and consensus_achieved:
            verification_status = VerificationStatus.VERIFIED
            status_claim = f"Verified: {claim_details}"
        elif not enforcement_passed:
            verification_status = VerificationStatus.ENFORCEMENT_BLOCKED
            status_claim = f"Enforcement Blocked: {claim_details}"
        elif not consensus_achieved:
            verification_status = VerificationStatus.CONSENSUS_REQUIRED
            status_claim = f"Consensus Required: {claim_details}"
        else:
            verification_status = VerificationStatus.FAILED_VERIFICATION
            status_claim = f"Verification Failed: {claim_details}"

        return VerifiedStatusEntry(
            component=claim_type,
            status_claim=status_claim,
            verification_status=verification_status,
            verification_timestamp=datetime.now(),
            verification_evidence={
                "enforcement_passed": enforcement_passed,
                "consensus_achieved": consensus_achieved,
                "claim_details": claim_details
            },
            enforcement_passed=enforcement_passed,
            consensus_achieved=consensus_achieved,
            status_level=StatusLevel.CRITICAL,
            manual_override_blocked=True
        )

    def generate_verified_system_status(self) -> SystemStatus:
        """Generate complete verified system status"""
        logger.info("📊 GENERATING VERIFIED SYSTEM STATUS")

        component_statuses = []

        # Get verified status for all critical components
        ci_status = self.get_verified_ci_pipeline_status()
        component_statuses.append(ci_status)

        operational_status = self.get_verified_operational_readiness()
        component_statuses.append(operational_status)

        # Determine overall status
        critical_failures = [s for s in component_statuses if s.status_level == StatusLevel.CRITICAL and not s.enforcement_passed]
        high_failures = [s for s in component_statuses if s.status_level == StatusLevel.HIGH and not s.enforcement_passed]

        if critical_failures:
            overall_status = f"❌ CRITICAL FAILURES ({len(critical_failures)} components)"
            enforcement_summary = "ENFORCEMENT BLOCKING OPERATIONS"
        elif high_failures:
            overall_status = f"⚠️ HIGH PRIORITY ISSUES ({len(high_failures)} components)"
            enforcement_summary = "ENFORCEMENT ACTIVE - PARTIAL RESTRICTIONS"
        else:
            overall_status = "✅ ALL SYSTEMS OPERATIONAL"
            enforcement_summary = "ENFORCEMENT PASSED - OPERATIONS AUTHORIZED"

        # Consensus summary
        consensus_required = [s for s in component_statuses if s.verification_status == VerificationStatus.CONSENSUS_REQUIRED]
        if consensus_required:
            consensus_summary = f"CONSENSUS REQUIRED for {len(consensus_required)} components"
        else:
            consensus_summary = "NO CONSENSUS REQUIREMENTS PENDING"

        # Critical violations
        critical_violations = []
        for status in component_statuses:
            if status.verification_status == VerificationStatus.ENFORCEMENT_BLOCKED:
                critical_violations.append(f"{status.component}: {status.status_claim}")
            elif status.verification_status == VerificationStatus.FAILED_VERIFICATION:
                critical_violations.append(f"{status.component}: Verification failed")

        # Next actions
        next_actions = []
        if critical_failures:
            next_actions.append("🚨 Fix critical component failures before proceeding")
            next_actions.append("📋 Address enforcement violations")
        if consensus_required:
            next_actions.append("🤝 Obtain required agent consensus")
        if not critical_failures and not consensus_required:
            next_actions.append("✅ System ready for operations")

        system_status = SystemStatus(
            overall_status=overall_status,
            verification_timestamp=datetime.now(),
            component_statuses=component_statuses,
            enforcement_summary=enforcement_summary,
            consensus_summary=consensus_summary,
            critical_violations=critical_violations,
            next_actions=next_actions
        )

        # Save verified status
        self._save_verified_status(system_status)

        return system_status

    def _save_verified_status(self, system_status: SystemStatus) -> None:
        """Save verified status to file"""
        try:
            status_data = {
                "overall_status": system_status.overall_status,
                "verification_timestamp": system_status.verification_timestamp.isoformat(),
                "enforcement_summary": system_status.enforcement_summary,
                "consensus_summary": system_status.consensus_summary,
                "critical_violations": system_status.critical_violations,
                "next_actions": system_status.next_actions,
                "component_statuses": [
                    {
                        "component": s.component,
                        "status_claim": s.status_claim,
                        "verification_status": s.verification_status.value,
                        "verification_timestamp": s.verification_timestamp.isoformat(),
                        "verification_evidence": s.verification_evidence,
                        "enforcement_passed": s.enforcement_passed,
                        "consensus_achieved": s.consensus_achieved,
                        "status_level": s.status_level.value,
                        "manual_override_blocked": s.manual_override_blocked
                    } for s in system_status.component_statuses
                ]
            }

            with open(self.status_file, 'w') as f:
                json.dump(status_data, f, indent=2)

            logger.info(f"💾 Verified status saved to {self.status_file}")

        except Exception as e:
            logger.error(f"Failed to save verified status: {e}")

    def enforce_verified_status_only(self, requested_claim: str) -> str:
        """Enforce that only verified status claims are allowed"""
        logger.info(f"🔒 ENFORCING VERIFIED STATUS ONLY for: {requested_claim}")

        # Generate current verified status
        system_status = self.generate_verified_system_status()

        # Check if the requested claim matches verified reality
        claim_lower = requested_claim.lower()

        # Common false claim patterns
        false_claim_indicators = [
            "mission accomplished",
            "completed",
            "operational",
            "successful",
            "fixed",
            "working"
        ]

        contains_success_claim = any(indicator in claim_lower for indicator in false_claim_indicators)

        if contains_success_claim:
            # This appears to be a success claim - verify against enforcement
            critical_violations = system_status.critical_violations

            if critical_violations:
                # Block the false claim and return verified status
                logger.error("🚨 BLOCKING FALSE SUCCESS CLAIM")

                verified_report = f"""
🔒 VERIFIED STATUS ENFORCEMENT ACTIVE

**Requested Claim**: {requested_claim}
**Enforcement Action**: BLOCKED - False success claim detected

## 📊 VERIFIED SYSTEM STATUS

**Overall Status**: {system_status.overall_status}
**Verification Timestamp**: {system_status.verification_timestamp.isoformat()}
**Enforcement Summary**: {system_status.enforcement_summary}

## 🚨 CRITICAL VIOLATIONS

""" + "\n".join([f"- {violation}" for violation in critical_violations])

                verified_report += f"""

## 📋 COMPONENT STATUS

""" + "\n".join([
    f"- **{s.component}**: {s.status_claim} ({s.verification_status.value})"
    for s in system_status.component_statuses
])

                verified_report += f"""

## ⚡ NEXT ACTIONS

""" + "\n".join([f"- {action}" for action in system_status.next_actions])

                verified_report += """

## 🔒 ENFORCEMENT NOTICE

This status was generated by the Verified Status System to prevent false success reporting.
Only verification-backed status claims are permitted.

**Manual Override**: BLOCKED - No override capability available
**Truth Source**: Enforcement protocols and agent consensus
"""

                return verified_report

        # If no success claim or verification passes, return original claim
        return requested_claim

    def generate_verified_status_report(self) -> str:
        """Generate comprehensive verified status report"""
        system_status = self.generate_verified_system_status()

        report = f"""
# 🔒 VERIFIED SYSTEM STATUS REPORT

**Generated**: {system_status.verification_timestamp.isoformat()}
**Overall Status**: {system_status.overall_status}
**Enforcement**: {system_status.enforcement_summary}
**Consensus**: {system_status.consensus_summary}

## 📊 Component Status Verification

"""

        for status in system_status.component_statuses:
            status_emoji = "✅" if status.enforcement_passed else "❌"
            consensus_emoji = "🤝" if status.consensus_achieved else "⏳"

            report += f"""
### {status_emoji} {status.component.replace('_', ' ').title()}

- **Status**: {status.status_claim}
- **Verification**: {status.verification_status.value}
- **Enforcement**: {"PASSED" if status.enforcement_passed else "FAILED"}
- **Consensus**: {consensus_emoji} {"ACHIEVED" if status.consensus_achieved else "PENDING"}
- **Level**: {status.status_level.value.upper()}
- **Override**: {"BLOCKED" if status.manual_override_blocked else "ALLOWED"}

"""

        if system_status.critical_violations:
            report += """
## 🚨 Critical Violations

""" + "\n".join([f"- {violation}" for violation in system_status.critical_violations])

        report += f"""

## ⚡ Next Actions

""" + "\n".join([f"- {action}" for action in system_status.next_actions])

        report += """

## 🔒 Verification Authority

This report is generated by the Verified Status System with:

- **Hard Enforcement Protocol**: Active monitoring and blocking
- **Multi-Agent Consensus**: Required for critical claims
- **Zero Manual Override**: No bypass capability for critical components
- **Truth-Source Verification**: All claims backed by enforcement evidence

**System Integrity**: MAINTAINED through mandatory verification
"""

        return report


def main():
    """Main verified status system execution"""
    verified_system = VerifiedStatusSystem()

    if len(sys.argv) > 1 and sys.argv[1] == "--enforce-claim":
        claim = " ".join(sys.argv[2:])
        result = verified_system.enforce_verified_status_only(claim)
        print(result)
    else:
        # Generate verified status report
        report = verified_system.generate_verified_status_report()
        print(report)


if __name__ == "__main__":
    main()