#!/usr/bin/env python3
"""
Test connection to board and debug hanging issues
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient


async def test_board_connection():
    """Test connection to the board"""
    print("🧪 Testing Board Connection")
    print("=" * 50)
    
    # Load config
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    config_path = os.path.join(project_root, 'config_pm_agent.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            print(f"📋 Config loaded:")
            print(f"   Project ID: {config.get('project_id')}")
            print(f"   Board ID: {config.get('board_id')}")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return False
    
    # Test connection
    client = MCPKanbanClient()
    client.project_id = config.get('project_id')
    client.board_id = config.get('board_id')
    
    print("\n🔌 Testing connection...")
    try:
        # Set a timeout for the connection
        async with asyncio.timeout(10):  # 10 second timeout
            async with client.connect() as conn:
                print("✅ Connected successfully!")
                
                # Test getting board info
                print("\n📊 Testing board access...")
                result = await conn.call_tool("mcp_kanban_project_board_manager", {
                    "action": "get_board",
                    "boardId": client.board_id
                })
                
                board_data = json.loads(result.content[0].text)
                print(f"✅ Board found: {board_data.get('name', 'Unknown')}")
                
                # Test getting lists
                print("\n📑 Testing list access...")
                result = await conn.call_tool("mcp_kanban_list_manager", {
                    "action": "get_all",
                    "boardId": client.board_id
                })
                
                lists = json.loads(result.content[0].text)
                print(f"✅ Found {len(lists)} lists")
                for lst in lists[:3]:  # Show first 3
                    print(f"   - {lst['name']}")
                
                return True
                
    except asyncio.TimeoutError:
        print("\n❌ Connection timed out!")
        print("\nPossible causes:")
        print("1. Kanban MCP server not running")
        print("2. Planka not accessible")
        print("3. Network issues")
        print("\nTry:")
        print("1. Check if Planka is running: curl http://localhost:3333")
        print("2. Start Kanban MCP manually: node /path/to/kanban-mcp/dist/index.js")
        return False
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_quick_task_creation():
    """Test creating a single task quickly"""
    print("\n\n🧪 Quick Task Creation Test")
    print("=" * 50)
    
    client = MCPKanbanClient()
    client.project_id = "1533678301472621705"
    client.board_id = "1533859887128249584"
    
    try:
        async with asyncio.timeout(15):
            async with client.connect() as conn:
                # Get first list
                result = await conn.call_tool("mcp_kanban_list_manager", {
                    "action": "get_all",
                    "boardId": client.board_id
                })
                lists = json.loads(result.content[0].text)
                
                if not lists:
                    print("❌ No lists found")
                    return False
                
                first_list = lists[0]
                print(f"📝 Creating test task in '{first_list['name']}'...")
                
                # Create one test task
                result = await conn.call_tool("mcp_kanban_card_manager", {
                    "action": "create",
                    "name": "Test Task - Connection Working",
                    "description": "This is a test task to verify connection",
                    "listId": first_list["id"],
                    "position": 1
                })
                
                card_data = json.loads(result.content[0].text)
                print(f"✅ Created task with ID: {card_data['id']}")
                print("\n🎉 Task creation is working!")
                return True
                
    except asyncio.TimeoutError:
        print("❌ Task creation timed out")
        return False
    except Exception as e:
        print(f"❌ Task creation failed: {e}")
        return False


if __name__ == "__main__":
    print("Running connection tests...\n")
    
    # Run tests
    async def run_all_tests():
        # Test basic connection
        connection_ok = await test_board_connection()
        
        if connection_ok:
            # Test task creation
            await test_quick_task_creation()
        
        return connection_ok
    
    success = asyncio.run(run_all_tests())
    
    if not success:
        print("\n📌 Next steps:")
        print("1. Ensure Planka is running at http://localhost:3333")
        print("2. Check Node.js is installed: which node")
        print("3. Verify kanban-mcp path exists: ls /Users/lwgray/dev/kanban-mcp/dist/index.js")
        print("4. Try running kanban-mcp manually to see errors")
    
    sys.exit(0 if success else 1)