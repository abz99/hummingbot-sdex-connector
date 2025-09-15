#!/usr/bin/env python3
"""
Agent Performance Dashboard
Real-time performance tracking and analytics for the 8-agent development team.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from enum import Enum

from agent_activity_monitor import AgentActivityMonitor, AgentActivity, AgentPerformanceMetrics

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerformanceLevel(Enum):
    """Performance rating levels."""
    EXCELLENT = "excellent"  # 9-10
    GOOD = "good"           # 7-8
    AVERAGE = "average"     # 5-6
    POOR = "poor"          # 3-4
    CRITICAL = "critical"   # 1-2

@dataclass
class AgentPerformanceAnalysis:
    """Comprehensive agent performance analysis."""
    agent_name: str
    overall_score: float
    performance_level: PerformanceLevel
    efficiency_score: float
    quality_score: float
    collaboration_score: float
    responsiveness_score: float
    recent_trend: str  # "improving", "stable", "declining"
    strengths: List[str]
    improvement_areas: List[str]
    recommendations: List[str]
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['performance_level'] = self.performance_level.value
        return data

@dataclass
class TeamPerformanceSnapshot:
    """Team performance at a point in time."""
    timestamp: datetime
    team_efficiency: float
    team_quality: float
    team_collaboration: float
    active_agents_count: int
    total_tasks_completed: int
    average_task_duration: float
    critical_issues_count: int
    workflow_bottlenecks: List[str]
    top_performers: List[str]
    agents_needing_support: List[str]
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class AgentPerformanceDashboard:
    """Advanced performance analytics and dashboard system."""
    
    def __init__(self, monitor: AgentActivityMonitor):
        self.monitor = monitor
        self.data_dir = monitor.data_dir
        self.performance_history_file = self.data_dir / "performance_history.jsonl"
        self.analytics_cache_file = self.data_dir / "analytics_cache.json"
        
        # Performance thresholds
        self.thresholds = {
            "excellent_threshold": 9.0,
            "good_threshold": 7.0,
            "average_threshold": 5.0,
            "poor_threshold": 3.0,
            "responsiveness_target": 30.0,  # minutes
            "quality_target": 8.0,
            "efficiency_target": 7.5
        }
        
        # Team role weights for performance calculation
        self.role_weights = {
            "coordinator": {"quality": 0.4, "efficiency": 0.3, "collaboration": 0.3},
            "reviewer": {"quality": 0.5, "efficiency": 0.2, "collaboration": 0.3},
            "implementer": {"quality": 0.3, "efficiency": 0.4, "collaboration": 0.3},
            "specialist": {"quality": 0.4, "efficiency": 0.3, "collaboration": 0.3}
        }
    
    def analyze_agent_performance(self, agent_name: str, days: int = 7) -> AgentPerformanceAnalysis:
        """Generate comprehensive performance analysis for an agent."""
        
        if agent_name not in self.monitor.agent_metrics:
            raise ValueError(f"Agent {agent_name} not found")
        
        metrics = self.monitor.agent_metrics[agent_name]
        agent_role = self.monitor.agents[agent_name]["role"]
        
        # Get recent activities
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_activities = [
            activity for activity in self.monitor.activity_log
            if activity.agent_name == agent_name and activity.timestamp > cutoff_date
        ]
        
        # Calculate performance dimensions
        efficiency_score = self._calculate_efficiency_score(metrics, recent_activities)
        quality_score = self._calculate_quality_score(metrics, recent_activities)
        collaboration_score = self._calculate_collaboration_score(agent_name, recent_activities)
        responsiveness_score = self._calculate_responsiveness_score(metrics, recent_activities)
        
        # Calculate weighted overall score based on role
        weights = self.role_weights.get(agent_role, self.role_weights["implementer"])
        overall_score = (
            quality_score * weights["quality"] +
            efficiency_score * weights["efficiency"] +
            collaboration_score * weights["collaboration"]
        )
        
        # Determine performance level
        performance_level = self._get_performance_level(overall_score)
        
        # Analyze trends
        recent_trend = self._analyze_performance_trend(agent_name, days)
        
        # Generate insights
        strengths = self._identify_strengths(efficiency_score, quality_score, 
                                           collaboration_score, responsiveness_score)
        improvement_areas = self._identify_improvement_areas(efficiency_score, quality_score,
                                                           collaboration_score, responsiveness_score)
        recommendations = self._generate_recommendations(agent_name, agent_role, 
                                                       improvement_areas, recent_activities)
        
        return AgentPerformanceAnalysis(
            agent_name=agent_name,
            overall_score=overall_score,
            performance_level=performance_level,
            efficiency_score=efficiency_score,
            quality_score=quality_score,
            collaboration_score=collaboration_score,
            responsiveness_score=responsiveness_score,
            recent_trend=recent_trend,
            strengths=strengths,
            improvement_areas=improvement_areas,
            recommendations=recommendations
        )
    
    def _calculate_efficiency_score(self, metrics: AgentPerformanceMetrics, 
                                  activities: List[AgentActivity]) -> float:
        """Calculate agent efficiency score (1-10)."""
        
        if not activities:
            return 5.0  # Neutral score for no activity
        
        # Factor 1: Average task completion time
        completed_tasks = [a for a in activities if a.activity_type == "task_complete" and a.duration_minutes]
        if completed_tasks:
            avg_duration = sum(a.duration_minutes for a in completed_tasks) / len(completed_tasks)
            duration_score = max(1, min(10, 10 - (avg_duration - 60) / 30))  # Penalize >60min tasks
        else:
            duration_score = 5.0
        
        # Factor 2: Task completion rate
        total_tasks = len([a for a in activities if a.activity_type in ["task_start", "task_complete"]])
        completed_count = len([a for a in activities if a.activity_type == "task_complete"])
        completion_rate = completed_count / max(1, total_tasks) * 10
        
        # Factor 3: Activity frequency (consistency)
        if len(activities) > 0:
            activity_span = (max(a.timestamp for a in activities) - 
                           min(a.timestamp for a in activities)).total_seconds() / 3600
            frequency_score = min(10, len(activities) / max(1, activity_span) * 24)
        else:
            frequency_score = 1.0
        
        # Weighted combination
        efficiency_score = (duration_score * 0.4 + completion_rate * 0.4 + frequency_score * 0.2)
        return round(min(10, max(1, efficiency_score)), 1)
    
    def _calculate_quality_score(self, metrics: AgentPerformanceMetrics,
                               activities: List[AgentActivity]) -> float:
        """Calculate agent quality score (1-10)."""
        
        # Factor 1: Direct quality ratings from activities
        quality_activities = [a for a in activities if a.output_quality]
        if quality_activities:
            avg_quality = sum(a.output_quality for a in quality_activities) / len(quality_activities)
        else:
            avg_quality = metrics.quality_score if metrics.quality_score > 0 else 5.0
        
        # Factor 2: Review activities (higher weight for reviewers)
        review_activities = [a for a in activities if a.activity_type == "review"]
        review_bonus = min(1.0, len(review_activities) * 0.1)
        
        # Factor 3: Error-related activities (penalty)
        error_keywords = ["fix", "error", "bug", "issue", "problem"]
        error_activities = [a for a in activities if any(kw in a.description.lower() for kw in error_keywords)]
        error_penalty = min(2.0, len(error_activities) * 0.2)
        
        quality_score = avg_quality + review_bonus - error_penalty
        return round(min(10, max(1, quality_score)), 1)
    
    def _calculate_collaboration_score(self, agent_name: str, 
                                     activities: List[AgentActivity]) -> float:
        """Calculate agent collaboration score (1-10)."""
        
        # Factor 1: Cross-agent activities
        collaboration_keywords = ["review", "coordinate", "collaborate", "support", "help"]
        collab_activities = [a for a in activities 
                           if any(kw in a.description.lower() for kw in collaboration_keywords)]
        
        # Factor 2: Response to other agents (simulated - would need cross-reference)
        response_score = 5.0  # Default neutral
        
        # Factor 3: Workflow phase transitions (indicates working with others)
        unique_phases = len(set(a.workflow_phase for a in activities if a.workflow_phase))
        phase_diversity_score = min(10, unique_phases * 2)
        
        collaboration_score = (
            min(10, len(collab_activities) + 3) * 0.4 +
            response_score * 0.3 +
            phase_diversity_score * 0.3
        )
        
        return round(min(10, max(1, collaboration_score)), 1)
    
    def _calculate_responsiveness_score(self, metrics: AgentPerformanceMetrics,
                                      activities: List[AgentActivity]) -> float:
        """Calculate agent responsiveness score (1-10)."""
        
        if not activities:
            return 5.0
        
        # Factor 1: Time between activities (consistency)
        if len(activities) > 1:
            time_gaps = []
            sorted_activities = sorted(activities, key=lambda a: a.timestamp)
            for i in range(1, len(sorted_activities)):
                gap = (sorted_activities[i].timestamp - sorted_activities[i-1].timestamp).total_seconds() / 60
                time_gaps.append(gap)
            
            avg_gap = sum(time_gaps) / len(time_gaps)
            gap_score = max(1, min(10, 10 - (avg_gap - self.thresholds["responsiveness_target"]) / 30))
        else:
            gap_score = 5.0
        
        # Factor 2: Recent activity (last 24 hours)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_count = len([a for a in activities if a.timestamp > recent_cutoff])
        recency_score = min(10, recent_count + 2)
        
        responsiveness_score = (gap_score * 0.6 + recency_score * 0.4)
        return round(min(10, max(1, responsiveness_score)), 1)
    
    def _get_performance_level(self, score: float) -> PerformanceLevel:
        """Convert numeric score to performance level."""
        if score >= self.thresholds["excellent_threshold"]:
            return PerformanceLevel.EXCELLENT
        elif score >= self.thresholds["good_threshold"]:
            return PerformanceLevel.GOOD
        elif score >= self.thresholds["average_threshold"]:
            return PerformanceLevel.AVERAGE
        elif score >= self.thresholds["poor_threshold"]:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL
    
    def _analyze_performance_trend(self, agent_name: str, days: int) -> str:
        """Analyze performance trend over time."""
        
        # Get activities for trend analysis
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_activities = [
            activity for activity in self.monitor.activity_log
            if activity.agent_name == agent_name and activity.timestamp > cutoff_date
        ]
        
        if len(recent_activities) < 4:
            return "stable"  # Not enough data
        
        # Split into first half and second half
        mid_point = len(recent_activities) // 2
        first_half = recent_activities[:mid_point]
        second_half = recent_activities[mid_point:]
        
        # Calculate quality scores for each half
        def avg_quality(activities):
            quality_scores = [a.output_quality for a in activities if a.output_quality]
            return sum(quality_scores) / len(quality_scores) if quality_scores else 5.0
        
        first_quality = avg_quality(first_half)
        second_quality = avg_quality(second_half)
        
        if second_quality > first_quality + 0.5:
            return "improving"
        elif second_quality < first_quality - 0.5:
            return "declining"
        else:
            return "stable"
    
    def _identify_strengths(self, efficiency: float, quality: float, 
                          collaboration: float, responsiveness: float) -> List[str]:
        """Identify agent strengths based on scores."""
        strengths = []
        
        if efficiency >= 8.0:
            strengths.append("High efficiency and task completion speed")
        if quality >= 8.0:
            strengths.append("Excellent output quality and attention to detail")
        if collaboration >= 8.0:
            strengths.append("Strong collaboration and team coordination")
        if responsiveness >= 8.0:
            strengths.append("Highly responsive and consistent engagement")
        
        # Cross-dimensional strengths
        if efficiency >= 7.0 and quality >= 7.0:
            strengths.append("Balanced efficiency and quality delivery")
        if collaboration >= 7.0 and responsiveness >= 7.0:
            strengths.append("Reliable team player with consistent communication")
        
        return strengths if strengths else ["Consistent baseline performance"]
    
    def _identify_improvement_areas(self, efficiency: float, quality: float,
                                  collaboration: float, responsiveness: float) -> List[str]:
        """Identify areas for improvement."""
        improvements = []
        
        if efficiency < 6.0:
            improvements.append("Task completion efficiency and time management")
        if quality < 6.0:
            improvements.append("Output quality and thoroughness")
        if collaboration < 6.0:
            improvements.append("Team collaboration and communication")
        if responsiveness < 6.0:
            improvements.append("Response time and engagement consistency")
        
        # Specific improvement suggestions
        if efficiency < quality:
            improvements.append("Focus on optimizing workflow and reducing task duration")
        if collaboration < 5.0:
            improvements.append("Increase participation in team coordination activities")
        
        return improvements
    
    def _generate_recommendations(self, agent_name: str, role: str, 
                                improvement_areas: List[str], 
                                activities: List[AgentActivity]) -> List[str]:
        """Generate specific recommendations for improvement."""
        recommendations = []
        
        # Role-specific recommendations
        if role == "coordinator":
            if "team collaboration" in " ".join(improvement_areas).lower():
                recommendations.append("Schedule regular team coordination meetings")
                recommendations.append("Implement more structured task delegation")
        
        elif role == "reviewer":
            if "output quality" in " ".join(improvement_areas).lower():
                recommendations.append("Develop more comprehensive review checklists")
                recommendations.append("Allocate more time for thorough code reviews")
        
        elif role == "implementer":
            if "task completion efficiency" in " ".join(improvement_areas).lower():
                recommendations.append("Break down large tasks into smaller increments")
                recommendations.append("Focus on test-driven development for faster iterations")
        
        elif role == "specialist":
            if "team collaboration" in " ".join(improvement_areas).lower():
                recommendations.append("Proactively share specialized knowledge with team")
                recommendations.append("Create documentation for specialized processes")
        
        # Activity-based recommendations
        recent_error_count = len([a for a in activities if "error" in a.description.lower() or "fix" in a.description.lower()])
        if recent_error_count > 3:
            recommendations.append("Implement more thorough testing before task completion")
            recommendations.append("Consider pair programming for complex tasks")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Continue current performance level and seek new challenges")
            recommendations.append("Consider mentoring other team members")
        
        return recommendations
    
    def generate_team_performance_snapshot(self) -> TeamPerformanceSnapshot:
        """Generate current team performance snapshot."""
        
        now = datetime.now()
        
        # Calculate team-level metrics
        all_metrics = list(self.monitor.agent_metrics.values())
        
        team_efficiency = sum(m.avg_task_duration for m in all_metrics if m.avg_task_duration > 0) / max(1, len([m for m in all_metrics if m.avg_task_duration > 0]))
        team_quality = sum(m.quality_score for m in all_metrics if m.quality_score > 0) / max(1, len([m for m in all_metrics if m.quality_score > 0]))
        
        # Active agents
        active_agents = [m for m in all_metrics if m.status == "active"]
        active_agents_count = len(active_agents)
        
        # Total tasks
        total_tasks_completed = sum(m.tasks_completed for m in all_metrics)
        
        # Average task duration (efficiency inverse)
        durations = [m.avg_task_duration for m in all_metrics if m.avg_task_duration > 0]
        average_task_duration = sum(durations) / len(durations) if durations else 0
        
        # Collaboration score (simplified)
        team_collaboration = 7.5  # Would calculate from cross-agent activities
        
        # Issues and bottlenecks
        issues = self.monitor.detect_issues()
        critical_issues_count = len([i for i in issues if i.get("severity") == "high"])
        
        workflow_bottlenecks = [i["phase"] for i in issues if i.get("type") == "workflow_bottleneck"]
        
        # Performance analysis for ranking
        performance_scores = {}
        for agent_name in self.monitor.agents:
            try:
                analysis = self.analyze_agent_performance(agent_name)
                performance_scores[agent_name] = analysis.overall_score
            except:
                performance_scores[agent_name] = 5.0
        
        # Top performers and those needing support
        sorted_agents = sorted(performance_scores.items(), key=lambda x: x[1], reverse=True)
        top_performers = [agent for agent, score in sorted_agents[:3] if score >= 7.0]
        agents_needing_support = [agent for agent, score in sorted_agents if score < 5.0]
        
        return TeamPerformanceSnapshot(
            timestamp=now,
            team_efficiency=round(10 - (average_task_duration / 60), 1) if average_task_duration else 8.0,
            team_quality=round(team_quality, 1),
            team_collaboration=team_collaboration,
            active_agents_count=active_agents_count,
            total_tasks_completed=total_tasks_completed,
            average_task_duration=round(average_task_duration, 1),
            critical_issues_count=critical_issues_count,
            workflow_bottlenecks=workflow_bottlenecks,
            top_performers=top_performers,
            agents_needing_support=agents_needing_support
        )
    
    def save_performance_snapshot(self, snapshot: TeamPerformanceSnapshot):
        """Save performance snapshot to history."""
        try:
            with open(self.performance_history_file, 'a') as f:
                f.write(json.dumps(snapshot.to_dict()) + '\n')
            logger.info("Saved performance snapshot")
        except Exception as e:
            logger.error(f"Error saving performance snapshot: {e}")
    
    def get_performance_trends(self, days: int = 30) -> Dict:
        """Get performance trends over time."""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Load historical snapshots
        snapshots = []
        if self.performance_history_file.exists():
            try:
                with open(self.performance_history_file, 'r') as f:
                    for line in f:
                        data = json.loads(line.strip())
                        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                        if data['timestamp'] > cutoff_date:
                            snapshots.append(data)
            except Exception as e:
                logger.error(f"Error loading performance history: {e}")
        
        if not snapshots:
            return {"error": "No historical data available"}
        
        # Calculate trends
        efficiency_trend = [s['team_efficiency'] for s in snapshots]
        quality_trend = [s['team_quality'] for s in snapshots]
        collaboration_trend = [s['team_collaboration'] for s in snapshots]
        
        return {
            "period_days": days,
            "snapshots_count": len(snapshots),
            "efficiency_trend": {
                "values": efficiency_trend,
                "average": round(sum(efficiency_trend) / len(efficiency_trend), 1),
                "trend": "improving" if efficiency_trend[-1] > efficiency_trend[0] else "declining"
            },
            "quality_trend": {
                "values": quality_trend,
                "average": round(sum(quality_trend) / len(quality_trend), 1),
                "trend": "improving" if quality_trend[-1] > quality_trend[0] else "declining"
            },
            "collaboration_trend": {
                "values": collaboration_trend,
                "average": round(sum(collaboration_trend) / len(collaboration_trend), 1),
                "trend": "improving" if collaboration_trend[-1] > collaboration_trend[0] else "declining"
            }
        }

def main():
    """Test the performance dashboard."""
    
    # Initialize monitor and dashboard
    from agent_activity_monitor import AgentActivityMonitor
    monitor = AgentActivityMonitor()
    dashboard = AgentPerformanceDashboard(monitor)
    
    # Simulate some activities for testing
    monitor.log_activity("ProjectManager", "task_start", "Coordinating Phase 4B validation", 
                        workflow_phase="coordination")
    monitor.log_activity("QAEngineer", "review", "Reviewed test framework completeness",
                        duration_minutes=35, output_quality=9, workflow_phase="qa_review")
    monitor.log_activity("Implementer", "task_complete", "Fixed performance optimization issues",
                        duration_minutes=85, output_quality=8, workflow_phase="implementation")
    monitor.log_activity("SecurityEngineer", "review", "Security audit of monitoring system",
                        duration_minutes=45, output_quality=9, workflow_phase="security_review")
    
    # Generate individual performance analysis
    print("🎯 Individual Agent Performance Analysis:")
    for agent_name in ["ProjectManager", "QAEngineer", "Implementer", "SecurityEngineer"]:
        try:
            analysis = dashboard.analyze_agent_performance(agent_name)
            print(f"\n📊 {agent_name} ({analysis.performance_level.value.upper()}):")
            print(f"   Overall Score: {analysis.overall_score}/10")
            print(f"   Efficiency: {analysis.efficiency_score}/10")
            print(f"   Quality: {analysis.quality_score}/10") 
            print(f"   Collaboration: {analysis.collaboration_score}/10")
            print(f"   Trend: {analysis.recent_trend}")
            if analysis.strengths:
                print(f"   Strengths: {', '.join(analysis.strengths[:2])}")
            if analysis.improvement_areas:
                print(f"   Improvements: {', '.join(analysis.improvement_areas[:2])}")
        except Exception as e:
            print(f"   Error analyzing {agent_name}: {e}")
    
    # Generate team snapshot
    print("\n\n🏢 Team Performance Snapshot:")
    snapshot = dashboard.generate_team_performance_snapshot()
    print(f"   Team Efficiency: {snapshot.team_efficiency}/10")
    print(f"   Team Quality: {snapshot.team_quality}/10")
    print(f"   Active Agents: {snapshot.active_agents_count}/{len(monitor.agents)}")
    print(f"   Tasks Completed: {snapshot.total_tasks_completed}")
    print(f"   Critical Issues: {snapshot.critical_issues_count}")
    if snapshot.top_performers:
        print(f"   Top Performers: {', '.join(snapshot.top_performers)}")
    if snapshot.agents_needing_support:
        print(f"   Need Support: {', '.join(snapshot.agents_needing_support)}")
    
    # Save snapshot
    dashboard.save_performance_snapshot(snapshot)
    
    print("\n✅ Performance Dashboard Test Complete")

if __name__ == "__main__":
    main()