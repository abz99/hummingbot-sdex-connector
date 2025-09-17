#!/usr/bin/env python3
"""
Hard Enforcement Protocol - MANDATORY CI Pipeline Status Verification
Implements ZERO-TOLERANCE verification system that BLOCKS false success claims.
"""

import sys
import os
import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Optional, NoReturn
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] ENFORCEMENT: %(message)s',
    handlers=[
        logging.FileHandler('logs/hard_enforcement.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class PipelineStatus:
    """Represents the status of a CI pipeline"""
    name: str
    status: str  # completed, in_progress, failure
    conclusion: str  # success, failure, None
    run_id: str
    duration: Optional[str] = None


@dataclass
class EnforcementResult:
    """Result of hard enforcement verification"""
    enforcement_passed: bool
    all_pipelines: List[PipelineStatus]
    failing_pipelines: List[PipelineStatus]
    timestamp: datetime
    summary: str
    enforcement_action: str


class CriticalEnforcementError(Exception):
    """Raised when critical enforcement check fails - CANNOT BE BYPASSED"""
    def __init__(self, message: str, enforcement_result: EnforcementResult):
        self.enforcement_result = enforcement_result
        super().__init__(message)


class HardEnforcementProtocol:
    """ZERO-TOLERANCE enforcement system for CI pipeline status verification"""

    def __init__(self):
        self.required_pipelines = [
            "Stellar Hummingbot Connector CI",
            "Production Deployment Pipeline",
            "CI Health Dashboard"
        ]
        self.enforcement_log_file = "logs/hard_enforcement.log"
        self.critical_violations_file = "logs/critical_violations.json"

        # Ensure log directory exists
        os.makedirs("logs", exist_ok=True)

    def check_all_ci_pipelines_with_enforcement(self) -> EnforcementResult:
        """Check CI pipeline status with MANDATORY enforcement"""
        logger.info("🔒 INITIATING HARD ENFORCEMENT VERIFICATION...")

        try:
            # Get pipeline status using GitHub CLI
            result = subprocess.run([
                "gh", "run", "list", "--limit", "10"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return self._create_enforcement_failure(
                    "GitHub CLI command failed",
                    f"Command error: {result.stderr}"
                )

            if not result.stdout.strip():
                return self._create_enforcement_failure(
                    "Empty GitHub response",
                    "No pipeline data available"
                )

            # Parse pipeline runs
            lines = result.stdout.strip().split('\n')
            runs_data = []

            for line in lines:
                if '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        runs_data.append({
                            'status': parts[0],
                            'conclusion': parts[1] if parts[1] else None,
                            'name': parts[2],
                            'displayTitle': parts[2]
                        })

            # Find latest run for each required pipeline
            latest_pipelines = {}
            for run in runs_data:
                pipeline_name = run['name']
                if pipeline_name in self.required_pipelines:
                    if pipeline_name not in latest_pipelines:
                        latest_pipelines[pipeline_name] = run

            # Analyze pipeline status with ZERO TOLERANCE
            all_pipelines = []
            failing_pipelines = []

            for pipeline_name in self.required_pipelines:
                if pipeline_name in latest_pipelines:
                    run = latest_pipelines[pipeline_name]
                    pipeline = PipelineStatus(
                        name=pipeline_name,
                        status=run.get('status', 'unknown'),
                        conclusion=run.get('conclusion', 'unknown'),
                        run_id=str(run.get('databaseId', 'unknown'))
                    )
                    all_pipelines.append(pipeline)

                    # ZERO TOLERANCE: Any non-success is FAILURE
                    if (pipeline.status != 'completed' or
                        pipeline.conclusion != 'success'):
                        failing_pipelines.append(pipeline)
                else:
                    # Missing pipeline is CRITICAL FAILURE
                    pipeline = PipelineStatus(
                        name=pipeline_name,
                        status="missing",
                        conclusion="critical_failure",
                        run_id="none"
                    )
                    all_pipelines.append(pipeline)
                    failing_pipelines.append(pipeline)

            # HARD ENFORCEMENT DECISION
            enforcement_passed = len(failing_pipelines) == 0

            if enforcement_passed:
                summary = f"✅ ALL {len(self.required_pipelines)} CI PIPELINES OPERATIONAL"
                enforcement_action = "ALLOW_OPERATIONS"
            else:
                summary = f"🚨 {len(failing_pipelines)}/{len(self.required_pipelines)} CI PIPELINES FAILING"
                enforcement_action = "BLOCK_ALL_SUCCESS_CLAIMS"

            enforcement_result = EnforcementResult(
                enforcement_passed=enforcement_passed,
                all_pipelines=all_pipelines,
                failing_pipelines=failing_pipelines,
                timestamp=datetime.now(),
                summary=summary,
                enforcement_action=enforcement_action
            )

            # Log enforcement result
            self._log_enforcement_result(enforcement_result)

            return enforcement_result

        except Exception as e:
            logger.error(f"🚨 ENFORCEMENT SYSTEM FAILURE: {e}")
            return self._create_enforcement_failure(
                "Enforcement system error",
                str(e)
            )

    def _create_enforcement_failure(self, reason: str, details: str) -> EnforcementResult:
        """Create enforcement failure result"""
        return EnforcementResult(
            enforcement_passed=False,
            all_pipelines=[],
            failing_pipelines=[],
            timestamp=datetime.now(),
            summary=f"🚨 ENFORCEMENT FAILURE: {reason}",
            enforcement_action="BLOCK_ALL_OPERATIONS"
        )

    def _log_enforcement_result(self, result: EnforcementResult) -> None:
        """Log enforcement result with CRITICAL SEVERITY"""
        logger.info("=" * 100)
        logger.info("🔒 HARD ENFORCEMENT VERIFICATION RESULT")
        logger.info("=" * 100)
        logger.info(f"Timestamp: {result.timestamp}")
        logger.info(f"Enforcement Status: {result.summary}")
        logger.info(f"Enforcement Action: {result.enforcement_action}")
        logger.info("")

        for pipeline in result.all_pipelines:
            status_emoji = "✅" if pipeline.conclusion == "success" else "🚨"
            logger.info(f"{status_emoji} {pipeline.name}: {pipeline.status} / {pipeline.conclusion}")

        if result.failing_pipelines:
            logger.error("")
            logger.error("🚨 CRITICAL ENFORCEMENT VIOLATIONS:")
            for pipeline in result.failing_pipelines:
                logger.error(f"   - {pipeline.name}: {pipeline.status} / {pipeline.conclusion}")

        logger.info("=" * 100)

        # Save critical violations to file
        if not result.enforcement_passed:
            self._record_critical_violation(result)

    def _record_critical_violation(self, result: EnforcementResult) -> None:
        """Record critical violations for audit trail"""
        try:
            violations = []
            try:
                with open(self.critical_violations_file, 'r') as f:
                    violations = json.load(f)
            except FileNotFoundError:
                pass

            violations.append({
                "timestamp": result.timestamp.isoformat(),
                "enforcement_passed": result.enforcement_passed,
                "summary": result.summary,
                "enforcement_action": result.enforcement_action,
                "failing_count": len(result.failing_pipelines),
                "total_count": len(result.all_pipelines),
                "failing_pipelines": [
                    {
                        "name": p.name,
                        "status": p.status,
                        "conclusion": p.conclusion
                    } for p in result.failing_pipelines
                ]
            })

            # Keep only last 100 violations
            violations = violations[-100:]

            with open(self.critical_violations_file, 'w') as f:
                json.dump(violations, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to record critical violation: {e}")

    def enforce_success_claim_prohibition(self, claim_type: str) -> NoReturn:
        """MANDATORY enforcement - BLOCKS false success claims with ZERO TOLERANCE"""
        logger.info(f"🔒 MANDATORY ENFORCEMENT CHECK for claim: {claim_type}")

        enforcement_result = self.check_all_ci_pipelines_with_enforcement()

        if not enforcement_result.enforcement_passed:
            error_message = f"""
🚨 CRITICAL ENFORCEMENT VIOLATION - OPERATION BLOCKED

Claim Type: {claim_type}
Enforcement Status: FAILED
Action Taken: {enforcement_result.enforcement_action}

DETAILS:
{enforcement_result.summary}

FAILING PIPELINES:
""" + "\n".join([f"  - {p.name}: {p.status}/{p.conclusion}" for p in enforcement_result.failing_pipelines])

            error_message += f"""

🔒 HARD ENFORCEMENT ACTIVE: This system prevents false success reporting.
All success claims BLOCKED until ALL pipelines pass verification.

REQUIRED ACTIONS:
1. Fix all failing CI pipelines
2. Verify all pipelines show 'completed/success' status
3. Re-run enforcement verification
4. Only then proceed with success claims

NO MANUAL OVERRIDE AVAILABLE - ENFORCEMENT IS MANDATORY
"""

            # Record critical violation
            logger.error("🚨 BLOCKING FALSE SUCCESS CLAIM")

            # HARD STOP - Cannot be bypassed
            raise CriticalEnforcementError(error_message, enforcement_result)

        logger.info(f"✅ ENFORCEMENT PASSED: Success claim authorized for {claim_type}")

    def generate_enforcement_status_report(self) -> str:
        """Generate enforcement-verified status report"""
        enforcement_result = self.check_all_ci_pipelines_with_enforcement()

        report = f"""
# 🔒 HARD ENFORCEMENT STATUS REPORT

**Verification Timestamp**: {enforcement_result.timestamp}
**Enforcement Status**: {enforcement_result.summary}
**Enforcement Action**: {enforcement_result.enforcement_action}

## Pipeline Status (ENFORCEMENT VERIFIED):

"""

        for pipeline in enforcement_result.all_pipelines:
            status_emoji = "✅" if pipeline.conclusion == "success" else "🚨"
            report += f"{status_emoji} **{pipeline.name}**: {pipeline.status} / {pipeline.conclusion}\n"

        if enforcement_result.failing_pipelines:
            report += f"""
## 🚨 ENFORCEMENT VIOLATIONS:

{len(enforcement_result.failing_pipelines)} pipeline(s) in violation:

"""
            for pipeline in enforcement_result.failing_pipelines:
                report += f"- **{pipeline.name}**: {pipeline.status} / {pipeline.conclusion}\n"

            report += """
## 🔒 ENFORCEMENT ACTION:

All success claims BLOCKED until violations resolved.
No manual override available - enforcement is mandatory.
"""
        else:
            report += """
## ✅ ENFORCEMENT STATUS:

All pipelines operational - success claims authorized.
"""

        report += f"""
## 🔒 Hard Enforcement Protocol:

This report is generated by the Hard Enforcement Protocol system.
All claims are verified through mandatory enforcement checks.
False success reporting is BLOCKED at system level.

**Enforcement Authority**: ACTIVE - Cannot be bypassed
**Next Action**: {"✅ Operations authorized" if enforcement_result.enforcement_passed else "🚨 Fix violations before proceeding"}
"""

        return report


def main():
    """Main enforcement protocol execution"""
    enforcement = HardEnforcementProtocol()

    if len(sys.argv) > 1 and sys.argv[1] == "--enforce-success-claim":
        claim_type = sys.argv[2] if len(sys.argv) > 2 else "General Success Claim"
        try:
            enforcement.enforce_success_claim_prohibition(claim_type)
            print("✅ ENFORCEMENT PASSED: Success claim authorized")
            return 0
        except CriticalEnforcementError as e:
            print(f"🚨 ENFORCEMENT BLOCKED: {e}")
            return 1
    else:
        # Generate enforcement status report
        report = enforcement.generate_enforcement_status_report()
        print(report)
        return 0


if __name__ == "__main__":
    sys.exit(main())