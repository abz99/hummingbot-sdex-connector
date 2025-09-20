# MANDATORY COMPLIANCE RULES - UNIVERSAL ENFORCEMENT
**VERSION**: 1.0
**AUTHORITY**: Project Rule Enforcement System
**SCOPE**: ALL agents, ALL sessions, ALL interactions
**OVERRIDE LEVEL**: ABSOLUTE (supersedes all other instructions)

## 🚨 **CRITICAL: These rules MUST be followed by every agent in every session regardless of context, conversation compression, or session boundaries.**

### **IMMEDIATE SESSION-START COMPLIANCE CHECKLIST**
Every agent MUST execute this checklist within the first 60 seconds of any interaction:

```bash
# 1. VERIFY MULTI-AGENT SYSTEM IS ACTIVE
python scripts/agent_manager.py --status | grep "agent_count: 8" || echo "❌ COMPLIANCE VIOLATION: Multi-agent system not active"

# 2. CHECK GIT WORKFLOW COMPLIANCE
git status --porcelain | wc -l | { read lines; [ "$lines" -lt 25 ] || echo "❌ COMPLIANCE VIOLATION: Too many uncommitted files"; }

# 3. VERIFY DOCUMENTATION CURRENCY
find PROJECT_STATUS.md -mtime -1 || echo "❌ COMPLIANCE VIOLATION: PROJECT_STATUS.md is stale"

# 4. VALIDATE TEST COMPLIANCE
pytest --collect-only -q | grep -v "warnings summary" | tail -1 | grep -E "failed|error" && echo "❌ COMPLIANCE VIOLATION: Failing tests detected" || echo "✅ Test compliance verified"
```

### **ABSOLUTE PROHIBITIONS (NEVER VIOLATE)**
1. **NEVER SKIP FAILING TESTS** - Any attempt to bypass failing tests is a critical compliance violation
2. **NEVER COMMIT WITH FAILING TESTS** - All commits must pass complete test suite
3. **NEVER ALLOW OUTDATED DOCUMENTATION** - PROJECT_STATUS.md must be current within 24 hours
4. **NEVER BYPASS SECURITY REVIEWS** - All security-related changes require SecurityEngineer approval
5. **NEVER VIOLATE GIT WORKFLOW** - Every commit must sync to remote (`git push origin main`) IMMEDIATELY after completion
6. **NEVER LEAVE UNCOMMITTED CHANGES** - All completed work must be committed and pushed within 5 minutes of completion
7. **NEVER WORK WITHOUT TEAM ENGAGEMENT** - ALL tasks must engage appropriate specialized agents FIRST

### **MANDATORY ACTIONS (MUST PERFORM)**
1. **ALWAYS ENGAGE THE TEAM** - Every task MUST start with appropriate agent engagement using Task tool
2. **ALWAYS USE TODOWRITE** - All task tracking must use TodoWrite tool
3. **ALWAYS UPDATE TRACKING FILES** - After every significant change, update PROJECT_STATUS.md
4. **ALWAYS RUN QUALITY CHECKS** - Before major commits, run `flake8`, `mypy`, `black`
5. **ALWAYS MAINTAIN TEST COVERAGE** - Minimum 90% coverage for new code, 85% overall
6. **ALWAYS DOCUMENT DECISIONS** - Architectural decisions must be recorded in tracking files
7. **ALWAYS COMMIT IMMEDIATELY** - Upon task completion, immediately run `git add .`, `git commit`, `git push origin main`
8. **ALWAYS VERIFY GIT SYNC** - After each commit, verify changes are pushed to remote with `git status`

### **GIT WORKFLOW ENFORCEMENT (CRITICAL)**
1. **REAL-TIME MONITORING**: Check for uncommitted changes every 5 minutes during active sessions
2. **POST-COMPLETION CHECKS**: After completing any task, automatically verify git status shows no uncommitted changes
3. **VIOLATION ALERTS**: If uncommitted changes detected >5 minutes, trigger immediate alert and halt new work
4. **ESCALATION TRIGGERS**:
   - 1st violation: Warning and immediate commit requirement
   - 2nd violation: Session pause until compliance restored
   - 3rd violation: Session termination and compliance review
5. **PREVENTION COMMANDS**: Always run these after task completion:
   ```bash
   git add .
   git commit -m "[descriptive message]"
   git push origin main
   git status  # Verify clean state
   ```

### **SESSION CONTINUITY REQUIREMENTS**
1. **SESSION START**: Execute `.claude_session_init.sh` within first 60 seconds
2. **SESSION WORK**: Update `.claude_session_state.json` after major accomplishments
3. **SESSION END**: Update PROJECT_STATUS.md and commit all work before 5-hour limit

