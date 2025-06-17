#!/usr/bin/env python3
"""Test the simple kanban client"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient


async def test_simple():
    client = SimpleMCPKanbanClient()
    
    print("Testing Simple MCP Kanban Client")
    print("=" * 60)
    
    try:
        # Test get board summary
        print("\n1. Testing get_board_summary...")
        summary = await client.get_board_summary()
        stats = summary.get('stats', {})
        print(f"✅ Board has {stats.get('totalCards', 0)} cards")
        
        # Test get available tasks
        print("\n2. Testing get_available_tasks...")
        tasks = await client.get_available_tasks()
        print(f"✅ Found {len(tasks)} available tasks")
        for task in tasks:
            print(f"   - {task.name}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple())