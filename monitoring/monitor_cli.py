#!/usr/bin/env python3
"""
Agent Monitoring CLI
Command-line interface for the Agent Monitoring System.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add the monitoring directory to the path
sys.path.append(str(Path(__file__).parent))

from master_agent_dashboard import MasterAgentDashboard
from agent_activity_monitor import AgentActivityMonitor
from agent_accountability_system import AgentAccountabilitySystem

class MonitorCLI:
    """Command-line interface for agent monitoring."""
    
    def __init__(self):
        self.dashboard = MasterAgentDashboard()
        self.monitor = self.dashboard.activity_monitor
        self.accountability = self.dashboard.accountability_system
    
    def status(self, format_type: str = "table"):
        """Display current team status."""
        
        print("🎛️  Agent Monitoring System - Team Status")
        print("=" * 60)
        
        try:
            comprehensive_status = self.dashboard.get_comprehensive_status()
            
            # Overview section
            overview = comprehensive_status["overview"]
            print(f"\n📊 Team Overview:")
            print(f"   Total Agents:      {overview['total_agents']}")
            print(f"   Active Agents:     {overview['active_agents']}")
            print(f"   Idle Agents:       {overview['idle_agents']}")
            print(f"   Offline Agents:    {overview['offline_agents']}")
            print(f"   Tasks Completed:   {overview['total_tasks_completed']}")
            print(f"   Team Velocity:     {overview['team_velocity']} tasks/hour")
            print(f"   Accountability:    {overview['overall_accountability_score']}/10")
            
            # Performance section
            performance = comprehensive_status["performance"]
            print(f"\n⚡ Team Performance:")
            print(f"   Efficiency:        {performance['team_efficiency']}/10")
            print(f"   Quality:           {performance['team_quality']}/10") 
            print(f"   Collaboration:     {performance['team_collaboration']}/10")
            print(f"   Avg Task Duration: {performance['average_task_duration']} min")
            
            if performance['top_performers']:
                print(f"   🏆 Top Performers: {', '.join(performance['top_performers'])}")
            
            if performance['agents_needing_support']:
                print(f"   🤝 Need Support:   {', '.join(performance['agents_needing_support'])}")
            
            # Coordination section
            coordination = comprehensive_status["coordination"]
            status_emoji = {"optimal": "🟢", "good": "🟡", "attention": "🟠", "critical": "🔴"}
            print(f"\n🔄 Coordination Status: {status_emoji.get(coordination['status'], '⚪')} {coordination['status'].upper()}")
            print(f"   Active Phases:     {coordination['active_phases_count']}")
            print(f"   Workflow Bottlenecks: {coordination['workflow_bottlenecks_count']}")
            print(f"   Coordination Issues: {coordination['coordination_issues_count']}")
            print(f"   Resource Conflicts: {coordination['resource_conflicts_count']}")
            print(f"   Communication Gaps: {coordination['communication_gaps_count']}")
            
            # Accountability section
            accountability = comprehensive_status["accountability"]
            print(f"\n📋 Accountability:")
            print(f"   Completion Rate:   {accountability['average_completion_rate']}%")
            print(f"   Active Commitments: {accountability['total_active_commitments']}")
            print(f"   Overdue Commitments: {accountability['total_overdue_commitments']}")
            print(f"   Accountability Risks: {accountability['risks_count']}")
            
            # Issues summary
            issues = comprehensive_status["issues"]
            total_issues = (issues['critical_performance_issues'] + 
                          len(issues['coordination_issues']) + 
                          len(issues['accountability_risks']) + 
                          len(issues['activity_issues']))
            
            if total_issues > 0:
                print(f"\n⚠️  Issues Summary (Total: {total_issues}):")
                if issues['critical_performance_issues'] > 0:
                    print(f"   Critical Performance: {issues['critical_performance_issues']}")
                if len(issues['coordination_issues']) > 0:
                    print(f"   Coordination Issues: {len(issues['coordination_issues'])}")
                if len(issues['accountability_risks']) > 0:
                    print(f"   Accountability Risks: {len(issues['accountability_risks'])}")
                if len(issues['activity_issues']) > 0:
                    print(f"   Activity Issues: {len(issues['activity_issues'])}")
            else:
                print(f"\n✅ No critical issues detected")
            
            # Recommendations
            recommendations = comprehensive_status["recommendations"]
            all_recs = recommendations['coordination'] + recommendations['accountability']
            if all_recs:
                print(f"\n💡 Top Recommendations:")
                for i, rec in enumerate(all_recs[:3], 1):
                    print(f"   {i}. {rec}")
            
            print(f"\n📅 Last Updated: {comprehensive_status['timestamp']}")
            
        except Exception as e:
            print(f"❌ Error generating status: {e}")
            return False
        
        return True
    
    def agent_report(self, agent_name: str):
        """Display detailed report for specific agent."""
        
        print(f"👤 Agent Report: {agent_name}")
        print("=" * 60)
        
        try:
            detailed_report = self.dashboard.get_agent_detailed_report(agent_name)
            
            if "error" in detailed_report:
                print(f"❌ Error: {detailed_report['error']}")
                return False
            
            # Basic info
            basic = detailed_report["basic_info"]
            print(f"\n📋 Basic Information:")
            print(f"   Agent Name:    {agent_name}")
            print(f"   Role:          {basic['role']}")
            print(f"   Priority:      {basic['priority']}")
            print(f"   Status:        {basic['status']}")
            print(f"   Last Active:   {basic['last_active'] or 'Never'}")
            
            # Performance
            perf = detailed_report["performance"]
            level_emoji = {
                "excellent": "🌟", "good": "🟢", "average": "🟡", 
                "poor": "🟠", "critical": "🔴"
            }
            print(f"\n⚡ Performance ({perf['performance_level'].upper()}) {level_emoji.get(perf['performance_level'], '⚪')}:")
            print(f"   Overall Score:     {perf['overall_score']}/10")
            print(f"   Efficiency:        {perf['efficiency_score']}/10")
            print(f"   Quality:           {perf['quality_score']}/10")
            print(f"   Collaboration:     {perf['collaboration_score']}/10")
            print(f"   Responsiveness:    {perf['responsiveness_score']}/10")
            print(f"   Recent Trend:      {perf['recent_trend']}")
            
            if perf['strengths']:
                print(f"   💪 Strengths:")
                for strength in perf['strengths'][:3]:
                    print(f"      • {strength}")
            
            if perf['improvement_areas']:
                print(f"   📈 Improvement Areas:")
                for area in perf['improvement_areas'][:3]:
                    print(f"      • {area}")
            
            # Workload
            workload = detailed_report["workload"]
            utilization_status = "🔴 Overloaded" if workload['utilization_percentage'] > 100 else \
                               "🟡 High" if workload['utilization_percentage'] > 80 else \
                               "🟢 Normal"
            print(f"\n📊 Current Workload:")
            print(f"   Utilization:       {workload['utilization_percentage']}% {utilization_status}")
            print(f"   Current Tasks:     {workload['task_count']}/{workload['estimated_capacity']}")
            print(f"   Current Phase:     {workload['current_phase'] or 'None'}")
            print(f"   Skill Areas:       {', '.join(workload['skill_areas'])}")
            
            if workload['current_tasks']:
                print(f"   🎯 Active Tasks:")
                for task in workload['current_tasks'][:3]:
                    print(f"      • {task}")
            
            # Accountability
            account = detailed_report["accountability"]
            account_emoji = {
                "exceptional": "🌟", "strong": "🟢", "adequate": "🟡",
                "concerning": "🟠", "critical": "🔴"
            }
            print(f"\n📋 Accountability ({account['accountability_level'].upper()}) {account_emoji.get(account['accountability_level'], '⚪')}:")
            print(f"   Overall Score:     {account['overall_score']}/10")
            print(f"   Completion Rate:   {account['commitment_completion_rate']}%")
            print(f"   Avg Delay:         {account['average_delay_days']} days")
            print(f"   Reliability:       {account['reliability_score']}/10")
            print(f"   Active Commitments: {account['active_commitments_count']}")
            print(f"   Overdue Commitments: {account['overdue_commitments_count']}")
            print(f"   Recent Completions: {account['recent_completions_count']}")
            print(f"   Next Review:       {account['next_review_date']}")
            
            # Recent activities
            activities = detailed_report["recent_activities"]
            if activities:
                print(f"\n📝 Recent Activities:")
                for activity in activities:
                    timestamp = datetime.fromisoformat(activity['timestamp']).strftime('%m/%d %H:%M')
                    duration_str = f" ({activity['duration']}min)" if activity.get('duration') else ""
                    print(f"   {timestamp} - {activity['type']}: {activity['description']}{duration_str}")
            
            # Recommendations
            if perf['recommendations']:
                print(f"\n💡 Recommendations:")
                for i, rec in enumerate(perf['recommendations'][:3], 1):
                    print(f"   {i}. {rec}")
            
            print(f"\n📅 Report Generated: {detailed_report['timestamp']}")
            
        except Exception as e:
            print(f"❌ Error generating agent report: {e}")
            return False
        
        return True
    
    def executive_summary(self):
        """Display executive summary."""
        
        print("📋 Executive Summary - Agent Monitoring System")
        print("=" * 60)
        
        try:
            exec_summary = self.dashboard.generate_executive_summary()
            
            if "error" in exec_summary:
                print(f"❌ Error: {exec_summary['error']}")
                return False
            
            # Overall status
            status_emoji = {
                "excellent": "🟢", "good": "🟢", "needs_attention": "🟡", "critical": "🔴"
            }
            print(f"\n🎯 Overall Status: {exec_summary['status_indicator']} {exec_summary['overall_status'].upper()}")
            print(f"   Team Health Score: {exec_summary['team_health_score']}/100")
            print(f"   Total Issues:      {exec_summary['total_issues']}")
            
            # Key metrics
            metrics = exec_summary["key_metrics"]
            print(f"\n📊 Key Metrics:")
            print(f"   Active Agents:     {metrics['active_agents']}/{metrics['total_agents']}")
            print(f"   Team Velocity:     {metrics['team_velocity']} tasks/hour")
            print(f"   Team Efficiency:   {metrics['team_efficiency']}/10")
            print(f"   Team Quality:      {metrics['team_quality']}/10")
            print(f"   Accountability:    {metrics['accountability_score']}/10")
            print(f"   Coordination:      {metrics['coordination_status']}")
            
            # Highlights
            if exec_summary['highlights']:
                print(f"\n✨ Key Highlights:")
                for highlight in exec_summary['highlights']:
                    print(f"   {highlight}")
            
            # Concerns
            if exec_summary['concerns']:
                print(f"\n🔴 Key Concerns:")
                for concern in exec_summary['concerns']:
                    print(f"   {concern}")
            
            # Priority actions
            if exec_summary['priority_actions']:
                print(f"\n💡 Priority Actions:")
                for i, action in enumerate(exec_summary['priority_actions'], 1):
                    print(f"   {i}. {action}")
            
            # Detailed breakdown
            breakdown = exec_summary["detailed_breakdown"]
            print(f"\n📊 Issue Breakdown:")
            print(f"   Performance Issues: {breakdown['performance_issues']}")
            print(f"   Coordination Issues: {breakdown['coordination_issues']}")
            print(f"   Accountability Risks: {breakdown['accountability_risks']}")
            print(f"   Activity Issues:    {breakdown['activity_issues']}")
            
            print(f"\n📅 Next Review:       {exec_summary['next_review_recommended']}")
            print(f"📅 Generated:         {exec_summary['timestamp']}")
            
        except Exception as e:
            print(f"❌ Error generating executive summary: {e}")
            return False
        
        return True
    
    def list_agents(self):
        """List all agents and their current status."""
        
        print("👥 Agent List - Team Status")
        print("=" * 60)
        
        try:
            team_dashboard = self.monitor.get_team_dashboard()
            agents_by_role = team_dashboard["agents_by_role"]
            
            for role, agents in agents_by_role.items():
                print(f"\n🏷️  {role.title()}s:")
                for agent in agents:
                    status_emoji = {"active": "🟢", "idle": "🟡", "offline": "🔴"}
                    emoji = status_emoji.get(agent['status'], '⚪')
                    last_active = agent['last_active']
                    if last_active:
                        last_active = datetime.fromisoformat(last_active).strftime('%m/%d %H:%M')
                    else:
                        last_active = 'Never'
                    
                    print(f"   {emoji} {agent['name']:<20} Status: {agent['status']:<8} "
                          f"Tasks: {agent['tasks_completed']:<3} Quality: {agent['quality_score']:<4} "
                          f"Last: {last_active}")
            
            print(f"\n📅 Last Updated: {team_dashboard['timestamp']}")
            
        except Exception as e:
            print(f"❌ Error listing agents: {e}")
            return False
        
        return True
    
    def log_activity(self, agent_name: str, activity_type: str, description: str,
                    duration: Optional[float] = None, quality: Optional[int] = None,
                    phase: Optional[str] = None):
        """Log an activity for an agent."""
        
        try:
            self.monitor.log_activity(
                agent_name=agent_name,
                activity_type=activity_type,
                description=description,
                duration_minutes=duration,
                output_quality=quality,
                workflow_phase=phase
            )
            
            print(f"✅ Logged activity for {agent_name}: {activity_type} - {description}")
            return True
            
        except Exception as e:
            print(f"❌ Error logging activity: {e}")
            return False
    
    def create_commitment(self, agent_name: str, description: str, days: int,
                         criteria: List[str], hours: float, quality: float = 8.0):
        """Create a commitment for an agent."""
        
        try:
            target_date = datetime.now() + timedelta(days=days)
            
            commitment_id = self.accountability.create_commitment(
                agent_name=agent_name,
                description=description,
                target_date=target_date,
                success_criteria=criteria,
                estimated_hours=hours,
                quality_target=quality
            )
            
            print(f"✅ Created commitment {commitment_id} for {agent_name}")
            print(f"   Description: {description}")
            print(f"   Target Date: {target_date.strftime('%Y-%m-%d')}")
            print(f"   Estimated Hours: {hours}")
            return commitment_id
            
        except Exception as e:
            print(f"❌ Error creating commitment: {e}")
            return None
    
    def snapshot(self):
        """Save current monitoring snapshot."""
        
        try:
            self.dashboard.save_dashboard_snapshot()
            print("✅ Dashboard snapshot saved successfully")
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"📅 Snapshot timestamp: {timestamp}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving snapshot: {e}")
            return False
    
    def monitor_continuous(self, interval_minutes: int = 30, duration_minutes: Optional[int] = None):
        """Run continuous monitoring."""
        
        print(f"🔄 Starting continuous monitoring (interval: {interval_minutes} min)")
        if duration_minutes:
            print(f"   Duration: {duration_minutes} minutes")
        print("   Press Ctrl+C to stop\n")
        
        start_time = datetime.now()
        
        try:
            iteration = 0
            while True:
                iteration += 1
                current_time = datetime.now()
                
                print(f"📊 Monitoring Iteration {iteration} - {current_time.strftime('%H:%M:%S')}")
                
                # Save snapshot
                self.dashboard.save_dashboard_snapshot()
                
                # Quick status check
                try:
                    comprehensive_status = self.dashboard.get_comprehensive_status()
                    overview = comprehensive_status["overview"]
                    
                    print(f"   Active Agents: {overview['active_agents']}/{overview['total_agents']}")
                    print(f"   Team Velocity: {overview['team_velocity']} tasks/hour")
                    print(f"   Accountability: {overview['overall_accountability_score']}/10")
                    
                    # Check for critical issues
                    issues = comprehensive_status["issues"]
                    total_issues = (issues['critical_performance_issues'] + 
                                  len(issues['coordination_issues']) + 
                                  len(issues['accountability_risks']) + 
                                  len(issues['activity_issues']))
                    
                    if total_issues > 0:
                        print(f"   ⚠️  Issues Detected: {total_issues}")
                    else:
                        print(f"   ✅ No critical issues")
                    
                except Exception as e:
                    print(f"   ❌ Error in status check: {e}")
                
                # Check if duration exceeded
                if duration_minutes:
                    elapsed = (current_time - start_time).total_seconds() / 60
                    if elapsed >= duration_minutes:
                        print(f"\n⏱️  Duration limit reached ({duration_minutes} minutes)")
                        break
                
                print(f"   💤 Sleeping for {interval_minutes} minutes...\n")
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            return True
        except Exception as e:
            print(f"\n❌ Error in continuous monitoring: {e}")
            return False
        
        print("✅ Continuous monitoring completed")
        return True

def main():
    """Main CLI entry point."""
    
    parser = argparse.ArgumentParser(
        description="Agent Monitoring System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  monitor_cli.py --status                    # Show team status
  monitor_cli.py --agent Implementer         # Show agent report  
  monitor_cli.py --executive                 # Executive summary
  monitor_cli.py --list                      # List all agents
  monitor_cli.py --snapshot                  # Save snapshot
  monitor_cli.py --monitor --interval 15     # Monitor every 15 min
  monitor_cli.py --log-activity Implementer task_start "Fix bug #123"
  monitor_cli.py --create-commitment QAEngineer "Review code" 3 "All tests pass" 8.0
        """
    )
    
    # Main commands (mutually exclusive)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--status', action='store_true', help='Show comprehensive team status')
    group.add_argument('--agent', type=str, help='Show detailed agent report')
    group.add_argument('--executive', action='store_true', help='Show executive summary')
    group.add_argument('--list', action='store_true', help='List all agents')
    group.add_argument('--snapshot', action='store_true', help='Save monitoring snapshot')
    group.add_argument('--monitor', action='store_true', help='Run continuous monitoring')
    group.add_argument('--log-activity', nargs=3, metavar=('AGENT', 'TYPE', 'DESCRIPTION'),
                      help='Log activity: agent_name activity_type description')
    group.add_argument('--create-commitment', nargs=5, 
                      metavar=('AGENT', 'DESCRIPTION', 'DAYS', 'CRITERIA', 'HOURS'),
                      help='Create commitment: agent_name description days criteria hours')
    
    # Optional arguments
    parser.add_argument('--format', choices=['table', 'json'], default='table',
                       help='Output format (default: table)')
    parser.add_argument('--interval', type=int, default=30,
                       help='Monitoring interval in minutes (default: 30)')
    parser.add_argument('--duration', type=int,
                       help='Monitoring duration in minutes (default: unlimited)')
    parser.add_argument('--phase', type=str,
                       help='Workflow phase for activity logging')
    parser.add_argument('--quality', type=int, choices=range(1, 11),
                       help='Quality score for activity logging (1-10)')
    parser.add_argument('--activity-duration', type=float,
                       help='Duration in minutes for activity logging')
    
    args = parser.parse_args()
    
    # Initialize CLI
    cli = MonitorCLI()
    success = False
    
    try:
        if args.status:
            success = cli.status(args.format)
            
        elif args.agent:
            success = cli.agent_report(args.agent)
            
        elif args.executive:
            success = cli.executive_summary()
            
        elif args.list:
            success = cli.list_agents()
            
        elif args.snapshot:
            success = cli.snapshot()
            
        elif args.monitor:
            success = cli.monitor_continuous(args.interval, args.duration)
            
        elif args.log_activity:
            agent_name, activity_type, description = args.log_activity
            success = cli.log_activity(
                agent_name, activity_type, description,
                args.activity_duration, args.quality, args.phase
            )
            
        elif args.create_commitment:
            agent_name, description, days_str, criteria_str, hours_str = args.create_commitment
            try:
                days = int(days_str)
                hours = float(hours_str)
                criteria = [criteria_str]  # Simple single criteria for CLI
                commitment_id = cli.create_commitment(agent_name, description, days, criteria, hours)
                success = commitment_id is not None
            except ValueError as e:
                print(f"❌ Invalid commitment parameters: {e}")
                success = False
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        success = False
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()