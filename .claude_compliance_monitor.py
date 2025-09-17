#!/usr/bin/env python3
"""
Claude Compliance Monitor - Real-time Rule Enforcement
Monitors and enforces all project rules across agent interactions
"""

import os
import sys
import json
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] COMPLIANCE: %(message)s',
    handlers=[
        logging.FileHandler('logs/compliance_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ComplianceViolation:
    """Represents a compliance rule violation"""
    rule_id: str
    severity: str  # CRITICAL, MAJOR, MINOR
    description: str
    timestamp: datetime
    auto_fixable: bool = False
    fix_command: str = None


class ComplianceViolationError(Exception):
    """Raised when critical compliance violations are detected"""
    def __init__(self, violations: List[ComplianceViolation]):
        self.violations = violations
        super().__init__(f"Critical compliance violations detected: {len(violations)}")


class ClaudeComplianceMonitor:
    """Real-time compliance monitoring and enforcement system"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.state_file = self.project_root / ".claude_session_state.json"
        self.compliance_log = self.project_root / "logs" / "compliance_violations.json"
        self.violations: List[ComplianceViolation] = []

        # Ensure logs directory exists
        (self.project_root / "logs").mkdir(exist_ok=True)

        # Load compliance history
        self.load_compliance_history()

    def load_compliance_history(self):
        """Load previous compliance violations for trend analysis"""
        if self.compliance_log.exists():
            try:
                with open(self.compliance_log, 'r') as f:
                    history = json.load(f)
                    logger.info(f"Loaded {len(history.get('violations', []))} historical violations")
            except Exception as e:
                logger.warning(f"Could not load compliance history: {e}")

    def validate_session_startup_compliance(self) -> List[ComplianceViolation]:
        """Validate compliance rules that must be checked at session start"""
        violations = []

        # Rule SC-001: Execute startup protocol within 60 seconds
        if not self.check_startup_protocol_executed():
            violations.append(ComplianceViolation(
                rule_id="SC-001",
                severity="CRITICAL",
                description="Startup protocol not executed within 60 seconds",
                timestamp=datetime.now(),
                auto_fixable=True,
                fix_command="python .claude_code_startup.py"
            ))

        # Rule SC-002: Multi-agent system must be active
        if not self.check_multi_agent_system_active():
            violations.append(ComplianceViolation(
                rule_id="SC-002",
                severity="CRITICAL",
                description="Multi-agent system not active",
                timestamp=datetime.now(),
                auto_fixable=True,
                fix_command="python .claude_code_startup.py"
            ))

        # Rule SC-003: Git workflow compliance
        git_violations = self.check_git_workflow_compliance()
        violations.extend(git_violations)

        return violations

    def validate_development_rules_compliance(self) -> List[ComplianceViolation]:
        """Validate development rules that must never be violated"""
        violations = []

        # Rule DR-001: NEVER SKIP FAILING TESTS (ABSOLUTE PROHIBITION)
        if self.has_failing_tests():
            violations.append(ComplianceViolation(
                rule_id="DR-001",
                severity="CRITICAL",
                description="ABSOLUTE PROHIBITION VIOLATED: Failing tests detected",
                timestamp=datetime.now(),
                auto_fixable=False,
                fix_command="Fix failing tests before continuing"
            ))

        # Rule DR-003: NEVER commit code with failing tests
        if self.has_committed_failing_tests():
            violations.append(ComplianceViolation(
                rule_id="DR-003",
                severity="CRITICAL",
                description="Code committed with failing tests",
                timestamp=datetime.now(),
                auto_fixable=False,
                fix_command="Revert commit and fix tests"
            ))

        # Rule DR-004: Code quality compliance
        quality_violations = self.check_code_quality_compliance()
        violations.extend(quality_violations)

        return violations

    def validate_documentation_compliance(self) -> List[ComplianceViolation]:
        """Validate documentation maintenance rules"""
        violations = []

        # Rule DM-001: NEVER ALLOW OUTDATED PROJECT DOCUMENTATION
        if self.is_documentation_stale():
            violations.append(ComplianceViolation(
                rule_id="DM-001",
                severity="CRITICAL",
                description="PROJECT_STATUS.md is stale (>24 hours old)",
                timestamp=datetime.now(),
                auto_fixable=True,
                fix_command="Update PROJECT_STATUS.md with current status"
            ))

        # Rule DM-003: Update LAST_SESSION.md before session end
        if self.is_session_documentation_stale():
            violations.append(ComplianceViolation(
                rule_id="DM-003",
                severity="MAJOR",
                description="Session documentation not updated",
                timestamp=datetime.now(),
                auto_fixable=False,
                fix_command="Update session documentation before ending"
            ))

        return violations

    def validate_quality_assurance_compliance(self) -> List[ComplianceViolation]:
        """Validate QA rules and coverage requirements"""
        violations = []

        # Rule QA-001: Minimum 85% overall test coverage
        coverage = self.get_test_coverage()
        if coverage < 85.0:
            violations.append(ComplianceViolation(
                rule_id="QA-001",
                severity="MAJOR",
                description=f"Test coverage {coverage}% below required 85%",
                timestamp=datetime.now(),
                auto_fixable=False,
                fix_command="Add tests to improve coverage"
            ))

        return violations

    def check_startup_protocol_executed(self) -> bool:
        """Check if startup protocol was executed"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    return state.get('compliance_checklist', {}).get('startup_executed', False)
            return False
        except Exception:
            return False

    def check_multi_agent_system_active(self) -> bool:
        """Check if multi-agent system is active"""
        try:
            result = subprocess.run([
                sys.executable, "scripts/agent_manager.py", "--status"
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return "agent_count: 8" in result.stdout
            return False
        except Exception:
            return False

    def check_git_workflow_compliance(self) -> List[ComplianceViolation]:
        """Check git workflow compliance"""
        violations = []

        try:
            # Check for uncommitted files
            result = subprocess.run([
                "git", "status", "--porcelain"
            ], capture_output=True, text=True)

            uncommitted_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

            if uncommitted_count > 25:
                violations.append(ComplianceViolation(
                    rule_id="SC-003",
                    severity="MAJOR",
                    description=f"Too many uncommitted files: {uncommitted_count}",
                    timestamp=datetime.now(),
                    auto_fixable=False,
                    fix_command="Review and commit changes"
                ))

            # Check if ahead of remote
            result = subprocess.run([
                "git", "status"
            ], capture_output=True, text=True)

            if "ahead" in result.stdout and uncommitted_count == 0:
                violations.append(ComplianceViolation(
                    rule_id="DR-008",
                    severity="MAJOR",
                    description="Local commits not synced to remote",
                    timestamp=datetime.now(),
                    auto_fixable=True,
                    fix_command="git push origin main"
                ))

        except Exception as e:
            violations.append(ComplianceViolation(
                rule_id="GIT-ERROR",
                severity="MAJOR",
                description=f"Git workflow check failed: {e}",
                timestamp=datetime.now(),
                auto_fixable=False
            ))

        return violations

    def has_failing_tests(self) -> bool:
        """Check if there are failing tests"""
        try:
            result = subprocess.run([
                "python", "-m", "pytest", "--collect-only", "-q"
            ], capture_output=True, text=True, timeout=30)

            # If collection fails, there might be syntax errors
            if result.returncode != 0:
                return True

            # Check for actual test failures
            result = subprocess.run([
                "python", "-m", "pytest", "--maxfail=1", "-q"
            ], capture_output=True, text=True, timeout=60)

            return result.returncode != 0

        except Exception:
            # If we can't run tests, assume they're failing
            return True

    def has_committed_failing_tests(self) -> bool:
        """Check if recent commits included failing tests"""
        # This is complex to implement - would need to check out previous commits
        # For now, return False but log that this check needs implementation
        logger.warning("has_committed_failing_tests check not fully implemented")
        return False

    def check_code_quality_compliance(self) -> List[ComplianceViolation]:
        """Check code quality compliance (flake8, mypy, black)"""
        violations = []

        # Check flake8 compliance
        try:
            result = subprocess.run([
                "flake8", "hummingbot/connector/exchange/stellar/"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                violations.append(ComplianceViolation(
                    rule_id="DR-004-FLAKE8",
                    severity="MAJOR",
                    description="flake8 violations detected",
                    timestamp=datetime.now(),
                    auto_fixable=False,
                    fix_command="Fix flake8 violations"
                ))
        except Exception:
            pass

        # Check mypy compliance
        try:
            result = subprocess.run([
                "mypy", "hummingbot/connector/exchange/stellar/", "--show-error-codes"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                violations.append(ComplianceViolation(
                    rule_id="DR-004-MYPY",
                    severity="MAJOR",
                    description="mypy violations detected",
                    timestamp=datetime.now(),
                    auto_fixable=False,
                    fix_command="Fix mypy violations"
                ))
        except Exception:
            pass

        return violations

    def is_documentation_stale(self) -> bool:
        """Check if PROJECT_STATUS.md is stale (>24 hours)"""
        try:
            project_status = self.project_root / "PROJECT_STATUS.md"
            if not project_status.exists():
                return True

            file_time = datetime.fromtimestamp(project_status.stat().st_mtime)
            age = datetime.now() - file_time
            return age > timedelta(hours=24)
        except Exception:
            return True

    def is_session_documentation_stale(self) -> bool:
        """Check if session documentation needs updates"""
        try:
            last_session = self.project_root / "LAST_SESSION.md"
            if not last_session.exists():
                return True

            file_time = datetime.fromtimestamp(last_session.stat().st_mtime)
            age = datetime.now() - file_time
            return age > timedelta(hours=6)
        except Exception:
            return True

    def get_test_coverage(self) -> float:
        """Get current test coverage percentage"""
        try:
            result = subprocess.run([
                "python", "-m", "pytest", "--cov=hummingbot/connector/exchange/stellar/",
                "--cov-report=term-missing", "--cov-fail-under=0"
            ], capture_output=True, text=True, timeout=60)

            # Parse coverage from output
            for line in result.stdout.split('\n'):
                if 'TOTAL' in line and '%' in line:
                    # Extract percentage
                    parts = line.split()
                    for part in parts:
                        if '%' in part:
                            return float(part.replace('%', ''))
            return 0.0
        except Exception:
            return 0.0

    def auto_fix_violations(self, violations: List[ComplianceViolation]) -> List[ComplianceViolation]:
        """Automatically fix violations that can be auto-fixed"""
        unfixed_violations = []

        for violation in violations:
            if violation.auto_fixable and violation.fix_command:
                try:
                    logger.info(f"Auto-fixing violation {violation.rule_id}: {violation.fix_command}")

                    if violation.fix_command.startswith("python"):
                        subprocess.run(violation.fix_command.split(), timeout=60)
                    elif violation.fix_command.startswith("git"):
                        subprocess.run(violation.fix_command.split(), timeout=30)
                    else:
                        logger.warning(f"Don't know how to auto-fix: {violation.fix_command}")
                        unfixed_violations.append(violation)

                except Exception as e:
                    logger.error(f"Failed to auto-fix violation {violation.rule_id}: {e}")
                    unfixed_violations.append(violation)
            else:
                unfixed_violations.append(violation)

        return unfixed_violations

    def save_compliance_state(self, violations: List[ComplianceViolation]):
        """Save compliance state for monitoring and trends"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "severity": v.severity,
                    "description": v.description,
                    "timestamp": v.timestamp.isoformat(),
                    "auto_fixable": v.auto_fixable
                }
                for v in violations
            ],
            "compliance_score": self.calculate_compliance_score(violations)
        }

        with open(self.compliance_log, 'w') as f:
            json.dump(state, f, indent=2)

    def calculate_compliance_score(self, violations: List[ComplianceViolation]) -> float:
        """Calculate overall compliance score (0-100)"""
        if not violations:
            return 100.0

        penalty = 0
        for violation in violations:
            if violation.severity == "CRITICAL":
                penalty += 25
            elif violation.severity == "MAJOR":
                penalty += 10
            elif violation.severity == "MINOR":
                penalty += 5

        return max(0.0, 100.0 - penalty)

    def run_full_compliance_check(self) -> Tuple[List[ComplianceViolation], float]:
        """Run complete compliance validation"""
        logger.info("🔍 Running full compliance check...")

        all_violations = []

        # Check all rule categories
        all_violations.extend(self.validate_session_startup_compliance())
        all_violations.extend(self.validate_development_rules_compliance())
        all_violations.extend(self.validate_documentation_compliance())
        all_violations.extend(self.validate_quality_assurance_compliance())

        # Auto-fix what we can
        unfixed_violations = self.auto_fix_violations(all_violations)

        # Calculate compliance score
        compliance_score = self.calculate_compliance_score(unfixed_violations)

        # Save state
        self.save_compliance_state(unfixed_violations)

        # Log results
        if unfixed_violations:
            logger.warning(f"❌ {len(unfixed_violations)} compliance violations found")
            for violation in unfixed_violations:
                logger.warning(f"  {violation.severity}: {violation.rule_id} - {violation.description}")
        else:
            logger.info("✅ All compliance checks passed")

        logger.info(f"📊 Compliance Score: {compliance_score:.1f}/100")

        return unfixed_violations, compliance_score


def main():
    """Main compliance monitoring entry point"""
    monitor = ClaudeComplianceMonitor()

    try:
        violations, score = monitor.run_full_compliance_check()

        # Handle critical violations
        critical_violations = [v for v in violations if v.severity == "CRITICAL"]
        if critical_violations:
            logger.error("🚨 CRITICAL COMPLIANCE VIOLATIONS DETECTED - SESSION MUST BE HALTED")
            for violation in critical_violations:
                logger.error(f"  CRITICAL: {violation.rule_id} - {violation.description}")
            raise ComplianceViolationError(critical_violations)

        # Warn about major violations
        major_violations = [v for v in violations if v.severity == "MAJOR"]
        if major_violations:
            logger.warning("⚠️  MAJOR COMPLIANCE VIOLATIONS - IMMEDIATE ACTION REQUIRED")
            for violation in major_violations:
                logger.warning(f"  MAJOR: {violation.rule_id} - {violation.description}")

        print(f"\n✅ Compliance Check Complete - Score: {score:.1f}/100")
        return 0 if score >= 90.0 else 1

    except ComplianceViolationError as e:
        logger.error(f"💥 COMPLIANCE ENFORCEMENT: {e}")
        return 2
    except Exception as e:
        logger.error(f"❌ Compliance monitor error: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())