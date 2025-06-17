#!/usr/bin/env python3
"""
Reset the board by cleaning all tasks and repopulating with fresh todo app tasks
Auto-accepts confirmation for automation
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set environment
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

# Configuration
PROJECT_ID = "1533678301472621705"
BOARD_ID = "1533859887128249584"


async def clean_board(session):
    """Remove all cards from the board"""
    print("\n🧹 Cleaning board...")
    
    # Get board summary to find all cards
    summary_result = await session.call_tool(
        "mcp_kanban_project_board_manager",
        {
            "action": "get_board_summary",
            "boardId": BOARD_ID,
            "includeTaskDetails": False
        }
    )
    summary = json.loads(summary_result.content[0].text)
    
    # Delete all cards
    total_cards = 0
    for lst in summary.get('lists', []):
        for card in lst.get('cards', []):
            try:
                await session.call_tool(
                    "mcp_kanban_card_manager",
                    {"action": "delete", "id": card['id']}
                )
                total_cards += 1
                print(f"  ❌ Deleted: {card['name']}")
            except Exception as e:
                print(f"  ⚠️  Failed to delete {card['name']}: {e}")
    
    print(f"\n✅ Cleaned {total_cards} cards from the board")
    
    # Delete all lists
    lists_result = await session.call_tool(
        "mcp_kanban_list_manager",
        {"action": "get_all", "boardId": BOARD_ID}
    )
    lists = json.loads(lists_result.content[0].text)
    
    for lst in lists:
        try:
            await session.call_tool(
                "mcp_kanban_list_manager",
                {"action": "delete", "id": lst['id']}
            )
        except:
            pass
    print(f"✅ Deleted {len(lists)} lists")
    
    return True


async def create_todo_app_board(session):
    """Create a fresh todo app board with tasks"""
    print("\n🚀 Creating Todo App Board...")
    print("=" * 60)
    
    # 1. Create Lists
    print("\n📋 Creating Lists...")
    lists = [
        {"name": "Backlog", "position": 1},
        {"name": "In Progress", "position": 2}, 
        {"name": "Review", "position": 3},
        {"name": "Done", "position": 4}
    ]
    
    created_lists = {}
    for list_data in lists:
        result = await session.call_tool(
            "mcp_kanban_list_manager",
            {
                "action": "create",
                "boardId": BOARD_ID,
                "name": list_data["name"],
                "position": list_data["position"]
            }
        )
        created_list = json.loads(result.content[0].text)
        created_lists[list_data["name"]] = created_list
        print(f"  ✅ Created list: {list_data['name']}")
    
    # 2. Create Labels  
    print("\n🏷️  Creating Labels...")
    labels = [
        {"name": "Frontend", "color": "lagoon-blue"},
        {"name": "Backend", "color": "berry-red"},
        {"name": "Database", "color": "pumpkin-orange"},
        {"name": "Testing", "color": "sunny-grass"},
        {"name": "Bug", "color": "midnight-blue"},
        {"name": "Feature", "color": "pink-tulip"},
        {"name": "High Priority", "color": "red-burgundy"}
    ]
    
    created_labels = {}
    for idx, label_data in enumerate(labels):
        result = await session.call_tool(
            "mcp_kanban_label_manager",
            {
                "action": "create",
                "boardId": BOARD_ID,
                "name": label_data["name"],
                "color": label_data["color"],
                "position": idx + 1
            }
        )
        created_label = json.loads(result.content[0].text)
        created_labels[label_data["name"]] = created_label
        print(f"  ✅ Created label: {label_data['name']}")
    
    # 3. Create Cards with Tasks
    print("\n📝 Creating Cards with Tasks...")
    
    # Define todo app features
    todo_features = [
        {
            "name": "Setup Project Infrastructure",
            "description": "Initialize the project with modern tooling",
            "list": "Done",
            "labels": ["Frontend", "Backend"],
            "tasks": [
                "Create Next.js 14 project",
                "Setup TypeScript",
                "Configure Tailwind CSS",
                "Setup ESLint and Prettier"
            ]
        },
        {
            "name": "Design Database Schema",
            "description": "Design and implement the database",
            "list": "In Progress",
            "labels": ["Backend", "Database"],
            "tasks": [
                "Design Todo model",
                "Design User model",
                "Setup Prisma ORM",
                "Create migrations"
            ]
        },
        {
            "name": "Implement Authentication",
            "description": "Add user authentication",
            "list": "In Progress",
            "labels": ["Backend", "Feature", "High Priority"],
            "tasks": [
                "Setup NextAuth.js",
                "Add OAuth providers",
                "Create login page",
                "Add session management"
            ]
        },
        {
            "name": "Build Todo API",
            "description": "Create REST API endpoints",
            "list": "Backlog",
            "labels": ["Backend", "Feature"],
            "tasks": [
                "Create POST /api/todos",
                "Create GET /api/todos",
                "Create PUT /api/todos/:id",
                "Create DELETE /api/todos/:id"
            ]
        },
        {
            "name": "Create UI Components",
            "description": "Build React components",
            "list": "Backlog",
            "labels": ["Frontend", "Feature"],
            "tasks": [
                "Create TodoList component",
                "Create TodoItem component",
                "Create AddTodo form",
                "Add drag-and-drop"
            ]
        },
        {
            "name": "Write Tests",
            "description": "Add comprehensive testing",
            "list": "Backlog",
            "labels": ["Testing"],
            "tasks": [
                "Setup Jest",
                "Write API tests",
                "Write component tests",
                "Setup E2E tests"
            ]
        },
        {
            "name": "Fix Mobile Layout",
            "description": "Fix responsive issues",
            "list": "Review",
            "labels": ["Frontend", "Bug", "High Priority"],
            "tasks": [
                "Fix small screen layout",
                "Test on devices",
                "Fix touch interactions"
            ]
        }
    ]
    
    created_cards = []
    for idx, feature in enumerate(todo_features):
        # Create card
        list_id = created_lists[feature["list"]]["id"]
        
        result = await session.call_tool(
            "mcp_kanban_card_manager",
            {
                "action": "create",
                "listId": list_id,
                "name": feature["name"],
                "description": feature["description"],
                "position": (idx + 1) * 65536
            }
        )
        card = json.loads(result.content[0].text)
        created_cards.append(card)
        print(f"\n  📌 Created: {feature['name']}")
        
        # Add labels
        for label_name in feature["labels"]:
            if label_name in created_labels:
                await session.call_tool(
                    "mcp_kanban_label_manager",
                    {
                        "action": "add_to_card",
                        "cardId": card["id"],
                        "labelId": created_labels[label_name]["id"]
                    }
                )
        
        # Create tasks
        for task_idx, task_name in enumerate(feature["tasks"]):
            await session.call_tool(
                "mcp_kanban_task_manager",
                {
                    "action": "create",
                    "cardId": card["id"],
                    "name": task_name,
                    "position": (task_idx + 1) * 65536
                }
            )
        
        print(f"     ✅ Added {len(feature['tasks'])} tasks")
    
    # Summary
    print("\n📊 Summary")
    print("=" * 60)
    print(f"Lists: {len(created_lists)}")
    print(f"Cards: {len(created_cards)}")
    print(f"Labels: {len(created_labels)}")
    
    total_tasks = sum(len(f["tasks"]) for f in todo_features)
    print(f"Tasks: {total_tasks}")
    
    print("\n✅ Todo App board created successfully!")
    return True


async def reset_board():
    """Main function to reset the board"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🔄 Todo Board Reset (Auto Mode)")
    print("=" * 60)
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected to kanban-mcp")
            
            # Clean the board
            await clean_board(session)
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Create new board
            await create_todo_app_board(session)
            
            print("\n🎉 Board reset complete!")
            print(f"View at: http://localhost:3333")


if __name__ == "__main__":
    asyncio.run(reset_board())
