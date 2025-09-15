# Session Restart Protocol
## Mandatory Steps for Every Claude Code Session Start

### 🚨 **IMMEDIATE ACTIONS (First 60 seconds)**

1. **Check Session State**
   ```bash
   # Verify session state exists and is current
   cat .claude_session_state.json | grep -E "(last_session_end|compliance_checklist)"
   ```

2. **Initialize Multi-Agent System**
   ```bash
   # MANDATORY: Always run on session start
   python .claude_code_startup.py

   # Verify agents are active
   python scripts/agent_manager.py --status | grep agent_count
   ```

3. **Git Workflow Check**
   ```bash
   # Check for uncommitted changes
   git status --porcelain

   # Check if ahead of remote
   git status | grep -E "(ahead|behind)"
   ```

4. **Documentation Sync Verification**
   ```bash
   # Check PROJECT_STATUS.md age
   stat -c "%Y" PROJECT_STATUS.md | awk '{print strftime("%Y-%m-%d %H:%M:%S", $1)}'
   ```

### 🔄 **5-HOUR SESSION LIMIT PROTOCOL**

#### Before Session End (Last 10 minutes):
1. **Commit All Work**
   ```bash
   git add -A
   git commit -m "Session end checkpoint: [description]"
   git push origin main
   ```

2. **Update PROJECT_STATUS.md**
   - Add session accomplishments
   - Update "Last Updated" timestamp
   - Document next session priorities

3. **Save Session State**
   ```bash
   # Update session state file
   echo "{
     \"last_session_end\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
     \"session_summary\": \"[brief description]\",
     \"next_priorities\": [\"priority1\", \"priority2\"],
     \"workflow_status\": \"compliant\"
   }" > .claude_session_state.json
   ```

#### New Session Start (First 5 minutes):
1. **Read Session State**
   ```bash
   cat .claude_session_state.json
   ```

2. **Execute Startup Protocol**
   ```bash
   ./SESSION_RESTART_PROTOCOL.sh
   ```

3. **Verify Compliance**
   ```bash
   python .claude_compliance_monitor.py
   ```

### 🤖 **CONVERSATION COMPRESSION RESILIENCE**

#### Context Preservation Strategy:
1. **Critical State Files** (Always preserve):
   - `.claude_session_state.json`
   - `PROJECT_STATUS.md`
   - `CLAUDE.md`
   - `DEVELOPMENT_RULES.md`

2. **Session Handoff Protocol**:
   ```
   HANDOFF_MESSAGE: "Session continuing from [timestamp].
   Multi-agent system: [status].
   Git status: [clean/dirty].
   Last task: [description].
   Next priority: [action]."
   ```

3. **Automatic State Recovery**:
   - Session state JSON contains all critical context
   - Multi-agent system preserves task queue
   - Git history maintains code context
   - PROJECT_STATUS.md maintains progress context

### ⚡ **AUTOMATION HOOKS**

#### `.claude_session_init.sh` (Auto-execute):
```bash
#!/bin/bash
echo "🚀 CLAUDE SESSION INITIALIZATION STARTING..."

# Check if session state exists
if [ -f ".claude_session_state.json" ]; then
    echo "📋 Found previous session state"
    cat .claude_session_state.json | grep -E "(last_session_end|workflow_status)"
else
    echo "🆕 New session - creating initial state"
fi

# Initialize multi-agent system
echo "🤖 Initializing multi-agent system..."
python .claude_code_startup.py

# Check git status
echo "🔧 Checking git workflow compliance..."
git status --short

# Verify PROJECT_STATUS.md is current
echo "📊 Checking documentation status..."
find PROJECT_STATUS.md -mtime -1 || echo "WARNING: PROJECT_STATUS.md may be stale"

echo "✅ SESSION INITIALIZATION COMPLETE"
```

### 🎯 **COMPLIANCE ENFORCEMENT MATRIX**

| Rule Category | Check Command | Auto-Fix Available | Manual Action Required |
|---------------|---------------|-------------------|----------------------|
| **Multi-Agent System** | `python scripts/agent_manager.py --status` | ✅ `python .claude_code_startup.py` | None |
| **Git Workflow** | `git status --porcelain` | ❌ | Commit and push changes |
| **Documentation** | `find PROJECT_STATUS.md -mtime -1` | ❌ | Update with session progress |
| **Session State** | `test -f .claude_session_state.json` | ✅ Create default state | None |

### 🔐 **EMERGENCY RECOVERY PROCEDURES**

#### If Multi-Agent System Fails:
```bash
# Kill stalled processes
pkill -f "agent_manager.py"
pkill -f "knowledge_base_watcher.py"

# Restart fresh
python .claude_code_startup.py

# Verify recovery
python scripts/agent_manager.py --status
```

#### If Git Workflow Broken:
```bash
# Force sync with remote
git fetch origin main
git reset --hard origin/main  # DANGER: Loses local changes
# OR
git stash && git pull && git stash pop
```

#### If Documentation Out of Sync:
```bash
# Emergency PROJECT_STATUS.md update
echo "**Last Updated:** $(date -u '+%Y-%m-%d %H:%M UTC')" >> PROJECT_STATUS.md
git add PROJECT_STATUS.md
git commit -m "Emergency documentation sync"
```

This protocol ensures **100% workflow compliance** across session boundaries and conversation compression events.