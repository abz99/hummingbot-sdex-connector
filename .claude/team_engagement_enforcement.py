#!/usr/bin/env python3
"""
Team Engagement Enforcement System
Mandatory compliance hard rule: ALWAYS ENGAGE THE TEAM

ENFORCEMENT LEVEL: ABSOLUTE OVERRIDE
VERSION: 1.0
AUTHORITY: PROJECT MANDATORY COMPLIANCE RULES
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TeamEngagementEnforcement')

class ViolationSeverity(Enum):
    ABSOLUTE_OVERRIDE = "ABSOLUTE_OVERRIDE"
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"

class TaskCategory(Enum):
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    QA = "qa"
    IMPLEMENTATION = "implementation"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    DEVOPS = "devops"

@dataclass
class EngagementRule:
    """Defines mandatory team engagement requirements for task categories"""
    task_category: TaskCategory
    required_agents: List[str]
    phase_gate: str
    enforcement_level: ViolationSeverity
    description: str
    timeout_minutes: int = 60

@dataclass
class TaskEngagement:
    """Tracks agent engagement for a specific task"""
    task_id: str
    task_description: str
    category: TaskCategory
    engaged_agents: Set[str]
    start_time: datetime
    required_agents: Set[str]
    status: str
    violations: List[str]

class TeamEngagementEnforcer:
    """
    Enforces mandatory team engagement compliance

    CRITICAL RULE: Every task must engage appropriate specialized agents FIRST
    No exceptions allowed for any reason
    """

    def __init__(self, config_path: str = ".claude/team_workflow.yaml"):
        self.config_path = config_path
        self.engagement_rules = self._load_engagement_rules()
        self.active_tasks: Dict[str, TaskEngagement] = {}
        self.session_state_file = ".claude/team_engagement_state.json"
        self.load_session_state()

    def _load_engagement_rules(self) -> Dict[TaskCategory, EngagementRule]:
        """Load engagement rules based on task categories"""
        rules = {
            TaskCategory.REQUIREMENTS: EngagementRule(
                task_category=TaskCategory.REQUIREMENTS,
                required_agents=["ProjectManager"],
                phase_gate="requirements_intake",
                enforcement_level=ViolationSeverity.ABSOLUTE_OVERRIDE,
                description="Task intake, scoping, and prioritization",
                timeout_minutes=30
            ),
            TaskCategory.ARCHITECTURE: EngagementRule(
                task_category=TaskCategory.ARCHITECTURE,
                required_agents=["Architect"],
                phase_gate="architecture_review",
                enforcement_level=ViolationSeverity.ABSOLUTE_OVERRIDE,
                description="Technical design and architecture approval",
                timeout_minutes=60
            ),
            TaskCategory.SECURITY: EngagementRule(
                task_category=TaskCategory.SECURITY,
                required_agents=["SecurityEngineer"],
                phase_gate="security_review",
                enforcement_level=ViolationSeverity.ABSOLUTE_OVERRIDE,
                description="Security threat modeling and validation",
                timeout_minutes=120
            ),
            TaskCategory.COMPLIANCE: EngagementRule(
                task_category=TaskCategory.COMPLIANCE,
                required_agents=["ComplianceOfficer"],
                phase_gate="compliance_review",
                enforcement_level=ViolationSeverity.ABSOLUTE_OVERRIDE,
                description="Regulatory compliance and governance validation",
                timeout_minutes=60
            ),
            TaskCategory.QA: EngagementRule(
                task_category=TaskCategory.QA,
                required_agents=["QAEngineer"],
                phase_gate="qa_criteria",
                enforcement_level=ViolationSeverity.ABSOLUTE_OVERRIDE,
                description="Quality acceptance criteria and test strategy",
                timeout_minutes=60
            ),
            TaskCategory.IMPLEMENTATION: EngagementRule(
                task_category=TaskCategory.IMPLEMENTATION,
                required_agents=["Implementer"],
                phase_gate="implementation",
                enforcement_level=ViolationSeverity.ABSOLUTE_OVERRIDE,
                description="Code implementation with quality compliance",
                timeout_minutes=480
            ),
            TaskCategory.DOCUMENTATION: EngagementRule(
                task_category=TaskCategory.DOCUMENTATION,
                required_agents=["DocumentationEngineer"],
                phase_gate="documentation",
                enforcement_level=ViolationSeverity.CRITICAL,
                description="Technical writing and documentation",
                timeout_minutes=120
            ),
            TaskCategory.PERFORMANCE: EngagementRule(
                task_category=TaskCategory.PERFORMANCE,
                required_agents=["PerformanceEngineer"],
                phase_gate="performance_validation",
                enforcement_level=ViolationSeverity.CRITICAL,
                description="Performance optimization and benchmarking",
                timeout_minutes=90
            ),
            TaskCategory.DEVOPS: EngagementRule(
                task_category=TaskCategory.DEVOPS,
                required_agents=["DevOpsEngineer"],
                phase_gate="devops_validation",
                enforcement_level=ViolationSeverity.CRITICAL,
                description="Infrastructure and deployment",
                timeout_minutes=180
            )
        }
        return rules

    def validate_task_start(self, task_description: str, category: TaskCategory) -> Dict[str, Any]:
        """
        CRITICAL: Validates that appropriate agents are engaged before task start

        Returns:
            Dict with validation result and required actions
        """
        task_id = f"task_{int(time.time())}"

        if category not in self.engagement_rules:
            return {
                "valid": False,
                "error": f"Unknown task category: {category}",
                "severity": ViolationSeverity.CRITICAL,
                "required_action": "HALT_EXECUTION"
            }

        rule = self.engagement_rules[category]

        # Create task engagement tracking
        engagement = TaskEngagement(
            task_id=task_id,
            task_description=task_description,
            category=category,
            engaged_agents=set(),
            start_time=datetime.now(),
            required_agents=set(rule.required_agents),
            status="VALIDATION_PENDING",
            violations=[]
        )

        self.active_tasks[task_id] = engagement

        # Check for pre-task agent engagement
        missing_agents = self._check_required_agents(engagement)

        if missing_agents:
            violation = f"TEAM_ENGAGEMENT_VIOLATION: Task '{task_description}' started without engaging required agents: {missing_agents}"
            engagement.violations.append(violation)
            engagement.status = "VIOLATION_DETECTED"

            logger.critical(violation)

            return {
                "valid": False,
                "task_id": task_id,
                "error": violation,
                "severity": rule.enforcement_level,
                "required_action": "ENGAGE_AGENTS_IMMEDIATELY",
                "missing_agents": missing_agents,
                "phase_gate": rule.phase_gate
            }

        engagement.status = "VALIDATED"
        logger.info(f"Task validation passed: {task_description}")

        return {
            "valid": True,
            "task_id": task_id,
            "message": f"Task validation successful for: {task_description}",
            "engaged_agents": list(engagement.engaged_agents),
            "phase_gate": rule.phase_gate
        }

    def register_agent_engagement(self, task_id: str, agent_name: str) -> bool:
        """Register that an agent has been engaged for a task"""
        if task_id not in self.active_tasks:
            logger.error(f"Task not found: {task_id}")
            return False

        engagement = self.active_tasks[task_id]
        engagement.engaged_agents.add(agent_name)

        logger.info(f"Agent {agent_name} engaged for task {task_id}")

        # Revalidate task after agent engagement
        missing_agents = self._check_required_agents(engagement)
        if not missing_agents and engagement.status == "VIOLATION_DETECTED":
            engagement.status = "VALIDATED"
            logger.info(f"Task {task_id} compliance restored")

        self.save_session_state()
        return True

    def _check_required_agents(self, engagement: TaskEngagement) -> List[str]:
        """Check which required agents are missing for a task"""
        return list(engagement.required_agents - engagement.engaged_agents)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of task engagement"""
        if task_id not in self.active_tasks:
            return None

        engagement = self.active_tasks[task_id]
        rule = self.engagement_rules[engagement.category]

        return {
            "task_id": task_id,
            "description": engagement.task_description,
            "category": engagement.category.value,
            "status": engagement.status,
            "engaged_agents": list(engagement.engaged_agents),
            "required_agents": list(engagement.required_agents),
            "missing_agents": self._check_required_agents(engagement),
            "violations": engagement.violations,
            "phase_gate": rule.phase_gate,
            "enforcement_level": rule.enforcement_level.value
        }

    def complete_task(self, task_id: str) -> bool:
        """Mark task as complete and perform final validation"""
        if task_id not in self.active_tasks:
            logger.error(f"Task not found: {task_id}")
            return False

        engagement = self.active_tasks[task_id]
        missing_agents = self._check_required_agents(engagement)

        if missing_agents:
            violation = f"COMPLETION_VIOLATION: Task {task_id} completed without required agent engagement: {missing_agents}"
            engagement.violations.append(violation)
            engagement.status = "COMPLETION_VIOLATION"
            logger.critical(violation)
            return False

        engagement.status = "COMPLETED"
        logger.info(f"Task {task_id} completed successfully with proper agent engagement")

        self.save_session_state()
        return True

    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        total_tasks = len(self.active_tasks)
        if total_tasks == 0:
            return {
                "compliance_score": 100.0,
                "total_tasks": 0,
                "compliant_tasks": 0,
                "violation_count": 0,
                "status": "NO_ACTIVE_TASKS"
            }

        violation_tasks = [
            task for task in self.active_tasks.values()
            if task.violations or task.status in ["VIOLATION_DETECTED", "COMPLETION_VIOLATION"]
        ]

        compliant_tasks = total_tasks - len(violation_tasks)
        compliance_score = (compliant_tasks / total_tasks) * 100

        return {
            "compliance_score": compliance_score,
            "total_tasks": total_tasks,
            "compliant_tasks": compliant_tasks,
            "violation_count": len(violation_tasks),
            "status": "COMPLIANT" if compliance_score == 100.0 else "NON_COMPLIANT",
            "violations": [
                {
                    "task_id": task.task_id,
                    "description": task.task_description,
                    "violations": task.violations,
                    "status": task.status
                }
                for task in violation_tasks
            ]
        }

    def save_session_state(self):
        """Save current enforcement state to persist across sessions"""
        state = {
            "active_tasks": {
                task_id: {
                    "task_id": task.task_id,
                    "task_description": task.task_description,
                    "category": task.category.value,
                    "engaged_agents": list(task.engaged_agents),
                    "start_time": task.start_time.isoformat(),
                    "required_agents": list(task.required_agents),
                    "status": task.status,
                    "violations": task.violations
                }
                for task_id, task in self.active_tasks.items()
            },
            "last_updated": datetime.now().isoformat()
        }

        os.makedirs(os.path.dirname(self.session_state_file), exist_ok=True)
        with open(self.session_state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def load_session_state(self):
        """Load enforcement state from previous session"""
        if not os.path.exists(self.session_state_file):
            return

        try:
            with open(self.session_state_file, 'r') as f:
                state = json.load(f)

            for task_id, task_data in state.get("active_tasks", {}).items():
                engagement = TaskEngagement(
                    task_id=task_data["task_id"],
                    task_description=task_data["task_description"],
                    category=TaskCategory(task_data["category"]),
                    engaged_agents=set(task_data["engaged_agents"]),
                    start_time=datetime.fromisoformat(task_data["start_time"]),
                    required_agents=set(task_data["required_agents"]),
                    status=task_data["status"],
                    violations=task_data["violations"]
                )
                self.active_tasks[task_id] = engagement

            logger.info(f"Loaded session state with {len(self.active_tasks)} active tasks")

        except Exception as e:
            logger.error(f"Failed to load session state: {e}")

def validate_task_engagement(task_description: str, category: str) -> Dict[str, Any]:
    """
    PUBLIC API: Validate task before execution

    CRITICAL: This must be called before starting any task
    """
    enforcer = TeamEngagementEnforcer()

    try:
        task_category = TaskCategory(category.lower())
    except ValueError:
        return {
            "valid": False,
            "error": f"Invalid task category: {category}",
            "severity": "CRITICAL",
            "required_action": "FIX_CATEGORY"
        }

    return enforcer.validate_task_start(task_description, task_category)

def engage_agent_for_task(task_id: str, agent_name: str) -> bool:
    """
    PUBLIC API: Register agent engagement for task
    """
    enforcer = TeamEngagementEnforcer()
    return enforcer.register_agent_engagement(task_id, agent_name)

def get_compliance_status() -> Dict[str, Any]:
    """
    PUBLIC API: Get current compliance status
    """
    enforcer = TeamEngagementEnforcer()
    return enforcer.get_compliance_report()

if __name__ == "__main__":
    # CLI interface for team engagement enforcement
    import argparse

    parser = argparse.ArgumentParser(description="Team Engagement Enforcement System")
    parser.add_argument("--validate", help="Validate task before execution", nargs=2, metavar=('DESCRIPTION', 'CATEGORY'))
    parser.add_argument("--engage", help="Register agent engagement", nargs=2, metavar=('TASK_ID', 'AGENT'))
    parser.add_argument("--status", help="Get compliance status", action="store_true")
    parser.add_argument("--report", help="Generate detailed compliance report", action="store_true")

    args = parser.parse_args()

    if args.validate:
        result = validate_task_engagement(args.validate[0], args.validate[1])
        print(json.dumps(result, indent=2))

    elif args.engage:
        result = engage_agent_for_task(args.engage[0], args.engage[1])
        print(f"Agent engagement registered: {result}")

    elif args.status:
        result = get_compliance_status()
        print(json.dumps(result, indent=2))

    elif args.report:
        enforcer = TeamEngagementEnforcer()
        print("\n=== TEAM ENGAGEMENT COMPLIANCE REPORT ===")
        for task_id, task in enforcer.active_tasks.items():
            status = enforcer.get_task_status(task_id)
            print(f"\nTask: {status['description']}")
            print(f"Status: {status['status']}")
            print(f"Engaged Agents: {status['engaged_agents']}")
            print(f"Missing Agents: {status['missing_agents']}")
            if status['violations']:
                print(f"Violations: {status['violations']}")

    else:
        parser.print_help()