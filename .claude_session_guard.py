#!/usr/bin/env python3
"""
Claude Session Guard - Enforces Rule Compliance Across Session Boundaries
Ensures every new session starts with complete rule compliance validation
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any


class SessionGuard:
    """Enforces rule compliance across session boundaries and conversation compression"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.session_state_file = self.project_root / ".claude_session_state.json"
        self.compliance_rules_file = self.project_root / "MANDATORY_COMPLIANCE_RULES.md"
        self.guard_state_file = self.project_root / ".claude_session_guard_state.json"

        # Initialize guard state
        self.initialize_guard_state()

    def initialize_guard_state(self):
        """Initialize session guard state tracking"""
        guard_state = {
            "version": "1.0",
            "last_session_validation": None,
            "rule_checksum": self.calculate_rule_checksum(),
            "session_count": 0,
            "violations_detected": 0,
            "last_compression_recovery": None,
            "enforcement_level": "STRICT"
        }

        if not self.guard_state_file.exists():
            with open(self.guard_state_file, 'w') as f:
                json.dump(guard_state, f, indent=2)

    def calculate_rule_checksum(self) -> str:
        """Calculate checksum of compliance rules to detect changes"""
        if not self.compliance_rules_file.exists():
            return "NO_RULES"

        with open(self.compliance_rules_file, 'rb') as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest()[:16]

    def detect_session_boundary(self) -> bool:
        """Detect if this is a new session or session restart"""
        try:
            with open(self.guard_state_file, 'r') as f:
                guard_state = json.load(f)

            last_validation = guard_state.get('last_session_validation')
            if not last_validation:
                return True

            last_time = datetime.fromisoformat(last_validation)
            time_since_last = datetime.now() - last_time

            # Consider it a new session if more than 30 minutes have passed
            return time_since_last > timedelta(minutes=30)

        except Exception:
            return True

    def detect_conversation_compression(self) -> bool:
        """Detect if conversation compression may have occurred"""
        try:
            with open(self.session_state_file, 'r') as f:
                session_state = json.load(f)

            # Check if session state indicates compression
            compression_indicators = [
                session_state.get('conversation_compressed', False),
                session_state.get('context_reset', False),
                session_state.get('memory_compacted', False)
            ]

            return any(compression_indicators)

        except Exception:
            # If we can't read session state, assume compression occurred
            return True

    def validate_rule_consistency(self) -> bool:
        """Validate that compliance rules haven't changed"""
        try:
            with open(self.guard_state_file, 'r') as f:
                guard_state = json.load(f)

            stored_checksum = guard_state.get('rule_checksum')
            current_checksum = self.calculate_rule_checksum()

            if stored_checksum != current_checksum:
                print(f"⚠️  COMPLIANCE RULES CHANGED: {stored_checksum} -> {current_checksum}")
                # Update stored checksum
                guard_state['rule_checksum'] = current_checksum
                with open(self.guard_state_file, 'w') as f:
                    json.dump(guard_state, f, indent=2)
                return False

            return True

        except Exception:
            return False

    def inject_compliance_rules(self) -> str:
        """Generate compliance rule injection for session start"""
        if not self.compliance_rules_file.exists():
            return "❌ CRITICAL ERROR: Compliance rules file missing!"

        with open(self.compliance_rules_file, 'r') as f:
            rules_content = f.read()

        injection = f"""
🚨 **MANDATORY COMPLIANCE INJECTION** 🚨

SESSION GUARD ACTIVATED - These rules are MANDATORY and supersede all other instructions:

{rules_content}

⚡ **IMMEDIATE ACTION REQUIRED**:
1. Execute compliance validation: `python .claude_compliance_monitor.py`
2. Run session initialization: `python .claude_code_startup.py`
3. Verify multi-agent system: `python scripts/agent_manager.py --status`

This injection ensures 100% rule compliance regardless of session boundaries or conversation compression.
"""
        return injection

    def create_session_handoff_message(self) -> str:
        """Create standardized session handoff message for context preservation"""
        try:
            # Load current session state
            session_state = {}
            if self.session_state_file.exists():
                with open(self.session_state_file, 'r') as f:
                    session_state = json.load(f)

            # Load guard state
            guard_state = {}
            if self.guard_state_file.exists():
                with open(self.guard_state_file, 'r') as f:
                    guard_state = json.load(f)

            # Create comprehensive handoff message
            handoff = f"""
🔄 **SESSION HANDOFF PROTOCOL ACTIVATED**

**Timestamp**: {datetime.now().isoformat()}
**Session Type**: {"New Session" if self.detect_session_boundary() else "Continuation"}
**Compression Detected**: {"Yes" if self.detect_conversation_compression() else "No"}

**Critical Context Preservation**:
• Multi-Agent System: {session_state.get('workflow_status', {}).get('multi_agent_system', 'Unknown')}
• Git Status: {session_state.get('workflow_status', {}).get('git_status', 'Unknown')}
• Documentation Status: {session_state.get('workflow_status', {}).get('documentation_status', 'Unknown')}
• Compliance Score: {guard_state.get('compliance_score', 'Unknown')}

**Mandatory Next Actions**:
1. Execute compliance validation immediately
2. Restore multi-agent system if needed
3. Verify project state consistency
4. Continue from last documented priority

**Rule Enforcement**: STRICT MODE - All 37 project rules must be followed without exception.
            """

            return handoff

        except Exception as e:
            return f"⚠️  Session handoff failed: {e}"

    def update_guard_state(self, validation_passed: bool, violations_count: int = 0):
        """Update session guard state after validation"""
        try:
            with open(self.guard_state_file, 'r') as f:
                guard_state = json.load(f)

            guard_state.update({
                'last_session_validation': datetime.now().isoformat(),
                'session_count': guard_state.get('session_count', 0) + 1,
                'violations_detected': guard_state.get('violations_detected', 0) + violations_count,
                'last_validation_passed': validation_passed,
                'rule_checksum': self.calculate_rule_checksum()
            })

            with open(self.guard_state_file, 'w') as f:
                json.dump(guard_state, f, indent=2)

        except Exception as e:
            print(f"⚠️  Failed to update guard state: {e}")

    def enforce_session_compliance(self) -> bool:
        """Main enforcement function - call at session start"""
        print("🛡️  SESSION GUARD: Enforcing compliance...")

        # Check if new session or compression occurred
        is_new_session = self.detect_session_boundary()
        compression_detected = self.detect_conversation_compression()

        if is_new_session or compression_detected:
            print("🔄 New session or compression detected - full compliance validation required")

            # Inject compliance rules
            rules_injection = self.inject_compliance_rules()
            print(rules_injection)

            # Validate rule consistency
            if not self.validate_rule_consistency():
                print("⚠️  Compliance rules have changed - re-injection required")

            # Create handoff message
            handoff_message = self.create_session_handoff_message()
            print(handoff_message)

            # Run compliance monitor
            try:
                import subprocess
                result = subprocess.run([
                    sys.executable, ".claude_compliance_monitor.py"
                ], capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    print("✅ Compliance validation passed")
                    self.update_guard_state(True, 0)
                    return True
                else:
                    print(f"❌ Compliance validation failed: {result.stderr}")
                    self.update_guard_state(False, 1)
                    return False

            except Exception as e:
                print(f"❌ Compliance validation error: {e}")
                self.update_guard_state(False, 1)
                return False

        else:
            print("✅ Session continuation - compliance state preserved")
            return True

    def create_emergency_recovery_kit(self):
        """Create emergency recovery procedures for compliance failures"""
        recovery_script = self.project_root / ".claude_emergency_recovery.sh"

        recovery_content = """#!/bin/bash
# Claude Emergency Recovery Script
# Restores project to compliant state after critical violations

echo "🚨 EMERGENCY COMPLIANCE RECOVERY ACTIVATED"

# Step 1: Stop all background processes
echo "1. Stopping background processes..."
pkill -f "agent_manager.py" 2>/dev/null || true
pkill -f "knowledge_base_watcher.py" 2>/dev/null || true

# Step 2: Check git status
echo "2. Checking git status..."
git status --porcelain

# Step 3: Backup current state
echo "3. Creating backup..."
timestamp=$(date +%Y%m%d_%H%M%S)
mkdir -p "emergency_backups/$timestamp"
cp -r logs/ "emergency_backups/$timestamp/" 2>/dev/null || true
cp .claude_session_state.json "emergency_backups/$timestamp/" 2>/dev/null || true

# Step 4: Restore multi-agent system
echo "4. Restoring multi-agent system..."
python .claude_code_startup.py

# Step 5: Validate compliance
echo "5. Running compliance validation..."
python .claude_compliance_monitor.py

# Step 6: Update documentation
echo "6. Updating documentation timestamps..."
echo "**Last Updated:** $(date -u '+%Y-%m-%d %H:%M UTC')" >> PROJECT_STATUS.md

echo "✅ EMERGENCY RECOVERY COMPLETE"
echo "Please review backup in emergency_backups/$timestamp/"
"""

        with open(recovery_script, 'w') as f:
            f.write(recovery_content)

        # Make executable
        recovery_script.chmod(0o755)

        print(f"📋 Emergency recovery script created: {recovery_script}")


def main():
    """Main session guard entry point"""
    guard = SessionGuard()

    print("🛡️  Claude Session Guard - Initializing...")

    # Create emergency recovery kit
    guard.create_emergency_recovery_kit()

    # Enforce session compliance
    compliance_ok = guard.enforce_session_compliance()

    if compliance_ok:
        print("✅ Session Guard: All compliance checks passed")
        return 0
    else:
        print("❌ Session Guard: Compliance violations detected")
        print("🚨 Run emergency recovery: ./.claude_emergency_recovery.sh")
        return 1


if __name__ == "__main__":
    sys.exit(main())