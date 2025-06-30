#!/usr/bin/env python3
"""
Final PM Agent Test Suite - Complete test of both halves
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pm_agent_mvp_fixed import PMAgentMVP


async def test_complete_workflow():
    """Test complete PM Agent workflow"""
    print("🧪 PM Agent Complete Workflow Test")
    print("=" * 70)
    
    pm_agent = PMAgentMVP()
    
    # Phase 1: Test Server-side (MCP Tools for Worker Agents)
    print("\n📡 Phase 1: Testing PM Agent MCP Server (Worker Agent Tools)")
    print("-" * 60)
    
    # Register multiple agents
    agents = [
        {
            "agent_id": "backend_alice",
            "name": "Alice Chen",
            "role": "Senior Backend Developer",
            "skills": ["python", "django", "postgresql", "redis", "docker"]
        },
        {
            "agent_id": "frontend_bob",
            "name": "Bob Smith",
            "role": "Frontend Developer",
            "skills": ["javascript", "react", "typescript", "css", "webpack"]
        },
        {
            "agent_id": "fullstack_charlie",
            "name": "Charlie Davis",
            "role": "Full Stack Developer",
            "skills": ["python", "javascript", "react", "fastapi", "mongodb"]
        }
    ]
    
    print("\n🤖 Registering Agents:")
    for agent in agents:
        result = await pm_agent._register_agent(**agent)
        if result.get("success"):
            print(f"   ✅ {agent['name']} ({agent['role']})")
        else:
            print(f"   ❌ Failed to register {agent['name']}: {result.get('error')}")
    
    # List all agents
    print("\n📋 Registered Agents:")
    list_result = await pm_agent._list_registered_agents()
    print(f"   Total: {list_result.get('agent_count', 0)} agents")
    
    # Phase 2: Test Client-side (Kanban Integration)
    print("\n\n🔗 Phase 2: Testing PM Agent MCP Client (Kanban Integration)")
    print("-" * 60)
    
    try:
        # Connect to Kanban
        print("   Connecting to Kanban MCP server...")
        await pm_agent.kanban_client.connect()
        print(f"   ✅ Connected to board: {pm_agent.kanban_client.board_id}")
        
        # Initialize AI
        await pm_agent.ai_engine.initialize()
        print("   ✅ AI engine initialized")
        
        # Phase 3: Test Complete Workflow
        print("\n\n🔄 Phase 3: Testing Complete Agent Workflow")
        print("-" * 60)
        
        # Agent 1 requests a task
        print("\n👤 Alice requests a task:")
        task_result = await pm_agent._request_next_task("backend_alice")
        
        alice_task_id = None
        if task_result.get("has_task"):
            assignment = task_result["assignment"]
            alice_task_id = assignment["task_id"]
            print(f"   ✅ Task assigned: {assignment['task_name']}")
            print(f"      Priority: {assignment['priority']}")
            print(f"      Task ID: {alice_task_id}")
            print(f"      Instructions: {assignment['instructions'][:100]}...")
            
            # Alice reports progress
            print("\n   📊 Alice reports 25% progress:")
            progress1 = await pm_agent._report_task_progress(
                agent_id="backend_alice",
                task_id=alice_task_id,
                status="in_progress",
                progress=25,
                message="Set up development environment and reviewed requirements"
            )
            print(f"      {'✅' if progress1.get('acknowledged') else '❌'} Progress reported")
            
            # Alice encounters a blocker
            print("\n   🚧 Alice reports a blocker:")
            blocker = await pm_agent._report_blocker(
                agent_id="backend_alice",
                task_id=alice_task_id,
                blocker_description="Database schema conflicts with existing production tables",
                severity="high"
            )
            if blocker.get("success"):
                print("      ✅ Blocker reported")
                print(f"      💡 Suggestion: {blocker['resolution_suggestion'][:100]}...")
        else:
            print(f"   ⚠️  No tasks available: {task_result.get('message')}")
        
        # Agent 2 requests a task
        print("\n\n👤 Bob requests a task:")
        task_result2 = await pm_agent._request_next_task("frontend_bob")
        
        if task_result2.get("has_task"):
            assignment2 = task_result2["assignment"]
            print(f"   ✅ Task assigned: {assignment2['task_name']}")
            print(f"      Priority: {assignment2['priority']}")
        else:
            print(f"   ⚠️  No tasks available: {task_result2.get('message')}")
        
        # Check project status
        print("\n\n📈 Project Status:")
        status = await pm_agent._get_project_status()
        if status.get("success"):
            stats = status["project_status"]
            print(f"   Total tasks: {stats['total_cards']}")
            print(f"   Completion: {stats['completion_percentage']}%")
            print(f"   In Progress: {stats['in_progress_count']}")
            print(f"   Completed: {stats['done_count']}")
            print(f"   Urgent tasks: {stats['urgent_count']}")
            print(f"   Bugs: {stats['bug_count']}")
        
        # Show agent statuses
        print("\n\n👥 Agent Status Summary:")
        for agent_id in ["backend_alice", "frontend_bob", "fullstack_charlie"]:
            agent_status = await pm_agent._get_agent_status(agent_id)
            if agent_status.get("found"):
                info = agent_status["agent_info"]
                task_info = "No task" if not info.get("current_task") else f"{info['current_task']['task_name']}"
                print(f"   {info['name']}: {task_info}")
        
        # If Alice had a task, complete it
        if alice_task_id:
            print("\n\n✅ Alice completes her task:")
            completion = await pm_agent._report_task_progress(
                agent_id="backend_alice",
                task_id=alice_task_id,
                status="completed",
                progress=100,
                message="Resolved schema conflicts and completed implementation with tests"
            )
            print(f"   {'✅' if completion.get('acknowledged') else '❌'} Task marked as completed")
        
        # Final summary
        print("\n\n📊 Final Summary:")
        final_list = await pm_agent._list_registered_agents()
        for agent in final_list.get("agents", []):
            print(f"   {agent['name']}: {agent['completed_tasks']} tasks completed")
        
        # Cleanup
        await pm_agent.kanban_client.disconnect()
        
    except Exception as e:
        print(f"\n❌ Error during integration test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("✅ PM Agent test completed!")


if __name__ == "__main__":
    asyncio.run(test_complete_workflow())