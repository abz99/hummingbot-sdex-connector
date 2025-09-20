#!/usr/bin/env python3
"""
Git Workflow Enforcement System
Prevents violations of mandatory git sync requirements with automated monitoring and enforcement.
"""

import subprocess
import time
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class GitWorkflowEnforcer:
    """Automated enforcement of git workflow compliance with real-time monitoring."""

    def __init__(self):
        self.project_root = Path.cwd()
        self.violation_log_file = "logs/git_workflow_violations.json"
        self.state_file = ".git_workflow_state.json"
        self.max_uncommitted_time = 300  # 5 minutes in seconds
        self.violation_count = 0
        self.last_check_time = datetime.now()
        self.setup_logging()

    def setup_logging(self):
        """Setup violation logging."""
        Path("logs").mkdir(exist_ok=True)

    def check_git_status(self) -> Tuple[bool, List[str]]:
        """Check git status for uncommitted changes."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return False, [f"Git status failed: {result.stderr}"]

            uncommitted_files = []
            if result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        uncommitted_files.append(line.strip())

            return len(uncommitted_files) == 0, uncommitted_files

        except Exception as e:
            return False, [f"Error checking git status: {e}"]

    def get_last_commit_time(self) -> Optional[datetime]:
        """Get timestamp of last commit."""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%ct'],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                timestamp = int(result.stdout.strip())
                return datetime.fromtimestamp(timestamp)

        except Exception as e:
            print(f"Error getting last commit time: {e}")

        return None

    def get_uncommitted_duration(self) -> Optional[int]:
        """Calculate how long changes have been uncommitted."""
        state = self.load_state()

        # If no uncommitted changes tracked, check if any exist now
        clean_status, uncommitted_files = self.check_git_status()
        if clean_status:
            return 0

        # Check if we have a tracked start time for current uncommitted changes
        if 'uncommitted_since' in state:
            start_time = datetime.fromisoformat(state['uncommitted_since'])
            duration = (datetime.now() - start_time).total_seconds()
            return int(duration)

        # New uncommitted changes detected, start tracking
        self.save_state({'uncommitted_since': datetime.now().isoformat()})
        return 0

    def enforce_immediate_commit(self) -> bool:
        """Enforce immediate commit of outstanding changes."""
        print("🚨 CRITICAL: Uncommitted changes detected beyond 5-minute limit!")
        print("📋 MANDATORY_COMPLIANCE_RULES.md Rule #6: NEVER LEAVE UNCOMMITTED CHANGES")
        print("⚡ IMMEDIATE ACTION REQUIRED:")
        print()

        clean_status, uncommitted_files = self.check_git_status()
        if clean_status:
            print("✅ No uncommitted changes found - compliance restored")
            return True

        print("📁 Uncommitted files:")
        for file in uncommitted_files:
            print(f"   {file}")
        print()

        print("🔧 REQUIRED COMMANDS (run immediately):")
        print("   git add .")
        print("   git commit -m \"[compliance] Commit outstanding changes\"")
        print("   git push origin main")
        print("   git status  # Verify clean state")
        print()

        # Log violation
        self.log_violation("uncommitted_changes_timeout", {
            "duration_seconds": self.get_uncommitted_duration(),
            "uncommitted_files": uncommitted_files,
            "max_allowed_seconds": self.max_uncommitted_time
        })

        return False

    def check_compliance(self) -> Dict[str, any]:
        """Comprehensive compliance check."""
        clean_status, uncommitted_files = self.check_git_status()
        uncommitted_duration = self.get_uncommitted_duration()

        compliance_status = {
            'timestamp': datetime.now().isoformat(),
            'clean_git_status': clean_status,
            'uncommitted_files': uncommitted_files,
            'uncommitted_duration_seconds': uncommitted_duration,
            'violation_detected': False,
            'violation_type': None,
            'enforcement_action': None
        }

        # Check for violations
        if not clean_status and uncommitted_duration > self.max_uncommitted_time:
            compliance_status.update({
                'violation_detected': True,
                'violation_type': 'uncommitted_changes_timeout',
                'enforcement_action': 'immediate_commit_required'
            })

            self.violation_count += 1

            # Escalation based on violation count
            if self.violation_count >= 3:
                compliance_status['enforcement_action'] = 'session_termination_required'
                print("💥 CRITICAL: 3rd git workflow violation - SESSION TERMINATION REQUIRED")
            elif self.violation_count >= 2:
                compliance_status['enforcement_action'] = 'session_pause_required'
                print("⚠️ WARNING: 2nd git workflow violation - SESSION PAUSE REQUIRED")
            else:
                compliance_status['enforcement_action'] = 'immediate_commit_required'
                print("🚨 ALERT: 1st git workflow violation - IMMEDIATE COMMIT REQUIRED")

        # Clear tracking if status is clean
        if clean_status:
            self.clear_uncommitted_tracking()

        return compliance_status

    def auto_commit_and_push(self, message: str = None) -> bool:
        """Automatically commit and push changes with proper compliance."""
        try:
            # Check if there are changes to commit
            clean_status, uncommitted_files = self.check_git_status()
            if clean_status:
                print("✅ No changes to commit - git status is clean")
                return True

            print(f"📝 Auto-committing {len(uncommitted_files)} changed files...")

            # Stage all changes
            result = subprocess.run(['git', 'add', '.'], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to stage changes: {result.stderr}")
                return False

            # Commit with message
            if not message:
                message = f"🔧 Auto-commit: Compliance enforcement at {datetime.now().strftime('%H:%M:%S')}"

            commit_message = f"{message}\n\n🤖 Generated with [Claude Code](https://claude.ai/code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

            result = subprocess.run(
                ['git', 'commit', '-m', commit_message],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"❌ Failed to commit: {result.stderr}")
                return False

            # Push to remote
            result = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to push: {result.stderr}")
                return False

            print("✅ Successfully committed and pushed changes")

            # Verify clean status
            clean_status, _ = self.check_git_status()
            if clean_status:
                print("✅ Git status verified clean - compliance restored")
                self.clear_uncommitted_tracking()
                return True
            else:
                print("⚠️ Warning: Git status still shows uncommitted changes after push")
                return False

        except Exception as e:
            print(f"❌ Error in auto-commit: {e}")
            return False

    def start_monitoring(self, interval_seconds: int = 300):
        """Start continuous monitoring of git workflow compliance."""
        print(f"🔄 Starting git workflow monitoring (checking every {interval_seconds}s)")
        print("📋 Enforcing MANDATORY_COMPLIANCE_RULES.md git workflow requirements")
        print("⏹️  Press Ctrl+C to stop monitoring")
        print()

        try:
            while True:
                compliance_status = self.check_compliance()

                if compliance_status['violation_detected']:
                    violation_type = compliance_status['violation_type']
                    action = compliance_status['enforcement_action']

                    print(f"🚨 VIOLATION DETECTED: {violation_type}")
                    print(f"⚡ ENFORCEMENT ACTION: {action}")

                    if action == 'immediate_commit_required':
                        self.enforce_immediate_commit()
                    elif action == 'session_pause_required':
                        print("🛑 SESSION PAUSED - Fix git compliance before continuing")
                        break
                    elif action == 'session_termination_required':
                        print("💥 SESSION TERMINATED - Compliance review required")
                        sys.exit(1)

                else:
                    print(f"✅ Compliance check passed at {compliance_status['timestamp']}")

                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")

    def load_state(self) -> Dict:
        """Load enforcer state from file."""
        try:
            if Path(self.state_file).exists():
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_state(self, state: Dict):
        """Save enforcer state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")

    def clear_uncommitted_tracking(self):
        """Clear uncommitted changes tracking."""
        state = self.load_state()
        if 'uncommitted_since' in state:
            del state['uncommitted_since']
            self.save_state(state)

    def log_violation(self, violation_type: str, details: Dict):
        """Log compliance violation for audit trail."""
        violation_record = {
            'timestamp': datetime.now().isoformat(),
            'violation_type': violation_type,
            'violation_count': self.violation_count,
            'details': details
        }

        try:
            violations = []
            if Path(self.violation_log_file).exists():
                with open(self.violation_log_file, 'r') as f:
                    violations = json.load(f)

            violations.append(violation_record)

            with open(self.violation_log_file, 'w') as f:
                json.dump(violations, f, indent=2)

        except Exception as e:
            print(f"Warning: Could not log violation: {e}")


