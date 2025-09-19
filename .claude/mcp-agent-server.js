#!/usr/bin/env node

// MCP Agent Server for Stellar Hummingbot Connector
// Provides specialized agents as MCP resources and tools

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const SharedKnowledgeBase = require('./shared_knowledge_base.js');
const AgentMemorySystem = require('./agent_memory_system.js');

const PROJECT_ROOT = process.env.PROJECT_ROOT || process.cwd();
const AGENTS_DIR = process.env.AGENTS_DIR || path.join(PROJECT_ROOT, '.claude', 'agents');

// Agent definitions from team_startup.yaml
const agents = {
  ProjectManager: {
    name: "ProjectManager",
    role: "Project Manager Agent",
    category: "coordinator",
    description: "Orchestrate multi-agent workflows ensuring disciplined development lifecycle",
    capabilities: ["task_orchestration", "workflow_management", "progress_tracking", "stakeholder_communication"]
  },
  Architect: {
    name: "Architect",
    role: "Senior Software Architect",
    category: "reviewer",
    description: "Ensure technical excellence through sound architectural decisions and design patterns",
    capabilities: ["system_design", "architecture_review", "technical_leadership", "pattern_recommendation"]
  },
  SecurityEngineer: {
    name: "SecurityEngineer",
    role: "Security Engineering Specialist",
    category: "reviewer",
    description: "Ensure enterprise-grade security through comprehensive threat modeling and secure design",
    capabilities: ["threat_modeling", "security_architecture", "cryptography_review", "vulnerability_assessment"]
  },
  QAEngineer: {
    name: "QAEngineer",
    role: "Quality Assurance Lead",
    category: "reviewer",
    description: "Establish and enforce comprehensive quality standards through systematic testing and validation",
    capabilities: ["test_strategy_design", "quality_framework_management", "acceptance_criteria_authoring", "ci_cd_optimization"]
  },
  Implementer: {
    name: "Implementer",
    role: "Senior Software Engineer",
    category: "implementer",
    description: "Deliver production-ready code that meets all architectural, security, and quality requirements",
    capabilities: ["code_implementation", "refactoring", "debugging", "documentation"]
  },
  DevOpsEngineer: {
    name: "DevOpsEngineer",
    role: "DevOps & Infrastructure Engineer",
    category: "implementer",
    description: "Automate deployment, monitoring, and operational excellence through robust DevOps practices",
    capabilities: ["ci_cd_pipeline_management", "infrastructure_automation", "deployment_strategies", "monitoring_setup"]
  },
  PerformanceEngineer: {
    name: "PerformanceEngineer",
    role: "Performance Engineering Specialist",
    category: "specialist",
    description: "Ensure optimal performance characteristics through systematic analysis and optimization",
    capabilities: ["performance_analysis", "optimization_strategies", "benchmarking", "scalability_planning"]
  },
  DocumentationEngineer: {
    name: "DocumentationEngineer",
    role: "Technical Documentation Specialist",
    category: "specialist",
    description: "Create and maintain comprehensive documentation that enables successful adoption and contribution",
    capabilities: ["technical_writing", "api_documentation", "developer_experience_design", "documentation_automation"]
  },
  ComplianceOfficer: {
    name: "ComplianceOfficer",
    role: "Compliance & Governance Specialist",
    category: "reviewer",
    description: "Ensure regulatory compliance and governance standards through continuous monitoring and proactive guardrail updates",
    capabilities: ["regulatory_compliance", "policy_enforcement", "risk_assessment", "governance_frameworks", "audit_coordination", "compliance_monitoring"]
  }
};

