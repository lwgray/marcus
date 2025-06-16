#!/usr/bin/env python3
"""Quick debug test for PM Agent"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.integrations.mcp_kanban_client import MCPKanbanClient

async def quick_test():
    """Quick test to see what's failing"""
    print("🔍 Quick Debug Test")
    
    try:
        # Test 1: Can we connect to Kanban?
        print("\n1. Testing Kanban connection...")
        client = MCPKanbanClient()
        await client.connect()
        print("✅ Kanban connected")
        print(f"   Board ID: {client.board_id}")
        print(f"   Project ID: {client.project_id}")
        
        # Test 2: Can we get tasks?
        print("\n2. Getting available tasks...")
        tasks = await client.get_available_tasks()
        print(f"✅ Found {len(tasks)} tasks")
        
        if tasks:
            print(f"   First task: {tasks[0].name}")
            
        await client.disconnect()
        print("\n✅ All basic tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(quick_test())