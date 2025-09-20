#!/usr/bin/env python3
"""
Compliance Gateway - Pre-execution validation for rule enforcement
Critical component to prevent compliance violations
"""

import json
import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


class ComplianceViolationError(Exception):
    """Exception raised when compliance violations are detected"""
    pass


class ComplianceGateway:
    """Pre-execution validation gateway for rule enforcement"""

    def __init__(self):
        self.rules_file = "MANDATORY_COMPLIANCE_RULES.md"
        self.session_state_file = ".claude_compliance_state.json"
        self.violation_log_file = "logs/compliance_violations.log"
        self.violation_log = []
        self.session_state = self.load_session_state()
        self.setup_logging()

    def setup_logging(self):
        """Setup compliance logging"""
        Path("logs").mkdir(exist_ok=True)
        logging.basicConfig(
            filename=self.violation_log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def validate_before_execution(self, tool_name: str, tool_params: dict, context: str) -> bool:
        """MANDATORY validation before ANY tool execution"""
        start_time = time.time()
        violations = []

        try:
            # Rule 1: Multi-agent system must be active
            if not self.check_agent_system_active():
                violations.append("CRITICAL: Multi-agent system not active")

            # Rule 2: Team engagement for technical tasks
            if self.requires_team_engagement(tool_name, tool_params, context):
                if not self.verify_team_engaged(context):
                    violations.append("CRITICAL: Team engagement required but not detected")

            # Rule 3: Session compliance checklist
            if not self.session_state.get('compliance_checklist_completed', False):
                violations.append("WARNING: Session compliance checklist not completed")

            # Rule 4: Git workflow compliance (if applicable)
            if tool_name in ['Bash'] and 'git commit' in str(tool_params):
                if not self.check_git_workflow_compliance():
                    violations.append("WARNING: Git workflow compliance issues")

            # Rule 5: Documentation currency check
            if not self.check_documentation_currency():
                violations.append("WARNING: PROJECT_STATUS.md may be stale")

            validation_time = (time.time() - start_time) * 1000

            if violations:
                self.log_violations(violations, tool_name, context, validation_time)
                # Only block for CRITICAL violations
                critical_violations = [v for v in violations if v.startswith("CRITICAL")]
                if critical_violations:
                    self.block_execution_with_message(violations)
                    return False
                else:
                    # Log warnings but allow execution
                    self.logger.warning(f"Non-critical violations: {violations}")

            self.log_successful_validation(tool_name, context, validation_time)
            return True

        except Exception as e:
            self.logger.error(f"Compliance validation error: {e}")
            # Fail secure - block execution on validation errors
            raise ComplianceViolationError(f"Compliance validation failed: {e}")

    def requires_team_engagement(self, tool_name: str, tool_params: dict, context: str) -> bool:
        """Determine if task requires specialized agent engagement"""
        # Technical task indicators mapped to required agents
        technical_indicators = {
            'ci': 'DevOpsEngineer',
            'pipeline': 'DevOpsEngineer',
            'workflow': 'DevOpsEngineer',
            'deployment': 'DevOpsEngineer',
            'security': 'SecurityEngineer',
            'vulnerability': 'SecurityEngineer',
            'penetration': 'SecurityEngineer',
            'test': 'QAEngineer',
            'testing': 'QAEngineer',
            'validation': 'QAEngineer',
            'performance': 'PerformanceEngineer',
            'optimization': 'PerformanceEngineer',
            'benchmark': 'PerformanceEngineer',
            'architecture': 'Architect',
            'design': 'Architect',
            'refactor': 'Architect',
            'documentation': 'DocumentationEngineer',
            'readme': 'DocumentationEngineer',
            'guide': 'DocumentationEngineer'
        }

        context_lower = context.lower()
        tool_params_str = str(tool_params).lower()

        # Check if any technical indicators are present
        for keyword in technical_indicators.keys():
            if keyword in context_lower or keyword in tool_params_str:
                return True

        # Special case: GitHub CLI operations often require DevOps
        if tool_name == 'Bash' and any(cmd in tool_params_str for cmd in ['gh ', 'git ']):
            return True

        return False

    def verify_team_engaged(self, context: str) -> bool:
        """Check if appropriate team member has been engaged"""
        # Look for evidence of agent engagement in context
        agent_indicators = [
            'mcp__stellar-agents__agent_',
            'DevOpsEngineer',
            'SecurityEngineer',
            'QAEngineer',
            'Architect',
            'PerformanceEngineer',
            'DocumentationEngineer',
            'Implementer',
            'ProjectManager'
        ]

        context_lower = context.lower()
        return any(indicator.lower() in context_lower for indicator in agent_indicators)

    def check_agent_system_active(self) -> bool:
        """Verify multi-agent system is operational"""
        try:
            result = subprocess.run(
                ['python', 'scripts/agent_manager.py', '--status'],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout

            # Check for healthy agent system
            has_correct_count = "agent_count: 8" in output
            not_stopped = "stopped" not in output.lower()

            return has_correct_count and not_stopped

        except subprocess.TimeoutExpired:
            self.logger.error("Agent system status check timed out")
            return False
        except Exception as e:
            self.logger.error(f"Agent system check failed: {e}")
            return False

    def check_git_workflow_compliance(self) -> bool:
        """Check git workflow compliance"""
        try:
            # Check uncommitted files count
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, timeout=10
            )
            uncommitted_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

            # Allow reasonable number of uncommitted files
            return uncommitted_count < 25

        except Exception:
            return True  # Don't block on git check failures

    def check_documentation_currency(self) -> bool:
        """Check if PROJECT_STATUS.md is current"""
        try:
            status_file = Path("PROJECT_STATUS.md")
            if not status_file.exists():
                return False

            # Check if modified within last 24 hours
            last_modified = datetime.fromtimestamp(status_file.stat().st_mtime)
            age_hours = (datetime.now() - last_modified).total_seconds() / 3600

            return age_hours < 24

        except Exception:
            return True  # Don't block on documentation check failures

    def load_session_state(self) -> dict:
        """Load session compliance state"""
        try:
            if Path(self.session_state_file).exists():
                with open(self.session_state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load session state: {e}")

        return {
            'compliance_checklist_completed': False,
            'session_start_time': datetime.now().isoformat(),
            'violations_count': 0
        }

    def save_session_state(self):
        """Save session compliance state"""
        try:
            with open(self.session_state_file, 'w') as f:
                json.dump(self.session_state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save session state: {e}")

    def mark_compliance_checklist_completed(self):
        """Mark session compliance checklist as completed"""
        self.session_state['compliance_checklist_completed'] = True
        self.session_state['checklist_completed_time'] = datetime.now().isoformat()
        self.save_session_state()
        self.logger.info("Session compliance checklist marked as completed")

    def log_violations(self, violations: List[str], tool_name: str, context: str, validation_time: float):
        """Log compliance violations"""
        violation_entry = {
            'timestamp': datetime.now().isoformat(),
            'tool_name': tool_name,
            'context': context[:200] + '...' if len(context) > 200 else context,
            'violations': violations,
            'validation_time_ms': validation_time
        }

        self.violation_log.append(violation_entry)
        self.session_state['violations_count'] = self.session_state.get('violations_count', 0) + 1
        self.save_session_state()

        self.logger.error(f"Compliance violations detected: {violations}")

    def log_successful_validation(self, tool_name: str, context: str, validation_time: float):
        """Log successful validation"""
        self.logger.info(f"Validation passed for {tool_name} in {validation_time:.2f}ms")

    def block_execution_with_message(self, violations: List[str]):
        """Block execution and provide clear remediation instructions"""
        message = "🚨 COMPLIANCE VIOLATION DETECTED - EXECUTION BLOCKED\n\n"
        message += "VIOLATIONS:\n"
        for violation in violations:
            message += f"  ❌ {violation}\n"

        message += "\n🔧 REMEDIATION REQUIRED:\n"

        if any("Multi-agent system not active" in v for v in violations):
            message += "1. ⚡ Start multi-agent system: python scripts/agent_manager.py --daemon\n"

        if any("Team engagement required" in v for v in violations):
            message += "2. 👥 Engage appropriate specialist agent FIRST:\n"
            message += "   - CI/Pipeline issues → DevOpsEngineer\n"
            message += "   - Security issues → SecurityEngineer\n"
            message += "   - Testing issues → QAEngineer\n"
            message += "   - Performance issues → PerformanceEngineer\n"
            message += "   - Architecture issues → Architect\n"
            message += "   - Documentation → DocumentationEngineer\n"

        if any("Session compliance checklist not completed" in v for v in violations):
            message += "3. ✅ Complete session compliance checklist\n"

        message += "\n🚨 This enforcement prevents the compliance violations that occurred earlier in this session.\n"
        message += "💡 Use mcp__stellar-agents__agent_[AGENT_NAME] to engage specialists.\n"

        raise ComplianceViolationError(message)

    def get_compliance_report(self) -> dict:
        """Generate compliance report"""
        return {
            'session_state': self.session_state,
            'violations_count': len(self.violation_log),
            'recent_violations': self.violation_log[-10:] if self.violation_log else [],
            'agent_system_active': self.check_agent_system_active(),
            'documentation_current': self.check_documentation_currency(),
            'git_compliance': self.check_git_workflow_compliance()
        }


# Global instance for easy access
compliance_gateway = ComplianceGateway()


def validate_tool_execution(tool_name: str, tool_params: dict, context: str = "") -> bool:
    """Main validation entry point"""
    return compliance_gateway.validate_before_execution(tool_name, tool_params, context)


def mark_session_compliant():
    """Mark session as compliant after checklist completion"""
    compliance_gateway.mark_compliance_checklist_completed()


def get_compliance_status() -> dict:
    """Get current compliance status"""
    return compliance_gateway.get_compliance_report()


if __name__ == "__main__":
    # Test the compliance gateway
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("🧪 Testing Compliance Gateway...")

        # Test 1: Multi-agent system check
        print(f"Agent system active: {compliance_gateway.check_agent_system_active()}")

        # Test 2: Team engagement detection
        test_context = "Need to fix CI pipeline issues with DevOpsEngineer engagement"
        requires_engagement = compliance_gateway.requires_team_engagement("Bash", {"command": "gh run list"}, test_context)
        team_engaged = compliance_gateway.verify_team_engaged(test_context)
        print(f"Requires engagement: {requires_engagement}")
        print(f"Team engaged: {team_engaged}")

        # Test 3: Generate compliance report
        report = compliance_gateway.get_compliance_report()
        print(f"Compliance report: {json.dumps(report, indent=2)}")

    elif len(sys.argv) > 1 and sys.argv[1] == "--mark-compliant":
        mark_session_compliant()
        print("✅ Session marked as compliant")

    else:
        print("Usage: python compliance_gateway.py [--test|--mark-compliant]")