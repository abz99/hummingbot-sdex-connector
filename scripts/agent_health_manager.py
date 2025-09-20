#!/usr/bin/env python3
"""
Agent Health Manager - Self-healing multi-agent system management
Ensures 100% agent system uptime and automatic recovery
"""

import json
import subprocess
import time
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import psutil


class AgentHealthManager:
    """Self-healing agent system management with automatic recovery"""

    def __init__(self):
        self.health_log_file = "logs/agent_health.log"
        self.agent_state_file = ".agent_health_state.json"
        self.recovery_attempts_file = ".agent_recovery_attempts.json"
        self.monitoring_active = False
        self.monitoring_thread = None
        self.max_recovery_attempts = 3
        self.health_check_interval = 30  # seconds
        self.setup_logging()

    def setup_logging(self):
        """Setup health monitoring logging"""
        Path("logs").mkdir(exist_ok=True)
        logging.basicConfig(
            filename=self.health_log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def ensure_system_operational(self) -> bool:
        """MANDATORY: Verify all 8 agents active and responsive"""
        try:
            self.logger.info("Starting comprehensive agent system health check")

            # Step 1: Check agent manager process
            if not self.is_agent_manager_running():
                self.logger.warning("Agent manager not running, attempting to start")
                if not self.start_agent_manager():
                    self.logger.error("Failed to start agent manager")
                    return False

            # Step 2: Verify agent count and status
            agent_status = self.get_agent_system_status()
            if not agent_status:
                self.logger.error("Could not get agent system status")
                return False

            # Step 3: Check individual agent health
            if not self.verify_agent_health(agent_status):
                self.logger.warning("Agent health issues detected, attempting recovery")
                if not self.recover_agent_system():
                    self.logger.error("Agent system recovery failed")
                    return False

            # Step 4: Verify system is not in 'stopped' state
            if agent_status.get('system_status') == 'stopped':
                self.logger.warning("System status is 'stopped', attempting to activate")
                if not self.activate_agent_system():
                    self.logger.error("Failed to activate agent system")
                    return False

            self.logger.info("Agent system health check passed")
            self.save_health_state({"last_healthy_check": datetime.now().isoformat()})
            return True

        except Exception as e:
            self.logger.error(f"Critical error in system health check: {e}")
            return False

    def is_agent_manager_running(self) -> bool:
        """Check if agent manager process is running"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = proc.info['cmdline']
                if cmdline and 'agent_manager.py' in ' '.join(cmdline):
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error checking agent manager process: {e}")
            return False

    def start_agent_manager(self) -> bool:
        """Start agent manager daemon"""
        try:
            self.logger.info("Starting agent manager daemon")

            # First try to initialize agents
            init_result = subprocess.run(
                ['python', 'scripts/agent_manager.py', '--init'],
                capture_output=True, text=True, timeout=30
            )

            if init_result.returncode != 0:
                self.logger.warning(f"Agent initialization warning: {init_result.stderr}")

            # Start daemon
            daemon_process = subprocess.Popen(
                ['python', 'scripts/agent_manager.py', '--daemon'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # Give it time to start
            time.sleep(10)

            # Check if it's running
            if self.is_agent_manager_running():
                self.logger.info("Agent manager daemon started successfully")
                return True
            else:
                self.logger.error("Agent manager daemon failed to start")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("Agent manager start timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error starting agent manager: {e}")
            return False

    def get_agent_system_status(self) -> Optional[Dict]:
        """Get current agent system status"""
        try:
            result = subprocess.run(
                ['python', 'scripts/agent_manager.py', '--status'],
                capture_output=True, text=True, timeout=15
            )

            if result.returncode != 0:
                self.logger.error(f"Agent status check failed: {result.stderr}")
                return None

            # Extract JSON from output
            lines = result.stdout.strip().split('\n')
            json_line = None

            for line in lines:
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    json_line = line
                    break

            if not json_line:
                self.logger.error("No JSON status found in agent manager output")
                return None

            status = json.loads(json_line)
            return status

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse agent status JSON: {e}")
            return None
        except subprocess.TimeoutExpired:
            self.logger.error("Agent status check timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error getting agent status: {e}")
            return None

    def verify_agent_health(self, agent_status: Dict) -> bool:
        """Verify individual agent health"""
        try:
            required_agents = [
                'ProjectManager', 'Architect', 'SecurityEngineer',
                'QAEngineer', 'Implementer', 'DevOpsEngineer',
                'PerformanceEngineer', 'DocumentationEngineer'
            ]

            agent_count = agent_status.get('agent_count', 0)
            if agent_count != 8:
                self.logger.warning(f"Expected 8 agents, found {agent_count}")
                return False

            agents = agent_status.get('agents', {})
            if not agents:
                self.logger.error("No agent details found in status")
                return False

            # Check each required agent
            for agent_name in required_agents:
                if agent_name not in agents:
                    self.logger.error(f"Required agent {agent_name} not found")
                    return False

                agent_info = agents[agent_name]
                agent_status_val = agent_info.get('status', 'unknown')

                # Allow 'initializing' status as it's common during startup
                if agent_status_val not in ['active', 'idle', 'initializing']:
                    self.logger.warning(f"Agent {agent_name} has status: {agent_status_val}")
                    return False

            self.logger.info("All 8 required agents are present and healthy")
            return True

        except Exception as e:
            self.logger.error(f"Error verifying agent health: {e}")
            return False

    def recover_agent_system(self) -> bool:
        """Attempt to recover failed agent system"""
        recovery_attempts = self.load_recovery_attempts()
        current_hour = datetime.now().strftime('%Y-%m-%d-%H')

        # Check if we've exceeded recovery attempts this hour
        if recovery_attempts.get(current_hour, 0) >= self.max_recovery_attempts:
            self.logger.error(f"Max recovery attempts ({self.max_recovery_attempts}) exceeded this hour")
            return False

        try:
            self.logger.info("Starting agent system recovery")

            # Step 1: Stop existing processes
            self.stop_agent_processes()
            time.sleep(5)

            # Step 2: Clean up state files
            self.cleanup_agent_state()
            time.sleep(2)

            # Step 3: Restart agent manager
            if not self.start_agent_manager():
                return False

            # Step 4: Wait and verify recovery
            time.sleep(15)
            final_status = self.get_agent_system_status()

            if final_status and self.verify_agent_health(final_status):
                self.logger.info("Agent system recovery successful")
                return True
            else:
                self.logger.error("Agent system recovery failed verification")
                return False

        except Exception as e:
            self.logger.error(f"Error during agent system recovery: {e}")
            return False
        finally:
            # Track recovery attempt
            recovery_attempts[current_hour] = recovery_attempts.get(current_hour, 0) + 1
            self.save_recovery_attempts(recovery_attempts)

    def activate_agent_system(self) -> bool:
        """Activate agent system if in stopped state"""
        try:
            self.logger.info("Attempting to activate agent system")

            # Try running the startup script
            startup_result = subprocess.run(
                ['python', '.claude_code_startup.py'],
                capture_output=True, text=True, timeout=60
            )

            if startup_result.returncode == 0:
                self.logger.info("Agent system activation successful")
                return True
            else:
                self.logger.warning(f"Startup script failed: {startup_result.stderr}")
                # Fall back to manual daemon start
                return self.start_agent_manager()

        except subprocess.TimeoutExpired:
            self.logger.error("Agent system activation timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error activating agent system: {e}")
            return False

    def stop_agent_processes(self):
        """Stop all agent-related processes"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = proc.info['cmdline']
                if cmdline and 'agent_manager.py' in ' '.join(cmdline):
                    self.logger.info(f"Stopping agent process {proc.info['pid']}")
                    proc.terminate()
                    # Wait for graceful termination
                    try:
                        proc.wait(timeout=10)
                    except psutil.TimeoutExpired:
                        proc.kill()
        except Exception as e:
            self.logger.error(f"Error stopping agent processes: {e}")

    def cleanup_agent_state(self):
        """Clean up agent state files for fresh start"""
        state_files = [
            '.agent_session_state.json',
            '.agent_workflow_state.json',
            'agent_system.lock'
        ]

        for state_file in state_files:
            try:
                file_path = Path(state_file)
                if file_path.exists():
                    file_path.unlink()
                    self.logger.info(f"Cleaned up state file: {state_file}")
            except Exception as e:
                self.logger.warning(f"Could not clean up {state_file}: {e}")

    def start_continuous_monitoring(self):
        """Start continuous health monitoring in background"""
        if self.monitoring_active:
            self.logger.warning("Health monitoring already active")
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        self.logger.info("Started continuous health monitoring")

    def stop_continuous_monitoring(self):
        """Stop continuous health monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        self.logger.info("Stopped continuous health monitoring")

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                if not self.ensure_system_operational():
                    self.logger.error("Health check failed during monitoring")

                time.sleep(self.health_check_interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.health_check_interval)

    def load_health_state(self) -> Dict:
        """Load health state from file"""
        try:
            if Path(self.agent_state_file).exists():
                with open(self.agent_state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load health state: {e}")
        return {}

    def save_health_state(self, state: Dict):
        """Save health state to file"""
        try:
            current_state = self.load_health_state()
            current_state.update(state)
            with open(self.agent_state_file, 'w') as f:
                json.dump(current_state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save health state: {e}")

    def load_recovery_attempts(self) -> Dict:
        """Load recovery attempts tracking"""
        try:
            if Path(self.recovery_attempts_file).exists():
                with open(self.recovery_attempts_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_recovery_attempts(self, attempts: Dict):
        """Save recovery attempts tracking"""
        try:
            with open(self.recovery_attempts_file, 'w') as f:
                json.dump(attempts, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save recovery attempts: {e}")

    def get_health_report(self) -> Dict:
        """Generate comprehensive health report"""
        try:
            agent_status = self.get_agent_system_status()
            health_state = self.load_health_state()
            recovery_attempts = self.load_recovery_attempts()

            return {
                'timestamp': datetime.now().isoformat(),
                'system_operational': self.ensure_system_operational(),
                'agent_manager_running': self.is_agent_manager_running(),
                'agent_status': agent_status,
                'health_state': health_state,
                'recovery_attempts': recovery_attempts,
                'monitoring_active': self.monitoring_active
            }

        except Exception as e:
            self.logger.error(f"Error generating health report: {e}")
            return {'error': str(e)}


# Global instance for easy access
agent_health_manager = AgentHealthManager()


def ensure_agents_operational() -> bool:
    """Main entry point for ensuring agent system is operational"""
    return agent_health_manager.ensure_system_operational()


def start_health_monitoring():
    """Start continuous health monitoring"""
    agent_health_manager.start_continuous_monitoring()


def stop_health_monitoring():
    """Stop continuous health monitoring"""
    agent_health_manager.stop_continuous_monitoring()


def get_health_status() -> Dict:
    """Get current health status"""
    return agent_health_manager.get_health_report()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--ensure":
            print("🔧 Ensuring agent system is operational...")
            if ensure_agents_operational():
                print("✅ Agent system is operational")
            else:
                print("❌ Agent system is not operational")

        elif command == "--monitor":
            print("📊 Starting continuous health monitoring...")
            start_health_monitoring()
            try:
                while True:
                    time.sleep(60)
                    print(f"⏰ Monitoring active: {datetime.now().strftime('%H:%M:%S')}")
            except KeyboardInterrupt:
                print("\n🛑 Stopping health monitoring...")
                stop_health_monitoring()

        elif command == "--status":
            print("📋 Agent Health Status:")
            status = get_health_status()
            print(json.dumps(status, indent=2))

        elif command == "--test":
            print("🧪 Testing Agent Health Manager...")
            manager = AgentHealthManager()

            print(f"Agent manager running: {manager.is_agent_manager_running()}")

            status = manager.get_agent_system_status()
            if status:
                print(f"Agent count: {status.get('agent_count', 'unknown')}")
                print(f"System status: {status.get('system_status', 'unknown')}")
            else:
                print("Could not get agent status")

    else:
        print("Usage: python agent_health_manager.py [--ensure|--monitor|--status|--test]")