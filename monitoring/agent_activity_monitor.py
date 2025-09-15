#!/usr/bin/env python3
"""
Agent Activity Monitor
Real-time tracking of agent engagement, outputs, and workflow progress.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class AgentActivity:
    """Individual agent activity record."""
    agent_name: str
    timestamp: datetime
    activity_type: str  # "task_start", "task_complete", "review", "output", "idle"
    description: str
    duration_minutes: Optional[float] = None
    output_quality: Optional[int] = None  # 1-10 scale
    workflow_phase: Optional[str] = None
    task_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass 
class AgentPerformanceMetrics:
    """Agent performance tracking."""
    agent_name: str
    tasks_completed: int = 0
    avg_task_duration: float = 0.0
    quality_score: float = 0.0
    responsiveness: float = 0.0  # Response time in minutes
    collaboration_score: float = 0.0
    last_active: Optional[datetime] = None
    status: str = "idle"  # "active", "idle", "blocked", "offline"
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.last_active:
            data['last_active'] = self.last_active.isoformat()
        return data

class AgentActivityMonitor:
    """Centralized agent activity monitoring system."""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Activity log
        self.activity_log: List[AgentActivity] = []
        self.activity_file = self.data_dir / "agent_activities.jsonl"
        
        # Performance metrics
        self.agent_metrics: Dict[str, AgentPerformanceMetrics] = {}
        self.metrics_file = self.data_dir / "agent_metrics.json"
        
        # Team configuration from team_startup.yaml
        self.agents = {
            # Coordinator
            "ProjectManager": {"role": "coordinator", "priority": 1},
            
            # Reviewers
            "Architect": {"role": "reviewer", "priority": 2},
            "SecurityEngineer": {"role": "reviewer", "priority": 2},
            "QAEngineer": {"role": "reviewer", "priority": 2},
            
            # Implementers  
            "Implementer": {"role": "implementer", "priority": 3},
            "DevOpsEngineer": {"role": "implementer", "priority": 3},
            
            # Specialists
            "PerformanceEngineer": {"role": "specialist", "priority": 4},
            "DocumentationEngineer": {"role": "specialist", "priority": 4}
        }
        
        # Initialize metrics for all agents
        for agent_name in self.agents:
            if agent_name not in self.agent_metrics:
                self.agent_metrics[agent_name] = AgentPerformanceMetrics(agent_name=agent_name)
        
        self._load_existing_data()
    
    def _load_existing_data(self):
        """Load existing activity and metrics data."""
        # Load activity log
        if self.activity_file.exists():
            try:
                with open(self.activity_file, 'r') as f:
                    for line in f:
                        data = json.loads(line.strip())
                        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                        activity = AgentActivity(**data)
                        self.activity_log.append(activity)
                logger.info(f"Loaded {len(self.activity_log)} activity records")
            except Exception as e:
                logger.error(f"Error loading activity log: {e}")
        
        # Load metrics
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    for agent_name, metrics_data in data.items():
                        if 'last_active' in metrics_data and metrics_data['last_active']:
                            metrics_data['last_active'] = datetime.fromisoformat(metrics_data['last_active'])
                        self.agent_metrics[agent_name] = AgentPerformanceMetrics(**metrics_data)
                logger.info(f"Loaded metrics for {len(self.agent_metrics)} agents")
            except Exception as e:
                logger.error(f"Error loading metrics: {e}")
    
    def log_activity(self, agent_name: str, activity_type: str, description: str, 
                     duration_minutes: float = None, output_quality: int = None,
                     workflow_phase: str = None, task_id: str = None):
        """Log agent activity."""
        activity = AgentActivity(
            agent_name=agent_name,
            timestamp=datetime.now(),
            activity_type=activity_type,
            description=description,
            duration_minutes=duration_minutes,
            output_quality=output_quality,
            workflow_phase=workflow_phase,
            task_id=task_id
        )
        
        self.activity_log.append(activity)
        self._update_agent_metrics(activity)
        self._save_activity(activity)
        
        logger.info(f"Logged activity: {agent_name} - {activity_type} - {description}")
    
    def _update_agent_metrics(self, activity: AgentActivity):
        """Update agent performance metrics based on activity."""
        agent_name = activity.agent_name
        metrics = self.agent_metrics[agent_name]
        
        # Update last active time
        metrics.last_active = activity.timestamp
        
        # Update status based on activity type
        if activity.activity_type in ["task_start", "output", "review"]:
            metrics.status = "active"
        elif activity.activity_type == "task_complete":
            metrics.status = "idle"
            metrics.tasks_completed += 1
            
            # Update average duration if provided
            if activity.duration_minutes:
                current_avg = metrics.avg_task_duration
                completed_tasks = metrics.tasks_completed
                metrics.avg_task_duration = ((current_avg * (completed_tasks - 1)) + activity.duration_minutes) / completed_tasks
        
        # Update quality score if provided
        if activity.output_quality:
            current_quality = metrics.quality_score
            if current_quality == 0:
                metrics.quality_score = activity.output_quality
            else:
                # Weighted average with recent bias
                metrics.quality_score = (current_quality * 0.7) + (activity.output_quality * 0.3)
    
    def _save_activity(self, activity: AgentActivity):
        """Save activity to persistent storage."""
        try:
            with open(self.activity_file, 'a') as f:
                f.write(json.dumps(activity.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"Error saving activity: {e}")
    
    def save_metrics(self):
        """Save current metrics to file."""
        try:
            metrics_data = {name: metrics.to_dict() for name, metrics in self.agent_metrics.items()}
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            logger.info("Saved agent metrics")
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
    
    def get_agent_status(self, agent_name: str) -> Dict:
        """Get current status for specific agent."""
        if agent_name not in self.agent_metrics:
            return {"error": f"Agent {agent_name} not found"}
        
        metrics = self.agent_metrics[agent_name]
        recent_activities = [
            activity for activity in self.activity_log[-20:]
            if activity.agent_name == agent_name
        ]
        
        return {
            "agent": agent_name,
            "role": self.agents[agent_name]["role"],
            "priority": self.agents[agent_name]["priority"], 
            "status": metrics.status,
            "last_active": metrics.last_active.isoformat() if metrics.last_active else None,
            "performance": {
                "tasks_completed": metrics.tasks_completed,
                "avg_duration_minutes": round(metrics.avg_task_duration, 1),
                "quality_score": round(metrics.quality_score, 1),
                "responsiveness": round(metrics.responsiveness, 1)
            },
            "recent_activities": [
                {
                    "timestamp": activity.timestamp.isoformat(),
                    "type": activity.activity_type,
                    "description": activity.description,
                    "duration": activity.duration_minutes
                }
                for activity in recent_activities[-5:]
            ]
        }
    
    def get_team_dashboard(self) -> Dict:
        """Generate comprehensive team monitoring dashboard."""
        now = datetime.now()
        
        # Team overview
        active_agents = sum(1 for m in self.agent_metrics.values() if m.status == "active")
        idle_agents = sum(1 for m in self.agent_metrics.values() if m.status == "idle")
        offline_agents = sum(1 for m in self.agent_metrics.values() 
                           if m.last_active and (now - m.last_active) > timedelta(hours=24))
        
        # Performance summary
        total_tasks = sum(m.tasks_completed for m in self.agent_metrics.values())
        avg_quality = sum(m.quality_score for m in self.agent_metrics.values()) / len(self.agent_metrics)
        
        # Recent activity (last 2 hours)
        recent_cutoff = now - timedelta(hours=2)
        recent_activities = [
            activity for activity in self.activity_log
            if activity.timestamp > recent_cutoff
        ]
        
        # Agent statuses by role
        agents_by_role = {}
        for agent_name, agent_info in self.agents.items():
            role = agent_info["role"]
            if role not in agents_by_role:
                agents_by_role[role] = []
            agents_by_role[role].append({
                "name": agent_name,
                "status": self.agent_metrics[agent_name].status,
                "last_active": self.agent_metrics[agent_name].last_active.isoformat() 
                              if self.agent_metrics[agent_name].last_active else None,
                "tasks_completed": self.agent_metrics[agent_name].tasks_completed,
                "quality_score": round(self.agent_metrics[agent_name].quality_score, 1)
            })
        
        return {
            "timestamp": now.isoformat(),
            "team_overview": {
                "total_agents": len(self.agents),
                "active_agents": active_agents,
                "idle_agents": idle_agents,
                "offline_agents": offline_agents,
                "total_tasks_completed": total_tasks,
                "avg_team_quality": round(avg_quality, 1)
            },
            "recent_activity": {
                "period_hours": 2,
                "activity_count": len(recent_activities),
                "activities": [
                    {
                        "agent": activity.agent_name,
                        "type": activity.activity_type,
                        "description": activity.description,
                        "timestamp": activity.timestamp.isoformat()
                    }
                    for activity in recent_activities[-10:]
                ]
            },
            "agents_by_role": agents_by_role
        }
    
    def detect_issues(self) -> List[Dict]:
        """Detect potential team coordination issues."""
        issues = []
        now = datetime.now()
        
        # Check for inactive agents
        for agent_name, metrics in self.agent_metrics.items():
            if metrics.last_active:
                inactive_duration = now - metrics.last_active
                if inactive_duration > timedelta(hours=4):
                    issues.append({
                        "type": "inactive_agent",
                        "severity": "medium" if inactive_duration < timedelta(days=1) else "high",
                        "agent": agent_name,
                        "message": f"{agent_name} inactive for {inactive_duration.total_seconds() / 3600:.1f} hours",
                        "recommendation": "Check agent status and workload assignment"
                    })
        
        # Check for low quality scores
        for agent_name, metrics in self.agent_metrics.items():
            if metrics.quality_score > 0 and metrics.quality_score < 6:
                issues.append({
                    "type": "low_quality",
                    "severity": "high",
                    "agent": agent_name,
                    "message": f"{agent_name} quality score: {metrics.quality_score:.1f}/10",
                    "recommendation": "Review recent outputs and provide feedback"
                })
        
        # Check for workflow bottlenecks
        recent_activities = [a for a in self.activity_log if (now - a.timestamp) < timedelta(hours=4)]
        phase_counts = {}
        for activity in recent_activities:
            if activity.workflow_phase:
                phase_counts[activity.workflow_phase] = phase_counts.get(activity.workflow_phase, 0) + 1
        
        # Detect if too many activities stuck in one phase
        for phase, count in phase_counts.items():
            if count > 5:
                issues.append({
                    "type": "workflow_bottleneck",
                    "severity": "medium",
                    "phase": phase,
                    "message": f"High activity in {phase} phase ({count} activities)",
                    "recommendation": "Check for blockers or resource constraints in this phase"
                })
        
        return issues

def main():
    """Test the monitoring system."""
    monitor = AgentActivityMonitor()
    
    # Simulate some agent activities
    monitor.log_activity("ProjectManager", "task_start", "Initiated Phase 4B validation", 
                        workflow_phase="execution")
    monitor.log_activity("QAEngineer", "review", "Reviewed test framework implementation",
                        duration_minutes=45, output_quality=9, workflow_phase="qa_review")
    monitor.log_activity("Implementer", "task_complete", "Fixed integration test issues",
                        duration_minutes=120, output_quality=8, workflow_phase="implementation")
    
    # Generate dashboard
    dashboard = monitor.get_team_dashboard()
    print("📊 Team Dashboard:")
    print(json.dumps(dashboard, indent=2))
    
    # Check for issues
    issues = monitor.detect_issues()
    if issues:
        print("\n⚠️  Detected Issues:")
        for issue in issues:
            print(f"- {issue['type']}: {issue['message']}")
    
    # Save metrics
    monitor.save_metrics()

if __name__ == "__main__":
    main()