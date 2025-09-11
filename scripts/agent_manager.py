#!/usr/bin/env python3
"""
Persistent Agent Management System for Stellar Hummingbot Connector

This system manages the lifecycle of persistent agents, handles communication
between agents, and maintains agent state across Claude Code sessions.
"""

import os
import sys
import json
import yaml
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/agent_manager.log')
    ]
)
logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status enumeration."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class WorkflowPhase(Enum):
    """Workflow phase enumeration."""
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    QA = "qa"
    IMPLEMENTATION = "implementation"
    VALIDATION = "validation"
    COMPLETED = "completed"


@dataclass
class AgentState:
    """Agent state information."""
    name: str
    role: str
    category: str
    status: AgentStatus
    priority: int
    capabilities: List[str]
    specializations: List[str]
    current_task: Optional[str] = None
    last_activity: Optional[datetime] = None
    message_queue_size: int = 0
    knowledge_base_sources: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if self.last_activity:
            data['last_activity'] = self.last_activity.isoformat()
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        """Create from dictionary."""
        if 'last_activity' in data and data['last_activity']:
            data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        if 'status' in data:
            data['status'] = AgentStatus(data['status'])
        return cls(**data)


@dataclass
class TaskState:
    """Task state information."""
    task_id: str
    description: str
    qa_ids: List[str]
    current_phase: WorkflowPhase
    assigned_agent: Optional[str]
    created_at: datetime
    updated_at: datetime
    phase_approvals: Dict[str, bool]
    phase_feedback: Dict[str, str]
    blocking_issues: List[str]
    priority: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['current_phase'] = self.current_phase.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskState':
        """Create from dictionary."""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['current_phase'] = WorkflowPhase(data['current_phase'])
        return cls(**data)