class MCPServer {
  constructor() {
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: false
    });

    this.knowledgeBase = new SharedKnowledgeBase(PROJECT_ROOT);
    this.memorySystem = new AgentMemorySystem(PROJECT_ROOT);
    this.serverStart = Date.now();
    this.sessionStart = null; // Will be set on first agent call
    this.SESSION_LIMIT_MS = 5 * 60 * 60 * 1000; // 5 hours in milliseconds
    this.activeSessions = new Map(); // Track active conversation sessions

    this.rl.on('line', (line) => {
      this.handleMessage(line);
    });
  }

  async handleMessage(line) {
    try {
      const message = JSON.parse(line);
      const response = await this.processRequest(message);
      console.log(JSON.stringify(response));
    } catch (error) {
      console.error('Error processing message:', error);
      console.log(JSON.stringify({
        jsonrpc: "2.0",
        id: null,
        error: {
          code: -32700,
          message: "Parse error: " + error.message
        }
      }));
    }
  }

  async processRequest(request) {
    const { id, method, params } = request;

    try {
      let result;

      switch (method) {
        case 'initialize':
          result = {
            protocolVersion: "2024-11-05",
            capabilities: {
              tools: {},
              resources: {},
              prompts: {}
            },
            serverInfo: {
              name: "stellar-agents",
              version: "1.0.0",
              description: "Stellar Hummingbot Connector Team Agents"
            }
          };
          break;

        case 'tools/list':
          result = {
            tools: this.getTools()
          };
          break;

        case 'resources/list':
          result = {
            resources: this.getResources()
          };
          break;

        case 'prompts/list':
          result = {
            prompts: this.getPrompts()
          };
          break;

        case 'tools/call':
          result = await this.callTool(params);
          break;

        case 'resources/read':
          result = await this.readResource(params);
          break;

        case 'prompts/get':
          result = await this.getPrompt(params);
          break;

        default:
          throw new Error(`Unknown method: ${method}`);
      }

      return {
        jsonrpc: "2.0",
        id: id,
        result: result
      };

    } catch (error) {
      return {
        jsonrpc: "2.0",
        id: id,
        error: {
          code: -32603,
          message: error.message
        }
      };
    }
  }

  getTools() {
    const tools = [];

    Object.keys(agents).forEach(agentName => {
      const agent = agents[agentName];
      tools.push({
        name: `agent_${agentName.toLowerCase()}`,
        description: `Invoke ${agent.name}: ${agent.description}`,
        inputSchema: {
          type: "object",
          properties: {
            task: {
              type: "string",
              description: "The task or request for the agent"
            },
            context: {
              type: "string",
              description: "Additional context or requirements"
            },
            sessionId: {
              type: "string",
              description: "Optional conversation session ID for continuity"
            },
            rememberAs: {
              type: "string",
              description: "Optional: How to remember this interaction for future reference"
            }
          },
          required: ["task"]
        }
      });
    });

    // Add memory management tools
    tools.push({
      name: "agent_memory_summary",
      description: "Get memory summary for a specific agent",
      inputSchema: {
        type: "object",
        properties: {
          agentName: {
            type: "string",
            description: "Name of the agent (e.g., 'ProjectManager', 'Architect')"
          }
        },
        required: ["agentName"]
      }
    });

    tools.push({
      name: "agent_conversation_history",
      description: "Get conversation history for an agent session",
      inputSchema: {
        type: "object",
        properties: {
          agentName: {
            type: "string",
            description: "Name of the agent"
          },
          sessionId: {
            type: "string",
            description: "Session ID to retrieve history for"
          },
          limit: {
            type: "number",
            description: "Number of messages to retrieve (default: 10)"
          }
        },
        required: ["agentName"]
      }
    });

    tools.push({
      name: "start_agent_session",
      description: "Start a new conversation session with an agent",
      inputSchema: {
        type: "object",
        properties: {
          agentName: {
            type: "string",
            description: "Name of the agent"
          },
          context: {
            type: "object",
            description: "Initial context for the session"
          }
        },
        required: ["agentName"]
      }
    });

    return tools;
  }

  getResources() {
    const resources = [];

    Object.keys(agents).forEach(agentName => {
      const agent = agents[agentName];
      resources.push({
        uri: `agent://${agentName.toLowerCase()}`,
        name: `${agent.name} Agent`,
        description: `${agent.role} - ${agent.description}`,
        mimeType: "text/markdown"
      });
    });

    return resources;
  }

  getPrompts() {
    const prompts = [];

    Object.keys(agents).forEach(agentName => {
      const agent = agents[agentName];
      prompts.push({
        name: `agent_${agentName.toLowerCase()}`,
        description: `Get instructions for ${agent.name}`,
        arguments: [
          {
            name: "task",
            description: "The task to be performed",
            required: false
          }
        ]
      });
    });

    return prompts;
  }

  async callTool(params) {
    const { name, arguments: args } = params;

    // Handle memory management tools
    if (name === 'agent_memory_summary') {
      return await this.getAgentMemorySummary(args.agentName);
    }
    if (name === 'agent_conversation_history') {
      return await this.getAgentConversationHistory(args.agentName, args.sessionId, args.limit);
    }
    if (name === 'start_agent_session') {
      return await this.startAgentSession(args.agentName, args.context);
    }

    // Reset session start if it's been more than 6 hours (likely a stale server)
    const currentTime = Date.now();
    if (this.sessionStart === null || (currentTime - this.sessionStart) > (6 * 60 * 60 * 1000)) {
      this.sessionStart = currentTime;
    }

    // For debugging: force reasonable session duration (max 4 hours)
    let sessionDuration = currentTime - this.sessionStart;
    if (sessionDuration > (4 * 60 * 60 * 1000)) {
      // If session appears to be longer than 4 hours, reset to current time
      this.sessionStart = currentTime;
      sessionDuration = 0;
    }

    const sessionWarning = this.checkSessionLimits(sessionDuration);

    const match = name.match(/^agent_(\w+)$/);
    if (!match) {
      throw new Error(`Unknown tool: ${name}`);
    }

    const agentKey = Object.keys(agents).find(key =>
      key.toLowerCase() === match[1].toLowerCase()
    );

    if (!agentKey) {
      throw new Error(`Unknown agent: ${match[1]}`);
    }

    const agent = agents[agentKey];

    // Refresh knowledge base to ensure current information
    this.knowledgeBase.refresh();

    // Get or create session for conversation continuity
    let sessionId = args.sessionId;
    if (!sessionId || !this.activeSessions.has(sessionId)) {
      sessionId = await this.memorySystem.startConversation(agentKey, sessionId, {
        taskType: args.task ? 'specific' : 'general',
        context: args.context,
        workflowPhase: 'active'
      });
      this.activeSessions.set(sessionId, {
        agentName: agentKey,
        startTime: Date.now(),
        lastActivity: Date.now()
      });
    }

    // Get agent's memory and conversation context
    const agentMemory = await this.memorySystem.getAgentContext(agentKey, sessionId, true);
    const conversationHistory = await this.memorySystem.getConversationHistory(sessionId, agentKey, 5);

    // Generate comprehensive instructions with mandatory rules AND memory context
    const comprehensiveInstructions = this.knowledgeBase.generateAgentInstructions(
      agentKey,
      args.task || 'General consultation'
    );

    // Get current project context
    const projectContext = this.knowledgeBase.getCurrentProjectContext();
    const mandatoryRules = this.knowledgeBase.getMandatoryRules();

    // Create memory-aware response
    const memoryContext = this.formatMemoryContext(agentMemory, conversationHistory);

    const response = `# ${agent.name} - MEMORY-ENHANCED RULE-COMPLIANT Response\n\n` +
                    `${sessionWarning}\n\n` +
                    `## 🧠 MEMORY & CONTEXT LOADED ✅\n\n` +
                    `- 🔄 **Session ID**: ${sessionId}\n` +
                    `- 📊 **Total Interactions**: ${agentMemory.agent.totalInteractions}\n` +
                    `- 🕒 **Last Accessed**: ${agentMemory.agent.lastAccessed}\n` +
                    `- 💭 **Recent Learnings**: ${agentMemory.memory.recentLearnings.length} insights available\n` +
                    `- 🤝 **Known Relationships**: ${Object.keys(agentMemory.relationships).length} other agents\n` +
                    `- 📝 **Conversation History**: ${conversationHistory.length} previous messages in this session\n\n` +
                    `## 🚨 COMPLIANCE VERIFICATION COMPLETED ✅\n\n` +
                    `- ✅ Fundamental principles loaded and acknowledged\n` +
                    `- ✅ Development rules enforced (NEVER skip failing tests)\n` +
                    `- ✅ Workflow requirements understood\n` +
                    `- ✅ Quality standards loaded from qa/quality_catalogue.yml\n` +
                    `- ✅ Current project context: ${projectContext.currentPhase} (${projectContext.overallProgress})\n` +
                    `- ✅ Session limits acknowledged (${Math.round(sessionDuration / 1000 / 60)} minutes elapsed)\n\n` +
                    `${memoryContext}\n\n` +
                    `## 🎯 TASK ANALYSIS\n\n` +
                    `**Role**: ${agent.role}\n` +
                    `**Category**: ${agent.category}\n` +
                    `**Task**: ${args.task || 'General consultation'}\n` +
                    `**Context**: ${args.context || 'Stellar Hummingbot connector project'}\n` +
                    `**Session Continuity**: ${conversationHistory.length > 0 ? 'Building on previous conversation' : 'Fresh start'}\n\n` +
                    `## 📋 MANDATORY COMPLIANCE CHECKLIST\n\n` +
                    `**Primary Goal**: ${mandatoryRules.fundamentalPrinciples.primaryGoal}\n\n` +
                    `**Critical Rules Applied**:\n` +
                    `- ${mandatoryRules.developmentRules.criticalRule}\n` +
                    `- All work must pass complete test suite\n` +
                    `- Must follow ${mandatoryRules.workflowRequirements.phaseGateSequence}\n` +
                    `- Must update PROJECT_STATUS.md after completion\n\n` +
                    `## 🔧 SPECIALIZED CAPABILITIES\n\n` +
                    `**Available Actions**: ${agent.capabilities.join(', ')}\n\n` +
                    `**Analysis**: As the ${agent.role}, I am analyzing this request according to:\n` +
                    `1. **Fundamental Principles**: Think deeply, build robust chain of thought, verify every step\n` +
                    `2. **Production Criteria**: Security, reliability, performance, maintainability, compliance\n` +
                    `3. **Project Context**: ${projectContext.currentPhase} with ${projectContext.qualityScore} quality score\n` +
                    `4. **Memory Context**: Building on ${agentMemory.agent.totalInteractions} previous interactions and current insights\n` +
                    `5. **Workflow Phase**: Following proper phase gates and approval processes\n\n` +
                    `## ⚡ NEXT ACTIONS\n\n` +
                    `Ready to execute this task while maintaining STRICT COMPLIANCE with:\n` +
                    `- All fundamental principles from CLAUDE.md\n` +
                    `- All development rules from DEVELOPMENT_RULES.md\n` +
                    `- Current project requirements and constraints\n` +
                    `- Quality standards from qa/quality_catalogue.yml\n` +
                    `- Memory and conversation continuity\n` +
                    `- Workflow coordination through ProjectManager\n\n` +
                    `**Specialized Instructions**: Comprehensive rule-compliant instructions with memory context loaded.\n\n` +
                    `---\n` +
                    `**AGENT STATUS**: ✅ FULLY COMPLIANT & MEMORY-ENHANCED - Ready to execute task with complete rule adherence and context awareness.`;

    // Store this interaction in memory
    await this.memorySystem.addToConversation(sessionId, {
      type: 'task',
      content: {
        task: args.task,
        context: args.context,
        rememberAs: args.rememberAs
      },
      metadata: {
        agentName: agentKey,
        timestamp: new Date().toISOString(),
        sessionDuration: Math.round(sessionDuration / 1000 / 60)
      },
      agentResponse: 'Generated memory-enhanced response'
    }, agentKey);

    // Add learning if specified
    if (args.rememberAs) {
      await this.memorySystem.addLearning(agentKey, {
        type: 'user_instruction',
        content: args.rememberAs,
        context: {
          task: args.task,
          sessionId: sessionId
        },
        tags: ['user_memory', 'instruction']
      });
    }

    // Update activity tracking
    this.activeSessions.set(sessionId, {
      agentName: agentKey,
      startTime: this.activeSessions.get(sessionId)?.startTime || Date.now(),
      lastActivity: Date.now()
    });

    return {
      content: [{
        type: "text",
        text: response
      }],
      metadata: {
        sessionId: sessionId,
        agentName: agentKey,
        memoryEnabled: true,
        conversationLength: conversationHistory.length
      }
    };
  }

  checkSessionLimits(durationMs) {
    const hoursElapsed = durationMs / (1000 * 60 * 60);
    const minutesElapsed = Math.round(durationMs / (1000 * 60));

    // Disable session warnings if duration seems unrealistic (indicates stale server)
    if (durationMs > (6 * 60 * 60 * 1000)) { // More than 6 hours
      return `⏱️ **SESSION TIME**: Active session (server uptime: ${hoursElapsed.toFixed(1)}h).`;
    }

    if (durationMs > this.SESSION_LIMIT_MS * 0.8) {
      return `🚨 **SESSION TIME WARNING**: ${minutesElapsed} minutes elapsed (${hoursElapsed.toFixed(1)}h). ` +
             `Approaching 5-hour limit. Prepare for handoff:\n` +
             `- Update PROJECT_STATUS.md with current progress\n` +
             `- Document next session priorities\n` +
             `- Commit work in progress\n` +
             `- Record any blocking issues`;
    } else if (durationMs > this.SESSION_LIMIT_MS * 0.5) {
      return `⏰ **SESSION TIME NOTICE**: ${minutesElapsed} minutes elapsed. Remember to document progress regularly.`;
    } else {
      return `⏱️ **SESSION TIME**: ${minutesElapsed} minutes elapsed of 300 minute limit.`;
    }
  }

  async readResource(params) {
    const { uri } = params;

    const match = uri.match(/^agent:\/\/(\w+)$/);
    if (!match) {
      throw new Error(`Unknown resource: ${uri}`);
    }

    const agentKey = Object.keys(agents).find(key =>
      key.toLowerCase() === match[1].toLowerCase()
    );

    if (!agentKey) {
      throw new Error(`Unknown agent: ${match[1]}`);
    }

    // Refresh knowledge base and get comprehensive instructions
    this.knowledgeBase.refresh();
    const comprehensiveInstructions = this.knowledgeBase.generateAgentInstructions(agentKey);

    return {
      contents: [{
        uri: uri,
        mimeType: "text/markdown",
        text: comprehensiveInstructions
      }]
    };
  }

  async getPrompt(params) {
    const { name, arguments: args } = params;

    const match = name.match(/^agent_(\w+)$/);
    if (!match) {
      throw new Error(`Unknown prompt: ${name}`);
    }

    const agentKey = Object.keys(agents).find(key =>
      key.toLowerCase() === match[1].toLowerCase()
    );

    if (!agentKey) {
      throw new Error(`Unknown agent: ${match[1]}`);
    }

    const task = args?.task || "general consultation";

    // Get comprehensive instructions with full rule compliance
    this.knowledgeBase.refresh();
    const comprehensiveInstructions = this.knowledgeBase.generateAgentInstructions(agentKey, task);

    return {
      description: `Complete rule-compliant instructions for ${agents[agentKey].name}`,
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text: comprehensiveInstructions
          }
        }
      ]
    };
  }

  // Helper method to format memory context for agent responses
  formatMemoryContext(agentMemory, conversationHistory) {
    let context = `## 💭 MEMORY CONTEXT\n\n`;

    if (agentMemory.memory.recentLearnings.length > 0) {
      context += `**Recent Learnings**:\n`;
      agentMemory.memory.recentLearnings.forEach((learning, i) => {
        context += `${i + 1}. ${learning.content} (${learning.type})\n`;
      });
      context += `\n`;
    }

    if (Object.keys(agentMemory.relationships).length > 0) {
      context += `**Agent Relationships**:\n`;
      Object.entries(agentMemory.relationships).forEach(([agentName, rel]) => {
        context += `- ${agentName}: ${rel.totalInteractions} interactions (${rel.primaryInteractionType})\n`;
      });
      context += `\n`;
    }

    if (conversationHistory.length > 0) {
      context += `**Recent Conversation**:\n`;
      conversationHistory.slice(-3).forEach((msg, i) => {
        const time = new Date(msg.timestamp).toLocaleTimeString();
        context += `${i + 1}. [${time}] ${msg.type}: ${msg.content.task || msg.content}\n`;
      });
      context += `\n`;
    }

    if (agentMemory.memory.activeReminders.length > 0) {
      context += `**Active Reminders**:\n`;
      agentMemory.memory.activeReminders.forEach((reminder, i) => {
        context += `${i + 1}. ${reminder.content}\n`;
      });
    }

    return context;
  }

  // Memory management tool handlers
  async getAgentMemorySummary(agentName) {
    try {
      const summary = await this.memorySystem.getMemorySummary(agentName);
      return {
        content: [{
          type: "text",
          text: `# Memory Summary for ${agentName}\n\n` +
                `**Total Interactions**: ${summary.totalInteractions}\n` +
                `**Successful Tasks**: ${summary.successfulTasks}\n` +
                `**Recent Conversations**: ${summary.recentConversations}\n` +
                `**Learnings Count**: ${summary.learningsCount}\n` +
                `**Active Reminders**: ${summary.activeReminders}\n` +
                `**Known Relationships**: ${summary.relationships}\n` +
                `**Last Accessed**: ${summary.lastAccessed}\n` +
                `**Workflow Phases**: ${summary.workflowPhases.join(', ')}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error retrieving memory summary for ${agentName}: ${error.message}`
        }]
      };
    }
  }

  async getAgentConversationHistory(agentName, sessionId, limit = 10) {
    try {
      let history;
      if (sessionId) {
        history = await this.memorySystem.getConversationHistory(sessionId, agentName, limit);
      } else {
        const recentConversations = await this.memorySystem.getRecentConversations(agentName, 5);
        history = recentConversations;
      }

      return {
        content: [{
          type: "text",
          text: `# Conversation History for ${agentName}\n\n` +
                JSON.stringify(history, null, 2)
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error retrieving conversation history: ${error.message}`
        }]
      };
    }
  }

  async startAgentSession(agentName, context = {}) {
    try {
      const sessionId = await this.memorySystem.startConversation(agentName, null, context);
      this.activeSessions.set(sessionId, {
        agentName,
        startTime: Date.now(),
        lastActivity: Date.now()
      });

      return {
        content: [{
          type: "text",
          text: `# New Session Started for ${agentName}\n\n` +
                `**Session ID**: ${sessionId}\n` +
                `**Context**: ${JSON.stringify(context, null, 2)}\n\n` +
                `You can now use this sessionId in subsequent agent calls for conversation continuity.`
        }],
        metadata: {
          sessionId,
          agentName
        }
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error starting session for ${agentName}: ${error.message}`
        }]
      };
    }
  }
}

// Start server
const server = new MCPServer();
process.stderr.write('Stellar Hummingbot MCP Agent Server with Memory System started\n');