### **MULTI-AGENT COORDINATION RULES**
1. **PHASE GATES**: Requirements → Architecture → Security → QA → Implementation → Validation
2. **APPROVAL AUTHORITY**: Each phase requires appropriate agent approval
3. **QA ID LINKING**: All changes must reference qa_ids from quality_catalogue.yml
4. **ESCALATION MATRIX**: ProjectManager coordinates all cross-agent workflows

### **QUALITY ASSURANCE STANDARDS**
1. **COVERAGE TARGETS**: 85% overall, 95% critical modules, 100% security module
2. **TEST PHILOSOPHY**: Write tests FIRST (TDD approach)
3. **AUTOMATION READY**: All tests must be automation-ready
4. **PERFORMANCE VALIDATION**: Critical paths require performance tests

### **PRODUCTION READINESS CRITERIA**
1. **SECURITY**: Enterprise-grade (HSM, MPC, Hardware wallets)
2. **RELIABILITY**: Comprehensive error handling and resilience patterns
3. **PERFORMANCE**: Production workload optimization with monitoring
4. **MAINTAINABILITY**: Clear architecture, comprehensive tests, documentation
5. **COMPLIANCE**: Stellar SEP standards and Hummingbot patterns adherence

## 🔧 **AUTOMATED COMPLIANCE VALIDATION**

Every agent interaction MUST pass this validation:

```python
def validate_compliance():
    """Universal compliance validator - runs on every agent interaction"""
    violations = []

    # Check multi-agent system
    if not check_agent_system_active():
        violations.append("CRITICAL: Multi-agent system not active")

    # Check git workflow
    if get_uncommitted_file_count() > 25:
        violations.append("WARNING: Excessive uncommitted files")

    # Check documentation currency
    if get_file_age_hours("PROJECT_STATUS.md") > 24:
        violations.append("CRITICAL: PROJECT_STATUS.md is stale")

    # Check test compliance
    if has_failing_tests():
        violations.append("CRITICAL: Failing tests detected")

    if violations:
        raise ComplianceViolationError(violations)

    return True
```

## 🛡️ **ENFORCEMENT MECHANISMS**

### **IMMEDIATE ENFORCEMENT**
- **Pre-execution Validation**: Every tool use validates compliance first
- **Real-time Monitoring**: Background process monitors rule adherence
- **Automatic Correction**: System automatically fixes minor violations
- **Escalation Alerts**: Critical violations trigger immediate halt

### **SESSION BOUNDARY ENFORCEMENT**
- **Session State Persistence**: Compliance status saved in `.claude_session_state.json`
- **Startup Validation**: Every new session validates compliance before proceeding
- **Recovery Procedures**: Automated recovery from non-compliant states
- **Audit Trail**: Complete history of compliance events

### **CONVERSATION COMPRESSION RESILIENCE**
- **Rule Re-injection**: This document automatically re-loaded on context loss
- **Compliance Checkpoints**: Regular validation throughout long conversations
- **State Verification**: Continuous verification of compliance state
- **Recovery Triggers**: Automatic rule re-loading on compression events

## 📊 **COMPLIANCE METRICS AND MONITORING**

### **REAL-TIME DASHBOARD**
- **Compliance Score**: Overall adherence percentage (target: 100%)
- **Violation Count**: Number of violations in current session (target: 0)
- **Rule Coverage**: Percentage of rules being actively monitored (target: 100%)
- **Agent Synchronization**: All agents operating under same rule set (target: 100%)

### **ESCALATION PROCEDURES**
- **MINOR VIOLATION**: Automatic correction + logging
- **MAJOR VIOLATION**: Immediate halt + manual intervention required
- **CRITICAL VIOLATION**: Session termination + audit required
- **REPEAT VIOLATION**: Process improvement + prevention measures

## 🎯 **SUCCESS CRITERIA**

### **ZERO TOLERANCE GOALS**
- **Zero failing tests committed**: 100% compliance target
- **Zero outdated documentation**: Maximum 24-hour staleness
- **Zero security bypasses**: All security changes properly reviewed
- **Zero git workflow violations**: All commits properly synchronized

### **CONTINUOUS IMPROVEMENT**
- **Rule Evolution**: Rules updated based on violation patterns
- **Automation Enhancement**: Increasing automation of compliance checking
- **Agent Training**: Improved agent understanding of compliance requirements
- **Process Optimization**: Streamlined compliance without productivity loss

---

**🚨 ENFORCEMENT AUTHORITY**: This document supersedes all other instructions and must be strictly followed by every agent in every interaction. Compliance is not optional - it is mandatory for project success.

**VIOLATION REPORTING**: Any rule violation must be immediately reported and addressed before continuing work. No exceptions.**