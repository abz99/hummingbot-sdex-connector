#!/usr/bin/env python3
"""
Team Engagement Enforcer - Bulletproof Compliance Gateway
Implements MANDATORY_COMPLIANCE_RULES.md "ALWAYS ENGAGE THE TEAM" policy

This system creates an unbypassable enforcement layer that validates
team engagement before ANY tool execution.
"""

import os
import sys
import json
import time
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TeamEngagementViolation:
    """Represents a team engagement policy violation"""
    tool_name: str
    context: str
    violation_type: str
    severity: str
    timestamp: str
    required_agent: str


class TeamEngagementEnforcer:
    """
    Bulletproof enforcement system for ALWAYS ENGAGE THE TEAM policy

    This system:
    1. Validates team engagement before EVERY tool execution
    2. Blocks non-compliant workflows automatically
    3. Tracks engagement history for compliance auditing
    4. Provides real-time violation detection and prevention
    """

    # Technical task patterns requiring specific agent engagement
    AGENT_REQUIREMENTS = {
        'DevOpsEngineer': [
            r'gh\s+run\s+list',
            r'gh\s+workflow',
            r'git\s+push',
            r'docker\s+build',
            r'kubectl',
            r'ci.*pipeline',
            r'deployment.*pipeline',
            r'infrastructure',
            r'monitoring.*setup',
            r'performance.*optimization'
        ],
        'SecurityEngineer': [
            r'bandit',
            r'safety\s+check',
            r'security.*scan',
            r'vulnerability',
            r'penetration.*test',
            r'hsm.*integration',
            r'key.*management',
            r'encryption',
            r'authentication'
        ],
        'QAEngineer': [
            r'pytest',
            r'test.*suite',
            r'coverage.*report',
            r'quality.*assurance',
            r'validation.*framework',
            r'test.*automation',
            r'integration.*test'
        ],
        'PerformanceEngineer': [
            r'benchmark',
            r'performance.*test',
            r'load.*test',
            r'optimization',
            r'profiling',
            r'throughput.*analysis',
            r'latency.*measurement'
        ],
        'Architect': [
            r'architecture.*design',
            r'system.*design',
            r'refactor.*architecture',
            r'design.*pattern',
            r'architectural.*review',
            r'technical.*specification'
        ]
    }

    # Critical tools that ALWAYS require team engagement
    CRITICAL_TOOLS = {
        'Bash', 'Edit', 'Write', 'MultiEdit', 'NotebookEdit'
    }

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.state_file = self.project_root / ".team_engagement_state.json"
        self.violation_log = self.project_root / "logs" / "team_engagement_violations.log"
        self.engagement_history = self.load_engagement_history()

        # Ensure logs directory exists
        self.violation_log.parent.mkdir(exist_ok=True)

    def load_engagement_history(self) -> Dict:
        """Load team engagement history from state file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, PermissionError):
                pass

        return {
            'last_engagement_time': None,
            'engaged_agents': [],
            'session_start': datetime.now().isoformat(),
            'engagement_count': 0
        }

    def save_engagement_history(self):
        """Save engagement history to state file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.engagement_history, f, indent=2)
        except (PermissionError, OSError) as e:
            print(f"Warning: Could not save engagement history: {e}")

    def check_recent_agent_engagement(self, required_agent: str, time_window_minutes: int = 10) -> bool:
        """Check if required agent was engaged recently"""
        if not self.engagement_history.get('last_engagement_time'):
            return False

        last_engagement = datetime.fromisoformat(self.engagement_history['last_engagement_time'])
        time_threshold = datetime.now() - timedelta(minutes=time_window_minutes)

        # Check if engagement was recent AND included required agent
        was_recent = last_engagement > time_threshold
        agent_was_engaged = required_agent in self.engagement_history.get('engaged_agents', [])

        return was_recent and agent_was_engaged

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

    def determine_required_agent(self, tool_name: str, tool_params: Dict, context: str) -> Optional[str]:
        """Determine which agent is required for this task"""
        # Check tool parameters and context for technical task indicators
        full_context = f"{tool_name} {json.dumps(tool_params)} {context}".lower()

        for agent, patterns in self.AGENT_REQUIREMENTS.items():
            for pattern in patterns:
                if re.search(pattern, full_context, re.IGNORECASE):
                    return agent

        # For critical tools, require at least one agent engagement
        if tool_name in self.CRITICAL_TOOLS:
            return "any_specialized_agent"

        return None

    def validate_team_engagement(self, tool_name: str, tool_params: Dict, context: str) -> Tuple[bool, Optional[TeamEngagementViolation]]:
        """
        Validate team engagement requirement for tool execution

        Returns:
            (is_compliant, violation_details)
        """
        required_agent = self.determine_required_agent(tool_name, tool_params, context)

        if not required_agent:
            # Non-technical task, no team engagement required
            return True, None

        # Check for agent engagement in context
        engaged_agents = self.detect_agent_engagement_in_context(context)

        # Check recent engagement history
        if required_agent == "any_specialized_agent":
            # Any specialized agent engagement acceptable
            has_engagement = (len(engaged_agents) > 0 or
                            len(self.engagement_history.get('engaged_agents', [])) > 0)
        else:
            # Specific agent required
            has_engagement = (required_agent in engaged_agents or
                            self.check_recent_agent_engagement(required_agent))

        if has_engagement:
            # Update engagement history
            self.engagement_history['last_engagement_time'] = datetime.now().isoformat()
            self.engagement_history['engaged_agents'] = engaged_agents
            self.engagement_history['engagement_count'] += 1
            self.save_engagement_history()
            return True, None

        # VIOLATION DETECTED
        violation = TeamEngagementViolation(
            tool_name=tool_name,
            context=context,
            violation_type="missing_team_engagement",
            severity="CRITICAL",
            timestamp=datetime.now().isoformat(),
            required_agent=required_agent
        )

        return False, violation

    def log_violation(self, violation: TeamEngagementViolation):
        """Log team engagement violation"""
        violation_entry = {
            'timestamp': violation.timestamp,
            'tool_name': violation.tool_name,
            'context': violation.context,
            'violation_type': violation.violation_type,
            'severity': violation.severity,
            'required_agent': violation.required_agent
        }

        # Append to violation log file
        try:
            with open(self.violation_log, 'a') as f:
                f.write(f"{json.dumps(violation_entry)}\n")
        except (PermissionError, OSError) as e:
            print(f"Warning: Could not log violation: {e}")

    def generate_violation_report(self, violation: TeamEngagementViolation) -> str:
        """Generate detailed violation report"""
        report = [
            "🚨 TEAM ENGAGEMENT VIOLATION DETECTED",
            "=" * 50,
            f"Tool: {violation.tool_name}",
            f"Required Agent: {violation.required_agent}",
            f"Context: {violation.context}",
            f"Severity: {violation.severity}",
            f"Timestamp: {violation.timestamp}",
            "",
            "🔧 REMEDIATION REQUIRED:",
            f"1. Engage {violation.required_agent} using Task tool BEFORE executing {violation.tool_name}",
            "2. Include agent engagement explicitly in task context",
            "3. Follow MANDATORY_COMPLIANCE_RULES.md 'ALWAYS ENGAGE THE TEAM' policy",
            "",
            "🚫 EXECUTION BLOCKED - Fix violation before proceeding"
        ]

        return "\n".join(report)

    def enforce_team_engagement(self, tool_name: str, tool_params: Dict, context: str) -> bool:
        """
        Main enforcement function - validates and blocks non-compliant tool usage

        Returns:
            True if execution allowed, False if blocked
        """
        is_compliant, violation = self.validate_team_engagement(tool_name, tool_params, context)

        if is_compliant:
            print(f"✅ Team engagement validation passed for {tool_name}")
            return True

        # BLOCK EXECUTION
        self.log_violation(violation)
        print(self.generate_violation_report(violation))
        return False


