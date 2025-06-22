#!/usr/bin/env python3
"""
Simple script to create Todo App tasks directly using MCP
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set environment variables
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

# Simplified task list
TASKS = [
    {
        "name": "Set up project structure",
        "description": "Initialize project with folder structure and basic configuration",
        "priority": "high"
    },
    {
        "name": "Design database schema", 
        "description": "Design tables for users, todos, and relationships",
        "priority": "high"
    },
    {
        "name": "Create Todo model",
        "description": "Implement Todo model with validation and CRUD operations",
        "priority": "high"
    },
    {
        "name": "Set up database connection",
        "description": "Configure database with connection pooling",
        "priority": "high"
    },
    {
        "name": "Create API endpoints",
        "description": "Implement REST API for todo CRUD operations",
        "priority": "high"
    },
    {
        "name": "Add input validation",
        "description": "Create middleware for request validation",
        "priority": "medium"
    },
    {
        "name": "Implement error handling",
        "description": "Add global error handler and logging",
        "priority": "medium"
    },
    {
        "name": "Create frontend structure",
        "description": "Set up React app with TypeScript",
        "priority": "high"
    },
    {
        "name": "Build TodoList component",
        "description": "Create main list component with todo display",
        "priority": "high"
    },
    {
        "name": "Build TodoItem component",
        "description": "Create individual todo item with actions",
        "priority": "high"
    },
    {
        "name": "Build AddTodo form",
        "description": "Create form for adding new todos",
        "priority": "high"
    },
    {
        "name": "Connect frontend to API",
        "description": "Wire up components to backend API",
        "priority": "high"
    },
    {
        "name": "Add filtering and search",
        "description": "Implement todo filtering and search functionality",
        "priority": "medium"
    },
    {
        "name": "Style the application",
        "description": "Apply CSS and make responsive",
        "priority": "medium"
    },
    {
        "name": "Write tests",
        "description": "Create unit and integration tests",
        "priority": "high"
    },
    {
        "name": "Add authentication",
        "description": "Implement user login and registration",
        "priority": "medium"
    },
    {
        "name": "Deploy to production",
        "description": "Set up CI/CD and deploy to cloud",
        "priority": "high"
    }
]


async def create_tasks():
    """Create tasks on the board"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🚀 Creating Todo App tasks on Task Master Test board...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("✅ Connected to kanban-mcp")
            
            # 1. Find Task Master Test project
            print("\n📋 Finding Task Master Test project...")
            result = await session.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_projects",
                "page": 1,
                "perPage": 25
            })
            
            projects_data = json.loads(result.content[0].text)
            project_id = None
            board_id = None
            
            for project in projects_data["items"]:
                if project["name"] == "Task Master Test":
                    project_id = project["id"]
                    print(f"✅ Found project: {project['name']} (ID: {project_id})")
                    break
            
            if not project_id:
                print("❌ Task Master Test project not found!")
                return
            
            # 2. Find the board
            if "boards" in projects_data.get("included", {}):
                for board in projects_data["included"]["boards"]:
                    if board["projectId"] == project_id:
                        board_id = board["id"]
                        print(f"✅ Found board: {board['name']} (ID: {board_id})")
                        break
            
            if not board_id:
                print("❌ No board found for Task Master Test!")
                return
            
            # 3. Get lists on the board
            print("\n📋 Getting lists...")
            result = await session.call_tool("mcp_kanban_list_manager", {
                "action": "get_all",
                "boardId": board_id
            })
            
            lists = json.loads(result.content[0].text)
            todo_list = None
            
            for lst in lists:
                if "TODO" in lst["name"].upper() or "BACKLOG" in lst["name"].upper():
                    todo_list = lst
                    print(f"✅ Found list: {lst['name']} (ID: {lst['id']})")
                    break
            
            if not todo_list:
                print("❌ No TODO/Backlog list found!")
                return
            
            # 4. Create tasks
            print("\n📋 Creating tasks...")
            created = 0
            
            for i, task in enumerate(TASKS, 1):
                print(f"\n  [{i}/{len(TASKS)}] Creating: {task['name']}")
                
                try:
                    # Create the card
                    result = await session.call_tool("mcp_kanban_card_manager", {
                        "action": "create",
                        "listId": todo_list["id"],
                        "name": task["name"],
                        "description": task["description"]
                    })
                    
                    card = json.loads(result.content[0].text)
                    print(f"  ✅ Created card ID: {card['id']}")
                    
                    # Add priority label
                    color_map = {"high": "red", "medium": "orange", "low": "green"}
                    
                    try:
                        await session.call_tool("mcp_kanban_label_manager", {
                            "action": "add",
                            "cardId": card["id"],
                            "name": f"{task['priority']}-priority",
                            "color": color_map[task['priority']]
                        })
                        print(f"  ✅ Added {task['priority']} priority label")
                    except Exception as e:
                        print(f"  ⚠️  Could not add label: {str(e)}")
                    
                    created += 1
                    
                except Exception as e:
                    print(f"  ❌ Error: {str(e)}")
            
            print(f"\n✅ Successfully created {created}/{len(TASKS)} tasks!")
            
            # 5. Get final board summary
            print("\n📊 Board Summary:")
            result = await session.call_tool("mcp_kanban_board_manager", {
                "action": "get_stats",
                "boardId": board_id
            })
            
            stats = json.loads(result.content[0].text)
            if "stats" in stats:
                s = stats["stats"]
                print(f"  Total cards: {s.get('totalCards', 0)}")
                print(f"  In Progress: {s.get('inProgressCount', 0)}")
                print(f"  Done: {s.get('doneCount', 0)}")


if __name__ == "__main__":
    asyncio.run(create_tasks())