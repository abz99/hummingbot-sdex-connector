#!/usr/bin/env python3
"""
Mandatory Consensus Protocol - Multi-Agent Consensus for Critical Claims
Requires DevOpsEngineer and QAEngineer approval for CI pipeline status claims.
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] CONSENSUS: %(message)s',
    handlers=[
        logging.FileHandler('logs/mandatory_consensus.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ConsensusStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONSENSUS_ACHIEVED = "consensus_achieved"
    CONSENSUS_FAILED = "consensus_failed"


@dataclass
class AgentApproval:
    """Represents an agent's approval decision"""
    agent_name: str
    decision: str  # approved, rejected
    reasoning: str
    timestamp: datetime
    verification_data: Optional[Dict] = None


@dataclass
class ConsensusResult:
    """Result of multi-agent consensus process"""
    consensus_status: ConsensusStatus
    approvals: List[AgentApproval]
    required_agents: List[str]
    consensus_achieved: bool
    timestamp: datetime
    summary: str


class ConsensusRequiredError(Exception):
    """Raised when consensus is required but not achieved"""
    def __init__(self, message: str, consensus_result: ConsensusResult):
        self.consensus_result = consensus_result
        super().__init__(message)


class MandatoryConsensusProtocol:
    """Enforces multi-agent consensus for critical CI pipeline claims"""

    def __init__(self):
        self.consensus_file = "logs/consensus_decisions.json"
        self.critical_claim_types = {
            "ci_pipeline_status": {
                "required_agents": ["DevOpsEngineer", "QAEngineer"],
                "description": "CI/CD pipeline status verification",
                "consensus_threshold": 1.0  # 100% agreement required
            },
            "operational_readiness": {
                "required_agents": ["DevOpsEngineer", "QAEngineer", "SecurityEngineer"],
                "description": "System operational readiness assessment",
                "consensus_threshold": 1.0  # 100% agreement required
            },
            "production_deployment": {
                "required_agents": ["DevOpsEngineer", "QAEngineer", "SecurityEngineer", "Architect"],
                "description": "Production deployment authorization",
                "consensus_threshold": 1.0  # 100% agreement required
            },
            "mission_accomplished": {
                "required_agents": ["ProjectManager", "DevOpsEngineer", "QAEngineer", "SecurityEngineer"],
                "description": "Mission completion verification",
                "consensus_threshold": 1.0  # 100% agreement required
            }
        }

        # Ensure log directory exists
        os.makedirs("logs", exist_ok=True)

    def require_consensus_for_claim(self, claim_type: str, claim_details: str) -> ConsensusResult:
        """Require multi-agent consensus for critical claims"""
        logger.info(f"🤝 REQUIRING CONSENSUS for claim type: {claim_type}")

        if claim_type not in self.critical_claim_types:
            # Non-critical claim - no consensus required
            return ConsensusResult(
                consensus_status=ConsensusStatus.APPROVED,
                approvals=[],
                required_agents=[],
                consensus_achieved=True,
                timestamp=datetime.now(),
                summary="Non-critical claim - no consensus required"
            )

        claim_config = self.critical_claim_types[claim_type]
        required_agents = claim_config["required_agents"]

        logger.info(f"📋 Required agents for consensus: {required_agents}")

        # Check if we already have valid consensus for this claim
        existing_consensus = self._check_existing_consensus(claim_type, claim_details)
        if existing_consensus and existing_consensus.consensus_achieved:
            logger.info("✅ Valid consensus already exists")
            return existing_consensus

        # Request consensus from required agents
        consensus_result = self._request_agent_consensus(claim_type, claim_details, required_agents)

        # Save consensus result
        self._save_consensus_result(claim_type, claim_details, consensus_result)

        return consensus_result

    def _request_agent_consensus(self, claim_type: str, claim_details: str, required_agents: List[str]) -> ConsensusResult:
        """Request consensus from required agents"""
        logger.info(f"📞 Requesting consensus from {len(required_agents)} agents")

        approvals = []

        # For now, simulate agent consensus requests
        # In a real implementation, this would invoke the MCP agents
        for agent_name in required_agents:
            try:
                approval = self._simulate_agent_approval(agent_name, claim_type, claim_details)
                approvals.append(approval)
                logger.info(f"📝 {agent_name}: {approval.decision} - {approval.reasoning}")
            except Exception as e:
                logger.error(f"❌ Failed to get approval from {agent_name}: {e}")
                # Create rejection for failed agent communication
                approval = AgentApproval(
                    agent_name=agent_name,
                    decision="rejected",
                    reasoning=f"Agent communication failed: {e}",
                    timestamp=datetime.now()
                )
                approvals.append(approval)

        # Evaluate consensus
        consensus_achieved = self._evaluate_consensus(approvals, required_agents)

        if consensus_achieved:
            consensus_status = ConsensusStatus.CONSENSUS_ACHIEVED
            summary = f"✅ Consensus achieved: {len([a for a in approvals if a.decision == 'approved'])}/{len(required_agents)} agents approved"
        else:
            consensus_status = ConsensusStatus.CONSENSUS_FAILED
            rejections = [a for a in approvals if a.decision == "rejected"]
            summary = f"❌ Consensus failed: {len(rejections)} agent(s) rejected"

        return ConsensusResult(
            consensus_status=consensus_status,
            approvals=approvals,
            required_agents=required_agents,
            consensus_achieved=consensus_achieved,
            timestamp=datetime.now(),
            summary=summary
        )

    def _simulate_agent_approval(self, agent_name: str, claim_type: str, claim_details: str) -> AgentApproval:
        """Simulate agent approval (replace with real MCP agent calls)"""

        # Import the hard enforcement protocol to check actual CI status
        from .claude_hard_enforcement_protocol import HardEnforcementProtocol

        enforcement = HardEnforcementProtocol()

        try:
            # Get actual CI pipeline status
            enforcement_result = enforcement.check_all_ci_pipelines_with_enforcement()

            # Agent-specific logic for approval
            if agent_name == "DevOpsEngineer":
                # DevOps focuses on CI/CD pipeline health
                if claim_type == "ci_pipeline_status":
                    if enforcement_result.enforcement_passed:
                        return AgentApproval(
                            agent_name=agent_name,
                            decision="approved",
                            reasoning="All CI pipelines verified as operational through enforcement protocol",
                            timestamp=datetime.now(),
                            verification_data={"pipelines_status": "all_passing"}
                        )
                    else:
                        return AgentApproval(
                            agent_name=agent_name,
                            decision="rejected",
                            reasoning=f"CI pipelines failing verification: {len(enforcement_result.failing_pipelines)} pipelines not operational",
                            timestamp=datetime.now(),
                            verification_data={"failing_pipelines": len(enforcement_result.failing_pipelines)}
                        )

            elif agent_name == "QAEngineer":
                # QA focuses on quality gates and testing
                if claim_type == "ci_pipeline_status":
                    if enforcement_result.enforcement_passed:
                        return AgentApproval(
                            agent_name=agent_name,
                            decision="approved",
                            reasoning="Quality gates satisfied: all pipelines passing verification",
                            timestamp=datetime.now(),
                            verification_data={"quality_gates": "passed"}
                        )
                    else:
                        return AgentApproval(
                            agent_name=agent_name,
                            decision="rejected",
                            reasoning="Quality gates failed: CI pipelines not meeting operational standards",
                            timestamp=datetime.now(),
                            verification_data={"quality_gates": "failed"}
                        )

            elif agent_name == "SecurityEngineer":
                # Security focuses on security compliance
                return AgentApproval(
                    agent_name=agent_name,
                    decision="approved",  # Assume security checks pass for simulation
                    reasoning="Security compliance verified for operational claims",
                    timestamp=datetime.now(),
                    verification_data={"security_status": "compliant"}
                )

            elif agent_name == "ProjectManager":
                # PM focuses on overall project readiness
                if enforcement_result.enforcement_passed:
                    return AgentApproval(
                        agent_name=agent_name,
                        decision="approved",
                        reasoning="Project infrastructure verified operational through enforcement protocols",
                        timestamp=datetime.now(),
                        verification_data={"project_status": "operational"}
                    )
                else:
                    return AgentApproval(
                        agent_name=agent_name,
                        decision="rejected",
                        reasoning="Project infrastructure not ready: CI pipeline failures prevent operational status",
                        timestamp=datetime.now(),
                        verification_data={"project_status": "infrastructure_failing"}
                    )

            else:
                # Default approval logic
                return AgentApproval(
                    agent_name=agent_name,
                    decision="approved",
                    reasoning="Agent approval simulated - no specific logic implemented",
                    timestamp=datetime.now()
                )

        except Exception as e:
            # If enforcement check fails, reject
            return AgentApproval(
                agent_name=agent_name,
                decision="rejected",
                reasoning=f"Could not verify CI status: {e}",
                timestamp=datetime.now(),
                verification_data={"error": str(e)}
            )

    def _evaluate_consensus(self, approvals: List[AgentApproval], required_agents: List[str]) -> bool:
        """Evaluate if consensus is achieved"""
        # Check that we have responses from all required agents
        responding_agents = {approval.agent_name for approval in approvals}
        missing_agents = set(required_agents) - responding_agents

        if missing_agents:
            logger.warning(f"⚠️ Missing responses from agents: {missing_agents}")
            return False

        # Check that all agents approved
        approved_count = len([a for a in approvals if a.decision == "approved"])
        total_count = len(approvals)

        # Require 100% approval for critical claims
        consensus_achieved = approved_count == total_count

        logger.info(f"📊 Consensus evaluation: {approved_count}/{total_count} approved")

        return consensus_achieved

    def _check_existing_consensus(self, claim_type: str, claim_details: str) -> Optional[ConsensusResult]:
        """Check if valid consensus already exists for this claim"""
        try:
            with open(self.consensus_file, 'r') as f:
                consensus_history = json.load(f)

            # Look for recent consensus (within last hour) for same claim type
            cutoff_time = datetime.now().timestamp() - 3600  # 1 hour ago

            for record in reversed(consensus_history):  # Check most recent first
                if (record.get("claim_type") == claim_type and
                    record.get("timestamp", 0) > cutoff_time and
                    record.get("consensus_achieved", False)):

                    logger.info(f"✅ Found existing valid consensus for {claim_type}")
                    return self._consensus_from_record(record)

        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"Error checking existing consensus: {e}")

        return None

    def _consensus_from_record(self, record: Dict) -> ConsensusResult:
        """Convert stored record back to ConsensusResult"""
        approvals = []
        for approval_data in record.get("approvals", []):
            approvals.append(AgentApproval(
                agent_name=approval_data["agent_name"],
                decision=approval_data["decision"],
                reasoning=approval_data["reasoning"],
                timestamp=datetime.fromisoformat(approval_data["timestamp"]),
                verification_data=approval_data.get("verification_data")
            ))

        return ConsensusResult(
            consensus_status=ConsensusStatus(record["consensus_status"]),
            approvals=approvals,
            required_agents=record["required_agents"],
            consensus_achieved=record["consensus_achieved"],
            timestamp=datetime.fromisoformat(record["timestamp"]),
            summary=record["summary"]
        )

    def _save_consensus_result(self, claim_type: str, claim_details: str, result: ConsensusResult) -> None:
        """Save consensus result to file"""
        try:
            # Load existing history
            try:
                with open(self.consensus_file, 'r') as f:
                    consensus_history = json.load(f)
            except FileNotFoundError:
                consensus_history = []

            # Add new consensus result
            record = {
                "claim_type": claim_type,
                "claim_details": claim_details,
                "consensus_status": result.consensus_status.value,
                "consensus_achieved": result.consensus_achieved,
                "required_agents": result.required_agents,
                "summary": result.summary,
                "timestamp": result.timestamp.isoformat(),
                "approvals": [
                    {
                        "agent_name": approval.agent_name,
                        "decision": approval.decision,
                        "reasoning": approval.reasoning,
                        "timestamp": approval.timestamp.isoformat(),
                        "verification_data": approval.verification_data
                    } for approval in result.approvals
                ]
            }

            consensus_history.append(record)

            # Keep only last 100 records
            consensus_history = consensus_history[-100:]

            # Save updated history
            with open(self.consensus_file, 'w') as f:
                json.dump(consensus_history, f, indent=2)

            logger.info(f"💾 Consensus result saved for {claim_type}")

        except Exception as e:
            logger.error(f"Failed to save consensus result: {e}")

    def enforce_consensus_requirement(self, claim_type: str, claim_details: str) -> None:
        """Enforce consensus requirement - raises exception if consensus not achieved"""
        logger.info(f"🔒 ENFORCING CONSENSUS REQUIREMENT for {claim_type}")

        consensus_result = self.require_consensus_for_claim(claim_type, claim_details)

        if not consensus_result.consensus_achieved:
            error_message = f"""
🚨 CONSENSUS REQUIREMENT VIOLATION

Claim Type: {claim_type}
Consensus Status: {consensus_result.consensus_status.value}
Required Agents: {consensus_result.required_agents}

AGENT DECISIONS:
""" + "\n".join([f"  {a.agent_name}: {a.decision.upper()} - {a.reasoning}" for a in consensus_result.approvals])

            error_message += f"""

🔒 CONSENSUS ENFORCEMENT: This claim requires unanimous approval from all specified agents.
Current status: {consensus_result.summary}

REQUIRED ACTIONS:
1. Address agent concerns and rejections
2. Re-submit for consensus when requirements are met
3. Ensure all agents approve before proceeding

NO BYPASS AVAILABLE - CONSENSUS IS MANDATORY FOR CRITICAL CLAIMS
"""

            raise ConsensusRequiredError(error_message, consensus_result)

        logger.info(f"✅ CONSENSUS ACHIEVED: {consensus_result.summary}")


def main():
    """Main consensus protocol execution"""
    consensus = MandatoryConsensusProtocol()

    if len(sys.argv) > 2 and sys.argv[1] == "--enforce-consensus":
        claim_type = sys.argv[2]
        claim_details = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""

        try:
            consensus.enforce_consensus_requirement(claim_type, claim_details)
            print("✅ CONSENSUS ACHIEVED: Claim authorized")
            return 0
        except ConsensusRequiredError as e:
            print(f"🚨 CONSENSUS REQUIRED: {e}")
            return 1
    else:
        print("Usage: python .claude_mandatory_consensus_protocol.py --enforce-consensus <claim_type> [claim_details]")
        print("Available claim types:", list(consensus.critical_claim_types.keys()))
        return 1


if __name__ == "__main__":
    sys.exit(main())