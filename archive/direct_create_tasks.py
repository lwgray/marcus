#!/usr/bin/env python3
"""
Direct task creation using MCP session - bypasses the refactored client
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ID = "1533678301472621705"


async def create_tasks_directly():
    """Create tasks using direct MCP connection"""
    
    # Server parameters
    server_params = StdioServerParameters(
        command="/opt/homebrew/bin/node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env={
            "PLANKA_BASE_URL": "http://localhost:3333",
            "PLANKA_AGENT_EMAIL": "demo@demo.demo",
            "PLANKA_AGENT_PASSWORD": "demo"
        }
    )
    
    # Connect
    print("🔌 Connecting to Kanban MCP directly...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected!")
            
            # First, find or create a board
            print("\n📋 Checking for existing boards...")
            result = await session.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_boards",
                "projectId": PROJECT_ID
            })
            
            boards = json.loads(result.content[0].text)
            # boards is directly a list
            
            if boards:
                board = boards[0]
                board_id = board["id"]
                print(f"✅ Found board: {board['name']}")
            else:
                print("📝 Creating new board...")
                result = await session.call_tool("mcp_kanban_project_board_manager", {
                    "action": "create_board",
                    "projectId": PROJECT_ID,
                    "name": "Todo App Development",
                    "position": 1
                })
                board_data = json.loads(result.content[0].text)
                board_id = board_data["id"]
                print(f"✅ Created board with ID: {board_id}")
            
            # Get lists
            print("\n📑 Getting lists...")
            result = await session.call_tool("mcp_kanban_list_manager", {
                "action": "get_all",
                "boardId": board_id
            })
            lists = json.loads(result.content[0].text)
            todo_list = lists[0]  # First list
            
            # Create a few test tasks
            print(f"\n📝 Creating tasks in '{todo_list['name']}'...")
            
            tasks = [
                {
                    "name": "BACKEND-001: Initialize FastAPI project",
                    "description": "Set up Python project with FastAPI, create folder structure, requirements.txt",
                },
                {
                    "name": "FRONTEND-001: Initialize React project", 
                    "description": "Create React app with TypeScript, set up component structure",
                },
                {
                    "name": "DEVOPS-001: Docker setup",
                    "description": "Create Dockerfiles and docker-compose.yml for local development",
                }
            ]
            
            for i, task in enumerate(tasks):
                print(f"\nCreating task {i+1}/{len(tasks)}: {task['name']}")
                
                result = await session.call_tool("mcp_kanban_card_manager", {
                    "action": "create",
                    "name": task["name"],
                    "description": task["description"],
                    "listId": todo_list["id"],
                    "position": i + 1
                })
                
                card_data = json.loads(result.content[0].text)
                print(f"✅ Created card ID: {card_data['id']}")
            
            print(f"\n🎉 Successfully created {len(tasks)} tasks!")
            print(f"\n📋 View them at: http://localhost:3333")
            print(f"Board ID: {board_id}")
            
            # Save config
            config = {
                "project_id": PROJECT_ID,
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
            
            print(f"\n💾 Saved configuration to config_pm_agent.json")


if __name__ == "__main__":
    asyncio.run(create_tasks_directly())