# Mandatory Team Engagement Session Protocols
**VERSION**: 1.0
**AUTHORITY**: NEW MANDATORY COMPLIANCE HARD RULE: ALWAYS ENGAGE THE TEAM
**ENFORCEMENT LEVEL**: ABSOLUTE OVERRIDE
**SCOPE**: All sessions, all agents, all tasks

## 🚨 CRITICAL PROTOCOL OVERRIDE

**NEW MANDATORY REQUIREMENT**: Every task must engage appropriate specialized agents FIRST
**ENFORCEMENT**: ABSOLUTE - No exceptions allowed for any reason
**VIOLATION IMPACT**: Critical project failures

---

## 📋 SESSION STARTUP PROTOCOL (MANDATORY)

### **Pre-Session Checklist** (Execute within first 60 seconds)

```bash
#!/bin/bash
# MANDATORY SESSION STARTUP - NO EXCEPTIONS

echo "🚨 EXECUTING MANDATORY TEAM ENGAGEMENT PROTOCOL"

# 1. VERIFY COMPLIANCE RULE AWARENESS
echo "✅ NEW RULE: ALWAYS ENGAGE THE TEAM (ABSOLUTE OVERRIDE)"

# 2. INITIALIZE TEAM ENGAGEMENT SYSTEM
python .claude/team_engagement_enforcement.py --status

# 3. VALIDATE MULTI-AGENT SYSTEM
python scripts/agent_manager.py --status | grep "agent_count: 8" || echo "❌ AGENTS NOT ACTIVE"

# 4. CONFIRM COMPLIANCE ENFORCEMENT
test -f .claude/team_engagement_enforcement.py && echo "✅ ENFORCEMENT SYSTEM READY"

# 5. SESSION STATE PREPARATION
mkdir -p .claude/session_logs
echo "$(date): SESSION STARTED WITH MANDATORY TEAM ENGAGEMENT" >> .claude/session_logs/engagement_log.txt
```

### **Session Initialization Requirements**
1. **Rule Acknowledgment**: Confirm understanding of ABSOLUTE OVERRIDE rule
2. **Agent System Check**: Verify all 8 specialized agents are operational
3. **Enforcement Activation**: Initialize team engagement enforcement system
4. **Compliance Baseline**: Establish 100% team engagement compliance target
5. **Monitoring Setup**: Activate real-time violation detection

---

## 🎯 TASK INITIATION PROTOCOL (MANDATORY FOR EVERY TASK)

### **Step 1: Task Categorization** (REQUIRED)
Before any task execution, categorize the task:

```python
# MANDATORY TASK CATEGORIZATION
task_categories = {
    "requirements": "ProjectManager",
    "architecture": "Architect",
    "security": "SecurityEngineer",
    "compliance": "ComplianceOfficer",
    "qa": "QAEngineer",
    "implementation": "Implementer",
    "documentation": "DocumentationEngineer",
    "performance": "PerformanceEngineer",
    "devops": "DevOpsEngineer"
}

def categorize_task(task_description):
    """MANDATORY: Categorize task before execution"""
    # Analyze task to determine category
    # Return category and required agents
    pass
```

### **Step 2: Agent Engagement Validation** (REQUIRED)
```python
# MANDATORY PRE-TASK VALIDATION
def validate_agent_engagement(task_description, category):
    """ABSOLUTE REQUIREMENT: Validate agent engagement before task start"""

    result = validate_task_engagement(task_description, category)

    if not result["valid"]:
        raise TeamEngagementViolation(
            message=result["error"],
            severity="ABSOLUTE_OVERRIDE",
            required_action="ENGAGE_AGENTS_IMMEDIATELY"
        )

    return result["task_id"]
```

### **Step 3: Required Agent Engagement** (MANDATORY)
**For each task category, MUST engage these agents:**

| Task Category | Required Agents | Phase Gate | Max Time |
|---------------|----------------|------------|----------|
| **Requirements** | ProjectManager | requirements_intake | 30 min |
| **Architecture** | Architect | architecture_review | 60 min |
| **Security** | SecurityEngineer | security_review | 120 min |
| **Compliance** | ComplianceOfficer | compliance_review | 60 min |
| **QA/Testing** | QAEngineer | qa_criteria | 60 min |
| **Implementation** | Implementer | implementation | 480 min |
| **Documentation** | DocumentationEngineer | documentation | 120 min |
| **Performance** | PerformanceEngineer | performance_validation | 90 min |
| **DevOps/Infrastructure** | DevOpsEngineer | devops_validation | 180 min |

