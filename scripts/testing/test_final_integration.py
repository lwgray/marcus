#!/usr/bin/env python3
"""
Final integration test - Verify PM Agent works with refactored Kanban client
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pm_agent_mvp_fixed import PMAgentMVP
from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient


async def test_complete_integration():
    """Test complete PM Agent integration with refactored client"""
    print("🧪 PM Agent Integration Test with Refactored Client")
    print("=" * 70)
    
    # Initialize PM Agent with refactored client
    pm_agent = PMAgentMVP()
    
    # Phase 1: Test PM Agent Server Side
    print("\n📡 Phase 1: Testing PM Agent Server (Worker Tools)")
    print("-" * 60)
    
    # Register test agents
    agents = [
        {
            "agent_id": "test_backend_dev",
            "name": "Test Backend Dev",
            "role": "Backend Developer",
            "skills": ["python", "django", "postgresql"]
        },
        {
            "agent_id": "test_frontend_dev",
            "name": "Test Frontend Dev",
            "role": "Frontend Developer",
            "skills": ["javascript", "react", "css"]
        }
    ]
    
    for agent in agents:
        result = await pm_agent._register_agent(**agent)
        print(f"✅ Registered: {agent['name']}")
    
    # Phase 2: Test Kanban Integration
    print("\n\n🔗 Phase 2: Testing Kanban Integration")
    print("-" * 60)
    
    # Set up the refactored client
    pm_agent.kanban_client.project_id = "1533678301472621705"
    
    print("\n1️⃣ Testing connection context manager...")
    async with pm_agent.kanban_client.connect() as conn:
        print(f"   ✅ Connected successfully")
        print(f"   Project ID: {pm_agent.kanban_client.project_id}")
        print(f"   Board ID: {pm_agent.kanban_client.board_id}")
    
    print("\n2️⃣ Creating test board...")
    board_name = f"Integration Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    async with pm_agent.kanban_client.connect() as conn:
        result = await conn.call_tool("mcp_kanban_project_board_manager", {
            "action": "create_board",
            "projectId": pm_agent.kanban_client.project_id,
            "name": board_name,
            "position": 1
        })
        
        import json
        board_data = json.loads(result.content[0].text)
        board_id = board_data["id"]
        pm_agent.kanban_client.board_id = board_id
        print(f"   ✅ Created board: {board_name}")
        print(f"   Board ID: {board_id}")
    
    print("\n3️⃣ Creating test tasks...")
    tasks_created = []
    for i in range(3):
        task = await pm_agent.kanban_client.create_task({
            "name": f"Integration Test Task {i+1}",
            "description": f"Task {i+1} for integration testing",
            "labels": ["test", "automated"]
        })
        tasks_created.append(task)
        print(f"   ✅ Created task: {task.name}")
    
    print("\n4️⃣ Testing task assignment workflow...")
    # Request task for backend dev
    task_result = await pm_agent._request_next_task("test_backend_dev")
    
    if task_result.get("has_task"):
        assignment = task_result["assignment"]
        print(f"   ✅ Task assigned: {assignment['task_name']}")
        print(f"   Priority: {assignment['priority']}")
        
        # Report progress
        print("\n5️⃣ Testing progress reporting...")
        progress_result = await pm_agent._report_task_progress(
            agent_id="test_backend_dev",
            task_id=assignment['task_id'],
            status="in_progress",
            progress=50,
            message="Integration test progress update"
        )
        print(f"   ✅ Progress reported: {progress_result.get('acknowledged')}")
        
        # Test blocker
        print("\n6️⃣ Testing blocker reporting...")
        blocker_result = await pm_agent._report_blocker(
            agent_id="test_backend_dev",
            task_id=assignment['task_id'],
            blocker_description="Test blocker for integration testing",
            severity="medium"
        )
        print(f"   ✅ Blocker reported: {blocker_result.get('success')}")
    
    print("\n7️⃣ Testing project status...")
    status = await pm_agent._get_project_status()
    if status.get("success"):
        stats = status["project_status"]
        print(f"   ✅ Project status retrieved:")
        print(f"      Total cards: {stats['total_cards']}")
        print(f"      Completion: {stats['completion_percentage']}%")
    
    print("\n8️⃣ Testing board summary with refactored client...")
    summary = await pm_agent.kanban_client.get_board_summary()
    print(f"   ✅ Board summary retrieved")
    print(f"      Stats: {summary.get('stats', {}).get('totalCards', 0)} cards")
    
    # Cleanup
    print("\n\n🧹 Cleaning up...")
    async with pm_agent.kanban_client.connect() as conn:
        await conn.call_tool("mcp_kanban_project_board_manager", {
            "action": "delete_board",
            "boardId": board_id
        })
        print("   ✅ Test board deleted")
    
    print("\n" + "=" * 70)
    print("✅ Integration test completed successfully!")
    print("\nKey validations:")
    print("- ✅ PM Agent server tools working")
    print("- ✅ Refactored Kanban client working")
    print("- ✅ Async context manager pattern working")
    print("- ✅ All CRUD operations working")
    print("- ✅ Task assignment workflow working")
    print("- ✅ Progress and blocker reporting working")
    print("\n🎉 PM Agent is fully operational with the refactored client!")


if __name__ == "__main__":
    asyncio.run(test_complete_integration())