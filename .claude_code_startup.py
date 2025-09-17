#!/usr/bin/env python3
"""
Claude Code Session Startup Automation

This script runs automatically when Claude Code sessions start,
initializing agents, knowledge bases, and monitoring systems.
"""

import os
import sys
import time
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Configure logging to be less verbose for startup
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class ClaudeCodeStartup:
    """Handles Claude Code session startup automation."""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.scripts_dir = self.project_root / "scripts"
        self.logs_dir = self.project_root / "logs"
        self.state_dir = self.project_root / "agent_state"
        
        # Ensure directories exist
        self.logs_dir.mkdir(exist_ok=True)
        self.state_dir.mkdir(exist_ok=True)
        
        self.startup_log = self.logs_dir / "claude_code_startup.log"
        
    def log_startup_event(self, message: str, level: str = "INFO"):
        """Log startup events to file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.startup_log, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {level}: {message}\n")
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        logger.info("🔍 Checking prerequisites...")
        
        # Check Python version
        if sys.version_info < (3, 11):
            logger.error("❌ Python 3.11+ required")
            return False
        
        # Check required files
        required_files = [
            "team_startup.yaml",
            "scripts/agent_manager.py",
            "scripts/knowledge_base_indexer.py"
        ]
        
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                logger.error(f"❌ Required file missing: {file_path}")
                return False
        
        # Check required dependencies
        try:
            import yaml
            import watchdog
        except ImportError as e:
            logger.error(f"❌ Missing dependency: {e}")
            return False
        
        logger.info("✅ Prerequisites check passed")
        return True
    
    def validate_configuration(self) -> bool:
        """Validate team startup configuration."""
        logger.info("📋 Validating configuration...")
        
        try:
            result = subprocess.run([
                sys.executable,
                str(self.scripts_dir / "validate_knowledge_base_config.py"),
                "team_startup.yaml"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("✅ Configuration validation passed")
                return True
            else:
                logger.error(f"❌ Configuration validation failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Configuration validation timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Configuration validation error: {e}")
            return False
    
    def initialize_knowledge_base(self) -> bool:
        """Initialize knowledge base indexing."""
        logger.info("📚 Initializing knowledge base...")
        
        try:
            # Check if indexing is needed
            result = subprocess.run([
                sys.executable,
                str(self.scripts_dir / "knowledge_base_indexer.py"),
                "--check-only"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("✅ Knowledge base is up-to-date")
                return True
            
            # Run indexing if needed
            logger.info("🔄 Updating knowledge base index...")
            result = subprocess.run([
                sys.executable,
                str(self.scripts_dir / "knowledge_base_indexer.py")
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("✅ Knowledge base indexing completed")
                return True
            else:
                logger.error(f"❌ Knowledge base indexing failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Knowledge base indexing timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Knowledge base indexing error: {e}")
            return False

    def verify_multi_agent_system_active(self) -> bool:
        """Verify multi-agent system is actually active with all 8 agents."""
        try:
            # Check agent manager status
            result = subprocess.run([
                sys.executable,
                str(self.scripts_dir / "agent_manager.py"),
                "--status"
            ], capture_output=True, text=True, timeout=15)

            if result.returncode != 0:
                logger.warning(f"⚠️  Agent status check failed: {result.stderr}")
                return False

            # Parse output to check for 8 active agents
            output = result.stdout
            if "System Status: active" not in output and "System Status: running" not in output:
                logger.warning("⚠️  System status is not active/running")
                return False

            # Count active agents (should be 8)
            active_agent_count = 0
            for line in output.split('\n'):
                if "✅" in line and "active" in line.lower():
                    active_agent_count += 1

            if active_agent_count < 8:
                logger.warning(f"⚠️  Only {active_agent_count}/8 agents are active")
                return False

            logger.info(f"✅ Multi-agent system verified: {active_agent_count}/8 agents active")
            return True

        except subprocess.TimeoutExpired:
            logger.warning("⚠️  Multi-agent verification timed out")
            return False
        except Exception as e:
            logger.warning(f"⚠️  Multi-agent verification error: {e}")
            return False

    def initialize_agents(self) -> bool:
        """Initialize persistent agents with robust retry mechanism."""
        logger.info("🤖 Initializing agents...")

        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Retry attempt {attempt + 1}/{max_retries} for agent initialization...")
                    time.sleep(retry_delay)

                # Initialize agents
                result = subprocess.run([
                    sys.executable,
                    str(self.scripts_dir / "agent_manager.py"),
                    "--init"
                ], capture_output=True, text=True, timeout=90)

                if result.returncode == 0:
                    logger.info("✅ Agents initialized successfully")

                    # CRITICAL: Verify agents are actually active
                    if self.verify_multi_agent_system_active():
                        logger.info("✅ Multi-agent system verification passed")
                        return True
                    else:
                        logger.warning(f"⚠️  Agents initialized but system not active (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            continue
                        else:
                            logger.error("❌ Failed to activate multi-agent system after all retries")
                            return False
                else:
                    logger.warning(f"⚠️  Agent initialization failed on attempt {attempt + 1}: {result.stderr}")
                    if attempt == max_retries - 1:
                        logger.error("❌ Agent initialization failed after all retries")
                        return False

            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️  Agent initialization timed out on attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    logger.error("❌ Agent initialization timed out after all retries")
                    return False
            except Exception as e:
                logger.warning(f"⚠️  Agent initialization error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"❌ Agent initialization failed after all retries: {e}")
                    return False

        return False
    
    def start_background_services(self) -> bool:
        """Start background monitoring services."""
        logger.info("⚙️ Starting background services...")
        
        try:
            # Start agent manager in background
            agent_manager_cmd = [
                sys.executable,
                str(self.scripts_dir / "agent_manager.py"),
                "--daemon"
            ]
            
            # Use nohup to keep process running even after session ends
            with open(self.logs_dir / "agent_manager_daemon.log", 'w') as log_file:
                subprocess.Popen(
                    agent_manager_cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
            
            # Start knowledge base watcher in background
            kb_watcher_cmd = [
                sys.executable,
                str(self.scripts_dir / "knowledge_base_watcher.py"),
                "--debounce", "10"
            ]
            
            with open(self.logs_dir / "knowledge_base_watcher.log", 'w') as log_file:
                subprocess.Popen(
                    kb_watcher_cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
            
            # Give services time to start
            time.sleep(2)
            
            logger.info("✅ Background services started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start background services: {e}")
            return False
    
    def display_startup_summary(self) -> Dict[str, Any]:
        """Display startup summary and system status."""
        logger.info("\n" + "="*60)
        logger.info("🚀 STELLAR HUMMINGBOT CONNECTOR - SYSTEM READY")
        logger.info("="*60)
        
        # Get system status
        try:
            result = subprocess.run([
                sys.executable,
                str(self.scripts_dir / "agent_manager.py"),
                "--status"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                status = json.loads(result.stdout)
                
                logger.info(f"📊 System Status: {status.get('workflow_health', {}).get('overall_health', 'unknown').upper()}")
                logger.info(f"🤖 Agents: {status.get('agent_count', 0)} initialized")
                logger.info(f"📋 Tasks: {status.get('task_count', 0)} tracked")
                
                # Display agent summary
                agents = status.get('agents', {})
                if agents:
                    logger.info("\n🤖 ACTIVE AGENTS:")
                    for name, agent_data in agents.items():
                        status_icon = {
                            'active': '🟢',
                            'idle': '🔵', 
                            'busy': '🟡',
                            'error': '🔴',
                            'stopped': '⚫'
                        }.get(agent_data.get('status', 'unknown'), '❓')
                        
                        logger.info(f"  {status_icon} {name} ({agent_data.get('category', 'unknown')})")
                
                # Display knowledge base status
                try:
                    kb_result = subprocess.run([
                        sys.executable,
                        str(self.scripts_dir / "knowledge_base_indexer.py"),
                        "--report"
                    ], capture_output=True, text=True, timeout=30)
                    
                    if kb_result.returncode == 0:
                        kb_status = json.loads(kb_result.stdout)
                        logger.info(f"\n📚 Knowledge Base: {kb_status.get('knowledge_base_count', 0)} sources indexed")
                        logger.info(f"📄 Files Tracked: {kb_status.get('tracked_file_count', 0)}")
                        
                        last_updated = kb_status.get('last_updated')
                        if last_updated:
                            logger.info(f"🕒 Last Updated: {last_updated}")
                
                except Exception:
                    logger.info("📚 Knowledge Base: Status unavailable")
                
                logger.info("\n🛠️ AVAILABLE COMMANDS:")
                logger.info("  • Project Status: cat PROJECT_STATUS.md")
                logger.info("  • Agent Status: python scripts/agent_manager.py --status")
                logger.info("  • KB Status: python scripts/knowledge_base_indexer.py --report")
                logger.info("  • Quality Check: python test_qa_requirements.py")
                
                logger.info("\n📖 KEY DOCUMENTATION:")
                logger.info("  • Master Checklist: stellar_sdex_checklist_v3.md")
                logger.info("  • Technical Design: stellar_sdex_tdd_v3.md")
                logger.info("  • Quality Guidelines: docs/QUALITY_GUIDELINES.md")
                logger.info("  • Security Model: SECURITY_REQUIREMENTS_DOCUMENT.md")
                
                logger.info("\n" + "="*60)
                logger.info("💡 TIP: All agents are now persistent and will maintain")
                logger.info("    context across sessions. Knowledge bases auto-update")
                logger.info("    when files change.")
                logger.info("="*60 + "\n")
                
                return status
                
        except Exception as e:
            logger.error(f"❌ Failed to get system status: {e}")
            return {}
    
    def run_startup_sequence(self) -> bool:
        """Run complete startup sequence."""
        start_time = time.time()
        
        self.log_startup_event("Starting Claude Code session startup sequence")
        
        # Run startup steps
        steps = [
            ("Prerequisites", self.check_prerequisites),
            ("Configuration", self.validate_configuration),
            ("Knowledge Base", self.initialize_knowledge_base),
            ("Agents", self.initialize_agents),
            ("Background Services", self.start_background_services)
        ]
        
        for step_name, step_func in steps:
            if not step_func():
                self.log_startup_event(f"Startup failed at step: {step_name}", "ERROR")
                logger.error(f"\n❌ Startup failed at: {step_name}")
                logger.error("Check logs/claude_code_startup.log for details")
                return False
        
        # Display summary
        self.display_startup_summary()
        
        duration = time.time() - start_time
        self.log_startup_event(f"Startup completed successfully in {duration:.1f}s")
        
        return True


def main():
    """Main entry point."""
    startup = ClaudeCodeStartup()
    
    # Check if we should skip startup (for testing/debugging)
    if os.environ.get('SKIP_CLAUDE_STARTUP'):
        print("⏭️ Skipping Claude Code startup (SKIP_CLAUDE_STARTUP set)")
        return True
    
    # Run startup sequence
    success = startup.run_startup_sequence()

    if not success:
        logger.error("❌ STARTUP SEQUENCE FAILED")
        sys.exit(1)

    # CRITICAL: Final validation of multi-agent system
    logger.info("🔍 Performing final multi-agent system validation...")
    if not startup.verify_multi_agent_system_active():
        logger.error("🚨 CRITICAL: Multi-agent system is not fully active after startup")
        logger.error("This violates compliance rule SC-002 and session cannot proceed")
        logger.error("Please check agent_manager logs and retry startup")
        sys.exit(2)

    logger.info("✅ STARTUP COMPLETE: Multi-agent system is active and verified")
    return True


if __name__ == '__main__':
    main()