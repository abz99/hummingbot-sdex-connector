#!/bin/bash
# Claude Code Session Initialization Script
# MANDATORY: Run at start of every Claude Code session

echo "🚀 CLAUDE SESSION INITIALIZATION STARTING..."
echo "================================================"

# Check if session state exists
if [ -f ".claude_session_state.json" ]; then
    echo "📋 Found previous session state:"
    cat .claude_session_state.json | jq -r '
        "Last session: " + .last_session_end,
        "Workflow status: " + (.workflow_status // "unknown"),
        "Compliance: " + (if .compliance_checklist.startup_executed then "✅" else "❌" end)
    ' 2>/dev/null || echo "  (State file exists but not JSON formatted)"
else
    echo "🆕 New session - will create initial state"
fi

echo ""
echo "🤖 Initializing multi-agent system..."

# Initialize multi-agent system with timeout protection
timeout 60 python .claude_code_startup.py 2>/dev/null || {
    echo "❌ Multi-agent initialization timed out or failed"
    echo "   Attempting background initialization..."
    nohup python .claude_code_startup.py > /dev/null 2>&1 &
}

# Wait a moment for agents to start
sleep 2

# Check agent status
AGENT_COUNT=$(python scripts/agent_manager.py --status 2>/dev/null | jq -r '.agent_count // 0' 2>/dev/null || echo "0")
if [ "$AGENT_COUNT" -gt 0 ]; then
    echo "✅ Multi-agent system active ($AGENT_COUNT agents)"
else
    echo "⚠️  Multi-agent system not responding (proceeding anyway)"
fi

echo ""
echo "🔧 Checking git workflow compliance..."

# Check for uncommitted changes
UNCOMMITTED=$(git status --porcelain | wc -l)
if [ "$UNCOMMITTED" -eq 0 ]; then
    echo "✅ No uncommitted changes"
else
    echo "⚠️  $UNCOMMITTED uncommitted files detected"
    git status --short | head -5
fi

# Check if ahead of remote
if git status | grep -q "ahead"; then
    AHEAD=$(git status | grep "ahead" | grep -o '[0-9]\+' | head -1)
    echo "⚠️  $AHEAD commits ahead of remote - push recommended"
elif git status | grep -q "behind"; then
    BEHIND=$(git status | grep "behind" | grep -o '[0-9]\+' | head -1)
    echo "⚠️  $BEHIND commits behind remote - pull recommended"
else
    echo "✅ Git in sync with remote"
fi

echo ""
echo "📊 Checking documentation status..."

# Check PROJECT_STATUS.md age
if [ -f "PROJECT_STATUS.md" ]; then
    LAST_MODIFIED=$(stat -c "%Y" PROJECT_STATUS.md)
    CURRENT_TIME=$(date +%s)
    HOURS_OLD=$(( (CURRENT_TIME - LAST_MODIFIED) / 3600 ))

    if [ "$HOURS_OLD" -lt 2 ]; then
        echo "✅ PROJECT_STATUS.md is current (${HOURS_OLD}h old)"
    else
        echo "⚠️  PROJECT_STATUS.md is ${HOURS_OLD}h old - update recommended"
    fi
else
    echo "❌ PROJECT_STATUS.md not found"
fi

echo ""
echo "💾 Updating session state..."

# Update session state
cat > .claude_session_state.json << EOF
{
  "version": "1.0",
  "session_start": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "workflow_status": {
    "multi_agent_system": "$([ $AGENT_COUNT -gt 0 ] && echo 'active' || echo 'inactive')",
    "git_status": "$([ $UNCOMMITTED -eq 0 ] && echo 'clean' || echo 'dirty')",
    "documentation_status": "$([ $HOURS_OLD -lt 2 ] 2>/dev/null && echo 'current' || echo 'stale')"
  },
  "compliance_checklist": {
    "startup_executed": true,
    "agents_checked": true,
    "git_checked": true,
    "docs_checked": true
  },
  "session_context": {
    "agent_count": $AGENT_COUNT,
    "uncommitted_files": $UNCOMMITTED,
    "documentation_age_hours": $(echo "${HOURS_OLD:-999}" | head -c 3)
  }
}
EOF

echo "✅ Session state saved"

echo ""
echo "================================================"
echo "✅ SESSION INITIALIZATION COMPLETE"
echo ""

# Display quick status summary
echo "📋 QUICK STATUS:"
echo "   🤖 Agents: $([ $AGENT_COUNT -gt 0 ] && echo "✅ Active ($AGENT_COUNT)" || echo "❌ Inactive")"
echo "   🔧 Git: $([ $UNCOMMITTED -eq 0 ] && echo "✅ Clean" || echo "⚠️  $UNCOMMITTED uncommitted")"
echo "   📊 Docs: $([ $HOURS_OLD -lt 2 ] 2>/dev/null && echo "✅ Current" || echo "⚠️  Update needed")"

echo ""
echo "💡 Ready for development work!"
echo "   Next: Review PROJECT_STATUS.md for current phase and priorities"