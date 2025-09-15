// Agent Memory and Context Persistence System
// Provides individual memory, conversation history, and context isolation for each agent

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

class AgentMemorySystem {
  constructor(projectRoot, storageDir = '.claude/agent_memory') {
    this.projectRoot = projectRoot;
    this.storageDir = path.join(projectRoot, storageDir);
    this.memoryCache = new Map(); // In-memory cache
    this.conversationCache = new Map(); // Conversation history cache

    // Ensure storage directory exists
    this.initializeStorage();
  }

  initializeStorage() {
    if (!fs.existsSync(this.storageDir)) {
      fs.mkdirSync(this.storageDir, { recursive: true });
    }

    // Create subdirectories for different types of memory
    const dirs = ['conversations', 'context', 'learning', 'decisions'];
    dirs.forEach(dir => {
      const dirPath = path.join(this.storageDir, dir);
      if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
      }
    });
  }

  // Generate unique session ID for conversation tracking
  generateSessionId(agentName, userId = 'default') {
    const timestamp = Date.now();
    const hash = crypto.createHash('md5')
      .update(`${agentName}-${userId}-${timestamp}`)
      .digest('hex')
      .substring(0, 8);
    return `${agentName}-${hash}`;
  }

  // Get agent's persistent memory
  async getAgentMemory(agentName) {
    const memoryFile = path.join(this.storageDir, 'context', `${agentName}.json`);

    if (this.memoryCache.has(agentName)) {
      return this.memoryCache.get(agentName);
    }

    let memory = {
      agentName,
      createdAt: new Date().toISOString(),
      lastAccessed: new Date().toISOString(),
      personalContext: {},
      workflowState: {},
      learnings: [],
      preferences: {},
      metrics: {
        totalInteractions: 0,
        successfulTasks: 0,
        averageResponseTime: 0,
        specializations: []
      },
      relationships: {}, // Interactions with other agents
      reminders: [], // Things to remember for future
      activeProjects: [],
      completedTasks: []
    };

    if (fs.existsSync(memoryFile)) {
      try {
        const existing = JSON.parse(fs.readFileSync(memoryFile, 'utf8'));
        memory = { ...memory, ...existing };
        memory.lastAccessed = new Date().toISOString();
      } catch (error) {
        console.error(`Error loading memory for ${agentName}:`, error);
      }
    }

    this.memoryCache.set(agentName, memory);
    return memory;
  }

  // Save agent's memory to persistent storage
  async saveAgentMemory(agentName, memory) {
    const memoryFile = path.join(this.storageDir, 'context', `${agentName}.json`);

    memory.lastUpdated = new Date().toISOString();
    memory.metrics.totalInteractions += 1;

    try {
      fs.writeFileSync(memoryFile, JSON.stringify(memory, null, 2));
      this.memoryCache.set(agentName, memory);
    } catch (error) {
      console.error(`Error saving memory for ${agentName}:`, error);
    }
  }

  // Start new conversation session
  async startConversation(agentName, sessionId = null, context = {}) {
    if (!sessionId) {
      sessionId = this.generateSessionId(agentName);
    }

    const conversation = {
      sessionId,
      agentName,
      startTime: new Date().toISOString(),
      lastActivity: new Date().toISOString(),
      messages: [],
      context,
      status: 'active',
      metadata: {
        taskType: context.taskType || 'general',
        priority: context.priority || 'normal',
        relatedAgents: [],
        workflowPhase: context.workflowPhase || 'unknown'
      }
    };

    const conversationFile = path.join(
      this.storageDir,
      'conversations',
      `${agentName}-${sessionId}.json`
    );

    fs.writeFileSync(conversationFile, JSON.stringify(conversation, null, 2));
    this.conversationCache.set(sessionId, conversation);

    return sessionId;
  }

  // Add message to conversation
  async addToConversation(sessionId, message, agentName) {
    let conversation = this.conversationCache.get(sessionId);

    if (!conversation) {
      // Try to load from disk
      const conversationFile = path.join(
        this.storageDir,
        'conversations',
        `${agentName}-${sessionId}.json`
      );

      if (fs.existsSync(conversationFile)) {
        conversation = JSON.parse(fs.readFileSync(conversationFile, 'utf8'));
      } else {
        // Create new conversation if not found
        sessionId = await this.startConversation(agentName);
        conversation = this.conversationCache.get(sessionId);
      }
    }

    const messageEntry = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      type: message.type || 'task',
      content: message.content,
      metadata: message.metadata || {},
      agentResponse: message.agentResponse || null
    };

    conversation.messages.push(messageEntry);
    conversation.lastActivity = new Date().toISOString();

    // Save to disk
    const conversationFile = path.join(
      this.storageDir,
      'conversations',
      `${agentName}-${sessionId}.json`
    );

    fs.writeFileSync(conversationFile, JSON.stringify(conversation, null, 2));
    this.conversationCache.set(sessionId, conversation);

    return messageEntry.id;
  }

  // Get conversation history
  async getConversationHistory(sessionId, agentName, limit = 50) {
    let conversation = this.conversationCache.get(sessionId);

    if (!conversation) {
      const conversationFile = path.join(
        this.storageDir,
        'conversations',
        `${agentName}-${sessionId}.json`
      );

      if (fs.existsSync(conversationFile)) {
        conversation = JSON.parse(fs.readFileSync(conversationFile, 'utf8'));
        this.conversationCache.set(sessionId, conversation);
      } else {
        return [];
      }
    }

    return conversation.messages.slice(-limit);
  }

  // Get recent conversations for agent
  async getRecentConversations(agentName, limit = 10) {
    const conversationsDir = path.join(this.storageDir, 'conversations');
    const files = fs.readdirSync(conversationsDir)
      .filter(file => file.startsWith(`${agentName}-`) && file.endsWith('.json'))
      .map(file => ({
        file,
        path: path.join(conversationsDir, file),
        stats: fs.statSync(path.join(conversationsDir, file))
      }))
      .sort((a, b) => b.stats.mtime - a.stats.mtime)
      .slice(0, limit);

    const conversations = [];
    for (const fileInfo of files) {
      try {
        const conversation = JSON.parse(fs.readFileSync(fileInfo.path, 'utf8'));
        conversations.push({
          sessionId: conversation.sessionId,
          startTime: conversation.startTime,
          lastActivity: conversation.lastActivity,
          messageCount: conversation.messages.length,
          context: conversation.context,
          status: conversation.status
        });
      } catch (error) {
        console.error(`Error reading conversation file ${fileInfo.file}:`, error);
      }
    }

    return conversations;
  }

  // Add learning/insight to agent memory
  async addLearning(agentName, learning) {
    const memory = await this.getAgentMemory(agentName);

    const learningEntry = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      type: learning.type || 'insight',
      content: learning.content,
      context: learning.context || {},
      confidence: learning.confidence || 0.8,
      tags: learning.tags || []
    };

    memory.learnings.push(learningEntry);

    // Keep only recent learnings (last 100)
    if (memory.learnings.length > 100) {
      memory.learnings = memory.learnings.slice(-100);
    }

    await this.saveAgentMemory(agentName, memory);
    return learningEntry.id;
  }

  // Update agent's workflow state
  async updateWorkflowState(agentName, phase, state, metadata = {}) {
    const memory = await this.getAgentMemory(agentName);

    memory.workflowState[phase] = {
      state,
      timestamp: new Date().toISOString(),
      metadata
    };

    await this.saveAgentMemory(agentName, memory);
  }

  // Record agent relationship/interaction
  async recordAgentInteraction(agentName, targetAgent, interactionType, details) {
    const memory = await this.getAgentMemory(agentName);

    if (!memory.relationships[targetAgent]) {
      memory.relationships[targetAgent] = {
        totalInteractions: 0,
        lastInteraction: null,
        interactionTypes: {},
        collaborationHistory: []
      };
    }

    const relationship = memory.relationships[targetAgent];
    relationship.totalInteractions += 1;
    relationship.lastInteraction = new Date().toISOString();

    if (!relationship.interactionTypes[interactionType]) {
      relationship.interactionTypes[interactionType] = 0;
    }
    relationship.interactionTypes[interactionType] += 1;

    relationship.collaborationHistory.push({
      timestamp: new Date().toISOString(),
      type: interactionType,
      details
    });

    // Keep only recent collaboration history
    if (relationship.collaborationHistory.length > 20) {
      relationship.collaborationHistory = relationship.collaborationHistory.slice(-20);
    }

    await this.saveAgentMemory(agentName, memory);
  }

  // Get agent's contextual information for current task
  async getAgentContext(agentName, sessionId = null, includeHistory = true) {
    const memory = await this.getAgentMemory(agentName);
    const context = {
      agent: {
        name: agentName,
        totalInteractions: memory.metrics.totalInteractions,
        specializations: memory.metrics.specializations,
        lastAccessed: memory.lastAccessed
      },
      memory: {
        personalContext: memory.personalContext,
        currentWorkflowState: memory.workflowState,
        recentLearnings: memory.learnings.slice(-5),
        activeReminders: memory.reminders.filter(r => !r.completed),
        preferences: memory.preferences
      },
      relationships: {},
      conversationHistory: []
    };

    // Add relationship summaries
    Object.keys(memory.relationships).forEach(agentName => {
      const rel = memory.relationships[agentName];
      context.relationships[agentName] = {
        totalInteractions: rel.totalInteractions,
        lastInteraction: rel.lastInteraction,
        primaryInteractionType: Object.keys(rel.interactionTypes)
          .sort((a, b) => rel.interactionTypes[b] - rel.interactionTypes[a])[0],
        recentCollaboration: rel.collaborationHistory.slice(-3)
      };
    });

    // Add conversation history if session provided
    if (sessionId && includeHistory) {
      context.conversationHistory = await this.getConversationHistory(sessionId, agentName, 10);
    }

    return context;
  }

  // Clean up old data (maintenance function)
  async cleanupOldData(retentionDays = 30) {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - retentionDays);

    const conversationsDir = path.join(this.storageDir, 'conversations');
    const files = fs.readdirSync(conversationsDir);

    let cleaned = 0;
    for (const file of files) {
      const filePath = path.join(conversationsDir, file);
      const stats = fs.statSync(filePath);

      if (stats.mtime < cutoffDate) {
        fs.unlinkSync(filePath);
        cleaned++;
      }
    }

    return cleaned;
  }

  // Generate memory summary for agent
  async getMemorySummary(agentName) {
    const memory = await this.getAgentMemory(agentName);
    const recentConversations = await this.getRecentConversations(agentName, 5);

    return {
      agent: agentName,
      totalInteractions: memory.metrics.totalInteractions,
      successfulTasks: memory.metrics.successfulTasks,
      recentConversations: recentConversations.length,
      learningsCount: memory.learnings.length,
      activeReminders: memory.reminders.filter(r => !r.completed).length,
      relationships: Object.keys(memory.relationships).length,
      lastAccessed: memory.lastAccessed,
      workflowPhases: Object.keys(memory.workflowState)
    };
  }
}

module.exports = AgentMemorySystem;