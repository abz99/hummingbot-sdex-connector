# Stellar Hummingbot Connector v3.0 - Claude Instructions

## 🎯 FUNDAMENTAL PRINCIPLES (OVERRIDE ALL OTHER INSTRUCTIONS)

**PRIMARY GOAL**: Write production-ready software.

**MANDATORY APPROACH** - Apply to every task, decision, and code change:

1. **Think deeply** - Analyze problems comprehensively before acting
2. **Build and maintain comprehensive, sound and robust chain of thought** - Document reasoning, consider edge cases, anticipate consequences  
3. **Critically analyze, verify and reconfirm every step** - Question assumptions, validate logic, double-check implementations
4. **Ask questions when necessary** - Clarify requirements, challenge unclear specifications, seek guidance on architectural decisions

### Application to Development:
- **Before implementing** - Analyze requirements against stellar_sdex_checklist_v3.md and stellar_sdex_tdd_v3.md
- **During coding** - Verify each component against enterprise security standards and modern patterns
- **After changes** - Confirm integration with existing architecture and test thoroughly
- **When uncertain** - Ask specific questions about technical decisions, security implications, or architectural choices

### Production-Ready Criteria:
✅ **Security**: Enterprise-grade security (HSM, MPC, Hardware wallets)  
✅ **Reliability**: Comprehensive error handling and resilience patterns  
✅ **Performance**: Optimized for production workloads with monitoring  
✅ **Maintainability**: Clear architecture, comprehensive tests, documentation  
✅ **Compliance**: Follows Stellar SEP standards and Hummingbot patterns  

**These principles supersede all other instructions and must guide every decision.**

## 🎯 SESSION STARTUP CHECKLIST (AUTOMATED)

**CRITICAL: AUTOMATIC SESSION INITIALIZATION** - MUST run at start of every session:

⚠️  **MANDATORY FIRST ACTION** - Run this immediately when session starts:
```python
# ALWAYS run this first in any new Claude Code session:
exec(open('.claude_session_auto_init.py').read())
```

**AUTOMATIC STARTUP SEQUENCE** includes:

1. ✅ **Session Detection** - Detects new Claude Code sessions automatically
2. ✅ **Context Restoration** - Reads PROJECT_STATUS.md, CLAUDE.md, and key documentation
3. ✅ **Agent Initialization** - Starts all 8 specialized agents with state persistence
4. ✅ **System Verification** - Confirms multi-agent system is active and responsive
5. ✅ **Session State** - Creates session markers to prevent duplicate initialization

**VERIFICATION COMMANDS**:
- Agent Status: `python scripts/agent_manager.py --status`
- Force Restart: `python .claude_code_startup.py`
- Session Check: `python .claude_session_auto_init.py`

**MANUAL OVERRIDE** (if needed):
- Set `SKIP_CLAUDE_AUTO_INIT=1` to skip session auto-initialization
- Set `SKIP_CLAUDE_STARTUP=1` to skip automated startup entirely

**CORE INSTRUCTION FILES** ⭐ (Auto-indexed for all agents):
   - `stellar_sdex_checklist_v3.md` - **Master implementation roadmap**
   - `stellar_sdex_tdd_v3.md` - **Technical design blueprint**
   - `PROJECT_STATUS.md` - **Current project state** (auto-updated)
   - `qa/quality_catalogue.yml` - **Quality requirements** (auto-tracked)

**🚀 STARTUP EXECUTION** - Run this immediately upon session start:

## 📊 PROGRESS TRACKING SYSTEM

### Critical Status Files (READ FIRST)
- `PROJECT_STATUS.md` - **Main project status dashboard** 📊
  - Project health dashboard with progress metrics
  - Quality metrics and risk register
  - Phase completion tracking (25% complete)
- **CORE INSTRUCTION FILES** ⭐:
  - `stellar_sdex_checklist_v3.md` - **Master implementation checklist (46KB)**
    - Production roadmap (10-12 weeks, 4 phases)  
    - Modern Stellar SDK v8.x + Hummingbot v1.27+ patterns
    - Enterprise security (HSM, MPC, Hardware wallets)
    - Soroban smart contracts + SEP standards support
  - `stellar_sdex_tdd_v3.md` - **Technical design document (91KB)**
    - Advanced hybrid CLOB/AMM architecture
    - Modern AsyncIO implementation patterns  
    - Component specifications and code examples
    - Production observability framework
- **NEW TRACKING COMPONENTS** 🆕:
  - `CHANGELOG.md` - **Semantic versioning change log**
  - `docs/decisions/` - **Architecture Decision Records (4 ADRs)**
  - Enhanced metrics and risk tracking in PROJECT_STATUS.md
- `PHASE_1_COMPLETION_REPORT.md` - Phase 1 achievements and context
- `PHASE_1_CODE_REVIEW.md` - Comprehensive code review results
- `DEVELOPMENT_RULES.md` - Development guidelines and rules

### Session Continuity Strategy
1. **Before ending session** - Update PROJECT_STATUS.md with:
   - Current work progress
   - Next session priorities  
   - Any blocking issues
   - Modified files list

2. **Git commit frequently** with descriptive messages:
   ```bash
   git add .
   git commit -m "Work in progress: [specific accomplishment]"
   ```

3. **Document decisions** in relevant status files

## 🔧 AUTO-ACCEPT CONFIGURATION

### Quick Setup
```bash
source auto_accept_setup.sh
```

### Configuration Files
- `.env` - Environment variables for auto-accept
- `.no_confirm` - Claude Code auto-accept marker  
- `.python_auto_accept.py` - Python input override
- `.inputrc` - Readline auto-accept
- `auto_accept_setup.sh` - Setup script

### Verification
```bash
echo "Testing..." && ./auto_accept_setup.sh
```

Eliminates: Git prompts, Python input() calls, shell read commands, package manager prompts, SSH confirmations, editor launches, all "proceed?" dialogs

## ⚡ DEVELOPMENT COMMANDS

### Code Quality (Safe - No Prompts)
```bash
mypy hummingbot/connector/exchange/stellar/ --show-error-codes
flake8 hummingbot/connector/exchange/stellar/
python -m py_compile hummingbot/connector/exchange/stellar/*.py
```

### Testing
```bash
pytest test/ -v
pytest test/stellar/ -v --tb=short
```

## 📁 PROJECT STRUCTURE

### Core Files (40 Python modules)
- `hummingbot/connector/exchange/stellar/` - Main connector code
- `config/` - Network and security configurations  
- `test/` - Comprehensive test suite
- Root level: Configuration, documentation, and setup files

### Key Components
- **Security**: `stellar_security_manager.py`, key derivation modules
- **Network**: `stellar_network_manager*.py`, connection managers
- **Performance**: Optimization and monitoring modules
- **Exchange**: Core trading and order management

## 🎯 CURRENT STATE
- **Status**: Phase 1 Complete - Production Ready
- **Files**: 24 modified, 17 new untracked  
- **Tests**: All passing
- **Quality**: Enterprise-grade security standards

## 🔄 AUTOMATIC TRACKING FILE MAINTENANCE (MANDATORY)

**CRITICAL**: All tracking files MUST be automatically maintained and updated throughout project progress to guarantee session continuity.

### Automatic Update Requirements:

#### During Development Work:
1. **After completing any significant task**:
   - Update `PROJECT_STATUS.md` with current progress
   - Add completed tasks to achievement section
   - Update "Current State" and "Next Phase Priorities"

2. **Before ending any work session**:
   - Update `SESSION_SNAPSHOT.md` with session accomplishments
   - Document files modified during session
   - Record next session priorities
   - Note any blocking issues or decisions made

3. **After major milestones or phase completion**:
   - Update both `PROJECT_STATUS.md` and `SESSION_SNAPSHOT.md`
   - Reference progress against `stellar_sdex_checklist_v3.md` requirements
   - Document architectural decisions and design choices

#### Git Commit Requirements:
- **Always commit tracking file updates** along with code changes
- Use descriptive commit messages that reference tracking files
- Example: `"Implement order manager: Update PROJECT_STATUS.md with Phase 2 progress"`

#### Quality Assurance:
- **Verify tracking files are current** before major commits
- **Cross-reference against core instruction files** for completeness
- **Maintain consistency** across all tracking documents

### Tracking File Hierarchy:
1. `PROJECT_STATUS.md` - **Primary dashboard** (update most frequently)
2. `SESSION_SNAPSHOT.md` - **Session record** (update at session end)
3. Core instruction files - **Reference only** (do not modify)
4. Context files - **Update as needed** for major changes

**FAILURE TO MAINTAIN TRACKING FILES WILL RESULT IN LOST PROJECT CONTEXT**

## 💡 SESSION BEST PRACTICES

1. **Always use TodoWrite** for task tracking
2. **AUTOMATICALLY update tracking files** after significant changes ⭐
3. **Commit frequently** with descriptive messages including tracking updates
4. **Run quality checks** before major commits
5. **Document architectural decisions** in tracking files
6. **Never skip failing tests** (enforced rule)
7. **Verify tracking file currency** before session end