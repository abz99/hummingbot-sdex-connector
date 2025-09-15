#!/usr/bin/env python3
"""
Agent Accountability System
Individual responsibility tracking, goal setting, and accountability metrics for the 8-agent development team.
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
from agent_performance_dashboard import AgentPerformanceDashboard, AgentPerformanceAnalysis
from team_coordination_dashboard import TeamCoordinationDashboard

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AccountabilityLevel(Enum):
    """Agent accountability levels."""
    EXCEPTIONAL = "exceptional"  # Exceeds all commitments
    STRONG = "strong"           # Meets all commitments consistently
    ADEQUATE = "adequate"       # Meets most commitments
    CONCERNING = "concerning"   # Missing some commitments
    CRITICAL = "critical"       # Frequently missing commitments

class CommitmentStatus(Enum):
    """Status of individual commitments."""
    ACTIVE = "active"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

@dataclass
class AgentCommitment:
    """Individual agent commitment/goal."""
    commitment_id: str
    agent_name: str
    description: str
    target_date: datetime
    created_date: datetime
    status: CommitmentStatus
    progress_percentage: float
    success_criteria: List[str]
    dependencies: List[str]
    estimated_hours: float
    actual_hours: Optional[float]
    quality_target: float  # 1-10 scale
    actual_quality: Optional[float]
    notes: List[str]
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['target_date'] = self.target_date.isoformat()
        data['created_date'] = self.created_date.isoformat()
        data['status'] = self.status.value
        return data

@dataclass
class AccountabilityMetrics:
    """Accountability metrics for an agent."""
    agent_name: str
    commitment_completion_rate: float  # Percentage of commitments met on time
    average_delay_days: float  # Average days past deadline
    quality_consistency: float  # How consistent quality is vs targets
    proactive_communication: float  # Score for proactive updates
    reliability_score: float  # Overall reliability metric
    trend: str  # "improving", "stable", "declining"
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class AgentAccountabilityReport:
    """Comprehensive accountability report for an agent."""
    agent_name: str
    role: str
    accountability_level: AccountabilityLevel
    overall_score: float
    metrics: AccountabilityMetrics
    active_commitments: List[AgentCommitment]
    recent_completions: List[AgentCommitment]
    overdue_commitments: List[AgentCommitment]
    strengths: List[str]
    improvement_areas: List[str]
    recommendations: List[str]
    next_review_date: datetime
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['accountability_level'] = self.accountability_level.value
        data['metrics'] = self.metrics.to_dict()
        data['active_commitments'] = [c.to_dict() for c in self.active_commitments]
        data['recent_completions'] = [c.to_dict() for c in self.recent_completions]
        data['overdue_commitments'] = [c.to_dict() for c in self.overdue_commitments]
        data['next_review_date'] = self.next_review_date.isoformat()
        return data

@dataclass
class TeamAccountabilitySnapshot:
    """Team-wide accountability snapshot."""
    timestamp: datetime
    overall_accountability_score: float
    agents_by_level: Dict[str, List[str]]  # accountability level -> agent names
    total_active_commitments: int
    total_overdue_commitments: int
    average_completion_rate: float
    team_reliability_trends: Dict[str, float]
    accountability_risks: List[Dict]
    intervention_recommendations: List[str]
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class AgentAccountabilitySystem:
    """Comprehensive agent accountability and responsibility tracking system."""
    
    def __init__(self, monitor: AgentActivityMonitor, 
                 performance_dashboard: AgentPerformanceDashboard,
                 coordination_dashboard: TeamCoordinationDashboard):
        self.monitor = monitor
        self.performance_dashboard = performance_dashboard
        self.coordination_dashboard = coordination_dashboard
        self.data_dir = monitor.data_dir
        
        self.commitments_file = self.data_dir / "agent_commitments.json"
        self.accountability_history_file = self.data_dir / "accountability_history.jsonl"
        
        # Store commitments in memory and persist to file
        self.agent_commitments: Dict[str, List[AgentCommitment]] = {}
        self._load_commitments()
        
        # Accountability thresholds
        self.thresholds = {
            "exceptional_completion_rate": 95.0,
            "strong_completion_rate": 85.0,
            "adequate_completion_rate": 70.0,
            "concerning_completion_rate": 50.0,
            "max_acceptable_delay": 2.0,  # days
            "quality_consistency_target": 0.8,  # variance threshold
            "proactive_communication_target": 8.0
        }
    
    def _load_commitments(self):
        """Load existing commitments from file."""
        if self.commitments_file.exists():
            try:
                with open(self.commitments_file, 'r') as f:
                    data = json.load(f)
                    
                for agent_name, commitments_data in data.items():
                    self.agent_commitments[agent_name] = []
                    for commitment_data in commitments_data:
                        commitment_data['target_date'] = datetime.fromisoformat(commitment_data['target_date'])
                        commitment_data['created_date'] = datetime.fromisoformat(commitment_data['created_date'])
                        commitment_data['status'] = CommitmentStatus(commitment_data['status'])
                        
                        commitment = AgentCommitment(**commitment_data)
                        self.agent_commitments[agent_name].append(commitment)
                
                logger.info(f"Loaded commitments for {len(self.agent_commitments)} agents")
            except Exception as e:
                logger.error(f"Error loading commitments: {e}")
    
    def _save_commitments(self):
        """Save commitments to file."""
        try:
            data = {}
            for agent_name, commitments in self.agent_commitments.items():
                data[agent_name] = [c.to_dict() for c in commitments]
            
            with open(self.commitments_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Saved agent commitments")
        except Exception as e:
            logger.error(f"Error saving commitments: {e}")
    
    def create_commitment(self, agent_name: str, description: str, target_date: datetime,
                         success_criteria: List[str], estimated_hours: float,
                         quality_target: float = 8.0, dependencies: List[str] = None) -> str:
        """Create a new commitment for an agent."""
        
        commitment_id = f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        commitment = AgentCommitment(
            commitment_id=commitment_id,
            agent_name=agent_name,
            description=description,
            target_date=target_date,
            created_date=datetime.now(),
            status=CommitmentStatus.ACTIVE,
            progress_percentage=0.0,
            success_criteria=success_criteria or [],
            dependencies=dependencies or [],
            estimated_hours=estimated_hours,
            actual_hours=None,
            quality_target=quality_target,
            actual_quality=None,
            notes=[]
        )
        
        if agent_name not in self.agent_commitments:
            self.agent_commitments[agent_name] = []
        
        self.agent_commitments[agent_name].append(commitment)
        self._save_commitments()
        
        # Log the commitment creation
        self.monitor.log_activity(
            agent_name=agent_name,
            activity_type="commitment_created",
            description=f"Created commitment: {description}",
            workflow_phase="planning"
        )
        
        logger.info(f"Created commitment {commitment_id} for {agent_name}")
        return commitment_id
    
    def update_commitment_progress(self, commitment_id: str, progress_percentage: float,
                                 notes: str = None, actual_hours: float = None):
        """Update progress on a commitment."""
        
        commitment = self._find_commitment(commitment_id)
        if not commitment:
            raise ValueError(f"Commitment {commitment_id} not found")
        
        commitment.progress_percentage = min(100, max(0, progress_percentage))
        if actual_hours is not None:
            commitment.actual_hours = actual_hours
        if notes:
            commitment.notes.append(f"{datetime.now().isoformat()}: {notes}")
        
        # Auto-complete if 100%
        if progress_percentage >= 100 and commitment.status == CommitmentStatus.ACTIVE:
            commitment.status = CommitmentStatus.COMPLETED
            
            # Log completion
            self.monitor.log_activity(
                agent_name=commitment.agent_name,
                activity_type="commitment_completed",
                description=f"Completed commitment: {commitment.description}",
                duration_minutes=(actual_hours * 60) if actual_hours else None,
                workflow_phase="completion"
            )
        
        self._save_commitments()
        logger.info(f"Updated commitment {commitment_id} progress to {progress_percentage}%")
    
    def complete_commitment(self, commitment_id: str, actual_quality: float = None,
                          actual_hours: float = None, notes: str = None):
        """Mark a commitment as completed."""
        
        commitment = self._find_commitment(commitment_id)
        if not commitment:
            raise ValueError(f"Commitment {commitment_id} not found")
        
        commitment.status = CommitmentStatus.COMPLETED
        commitment.progress_percentage = 100.0
        if actual_quality is not None:
            commitment.actual_quality = actual_quality
        if actual_hours is not None:
            commitment.actual_hours = actual_hours
        if notes:
            commitment.notes.append(f"{datetime.now().isoformat()}: {notes}")
        
        self._save_commitments()
        
        # Log completion
        self.monitor.log_activity(
            agent_name=commitment.agent_name,
            activity_type="commitment_completed",
            description=f"Completed commitment: {commitment.description}",
            duration_minutes=(actual_hours * 60) if actual_hours else None,
            output_quality=int(actual_quality) if actual_quality else None,
            workflow_phase="completion"
        )
        
        logger.info(f"Completed commitment {commitment_id}")
    
    def _find_commitment(self, commitment_id: str) -> Optional[AgentCommitment]:
        """Find a commitment by ID."""
        for agent_commitments in self.agent_commitments.values():
            for commitment in agent_commitments:
                if commitment.commitment_id == commitment_id:
                    return commitment
        return None
    
    def calculate_accountability_metrics(self, agent_name: str, days: int = 30) -> AccountabilityMetrics:
        """Calculate comprehensive accountability metrics for an agent."""
        
        if agent_name not in self.agent_commitments:
            # Return default metrics for agents with no commitments yet
            return AccountabilityMetrics(
                agent_name=agent_name,
                commitment_completion_rate=80.0,  # Default assumption
                average_delay_days=0.0,
                quality_consistency=8.0,
                proactive_communication=7.0,
                reliability_score=7.5,
                trend="stable"
            )
        
        commitments = self.agent_commitments[agent_name]
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_commitments = [c for c in commitments if c.created_date > cutoff_date]
        
        if not recent_commitments:
            recent_commitments = commitments[-10:]  # Last 10 commitments if no recent ones
        
        # Calculate completion rate
        completed = [c for c in recent_commitments if c.status == CommitmentStatus.COMPLETED]
        total_finished = [c for c in recent_commitments 
                         if c.status in [CommitmentStatus.COMPLETED, CommitmentStatus.OVERDUE]]
        
        if total_finished:
            completion_rate = (len(completed) / len(total_finished)) * 100
        else:
            completion_rate = 100.0  # No finished commitments to judge
        
        # Calculate average delay
        delays = []
        for commitment in completed:
            if commitment.target_date:
                # Find actual completion date from activities
                completion_activities = [
                    a for a in self.monitor.activity_log
                    if (a.agent_name == agent_name and 
                        a.activity_type == "commitment_completed" and
                        commitment.description in a.description)
                ]
                
                if completion_activities:
                    completion_date = max(a.timestamp for a in completion_activities)
                    delay = (completion_date - commitment.target_date).total_seconds() / (24 * 3600)
                    delays.append(max(0, delay))  # Only count positive delays
        
        average_delay = sum(delays) / len(delays) if delays else 0.0
        
        # Calculate quality consistency
        quality_scores = [c.actual_quality for c in completed if c.actual_quality is not None]
        if len(quality_scores) > 1:
            quality_variance = sum((q - sum(quality_scores)/len(quality_scores))**2 for q in quality_scores) / len(quality_scores)
            quality_consistency = max(1, 10 - quality_variance)  # Lower variance = higher consistency
        else:
            quality_consistency = 8.0  # Default
        
        # Calculate proactive communication score
        communication_activities = [
            a for a in self.monitor.activity_log
            if (a.agent_name == agent_name and 
                a.timestamp > cutoff_date and
                any(kw in a.description.lower() for kw in ["update", "status", "progress", "report"]))
        ]
        proactive_communication = min(10, len(communication_activities) / 3)  # 3+ updates = 10 score
        
        # Calculate overall reliability score
        reliability_score = (
            completion_rate * 0.4 +  # 40% weight on completion
            max(0, 10 - average_delay) * 0.3 +  # 30% weight on timeliness
            quality_consistency * 0.2 +  # 20% weight on quality
            proactive_communication * 0.1  # 10% weight on communication
        ) / 10
        
        # Determine trend
        if len(recent_commitments) >= 4:
            first_half = recent_commitments[:len(recent_commitments)//2]
            second_half = recent_commitments[len(recent_commitments)//2:]
            
            first_half_rate = len([c for c in first_half if c.status == CommitmentStatus.COMPLETED]) / len(first_half) * 100
            second_half_rate = len([c for c in second_half if c.status == CommitmentStatus.COMPLETED]) / len(second_half) * 100
            
            if second_half_rate > first_half_rate + 10:
                trend = "improving"
            elif second_half_rate < first_half_rate - 10:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return AccountabilityMetrics(
            agent_name=agent_name,
            commitment_completion_rate=round(completion_rate, 1),
            average_delay_days=round(average_delay, 1),
            quality_consistency=round(quality_consistency, 1),
            proactive_communication=round(proactive_communication, 1),
            reliability_score=round(reliability_score * 10, 1),  # Scale to 1-10
            trend=trend
        )
    
    def generate_agent_accountability_report(self, agent_name: str) -> AgentAccountabilityReport:
        """Generate comprehensive accountability report for an agent."""
        
        if agent_name not in self.monitor.agents:
            raise ValueError(f"Agent {agent_name} not found")
        
        role = self.monitor.agents[agent_name]["role"]
        metrics = self.calculate_accountability_metrics(agent_name)
        
        # Get commitments by status
        agent_commitments = self.agent_commitments.get(agent_name, [])
        active_commitments = [c for c in agent_commitments if c.status == CommitmentStatus.ACTIVE]
        recent_completions = [c for c in agent_commitments 
                            if c.status == CommitmentStatus.COMPLETED and 
                            (datetime.now() - c.created_date).days <= 30]
        
        # Update overdue commitments
        now = datetime.now()
        overdue_commitments = []
        for commitment in active_commitments:
            if commitment.target_date < now:
                commitment.status = CommitmentStatus.OVERDUE
                overdue_commitments.append(commitment)
        
        # Calculate accountability level
        accountability_level = self._calculate_accountability_level(metrics)
        
        # Calculate overall score
        overall_score = (
            metrics.reliability_score * 0.5 +
            (100 - metrics.average_delay_days * 10) * 0.3 / 10 +
            metrics.quality_consistency * 0.2
        )
        
        # Generate insights
        strengths = self._identify_accountability_strengths(metrics, recent_completions)
        improvement_areas = self._identify_accountability_improvements(metrics, overdue_commitments)
        recommendations = self._generate_accountability_recommendations(agent_name, role, metrics, improvement_areas)
        
        # Next review date (2 weeks for concerning/critical, 1 month for others)
        if accountability_level in [AccountabilityLevel.CONCERNING, AccountabilityLevel.CRITICAL]:
            next_review = datetime.now() + timedelta(weeks=2)
        else:
            next_review = datetime.now() + timedelta(weeks=4)
        
        return AgentAccountabilityReport(
            agent_name=agent_name,
            role=role,
            accountability_level=accountability_level,
            overall_score=round(overall_score, 1),
            metrics=metrics,
            active_commitments=active_commitments,
            recent_completions=recent_completions,
            overdue_commitments=overdue_commitments,
            strengths=strengths,
            improvement_areas=improvement_areas,
            recommendations=recommendations,
            next_review_date=next_review
        )
    
    def _calculate_accountability_level(self, metrics: AccountabilityMetrics) -> AccountabilityLevel:
        """Determine accountability level based on metrics."""
        
        completion_rate = metrics.commitment_completion_rate
        reliability = metrics.reliability_score
        delay = metrics.average_delay_days
        
        # Exceptional: >95% completion, >9 reliability, <1 day delay
        if (completion_rate >= self.thresholds["exceptional_completion_rate"] and 
            reliability >= 9.0 and delay < 1.0):
            return AccountabilityLevel.EXCEPTIONAL
        
        # Strong: >85% completion, >7.5 reliability, <2 day delay
        elif (completion_rate >= self.thresholds["strong_completion_rate"] and 
              reliability >= 7.5 and delay <= self.thresholds["max_acceptable_delay"]):
            return AccountabilityLevel.STRONG
        
        # Adequate: >70% completion, >6 reliability, <5 day delay
        elif (completion_rate >= self.thresholds["adequate_completion_rate"] and 
              reliability >= 6.0 and delay < 5.0):
            return AccountabilityLevel.ADEQUATE
        
        # Concerning: >50% completion, >4 reliability
        elif (completion_rate >= self.thresholds["concerning_completion_rate"] and 
              reliability >= 4.0):
            return AccountabilityLevel.CONCERNING
        
        # Critical: Below concerning thresholds
        else:
            return AccountabilityLevel.CRITICAL
    
    def _identify_accountability_strengths(self, metrics: AccountabilityMetrics, 
                                         completions: List[AgentCommitment]) -> List[str]:
        """Identify accountability strengths."""
        strengths = []
        
        if metrics.commitment_completion_rate >= 90:
            strengths.append("Excellent commitment completion rate")
        if metrics.average_delay_days <= 1.0:
            strengths.append("Consistently meets deadlines")
        if metrics.quality_consistency >= 8.0:
            strengths.append("High quality consistency across deliverables")
        if metrics.proactive_communication >= 7.0:
            strengths.append("Proactive communication and status updates")
        if metrics.trend == "improving":
            strengths.append("Demonstrating improvement over time")
        
        # Analyze completion patterns
        if len(completions) >= 5:
            on_time_completions = sum(1 for c in completions if c.actual_hours and c.estimated_hours and c.actual_hours <= c.estimated_hours * 1.1)
            if on_time_completions / len(completions) >= 0.8:
                strengths.append("Accurate effort estimation and delivery")
        
        return strengths if strengths else ["Maintains baseline accountability standards"]
    
    def _identify_accountability_improvements(self, metrics: AccountabilityMetrics,
                                           overdue_commitments: List[AgentCommitment]) -> List[str]:
        """Identify areas for accountability improvement."""
        improvements = []
        
        if metrics.commitment_completion_rate < 70:
            improvements.append("Improve commitment completion consistency")
        if metrics.average_delay_days > 3.0:
            improvements.append("Better deadline management and planning")
        if metrics.quality_consistency < 6.0:
            improvements.append("More consistent quality delivery")
        if metrics.proactive_communication < 5.0:
            improvements.append("Increase proactive status communication")
        if len(overdue_commitments) > 2:
            improvements.append("Address overdue commitments promptly")
        if metrics.trend == "declining":
            improvements.append("Reverse declining performance trend")
        
        return improvements
    
    def _generate_accountability_recommendations(self, agent_name: str, role: str,
                                               metrics: AccountabilityMetrics,
                                               improvement_areas: List[str]) -> List[str]:
        """Generate specific recommendations for accountability improvement."""
        recommendations = []
        
        # Role-specific recommendations
        if role == "coordinator" and "proactive status communication" in " ".join(improvement_areas).lower():
            recommendations.append("Implement weekly team status update routine")
            recommendations.append("Set up automated progress tracking dashboard")
        
        elif role == "reviewer" and "commitment completion consistency" in " ".join(improvement_areas).lower():
            recommendations.append("Break large review tasks into smaller, time-boxed reviews")
            recommendations.append("Set up review completion tracking with clear criteria")
        
        elif role == "implementer" and "deadline management" in " ".join(improvement_areas).lower():
            recommendations.append("Use time-boxing techniques for implementation tasks")
            recommendations.append("Create buffer time in estimates for unexpected issues")
        
        # Metric-specific recommendations
        if metrics.commitment_completion_rate < 60:
            recommendations.append("Work with ProjectManager to reassess commitment feasibility")
            recommendations.append("Focus on completing existing commitments before taking new ones")
        
        if metrics.average_delay_days > 5:
            recommendations.append("Implement daily progress check-ins")
            recommendations.append("Create early warning system for at-risk commitments")
        
        # General recommendations
        if not recommendations:
            if metrics.reliability_score >= 8.0:
                recommendations.append("Consider mentoring other team members on accountability practices")
                recommendations.append("Take on additional responsibilities or complex commitments")
            else:
                recommendations.append("Continue current accountability practices and monitor trends")
        
        return recommendations
    
    def generate_team_accountability_snapshot(self) -> TeamAccountabilitySnapshot:
        """Generate team-wide accountability snapshot."""
        
        now = datetime.now()
        
        # Generate reports for all agents
        agent_reports = {}
        for agent_name in self.monitor.agents:
            try:
                agent_reports[agent_name] = self.generate_agent_accountability_report(agent_name)
            except Exception as e:
                logger.error(f"Error generating report for {agent_name}: {e}")
                continue
        
        # Group agents by accountability level
        agents_by_level = {level.value: [] for level in AccountabilityLevel}
        for agent_name, report in agent_reports.items():
            agents_by_level[report.accountability_level.value].append(agent_name)
        
        # Calculate team metrics
        total_active = sum(len(report.active_commitments) for report in agent_reports.values())
        total_overdue = sum(len(report.overdue_commitments) for report in agent_reports.values())
        
        completion_rates = [report.metrics.commitment_completion_rate for report in agent_reports.values()]
        average_completion_rate = sum(completion_rates) / len(completion_rates) if completion_rates else 0
        
        reliability_scores = [report.metrics.reliability_score for report in agent_reports.values()]
        overall_score = sum(reliability_scores) / len(reliability_scores) if reliability_scores else 0
        
        # Analyze trends
        improving_agents = [name for name, report in agent_reports.items() if report.metrics.trend == "improving"]
        declining_agents = [name for name, report in agent_reports.items() if report.metrics.trend == "declining"]
        
        team_reliability_trends = {
            "improving": len(improving_agents) / len(agent_reports) * 100,
            "declining": len(declining_agents) / len(agent_reports) * 100,
            "stable": (len(agent_reports) - len(improving_agents) - len(declining_agents)) / len(agent_reports) * 100
        }
        
        # Identify risks
        accountability_risks = []
        
        critical_agents = agents_by_level[AccountabilityLevel.CRITICAL.value]
        if critical_agents:
            accountability_risks.append({
                "type": "critical_accountability",
                "severity": "high",
                "agents": critical_agents,
                "description": f"Agents with critical accountability: {', '.join(critical_agents)}",
                "impact": "Project delivery risk"
            })
        
        if total_overdue > 5:
            accountability_risks.append({
                "type": "high_overdue_commitments",
                "severity": "medium",
                "count": total_overdue,
                "description": f"{total_overdue} overdue commitments across team",
                "impact": "Schedule and quality risk"
            })
        
        if len(declining_agents) > len(improving_agents):
            accountability_risks.append({
                "type": "declining_team_trend",
                "severity": "medium",
                "declining_count": len(declining_agents),
                "description": "More agents declining than improving in accountability",
                "impact": "Team performance degradation risk"
            })
        
        # Generate intervention recommendations
        intervention_recommendations = []
        
        if critical_agents:
            intervention_recommendations.append(f"Immediate 1:1 review with critical agents: {', '.join(critical_agents)}")
        
        if total_overdue > 0:
            intervention_recommendations.append("Review and reprioritize overdue commitments team-wide")
        
        concerning_agents = agents_by_level[AccountabilityLevel.CONCERNING.value]
        if concerning_agents:
            intervention_recommendations.append(f"Enhanced monitoring for concerning agents: {', '.join(concerning_agents)}")
        
        if not intervention_recommendations:
            if overall_score >= 8.0:
                intervention_recommendations.append("Team accountability is strong - consider stretch goals")
            else:
                intervention_recommendations.append("Maintain current accountability practices and monitor trends")
        
        return TeamAccountabilitySnapshot(
            timestamp=now,
            overall_accountability_score=round(overall_score, 1),
            agents_by_level=agents_by_level,
            total_active_commitments=total_active,
            total_overdue_commitments=total_overdue,
            average_completion_rate=round(average_completion_rate, 1),
            team_reliability_trends=team_reliability_trends,
            accountability_risks=accountability_risks,
            intervention_recommendations=intervention_recommendations
        )
    
    def save_accountability_snapshot(self, snapshot: TeamAccountabilitySnapshot):
        """Save accountability snapshot to history."""
        try:
            with open(self.accountability_history_file, 'a') as f:
                f.write(json.dumps(snapshot.to_dict()) + '\n')
            logger.info("Saved accountability snapshot")
        except Exception as e:
            logger.error(f"Error saving accountability snapshot: {e}")

def main():
    """Test the agent accountability system."""
    
    # Initialize all components
    from agent_activity_monitor import AgentActivityMonitor
    from agent_performance_dashboard import AgentPerformanceDashboard
    from team_coordination_dashboard import TeamCoordinationDashboard
    
    monitor = AgentActivityMonitor()
    performance_dashboard = AgentPerformanceDashboard(monitor)
    coordination_dashboard = TeamCoordinationDashboard(monitor, performance_dashboard)
    accountability_system = AgentAccountabilitySystem(monitor, performance_dashboard, coordination_dashboard)
    
    # Create some test commitments
    print("🎯 Creating Test Commitments:")
    
    # ProjectManager commitments
    pm_commitment1 = accountability_system.create_commitment(
        agent_name="ProjectManager",
        description="Complete Phase 4B validation coordination",
        target_date=datetime.now() + timedelta(days=7),
        success_criteria=["All validation tests executed", "Results documented", "Next phase planned"],
        estimated_hours=20.0,
        quality_target=9.0
    )
    
    # QAEngineer commitments
    qa_commitment1 = accountability_system.create_commitment(
        agent_name="QAEngineer", 
        description="Execute comprehensive security penetration testing",
        target_date=datetime.now() + timedelta(days=5),
        success_criteria=["All security tests pass", "Vulnerabilities documented", "Mitigation plans created"],
        estimated_hours=15.0,
        quality_target=9.5
    )
    
    # Implementer commitments (with one overdue for testing)
    impl_commitment1 = accountability_system.create_commitment(
        agent_name="Implementer",
        description="Implement performance optimization fixes",
        target_date=datetime.now() - timedelta(days=2),  # Make it overdue
        success_criteria=["Performance benchmarks improved", "Code review passed", "Tests updated"],
        estimated_hours=12.0,
        quality_target=8.0
    )
    
    print(f"   Created commitment: {pm_commitment1}")
    print(f"   Created commitment: {qa_commitment1}")
    print(f"   Created commitment: {impl_commitment1}")
    
    # Update some progress
    accountability_system.update_commitment_progress(pm_commitment1, 30.0, "Validation framework reviewed")
    accountability_system.update_commitment_progress(qa_commitment1, 60.0, "Security tests configured", actual_hours=8.0)
    accountability_system.complete_commitment(impl_commitment1, actual_quality=7.5, actual_hours=14.0, notes="Completed with minor delays")
    
    # Generate individual accountability reports
    print("\n📊 Individual Accountability Reports:")
    for agent_name in ["ProjectManager", "QAEngineer", "Implementer"]:
        try:
            report = accountability_system.generate_agent_accountability_report(agent_name)
            print(f"\n👤 {agent_name} ({report.accountability_level.value.upper()}):")
            print(f"   Overall Score: {report.overall_score}/10")
            print(f"   Completion Rate: {report.metrics.commitment_completion_rate}%")
            print(f"   Average Delay: {report.metrics.average_delay_days} days")
            print(f"   Reliability Score: {report.metrics.reliability_score}/10")
            print(f"   Trend: {report.metrics.trend}")
            print(f"   Active Commitments: {len(report.active_commitments)}")
            print(f"   Overdue Commitments: {len(report.overdue_commitments)}")
            if report.strengths:
                print(f"   Strengths: {'; '.join(report.strengths[:2])}")
            if report.recommendations:
                print(f"   Recommendations: {'; '.join(report.recommendations[:2])}")
        except Exception as e:
            print(f"   Error generating report for {agent_name}: {e}")
    
    # Generate team accountability snapshot
    print("\n🏢 Team Accountability Snapshot:")
    snapshot = accountability_system.generate_team_accountability_snapshot()
    
    print(f"   Overall Accountability Score: {snapshot.overall_accountability_score}/10")
    print(f"   Active Commitments: {snapshot.total_active_commitments}")
    print(f"   Overdue Commitments: {snapshot.total_overdue_commitments}")
    print(f"   Average Completion Rate: {snapshot.average_completion_rate}%")
    
    print("\n📈 Agents by Accountability Level:")
    for level, agents in snapshot.agents_by_level.items():
        if agents:
            print(f"   {level.title()}: {', '.join(agents)}")
    
    print(f"\n📊 Team Trends:")
    for trend, percentage in snapshot.team_reliability_trends.items():
        print(f"   {trend.title()}: {percentage:.1f}%")
    
    if snapshot.accountability_risks:
        print("\n⚠️  Accountability Risks:")
        for risk in snapshot.accountability_risks:
            print(f"   {risk['type']}: {risk['description']}")
    
    if snapshot.intervention_recommendations:
        print("\n💡 Intervention Recommendations:")
        for rec in snapshot.intervention_recommendations:
            print(f"   - {rec}")
    
    # Save snapshot
    accountability_system.save_accountability_snapshot(snapshot)
    
    print("\n✅ Agent Accountability System Test Complete")

if __name__ == "__main__":
    main()