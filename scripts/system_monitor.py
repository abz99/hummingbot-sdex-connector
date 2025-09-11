#!/usr/bin/env python3
"""
System Monitor for Stellar Hummingbot Connector

Comprehensive monitoring and health check system for agents,
knowledge bases, workflows, and system resources.
"""

import os
import sys
import json
import time
import psutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: str  # healthy, warning, critical, unknown
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class SystemMetrics:
    """System resource metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    disk_free_gb: float
    load_average: Optional[List[float]]
    process_count: int
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class SystemMonitor:
    """Comprehensive system monitoring and health checks."""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.scripts_dir = self.project_root / "scripts"
        self.logs_dir = self.project_root / "logs"
        self.state_dir = self.project_root / "agent_state"
        self.monitoring_dir = self.project_root / "monitoring"
        
        # Ensure directories exist
        self.monitoring_dir.mkdir(exist_ok=True)
        
        self.health_checks: List[HealthCheck] = []
        self.metrics_history: List[SystemMetrics] = []
        
        # Thresholds for alerts
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning': 80.0,
            'memory_critical': 95.0,
            'disk_warning': 85.0,
            'disk_critical': 95.0,
            'knowledge_base_age_warning': 3600,  # 1 hour
            'knowledge_base_age_critical': 86400,  # 24 hours
            'agent_inactive_warning': 1800,  # 30 minutes
            'agent_inactive_critical': 3600,  # 1 hour
        }
    
    def check_system_resources(self) -> HealthCheck:
        """Check system resource utilization."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get load average (Unix only)
            load_avg = None
            try:
                load_avg = os.getloadavg()
            except (AttributeError, OSError):
                pass
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_percent=disk.percent,
                disk_free_gb=disk.free / (1024 * 1024 * 1024),
                load_average=list(load_avg) if load_avg else None,
                process_count=len(psutil.pids()),
                timestamp=datetime.now(timezone.utc)
            )
            
            self.metrics_history.append(metrics)
            
            # Determine status
            status = "healthy"
            issues = []
            
            if cpu_percent >= self.thresholds['cpu_critical']:
                status = "critical"
                issues.append(f"CPU usage critical: {cpu_percent:.1f}%")
            elif cpu_percent >= self.thresholds['cpu_warning']:
                status = "warning"
                issues.append(f"CPU usage high: {cpu_percent:.1f}%")
            
            if memory.percent >= self.thresholds['memory_critical']:
                status = "critical"
                issues.append(f"Memory usage critical: {memory.percent:.1f}%")
            elif memory.percent >= self.thresholds['memory_warning']:
                if status != "critical":
                    status = "warning"
                issues.append(f"Memory usage high: {memory.percent:.1f}%")
            
            if disk.percent >= self.thresholds['disk_critical']:
                status = "critical"
                issues.append(f"Disk usage critical: {disk.percent:.1f}%")
            elif disk.percent >= self.thresholds['disk_warning']:
                if status != "critical":
                    status = "warning"
                issues.append(f"Disk usage high: {disk.percent:.1f}%")
            
            message = "; ".join(issues) if issues else "System resources within normal limits"
            
            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                details=metrics.to_dict(),
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return HealthCheck(
                name="system_resources",
                status="unknown",
                message=f"Failed to check system resources: {e}",
                details={},
                timestamp=datetime.now(timezone.utc)
            )
    
    def check_agent_health(self) -> HealthCheck:
        """Check agent manager health."""
        try:
            # Get agent status
            result = subprocess.run([
                sys.executable,
                str(self.scripts_dir / "agent_manager.py"),
                "--status"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return HealthCheck(
                    name="agent_health",
                    status="critical",
                    message=f"Agent manager not responding: {result.stderr}",
                    details={},
                    timestamp=datetime.now(timezone.utc)
                )
            
            try:
                status_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return HealthCheck(
                    name="agent_health",
                    status="critical",
                    message="Agent manager returned invalid status data",
                    details={},
                    timestamp=datetime.now(timezone.utc)
                )
            
            # Analyze agent status
            agents = status_data.get('agents', {})
            workflow_health = status_data.get('workflow_health', {})
            
            agent_stats = workflow_health.get('agents', {})
            active_agents = agent_stats.get('active', 0)
            idle_agents = agent_stats.get('idle', 0)
            error_agents = agent_stats.get('error', 0)
            
            status = "healthy"
            issues = []
            
            if error_agents > 0:
                status = "critical"
                issues.append(f"{error_agents} agents in error state")
            
            if active_agents + idle_agents == 0:
                status = "critical"
                issues.append("No agents are active or idle")
            
            # Check for inactive agents
            current_time = datetime.now(timezone.utc)
            inactive_agents = []
            
            for agent_name, agent_data in agents.items():
                last_activity = agent_data.get('last_activity')
                if last_activity:
                    try:
                        last_activity_time = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                        time_since_activity = (current_time - last_activity_time).total_seconds()
                        
                        if time_since_activity > self.thresholds['agent_inactive_critical']:
                            inactive_agents.append(f"{agent_name} ({time_since_activity/3600:.1f}h)")
                    except Exception:
                        pass
            
            if inactive_agents:
                if status != "critical":
                    status = "warning"
                issues.append(f"Inactive agents: {', '.join(inactive_agents)}")
            
            message = "; ".join(issues) if issues else f"{len(agents)} agents operational"
            
            return HealthCheck(
                name="agent_health",
                status=status,
                message=message,
                details={
                    'total_agents': len(agents),
                    'active_agents': active_agents,
                    'idle_agents': idle_agents,
                    'error_agents': error_agents,
                    'inactive_agents': inactive_agents
                },
                timestamp=datetime.now(timezone.utc)
            )
            
        except subprocess.TimeoutExpired:
            return HealthCheck(
                name="agent_health",
                status="critical",
                message="Agent manager health check timed out",
                details={},
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            return HealthCheck(
                name="agent_health",
                status="unknown",
                message=f"Failed to check agent health: {e}",
                details={},
                timestamp=datetime.now(timezone.utc)
            )
    
    def check_knowledge_base_health(self) -> HealthCheck:
        """Check knowledge base health."""
        try:
            # Check knowledge base status
            result = subprocess.run([
                sys.executable,
                str(self.scripts_dir / "knowledge_base_indexer.py"),
                "--report"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                return HealthCheck(
                    name="knowledge_base_health",
                    status="critical",
                    message=f"Knowledge base indexer not responding: {result.stderr}",
                    details={},
                    timestamp=datetime.now(timezone.utc)
                )
            
            try:
                kb_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return HealthCheck(
                    name="knowledge_base_health",
                    status="critical",
                    message="Knowledge base indexer returned invalid data",
                    details={},
                    timestamp=datetime.now(timezone.utc)
                )
            
            # Analyze knowledge base status
            last_updated = kb_data.get('last_updated')
            kb_count = kb_data.get('knowledge_base_count', 0)
            file_count = kb_data.get('tracked_file_count', 0)
            
            status = "healthy"
            issues = []
            
            if last_updated:
                try:
                    last_update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    time_since_update = (datetime.now(timezone.utc) - last_update_time).total_seconds()
                    
                    if time_since_update > self.thresholds['knowledge_base_age_critical']:
                        status = "critical"
                        issues.append(f"Knowledge base not updated for {time_since_update/3600:.1f}h")
                    elif time_since_update > self.thresholds['knowledge_base_age_warning']:
                        status = "warning"
                        issues.append(f"Knowledge base last updated {time_since_update/3600:.1f}h ago")
                        
                except Exception:
                    status = "warning"
                    issues.append("Cannot parse last update time")
            else:
                status = "warning"
                issues.append("No update timestamp available")
            
            if kb_count == 0:
                status = "critical"
                issues.append("No knowledge bases indexed")
            
            message = "; ".join(issues) if issues else f"{kb_count} knowledge bases, {file_count} files indexed"
            
            return HealthCheck(
                name="knowledge_base_health",
                status=status,
                message=message,
                details={
                    'knowledge_base_count': kb_count,
                    'tracked_file_count': file_count,
                    'last_updated': last_updated,
                    'time_since_update': time_since_update if last_updated else None
                },
                timestamp=datetime.now(timezone.utc)
            )
            
        except subprocess.TimeoutExpired:
            return HealthCheck(
                name="knowledge_base_health",
                status="critical",
                message="Knowledge base health check timed out",
                details={},
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            return HealthCheck(
                name="knowledge_base_health",
                status="unknown",
                message=f"Failed to check knowledge base health: {e}",
                details={},
                timestamp=datetime.now(timezone.utc)
            )
    
    def check_file_system_health(self) -> HealthCheck:
        """Check file system health (permissions, required files, etc.)."""
        try:
            status = "healthy"
            issues = []
            details = {}
            
            # Check required files exist
            required_files = [
                "team_startup.yaml",
                "PROJECT_STATUS.md",
                "stellar_sdex_checklist_v3.md",
                "stellar_sdex_tdd_v3.md"
            ]
            
            missing_files = []
            for file_path in required_files:
                if not (self.project_root / file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                status = "critical"
                issues.append(f"Missing required files: {', '.join(missing_files)}")
            
            details['missing_files'] = missing_files
            
            # Check directory permissions
            critical_dirs = [
                self.logs_dir,
                self.state_dir,
                self.monitoring_dir,
                self.project_root / "knowledge"
            ]
            
            permission_issues = []
            for dir_path in critical_dirs:
                if dir_path.exists():
                    if not os.access(dir_path, os.R_OK | os.W_OK):
                        permission_issues.append(str(dir_path))
                else:
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                    except PermissionError:
                        permission_issues.append(str(dir_path))
            
            if permission_issues:
                if status != "critical":
                    status = "warning"
                issues.append(f"Directory permission issues: {', '.join(permission_issues)}")
            
            details['permission_issues'] = permission_issues
            
            # Check log file sizes
            large_logs = []
            if self.logs_dir.exists():
                for log_file in self.logs_dir.glob("*.log"):
                    size_mb = log_file.stat().st_size / (1024 * 1024)
                    if size_mb > 100:  # > 100MB
                        large_logs.append(f"{log_file.name} ({size_mb:.1f}MB)")
            
            if large_logs:
                if status == "healthy":
                    status = "warning"
                issues.append(f"Large log files: {', '.join(large_logs)}")
            
            details['large_logs'] = large_logs
            
            message = "; ".join(issues) if issues else "File system health normal"
            
            return HealthCheck(
                name="file_system_health",
                status=status,
                message=message,
                details=details,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return HealthCheck(
                name="file_system_health",
                status="unknown",
                message=f"Failed to check file system health: {e}",
                details={},
                timestamp=datetime.now(timezone.utc)
            )
    
    def check_process_health(self) -> HealthCheck:
        """Check health of background processes."""
        try:
            status = "healthy"
            issues = []
            details = {}
            
            # Look for running background processes
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    cmdline = proc.info['cmdline'] or []
                    if any('knowledge_base_watcher.py' in arg or 'agent_manager.py' in arg for arg in cmdline):
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': ' '.join(cmdline),
                            'uptime_hours': (time.time() - proc.info['create_time']) / 3600
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            details['background_processes'] = processes
            
            # Check if essential processes are running
            has_watcher = any('knowledge_base_watcher.py' in p['cmdline'] for p in processes)
            has_agent_manager = any('agent_manager.py' in p['cmdline'] for p in processes)
            
            if not has_watcher:
                status = "warning"
                issues.append("Knowledge base watcher not running")
            
            if not has_agent_manager:
                status = "warning"
                issues.append("Agent manager daemon not running")
            
            # Check for zombie or stalled processes
            stalled_processes = []
            for proc in processes:
                if proc['uptime_hours'] > 24 and 'daemon' in proc['cmdline']:
                    # Long-running processes are normal for daemons
                    continue
                elif proc['uptime_hours'] > 1 and 'daemon' not in proc['cmdline']:
                    stalled_processes.append(f"PID {proc['pid']} ({proc['uptime_hours']:.1f}h)")
            
            if stalled_processes:
                if status == "healthy":
                    status = "warning"
                issues.append(f"Potentially stalled processes: {', '.join(stalled_processes)}")
            
            message = "; ".join(issues) if issues else f"{len(processes)} background processes running"
            
            return HealthCheck(
                name="process_health",
                status=status,
                message=message,
                details=details,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            return HealthCheck(
                name="process_health",
                status="unknown",
                message=f"Failed to check process health: {e}",
                details={},
                timestamp=datetime.now(timezone.utc)
            )
    
    def run_all_health_checks(self) -> List[HealthCheck]:
        """Run all health checks."""
        logger.info("Running comprehensive health checks...")
        
        health_checks = [
            self.check_system_resources(),
            self.check_agent_health(),
            self.check_knowledge_base_health(),
            self.check_file_system_health(),
            self.check_process_health()
        ]
        
        self.health_checks = health_checks
        return health_checks
    
    def get_overall_health_status(self, health_checks: List[HealthCheck] = None) -> str:
        """Get overall system health status."""
        checks = health_checks or self.health_checks
        
        if not checks:
            return "unknown"
        
        statuses = [check.status for check in checks]
        
        if "critical" in statuses:
            return "critical"
        elif "unknown" in statuses:
            return "unknown"
        elif "warning" in statuses:
            return "warning"
        else:
            return "healthy"
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        health_checks = self.run_all_health_checks()
        overall_status = self.get_overall_health_status(health_checks)
        
        # Get latest metrics
        latest_metrics = self.metrics_history[-1] if self.metrics_history else None
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': overall_status,
            'health_checks': [check.to_dict() for check in health_checks],
            'system_metrics': latest_metrics.to_dict() if latest_metrics else None,
            'summary': {
                'total_checks': len(health_checks),
                'healthy_checks': len([c for c in health_checks if c.status == "healthy"]),
                'warning_checks': len([c for c in health_checks if c.status == "warning"]),
                'critical_checks': len([c for c in health_checks if c.status == "critical"]),
                'unknown_checks': len([c for c in health_checks if c.status == "unknown"])
            }
        }
    
    def save_health_report(self, report: Dict[str, Any] = None):
        """Save health report to file."""
        report = report or self.generate_health_report()
        
        # Save latest report
        report_file = self.monitoring_dir / "health_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Save timestamped report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_file = self.monitoring_dir / f"health_report_{timestamp}.json"
        with open(timestamped_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Clean up old reports (keep last 24)
        report_files = sorted(self.monitoring_dir.glob("health_report_*.json"))
        if len(report_files) > 24:
            for old_file in report_files[:-24]:
                old_file.unlink()
    
    def display_health_status(self, report: Dict[str, Any] = None):
        """Display health status in human-readable format."""
        report = report or self.generate_health_report()
        
        overall_status = report['overall_status']
        status_icons = {
            'healthy': '🟢',
            'warning': '🟡', 
            'critical': '🔴',
            'unknown': '❓'
        }
        
        print(f"\n{'='*60}")
        print(f"🏥 SYSTEM HEALTH REPORT - {status_icons.get(overall_status, '❓')} {overall_status.upper()}")
        print(f"{'='*60}")
        print(f"📅 Generated: {report['timestamp']}")
        
        summary = report['summary']
        print(f"📊 Checks: {summary['healthy_checks']}✅ {summary['warning_checks']}⚠️ {summary['critical_checks']}🔴 {summary['unknown_checks']}❓")
        
        print(f"\n📋 HEALTH CHECK DETAILS:")
        for check_data in report['health_checks']:
            status_icon = status_icons.get(check_data['status'], '❓')
            print(f"  {status_icon} {check_data['name']}: {check_data['message']}")
        
        # Display system metrics if available
        metrics = report.get('system_metrics')
        if metrics:
            print(f"\n📊 SYSTEM METRICS:")
            print(f"  💻 CPU: {metrics['cpu_percent']:.1f}%")
            print(f"  🧠 Memory: {metrics['memory_percent']:.1f}% ({metrics['memory_used_mb']:.0f}MB used)")
            print(f"  💾 Disk: {metrics['disk_percent']:.1f}% ({metrics['disk_free_gb']:.1f}GB free)")
            if metrics.get('load_average'):
                load_avg = metrics['load_average']
                print(f"  ⚡ Load: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}")
        
        print(f"{'='*60}\n")


def main():
    """Main entry point for system monitor."""
    import argparse
    
    parser = argparse.ArgumentParser(description='System Monitor for Stellar Hummingbot Connector')
    parser.add_argument('--report', action='store_true', help='Generate health report')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--save', action='store_true', help='Save report to file')
    parser.add_argument('--watch', type=int, metavar='SECONDS', help='Continuously monitor with interval')
    
    args = parser.parse_args()
    
    monitor = SystemMonitor()
    
    if args.watch:
        print(f"🔍 Starting continuous monitoring (interval: {args.watch}s)")
        print("Press Ctrl+C to stop...")
        
        try:
            while True:
                report = monitor.generate_health_report()
                
                if args.json:
                    print(json.dumps(report, indent=2))
                else:
                    monitor.display_health_status(report)
                
                if args.save:
                    monitor.save_health_report(report)
                
                time.sleep(args.watch)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped")
    
    else:
        report = monitor.generate_health_report()
        
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            monitor.display_health_status(report)
        
        if args.save:
            monitor.save_health_report(report)
            print(f"💾 Health report saved to monitoring/health_report.json")


if __name__ == '__main__':
    main()