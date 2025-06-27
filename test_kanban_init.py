#!/usr/bin/env python3
"""Test script to debug kanban client initialization"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_direct_client():
    """Test SimpleMCPKanbanClient directly"""
    from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient
    
    print("Testing SimpleMCPKanbanClient...")
    print(f"Current directory: {os.getcwd()}")
    print(f"Config file exists: {os.path.exists('config_marcus.json')}")
    
    try:
        client = SimpleMCPKanbanClient()
        print(f"✅ Client initialized")
        print(f"   Board ID: {client.board_id}")
        print(f"   Project ID: {client.project_id}")
        
        # Try to get tasks
        print("\nGetting available tasks...")
        tasks = await client.get_available_tasks()
        print(f"✅ Got {len(tasks)} tasks")
        for task in tasks[:3]:  # Show first 3
            print(f"   - {task.name}")
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def test_via_factory():
    """Test via KanbanFactory"""
    from src.integrations.kanban_factory import KanbanFactory
    
    print("\n\nTesting via KanbanFactory...")
    
    try:
        kanban = KanbanFactory.create_default()
        print(f"✅ Created kanban interface: {type(kanban).__name__}")
        
        # Connect
        print("\nConnecting...")
        await kanban.connect()
        print("✅ Connected")
        
        # Get tasks
        print("\nGetting available tasks...")
        tasks = await kanban.get_available_tasks()
        print(f"✅ Got {len(tasks)} tasks")
        for task in tasks[:3]:  # Show first 3
            print(f"   - {task.name}")
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def test_from_marcus_state():
    """Test how marcus_mcp_server initializes kanban"""
    from marcus_mcp_server import state, refresh_project_state
    
    print("\n\nTesting from Marcus state...")
    
    try:
        print("Initializing kanban...")
        await state.initialize_kanban()
        print(f"✅ Kanban initialized: {type(state.kanban_client).__name__}")
        
        # Refresh project state
        print("\nRefreshing project state...")
        await refresh_project_state()
        print("✅ Project state refreshed")
        print(f"   Total tasks: {len(state.project_tasks)}")
        print(f"   Project state: {state.project_state}")
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_direct_client()
    await test_via_factory()
    await test_from_marcus_state()

if __name__ == "__main__":
    asyncio.run(main())