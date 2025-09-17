#!/bin/bash
# Claude Session Startup Integration
# Automatically runs at session start to enforce compliance

echo "🚀 Claude Session Startup - Compliance Enforcement Active"

# 1. Run session guard (enforces rules across session boundaries)
if ! python .claude_session_guard.py; then
    echo "❌ Session Guard failed - compliance violations detected"
    exit 1
fi

# 2. Initialize multi-agent system (SC-002 enforcement)
if ! python .claude_code_startup.py; then
    echo "❌ Multi-agent system initialization failed"
    exit 1
fi

# 3. Validate current compliance state
if ! python .claude_compliance_monitor.py; then
    echo "❌ Compliance validation failed"
    exit 1
fi

# 4. Update session state
python -c "
import json
from datetime import datetime
from pathlib import Path

state = {
    'session_start': datetime.now().isoformat(),
    'compliance_validation': 'passed',
    'startup_complete': True,
    'workflow_status': {
        'multi_agent_system': 'active',
        'git_status': 'checked',
        'documentation_status': 'current'
    }
}

with open('.claude_session_state.json', 'w') as f:
    json.dump(state, f, indent=2)
"

echo "✅ Session startup complete - all compliance checks passed"
