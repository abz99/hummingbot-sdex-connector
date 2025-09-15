# Team Workflow Guide - Stellar Hummingbot Connector v3.0

## Overview
This guide explains how to use the multi-agent team workflow for the Stellar Hummingbot connector project.

## Team Structure

### 👥 Agent Hierarchy
```
Coordinator: ProjectManager
├── Reviewers: Architect, SecurityEngineer, QAEngineer  
├── Implementers: Implementer, DevOpsEngineer
└── Specialists: PerformanceEngineer, DocumentationEngineer
```

## Workflow Process

### Phase-Gate Workflow
1. **Requirements Intake** → ProjectManager
2. **Architecture Review** → Architect  
3. **Security Review** → SecurityEngineer
4. **QA Criteria** → QAEngineer
5. **Implementation** → Implementer + Specialists
6. **Final Validation** → All Reviewers

## Using Claude Code Agents

### Activating Agents
```bash
# Use Claude Code agent system
/agent ProjectManager    # For task coordination
/agent Architect        # For technical design
/agent SecurityEngineer # For security validation
/agent QAEngineer       # For quality assurance
/agent Implementer      # For code development
```

### Agent Specializations

#### ProjectManager
- **Purpose**: Orchestrate workflows and track progress
- **When to Use**: Starting new tasks, status updates, coordination
- **Output**: Task status reports with phase progress

#### Architect  
- **Purpose**: Technical design and system architecture
- **When to Use**: System design, integration patterns, code reviews
- **Output**: Architectural analysis with implementation guidance

#### SecurityEngineer
- **Purpose**: Security validation and threat modeling
- **When to Use**: Security reviews, cryptographic implementations
- **Output**: Security analysis reports with risk assessment

#### QAEngineer
- **Purpose**: Quality assurance and testing strategy
- **When to Use**: Test planning, coverage analysis, quality gates
- **Output**: Quality assessment reports with acceptance criteria

#### Implementer
- **Purpose**: Code development and implementation
- **When to Use**: Feature development, bug fixes, code changes
- **Output**: Implementation delivery with quality checklist

#### DevOpsEngineer
- **Purpose**: Infrastructure and deployment automation
- **When to Use**: CI/CD, deployment, monitoring setup
- **Output**: DevOps implementation reports

#### PerformanceEngineer
- **Purpose**: Performance optimization and benchmarking
- **When to Use**: Performance issues, optimization, SLA validation
- **Output**: Performance analysis reports

#### DocumentationEngineer
- **Purpose**: Technical documentation and developer experience
- **When to Use**: API docs, user guides, integration examples
- **Output**: Documentation assessment reports

## Quality Gates

### Required Approvals
- **Architecture Phase**: Architect approval required
- **Security Phase**: SecurityEngineer approval required  
- **QA Phase**: QAEngineer acceptance criteria required
- **Final Validation**: Multi-reviewer approval (Architect + SecurityEngineer + QAEngineer)

### Quality Standards
- ✅ Code passes flake8 linting
- ✅ Code passes mypy type checking
- ✅ 85%+ test coverage
- ✅ Security requirements addressed
- ✅ Documentation complete

## Escalation Matrix

### Issue Types
1. **Blocking Issues**: Engage appropriate specialist
2. **Scope Creep**: Return to Requirements Intake (ProjectManager)
3. **Quality Issues**: Loop back to Implementer with feedback
4. **Timeline Concerns**: ProjectManager re-prioritization

## Example Workflow

### Scenario: Adding New Feature
1. **Start**: Contact ProjectManager for task intake
2. **Design**: Architect reviews technical approach
3. **Security**: SecurityEngineer validates security implications
4. **Quality**: QAEngineer defines acceptance criteria and tests
5. **Code**: Implementer develops with specialist support
6. **Review**: All reviewers validate final implementation
7. **Complete**: Task marked complete with all approvals

## Configuration Files

### Key Files
- `.claude/agents/`: Agent configurations
- `.claude/team_workflow.yaml`: Workflow automation
- `team_startup.yaml`: Team definitions and roles
- `PROJECT_STATUS.md`: Current progress tracking

### Verification
```bash
# Check team status
python scripts/team_status.py
```

## Best Practices

### For Users
1. **Start with ProjectManager** for all new tasks
2. **Follow phase gates** - don't skip approval steps
3. **Use appropriate specialist** for domain-specific issues
4. **Document decisions** in PROJECT_STATUS.md
5. **Maintain quality standards** throughout workflow

### For Agents
1. **Use structured output formats** defined in agent configs
2. **Reference qa_ids** for traceability
3. **Update PROJECT_STATUS.md** after major milestones
4. **Coordinate with other agents** through ProjectManager
5. **Escalate appropriately** when blocked

## Integration with Project

### Current Status
- **Project Phase**: Phase 5 Production Launch Ready
- **Progress**: 87% complete
- **Quality Score**: 96/100
- **Team Status**: All 8 agents operational ✅

### Key Project Files
- `stellar_sdex_checklist_v3.md`: Master implementation roadmap
- `stellar_sdex_tdd_v3.md`: Technical design blueprint  
- `qa/quality_catalogue.yml`: Quality requirements
- `DEVELOPMENT_RULES.md`: Development guidelines

## Monitoring and Reporting

### Automated Updates
- **PROJECT_STATUS.md**: Updated after each phase completion
- **Quality Tracking**: Continuous validation against qa/quality_catalogue.yml
- **Progress Reporting**: On-demand and milestone-based

### Success Metrics
- Phase-gate completion rates
- Quality standards compliance
- Agent utilization and effectiveness
- Time-to-completion for tasks