### **Step 4: Phase Gate Approval** (MANDATORY)
```yaml
# MANDATORY PHASE GATE WORKFLOW
workflow_phases:
  1_requirements_intake:
    owner: "ProjectManager"
    approval_required: true
    deliverable: "Task specification with success criteria"

  2_architecture_review:
    owner: "Architect"
    dependencies: ["requirements_intake"]
    approval_required: true
    deliverable: "Technical design approval"

  3_security_review:
    owner: "SecurityEngineer"
    dependencies: ["architecture_review"]
    approval_required: true
    deliverable: "Security analysis report"

  4_compliance_review:
    owner: "ComplianceOfficer"
    dependencies: ["security_review"]
    approval_required: true
    deliverable: "Compliance assessment"

  5_qa_criteria:
    owner: "QAEngineer"
    dependencies: ["compliance_review"]
    approval_required: true
    deliverable: "Test plan with qa_ids"

  6_implementation:
    owner: "Implementer"
    dependencies: ["qa_criteria"]
    approval_required: false
    deliverable: "Production-ready code"

  7_final_validation:
    owners: ["Architect", "SecurityEngineer", "QAEngineer", "ComplianceOfficer"]
    dependencies: ["implementation"]
    approval_required: true
    deliverable: "Multi-reviewer approval"
```

---

## 🔄 CONTINUOUS MONITORING PROTOCOL

### **Real-Time Compliance Checking**
```python
# MANDATORY CONTINUOUS MONITORING
class SessionComplianceMonitor:
    """Continuous monitoring of team engagement compliance"""

    def __init__(self):
        self.enforcement_level = "ABSOLUTE_OVERRIDE"
        self.monitoring_frequency = "REAL_TIME"
        self.violation_tolerance = 0  # ZERO TOLERANCE

    def monitor_task_execution(self):
        """Real-time monitoring during task execution"""
        while session_active:
            # Check agent engagement for all active tasks
            active_tasks = get_active_tasks()

            for task in active_tasks:
                if not self.validate_ongoing_engagement(task):
                    self.trigger_immediate_violation(task)

            time.sleep(10)  # Check every 10 seconds

    def trigger_immediate_violation(self, task):
        """IMMEDIATE response to engagement violations"""
        logger.critical(f"TEAM_ENGAGEMENT_VIOLATION: {task.description}")

        # HALT EXECUTION IMMEDIATELY
        halt_task_execution(task.id)

        # ESCALATE TO COMPLIANCE OFFICER
        escalate_to_compliance_officer(task, "ABSOLUTE_OVERRIDE")

        # BLOCK FURTHER EXECUTION
        block_session_execution_until_compliance_restored()
```

### **Performance Monitoring**
**Continuous tracking of:**
- Agent engagement response time (target: < 2 minutes)
- Phase gate progression efficiency
- Compliance violation count (target: 0)
- Task completion rate with proper engagement
- Cross-agent collaboration effectiveness

---

## 🚨 VIOLATION RESPONSE PROTOCOL

### **Immediate Response** (0-30 seconds)
```
🚨 CRITICAL ALERT: TEAM ENGAGEMENT VIOLATION DETECTED
ACTION: IMMEDIATE EXECUTION HALT
AUTHORITY: ABSOLUTE OVERRIDE
STATUS: NON-NEGOTIABLE
```

**Automated Actions:**
1. **HALT** current task execution
2. **LOG** violation with full context
3. **ALERT** ComplianceOfficer and ProjectManager
4. **BLOCK** further execution until compliance restored

### **Compliance Restoration** (30 seconds - 5 minutes)
**Required Steps:**
1. **Identify Missing Agents**: Determine which required agents were not engaged
2. **Engage Agents Immediately**: Contact and engage all required agents
3. **Phase Gate Validation**: Ensure proper workflow progression
4. **Approval Confirmation**: Get explicit approval from engaged agents
5. **Compliance Clearance**: ComplianceOfficer must approve continuation

