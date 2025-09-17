#!/bin/bash
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