class AgentManager:
    """Manages persistent agents and their lifecycle."""
    
    def __init__(self, config_path: Path = None):
        self.project_root = Path.cwd()
        self.config_path = config_path or self.project_root / "team_startup.yaml"
        self.state_dir = self.project_root / "agent_state"
        self.logs_dir = self.project_root / "logs"
        
        # Ensure directories exist
        self.state_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        self.agents: Dict[str, AgentState] = {}
        self.tasks: Dict[str, TaskState] = {}
        self.message_queues: Dict[str, queue.Queue] = {}
        self.config = self._load_config()
        
        self.running = False
        self.monitor_thread = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load team startup configuration."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            return {}
    
    def _save_agent_state(self, agent_name: str):
        """Save agent state to disk."""
        try:
            state_file = self.state_dir / f"{agent_name}_state.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(self.agents[agent_name].to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save state for agent {agent_name}: {e}")
    
    def _load_agent_state(self, agent_name: str) -> Optional[AgentState]:
        """Load agent state from disk."""
        try:
            state_file = self.state_dir / f"{agent_name}_state.json"
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return AgentState.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load state for agent {agent_name}: {e}")
        return None
    
    def _save_task_state(self, task_id: str):
        """Save task state to disk."""
        try:
            state_file = self.state_dir / f"task_{task_id}.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks[task_id].to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save state for task {task_id}: {e}")
    
    def _load_all_task_states(self):
        """Load all task states from disk."""
        try:
            for state_file in self.state_dir.glob("task_*.json"):
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    task = TaskState.from_dict(data)
                    self.tasks[task.task_id] = task
        except Exception as e:
            logger.error(f"Failed to load task states: {e}")
    
    def initialize_agents(self) -> bool:
        """Initialize all agents from configuration."""
        try:
            agents_config = self.config.get('agents', [])
            
            for agent_config in agents_config:
                agent_name = agent_config.get('name')
                if not agent_name:
                    continue
                
                # Load existing state or create new
                existing_state = self._load_agent_state(agent_name)
                
                if existing_state:
                    # Update configuration but preserve state
                    existing_state.status = AgentStatus.INITIALIZING
                    current_agent = existing_state
                    self.agents[agent_name] = existing_state
                else:
                    # Create new agent state
                    current_agent = AgentState(
                        name=agent_name,
                        role=agent_config.get('role', ''),
                        category=agent_config.get('category', 'general'),
                        status=AgentStatus.INITIALIZING,
                        priority=agent_config.get('priority', 5),
                        capabilities=agent_config.get('capabilities', []),
                        specializations=agent_config.get('specializations', []),
                        knowledge_base_sources=agent_config.get('rag', {}).get('sources', [])
                    )
                    self.agents[agent_name] = current_agent
                
                # Initialize message queue
                self.message_queues[agent_name] = queue.Queue()
                
                # Save initial state
                self._save_agent_state(agent_name)
                
                logger.info(f"Initialized agent: {agent_name} ({current_agent.category})")
            
            # Load existing tasks
            self._load_all_task_states()
            
            logger.info(f"Initialized {len(self.agents)} agents and {len(self.tasks)} tasks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            return False
    
    def start_monitoring(self):
        """Start background monitoring thread."""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Started agent monitoring")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Stopped agent monitoring")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.running:
            try:
                # Update agent statuses
                for agent_name, agent in self.agents.items():
                    # Check if agent is responsive (placeholder)
                    if agent.status == AgentStatus.INITIALIZING:
                        agent.status = AgentStatus.IDLE
                        agent.last_activity = datetime.now(timezone.utc)
                        self._save_agent_state(agent_name)
                    
                    # Update message queue size
                    agent.message_queue_size = self.message_queues[agent_name].qsize()
                
                # Check for workflow timeouts and health issues
                self._check_workflow_health()
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
    
    def _check_workflow_health(self):
        """Check workflow health and detect issues."""
        current_time = datetime.now(timezone.utc)
        
        for task_id, task in self.tasks.items():
            # Check for stalled tasks
            time_since_update = current_time - task.updated_at
            if time_since_update.total_seconds() > 3600:  # 1 hour
                logger.warning(f"Task {task_id} stalled in {task.current_phase.value} phase")
            
            # Check for blocking issues
            if task.blocking_issues:
                logger.warning(f"Task {task_id} blocked: {', '.join(task.blocking_issues)}")
    
    def create_task(self, description: str, qa_ids: List[str] = None, priority: str = "medium") -> str:
        """Create a new task."""
        task_id = str(uuid.uuid4())
        current_time = datetime.now(timezone.utc)
        
        task = TaskState(
            task_id=task_id,
            description=description,
            qa_ids=qa_ids or [],
            current_phase=WorkflowPhase.REQUIREMENTS,
            assigned_agent=None,
            created_at=current_time,
            updated_at=current_time,
            phase_approvals={},
            phase_feedback={},
            blocking_issues=[],
            priority=priority
        )
        
        self.tasks[task_id] = task
        self._save_task_state(task_id)
        
        logger.info(f"Created task {task_id}: {description}")
        return task_id
    
    def assign_task(self, task_id: str, agent_name: str) -> bool:
        """Assign a task to an agent."""
        if task_id not in self.tasks:
            logger.error(f"Task {task_id} not found")
            return False
        
        if agent_name not in self.agents:
            logger.error(f"Agent {agent_name} not found")
            return False
        
        task = self.tasks[task_id]
        agent = self.agents[agent_name]
        
        # Update task assignment
        task.assigned_agent = agent_name
        task.updated_at = datetime.now(timezone.utc)
        
        # Update agent status
        agent.current_task = task_id
        agent.status = AgentStatus.BUSY
        agent.last_activity = datetime.now(timezone.utc)
        
        # Save states
        self._save_task_state(task_id)
        self._save_agent_state(agent_name)
        
        logger.info(f"Assigned task {task_id} to agent {agent_name}")
        return True
    
    def update_task_phase(self, task_id: str, new_phase: WorkflowPhase, feedback: str = "") -> bool:
        """Update task phase."""
        if task_id not in self.tasks:
            logger.error(f"Task {task_id} not found")
            return False
        
        task = self.tasks[task_id]
        old_phase = task.current_phase
        
        task.current_phase = new_phase
        task.updated_at = datetime.now(timezone.utc)
        
        if feedback:
            task.phase_feedback[new_phase.value] = feedback
        
        self._save_task_state(task_id)
        
        logger.info(f"Task {task_id} moved from {old_phase.value} to {new_phase.value}")
        return True
    
    def approve_task_phase(self, task_id: str, phase: WorkflowPhase, approver: str) -> bool:
        """Approve a task phase."""
        if task_id not in self.tasks:
            logger.error(f"Task {task_id} not found")
            return False
        
        task = self.tasks[task_id]
        task.phase_approvals[f"{phase.value}_{approver}"] = True
        task.updated_at = datetime.now(timezone.utc)
        
        self._save_task_state(task_id)
        
        logger.info(f"Task {task_id} phase {phase.value} approved by {approver}")
        return True
    
    def get_agent_status(self, agent_name: str) -> Optional[AgentState]:
        """Get agent status."""
        return self.agents.get(agent_name)
    
    def get_task_status(self, task_id: str) -> Optional[TaskState]:
        """Get task status."""
        return self.tasks.get(task_id)
    
    def list_agents(self) -> List[AgentState]:
        """List all agents."""
        return list(self.agents.values())
    
    def list_tasks(self, status_filter: WorkflowPhase = None) -> List[TaskState]:
        """List all tasks, optionally filtered by status."""
        tasks = list(self.tasks.values())
        if status_filter:
            tasks = [t for t in tasks if t.current_phase == status_filter]
        return sorted(tasks, key=lambda t: t.updated_at, reverse=True)
    
    def get_agent_by_capability(self, capability: str) -> List[str]:
        """Get agents by capability."""
        return [
            name for name, agent in self.agents.items()
            if capability in agent.capabilities
        ]
    
    def get_agent_by_category(self, category: str) -> List[str]:
        """Get agents by category."""
        return [
            name for name, agent in self.agents.items()
            if agent.category == category
        ]
    
    def send_message(self, from_agent: str, to_agent: str, message: Dict[str, Any]) -> bool:
        """Send message between agents."""
        if to_agent not in self.message_queues:
            logger.error(f"Agent {to_agent} not found for message delivery")
            return False
        
        message_with_metadata = {
            'from': from_agent,
            'to': to_agent,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message': message
        }
        
        self.message_queues[to_agent].put(message_with_metadata)
        
        # Update sender status
        if from_agent in self.agents:
            self.agents[from_agent].last_activity = datetime.now(timezone.utc)
            self._save_agent_state(from_agent)
        
        logger.debug(f"Message sent from {from_agent} to {to_agent}")
        return True
    
    def get_messages(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get messages for an agent."""
        if agent_name not in self.message_queues:
            return []
        
        messages = []
        queue_obj = self.message_queues[agent_name]
        
        while not queue_obj.empty():
            try:
                messages.append(queue_obj.get_nowait())
            except queue.Empty:
                break
        
        return messages
    
    def generate_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive status report."""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'agent_count': len(self.agents),
            'task_count': len(self.tasks),
            'agents': {name: agent.to_dict() for name, agent in self.agents.items()},
            'tasks': {task_id: task.to_dict() for task_id, task in self.tasks.items()},
            'workflow_health': self._assess_workflow_health(),
            'system_status': 'healthy' if self.running else 'stopped'
        }
    
    def _assess_workflow_health(self) -> Dict[str, Any]:
        """Assess overall workflow health."""
        current_time = datetime.now(timezone.utc)
        
        active_agents = sum(1 for agent in self.agents.values() if agent.status == AgentStatus.ACTIVE)
        idle_agents = sum(1 for agent in self.agents.values() if agent.status == AgentStatus.IDLE)
        busy_agents = sum(1 for agent in self.agents.values() if agent.status == AgentStatus.BUSY)
        error_agents = sum(1 for agent in self.agents.values() if agent.status == AgentStatus.ERROR)
        
        active_tasks = sum(1 for task in self.tasks.values() if task.current_phase != WorkflowPhase.COMPLETED)
        stalled_tasks = sum(
            1 for task in self.tasks.values()
            if (current_time - task.updated_at).total_seconds() > 3600
        )
        blocked_tasks = sum(1 for task in self.tasks.values() if task.blocking_issues)
        
        return {
            'agents': {
                'active': active_agents,
                'idle': idle_agents, 
                'busy': busy_agents,
                'error': error_agents
            },
            'tasks': {
                'active': active_tasks,
                'stalled': stalled_tasks,
                'blocked': blocked_tasks
            },
            'overall_health': 'healthy' if (error_agents == 0 and stalled_tasks < 3) else 'degraded'
        }


def main():
    """Main entry point for agent manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Agent Management System')
    parser.add_argument('--config', default='team_startup.yaml', help='Configuration file')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--status', action='store_true', help='Show status report')
    parser.add_argument('--init', action='store_true', help='Initialize agents')
    
    args = parser.parse_args()
    
    manager = AgentManager(Path(args.config))
    
    if args.status:
        report = manager.generate_status_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    
    if args.init:
        if manager.initialize_agents():
            print("✅ Agents initialized successfully")
        else:
            print("❌ Failed to initialize agents")
            sys.exit(1)
        return
    
    if args.daemon:
        try:
            manager.initialize_agents()
            manager.start_monitoring()
            
            print("🚀 Agent manager started. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping agent manager...")
            manager.stop_monitoring()
            print("✅ Agent manager stopped")
    else:
        print("Use --daemon to run as service, --status for report, --init to initialize")


if __name__ == '__main__':
    main()