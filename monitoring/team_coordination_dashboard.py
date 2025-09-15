#!/usr/bin/env python3
"""
Team Coordination Dashboard
Real-time workflow monitoring and coordination for the 8-agent development team.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from enum import Enum

from agent_activity_monitor import AgentActivityMonitor, AgentActivity
from agent_performance_dashboard import AgentPerformanceDashboard

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkflowPhase(Enum):
    """Development workflow phases."""
    PLANNING = "planning"
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    SECURITY_REVIEW = "security_review"
    IMPLEMENTATION = "implementation"
    QA_REVIEW = "qa_review"
    INTEGRATION = "integration"
    VALIDATION = "validation"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"

class CoordinationStatus(Enum):
    """Team coordination status levels."""
    OPTIMAL = "optimal"        # All agents coordinated, no conflicts
    GOOD = "good"             # Minor coordination issues
    ATTENTION = "attention"   # Coordination issues need attention
    CRITICAL = "critical"     # Major coordination problems

@dataclass
class WorkflowPhaseStatus:
    """Status of a specific workflow phase."""
    phase: WorkflowPhase
    active_agents: List[str]
    pending_agents: List[str]
    completed_agents: List[str]
    blocked_agents: List[str]
    phase_progress: float  # 0-100%
    estimated_completion: Optional[datetime]
    bottlenecks: List[str]
    dependencies: List[str]
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['phase'] = self.phase.value
        if self.estimated_completion:
            data['estimated_completion'] = self.estimated_completion.isoformat()
        return data

@dataclass
class AgentWorkload:
    """Current workload and capacity for an agent."""
    agent_name: str
    role: str
    current_tasks: List[str]
    task_count: int
    estimated_capacity: int  # Max tasks this agent can handle
    utilization_percentage: float
    next_available: Optional[datetime]
    skill_areas: List[str]
    current_phase: Optional[str]
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.next_available:
            data['next_available'] = self.next_available.isoformat()
        return data

@dataclass
class TeamCoordinationState:
    """Overall team coordination state."""
    timestamp: datetime
    coordination_status: CoordinationStatus
    active_phases: List[WorkflowPhaseStatus]
    agent_workloads: List[AgentWorkload]
    workflow_bottlenecks: List[str]
    coordination_issues: List[Dict]
    resource_conflicts: List[Dict]
    communication_gaps: List[Dict]
    recommended_actions: List[str]
    team_velocity: float  # Tasks per hour
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['coordination_status'] = self.coordination_status.value
        data['active_phases'] = [phase.to_dict() for phase in self.active_phases]
        data['agent_workloads'] = [workload.to_dict() for workload in self.agent_workloads]
        return data

class TeamCoordinationDashboard:
    """Advanced team coordination and workflow monitoring system."""
    
    def __init__(self, monitor: AgentActivityMonitor, performance_dashboard: AgentPerformanceDashboard):
        self.monitor = monitor
        self.performance_dashboard = performance_dashboard
        self.data_dir = monitor.data_dir
        self.coordination_history_file = self.data_dir / "coordination_history.jsonl"
        
        # Workflow phase dependencies
        self.phase_dependencies = {
            WorkflowPhase.REQUIREMENTS: [],
            WorkflowPhase.ARCHITECTURE: [WorkflowPhase.REQUIREMENTS],
            WorkflowPhase.SECURITY_REVIEW: [WorkflowPhase.ARCHITECTURE],
            WorkflowPhase.IMPLEMENTATION: [WorkflowPhase.ARCHITECTURE, WorkflowPhase.SECURITY_REVIEW],
            WorkflowPhase.QA_REVIEW: [WorkflowPhase.IMPLEMENTATION],
            WorkflowPhase.INTEGRATION: [WorkflowPhase.IMPLEMENTATION, WorkflowPhase.QA_REVIEW],
            WorkflowPhase.VALIDATION: [WorkflowPhase.INTEGRATION],
            WorkflowPhase.DEPLOYMENT: [WorkflowPhase.VALIDATION],
            WorkflowPhase.MONITORING: [WorkflowPhase.DEPLOYMENT]
        }
        
        # Agent role capabilities
        self.agent_capabilities = {
            "ProjectManager": {
                "phases": [WorkflowPhase.PLANNING, WorkflowPhase.REQUIREMENTS, WorkflowPhase.MONITORING],
                "capacity": 8,
                "skills": ["coordination", "planning", "requirements", "project_management"]
            },
            "Architect": {
                "phases": [WorkflowPhase.ARCHITECTURE, WorkflowPhase.PLANNING],
                "capacity": 6,
                "skills": ["system_design", "architecture", "technical_review", "patterns"]
            },
            "SecurityEngineer": {
                "phases": [WorkflowPhase.SECURITY_REVIEW, WorkflowPhase.ARCHITECTURE],
                "capacity": 5,
                "skills": ["security", "cryptography", "vulnerability_assessment", "compliance"]
            },
            "QAEngineer": {
                "phases": [WorkflowPhase.QA_REVIEW, WorkflowPhase.VALIDATION],
                "capacity": 7,
                "skills": ["testing", "quality_assurance", "automation", "validation"]
            },
            "Implementer": {
                "phases": [WorkflowPhase.IMPLEMENTATION, WorkflowPhase.INTEGRATION],
                "capacity": 10,
                "skills": ["coding", "implementation", "integration", "debugging"]
            },
            "DevOpsEngineer": {
                "phases": [WorkflowPhase.DEPLOYMENT, WorkflowPhase.MONITORING, WorkflowPhase.INTEGRATION],
                "capacity": 6,
                "skills": ["deployment", "infrastructure", "monitoring", "automation"]
            },
            "PerformanceEngineer": {
                "phases": [WorkflowPhase.IMPLEMENTATION, WorkflowPhase.VALIDATION],
                "capacity": 5,
                "skills": ["performance", "optimization", "benchmarking", "profiling"]
            },
            "DocumentationEngineer": {
                "phases": [WorkflowPhase.REQUIREMENTS, WorkflowPhase.VALIDATION],
                "capacity": 4,
                "skills": ["documentation", "technical_writing", "knowledge_management", "training"]
            }
        }
    
    def analyze_current_coordination(self) -> TeamCoordinationState:
        """Analyze current team coordination state."""
        
        now = datetime.now()
        
        # Analyze workflow phases
        active_phases = self._analyze_workflow_phases()
        
        # Analyze agent workloads  
        agent_workloads = self._analyze_agent_workloads()
        
        # Detect coordination issues
        coordination_issues = self._detect_coordination_issues(active_phases, agent_workloads)
        
        # Detect resource conflicts
        resource_conflicts = self._detect_resource_conflicts(agent_workloads)
        
        # Detect communication gaps
        communication_gaps = self._detect_communication_gaps()
        
        # Identify bottlenecks
        workflow_bottlenecks = self._identify_workflow_bottlenecks(active_phases)
        
        # Calculate coordination status
        coordination_status = self._calculate_coordination_status(
            coordination_issues, resource_conflicts, communication_gaps
        )
        
        # Generate recommendations
        recommended_actions = self._generate_coordination_recommendations(
            coordination_issues, resource_conflicts, communication_gaps, workflow_bottlenecks
        )
        
        # Calculate team velocity
        team_velocity = self._calculate_team_velocity()
        
        return TeamCoordinationState(
            timestamp=now,
            coordination_status=coordination_status,
            active_phases=active_phases,
            agent_workloads=agent_workloads,
            workflow_bottlenecks=workflow_bottlenecks,
            coordination_issues=coordination_issues,
            resource_conflicts=resource_conflicts,
            communication_gaps=communication_gaps,
            recommended_actions=recommended_actions,
            team_velocity=team_velocity
        )
    
    def _analyze_workflow_phases(self) -> List[WorkflowPhaseStatus]:
        """Analyze current status of all workflow phases."""
        
        active_phases = []
        
        # Get recent activities to determine current phases
        recent_cutoff = datetime.now() - timedelta(hours=8)
        recent_activities = [
            activity for activity in self.monitor.activity_log
            if activity.timestamp > recent_cutoff and activity.workflow_phase
        ]
        
        # Group activities by phase
        phase_activities = {}
        for activity in recent_activities:
            phase = activity.workflow_phase
            if phase not in phase_activities:
                phase_activities[phase] = []
            phase_activities[phase].append(activity)
        
        # Analyze each active phase
        for phase_name, activities in phase_activities.items():
            try:
                phase_enum = WorkflowPhase(phase_name)
            except ValueError:
                # Handle custom phase names
                continue
            
            # Categorize agents by status in this phase
            agents_in_phase = set(a.agent_name for a in activities)
            active_agents = []
            completed_agents = []
            blocked_agents = []
            
            for agent_name in agents_in_phase:
                agent_activities = [a for a in activities if a.agent_name == agent_name]
                latest_activity = max(agent_activities, key=lambda a: a.timestamp)
                
                if latest_activity.activity_type == "task_complete":
                    completed_agents.append(agent_name)
                elif latest_activity.activity_type in ["task_start", "output"]:
                    active_agents.append(agent_name)
                else:
                    # Could be blocked if no recent progress
                    if (datetime.now() - latest_activity.timestamp) > timedelta(hours=4):
                        blocked_agents.append(agent_name)
                    else:
                        active_agents.append(agent_name)
            
            # Estimate phase progress
            total_expected_agents = len(self._get_capable_agents_for_phase(phase_enum))
            if total_expected_agents > 0:
                progress = (len(completed_agents) / total_expected_agents) * 100
            else:
                progress = 50.0  # Default for unknown phases
            
            # Identify bottlenecks
            bottlenecks = []
            if len(blocked_agents) > 0:
                bottlenecks.append(f"Blocked agents: {', '.join(blocked_agents)}")
            if len(active_agents) == 0 and len(completed_agents) == 0:
                bottlenecks.append("No active agents in phase")
            
            # Get dependencies
            dependencies = [dep.value for dep in self.phase_dependencies.get(phase_enum, [])]
            
            # Estimate completion (simplified)
            if len(active_agents) > 0:
                avg_task_time = 2.0  # hours
                remaining_work = (100 - progress) / 100 * total_expected_agents * avg_task_time
                estimated_completion = datetime.now() + timedelta(hours=remaining_work / len(active_agents))
            else:
                estimated_completion = None
            
            phase_status = WorkflowPhaseStatus(
                phase=phase_enum,
                active_agents=active_agents,
                pending_agents=[],  # Would need more logic to determine
                completed_agents=completed_agents,
                blocked_agents=blocked_agents,
                phase_progress=round(progress, 1),
                estimated_completion=estimated_completion,
                bottlenecks=bottlenecks,
                dependencies=dependencies
            )
            
            active_phases.append(phase_status)
        
        return active_phases
    
    def _analyze_agent_workloads(self) -> List[AgentWorkload]:
        """Analyze current workload for each agent."""
        
        workloads = []
        
        for agent_name, agent_info in self.monitor.agents.items():
            role = agent_info["role"]
            capabilities = self.agent_capabilities.get(agent_name, {
                "capacity": 5,
                "skills": ["general"],
                "phases": []
            })
            
            # Get current tasks (recent activities)
            recent_cutoff = datetime.now() - timedelta(hours=24)
            recent_activities = [
                activity for activity in self.monitor.activity_log
                if activity.agent_name == agent_name and activity.timestamp > recent_cutoff
            ]
            
            # Extract current tasks
            current_tasks = []
            current_phase = None
            for activity in recent_activities:
                if activity.activity_type in ["task_start", "output"] and activity.description not in current_tasks:
                    current_tasks.append(activity.description)
                if activity.workflow_phase:
                    current_phase = activity.workflow_phase
            
            task_count = len(current_tasks)
            capacity = capabilities["capacity"]
            utilization = min(100, (task_count / capacity) * 100)
            
            # Estimate next available time
            if utilization >= 100:
                # Estimate based on average task completion time
                avg_duration = 3.0  # hours (could get from metrics)
                next_available = datetime.now() + timedelta(hours=avg_duration)
            else:
                next_available = datetime.now()
            
            workload = AgentWorkload(
                agent_name=agent_name,
                role=role,
                current_tasks=current_tasks[:5],  # Limit display
                task_count=task_count,
                estimated_capacity=capacity,
                utilization_percentage=round(utilization, 1),
                next_available=next_available if utilization >= 100 else None,
                skill_areas=capabilities["skills"],
                current_phase=current_phase
            )
            
            workloads.append(workload)
        
        return workloads
    
    def _get_capable_agents_for_phase(self, phase: WorkflowPhase) -> List[str]:
        """Get agents capable of working on a specific phase."""
        capable_agents = []
        
        for agent_name, capabilities in self.agent_capabilities.items():
            if phase in capabilities.get("phases", []):
                capable_agents.append(agent_name)
        
        return capable_agents
    
    def _detect_coordination_issues(self, phases: List[WorkflowPhaseStatus], 
                                  workloads: List[AgentWorkload]) -> List[Dict]:
        """Detect coordination issues between agents and phases."""
        issues = []
        
        # Issue 1: Multiple agents working on same task
        task_assignments = {}
        for workload in workloads:
            for task in workload.current_tasks:
                if task not in task_assignments:
                    task_assignments[task] = []
                task_assignments[task].append(workload.agent_name)
        
        for task, agents in task_assignments.items():
            if len(agents) > 1:
                issues.append({
                    "type": "duplicate_work",
                    "severity": "medium",
                    "description": f"Multiple agents working on: {task}",
                    "agents": agents,
                    "recommendation": "Coordinate task assignment to avoid duplication"
                })
        
        # Issue 2: Phase dependencies not met
        for phase_status in phases:
            for dep_phase_name in phase_status.dependencies:
                try:
                    dep_phase = WorkflowPhase(dep_phase_name)
                    dep_status = next((p for p in phases if p.phase == dep_phase), None)
                    
                    if dep_status and dep_status.phase_progress < 80:
                        issues.append({
                            "type": "dependency_not_ready",
                            "severity": "high",
                            "description": f"{phase_status.phase.value} depends on incomplete {dep_phase_name}",
                            "phase": phase_status.phase.value,
                            "dependency": dep_phase_name,
                            "recommendation": f"Complete {dep_phase_name} before proceeding with {phase_status.phase.value}"
                        })
                except ValueError:
                    continue
        
        # Issue 3: No agent assigned to critical phase
        for phase_status in phases:
            if not phase_status.active_agents and not phase_status.completed_agents:
                capable_agents = self._get_capable_agents_for_phase(phase_status.phase)
                issues.append({
                    "type": "unassigned_phase",
                    "severity": "high",
                    "description": f"No agents assigned to {phase_status.phase.value}",
                    "phase": phase_status.phase.value,
                    "capable_agents": capable_agents,
                    "recommendation": f"Assign one of: {', '.join(capable_agents)} to {phase_status.phase.value}"
                })
        
        return issues
    
    def _detect_resource_conflicts(self, workloads: List[AgentWorkload]) -> List[Dict]:
        """Detect resource allocation conflicts."""
        conflicts = []
        
        # Conflict 1: Over-utilized agents
        for workload in workloads:
            if workload.utilization_percentage > 100:
                conflicts.append({
                    "type": "agent_overloaded",
                    "severity": "high",
                    "agent": workload.agent_name,
                    "utilization": workload.utilization_percentage,
                    "description": f"{workload.agent_name} is overloaded ({workload.utilization_percentage}%)",
                    "recommendation": "Redistribute tasks or extend timeline"
                })
        
        # Conflict 2: Critical skills bottleneck
        skill_demand = {}
        skill_supply = {}
        
        # Count skill demand and supply
        for workload in workloads:
            for skill in workload.skill_areas:
                skill_supply[skill] = skill_supply.get(skill, 0) + (workload.estimated_capacity - workload.task_count)
        
        # Simplified demand calculation (would be more sophisticated in practice)
        for workload in workloads:
            if workload.utilization_percentage > 80:
                for skill in workload.skill_areas:
                    skill_demand[skill] = skill_demand.get(skill, 0) + 1
        
        for skill, demand in skill_demand.items():
            supply = skill_supply.get(skill, 0)
            if demand > supply:
                conflicts.append({
                    "type": "skill_bottleneck",
                    "severity": "medium",
                    "skill": skill,
                    "demand": demand,
                    "supply": supply,
                    "description": f"High demand for {skill} skill, limited supply",
                    "recommendation": f"Consider cross-training or external support for {skill}"
                })
        
        return conflicts
    
    def _detect_communication_gaps(self) -> List[Dict]:
        """Detect communication and coordination gaps."""
        gaps = []
        
        # Gap 1: Agents not participating in coordination activities
        recent_cutoff = datetime.now() - timedelta(days=1)
        coordination_keywords = ["coordinate", "discuss", "review", "sync", "meeting"]
        
        coordination_activities = [
            activity for activity in self.monitor.activity_log
            if activity.timestamp > recent_cutoff and 
            any(kw in activity.description.lower() for kw in coordination_keywords)
        ]
        
        participating_agents = set(a.agent_name for a in coordination_activities)
        all_agents = set(self.monitor.agents.keys())
        non_participating = all_agents - participating_agents
        
        if len(non_participating) > 0:
            gaps.append({
                "type": "low_coordination_participation",
                "severity": "medium",
                "agents": list(non_participating),
                "description": f"Agents not participating in coordination: {', '.join(non_participating)}",
                "recommendation": "Encourage regular sync meetings and status updates"
            })
        
        # Gap 2: Long periods without cross-agent communication
        agent_pairs = {}
        for activity in self.monitor.activity_log[-50:]:  # Last 50 activities
            for other_activity in self.monitor.activity_log[-50:]:
                if (activity.agent_name != other_activity.agent_name and 
                    abs((activity.timestamp - other_activity.timestamp).total_seconds()) < 3600):
                    pair = tuple(sorted([activity.agent_name, other_activity.agent_name]))
                    agent_pairs[pair] = max(agent_pairs.get(pair, datetime.min), activity.timestamp)
        
        # Check for gaps
        cutoff = datetime.now() - timedelta(hours=8)
        for pair, last_interaction in agent_pairs.items():
            if last_interaction < cutoff:
                gaps.append({
                    "type": "communication_gap",
                    "severity": "low",
                    "agents": list(pair),
                    "last_interaction": last_interaction.isoformat(),
                    "description": f"No recent communication between {pair[0]} and {pair[1]}",
                    "recommendation": "Schedule sync or coordination meeting"
                })
        
        return gaps
    
    def _identify_workflow_bottlenecks(self, phases: List[WorkflowPhaseStatus]) -> List[str]:
        """Identify workflow bottlenecks."""
        bottlenecks = []
        
        for phase in phases:
            if len(phase.blocked_agents) > 0:
                bottlenecks.append(f"{phase.phase.value}: {len(phase.blocked_agents)} blocked agents")
            
            if phase.phase_progress < 20 and len(phase.active_agents) == 0:
                bottlenecks.append(f"{phase.phase.value}: No progress, no active agents")
            
            if len(phase.bottlenecks) > 0:
                bottlenecks.extend([f"{phase.phase.value}: {b}" for b in phase.bottlenecks])
        
        return bottlenecks
    
    def _calculate_coordination_status(self, coordination_issues: List[Dict],
                                     resource_conflicts: List[Dict],
                                     communication_gaps: List[Dict]) -> CoordinationStatus:
        """Calculate overall coordination status."""
        
        high_severity_issues = len([i for i in coordination_issues if i.get("severity") == "high"])
        medium_severity_issues = len([i for i in coordination_issues if i.get("severity") == "medium"])
        
        high_severity_conflicts = len([c for c in resource_conflicts if c.get("severity") == "high"])
        medium_severity_conflicts = len([c for c in resource_conflicts if c.get("severity") == "medium"])
        
        total_gaps = len(communication_gaps)
        
        # Calculate score
        score = 100
        score -= high_severity_issues * 20
        score -= medium_severity_issues * 10
        score -= high_severity_conflicts * 15
        score -= medium_severity_conflicts * 8
        score -= total_gaps * 5
        
        if score >= 90:
            return CoordinationStatus.OPTIMAL
        elif score >= 70:
            return CoordinationStatus.GOOD
        elif score >= 50:
            return CoordinationStatus.ATTENTION
        else:
            return CoordinationStatus.CRITICAL
    
    def _generate_coordination_recommendations(self, coordination_issues: List[Dict],
                                             resource_conflicts: List[Dict],
                                             communication_gaps: List[Dict],
                                             bottlenecks: List[str]) -> List[str]:
        """Generate actionable coordination recommendations."""
        recommendations = []
        
        # From coordination issues
        if coordination_issues:
            high_priority_issues = [i for i in coordination_issues if i.get("severity") == "high"]
            if high_priority_issues:
                recommendations.append(f"Address {len(high_priority_issues)} high-priority coordination issues immediately")
            
            duplicate_work = [i for i in coordination_issues if i.get("type") == "duplicate_work"]
            if duplicate_work:
                recommendations.append("Implement task assignment coordination to prevent duplicate work")
        
        # From resource conflicts
        if resource_conflicts:
            overloaded_agents = [c for c in resource_conflicts if c.get("type") == "agent_overloaded"]
            if overloaded_agents:
                agents = [c["agent"] for c in overloaded_agents]
                recommendations.append(f"Redistribute workload for overloaded agents: {', '.join(agents)}")
        
        # From communication gaps
        if communication_gaps:
            if len(communication_gaps) > 3:
                recommendations.append("Schedule regular team sync meetings to improve communication")
        
        # From bottlenecks
        if bottlenecks:
            recommendations.append("Focus on resolving workflow bottlenecks to improve team velocity")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Team coordination is optimal - maintain current practices")
        
        return recommendations
    
    def _calculate_team_velocity(self) -> float:
        """Calculate current team velocity in tasks per hour."""
        
        # Get completed tasks in last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        completed_tasks = [
            activity for activity in self.monitor.activity_log
            if activity.timestamp > cutoff and activity.activity_type == "task_complete"
        ]
        
        if not completed_tasks:
            return 0.0
        
        # Calculate velocity
        hours = 24
        velocity = len(completed_tasks) / hours
        
        return round(velocity, 2)
    
    def save_coordination_state(self, state: TeamCoordinationState):
        """Save coordination state to history."""
        try:
            with open(self.coordination_history_file, 'a') as f:
                f.write(json.dumps(state.to_dict()) + '\n')
            logger.info("Saved coordination state")
        except Exception as e:
            logger.error(f"Error saving coordination state: {e}")
    
    def get_coordination_trends(self, days: int = 7) -> Dict:
        """Get coordination trends over time."""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Load historical states
        states = []
        if self.coordination_history_file.exists():
            try:
                with open(self.coordination_history_file, 'r') as f:
                    for line in f:
                        data = json.loads(line.strip())
                        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                        if data['timestamp'] > cutoff_date:
                            states.append(data)
            except Exception as e:
                logger.error(f"Error loading coordination history: {e}")
        
        if not states:
            return {"error": "No historical data available"}
        
        # Calculate trends
        velocity_trend = [s['team_velocity'] for s in states]
        coordination_scores = []
        
        for s in states:
            status = s['coordination_status']
            score_map = {'optimal': 100, 'good': 80, 'attention': 60, 'critical': 40}
            coordination_scores.append(score_map.get(status, 50))
        
        return {
            "period_days": days,
            "states_count": len(states),
            "velocity_trend": {
                "values": velocity_trend,
                "average": round(sum(velocity_trend) / len(velocity_trend), 2),
                "trend": "improving" if velocity_trend[-1] > velocity_trend[0] else "declining"
            },
            "coordination_trend": {
                "values": coordination_scores,
                "average": round(sum(coordination_scores) / len(coordination_scores), 1),
                "trend": "improving" if coordination_scores[-1] > coordination_scores[0] else "declining"
            }
        }

def main():
    """Test the team coordination dashboard."""
    
    # Initialize components
    from agent_activity_monitor import AgentActivityMonitor
    from agent_performance_dashboard import AgentPerformanceDashboard
    
    monitor = AgentActivityMonitor()
    performance_dashboard = AgentPerformanceDashboard(monitor)
    coordination_dashboard = TeamCoordinationDashboard(monitor, performance_dashboard)
    
    # Simulate team activities across different phases
    monitor.log_activity("ProjectManager", "task_start", "Coordinating Phase 4B validation execution", 
                        workflow_phase="planning")
    monitor.log_activity("Architect", "review", "Reviewing validation framework architecture",
                        duration_minutes=45, output_quality=9, workflow_phase="architecture")
    monitor.log_activity("SecurityEngineer", "review", "Security review of monitoring system",
                        duration_minutes=60, output_quality=8, workflow_phase="security_review")
    monitor.log_activity("QAEngineer", "task_start", "Preparing validation test execution",
                        workflow_phase="qa_review")
    monitor.log_activity("Implementer", "output", "Implementing coordination dashboard features",
                        workflow_phase="implementation")
    monitor.log_activity("DevOpsEngineer", "task_complete", "Set up monitoring infrastructure",
                        duration_minutes=90, output_quality=8, workflow_phase="deployment")
    monitor.log_activity("PerformanceEngineer", "task_start", "Analyzing team performance metrics",
                        workflow_phase="validation")
    monitor.log_activity("DocumentationEngineer", "output", "Updating coordination documentation",
                        workflow_phase="requirements")
    
    # Generate coordination analysis
    print("🏢 Team Coordination Dashboard Analysis:")
    coordination_state = coordination_dashboard.analyze_current_coordination()
    
    print(f"\n📊 Coordination Status: {coordination_state.coordination_status.value.upper()}")
    print(f"   Team Velocity: {coordination_state.team_velocity} tasks/hour")
    print(f"   Active Phases: {len(coordination_state.active_phases)}")
    print(f"   Coordination Issues: {len(coordination_state.coordination_issues)}")
    print(f"   Resource Conflicts: {len(coordination_state.resource_conflicts)}")
    print(f"   Communication Gaps: {len(coordination_state.communication_gaps)}")
    
    # Show active workflow phases
    if coordination_state.active_phases:
        print("\n🔄 Active Workflow Phases:")
        for phase in coordination_state.active_phases:
            print(f"   {phase.phase.value}: {phase.phase_progress}% complete")
            if phase.active_agents:
                print(f"      Active: {', '.join(phase.active_agents)}")
            if phase.completed_agents:
                print(f"      Completed: {', '.join(phase.completed_agents)}")
            if phase.blocked_agents:
                print(f"      Blocked: {', '.join(phase.blocked_agents)}")
    
    # Show agent workloads
    print("\n👥 Agent Workload Summary:")
    for workload in coordination_state.agent_workloads:
        utilization_status = "🔴 Overloaded" if workload.utilization_percentage > 100 else \
                           "🟡 High" if workload.utilization_percentage > 80 else \
                           "🟢 Normal"
        print(f"   {workload.agent_name}: {workload.utilization_percentage}% {utilization_status}")
        print(f"      Tasks: {workload.task_count}/{workload.estimated_capacity}")
        if workload.current_phase:
            print(f"      Phase: {workload.current_phase}")
    
    # Show issues and recommendations
    if coordination_state.coordination_issues:
        print("\n⚠️  Coordination Issues:")
        for issue in coordination_state.coordination_issues:
            print(f"   {issue['type']}: {issue['description']}")
    
    if coordination_state.recommended_actions:
        print("\n💡 Recommended Actions:")
        for action in coordination_state.recommended_actions:
            print(f"   - {action}")
    
    # Save state
    coordination_dashboard.save_coordination_state(coordination_state)
    
    print("\n✅ Team Coordination Dashboard Test Complete")

if __name__ == "__main__":
    main()