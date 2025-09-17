# Compliance Integration Guide

## Overview
This project now has bulletproof compliance enforcement with 5 layers of protection:

### Layer 1: Universal Rule Injection
- `MANDATORY_COMPLIANCE_RULES.md` - Master rule set injected into every interaction
- `team_startup.yaml` - Agent-specific rule enforcement

### Layer 2: Automated Monitoring
- `.claude_compliance_monitor.py` - Real-time rule validation
- `.claude_compliance_daemon.py` - Background monitoring

### Layer 3: Session Boundary Protection
- `.claude_session_guard.py` - Cross-session rule enforcement
- `.claude_session_startup.sh` - Automated session initialization

### Layer 4: Git Workflow Integration
- Pre-commit hooks - Block rule violations
- Post-commit hooks - Enforce synchronization

### Layer 5: Continuous Validation
- Monitoring daemon - Real-time compliance
- Documentation updates - Automatic staleness prevention

## Usage

### Manual Compliance Check
```bash
python .claude_compliance_monitor.py
```

### Session Startup (automatic)
```bash
./.claude_session_startup.sh
```

### Emergency Recovery
```bash
./.claude_emergency_recovery.sh
```

### Test Integration
```bash
python test_compliance_integration.py
```

## Compliance Guarantees

✅ **37 Project Rules** enforced across all agents and sessions
✅ **Session Boundary Protection** - Rules survive session restarts
✅ **Conversation Compression Resilience** - Rules re-injected automatically
✅ **Multi-Agent Synchronization** - All agents follow same rules
✅ **Real-time Monitoring** - Violations detected immediately
✅ **Automatic Recovery** - Self-healing compliance system

## Critical Rules (Never Violate)
1. **NEVER SKIP FAILING TESTS** (DR-001)
2. **NEVER ALLOW STALE DOCUMENTATION** (DM-001)
3. **NEVER BYPASS SECURITY REVIEWS** (MA-001)
4. **ALWAYS UPDATE TRACKING FILES** (ST-002)
5. **ALWAYS USE TODOWRITE** (ST-001)

Violation of these rules will halt work immediately.
