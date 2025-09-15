#!/usr/bin/env node

// Memory-Aware Workflow Coordination System
// Enhances multi-agent workflows with persistent memory and context continuity

const AgentMemorySystem = require('./agent_memory_system.js');
const SharedKnowledgeBase = require('./shared_knowledge_base.js');

class MemoryAwareWorkflowCoordinator {
  constructor(projectRoot) {
    this.projectRoot = projectRoot || process.cwd();
    this.memory = new AgentMemorySystem(projectRoot);
    this.knowledgeBase = new SharedKnowledgeBase(projectRoot);
    this.workflowHistory = [];

    // Workflow phase sequence
    this.phaseSequence = [
      'Requirements',
      'Architecture',
      'Security',
      'QA',
      'Implementation',
      'Validation'
    ];

    // Agent role mapping
    this.phaseAgents = {
      'Requirements': 'ProjectManager',
      'Architecture': 'Architect',
      'Security': 'SecurityEngineer',
      'QA': 'QAEngineer',
      'Implementation': 'Implementer',
      'Validation': 'QAEngineer'
    };
  }

  // Start a new workflow with memory context
  async startWorkflow(taskDescription, priority = 'normal') {
    console.log(`🚀 Starting memory-aware workflow: ${taskDescription}`);

    const workflowId = `workflow-${Date.now()}`;
    const workflow = {
      id: workflowId,
      description: taskDescription,
      priority,
      startTime: new Date().toISOString(),
      phases: [],
      currentPhase: 0,
      status: 'active',
      agentSessions: {}
    };

    // Initialize sessions for all agents
    for (const [phase, agentName] of Object.entries(this.phaseAgents)) {
      const sessionId = await this.memory.startConversation(agentName, null, {
        taskType: 'workflow_coordination',
        priority,
        workflowPhase: phase,
        workflowId,
        taskDescription
      });

      workflow.agentSessions[agentName] = sessionId;

      // Add workflow context to agent memory
      await this.memory.updateWorkflowState(agentName, workflowId, 'initialized', {
        phase,
        taskDescription,
        sessionId
      });
    }

    this.workflowHistory.push(workflow);
    return workflow;
  }

  // Execute a workflow phase with memory-enhanced context
  async executePhase(workflow, phaseIndex) {
    if (phaseIndex >= this.phaseSequence.length) {
      console.log('✅ All workflow phases completed');
      return { status: 'completed' };
    }

    const phaseName = this.phaseSequence[phaseIndex];
    const agentName = this.phaseAgents[phaseName];
    const sessionId = workflow.agentSessions[agentName];

    console.log(`\n📋 Phase ${phaseIndex + 1}: ${phaseName} (${agentName})`);

    // Get agent context with memory
    const agentContext = await this.memory.getAgentContext(agentName, sessionId, true);

    // Get relevant learnings from previous workflows
    const relevantLearnings = this.getRelevantLearnings(agentContext, workflow.description);

    // Get relationships with other agents in this workflow
    const agentRelationships = this.getWorkflowRelationships(agentContext, workflow);

    const phaseResult = {
      phase: phaseName,
      agent: agentName,
      sessionId,
      startTime: new Date().toISOString(),
      context: {
        totalExperience: agentContext.agent.totalInteractions,
        relevantLearnings: relevantLearnings.length,
        activeRelationships: Object.keys(agentRelationships).length,
        previousPhases: workflow.phases.length
      },
      status: 'completed',
      recommendations: [],
      blockers: []
    };

    // Add phase message to conversation
    await this.memory.addToConversation(sessionId, {
      type: 'phase_execution',
      content: `Executing ${phaseName} phase for: ${workflow.description}`,
      metadata: {
        workflowId: workflow.id,
        phase: phaseName,
        phaseIndex,
        context: phaseResult.context
      }
    }, agentName);

    // Record inter-agent collaboration
    if (phaseIndex > 0) {
      const previousPhase = workflow.phases[phaseIndex - 1];
      if (previousPhase) {
        await this.memory.recordAgentInteraction(
          agentName,
          previousPhase.agent,
          'workflow_handoff',
          {
            workflowId: workflow.id,
            fromPhase: previousPhase.phase,
            toPhase: phaseName,
            handoffTime: new Date().toISOString()
          }
        );
      }
    }

    // Update workflow state
    await this.memory.updateWorkflowState(agentName, workflow.id, 'phase_completed', {
      phase: phaseName,
      result: phaseResult,
      completedAt: new Date().toISOString()
    });

    // Add learning if phase revealed insights
    if (phaseResult.recommendations.length > 0) {
      await this.memory.addLearning(agentName, {
        type: 'workflow_insight',
        content: `${phaseName} phase insights for similar tasks: ${phaseResult.recommendations.join(', ')}`,
        context: {
          workflowType: workflow.description,
          phase: phaseName,
          taskComplexity: workflow.priority
        },
        confidence: 0.8,
        tags: [phaseName.toLowerCase(), 'workflow', 'recommendations']
      });
    }

    workflow.phases.push(phaseResult);
    workflow.currentPhase = phaseIndex + 1;

    console.log(`✅ ${phaseName} phase completed by ${agentName}`);
    console.log(`   Experience: ${phaseResult.context.totalExperience} interactions`);
    console.log(`   Relevant learnings: ${phaseResult.context.relevantLearnings}`);
    console.log(`   Active relationships: ${phaseResult.context.activeRelationships}`);

    return phaseResult;
  }

