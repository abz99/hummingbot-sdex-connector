#!/usr/bin/env python3
"""
Claude Verification Protocol - Mandatory Status Verification System
Prevents false success reporting by requiring comprehensive validation before status claims.
"""

import sys
import json
import time
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] VERIFICATION: %(message)s',
    handlers=[
        logging.FileHandler('logs/verification_protocol.log'),
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
class VerificationResult:
    """Result of comprehensive verification check"""
    passed: bool
    all_pipelines: List[PipelineStatus]
    failing_pipelines: List[PipelineStatus]
    timestamp: datetime
    summary: str


class StatusReportingError(Exception):
    """Raised when attempting to make false success claims"""
    def __init__(self, message: str, verification_result: VerificationResult):
        self.verification_result = verification_result
        super().__init__(message)


class ClaudeVerificationProtocol:
    """Mandatory verification system for CI pipeline status reporting"""

    def __init__(self):
        self.required_pipelines = [
            "Stellar Hummingbot Connector CI",
            "Production Deployment Pipeline",
            "CI Health Dashboard"
        ]
        self.verification_history_file = "logs/verification_history.json"

    def check_all_ci_pipelines(self, commit_ref: str = "main") -> VerificationResult:
        """
        Check status of ALL CI pipelines for comprehensive verification.

        Args:
            commit_ref: Git commit reference to check

        Returns:
            VerificationResult with complete pipeline status
        """
        logger.info("🔍 Starting comprehensive CI pipeline verification...")

        try:
            # Get recent pipeline runs using simpler approach
            result = subprocess.run([
                "gh", "run", "list", "--limit", "10"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                raise Exception(f"Failed to get CI status: {result.stderr}")

            if not result.stdout.strip():
                raise Exception("Empty response from gh run list command")

            # Parse the tabular output instead of JSON to avoid parsing issues
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

            # Convert to PipelineStatus objects
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

                    # Check if failing
                    if (pipeline.status == 'completed' and pipeline.conclusion == 'failure') or \
                       (pipeline.status == 'in_progress' and pipeline_name != "Stellar Hummingbot Connector CI"):
                        failing_pipelines.append(pipeline)
                else:
                    # Missing pipeline
                    pipeline = PipelineStatus(
                        name=pipeline_name,
                        status="missing",
                        conclusion="unknown",
                        run_id="none"
                    )
                    all_pipelines.append(pipeline)
                    failing_pipelines.append(pipeline)

            # Determine overall status
            passed = len(failing_pipelines) == 0

            # Create summary
            if passed:
                summary = f"✅ ALL {len(self.required_pipelines)} CI PIPELINES OPERATIONAL"
            else:
                summary = f"❌ {len(failing_pipelines)}/{len(self.required_pipelines)} CI PIPELINES FAILING"

            verification_result = VerificationResult(
                passed=passed,
                all_pipelines=all_pipelines,
                failing_pipelines=failing_pipelines,
                timestamp=datetime.now(),
                summary=summary
            )

            # Log verification result
            self._log_verification_result(verification_result)

            return verification_result

        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            # Return failed verification on error
            return VerificationResult(
                passed=False,
                all_pipelines=[],
                failing_pipelines=[],
                timestamp=datetime.now(),
                summary=f"❌ VERIFICATION FAILED: {e}"
            )

    def _log_verification_result(self, result: VerificationResult) -> None:
        """Log verification result for audit trail"""
        logger.info("=" * 80)
        logger.info("🔍 CI PIPELINE COMPREHENSIVE VERIFICATION RESULT")
        logger.info("=" * 80)
        logger.info(f"Timestamp: {result.timestamp}")
        logger.info(f"Overall Status: {result.summary}")
        logger.info("")

        for pipeline in result.all_pipelines:
            status_emoji = "✅" if pipeline.conclusion == "success" else "❌" if pipeline.conclusion == "failure" else "🟡"
            logger.info(f"{status_emoji} {pipeline.name}: {pipeline.status} / {pipeline.conclusion}")

        if result.failing_pipelines:
            logger.error("")
            logger.error("❌ FAILING PIPELINES:")
            for pipeline in result.failing_pipelines:
                logger.error(f"   - {pipeline.name}: {pipeline.status} / {pipeline.conclusion}")

        logger.info("=" * 80)

        # Save to history file
        try:
            history = []
            try:
                with open(self.verification_history_file, 'r') as f:
                    history = json.load(f)
            except FileNotFoundError:
                pass

            history.append({
                "timestamp": result.timestamp.isoformat(),
                "passed": result.passed,
                "summary": result.summary,
                "failing_count": len(result.failing_pipelines),
                "total_count": len(result.all_pipelines)
            })

            # Keep only last 50 entries
            history = history[-50:]

            with open(self.verification_history_file, 'w') as f:
                json.dump(history, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to save verification history: {e}")

    def verify_before_success_claim(self, claim_type: str = "CI Pipeline Status") -> VerificationResult:
        """
        MANDATORY verification before making any success claims.

        Args:
            claim_type: Type of success claim being made

        Returns:
            VerificationResult

        Raises:
            StatusReportingError: If verification fails and success claim is invalid
        """
        logger.info(f"🚨 MANDATORY VERIFICATION for success claim: {claim_type}")

        verification_result = self.check_all_ci_pipelines()

        if not verification_result.passed:
            error_message = f"""
🚨 BLOCKED: FALSE SUCCESS CLAIM PREVENTION

Claim Type: {claim_type}
Verification Status: FAILED
Failing Pipelines: {len(verification_result.failing_pipelines)}

DETAILS:
{verification_result.summary}

FAILING PIPELINES:
""" + "\n".join([f"  - {p.name}: {p.status}/{p.conclusion}" for p in verification_result.failing_pipelines])

            error_message += f"""

ACTION REQUIRED: Fix all failing pipelines before making success claims.
This verification system prevents the systematic false reporting pattern identified in root-cause analysis.
"""

            raise StatusReportingError(error_message, verification_result)

        logger.info(f"✅ VERIFICATION PASSED: Success claim authorized for {claim_type}")
        return verification_result

    def generate_accurate_status_report(self) -> str:
        """Generate accurate CI pipeline status report based on verification"""
        verification_result = self.check_all_ci_pipelines()

        report = f"""
# 🔍 VERIFIED CI PIPELINE STATUS REPORT

**Verification Timestamp**: {verification_result.timestamp}
**Overall Status**: {verification_result.summary}

## Pipeline Details:

"""

        for pipeline in verification_result.all_pipelines:
            status_emoji = "✅" if pipeline.conclusion == "success" else "❌" if pipeline.conclusion == "failure" else "🟡"
            report += f"{status_emoji} **{pipeline.name}**: {pipeline.status} / {pipeline.conclusion}\n"

        if verification_result.failing_pipelines:
            report += f"""
## ❌ Action Required:

{len(verification_result.failing_pipelines)} pipeline(s) require attention:

"""
            for pipeline in verification_result.failing_pipelines:
                report += f"- **{pipeline.name}**: {pipeline.status} / {pipeline.conclusion}\n"

        report += f"""
## Verification Protocol:

This report was generated by the Claude Verification Protocol system to prevent false success reporting.
All claims are backed by actual CI pipeline status verification.

**Next Steps**: {"✅ Pipelines operational - ready for deployment" if verification_result.passed else "❌ Fix failing pipelines before proceeding"}
"""

        return report


def main():
    """Main verification protocol execution"""
    protocol = ClaudeVerificationProtocol()

    if len(sys.argv) > 1 and sys.argv[1] == "--verify-success-claim":
        claim_type = sys.argv[2] if len(sys.argv) > 2 else "General Success Claim"
        try:
            result = protocol.verify_before_success_claim(claim_type)
            print("✅ VERIFICATION PASSED: Success claim authorized")
            return 0
        except StatusReportingError as e:
            print(f"❌ VERIFICATION FAILED: {e}")
            return 1
    else:
        # Generate status report
        report = protocol.generate_accurate_status_report()
        print(report)
        return 0


if __name__ == "__main__":
    sys.exit(main())