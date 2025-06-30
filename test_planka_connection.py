#!/usr/bin/env python3
"""
Test Planka connection to see if Marcus can connect
"""

import asyncio
import os
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables
os.environ['KANBAN_PROVIDER'] = 'planka'
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

from src.integrations.kanban_factory import KanbanFactory


async def test_planka_connection():
    """Test if we can connect to Planka"""
    
    print("=== Testing Planka Connection ===\n")
    
    print("Environment variables:")
    print(f"  KANBAN_PROVIDER: {os.environ.get('KANBAN_PROVIDER')}")
    print(f"  PLANKA_BASE_URL: {os.environ.get('PLANKA_BASE_URL')}")
    print(f"  PLANKA_AGENT_EMAIL: {os.environ.get('PLANKA_AGENT_EMAIL')}")
    print()
    
    try:
        # Create kanban client
        print("1. Creating kanban client...")
        kanban_client = KanbanFactory.create('planka')
        print("   ✓ Kanban client created")
        
        # Test connection
        print("\n2. Testing connection...")
        if hasattr(kanban_client, 'connect'):
            await kanban_client.connect()
            print("   ✓ Connected successfully")
        
        # Get tasks
        print("\n3. Getting tasks...")
        tasks = await kanban_client.get_all_tasks()
        print(f"   ✓ Retrieved {len(tasks)} tasks")
        
        if tasks:
            print("\n   Sample tasks:")
            for i, task in enumerate(tasks[:3]):
                print(f"     {i+1}. {task.name} (Status: {task.status})")
        else:
            print("   No tasks found on the board")
        
        print(f"\n✅ Connection successful! Marcus should now work with get_project_status")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nPossible issues:")
        print("- Planka is not running on localhost:3333")
        print("- Demo user doesn't exist or has wrong credentials")
        print("- Board ID in config_marcus.json is incorrect")
        print("- Network connectivity issues")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_planka_connection())
    
    if success:
        print(f"\n🎉 You should now be able to use get_project_status from Marcus!")
    else:
        print(f"\n💡 Fix the connection issues above, then try get_project_status again")