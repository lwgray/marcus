#!/usr/bin/env python3
"""
Test the SimpleMCPKanbanClient functionality
Quick diagnostic to verify the client is working properly
"""

import asyncio
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient


async def test_simple():
    """Test basic SimpleMCPKanbanClient operations"""
    client = SimpleMCPKanbanClient()
    
    print("🔍 Testing Simple MCP Kanban Client")
    print("=" * 60)
    
    # Check configuration
    print(f"\nConfiguration loaded:")
    print(f"  - Project ID: {client.project_id}")
    print(f"  - Board ID: {client.board_id}")
    
    if not client.board_id:
        print("❌ No board_id configured. Check config_pm_agent.json")
        return
    
    try:
        # Test get board summary
        print("\n1. Testing get_board_summary...")
        summary = await client.get_board_summary()
        stats = summary.get('stats', {})
        print(f"✅ Board statistics:")
        print(f"   - Total cards: {stats.get('totalCards', 0)}")
        print(f"   - In progress: {stats.get('inProgressCount', 0)}")
        print(f"   - Done: {stats.get('doneCount', 0)}")
        print(f"   - Completion: {stats.get('completionPercentage', 0)}%")
        
        # Test get available tasks
        print("\n2. Testing get_available_tasks...")
        tasks = await client.get_available_tasks()
        print(f"✅ Found {len(tasks)} available tasks")
        
        if tasks:
            print("\nAvailable tasks:")
            for i, task in enumerate(tasks[:5]):  # Show first 5
                print(f"   {i+1}. {task.name}")
                print(f"      - ID: {task.id}")
                print(f"      - Status: {task.status.value}")
                print(f"      - Priority: {task.priority.value}")
        else:
            print("   (No unassigned tasks in TODO/Backlog lists)")
        
        # Test task assignment (if tasks available)
        if tasks and len(tasks) > 0:
            print("\n3. Testing task assignment...")
            test_task = tasks[0]
            test_agent = "diagnostic-test-agent"
            
            print(f"   Assigning '{test_task.name}' to {test_agent}")
            await client.assign_task(test_task.id, test_agent)
            print(f"✅ Task assigned successfully")
            print("   (Check kanban board for comment and list change)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple())