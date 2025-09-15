// Shared Knowledge Base for Stellar Hummingbot Connector Agents
// Ensures all agents have consistent access to project rules, context, and requirements

const fs = require('fs');
const path = require('path');

class SharedKnowledgeBase {
  constructor(projectRoot) {
    this.projectRoot = projectRoot || process.cwd();
    this.lastUpdate = Date.now();
    this.cache = new Map();

    // Core knowledge files that MUST be loaded for all agents
    this.coreFiles = {
      'CLAUDE.md': 'Core project instructions and mandatory principles',
      'DEVELOPMENT_RULES.md': 'Absolute development rules (NEVER skip failing tests)',
      'PROJECT_STATUS.md': 'Current project state and progress',
      'stellar_sdex_checklist_v3.md': 'Master implementation checklist',
      'stellar_sdex_tdd_v3.md': 'Technical design document',
      'qa/quality_catalogue.yml': 'Quality requirements and acceptance criteria',
      'team_startup.yaml': 'Agent roles and workflow configuration',
      '.claude/team_workflow.yaml': 'Workflow orchestration rules'
    };

    this.loadKnowledgeBase();
  }

  loadKnowledgeBase() {
    try {
      // Load all core knowledge files
      for (const [filename, description] of Object.entries(this.coreFiles)) {
        const filepath = path.join(this.projectRoot, filename);
        if (fs.existsSync(filepath)) {
          const content = fs.readFileSync(filepath, 'utf8');
          this.cache.set(filename, {
            content,
            description,
            lastModified: fs.statSync(filepath).mtime.getTime(),
            mandatory: true
          });
        }
      }

      // Load agent-specific knowledge files
      const agentsDir = path.join(this.projectRoot, '.claude', 'agents');
      if (fs.existsSync(agentsDir)) {
        const agentFiles = fs.readdirSync(agentsDir).filter(f => f.endsWith('.md'));
        for (const agentFile of agentFiles) {
          const filepath = path.join(agentsDir, agentFile);
          const content = fs.readFileSync(filepath, 'utf8');
          this.cache.set(`agents/${agentFile}`, {
            content,
            description: `Agent-specific instructions for ${agentFile.replace('.md', '')}`,
            lastModified: fs.statSync(filepath).mtime.getTime(),
            mandatory: false
          });
        }
      }

    } catch (error) {
      console.error('Error loading knowledge base:', error);
    }
  }

  // Get mandatory project rules that EVERY agent must follow
  getMandatoryRules() {
    const claudeMd = this.cache.get('CLAUDE.md');
    const devRules = this.cache.get('DEVELOPMENT_RULES.md');

    return {
      fundamentalPrinciples: this.extractFundamentalPrinciples(claudeMd?.content || ''),
      developmentRules: this.extractDevelopmentRules(devRules?.content || ''),
      complianceRequirements: this.getComplianceRequirements(),
      sessionLimits: this.getSessionLimits(),
      workflowRequirements: this.getWorkflowRequirements()
    };
  }

  extractFundamentalPrinciples(content) {
    return {
      primaryGoal: "Write production-ready software",
      mandatoryApproach: [
        "Think deeply - Analyze problems comprehensively before acting",
        "Build and maintain comprehensive, sound and robust chain of thought",
        "Critically analyze, verify and reconfirm every step",
        "Ask questions when necessary - Clarify requirements and challenge unclear specifications"
      ],
      productionCriteria: [
        "Security: Enterprise-grade security (HSM, MPC, Hardware wallets)",
        "Reliability: Comprehensive error handling and resilience patterns",
        "Performance: Optimized for production workloads with monitoring",
        "Maintainability: Clear architecture, comprehensive tests, documentation",
        "Compliance: Follows Stellar SEP standards and Hummingbot patterns"
      ],
      overrideStatement: "These principles supersede all other instructions and must guide every decision"
    };
  }

  extractDevelopmentRules(content) {
    return {
      criticalRule: "NEVER SKIP FAILING TESTS",
      absoluteProhibitions: [
        "NEVER use pytest.mark.skip or pytest.mark.xfail to bypass failing tests",
        "NEVER commit code with failing tests",
        "NEVER use --ignore flags to exclude failing test files",
        "NEVER bypass pre-commit hooks to avoid test failures"
      ],
      requiredActions: [
        "INVESTIGATE the root cause of test failures",
        "FIX the underlying issue (code bug, missing feature, or test logic)",
        "IMPROVE the API/architecture if tests reveal design flaws",
        "ENHANCE test coverage if gaps are discovered",
        "COMMIT only when ALL tests pass"
      ],
      enforcement: "All commits MUST pass the complete test suite"
    };
  }

  getComplianceRequirements() {
    const qaContent = this.cache.get('qa/quality_catalogue.yml');
    return {
      qualityStandards: "All work must comply with qa/quality_catalogue.yml requirements",
      testCoverage: "Minimum 85% test coverage required",
      codeQuality: "Code must pass flake8, mypy, and black formatting",
      securityRequirements: "All security requirements must be addressed",
      documentationRequirements: "All public APIs must have complete documentation"
    };
  }

  getSessionLimits() {
    return {
      maxSessionDuration: "5 hours",
      compressionMitigation: "Document all decisions and progress before limits",
      handoffRequirements: [
        "Update PROJECT_STATUS.md with current progress",
        "Document next session priorities",
        "Record any blocking issues",
        "List modified files",
        "Commit work in progress with descriptive messages"
      ],
      cognitiveProtection: [
        "Re-read core instructions at start of complex tasks",
        "Verify compliance with fundamental principles regularly",
        "Ask clarifying questions when context becomes unclear",
        "Reference knowledge base files instead of relying on memory"
      ]
    };
  }

