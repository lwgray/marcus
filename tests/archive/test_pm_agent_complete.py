#!/usr/bin/env python3
"""
Complete PM Agent Test Suite - Tests both MCP Server and Client sides
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import PM Agent components
from src.core.models import Task, TaskStatus, Priority
from src.integrations.mcp_kanban_client import MCPKanbanClient
from pm_agent_mvp_fixed import PMAgentMVP


class PMAgentTester:
    """Test suite for PM Agent functionality"""
    
    def __init__(self):
        self.kanban_client = None
        self.pm_agent = None
        self.test_results = []
        
    async def setup(self):
        """Setup test environment"""
        print("🔧 Setting up test environment...")
        
        # Initialize Kanban client
        self.kanban_client = MCPKanbanClient()
        await self.kanban_client.connect()
        print("✅ Kanban client connected")
        
        # Initialize PM Agent (but don't start the server)
        self.pm_agent = PMAgentMVP()
        await self.pm_agent.kanban_client.connect()
        await self.pm_agent.ai_engine.initialize()
        print("✅ PM Agent initialized")
        
    async def teardown(self):
        """Cleanup test environment"""
        print("\n🧹 Cleaning up...")
        if self.kanban_client:
            await self.kanban_client.disconnect()
        if self.pm_agent and self.pm_agent.kanban_client:
            await self.pm_agent.kanban_client.disconnect()
            
    async def test_kanban_client_operations(self):
        """Test 1: Kanban MCP Client Operations"""
        print("\n📋 Test 1: Testing Kanban MCP Client Operations")
        
        try:
            # Test getting available tasks
            print("  → Getting available tasks...")
            tasks = await self.kanban_client.get_available_tasks()
            print(f"  ✅ Found {len(tasks)} available tasks")
            
            if tasks:
                # Test getting task details
                first_task = tasks[0]
                print(f"  → Getting details for task: {first_task.name}")
                details = await self.kanban_client.get_task_details(first_task.id)
                print(f"  ✅ Got task details: {details.name}")
                
                # Test adding a comment
                print("  → Adding test comment...")
                await self.kanban_client.add_comment(
                    first_task.id, 
                    f"🧪 Test comment from PM Agent at {datetime.now().isoformat()}"
                )
                print("  ✅ Comment added successfully")
            
            # Test board summary
            print("  → Getting board summary...")
            summary = await self.kanban_client.get_board_summary()
            print(f"  ✅ Board summary: {summary.get('stats', {}).get('totalCards', 0)} total cards")
            
            self.test_results.append(("Kanban Client Operations", "PASSED"))
            return True
            
        except Exception as e:
            print(f"  ❌ Test failed: {e}")
            self.test_results.append(("Kanban Client Operations", f"FAILED: {e}"))
            return False
            
    async def test_agent_registration(self):
        """Test 2: Agent Registration"""
        print("\n👤 Test 2: Testing Agent Registration")
        
        try:
            # Register a test agent
            agent_data = {
                "agent_id": "test_agent_1",
                "name": "Test Agent One",
                "role": "Backend Developer",
                "skills": ["python", "fastapi", "postgresql"]
            }
            
            print(f"  → Registering agent: {agent_data['name']}")
            result = await self.pm_agent._register_agent(**agent_data)
            
            if result.get("success"):
                print(f"  ✅ Agent registered: {result['message']}")
                
                # Verify agent status
                print("  → Checking agent status...")
                status = await self.pm_agent._get_agent_status(agent_data["agent_id"])
                
                if status.get("found"):
                    print(f"  ✅ Agent found in system: {status['agent_info']['name']}")
                    self.test_results.append(("Agent Registration", "PASSED"))
                    return True
                else:
                    print("  ❌ Agent not found after registration")
                    self.test_results.append(("Agent Registration", "FAILED: Agent not found"))
                    return False
            else:
                print(f"  ❌ Registration failed: {result.get('error')}")
                self.test_results.append(("Agent Registration", f"FAILED: {result.get('error')}"))
                return False
                
        except Exception as e:
            print(f"  ❌ Test failed: {e}")
            self.test_results.append(("Agent Registration", f"FAILED: {e}"))
            return False
            
    async def test_task_assignment(self):
        """Test 3: Task Assignment Flow"""
        print("\n📝 Test 3: Testing Task Assignment")
        
        try:
            # First register an agent if not already done
            agent_id = "test_agent_2"
            if agent_id not in self.pm_agent.agent_status:
                print("  → Registering test agent...")
                await self.pm_agent._register_agent(
                    agent_id=agent_id,
                    name="Test Agent Two",
                    role="Frontend Developer",
                    skills=["javascript", "react", "typescript"]
                )
            
            # Request a task
            print(f"  → Requesting task for agent: {agent_id}")
            result = await self.pm_agent._request_next_task(agent_id)
            
            if result.get("has_task"):
                assignment = result["assignment"]
                print(f"  ✅ Task assigned: {assignment['task_name']}")
                print(f"     Priority: {assignment['priority']}")
                print(f"     Instructions: {assignment['instructions'][:100]}...")
                
                self.test_results.append(("Task Assignment", "PASSED"))
                return True, assignment['task_id']
            else:
                if "No tasks available" in result.get("message", ""):
                    print("  ⚠️  No tasks available for assignment")
                    self.test_results.append(("Task Assignment", "PASSED (No tasks available)"))
                    return True, None
                else:
                    print(f"  ❌ Task assignment failed: {result.get('error', result.get('message'))}")
                    self.test_results.append(("Task Assignment", f"FAILED: {result.get('error')}"))
                    return False, None
                    
        except Exception as e:
            print(f"  ❌ Test failed: {e}")
            self.test_results.append(("Task Assignment", f"FAILED: {e}"))
            return False, None
            
    async def test_progress_reporting(self, task_id: Optional[str] = None):
        """Test 4: Progress Reporting"""
        print("\n📊 Test 4: Testing Progress Reporting")
        
        try:
            agent_id = "test_agent_2"
            
            # If no task_id provided, try to get one
            if not task_id:
                if agent_id in self.pm_agent.agent_tasks:
                    task_id = self.pm_agent.agent_tasks[agent_id].task_id
                else:
                    print("  ⚠️  No active task to report progress on")
                    self.test_results.append(("Progress Reporting", "SKIPPED (No active task)"))
                    return True
            
            # Report progress
            print(f"  → Reporting 50% progress on task: {task_id}")
            result = await self.pm_agent._report_task_progress(
                agent_id=agent_id,
                task_id=task_id,
                status="in_progress",
                progress=50,
                message="Completed initial implementation, starting tests"
            )
            
            if result.get("acknowledged"):
                print("  ✅ Progress reported successfully")
                
                # Report completion
                print("  → Reporting task completion...")
                result = await self.pm_agent._report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="completed",
                    progress=100,
                    message="All tests passing, task complete"
                )
                
                if result.get("acknowledged"):
                    print("  ✅ Task marked as completed")
                    self.test_results.append(("Progress Reporting", "PASSED"))
                    return True
                    
            print(f"  ❌ Progress reporting failed: {result.get('error')}")
            self.test_results.append(("Progress Reporting", f"FAILED: {result.get('error')}"))
            return False
            
        except Exception as e:
            print(f"  ❌ Test failed: {e}")
            self.test_results.append(("Progress Reporting", f"FAILED: {e}"))
            return False
            
    async def test_blocker_reporting(self):
        """Test 5: Blocker Reporting"""
        print("\n🚧 Test 5: Testing Blocker Reporting")
        
        try:
            # Create a test task or use existing
            agent_id = "test_agent_3"
            
            # Register agent
            await self.pm_agent._register_agent(
                agent_id=agent_id,
                name="Test Agent Three",
                role="DevOps Engineer",
                skills=["kubernetes", "docker", "terraform"]
            )
            
            # Get a task
            task_result = await self.pm_agent._request_next_task(agent_id)
            
            if not task_result.get("has_task"):
                print("  ⚠️  No task available for blocker test")
                self.test_results.append(("Blocker Reporting", "SKIPPED (No task available)"))
                return True
            
            task_id = task_result["assignment"]["task_id"]
            
            # Report a blocker
            print(f"  → Reporting blocker on task: {task_id}")
            result = await self.pm_agent._report_blocker(
                agent_id=agent_id,
                task_id=task_id,
                blocker_description="Database migration failed due to missing permissions on production database",
                severity="high"
            )
            
            if result.get("success"):
                print("  ✅ Blocker reported successfully")
                print(f"  💡 Resolution suggestion: {result['resolution_suggestion'][:100]}...")
                self.test_results.append(("Blocker Reporting", "PASSED"))
                return True
            else:
                print(f"  ❌ Blocker reporting failed: {result.get('error')}")
                self.test_results.append(("Blocker Reporting", f"FAILED: {result.get('error')}"))
                return False
                
        except Exception as e:
            print(f"  ❌ Test failed: {e}")
            self.test_results.append(("Blocker Reporting", f"FAILED: {e}"))
            return False
            
    async def test_project_status(self):
        """Test 6: Project Status Queries"""
        print("\n📈 Test 6: Testing Project Status")
        
        try:
            # Get project status
            print("  → Getting project status...")
            result = await self.pm_agent._get_project_status()
            
            if result.get("success"):
                status = result["project_status"]
                print("  ✅ Project status retrieved:")
                print(f"     Total cards: {status['total_cards']}")
                print(f"     Completion: {status['completion_percentage']}%")
                print(f"     In progress: {status['in_progress_count']}")
                print(f"     Completed: {status['done_count']}")
                
                # List all agents
                print("\n  → Listing registered agents...")
                agents_result = await self.pm_agent._list_registered_agents()
                
                if agents_result.get("success"):
                    print(f"  ✅ Found {agents_result['agent_count']} registered agents:")
                    for agent in agents_result["agents"]:
                        print(f"     - {agent['name']} ({agent['role']}) - {agent['completed_tasks']} tasks completed")
                    
                    self.test_results.append(("Project Status", "PASSED"))
                    return True
                    
            print(f"  ❌ Status query failed: {result.get('error')}")
            self.test_results.append(("Project Status", f"FAILED: {result.get('error')}"))
            return False
            
        except Exception as e:
            print(f"  ❌ Test failed: {e}")
            self.test_results.append(("Project Status", f"FAILED: {e}"))
            return False
            
    async def run_all_tests(self):
        """Run all tests in sequence"""
        print("\n🚀 Starting PM Agent Complete Test Suite")
        print("=" * 50)
        
        await self.setup()
        
        # Run tests
        await self.test_kanban_client_operations()
        await self.test_agent_registration()
        
        # Task assignment returns task_id for next test
        success, task_id = await self.test_task_assignment()
        
        if task_id:
            await self.test_progress_reporting(task_id)
        else:
            await self.test_progress_reporting()
            
        await self.test_blocker_reporting()
        await self.test_project_status()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Summary:")
        print("=" * 50)
        
        passed = 0
        failed = 0
        skipped = 0
        
        for test_name, result in self.test_results:
            status_emoji = "✅" if "PASSED" in result else ("⚠️" if "SKIPPED" in result else "❌")
            print(f"{status_emoji} {test_name}: {result}")
            
            if "PASSED" in result:
                passed += 1
            elif "SKIPPED" in result:
                skipped += 1
            else:
                failed += 1
        
        print("\n" + "=" * 50)
        print(f"Total: {len(self.test_results)} tests")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Skipped: {skipped}")
        print("=" * 50)
        
        await self.teardown()
        
        return failed == 0


async def main():
    """Main test runner"""
    tester = PMAgentTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)