  // Execute complete workflow with memory continuity
  async executeWorkflow(taskDescription, priority = 'normal') {
    const workflow = await this.startWorkflow(taskDescription, priority);

    console.log(`\n🔄 Executing 6-phase workflow with memory-aware coordination...`);

    for (let i = 0; i < this.phaseSequence.length; i++) {
      const result = await this.executePhase(workflow, i);
      if (result.status === 'blocked') {
        console.log(`⚠️  Workflow blocked at phase ${i + 1}: ${result.blocker}`);
        workflow.status = 'blocked';
        break;
      }
    }

    if (workflow.status === 'active') {
      workflow.status = 'completed';
      workflow.endTime = new Date().toISOString();

      // Add workflow completion learning for ProjectManager
      await this.memory.addLearning('ProjectManager', {
        type: 'workflow_completion',
        content: `Successfully coordinated 6-phase workflow: ${taskDescription}`,
        context: {
          workflowId: workflow.id,
          duration: new Date(workflow.endTime) - new Date(workflow.startTime),
          phases: workflow.phases.length,
          priority
        },
        confidence: 0.9,
        tags: ['workflow', 'coordination', 'completion', priority]
      });
    }

    console.log(`\n🎉 Workflow ${workflow.status}: ${workflow.description}`);
    return workflow;
  }

  // Get relevant learnings for current context
  getRelevantLearnings(agentContext, taskDescription) {
    const relevantLearnings = agentContext.memory.recentLearnings.filter(learning => {
      const contentLower = learning.content.toLowerCase();
      const taskLower = taskDescription.toLowerCase();

      // Check for keyword matches or tag relevance
      return learning.tags.some(tag => taskLower.includes(tag.toLowerCase())) ||
             contentLower.includes('workflow') ||
             contentLower.includes('memory') ||
             learning.confidence > 0.85;
    });

    return relevantLearnings;
  }

  // Get workflow-relevant relationships
  getWorkflowRelationships(agentContext, workflow) {
    const workflowAgents = Object.values(this.phaseAgents);
    const relevantRelationships = {};

    Object.keys(agentContext.relationships).forEach(agentName => {
      if (workflowAgents.includes(agentName)) {
        relevantRelationships[agentName] = agentContext.relationships[agentName];
      }
    });

    return relevantRelationships;
  }

  // Get workflow summary with memory insights
  async getWorkflowSummary() {
    const summaries = {};
    const agents = Object.values(this.phaseAgents);

    for (const agentName of [...new Set(agents)]) {
      summaries[agentName] = await this.memory.getMemorySummary(agentName);
    }

    return {
      totalWorkflows: this.workflowHistory.length,
      agentSummaries: summaries,
      recentWorkflows: this.workflowHistory.slice(-5),
      memorySystemStatus: 'operational'
    };
  }
}

// Export for use as module
module.exports = MemoryAwareWorkflowCoordinator;

// CLI usage
if (require.main === module) {
  const coordinator = new MemoryAwareWorkflowCoordinator('.');

  const args = process.argv.slice(2);
  const command = args[0];

  if (command === 'test') {
    // Test the memory-aware workflow
    coordinator.executeWorkflow(
      'Test memory-aware multi-agent workflow coordination',
      'high'
    ).then(result => {
      console.log('\n📊 Workflow Test Results:');
      console.log(`Status: ${result.status}`);
      console.log(`Phases: ${result.phases.length}/${coordinator.phaseSequence.length}`);
      console.log(`Duration: ${new Date(result.endTime) - new Date(result.startTime)}ms`);
    }).catch(console.error);
  } else if (command === 'summary') {
    // Get workflow summary
    coordinator.getWorkflowSummary().then(summary => {
      console.log('\n📊 Memory-Aware Workflow Summary:');
      console.log(`Total workflows: ${summary.totalWorkflows}`);
      console.log(`Memory system: ${summary.memorySystemStatus}`);
      console.log('\nAgent Experience:');
      Object.entries(summary.agentSummaries).forEach(([agent, data]) => {
        console.log(`  ${agent}: ${data.totalInteractions} interactions, ${data.learningsCount} learnings`);
      });
    }).catch(console.error);
  } else {
    console.log('Usage:');
    console.log('  node memory_aware_workflow.js test    - Test workflow coordination');
    console.log('  node memory_aware_workflow.js summary - Show workflow summary');
  }
}