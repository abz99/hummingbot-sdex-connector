#!/usr/bin/env python3
"""
Claude Compliance Daemon - Continuous Rule Monitoring
Runs in background to monitor compliance in real-time
"""

import time
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] DAEMON: %(message)s',
    handlers=[
        logging.FileHandler('logs/compliance_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ComplianceDaemon:
    def __init__(self):
        self.project_root = Path.cwd()
        self.running = True
        self.check_interval = 300  # 5 minutes

    def run_compliance_check(self):
        """Run compliance check and log results"""
        try:
            result = subprocess.run([
                "python", ".claude_compliance_monitor.py"
            ], capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                logger.info("✅ Compliance check passed")
            else:
                logger.warning(f"⚠️  Compliance violations detected: {result.stderr}")

        except Exception as e:
            logger.error(f"❌ Compliance check failed: {e}")

    def check_documentation_staleness(self):
        """Check if documentation is getting stale (DM-001)"""
        project_status = Path("PROJECT_STATUS.md")
        if project_status.exists():
            file_time = datetime.fromtimestamp(project_status.stat().st_mtime)
            age = datetime.now() - file_time

            if age > timedelta(hours=20):  # Warn before 24hr limit
                logger.warning("⚠️  PROJECT_STATUS.md approaching staleness limit")

    def monitor_test_failures(self):
        """Monitor for test failures (DR-001 enforcement)"""
        try:
            result = subprocess.run([
                "python", "-m", "pytest", "--collect-only", "-q"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error("🚨 CRITICAL: Test failures detected - Rule DR-001 violation risk")

        except Exception as e:
            logger.warning(f"Could not check test status: {e}")

    def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        logger.info("🔍 Running compliance monitoring cycle...")

        self.run_compliance_check()
        self.check_documentation_staleness()
        self.monitor_test_failures()

        logger.info("✅ Monitoring cycle complete")

    def start(self):
        """Start the monitoring daemon"""
        logger.info("🛡️  Compliance daemon starting...")

        while self.running:
            try:
                self.run_monitoring_cycle()
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("🛑 Daemon stopped by user")
                self.running = False
            except Exception as e:
                logger.error(f"❌ Daemon error: {e}")
                time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    daemon = ComplianceDaemon()
    daemon.start()