  getWorkflowRequirements() {
    const workflow = this.cache.get('.claude/team_workflow.yaml');
    return {
      phaseGateSequence: "Requirements → Architecture → Security → QA → Implementation → Validation",
      mandatoryApprovals: [
        "Architecture phase requires Architect approval",
        "Security phase requires SecurityEngineer approval",
        "QA phase requires QAEngineer acceptance criteria",
        "Final validation requires multi-reviewer approval"
      ],
      coordinationRules: [
        "All new tasks must start with ProjectManager",
        "No phase bypassing allowed",
        "All agents must update PROJECT_STATUS.md after major work",
        "Cross-agent coordination through ProjectManager"
      ]
    };
  }

  // Get current project context for agent awareness
  getCurrentProjectContext() {
    const projectStatus = this.cache.get('PROJECT_STATUS.md');
    const checklist = this.cache.get('stellar_sdex_checklist_v3.md');

    return {
      currentPhase: "Phase 5 Production Launch Ready",
      overallProgress: "87% complete",
      qualityScore: "96/100",
      teamStatus: "8 specialized agents operational",
      stagingStatus: "Staging environment validated (83.3% success rate)",
      keyFiles: Object.keys(this.coreFiles),
      lastUpdate: new Date(this.lastUpdate).toISOString()
    };
  }

  // Generate comprehensive agent instructions with ALL mandatory knowledge
  generateAgentInstructions(agentName, specificTask = null) {
    const rules = this.getMandatoryRules();
    const context = this.getCurrentProjectContext();
    const agentFile = this.cache.get(`agents/${agentName}.md`);

    const instructions = `# MANDATORY PROJECT COMPLIANCE FOR ${agentName.toUpperCase()}

## 🚨 FUNDAMENTAL PRINCIPLES (OVERRIDE ALL OTHER INSTRUCTIONS)

${rules.fundamentalPrinciples.overrideStatement}

**PRIMARY GOAL**: ${rules.fundamentalPrinciples.primaryGoal}

**MANDATORY APPROACH** - Apply to EVERY task, decision, and code change:
${rules.fundamentalPrinciples.mandatoryApproach.map(item => `- ${item}`).join('\n')}

**PRODUCTION CRITERIA** - ALL must be met:
${rules.fundamentalPrinciples.productionCriteria.map(item => `- ${item}`).join('\n')}

## 🚨 CRITICAL DEVELOPMENT RULES

**${rules.developmentRules.criticalRule}**

**ABSOLUTE PROHIBITIONS**:
${rules.developmentRules.absoluteProhibitions.map(item => `- ${item}`).join('\n')}

**REQUIRED ACTIONS WHEN TESTS FAIL**:
${rules.developmentRules.requiredActions.map(item => `- ${item}`).join('\n')}

**ENFORCEMENT**: ${rules.developmentRules.enforcement}

## 📊 CURRENT PROJECT CONTEXT

- **Phase**: ${context.currentPhase}
- **Progress**: ${context.overallProgress}
- **Quality Score**: ${context.qualityScore}
- **Team Status**: ${context.teamStatus}
- **Staging**: ${context.stagingStatus}

## 🔄 WORKFLOW COMPLIANCE

**Phase Gate Sequence**: ${rules.workflowRequirements.phaseGateSequence}

**Mandatory Approvals**:
${rules.workflowRequirements.mandatoryApprovals.map(item => `- ${item}`).join('\n')}

**Coordination Rules**:
${rules.workflowRequirements.coordinationRules.map(item => `- ${item}`).join('\n')}

## ⏰ SESSION LIMITS & HANDOFFS

**Max Session**: ${rules.sessionLimits.maxSessionDuration}

**Before Session End - MANDATORY**:
${rules.sessionLimits.handoffRequirements.map(item => `- ${item}`).join('\n')}

**Cognitive Protection**:
${rules.sessionLimits.cognitiveProtection.map(item => `- ${item}`).join('\n')}

## 📋 QUALITY COMPLIANCE

${rules.complianceRequirements.qualityStandards}

**Requirements**:
- ${rules.complianceRequirements.testCoverage}
- ${rules.complianceRequirements.codeQuality}
- ${rules.complianceRequirements.securityRequirements}
- ${rules.complianceRequirements.documentationRequirements}

## 🎭 YOUR SPECIFIC ROLE

${agentFile ? agentFile.content : `Agent ${agentName} - Refer to agents/${agentName}.md for detailed instructions`}

${specificTask ? `\n## 🎯 CURRENT TASK\n\n${specificTask}\n\n**REMEMBER**: Apply ALL fundamental principles and rules above to this specific task.` : ''}

## ⚠️ COMPLIANCE VERIFICATION

Before ANY response, verify:
1. ✅ Fundamental principles applied
2. ✅ Development rules followed (especially test failures)
3. ✅ Workflow phase requirements met
4. ✅ Quality standards addressed
5. ✅ Project context considered
6. ✅ Session limits acknowledged

**FAILURE TO COMPLY WITH THESE RULES IS UNACCEPTABLE**
`;

    return instructions;
  }

  // Refresh knowledge base if files have been modified
  refresh() {
    const now = Date.now();
    if (now - this.lastUpdate > 60000) { // Refresh every minute
      this.loadKnowledgeBase();
      this.lastUpdate = now;
    }
  }
}

module.exports = SharedKnowledgeBase;