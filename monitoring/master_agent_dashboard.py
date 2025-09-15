#!/usr/bin/env python3
"""
Master Agent Dashboard
Integrated monitoring system combining all agent monitoring capabilities.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from agent_activity_monitor import AgentActivityMonitor
from agent_performance_dashboard import AgentPerformanceDashboard
from team_coordination_dashboard import TeamCoordinationDashboard
from agent_accountability_system import AgentAccountabilitySystem

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MasterAgentDashboard:
    """Master dashboard integrating all agent monitoring capabilities."""
    
    def __init__(self, data_dir: Path = None):
        """Initialize the master dashboard with all monitoring components."""
        
        self.data_dir = data_dir or Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize all monitoring components
        self.activity_monitor = AgentActivityMonitor(self.data_dir)
        self.performance_dashboard = AgentPerformanceDashboard(self.activity_monitor)
        self.coordination_dashboard = TeamCoordinationDashboard(
            self.activity_monitor, self.performance_dashboard
        )
        self.accountability_system = AgentAccountabilitySystem(
            self.activity_monitor, self.performance_dashboard, self.coordination_dashboard
        )
        
        self.dashboard_history_file = self.data_dir / "master_dashboard_history.jsonl"
    
    def get_comprehensive_status(self) -> Dict:
        """Get comprehensive status across all monitoring dimensions."""
        
        try:
            # Get team dashboard from activity monitor
            team_dashboard = self.activity_monitor.get_team_dashboard()
            
            # Get team performance snapshot
            performance_snapshot = self.performance_dashboard.generate_team_performance_snapshot()
            
            # Get coordination state
            coordination_state = self.coordination_dashboard.analyze_current_coordination()
            
            # Get accountability snapshot
            accountability_snapshot = self.accountability_system.generate_team_accountability_snapshot()
            
            # Integrate all data
            comprehensive_status = {
                "timestamp": datetime.now().isoformat(),
                "overview": {
                    "total_agents": team_dashboard["team_overview"]["total_agents"],
                    "active_agents": team_dashboard["team_overview"]["active_agents"],
                    "idle_agents": team_dashboard["team_overview"]["idle_agents"],
                    "offline_agents": team_dashboard["team_overview"]["offline_agents"],
                    "total_tasks_completed": team_dashboard["team_overview"]["total_tasks_completed"],
                    "team_velocity": coordination_state.team_velocity,
                    "overall_accountability_score": accountability_snapshot.overall_accountability_score
                },
                "performance": {
                    "team_efficiency": performance_snapshot.team_efficiency,
                    "team_quality": performance_snapshot.team_quality,
                    "team_collaboration": performance_snapshot.team_collaboration,
                    "average_task_duration": performance_snapshot.average_task_duration,
                    "top_performers": performance_snapshot.top_performers,
                    "agents_needing_support": performance_snapshot.agents_needing_support
                },
                "coordination": {
                    "status": coordination_state.coordination_status.value,
                    "active_phases_count": len(coordination_state.active_phases),
                    "workflow_bottlenecks_count": len(coordination_state.workflow_bottlenecks),
                    "coordination_issues_count": len(coordination_state.coordination_issues),
                    "resource_conflicts_count": len(coordination_state.resource_conflicts),
                    "communication_gaps_count": len(coordination_state.communication_gaps)
                },
                "accountability": {
                    "average_completion_rate": accountability_snapshot.average_completion_rate,
                    "total_active_commitments": accountability_snapshot.total_active_commitments,
                    "total_overdue_commitments": accountability_snapshot.total_overdue_commitments,
                    "agents_by_level": accountability_snapshot.agents_by_level,
                    "risks_count": len(accountability_snapshot.accountability_risks)
                },
                "issues": {
                    "critical_performance_issues": performance_snapshot.critical_issues_count,
                    "coordination_issues": coordination_state.coordination_issues,
                    "accountability_risks": accountability_snapshot.accountability_risks,
                    "activity_issues": self.activity_monitor.detect_issues()
                },
                "recommendations": {
                    "coordination": coordination_state.recommended_actions,
                    "accountability": accountability_snapshot.intervention_recommendations
                }
            }
            
            return comprehensive_status
            
        except Exception as e:
            logger.error(f"Error generating comprehensive status: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def get_agent_detailed_report(self, agent_name: str) -> Dict:
        """Get detailed report for a specific agent across all dimensions."""
        
        try:
            # Get agent status from activity monitor
            agent_status = self.activity_monitor.get_agent_status(agent_name)
            
            # Get performance analysis
            performance_analysis = self.performance_dashboard.analyze_agent_performance(agent_name)
            
            # Get agent workload from coordination
            coordination_state = self.coordination_dashboard.analyze_current_coordination()
            agent_workload = next(
                (w for w in coordination_state.agent_workloads if w.agent_name == agent_name), 
                None
            )
            
            # Get accountability report
            accountability_report = self.accountability_system.generate_agent_accountability_report(agent_name)
            
            # Integrate all data
            detailed_report = {
                "agent": agent_name,
                "timestamp": datetime.now().isoformat(),
                "basic_info": {
                    "role": agent_status["role"],
                    "priority": agent_status["priority"],
                    "status": agent_status["status"],
                    "last_active": agent_status["last_active"]
                },
                "performance": {
                    "overall_score": performance_analysis.overall_score,
                    "performance_level": performance_analysis.performance_level.value,
                    "efficiency_score": performance_analysis.efficiency_score,
                    "quality_score": performance_analysis.quality_score,
                    "collaboration_score": performance_analysis.collaboration_score,
                    "responsiveness_score": performance_analysis.responsiveness_score,
                    "recent_trend": performance_analysis.recent_trend,
                    "strengths": performance_analysis.strengths,
                    "improvement_areas": performance_analysis.improvement_areas,
                    "recommendations": performance_analysis.recommendations
                },
                "workload": {
                    "current_tasks": agent_workload.current_tasks if agent_workload else [],
                    "task_count": agent_workload.task_count if agent_workload else 0,
                    "utilization_percentage": agent_workload.utilization_percentage if agent_workload else 0,
                    "estimated_capacity": agent_workload.estimated_capacity if agent_workload else 5,
                    "current_phase": agent_workload.current_phase if agent_workload else None,
                    "skill_areas": agent_workload.skill_areas if agent_workload else []
                },
                "accountability": {
                    "accountability_level": accountability_report.accountability_level.value,
                    "overall_score": accountability_report.overall_score,
                    "commitment_completion_rate": accountability_report.metrics.commitment_completion_rate,
                    "average_delay_days": accountability_report.metrics.average_delay_days,
                    "reliability_score": accountability_report.metrics.reliability_score,
                    "active_commitments_count": len(accountability_report.active_commitments),
                    "overdue_commitments_count": len(accountability_report.overdue_commitments),
                    "recent_completions_count": len(accountability_report.recent_completions),
                    "strengths": accountability_report.strengths,
                    "improvement_areas": accountability_report.improvement_areas,
                    "recommendations": accountability_report.recommendations,
                    "next_review_date": accountability_report.next_review_date.isoformat()
                },
                "recent_activities": agent_status["recent_activities"]
            }
            
            return detailed_report
            
        except Exception as e:
            logger.error(f"Error generating detailed report for {agent_name}: {e}")
            return {"error": str(e), "agent": agent_name, "timestamp": datetime.now().isoformat()}
    
    def generate_executive_summary(self) -> Dict:
        """Generate executive summary for management review."""
        
        try:
            comprehensive_status = self.get_comprehensive_status()
            
            # Calculate key metrics
            team_health_score = (
                comprehensive_status["performance"]["team_efficiency"] * 0.25 +
                comprehensive_status["performance"]["team_quality"] * 0.25 +
                comprehensive_status["overview"]["overall_accountability_score"] * 0.25 +
                (100 if comprehensive_status["coordination"]["status"] == "optimal" else
                 80 if comprehensive_status["coordination"]["status"] == "good" else
                 60 if comprehensive_status["coordination"]["status"] == "attention" else 40) * 0.25
            )
            
            # Determine overall status
            if team_health_score >= 85:
                overall_status = "excellent"
                status_color = "🟢"
            elif team_health_score >= 70:
                overall_status = "good"
                status_color = "🟡"
            elif team_health_score >= 55:
                overall_status = "needs_attention"
                status_color = "🟠"
            else:
                overall_status = "critical"
                status_color = "🔴"
            
            # Count total issues
            total_issues = (
                comprehensive_status["issues"]["critical_performance_issues"] +
                comprehensive_status["coordination"]["coordination_issues_count"] +
                comprehensive_status["accountability"]["risks_count"] +
                len(comprehensive_status["issues"]["activity_issues"])
            )
            
            # Key highlights
            highlights = []
            
            # Performance highlights
            if comprehensive_status["performance"]["team_efficiency"] >= 8.5:
                highlights.append("🚀 Excellent team efficiency")
            if comprehensive_status["performance"]["team_quality"] >= 8.5:
                highlights.append("⭐ High quality delivery")
            
            # Coordination highlights
            if comprehensive_status["coordination"]["status"] == "optimal":
                highlights.append("🎯 Optimal team coordination")
            elif comprehensive_status["coordination"]["workflow_bottlenecks_count"] > 3:
                highlights.append("⚠️ Multiple workflow bottlenecks")
            
            # Accountability highlights
            if comprehensive_status["accountability"]["average_completion_rate"] >= 90:
                highlights.append("✅ Excellent commitment delivery")
            elif comprehensive_status["accountability"]["total_overdue_commitments"] > 5:
                highlights.append("🔴 High overdue commitments")
            
            # Top concerns
            concerns = []
            
            if comprehensive_status["overview"]["offline_agents"] > 2:
                concerns.append(f"👤 {comprehensive_status['overview']['offline_agents']} agents offline")
            
            if comprehensive_status["coordination"]["resource_conflicts_count"] > 0:
                concerns.append(f"⚡ {comprehensive_status['coordination']['resource_conflicts_count']} resource conflicts")
            
            if comprehensive_status["accountability"]["total_overdue_commitments"] > 0:
                concerns.append(f"📅 {comprehensive_status['accountability']['total_overdue_commitments']} overdue commitments")
            
            # Generate recommendations
            priority_actions = []
            
            # Combine all recommendations
            all_recommendations = (
                comprehensive_status["recommendations"]["coordination"] +
                comprehensive_status["recommendations"]["accountability"]
            )
            
            # Prioritize top 5 recommendations
            priority_actions = all_recommendations[:5] if all_recommendations else ["Continue monitoring team performance"]
            
            executive_summary = {
                "timestamp": datetime.now().isoformat(),
                "overall_status": overall_status,
                "team_health_score": round(team_health_score, 1),
                "status_indicator": status_color,
                "key_metrics": {
                    "total_agents": comprehensive_status["overview"]["total_agents"],
                    "active_agents": comprehensive_status["overview"]["active_agents"],
                    "team_velocity": comprehensive_status["overview"]["team_velocity"],
                    "team_efficiency": comprehensive_status["performance"]["team_efficiency"],
                    "team_quality": comprehensive_status["performance"]["team_quality"],
                    "accountability_score": comprehensive_status["overview"]["overall_accountability_score"],
                    "coordination_status": comprehensive_status["coordination"]["status"]
                },
                "highlights": highlights,
                "concerns": concerns,
                "total_issues": total_issues,
                "priority_actions": priority_actions,
                "next_review_recommended": (datetime.now() + timedelta(days=7)).isoformat(),
                "detailed_breakdown": {
                    "performance_issues": comprehensive_status["issues"]["critical_performance_issues"],
                    "coordination_issues": comprehensive_status["coordination"]["coordination_issues_count"],
                    "accountability_risks": comprehensive_status["accountability"]["risks_count"],
                    "activity_issues": len(comprehensive_status["issues"]["activity_issues"])
                }
            }
            
            return executive_summary
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def save_dashboard_snapshot(self):
        """Save current dashboard state to history."""
        try:
            comprehensive_status = self.get_comprehensive_status()
            
            with open(self.dashboard_history_file, 'a') as f:
                f.write(json.dumps(comprehensive_status) + '\n')
            
            # Also save individual component snapshots
            performance_snapshot = self.performance_dashboard.generate_team_performance_snapshot()
            self.performance_dashboard.save_performance_snapshot(performance_snapshot)
            
            coordination_state = self.coordination_dashboard.analyze_current_coordination()
            self.coordination_dashboard.save_coordination_state(coordination_state)
            
            accountability_snapshot = self.accountability_system.generate_team_accountability_snapshot()
            self.accountability_system.save_accountability_snapshot(accountability_snapshot)
            
            logger.info("Saved complete dashboard snapshot")
            
        except Exception as e:
            logger.error(f"Error saving dashboard snapshot: {e}")
    
    def run_automated_monitoring(self, interval_minutes: int = 30):
        """Run automated monitoring with specified interval."""
        
        logger.info(f"Starting automated monitoring with {interval_minutes} minute intervals")
        
        try:
            while True:
                # Generate and save snapshots
                self.save_dashboard_snapshot()
                
                # Check for critical issues that need immediate attention
                comprehensive_status = self.get_comprehensive_status()
                
                critical_issues = []
                if comprehensive_status["issues"]["critical_performance_issues"] > 0:
                    critical_issues.append("Critical performance issues detected")
                
                if comprehensive_status["coordination"]["status"] == "critical":
                    critical_issues.append("Critical coordination issues detected")
                
                if comprehensive_status["accountability"]["total_overdue_commitments"] > 10:
                    critical_issues.append("High number of overdue commitments")
                
                if critical_issues:
                    logger.warning(f"CRITICAL ISSUES DETECTED: {'; '.join(critical_issues)}")
                
                # Wait for next interval
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            logger.info("Automated monitoring stopped")
        except Exception as e:
            logger.error(f"Error in automated monitoring: {e}")

def main():
    """Test the master agent dashboard."""
    
    print("🎛️  Master Agent Dashboard - Comprehensive Team Monitoring")
    
    # Initialize master dashboard
    dashboard = MasterAgentDashboard()
    
    # Simulate some activities for testing
    print("\n📝 Simulating Team Activities...")
    
    # Project coordination
    dashboard.activity_monitor.log_activity(
        "ProjectManager", "task_start", "Coordinating Phase 4B validation execution", 
        workflow_phase="coordination"
    )
    
    # Review activities
    dashboard.activity_monitor.log_activity(
        "Architect", "review", "Architecture review of monitoring system",
        duration_minutes=45, output_quality=9, workflow_phase="architecture"
    )
    
    dashboard.activity_monitor.log_activity(
        "SecurityEngineer", "review", "Security audit of agent monitoring framework",
        duration_minutes=60, output_quality=8, workflow_phase="security_review"
    )
    
    dashboard.activity_monitor.log_activity(
        "QAEngineer", "review", "Quality review of monitoring components",
        duration_minutes=35, output_quality=9, workflow_phase="qa_review"
    )
    
    # Implementation activities
    dashboard.activity_monitor.log_activity(
        "Implementer", "task_complete", "Completed agent monitoring system implementation",
        duration_minutes=180, output_quality=8, workflow_phase="implementation"
    )
    
    dashboard.activity_monitor.log_activity(
        "DevOpsEngineer", "output", "Set up monitoring infrastructure deployment",
        workflow_phase="deployment"
    )
    
    # Specialist activities
    dashboard.activity_monitor.log_activity(
        "PerformanceEngineer", "output", "Analyzed monitoring system performance metrics",
        workflow_phase="validation"
    )
    
    dashboard.activity_monitor.log_activity(
        "DocumentationEngineer", "task_complete", "Completed monitoring system documentation",
        duration_minutes=90, output_quality=8, workflow_phase="documentation"
    )
    
    # Create some test commitments
    dashboard.accountability_system.create_commitment(
        agent_name="ProjectManager",
        description="Complete Phase 4B coordination",
        target_date=datetime.now() + timedelta(days=7),
        success_criteria=["All validation complete", "Results documented"],
        estimated_hours=20.0
    )
    
    dashboard.accountability_system.create_commitment(
        agent_name="QAEngineer",
        description="Execute comprehensive testing suite",
        target_date=datetime.now() + timedelta(days=5),
        success_criteria=["All tests pass", "Quality metrics met"],
        estimated_hours=15.0
    )
    
    print("✅ Activities simulated")
    
    # Generate comprehensive status
    print("\n📊 Comprehensive Team Status:")
    comprehensive_status = dashboard.get_comprehensive_status()
    
    print(f"   Total Agents: {comprehensive_status['overview']['total_agents']}")
    print(f"   Active Agents: {comprehensive_status['overview']['active_agents']}")
    print(f"   Team Velocity: {comprehensive_status['overview']['team_velocity']} tasks/hour")
    print(f"   Team Efficiency: {comprehensive_status['performance']['team_efficiency']}/10")
    print(f"   Team Quality: {comprehensive_status['performance']['team_quality']}/10")
    print(f"   Coordination Status: {comprehensive_status['coordination']['status']}")
    print(f"   Accountability Score: {comprehensive_status['overview']['overall_accountability_score']}/10")
    
    # Show top performers and those needing support
    if comprehensive_status['performance']['top_performers']:
        print(f"   🏆 Top Performers: {', '.join(comprehensive_status['performance']['top_performers'])}")
    
    if comprehensive_status['performance']['agents_needing_support']:
        print(f"   🤝 Need Support: {', '.join(comprehensive_status['performance']['agents_needing_support'])}")
    
    # Generate executive summary
    print("\n📋 Executive Summary:")
    executive_summary = dashboard.generate_executive_summary()
    
    print(f"   {executive_summary['status_indicator']} Overall Status: {executive_summary['overall_status'].upper()}")
    print(f"   🎯 Team Health Score: {executive_summary['team_health_score']}/100")
    print(f"   ⚠️  Total Issues: {executive_summary['total_issues']}")
    
    if executive_summary['highlights']:
        print("   ✨ Key Highlights:")
        for highlight in executive_summary['highlights']:
            print(f"      {highlight}")
    
    if executive_summary['concerns']:
        print("   🔴 Key Concerns:")
        for concern in executive_summary['concerns']:
            print(f"      {concern}")
    
    if executive_summary['priority_actions']:
        print("   💡 Priority Actions:")
        for action in executive_summary['priority_actions'][:3]:
            print(f"      - {action}")
    
    # Show detailed report for one agent
    print("\n👤 Sample Agent Detailed Report (ProjectManager):")
    detailed_report = dashboard.get_agent_detailed_report("ProjectManager")
    
    print(f"   Role: {detailed_report['basic_info']['role']}")
    print(f"   Status: {detailed_report['basic_info']['status']}")
    print(f"   Performance Score: {detailed_report['performance']['overall_score']}/10")
    print(f"   Performance Level: {detailed_report['performance']['performance_level']}")
    print(f"   Accountability Level: {detailed_report['accountability']['accountability_level']}")
    print(f"   Task Utilization: {detailed_report['workload']['utilization_percentage']}%")
    print(f"   Active Commitments: {detailed_report['accountability']['active_commitments_count']}")
    
    # Save dashboard snapshot
    print("\n💾 Saving Dashboard Snapshot...")
    dashboard.save_dashboard_snapshot()
    
    print("\n✅ Master Agent Dashboard Test Complete")
    print("\n📚 Available Commands:")
    print("   python monitoring/master_agent_dashboard.py  # Run this test")
    print("   python monitoring/agent_activity_monitor.py   # Test activity monitoring")  
    print("   python monitoring/agent_performance_dashboard.py  # Test performance analytics")
    print("   python monitoring/team_coordination_dashboard.py  # Test coordination monitoring")
    print("   python monitoring/agent_accountability_system.py  # Test accountability tracking")

if __name__ == "__main__":
    main()