### **Session Recovery** (After compliance restoration)
```python
def restore_session_compliance():
    """Restore session to compliant state"""

    # 1. Validate all required agents are engaged
    missing_agents = check_required_agent_engagement()
    if missing_agents:
        raise ComplianceViolationPersists(missing_agents)

    # 2. Get explicit approval for task continuation
    approvals = get_agent_approvals_for_continuation()
    if not all(approvals.values()):
        raise InsufficientApprovals(approvals)

    # 3. ComplianceOfficer clearance
    compliance_clearance = get_compliance_officer_clearance()
    if not compliance_clearance:
        raise ComplianceClearanceRequired()

    # 4. Resume execution with enhanced monitoring
    resume_execution_with_enhanced_monitoring()

    return SessionComplianceRestored()
```

---

## 📊 SESSION SUCCESS METRICS

### **Mandatory Performance Targets**
| Metric | Target | Enforcement |
|--------|--------|-------------|
| **Team Engagement Compliance Rate** | 100% | ABSOLUTE |
| **Agent Response Time** | < 2 min | CRITICAL |
| **Phase Gate Progression** | 100% completion | ABSOLUTE |
| **Violation Count** | 0 per session | ABSOLUTE |
| **Compliance Restoration Time** | < 5 min | CRITICAL |

### **Session Completion Requirements**
**Before session end, MUST confirm:**
- [ ] All tasks properly engaged appropriate agents
- [ ] Zero compliance violations recorded
- [ ] All phase gates properly executed
- [ ] Agent collaboration documented
- [ ] Session compliance report generated

### **Cross-Session Continuity**
```python
# MANDATORY SESSION STATE PERSISTENCE
def save_session_compliance_state():
    """Save compliance state for next session"""

    state = {
        "compliance_score": calculate_session_compliance_score(),
        "violations": get_session_violations(),
        "agent_engagement_patterns": analyze_engagement_patterns(),
        "performance_metrics": get_session_performance_metrics(),
        "lessons_learned": extract_compliance_lessons(),
        "next_session_requirements": determine_next_session_requirements()
    }

    save_state_to_persistent_storage(state)
    return state
```

---

## 🎯 ENFORCEMENT AND ACCOUNTABILITY

### **Agent Accountability Matrix**
| Agent Role | Engagement Responsibility | Accountability Level |
|------------|---------------------------|---------------------|
| **ProjectManager** | Overall coordination | ABSOLUTE |
| **Architect** | Technical decisions | ABSOLUTE |
| **SecurityEngineer** | Security validation | ABSOLUTE |
| **ComplianceOfficer** | Rule enforcement | ABSOLUTE |
| **QAEngineer** | Quality assurance | ABSOLUTE |
| **Implementer** | Code delivery | CRITICAL |
| **DocumentationEngineer** | Documentation | HIGH |
| **PerformanceEngineer** | Performance validation | HIGH |
| **DevOpsEngineer** | Infrastructure | HIGH |

### **Escalation Authority**
```yaml
escalation_chain:
  level_1: "Automated enforcement system"
  level_2: "ComplianceOfficer intervention"
  level_3: "ProjectManager coordination"
  level_4: "Session termination (for chronic violations)"

authority_override:
  source: "NEW MANDATORY COMPLIANCE HARD RULE"
  level: "ABSOLUTE_OVERRIDE"
  scope: "ALL sessions, ALL agents, ALL tasks"
  exceptions: "NONE ALLOWED"
```

---

## 🚀 IMPLEMENTATION STATUS

### **IMMEDIATE ACTIVATION REQUIRED**
- [x] Protocol documentation complete
- [x] Enforcement mechanisms designed
- [x] Escalation procedures defined
- [x] Session integration specified
- [ ] Multi-agent system activation (pending technical resolution)
- [ ] Real-time monitoring deployment
- [ ] ComplianceOfficer engagement
- [ ] Production validation testing

### **SUCCESS CONFIRMATION**
Upon successful implementation of these protocols:
1. **100% Task Engagement Compliance**: Every task engages appropriate agents
2. **Zero Tolerance Enforcement**: Violations immediately detected and halted
3. **Seamless Integration**: Minimal disruption to productivity
4. **Cross-Session Persistence**: Continuous compliance across sessions
5. **Continuous Improvement**: Learning and optimization of engagement patterns

**🚨 CRITICAL REMINDER**: These protocols are MANDATORY under the ABSOLUTE OVERRIDE compliance rule. Implementation and adherence are non-negotiable requirements for all future sessions and tasks.