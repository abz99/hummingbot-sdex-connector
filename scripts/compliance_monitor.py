#!/usr/bin/env python3
"""
Real-time Compliance Monitoring & Violation Detection System
Continuous monitoring to ensure ZERO compliance violations
"""

import json
import time
import threading
import logging
import subprocess
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import smtplib
from email.mime.text import MIMEText


@dataclass
class ComplianceAlert:
    """Compliance alert data structure"""
    alert_id: str
    timestamp: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    rule_violated: str
    description: str
    remediation: str
    context: Dict[str, Any]


class ComplianceMonitor:
    """Real-time compliance monitoring and violation detection"""

    def __init__(self):
        self.monitoring_active = False
        self.monitoring_thread = None
        self.alert_handlers = []
        self.violation_count = 0
        self.last_violation_time = None
        self.monitoring_interval = 10  # seconds
        self.alert_log_file = "logs/compliance_alerts.log"
        self.monitor_state_file = ".compliance_monitor_state.json"
        self.setup_logging()
        self.load_monitor_state()

    def setup_logging(self):
        """Setup monitoring logging"""
        Path("logs").mkdir(exist_ok=True)
        logging.basicConfig(
            filename=self.alert_log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def start_monitoring(self):
        """Start real-time compliance monitoring"""
        if self.monitoring_active:
            self.logger.warning("Compliance monitoring already active")
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        self.logger.info("🚨 Compliance monitoring started - Zero tolerance enforcement active")
        print("🚨 Real-time compliance monitoring ACTIVE")
        print("📊 Monitoring for violations every 10 seconds")
        print("⚡ Zero tolerance policy - All violations will be detected and logged")

    def stop_monitoring(self):
        """Stop real-time compliance monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

        self.save_monitor_state()
        self.logger.info("Compliance monitoring stopped")
        print("🛑 Compliance monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Check all compliance rules
                violations = self.check_all_compliance_rules()

                if violations:
                    self.handle_violations(violations)
                else:
                    self.log_healthy_check()

                # Update monitoring state
                self.save_monitor_state()

                time.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)

    def check_all_compliance_rules(self) -> List[ComplianceAlert]:
        """Check all compliance rules and return violations"""
        violations = []

        # Rule 1: Multi-agent system health
        agent_violation = self.check_agent_system_health()
        if agent_violation:
            violations.append(agent_violation)

        # Rule 2: Session compliance state
        session_violation = self.check_session_compliance()
        if session_violation:
            violations.append(session_violation)

        # Rule 3: Documentation currency
        doc_violation = self.check_documentation_currency()
        if doc_violation:
            violations.append(doc_violation)

        # Rule 4: Git workflow compliance
        git_violation = self.check_git_workflow()
        if git_violation:
            violations.append(git_violation)

        # Rule 5: Test compliance
        test_violation = self.check_test_compliance()
        if test_violation:
            violations.append(test_violation)

        # Rule 6: Resource utilization
        resource_violation = self.check_resource_utilization()
        if resource_violation:
            violations.append(resource_violation)

        return violations

    def check_agent_system_health(self) -> Optional[ComplianceAlert]:
        """Check multi-agent system health (Rule #14)"""
        try:
            result = subprocess.run(
                ['python', 'scripts/agent_manager.py', '--status'],
                capture_output=True, text=True, timeout=15
            )

            if result.returncode != 0:
                return ComplianceAlert(
                    alert_id=f"AGENT-{int(time.time())}",
                    timestamp=datetime.now().isoformat(),
                    severity="CRITICAL",
                    rule_violated="Rule #14 - Multi-agent system must be active",
                    description="Agent manager status check failed",
                    remediation="Restart agent system: python scripts/agent_manager.py --daemon",
                    context={"stderr": result.stderr, "returncode": result.returncode}
                )

            # Parse status for detailed check
            try:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip().startswith('{'):
                        status = json.loads(line.strip())

                        if status.get('agent_count') != 8:
                            return ComplianceAlert(
                                alert_id=f"AGENT-COUNT-{int(time.time())}",
                                timestamp=datetime.now().isoformat(),
                                severity="CRITICAL",
                                rule_violated="Rule #14 - Must have 8 active agents",
                                description=f"Expected 8 agents, found {status.get('agent_count')}",
                                remediation="Initialize agents: python scripts/agent_manager.py --init",
                                context={"status": status}
                            )

                        if status.get('system_status') == 'stopped':
                            return ComplianceAlert(
                                alert_id=f"AGENT-STOPPED-{int(time.time())}",
                                timestamp=datetime.now().isoformat(),
                                severity="HIGH",
                                rule_violated="Rule #14 - Agent system must not be stopped",
                                description="Agent system status is 'stopped'",
                                remediation="Activate system: python .claude_code_startup.py",
                                context={"status": status}
                            )
                        break
            except json.JSONDecodeError:
                pass

        except subprocess.TimeoutExpired:
            return ComplianceAlert(
                alert_id=f"AGENT-TIMEOUT-{int(time.time())}",
                timestamp=datetime.now().isoformat(),
                severity="HIGH",
                rule_violated="Rule #14 - Agent system responsiveness",
                description="Agent status check timed out",
                remediation="Check system resources and restart agent manager",
                context={"timeout": True}
            )
        except Exception as e:
            return ComplianceAlert(
                alert_id=f"AGENT-ERROR-{int(time.time())}",
                timestamp=datetime.now().isoformat(),
                severity="MEDIUM",
                rule_violated="Rule #14 - Agent system monitoring",
                description=f"Agent health check failed: {e}",
                remediation="Investigate agent system issues",
                context={"error": str(e)}
            )

        return None

    def check_session_compliance(self) -> Optional[ComplianceAlert]:
        """Check session compliance state (Rule #43)"""
        try:
            state_file = Path(".claude_compliance_state.json")
            if not state_file.exists():
                return ComplianceAlert(
                    alert_id=f"SESSION-MISSING-{int(time.time())}",
                    timestamp=datetime.now().isoformat(),
                    severity="MEDIUM",
                    rule_violated="Rule #43 - Session compliance state",
                    description="Session compliance state file missing",
                    remediation="Initialize session: python scripts/compliance_gateway.py --mark-compliant",
                    context={"file_missing": True}
                )

            with open(state_file, 'r') as f:
                state = json.load(f)

            if not state.get('compliance_checklist_completed', False):
                return ComplianceAlert(
                    alert_id=f"SESSION-INCOMPLETE-{int(time.time())}",
                    timestamp=datetime.now().isoformat(),
                    severity="MEDIUM",
                    rule_violated="Rule #43 - Session compliance checklist",
                    description="Session compliance checklist not completed",
                    remediation="Complete checklist and mark compliant",
                    context={"state": state}
                )

        except Exception as e:
            return ComplianceAlert(
                alert_id=f"SESSION-ERROR-{int(time.time())}",
                timestamp=datetime.now().isoformat(),
                severity="LOW",
                rule_violated="Rule #43 - Session state monitoring",
                description=f"Session compliance check failed: {e}",
                remediation="Check session state file integrity",
                context={"error": str(e)}
            )

        return None

    def check_documentation_currency(self) -> Optional[ComplianceAlert]:
        """Check documentation currency (Rule #29)"""
        try:
            status_file = Path("PROJECT_STATUS.md")
            if not status_file.exists():
                return ComplianceAlert(
                    alert_id=f"DOC-MISSING-{int(time.time())}",
                    timestamp=datetime.now().isoformat(),
                    severity="HIGH",
                    rule_violated="Rule #29 - PROJECT_STATUS.md must exist",
                    description="PROJECT_STATUS.md file is missing",
                    remediation="Restore PROJECT_STATUS.md from backup or recreate",
                    context={"file_missing": True}
                )

            last_modified = datetime.fromtimestamp(status_file.stat().st_mtime)
            age_hours = (datetime.now() - last_modified).total_seconds() / 3600

            if age_hours > 48:  # More than 2 days is concerning
                return ComplianceAlert(
                    alert_id=f"DOC-STALE-{int(time.time())}",
                    timestamp=datetime.now().isoformat(),
                    severity="MEDIUM",
                    rule_violated="Rule #29 - Documentation must be current",
                    description=f"PROJECT_STATUS.md is {age_hours:.1f} hours old",
                    remediation="Update PROJECT_STATUS.md with current project state",
                    context={"age_hours": age_hours, "last_modified": last_modified.isoformat()}
                )

        except Exception as e:
            return ComplianceAlert(
                alert_id=f"DOC-ERROR-{int(time.time())}",
                timestamp=datetime.now().isoformat(),
                severity="LOW",
                rule_violated="Rule #29 - Documentation monitoring",
                description=f"Documentation check failed: {e}",
                remediation="Check file system permissions and integrity",
                context={"error": str(e)}
            )

        return None

    def check_git_workflow(self) -> Optional[ComplianceAlert]:
        """Check git workflow compliance (Rule #31)"""
        try:
            # Check for excessive uncommitted files
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                uncommitted_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
                uncommitted_count = len(uncommitted_lines)

                if uncommitted_count > 50:  # Very high number of uncommitted files
                    return ComplianceAlert(
                        alert_id=f"GIT-UNCOMMITTED-{int(time.time())}",
                        timestamp=datetime.now().isoformat(),
                        severity="MEDIUM",
                        rule_violated="Rule #31 - Git workflow management",
                        description=f"Excessive uncommitted files: {uncommitted_count}",
                        remediation="Review and commit or stash uncommitted changes",
                        context={"uncommitted_count": uncommitted_count}
                    )

        except subprocess.TimeoutExpired:
            return ComplianceAlert(
                alert_id=f"GIT-TIMEOUT-{int(time.time())}",
                timestamp=datetime.now().isoformat(),
                severity="LOW",
                rule_violated="Rule #31 - Git workflow monitoring",
                description="Git status check timed out",
                remediation="Check git repository health",
                context={"timeout": True}
            )
        except Exception as e:
            # Git errors are common and usually not critical for compliance
            pass

        return None

    def check_test_compliance(self) -> Optional[ComplianceAlert]:
        """Check test compliance (Rule #27)"""
        try:
            # Quick test collection check
            result = subprocess.run(
                ['python', '-m', 'pytest', '--collect-only', '-q'],
                capture_output=True, text=True, timeout=30
            )

            if "FAILED" in result.stdout or "ERROR" in result.stdout:
                return ComplianceAlert(
                    alert_id=f"TEST-FAIL-{int(time.time())}",
                    timestamp=datetime.now().isoformat(),
                    severity="HIGH",
                    rule_violated="Rule #27 - Never skip failing tests",
                    description="Test collection or execution failures detected",
                    remediation="Fix failing tests immediately - never skip or ignore",
                    context={"test_output": result.stdout[-500:]}  # Last 500 chars
                )

        except subprocess.TimeoutExpired:
            # Test timeouts are not critical violations
            pass
        except Exception:
            # Test framework issues are not compliance violations
            pass

        return None

    def check_resource_utilization(self) -> Optional[ComplianceAlert]:
        """Check system resource utilization"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 95:
                return ComplianceAlert(
                    alert_id=f"RESOURCE-CPU-{int(time.time())}",
                    timestamp=datetime.now().isoformat(),
                    severity="MEDIUM",
                    rule_violated="System Performance - Resource utilization",
                    description=f"High CPU usage: {cpu_percent}%",
                    remediation="Check for runaway processes, consider system optimization",
                    context={"cpu_percent": cpu_percent}
                )

            # Memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                return ComplianceAlert(
                    alert_id=f"RESOURCE-MEM-{int(time.time())}",
                    timestamp=datetime.now().isoformat(),
                    severity="MEDIUM",
                    rule_violated="System Performance - Memory utilization",
                    description=f"High memory usage: {memory.percent}%",
                    remediation="Check for memory leaks, restart processes if needed",
                    context={"memory_percent": memory.percent, "available_gb": memory.available / (1024**3)}
                )

            # Disk space
            disk = psutil.disk_usage('.')
            if disk.percent > 95:
                return ComplianceAlert(
                    alert_id=f"RESOURCE-DISK-{int(time.time())}",
                    timestamp=datetime.now().isoformat(),
                    severity="HIGH",
                    rule_violated="System Performance - Disk space",
                    description=f"Low disk space: {disk.percent}% used",
                    remediation="Clean up disk space, remove unnecessary files",
                    context={"disk_percent": disk.percent, "free_gb": disk.free / (1024**3)}
                )

        except Exception:
            # Resource monitoring failures are not critical
            pass

        return None

    def handle_violations(self, violations: List[ComplianceAlert]):
        """Handle detected compliance violations"""
        self.violation_count += len(violations)
        self.last_violation_time = datetime.now()

        for violation in violations:
            # Log violation
            self.logger.error(f"COMPLIANCE VIOLATION: {violation.rule_violated} - {violation.description}")

            # Print to console
            print(f"\n🚨 COMPLIANCE VIOLATION DETECTED:")
            print(f"   📋 Rule: {violation.rule_violated}")
            print(f"   📄 Description: {violation.description}")
            print(f"   🔧 Remediation: {violation.remediation}")
            print(f"   ⏰ Time: {violation.timestamp}")
            print(f"   🔥 Severity: {violation.severity}")

            # Execute alert handlers
            for handler in self.alert_handlers:
                try:
                    handler(violation)
                except Exception as e:
                    self.logger.error(f"Alert handler failed: {e}")

            # Auto-remediation for critical violations
            if violation.severity == "CRITICAL":
                self.attempt_auto_remediation(violation)

    def attempt_auto_remediation(self, violation: ComplianceAlert):
        """Attempt automatic remediation for critical violations"""
        try:
            if "Multi-agent system" in violation.rule_violated:
                self.logger.info("Attempting auto-remediation: Restarting agent system")
                subprocess.run(
                    ['python', 'scripts/agent_health_manager.py', '--ensure'],
                    timeout=60
                )
                print("🔧 Auto-remediation attempted: Agent system restart")

        except Exception as e:
            self.logger.error(f"Auto-remediation failed: {e}")

    def log_healthy_check(self):
        """Log successful compliance check"""
        # Only log periodically to avoid spam
        if hasattr(self, '_last_healthy_log'):
            if (datetime.now() - self._last_healthy_log).total_seconds() < 300:  # 5 minutes
                return

        self.logger.info("Compliance check passed - All rules enforced")
        self._last_healthy_log = datetime.now()

    def add_alert_handler(self, handler):
        """Add custom alert handler"""
        self.alert_handlers.append(handler)

    def get_monitoring_report(self) -> Dict:
        """Generate monitoring status report"""
        return {
            'monitoring_active': self.monitoring_active,
            'violation_count': self.violation_count,
            'last_violation_time': self.last_violation_time.isoformat() if self.last_violation_time else None,
            'monitoring_interval': self.monitoring_interval,
            'uptime_hours': self.get_monitoring_uptime_hours(),
            'alert_handlers_count': len(self.alert_handlers)
        }

    def get_monitoring_uptime_hours(self) -> float:
        """Get monitoring uptime in hours"""
        if hasattr(self, '_monitor_start_time'):
            return (datetime.now() - self._monitor_start_time).total_seconds() / 3600
        return 0.0

    def load_monitor_state(self):
        """Load monitoring state from file"""
        try:
            if Path(self.monitor_state_file).exists():
                with open(self.monitor_state_file, 'r') as f:
                    state = json.load(f)
                    self.violation_count = state.get('violation_count', 0)
                    if state.get('last_violation_time'):
                        self.last_violation_time = datetime.fromisoformat(state['last_violation_time'])
        except Exception as e:
            self.logger.warning(f"Could not load monitor state: {e}")

    def save_monitor_state(self):
        """Save monitoring state to file"""
        try:
            state = {
                'violation_count': self.violation_count,
                'last_violation_time': self.last_violation_time.isoformat() if self.last_violation_time else None,
                'last_update': datetime.now().isoformat()
            }
            with open(self.monitor_state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save monitor state: {e}")


# Global monitor instance
compliance_monitor = ComplianceMonitor()


def start_compliance_monitoring():
    """Start real-time compliance monitoring"""
    compliance_monitor.start_monitoring()


def stop_compliance_monitoring():
    """Stop real-time compliance monitoring"""
    compliance_monitor.stop_monitoring()


def get_monitoring_status() -> Dict:
    """Get current monitoring status"""
    return compliance_monitor.get_monitoring_report()


def add_alert_handler(handler):
    """Add custom alert handler"""
    compliance_monitor.add_alert_handler(handler)


# Example alert handlers
def console_alert_handler(alert: ComplianceAlert):
    """Simple console alert handler"""
    print(f"🔔 ALERT: {alert.severity} - {alert.description}")


def log_alert_handler(alert: ComplianceAlert):
    """Log alert to file"""
    with open("logs/compliance_alerts.json", "a") as f:
        f.write(json.dumps(asdict(alert)) + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--start":
            print("🚨 Starting real-time compliance monitoring...")
            compliance_monitor._monitor_start_time = datetime.now()
            start_compliance_monitoring()

            try:
                while True:
                    time.sleep(60)
                    status = get_monitoring_status()
                    print(f"⏰ Monitoring active - Violations: {status['violation_count']} | Uptime: {status['uptime_hours']:.1f}h")
            except KeyboardInterrupt:
                print("\n🛑 Stopping compliance monitoring...")
                stop_compliance_monitoring()

        elif command == "--status":
            print("📊 Compliance Monitoring Status:")
            status = get_monitoring_status()
            print(json.dumps(status, indent=2))

        elif command == "--test":
            print("🧪 Testing compliance monitoring...")
            monitor = ComplianceMonitor()
            violations = monitor.check_all_compliance_rules()

            if violations:
                print(f"⚠️  Found {len(violations)} violations:")
                for v in violations:
                    print(f"  - {v.severity}: {v.description}")
            else:
                print("✅ No violations detected")

    else:
        print("Usage: python compliance_monitor.py [--start|--status|--test]")
        print("")
        print("Commands:")
        print("  --start   Start real-time monitoring (blocks until Ctrl+C)")
        print("  --status  Show current monitoring status")
        print("  --test    Run one-time compliance check")