def main():
    """Main function for git workflow enforcement."""
    enforcer = GitWorkflowEnforcer()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--check":
            print("🔍 Checking git workflow compliance...")
            compliance_status = enforcer.check_compliance()

            if compliance_status['violation_detected']:
                print(f"❌ VIOLATION: {compliance_status['violation_type']}")
                print(f"⚡ ACTION: {compliance_status['enforcement_action']}")
                sys.exit(1)
            else:
                print("✅ Git workflow compliance verified")

        elif command == "--monitor":
            enforcer.start_monitoring()

        elif command == "--auto-commit":
            message = sys.argv[2] if len(sys.argv) > 2 else None
            if enforcer.auto_commit_and_push(message):
                print("✅ Auto-commit successful")
            else:
                print("❌ Auto-commit failed")
                sys.exit(1)

        elif command == "--enforce":
            if not enforcer.enforce_immediate_commit():
                sys.exit(1)

        else:
            print("Usage: python git_workflow_enforcer.py [--check|--monitor|--auto-commit|--enforce]")

    else:
        print("Git Workflow Enforcer - MANDATORY_COMPLIANCE_RULES.md Implementation")
        print("Usage:")
        print("  --check      : Check current compliance status")
        print("  --monitor    : Start continuous monitoring")
        print("  --auto-commit: Automatically commit and push changes")
        print("  --enforce    : Enforce immediate commit of violations")


if __name__ == "__main__":
    main()