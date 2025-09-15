#!/usr/bin/env python3
"""
Team Status Verification for Stellar Hummingbot Connector
Validates that all agents are properly configured and accessible.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List

def check_agent_files() -> Dict[str, bool]:
    """Check if all agent files exist."""
    agents_dir = Path(".claude/agents")
    expected_agents = [
        "ProjectManager.md",
        "Architect.md", 
        "SecurityEngineer.md",
        "QAEngineer.md",
        "Implementer.md",
        "DevOpsEngineer.md",
        "PerformanceEngineer.md",
        "DocumentationEngineer.md"
    ]
    
    agent_status = {}
    for agent in expected_agents:
        agent_path = agents_dir / agent
        agent_status[agent] = agent_path.exists()
    
    return agent_status

def check_workflow_config() -> bool:
    """Check if team workflow configuration exists."""
    return Path(".claude/team_workflow.yaml").exists()

def validate_team_startup() -> bool:
    """Validate team_startup.yaml configuration."""
    try:
        with open("team_startup.yaml", 'r') as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        required_sections = ['agents', 'agent_roles', 'workflow']
        for section in required_sections:
            if section not in config:
                print(f"❌ Missing required section: {section}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Error validating team_startup.yaml: {e}")
        return False

def generate_team_report():
    """Generate comprehensive team status report."""
    print("🚀 Stellar Hummingbot Connector - Team Status Report")
    print("=" * 60)
    
    # Check agent files
    print("\n👥 AGENT STATUS:")
    agent_status = check_agent_files()
    all_agents_ready = True
    
    for agent, exists in agent_status.items():
        status_icon = "✅" if exists else "❌"
        agent_name = agent.replace('.md', '')
        print(f"  {status_icon} {agent_name}")
        if not exists:
            all_agents_ready = False
    
    # Check workflow configuration
    print(f"\n🔄 WORKFLOW CONFIGURATION:")
    workflow_ready = check_workflow_config()
    workflow_icon = "✅" if workflow_ready else "❌"
    print(f"  {workflow_icon} Team Workflow Config")
    
    # Check team startup
    print(f"\n⚙️  TEAM STARTUP VALIDATION:")
    startup_valid = validate_team_startup()
    startup_icon = "✅" if startup_valid else "❌"
    print(f"  {startup_icon} team_startup.yaml")
    
    # Overall status
    print(f"\n📊 OVERALL TEAM STATUS:")
    if all_agents_ready and workflow_ready and startup_valid:
        print("  ✅ Team Fully Operational")
        print("  🎯 Ready for Multi-Agent Workflow")
    else:
        print("  ❌ Team Setup Incomplete")
        print("  🔧 Configuration Issues Detected")
    
    # Next steps
    print(f"\n🚀 NEXT STEPS:")
    print("  1. Use /agent <AgentName> to activate specific agents")
    print("  2. Follow phase-gate workflow: Requirements → Architecture → Security → QA → Implementation")
    print("  3. ProjectManager coordinates all multi-agent tasks")
    print("  4. Reference .claude/team_workflow.yaml for detailed workflow")
    
    print("\n" + "=" * 60)
    return all_agents_ready and workflow_ready and startup_valid

if __name__ == "__main__":
    success = generate_team_report()
    exit(0 if success else 1)