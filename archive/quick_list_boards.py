#!/usr/bin/env python3
"""
Quick script to list boards in Task Master project
"""

import asyncio
import json
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient


async def quick_list():
    """Quick list of boards"""
    print("🔍 Quick board listing for Task Master project...")
    
    client = MCPKanbanClient()
    client.project_id = "1533678301472621705"
    
    try:
        print("📡 Connecting to Kanban MCP...")
        async with client.connect() as conn:
            print("✅ Connected!")
            print(f"   Project ID: {client.project_id}")
            print(f"   Board ID: {client.board_id}")
            
            if client.board_id:
                print(f"\n✅ Found board automatically: {client.board_id}")
                
                # Update config
                config = {
                    "project_id": client.project_id,
                    "board_id": client.board_id,
                    "project_name": "Task Master Test",
                    "auto_find_board": False,
                    "planka": {
                        "base_url": "http://localhost:3333",
                        "email": "demo@demo.demo",
                        "password": "demo"
                    }
                }
                
                with open("config_pm_agent.json", "w") as f:
                    json.dump(config, f, indent=2)
                
                print(f"\n💾 Saved board ID to config_pm_agent.json")
                print("\nYou can now run:")
                print("  python create_todo_app_tasks_fixed.py")
            else:
                print("\n⚠️  No board found. Let's create one...")
                
                board_name = f"Todo App Test - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                result = await conn.call_tool("mcp_kanban_project_board_manager", {
                    "action": "create_board",
                    "projectId": client.project_id,
                    "name": board_name,
                    "position": 1
                })
                
                board_data = json.loads(result.content[0].text)
                board_id = board_data["id"]
                
                print(f"✅ Created board: {board_name}")
                print(f"   Board ID: {board_id}")
                
                # Save to config
                config = {
                    "project_id": client.project_id,
                    "board_id": board_id,
                    "project_name": "Task Master Test",
                    "auto_find_board": False,
                    "planka": {
                        "base_url": "http://localhost:3333",
                        "email": "demo@demo.demo",
                        "password": "demo"
                    }
                }
                
                with open("config_pm_agent.json", "w") as f:
                    json.dump(config, f, indent=2)
                
                print(f"\n💾 Saved new board to config_pm_agent.json")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    from datetime import datetime
    success = asyncio.run(quick_list())
    sys.exit(0 if success else 1)