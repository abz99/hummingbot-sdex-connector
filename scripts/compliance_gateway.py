#!/usr/bin/env python3
"""
Compliance Gateway - Pre-execution Validation System
Enforces MANDATORY_COMPLIANCE_RULES.md "ALWAYS ENGAGE THE TEAM" policy
"""

import os
import sys
import json
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class ComplianceViolationError(Exception):
    """Raised when a compliance violation is detected"""
    pass


class ComplianceGateway:
    """Central compliance validation gateway"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.session_state_file = self.project_root / ".claude_compliance_state.json"
        self.violation_log = []
        self.session_state = self.load_session_state()

    def load_session_state(self) -> Dict:
        """Load compliance session state"""
        if self.session_state_file.exists():
            try:
                with open(self.session_state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, PermissionError):
                pass

        return {
            'session_start_time': datetime.now().isoformat(),
            'compliance_checklist_completed': False,
            'violations_count': 0,
            'last_validation_time': None
        }

    def save_session_state(self):
        """Save compliance session state"""
        try:
            with open(self.session_state_file, 'w') as f:
                json.dump(self.session_state, f, indent=2)
        except (PermissionError, OSError) as e:
            print(f"Warning: Could not save compliance state: {e}")

    def check_agent_system_active(self) -> bool:
        """Check if multi-agent system is active"""
        try:
            agent_manager = self.project_root / "scripts" / "agent_manager.py"
            if not agent_manager.exists():
                return False

            result = subprocess.run([
                sys.executable, str(agent_manager), "--status"
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                output = result.stdout.lower()
                return ("agent_count" in output or "active" in output or "operational" in output)
            return False
        except:
            return False

    def requires_team_engagement(self, tool_name: str, tool_params: Dict, context: str) -> bool:
        """Determine if this task requires team engagement"""
        technical_patterns = [
            r'gh\s+run\s+list', r'gh\s+workflow', r'git\s+push', r'docker\s+build',
            r'bandit', r'safety\s+check', r'security.*scan',
            r'pytest', r'test.*suite', r'coverage.*report',
            r'benchmark', r'performance.*test', r'optimization',
            r'ci.*pipeline', r'deployment.*pipeline', r'infrastructure'
        ]

        critical_tools = {'Bash', 'Edit', 'Write', 'MultiEdit', 'NotebookEdit'}
        full_context = f"{tool_name} {json.dumps(tool_params)} {context}".lower()

        for pattern in technical_patterns:
            if re.search(pattern, full_context, re.IGNORECASE):
                return True

        if tool_name in critical_tools:
            return True

        return False

    def detect_agent_engagement_in_context(self, context: str) -> List[str]:
        """Detect which agents are mentioned in the context"""
        engaged_agents = []
        agent_patterns = {
            'DevOpsEngineer': r'DevOpsEngineer|DevOps\s+Engineer',
            'SecurityEngineer': r'SecurityEngineer|Security\s+Engineer',
            'QAEngineer': r'QAEngineer|QA\s+Engineer',
            'PerformanceEngineer': r'PerformanceEngineer|Performance\s+Engineer',
            'Architect': r'Architect',
            'ProjectManager': r'ProjectManager|Project\s+Manager',
            'Implementer': r'Implementer',
            'DocumentationEngineer': r'DocumentationEngineer|Documentation\s+Engineer'
        }

        for agent, pattern in agent_patterns.items():
            if re.search(pattern, context, re.IGNORECASE):
                engaged_agents.append(agent)

        return engaged_agents

    def validate_before_execution(self, tool_name: str, tool_params: Dict, context: str = "") -> bool:
        """Main validation function called before tool execution"""
        violations = []
        warnings = []

        # 1. CRITICAL: Multi-agent system must be active
        if not self.check_agent_system_active():
            violations.append("Multi-agent system not active - run .claude_session_auto_init.py")

        # 2. CRITICAL: Team engagement validation for technical tasks
        if self.requires_team_engagement(tool_name, tool_params, context):
            engaged_agents = self.detect_agent_engagement_in_context(context)
            if not engaged_agents:
                violations.append(f"Team engagement required - must engage appropriate specialized agent before executing {tool_name}")

        # Update session state
        self.session_state['last_validation_time'] = datetime.now().isoformat()
        self.session_state['violations_count'] += len(violations)

        # Log violations
        if violations:
            violation_entry = {
                'timestamp': datetime.now().isoformat(),
                'tool_name': tool_name,
                'tool_params': tool_params,
                'context': context,
                'violations': violations,
                'warnings': warnings
            }
            self.violation_log.append(violation_entry)

        self.save_session_state()

        # Block execution if critical violations found
        if violations:
            violation_report = self.generate_violation_report(violations, warnings, tool_name, context)
            raise ComplianceViolationError(violation_report)

        return True

    def generate_violation_report(self, violations: List[str], warnings: List[str], tool_name: str, context: str) -> str:
        """Generate detailed violation report"""
        report = [
            "🚨 COMPLIANCE VIOLATION DETECTED",
            "=" * 50,
            f"Tool: {tool_name}",
            f"Context: {context}",
            f"Timestamp: {datetime.now().isoformat()}",
            "",
            "CRITICAL VIOLATIONS:"
        ]

        for i, violation in enumerate(violations, 1):
            report.append(f"{i}. {violation}")

        report.extend([
            "",
            "🔧 REMEDIATION REQUIRED:",
            "1. Follow MANDATORY_COMPLIANCE_RULES.md strictly",
            "2. Engage appropriate specialized agents BEFORE tool execution",
            "3. Ensure multi-agent system is active",
            "",
            "🚫 EXECUTION BLOCKED - Fix violations before proceeding"
        ])

        return "\n".join(report)


def validate_tool_execution(tool_name: str, tool_params: Dict, context: str = "") -> bool:
    """Global validation function for Claude Code tool execution"""
    gateway = ComplianceGateway()
    return gateway.validate_before_execution(tool_name, tool_params, context)


if __name__ == "__main__":
    gateway = ComplianceGateway()
    print("🛡️ Compliance Gateway Status")
    print(f"Agent system active: {gateway.check_agent_system_active()}")
    print(f"Session violations: {gateway.session_state.get('violations_count', 0)}")