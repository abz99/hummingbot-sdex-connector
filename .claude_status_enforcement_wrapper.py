#!/usr/bin/env python3
"""
Status Enforcement Wrapper - System-Level Blocking for False Claims
Intercepts and blocks all CI pipeline success claims that fail verification.
"""

import sys
import os
import subprocess
import logging
from typing import List, Dict, Any, NoReturn
from datetime import datetime

# Import the hard enforcement protocol
from .claude_hard_enforcement_protocol import HardEnforcementProtocol, CriticalEnforcementError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] STATUS_ENFORCEMENT: %(message)s',
    handlers=[
        logging.FileHandler('logs/status_enforcement.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StatusEnforcementWrapper:
    """System-level wrapper that enforces verification before status claims"""

    def __init__(self):
        self.enforcement_protocol = HardEnforcementProtocol()
        self.blocked_phrases = [
            "mission accomplished",
            "completed ci pipeline",
            "ci pipelines operational",
            "all pipelines passing",
            "ci fixes complete",
            "pipelines fixed",
            "ci working",
            "pipelines successful"
        ]
        self.enforcement_log = "logs/status_enforcement.log"

    def intercept_status_claim(self, status_text: str) -> str:
        """Intercept and verify status claims before allowing them"""
        logger.info("🔍 INTERCEPTING STATUS CLAIM FOR VERIFICATION")

        # Check if this is a CI pipeline success claim
        if self._contains_ci_success_claim(status_text):
            logger.warning("⚠️ CI SUCCESS CLAIM DETECTED - ENFORCING VERIFICATION")

            try:
                # MANDATORY enforcement check
                self.enforcement_protocol.enforce_success_claim_prohibition(
                    "CI Pipeline Status Claim"
                )

                # If we get here, enforcement passed
                logger.info("✅ ENFORCEMENT PASSED - Status claim authorized")
                return status_text

            except CriticalEnforcementError as e:
                # Enforcement failed - BLOCK the claim
                logger.error("🚨 ENFORCEMENT BLOCKED STATUS CLAIM")

                # Return corrected status based on actual verification
                corrected_status = self._generate_corrected_status()
                logger.info(f"📝 CORRECTED STATUS: {corrected_status}")
                return corrected_status

        return status_text

    def _contains_ci_success_claim(self, text: str) -> bool:
        """Check if text contains CI pipeline success claims"""
        text_lower = text.lower()

        # Check for blocked phrases
        for phrase in self.blocked_phrases:
            if phrase in text_lower:
                return True

        # Check for specific success indicators
        success_indicators = [
            "✅" and ("ci" in text_lower or "pipeline" in text_lower),
            "completed" and "ci" in text_lower,
            "operational" and "pipeline" in text_lower,
            "passing" and ("test" in text_lower or "ci" in text_lower)
        ]

        return any(success_indicators)

    def _generate_corrected_status(self) -> str:
        """Generate corrected status based on actual verification"""
        try:
            enforcement_result = self.enforcement_protocol.check_all_ci_pipelines_with_enforcement()

            corrected_status = f"""
🔒 ENFORCEMENT-VERIFIED CI PIPELINE STATUS

**Verification Timestamp**: {datetime.now().isoformat()}
**Status**: {enforcement_result.summary}
**Enforcement Action**: {enforcement_result.enforcement_action}

## Actual Pipeline Status:
"""

            for pipeline in enforcement_result.all_pipelines:
                status_emoji = "✅" if pipeline.conclusion == "success" else "❌"
                corrected_status += f"{status_emoji} **{pipeline.name}**: {pipeline.status} / {pipeline.conclusion}\n"

            if enforcement_result.failing_pipelines:
                corrected_status += f"""
## ⚠️ ENFORCEMENT VIOLATIONS DETECTED:

{len(enforcement_result.failing_pipelines)} pipeline(s) require attention:

"""
                for pipeline in enforcement_result.failing_pipelines:
                    corrected_status += f"- **{pipeline.name}**: {pipeline.status} / {pipeline.conclusion}\n"

                corrected_status += """
## 🔒 NEXT STEPS:

1. Fix all failing CI pipelines
2. Verify all pipelines show 'completed/success' status
3. Re-run enforcement verification
4. Then proceed with accurate status reporting

**Note**: This status was corrected by the Hard Enforcement Protocol to prevent false success reporting.
"""

            return corrected_status

        except Exception as e:
            logger.error(f"Error generating corrected status: {e}")
            return f"""
🚨 ENFORCEMENT SYSTEM ERROR

Could not verify CI pipeline status due to system error: {e}

**Action Required**: Manually verify CI pipeline status before making any success claims.

**Warning**: False success reporting has been blocked by enforcement system.
"""

    def enforce_accurate_project_status(self, project_status_content: str) -> str:
        """Enforce accurate project status in PROJECT_STATUS.md updates"""
        logger.info("🔍 ENFORCING ACCURATE PROJECT STATUS")

        # Check for CI-related success claims in project status
        if self._contains_ci_success_claim(project_status_content):
            logger.warning("⚠️ CI SUCCESS CLAIMS DETECTED IN PROJECT STATUS")

            try:
                # MANDATORY enforcement check
                self.enforcement_protocol.enforce_success_claim_prohibition(
                    "Project Status CI Claims"
                )

                # If enforcement passes, allow the content
                return project_status_content

            except CriticalEnforcementError as e:
                # Enforcement failed - inject corrected status
                logger.error("🚨 BLOCKING FALSE PROJECT STATUS CLAIMS")

                # Insert enforcement notice at the top
                enforcement_notice = f"""
# ⚠️ ENFORCEMENT NOTICE

**This project status has been corrected by the Hard Enforcement Protocol**

The original status contained CI pipeline success claims that failed verification.
See logs/status_enforcement.log for details.

{self._generate_corrected_status()}

---

# Original Project Status (Enforcement Corrected)

"""
                return enforcement_notice + project_status_content

        return project_status_content

    def block_false_completion_claims(self, message: str) -> NoReturn:
        """Block any attempt to claim task completion with failing pipelines"""
        logger.info("🔒 BLOCKING FALSE COMPLETION CLAIM")

        try:
            self.enforcement_protocol.enforce_success_claim_prohibition(
                "Task Completion Claim"
            )
        except CriticalEnforcementError as e:
            logger.error("🚨 TASK COMPLETION BLOCKED BY ENFORCEMENT")
            # Re-raise to block the completion
            raise


def enforce_status_claims():
    """Main enforcement function for status claims"""
    wrapper = StatusEnforcementWrapper()

    # Check if this is being called to verify a status claim
    if len(sys.argv) > 1:
        claim_text = " ".join(sys.argv[1:])
        corrected_text = wrapper.intercept_status_claim(claim_text)
        print(corrected_text)
    else:
        # Generate current enforcement status
        enforcement_report = wrapper.enforcement_protocol.generate_enforcement_status_report()
        print(enforcement_report)


if __name__ == "__main__":
    enforce_status_claims()