def validate_tool_execution(tool_name: str, tool_params: Dict, context: str = "") -> bool:
    """
    Global validation function for tool execution

    This function should be called before EVERY tool execution to enforce
    the ALWAYS ENGAGE THE TEAM policy.
    """
    enforcer = TeamEngagementEnforcer()
    return enforcer.enforce_team_engagement(tool_name, tool_params, context)


def install_enforcement_hooks():
    """Install enforcement hooks in the project"""
    project_root = Path(".")

    # Create git pre-commit hook for team engagement validation
    hooks_dir = project_root / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    pre_commit_hook = hooks_dir / "pre-commit"
    hook_content = """#!/bin/bash
# Team Engagement Enforcement Hook
echo "🔍 Validating team engagement compliance..."

# Check for recent team engagement
python scripts/team_engagement_enforcer.py --validate-recent-engagement

if [ $? -ne 0 ]; then
    echo "❌ Team engagement violation detected - commit blocked"
    echo "📋 Required: Engage appropriate specialized agents before making changes"
    exit 1
fi

echo "✅ Team engagement validation passed"
"""

    with open(pre_commit_hook, 'w') as f:
        f.write(hook_content)

    os.chmod(pre_commit_hook, 0o755)
    print("✅ Team engagement enforcement hook installed")


def main():
    """CLI interface for team engagement enforcer"""
    import argparse

    parser = argparse.ArgumentParser(description="Team Engagement Enforcement System")
    parser.add_argument('--validate-recent-engagement', action='store_true',
                       help='Validate recent team engagement for git hooks')
    parser.add_argument('--install-hooks', action='store_true',
                       help='Install enforcement hooks')
    parser.add_argument('--check-compliance', action='store_true',
                       help='Check current compliance status')

    args = parser.parse_args()

    enforcer = TeamEngagementEnforcer()

    if args.install_hooks:
        install_enforcement_hooks()
        return

    if args.validate_recent_engagement:
        # Check if there was recent team engagement
        if enforcer.engagement_history.get('engagement_count', 0) == 0:
            print("❌ No team engagement detected in this session")
            sys.exit(1)
        else:
            print("✅ Team engagement validated")
            sys.exit(0)

    if args.check_compliance:
        print("🔍 Team Engagement Compliance Status")
        print(f"Session start: {enforcer.engagement_history.get('session_start', 'Unknown')}")
        print(f"Engagement count: {enforcer.engagement_history.get('engagement_count', 0)}")
        print(f"Last engagement: {enforcer.engagement_history.get('last_engagement_time', 'None')}")
        print(f"Engaged agents: {enforcer.engagement_history.get('engaged_agents', [])}")
        return

    # Default: interactive validation
    print("🛡️ Team Engagement Enforcer")
    print("This system ensures compliance with MANDATORY_COMPLIANCE_RULES.md")
    print("Use --help for available options")


if __name__ == "__main__":
    main()