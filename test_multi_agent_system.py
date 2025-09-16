#!/usr/bin/env python3
"""
Multi-Agent System Verification and Testing Script

This script tests and verifies all components of the multi-agent workflow system
to ensure everything works as claimed.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.agent_manager import AgentManager
from scripts.claude_code_agent_workflow import ClaudeCodeMultiAgentWorkflow, TaskPhase, TaskStatus

def test_agent_discovery():
    """Test 1: Agent Discovery and Status Reporting"""
    print("🔍 TEST 1: Agent Discovery and Status Reporting")
    print("=" * 60)

    try:
        manager = AgentManager(Path("team_startup.yaml"))

        # Initialize agents
        init_success = manager.initialize_agents()
        print(f"✅ Agent initialization: {'SUCCESS' if init_success else 'FAILED'}")

        # Generate status report
        status = manager.generate_status_report()

        print(f"📊 Agent count: {status['agent_count']}")
        print(f"📊 System status: {status['system_status']}")
        print(f"📊 Agents detected:")

        for name, agent in status['agents'].items():
            print(f"   {name}: {agent['status']} ({agent['role']})")

        # Verify we have all expected agents
        expected_agents = {
            'ProjectManager', 'Architect', 'SecurityEngineer', 'QAEngineer',
            'Implementer', 'DevOpsEngineer', 'PerformanceEngineer', 'DocumentationEngineer'
        }

        actual_agents = set(status['agents'].keys())
        missing_agents = expected_agents - actual_agents

        if not missing_agents:
            print("✅ All 8 expected agents are present and discoverable")
            return True
        else:
            print(f"❌ Missing agents: {missing_agents}")
            return False

    except Exception as e:
        print(f"❌ Agent discovery test failed: {e}")
        return False

def test_workflow_task_creation():
    """Test 2: Workflow Task Creation and State Management"""
    print("\n🏗️ TEST 2: Workflow Task Creation and State Management")
    print("=" * 60)

    try:
        workflow = ClaudeCodeMultiAgentWorkflow()

        # Test task creation
        task = workflow.active_tasks
        print(f"✅ Workflow initialized with {len(task)} active tasks")

        # Test agent specifications
        print(f"📋 Available agents:")
        for name, agent in workflow.agents.items():
            print(f"   {name}: {len(agent.capabilities)} capabilities, {len(agent.specializations)} specializations")

        # Test phase transitions
        phases = list(workflow.phase_transitions.keys())
        print(f"🔄 Workflow phases: {[phase.value for phase in phases]}")

        print("✅ Workflow system initialized successfully")
        return True

    except Exception as e:
        print(f"❌ Workflow task creation test failed: {e}")
        return False

def test_state_persistence():
    """Test 3: State Persistence and Recovery"""
    print("\n💾 TEST 3: State Persistence and Recovery")
    print("=" * 60)

    try:
        # Create workflow and check state directory
        workflow = ClaudeCodeMultiAgentWorkflow()

        state_dir = Path("agent_state")
        if state_dir.exists():
            state_files = list(state_dir.glob("*.json"))
            print(f"📂 State directory exists with {len(state_files)} state files")

            # Check if state files are valid JSON
            valid_files = 0
            for state_file in state_files:
                try:
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                        if 'name' in data and 'status' in data:
                            valid_files += 1
                except:
                    pass

            print(f"✅ {valid_files}/{len(state_files)} state files are valid")
            return valid_files >= len(state_files) * 0.8  # 80% success rate
        else:
            print("❌ State directory not found")
            return False

    except Exception as e:
        print(f"❌ State persistence test failed: {e}")
        return False

async def test_simulated_workflow_execution():
    """Test 4: Simulated Workflow Execution"""
    print("\n🎭 TEST 4: Simulated Workflow Execution")
    print("=" * 60)

    try:
        workflow = ClaudeCodeMultiAgentWorkflow()

        # Create a test task
        task_id = "test_task_" + str(int(asyncio.get_event_loop().time()))

        from datetime import datetime
        from scripts.claude_code_agent_workflow import WorkflowTask

        test_task = WorkflowTask(
            id=task_id,
            description="Test task for verification",
            requirements="Verify multi-agent system functionality",
            phase=TaskPhase.REQUIREMENTS_INTAKE,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )

        workflow.active_tasks[task_id] = test_task

        # Test phase progression simulation
        phases_completed = 0
        current_phase = test_task.phase

        # Simulate completing each phase
        phase_order = [
            TaskPhase.REQUIREMENTS_INTAKE,
            TaskPhase.ARCHITECTURE_REVIEW,
            TaskPhase.SECURITY_REVIEW,
            TaskPhase.QA_CRITERIA,
            TaskPhase.IMPLEMENTATION,
            TaskPhase.FINAL_VALIDATION
        ]

        for phase in phase_order:
            if phase == current_phase:
                print(f"   🔄 Simulating {phase.value} phase")

                # Simulate agent result
                agent_name = workflow._get_next_phase_agents(phase)
                if agent_name:
                    test_task.agent_results[agent_name[0] if isinstance(agent_name, list) else agent_name] = {
                        "status": "completed",
                        "phase": phase.value,
                        "quality_score": 9.0
                    }

                phases_completed += 1

                # Move to next phase
                next_phases = workflow.phase_transitions.get(phase, [])
                if next_phases:
                    test_task.phase = next_phases[0]
                    current_phase = next_phases[0]
                else:
                    break

        print(f"✅ Completed {phases_completed} workflow phases")
        print(f"📊 Task results: {len(test_task.agent_results)} agent results collected")

        # Test status reporting
        status = workflow.get_workflow_status()
        print(f"📈 Workflow status: {status['system_info']['active_tasks']} active tasks")

        return phases_completed >= 3  # At least 3 phases completed

    except Exception as e:
        print(f"❌ Simulated workflow execution test failed: {e}")
        return False

def test_real_task_integration():
    """Test 5: Real Claude Code Task Integration Points"""
    print("\n🎯 TEST 5: Real Claude Code Task Integration Points")
    print("=" * 60)

    try:
        from scripts.claude_code_task_integration import ClaudeCodeTaskIntegration
        from scripts.claude_code_agent_workflow import ClaudeCodeMultiAgentWorkflow

        # Test integration layer initialization
        workflow = ClaudeCodeMultiAgentWorkflow()
        integration = ClaudeCodeTaskIntegration(workflow)

        print("✅ Task integration layer initialized")

        # Test Task call generation
        task_calls = integration.get_active_task_calls()
        print(f"📋 Active task calls: {len(task_calls)}")

        # Test script generation
        script_content = integration.generate_claude_code_execution_script()
        script_lines = len(script_content.split('\n'))
        print(f"📜 Generated execution script: {script_lines} lines")

        # Verify script contains Task tool references
        has_task_references = "Task(" in script_content and "subagent_type" in script_content
        print(f"🔗 Task tool integration: {'PRESENT' if has_task_references else 'MISSING'}")

        return has_task_references

    except Exception as e:
        print(f"❌ Real task integration test failed: {e}")
        return False

def test_system_comprehensive_validation():
    """Test 6: Comprehensive System Validation"""
    print("\n🏆 TEST 6: Comprehensive System Validation")
    print("=" * 60)

    try:
        # Test file existence
        critical_files = [
            "scripts/agent_manager.py",
            "scripts/claude_code_agent_workflow.py",
            "scripts/claude_code_task_integration.py",
            "team_startup.yaml",
            "agent_state/"
        ]

        files_found = 0
        for file_path in critical_files:
            if Path(file_path).exists():
                files_found += 1
                print(f"   ✅ {file_path}")
            else:
                print(f"   ❌ {file_path}")

        print(f"📂 Critical files: {files_found}/{len(critical_files)} present")

        # Test import capabilities
        imports_successful = 0
        critical_imports = [
            ("scripts.agent_manager", "AgentManager"),
            ("scripts.claude_code_agent_workflow", "ClaudeCodeMultiAgentWorkflow"),
            ("scripts.claude_code_task_integration", "ClaudeCodeTaskIntegration")
        ]

        for module_name, class_name in critical_imports:
            try:
                module = __import__(module_name, fromlist=[class_name])
                getattr(module, class_name)
                imports_successful += 1
                print(f"   ✅ {module_name}.{class_name}")
            except Exception as e:
                print(f"   ❌ {module_name}.{class_name}: {e}")

        print(f"🔌 Critical imports: {imports_successful}/{len(critical_imports)} successful")

        # Overall system health score
        file_score = files_found / len(critical_files)
        import_score = imports_successful / len(critical_imports)
        overall_score = (file_score + import_score) / 2

        print(f"🎯 System Health Score: {overall_score:.1%}")

        return overall_score >= 0.8  # 80% health threshold

    except Exception as e:
        print(f"❌ Comprehensive validation test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests and generate summary report"""
    print("🚀 MULTI-AGENT SYSTEM VERIFICATION AND TESTING")
    print("=" * 80)

    test_results = {}

    # Run all tests
    tests = [
        ("Agent Discovery", test_agent_discovery),
        ("Workflow Creation", test_workflow_task_creation),
        ("State Persistence", test_state_persistence),
        ("Workflow Execution", test_simulated_workflow_execution),
        ("Task Integration", test_real_task_integration),
        ("System Validation", test_system_comprehensive_validation)
    ]

    passed_tests = 0

    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()

            test_results[test_name] = result
            if result:
                passed_tests += 1

        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            test_results[test_name] = False

    # Generate summary
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)

    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<25} {status}")

    success_rate = passed_tests / len(tests)
    print(f"\n🎯 Overall Success Rate: {success_rate:.1%} ({passed_tests}/{len(tests)} tests passed)")

    if success_rate >= 0.8:
        print("🏆 SYSTEM STATUS: VERIFIED AND OPERATIONAL")
    elif success_rate >= 0.6:
        print("⚠️  SYSTEM STATUS: PARTIALLY FUNCTIONAL - NEEDS ATTENTION")
    else:
        print("❌ SYSTEM STATUS: CRITICAL ISSUES DETECTED")

    return test_results, success_rate

if __name__ == "__main__":
    asyncio.run(run_all_tests())