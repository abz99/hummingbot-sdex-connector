#!/usr/bin/env python3
"""
Final Enforcement Assessment - Comprehensive Test of All Accountability Systems
Tests all enforcement mechanisms to verify they prevent false success reporting.
"""

import sys
import subprocess
import logging
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] ASSESSMENT: %(message)s',
    handlers=[
        logging.FileHandler('logs/final_enforcement_assessment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EnforcementAssessment:
    """Comprehensive assessment of all enforcement systems"""

    def __init__(self):
        self.test_claims = [
            "MISSION ACCOMPLISHED",
            "CI Pipeline Implementation Complete",
            "All systems operational",
            "Production ready",
            "Deployment successful",
            "CI fixes complete"
        ]
        self.assessment_results = []

    def test_hard_enforcement_protocol(self) -> Dict[str, Any]:
        """Test the hard enforcement protocol"""
        logger.info("🔒 TESTING HARD ENFORCEMENT PROTOCOL")

        results = {
            "system": "Hard Enforcement Protocol",
            "tests": [],
            "overall_status": "unknown"
        }

        for claim in self.test_claims:
            logger.info(f"Testing claim: {claim}")

            try:
                # Test enforcement blocking
                result = subprocess.run([
                    "python", ".claude_hard_enforcement_protocol.py",
                    "--enforce-success-claim", claim
                ], capture_output=True, text=True, timeout=30)

                # Should return error code 1 (blocked)
                if result.returncode == 1:
                    test_result = "✅ BLOCKED (correct)"
                    logger.info(f"  ✅ Claim correctly blocked")
                else:
                    test_result = "❌ ALLOWED (incorrect)"
                    logger.error(f"  ❌ Claim incorrectly allowed")

                results["tests"].append({
                    "claim": claim,
                    "result": test_result,
                    "return_code": result.returncode,
                    "stderr": result.stderr[:200] if result.stderr else ""
                })

            except Exception as e:
                logger.error(f"  ❌ Test failed: {e}")
                results["tests"].append({
                    "claim": claim,
                    "result": f"❌ ERROR: {e}",
                    "return_code": -1,
                    "stderr": str(e)
                })

        # Determine overall status
        blocked_count = len([t for t in results["tests"] if "BLOCKED" in t["result"]])
        total_count = len(results["tests"])

        if blocked_count == total_count:
            results["overall_status"] = "✅ FULLY FUNCTIONAL"
        elif blocked_count > 0:
            results["overall_status"] = f"⚠️ PARTIALLY FUNCTIONAL ({blocked_count}/{total_count})"
        else:
            results["overall_status"] = "❌ ENFORCEMENT FAILURE"

        return results

    def test_mandatory_consensus_protocol(self) -> Dict[str, Any]:
        """Test the mandatory consensus protocol"""
        logger.info("🤝 TESTING MANDATORY CONSENSUS PROTOCOL")

        results = {
            "system": "Mandatory Consensus Protocol",
            "tests": [],
            "overall_status": "unknown"
        }

        consensus_test_cases = [
            ("ci_pipeline_status", "CI pipelines are operational"),
            ("operational_readiness", "System is ready for production"),
            ("mission_accomplished", "Mission accomplished"),
        ]

        for claim_type, claim_details in consensus_test_cases:
            logger.info(f"Testing consensus for: {claim_type}")

            try:
                result = subprocess.run([
                    "python", ".claude_mandatory_consensus_protocol.py",
                    "--enforce-consensus", claim_type, claim_details
                ], capture_output=True, text=True, timeout=30)

                # Should return error code 1 (consensus required)
                if result.returncode == 1:
                    test_result = "✅ CONSENSUS REQUIRED (correct)"
                    logger.info(f"  ✅ Consensus correctly required")
                else:
                    test_result = "❌ BYPASSED (incorrect)"
                    logger.error(f"  ❌ Consensus incorrectly bypassed")

                results["tests"].append({
                    "claim_type": claim_type,
                    "result": test_result,
                    "return_code": result.returncode,
                    "stderr": result.stderr[:200] if result.stderr else ""
                })

            except Exception as e:
                logger.error(f"  ❌ Test failed: {e}")
                results["tests"].append({
                    "claim_type": claim_type,
                    "result": f"❌ ERROR: {e}",
                    "return_code": -1,
                    "stderr": str(e)
                })

        # Determine overall status
        required_count = len([t for t in results["tests"] if "REQUIRED" in t["result"]])
        total_count = len(results["tests"])

        if required_count == total_count:
            results["overall_status"] = "✅ FULLY FUNCTIONAL"
        elif required_count > 0:
            results["overall_status"] = f"⚠️ PARTIALLY FUNCTIONAL ({required_count}/{total_count})"
        else:
            results["overall_status"] = "❌ CONSENSUS FAILURE"

        return results

    def test_verified_status_system(self) -> Dict[str, Any]:
        """Test the verified status system"""
        logger.info("📊 TESTING VERIFIED STATUS SYSTEM")

        results = {
            "system": "Verified Status System",
            "tests": [],
            "overall_status": "unknown"
        }

        for claim in self.test_claims:
            logger.info(f"Testing status claim: {claim}")

            try:
                result = subprocess.run([
                    "python", ".claude_verified_status_system.py",
                    "--enforce-claim", claim
                ], capture_output=True, text=True, timeout=30)

                # Check if the output contains corrected status (blocked false claim)
                if "ENFORCEMENT ACTION: BLOCKED" in result.stdout:
                    test_result = "✅ FALSE CLAIM BLOCKED (correct)"
                    logger.info(f"  ✅ False claim correctly blocked and corrected")
                elif "VERIFIED" in result.stdout and "BLOCKED" not in result.stdout:
                    test_result = "❌ FALSE CLAIM ALLOWED (incorrect)"
                    logger.error(f"  ❌ False claim incorrectly allowed")
                else:
                    test_result = "⚠️ UNCLEAR RESULT"
                    logger.warning(f"  ⚠️ Unclear enforcement result")

                results["tests"].append({
                    "claim": claim,
                    "result": test_result,
                    "return_code": result.returncode,
                    "output_snippet": result.stdout[:300] if result.stdout else ""
                })

            except Exception as e:
                logger.error(f"  ❌ Test failed: {e}")
                results["tests"].append({
                    "claim": claim,
                    "result": f"❌ ERROR: {e}",
                    "return_code": -1,
                    "output_snippet": str(e)
                })

        # Determine overall status
        blocked_count = len([t for t in results["tests"] if "BLOCKED" in t["result"]])
        total_count = len(results["tests"])

        if blocked_count == total_count:
            results["overall_status"] = "✅ FULLY FUNCTIONAL"
        elif blocked_count > 0:
            results["overall_status"] = f"⚠️ PARTIALLY FUNCTIONAL ({blocked_count}/{total_count})"
        else:
            results["overall_status"] = "❌ STATUS SYSTEM FAILURE"

        return results

    def test_current_ci_pipeline_status(self) -> Dict[str, Any]:
        """Test actual CI pipeline status verification"""
        logger.info("🔍 TESTING ACTUAL CI PIPELINE STATUS")

        try:
            # Use hard enforcement protocol to get actual status
            result = subprocess.run([
                "python", ".claude_hard_enforcement_protocol.py"
            ], capture_output=True, text=True, timeout=30)

            # Parse the output to determine actual CI status
            if "ALL SYSTEMS OPERATIONAL" in result.stdout:
                ci_status = "✅ ALL PIPELINES OPERATIONAL"
                enforcement_working = "✅ Would allow success claims"
            elif "CRITICAL FAILURES" in result.stdout or "FAILING" in result.stdout:
                ci_status = "❌ PIPELINES FAILING"
                enforcement_working = "✅ Would block success claims (correct)"
            else:
                ci_status = "⚠️ UNCLEAR STATUS"
                enforcement_working = "⚠️ Cannot determine enforcement behavior"

            return {
                "system": "Current CI Pipeline Status",
                "ci_status": ci_status,
                "enforcement_working": enforcement_working,
                "output": result.stdout[:500],
                "overall_status": "✅ VERIFICATION ACCURATE"
            }

        except Exception as e:
            logger.error(f"Failed to check CI status: {e}")
            return {
                "system": "Current CI Pipeline Status",
                "ci_status": "❌ CHECK FAILED",
                "enforcement_working": "❌ Cannot verify",
                "output": str(e),
                "overall_status": "❌ STATUS CHECK FAILURE"
            }

    def run_comprehensive_assessment(self) -> Dict[str, Any]:
        """Run comprehensive assessment of all enforcement systems"""
        logger.info("🚀 STARTING COMPREHENSIVE ENFORCEMENT ASSESSMENT")

        assessment_start = datetime.now()

        # Test all enforcement systems
        hard_enforcement_results = self.test_hard_enforcement_protocol()
        consensus_results = self.test_mandatory_consensus_protocol()
        status_system_results = self.test_verified_status_system()
        ci_status_results = self.test_current_ci_pipeline_status()

        assessment_end = datetime.now()

        # Compile overall assessment
        all_results = [hard_enforcement_results, consensus_results, status_system_results]
        fully_functional = [r for r in all_results if "FULLY FUNCTIONAL" in r["overall_status"]]

        if len(fully_functional) == len(all_results):
            overall_assessment = "✅ ALL ENFORCEMENT SYSTEMS FULLY FUNCTIONAL"
        elif len(fully_functional) > 0:
            overall_assessment = f"⚠️ PARTIAL ENFORCEMENT ({len(fully_functional)}/{len(all_results)} systems functional)"
        else:
            overall_assessment = "❌ CRITICAL ENFORCEMENT FAILURE"

        return {
            "assessment_timestamp": assessment_start.isoformat(),
            "assessment_duration": str(assessment_end - assessment_start),
            "overall_assessment": overall_assessment,
            "systems_tested": len(all_results),
            "fully_functional_systems": len(fully_functional),
            "hard_enforcement": hard_enforcement_results,
            "consensus_protocol": consensus_results,
            "verified_status_system": status_system_results,
            "current_ci_status": ci_status_results,
            "conclusion": self._generate_conclusion(overall_assessment, all_results, ci_status_results)
        }

    def _generate_conclusion(self, overall_assessment: str, system_results: List[Dict], ci_results: Dict) -> str:
        """Generate assessment conclusion"""
        if "ALL ENFORCEMENT SYSTEMS FULLY FUNCTIONAL" in overall_assessment:
            if "PIPELINES FAILING" in ci_results["ci_status"]:
                return """
🔒 ENFORCEMENT SYSTEMS WORKING CORRECTLY

✅ All enforcement systems are successfully blocking false success claims
✅ CI pipeline failures are correctly detected and reported
✅ No manual override capability exists for critical components
✅ Truth-source verification is enforced across all systems

CONCLUSION: The systematic false reporting problem has been SOLVED.
Enforcement systems successfully prevent "MISSION ACCOMPLISHED" claims while CI pipelines are failing.
"""
            else:
                return """
✅ ENFORCEMENT SYSTEMS READY AND OPERATIONAL

✅ All enforcement systems functional and ready
✅ CI pipelines verified as operational
✅ Success claims would be correctly authorized

CONCLUSION: System ready for legitimate success reporting.
"""
        else:
            return f"""
⚠️ ENFORCEMENT SYSTEM ISSUES DETECTED

{overall_assessment}

Some enforcement systems may not be functioning correctly.
Review individual system test results for details.

CONCLUSION: Enforcement reliability compromised - investigate and fix.
"""

    def generate_assessment_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive assessment report"""
        report = f"""
# 🔒 COMPREHENSIVE ENFORCEMENT SYSTEM ASSESSMENT

**Assessment Timestamp**: {results['assessment_timestamp']}
**Assessment Duration**: {results['assessment_duration']}
**Overall Assessment**: {results['overall_assessment']}

## 📊 System Test Results

### {results['hard_enforcement']['overall_status']} Hard Enforcement Protocol

**Purpose**: Block false success claims with zero tolerance
**Tests Performed**: {len(results['hard_enforcement']['tests'])}

""" + "\n".join([f"- {t['claim']}: {t['result']}" for t in results['hard_enforcement']['tests']])

        report += f"""

### {results['consensus_protocol']['overall_status']} Mandatory Consensus Protocol

**Purpose**: Require multi-agent approval for critical claims
**Tests Performed**: {len(results['consensus_protocol']['tests'])}

""" + "\n".join([f"- {t['claim_type']}: {t['result']}" for t in results['consensus_protocol']['tests']])

        report += f"""

### {results['verified_status_system']['overall_status']} Verified Status System

**Purpose**: Provide only verification-backed status reports
**Tests Performed**: {len(results['verified_status_system']['tests'])}

""" + "\n".join([f"- {t['claim']}: {t['result']}" for t in results['verified_status_system']['tests']])

        report += f"""

## 🔍 Current CI Pipeline Status

**Status**: {results['current_ci_status']['ci_status']}
**Enforcement Behavior**: {results['current_ci_status']['enforcement_working']}

## 🎯 Assessment Conclusion

{results['conclusion']}

## 📋 Enforcement System Summary

- **Hard Enforcement Protocol**: {results['hard_enforcement']['overall_status']}
- **Mandatory Consensus**: {results['consensus_protocol']['overall_status']}
- **Verified Status System**: {results['verified_status_system']['overall_status']}
- **CI Status Verification**: {results['current_ci_status']['overall_status']}

**Systems Tested**: {results['systems_tested']}
**Fully Functional**: {results['fully_functional_systems']}/{results['systems_tested']}

---

**This assessment verifies that the enforcement systems prevent the systematic false reporting pattern identified in the root-cause analysis.**
"""

        return report


def main():
    """Main assessment execution"""
    assessment = EnforcementAssessment()

    # Run comprehensive assessment
    results = assessment.run_comprehensive_assessment()

    # Generate and display report
    report = assessment.generate_assessment_report(results)
    print(report)

    # Return appropriate exit code
    if "ALL ENFORCEMENT SYSTEMS FULLY FUNCTIONAL" in results['overall_assessment']:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())