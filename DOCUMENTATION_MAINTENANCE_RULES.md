# Documentation Maintenance Rules
**Established**: 2025-09-11  
**Authority**: ProjectManager Agent  
**Enforcement**: Mandatory for all team members and sessions  

## 🚨 **CRITICAL RULE: NEVER ALLOW OUTDATED PROJECT DOCUMENTATION**

### **Primary Directive**
Project status documentation MUST be updated immediately after any significant milestone, phase completion, or major code changes. Outdated documentation is a **critical project risk** that leads to:
- Lost context between sessions
- Incorrect priority assessments  
- Wasted development time
- Poor decision making based on stale information

---

## 📋 **MANDATORY DOCUMENTATION UPDATE TRIGGERS**

### **Immediate Updates Required** (Within same session)
1. **Phase Completion** - Any phase milestone reached
2. **Major Feature Implementation** - Significant functionality added
3. **Critical Bug Fixes** - Issues that affect project status
4. **Architecture Changes** - Design decisions or structural modifications
5. **Testing Milestones** - Test suite completions or major validations
6. **Session End** - Before ending any development session

### **Automatic Updates Required** (Daily/Weekly)
1. **Git Commit Activity** - After significant commit activity
2. **Team Configuration Changes** - Agent role or workflow modifications
3. **Quality Metrics Changes** - Coverage, performance, or security updates
4. **Timeline Adjustments** - Schedule or milestone modifications

---

## 📂 **CRITICAL DOCUMENTATION FILES**

### **Primary Status Documents** (Update Priority: CRITICAL)
1. **`PROJECT_STATUS.md`** - Master project dashboard
   - **Update Trigger**: Any milestone or phase change
   - **Max Age**: 24 hours from last significant change
   - **Responsibility**: ProjectManager + completing agent

2. **`LAST_SESSION.md`** - Session continuity document  
   - **Update Trigger**: End of every development session
   - **Max Age**: Current session only (must be updated before session end)
   - **Responsibility**: Last active agent in session

3. **`SESSION_SNAPSHOT.md`** - Current state summary
   - **Update Trigger**: Daily or after major changes
   - **Max Age**: 48 hours maximum
   - **Responsibility**: Automated system + manual verification

### **Secondary Status Documents** (Update Priority: HIGH)
4. **Phase Completion Reports** - `PHASE_X_COMPLETION_REPORT.md`
   - **Update Trigger**: Phase completion milestone
   - **Responsibility**: QAEngineer + ProjectManager validation

5. **`CHANGELOG.md`** - Version and change tracking
   - **Update Trigger**: Each git commit with user-facing changes
   - **Responsibility**: Implementer + DevOpsEngineer

6. **`team_startup.yaml`** - Team configuration
   - **Update Trigger**: Agent role or workflow changes
   - **Responsibility**: ProjectManager + affected agents

---

## 🔄 **AUTOMATED MAINTENANCE SYSTEM**

### **Documentation Update Script**
```bash
# Run automated documentation update
python scripts/update_project_docs.py

# Schedule regular updates (add to cron or CI/CD)
# Daily at 09:00 and 17:00
0 9,17 * * * cd /path/to/project && python scripts/update_project_docs.py
```

### **Pre-commit Hook Integration**
```bash
# Add to .git/hooks/pre-commit
#!/bin/bash
echo "Checking documentation synchronization..."
python scripts/update_project_docs.py --validate-only
if [ $? -ne 0 ]; then
    echo "❌ Documentation is outdated. Run: python scripts/update_project_docs.py"
    exit 1
fi
```

### **CI/CD Pipeline Integration**
- **GitHub Actions**: Add documentation check step to all workflows
- **Quality Gates**: Block PRs with outdated documentation
- **Automated Updates**: Daily scheduled runs to update metrics

---

## 📊 **DOCUMENTATION QUALITY STANDARDS**

### **Accuracy Requirements**
- ✅ **Dates**: All documents must contain current dates
- ✅ **Progress**: Phase progress must reflect actual completion status
- ✅ **Metrics**: Statistics must be current (commits, test counts, etc.)
- ✅ **Next Actions**: Must reflect actual immediate priorities

### **Completeness Requirements** 
- ✅ **Current Phase**: Clearly identified with accurate status
- ✅ **Recent Achievements**: Latest milestones and completions documented
- ✅ **Immediate Priorities**: Next session actions clearly defined
- ✅ **Team Status**: Agent roles and responsibilities current

### **Consistency Requirements**
- ✅ **Cross-Document Sync**: All documents must show same phase/progress
- ✅ **Terminology**: Consistent naming and status indicators
- ✅ **Format**: Standardized structure across all status documents

---

## ⚡ **ENFORCEMENT MECHANISMS**

### **Session Start Validation**
**Every session MUST begin with**:
1. Check `LAST_SESSION.md` date (must be recent)
2. Verify `PROJECT_STATUS.md` matches current git state
3. Update outdated documents BEFORE starting new work

### **Session End Requirements**  
**Every session MUST end with**:
1. Update `LAST_SESSION.md` with session accomplishments
2. Update `PROJECT_STATUS.md` if significant progress made
3. Run `python scripts/update_project_docs.py` to validate sync

### **Phase Gate Requirements**
**Before any phase completion approval**:
1. All documentation must be current and accurate
2. Phase completion report must be created/updated
3. Next phase priorities must be clearly documented
4. All team agents must acknowledge documentation accuracy

---

## 🔧 **RECOVERY PROCEDURES**

### **When Documentation is Discovered Outdated**

#### **Immediate Actions** (within current session)
1. **Stop all other work immediately**
2. **Audit all project documentation** using checklist below
3. **Update all outdated documents** to current state
4. **Validate synchronization** across all documents
5. **Document the gap** and create prevention measures

#### **Documentation Audit Checklist**
```bash
# Run full audit
python scripts/update_project_docs.py --audit

# Manual verification checklist:
□ LAST_SESSION.md date matches recent activity
□ PROJECT_STATUS.md shows correct phase and progress
□ All completion reports exist for completed phases  
□ Git commit count matches documentation claims
□ Next actions align with current project priorities
□ Team configuration reflects current agent roles
```

#### **Prevention Measures**
- Add calendar reminders for documentation updates
- Create documentation review in every phase gate
- Implement stricter automated validation
- Assign documentation stewardship to specific agents

---

## 👥 **AGENT RESPONSIBILITIES**

### **ProjectManager** (Primary Documentation Steward)
- **Daily**: Validate documentation accuracy
- **Weekly**: Run comprehensive documentation audit
- **Per Phase**: Update all status documents before phase gates
- **Per Session**: Ensure session end documentation updates

### **All Agents** (Secondary Responsibility)
- **After Major Work**: Update relevant documentation sections
- **Before Session End**: Contribute to session summary
- **During Reviews**: Validate documentation accuracy as part of review process

### **QAEngineer** (Documentation Quality Assurance)
- **Validation**: Include documentation checks in quality criteria
- **Testing**: Verify documentation matches actual system behavior
- **Standards**: Maintain documentation quality standards and templates

### **DevOpsEngineer** (Automation Implementation)  
- **CI/CD**: Implement automated documentation validation
- **Scheduling**: Set up regular documentation update automation
- **Monitoring**: Create alerts for documentation drift

---

## 🎯 **SUCCESS CRITERIA**

### **Never Again Situations**
- ✅ **No session starts with outdated LAST_SESSION.md**
- ✅ **No documentation shows incorrect phase or progress**  
- ✅ **No gaps >48 hours between documentation updates**
- ✅ **No manual discovery of outdated documentation**

### **Continuous Improvement Metrics**
- **Documentation Accuracy**: >99% (automated validation)
- **Update Frequency**: <24 hours average gap
- **Synchronization**: 100% consistency across documents
- **Automation Coverage**: 80%+ of updates automated

---

## 📞 **ESCALATION PROCEDURES**

### **Critical Documentation Issues**
- **Definition**: Documentation >72 hours outdated or fundamentally incorrect
- **Response**: Immediate session halt + full documentation audit + prevention analysis
- **Authority**: ProjectManager with all agents participation required
- **Resolution**: Must be resolved before any other work can proceed

### **Recurring Issues**
- **Definition**: Same documentation maintenance issue occurring >2 times
- **Response**: Process improvement + automation enhancement + responsibility reassignment
- **Review**: Full team retrospective on documentation processes

---

**🎯 BOTTOM LINE**: Documentation maintenance is NOT optional. It's a critical project success factor that must be maintained with the same rigor as code quality and security.**

*This rule document was established following the September 11, 2025 documentation crisis where LAST_SESSION.md was 5 days outdated, causing confusion about project phase and priorities.*