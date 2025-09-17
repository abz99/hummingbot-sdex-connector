#!/usr/bin/env python3
"""
Claude Multi-Agent Oversight System
Ensures multi-agent validation for critical system status reporting and prevents single-point-of-failure decisions.
"""

import sys
import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] OVERSIGHT: %(message)s',
    handlers=[
        logging.FileHandler('logs/agent_oversight.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class AgentValidation:
    """Represents validation from a specialized agent"""
    agent_name: str
    validation_type: str
    status: str  # approved, rejected, pending
    comments: str
    timestamp: datetime
    evidence: Optional[Dict] = None


@dataclass
class OversightResult:
    """Result of multi-agent oversight process"""
    task_type: str
    validations: List[AgentValidation]
    overall_status: str  # approved, rejected, pending
    required_agents: List[str]
    missing_validations: List[str]
    summary: str
    timestamp: datetime


class AgentOversightSystem:
    """Multi-agent oversight system for critical decisions and status reporting"""

    def __init__(self):
        self.oversight_rules = {
            "ci_pipeline_status": {
                "required_agents": ["DevOpsEngineer", "QAEngineer"],
                "description": "CI/CD pipeline status validation",
                "criticality": "high"
            },
            "production_readiness": {
                "required_agents": ["DevOpsEngineer", "SecurityEngineer", "QAEngineer", "Architect"],
                "description": "Production deployment readiness assessment",
                "criticality": "critical"
            },
            "security_validation": {
                "required_agents": ["SecurityEngineer", "Architect"],
                "description": "Security compliance and threat assessment",
                "criticality": "critical"
            },
            "system_architecture": {
                "required_agents": ["Architect", "SecurityEngineer", "PerformanceEngineer"],
                "description": "System architecture changes and design decisions",
                "criticality": "high"
            },
            "status_reporting": {
                "required_agents": ["ProjectManager", "QAEngineer"],
                "description": "Critical status reporting and milestone claims",
                "criticality": "high"
            }
        }

    def initiate_oversight_process(self, task_type: str, context: Dict) -> OversightResult:
        """
        Initiate multi-agent oversight process for critical decisions.

        Args:
            task_type: Type of task requiring oversight (must be in oversight_rules)
            context: Context information for agents to evaluate

        Returns:
            OversightResult with validation status
        """
        if task_type not in self.oversight_rules:
            raise ValueError(f"Unknown task type for oversight: {task_type}")

        rule = self.oversight_rules[task_type]
        required_agents = rule["required_agents"]

        logger.info(f"🔍 Initiating multi-agent oversight for: {task_type}")
        logger.info(f"Required agents: {', '.join(required_agents)}")

        validations = []
        missing_validations = []

        # Check if multi-agent system is available
        if not self._check_multi_agent_availability():
            logger.warning("⚠️ Multi-agent system not fully available - marking as pending")
            missing_validations = required_agents
        else:
            # Request validation from each required agent
            for agent_name in required_agents:
                validation = self._request_agent_validation(agent_name, task_type, context)
                if validation:
                    validations.append(validation)
                else:
                    missing_validations.append(agent_name)

        # Determine overall status
        if missing_validations:
            overall_status = "pending"
            summary = f"⏳ Awaiting validation from {len(missing_validations)} agents: {', '.join(missing_validations)}"
        elif any(v.status == "rejected" for v in validations):
            overall_status = "rejected"
            rejected_agents = [v.agent_name for v in validations if v.status == "rejected"]
            summary = f"❌ Rejected by {len(rejected_agents)} agents: {', '.join(rejected_agents)}"
        elif all(v.status == "approved" for v in validations):
            overall_status = "approved"
            summary = f"✅ Approved by all {len(validations)} required agents"
        else:
            overall_status = "pending"
            pending_agents = [v.agent_name for v in validations if v.status == "pending"]
            summary = f"⏳ Pending validation from {len(pending_agents)} agents: {', '.join(pending_agents)}"

        result = OversightResult(
            task_type=task_type,
            validations=validations,
            overall_status=overall_status,
            required_agents=required_agents,
            missing_validations=missing_validations,
            summary=summary,
            timestamp=datetime.now()
        )

        self._log_oversight_result(result)
        return result

    def _check_multi_agent_availability(self) -> bool:
        """Check if multi-agent system is available"""
        try:
            # Try to check agent status via scripts
            result = subprocess.run([
                "python", "scripts/agent_manager.py", "--status"
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                # Check if agents are operational (could be via MCP even if local status shows stopped)
                return "agent_count: 8" in result.stdout or "Agents: 8" in result.stdout
            return False
        except Exception as e:
            logger.warning(f"Could not check multi-agent availability: {e}")
            return False

    def _request_agent_validation(self, agent_name: str, task_type: str, context: Dict) -> Optional[AgentValidation]:
        """
        Request validation from a specific agent.

        Args:
            agent_name: Name of the agent to request validation from
            task_type: Type of task being validated
            context: Context for validation

        Returns:
            AgentValidation if successful, None if agent unavailable
        """
        try:
            # For now, simulate agent validation based on context and rules
            # In a full implementation, this would use the MCP interface to actually call agents

            # Simulate basic validation logic
            if task_type == "ci_pipeline_status":
                if agent_name == "DevOpsEngineer":
                    # Check if CI status is in context
                    ci_status = context.get("ci_status", {})
                    all_passing = context.get("all_pipelines_passing", False)

                    if all_passing:
                        status = "approved"
                        comments = "All CI pipelines verified as operational"
                    else:
                        status = "rejected"
                        comments = "CI pipelines have failures - cannot approve operational status"

                elif agent_name == "QAEngineer":
                    test_results = context.get("test_results", {})
                    all_tests_passing = context.get("all_tests_passing", False)

                    if all_tests_passing:
                        status = "approved"
                        comments = "All test suites passing - quality gates satisfied"
                    else:
                        status = "rejected"
                        comments = "Test failures detected - quality gates not satisfied"
                else:
                    status = "pending"
                    comments = f"Agent {agent_name} validation not implemented"

            elif task_type == "status_reporting":
                if agent_name == "ProjectManager":
                    # Check if status claims are backed by evidence
                    evidence_provided = context.get("evidence_provided", False)
                    verification_passed = context.get("verification_passed", False)

                    if evidence_provided and verification_passed:
                        status = "approved"
                        comments = "Status claim backed by comprehensive verification"
                    else:
                        status = "rejected"
                        comments = "Insufficient evidence for status claim - verification required"

                elif agent_name == "QAEngineer":
                    comprehensive_testing = context.get("comprehensive_testing", False)

                    if comprehensive_testing:
                        status = "approved"
                        comments = "Comprehensive testing validation confirms status"
                    else:
                        status = "rejected"
                        comments = "Insufficient testing validation for status claim"
                else:
                    status = "pending"
                    comments = f"Agent {agent_name} validation logic not implemented"
            else:
                status = "pending"
                comments = f"Validation logic for {task_type} not implemented"

            return AgentValidation(
                agent_name=agent_name,
                validation_type=task_type,
                status=status,
                comments=comments,
                timestamp=datetime.now(),
                evidence=context
            )

        except Exception as e:
            logger.error(f"Failed to get validation from {agent_name}: {e}")
            return None

    def _log_oversight_result(self, result: OversightResult) -> None:
        """Log oversight result for audit trail"""
        logger.info("=" * 80)
        logger.info(f"🔍 MULTI-AGENT OVERSIGHT RESULT: {result.task_type}")
        logger.info("=" * 80)
        logger.info(f"Overall Status: {result.summary}")
        logger.info(f"Required Agents: {', '.join(result.required_agents)}")

        if result.validations:
            logger.info("")
            logger.info("Agent Validations:")
            for validation in result.validations:
                status_emoji = "✅" if validation.status == "approved" else "❌" if validation.status == "rejected" else "⏳"
                logger.info(f"  {status_emoji} {validation.agent_name}: {validation.status}")
                logger.info(f"     Comments: {validation.comments}")

        if result.missing_validations:
            logger.warning("")
            logger.warning("Missing Validations:")
            for agent in result.missing_validations:
                logger.warning(f"  ⚠️ {agent}: No validation received")

        logger.info("=" * 80)

    def enforce_oversight_requirement(self, task_type: str, context: Dict) -> bool:
        """
        Enforce multi-agent oversight requirement for critical tasks.

        Args:
            task_type: Type of task requiring oversight
            context: Context information

        Returns:
            True if oversight passed, False if failed or pending

        Raises:
            Exception: If oversight is required but not satisfied
        """
        if task_type not in self.oversight_rules:
            logger.warning(f"No oversight rules defined for task type: {task_type}")
            return True

        rule = self.oversight_rules[task_type]

        if rule["criticality"] in ["critical", "high"]:
            logger.info(f"🚨 Enforcing multi-agent oversight for {task_type} (criticality: {rule['criticality']})")

            result = self.initiate_oversight_process(task_type, context)

            if result.overall_status == "approved":
                logger.info(f"✅ Multi-agent oversight APPROVED for {task_type}")
                return True
            elif result.overall_status == "rejected":
                error_msg = f"""
🚨 MULTI-AGENT OVERSIGHT REJECTION

Task Type: {task_type}
Status: REJECTED
Summary: {result.summary}

Rejecting Agents:
""" + "\n".join([f"  - {v.agent_name}: {v.comments}" for v in result.validations if v.status == "rejected"])

                raise Exception(error_msg)
            else:  # pending
                error_msg = f"""
🚨 MULTI-AGENT OVERSIGHT INCOMPLETE

Task Type: {task_type}
Status: PENDING
Summary: {result.summary}

Required Actions:
  - Obtain validation from missing agents: {', '.join(result.missing_validations)}
  - Ensure multi-agent system is operational
  - Re-run oversight process after addressing issues
"""
                raise Exception(error_msg)
        else:
            logger.info(f"ℹ️ Task {task_type} does not require enforced oversight (criticality: {rule['criticality']})")
            return True


def main():
    """Main oversight system execution"""
    oversight = AgentOversightSystem()

    if len(sys.argv) > 1:
        task_type = sys.argv[1]
        context = {}

        # Parse context from command line arguments
        if len(sys.argv) > 2:
            try:
                context = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                logger.error("Invalid JSON context provided")
                return 1

        try:
            oversight.enforce_oversight_requirement(task_type, context)
            print(f"✅ Multi-agent oversight satisfied for {task_type}")
            return 0
        except Exception as e:
            print(f"❌ Multi-agent oversight failed: {e}")
            return 1
    else:
        print("Usage: python .claude_agent_oversight.py <task_type> [context_json]")
        print("Available task types:", list(oversight.oversight_rules.keys()))
        return 1


if __name__ == "__main__":
    sys.exit(main())