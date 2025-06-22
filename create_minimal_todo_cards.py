#!/usr/bin/env python3
"""
Create Todo App cards with minimal information
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

# Load the JSON data
with open('todo_app_planka_cards.json', 'r') as f:
    TODO_APP_DATA = json.load(f)

# Minimal card info - just the essentials
MINIMAL_CARDS = {
    "card-001": {
        "description": "Set up project folders and install dependencies",
        "subtasks": ["Initialize project", "Install packages"]
    },
    "card-002": {
        "description": "Create database tables for users and todos",
        "subtasks": ["Create schema", "Run migrations"]
    },
    "card-003": {
        "description": "Create Todo model with CRUD operations",
        "subtasks": ["Define model", "Add methods"]
    },
    "card-004": {
        "description": "Configure database connection",
        "subtasks": ["Install packages", "Configure connection"]
    },
    "card-005": {
        "description": "Create REST endpoints for todos",
        "subtasks": ["Create routes", "Add controllers"]
    },
    "card-006": {
        "description": "Validate API requests",
        "subtasks": ["Add validation rules"]
    },
    "card-007": {
        "description": "Handle errors properly",
        "subtasks": ["Create error handler"]
    },
    "card-008": {
        "description": "Create React app",
        "subtasks": ["Initialize React", "Set up routing"]
    },
    "card-009": {
        "description": "Design the UI",
        "subtasks": ["Create mockups"]
    },
    "card-010": {
        "description": "Build list component",
        "subtasks": ["Create component"]
    },
    "card-011": {
        "description": "Build todo item component",
        "subtasks": ["Create component"]
    },
    "card-012": {
        "description": "Build add todo form",
        "subtasks": ["Create form"]
    },
    "card-013": {
        "description": "Create API service",
        "subtasks": ["Set up API calls"]
    },
    "card-014": {
        "description": "Connect frontend to backend",
        "subtasks": ["Integrate API"]
    },
    "card-015": {
        "description": "Add user login",
        "subtasks": ["Create auth", "Add JWT"]
    },
    "card-016": {
        "description": "Write tests",
        "subtasks": ["Unit tests", "Integration tests"]
    },
    "card-017": {
        "description": "Deploy to production",
        "subtasks": ["Set up hosting", "Deploy"]
    }
}

async def clear_board(session, list_id):
    """Clear all cards from the board"""
    try:
        # Get all cards in the list
        cards_result = await session.call_tool("planka_get_cards_by_list", {
            "listId": list_id
        })
        
        if isinstance(cards_result, str):
            cards_data = json.loads(cards_result)
        else:
            cards_data = cards_result
            
        cards = cards_data.get("included", {}).get("cards", [])
        
        # Delete each card
        for card in cards:
            await session.call_tool("planka_delete_card", {
                "cardId": card["id"]
            })
            
        print(f"  ✅ Cleared {len(cards)} existing cards")
        
    except Exception as e:
        print(f"  ⚠️  Error clearing board: {e}")

async def create_minimal_cards():
    """Create Todo App cards with minimal information"""
    print("🚀 Creating Todo App cards with minimal information...")
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("✅ Connected to kanban-mcp\n")
            
            # Find project
            print("📋 Finding Task Master Test project...")
            projects_result = await session.call_tool("planka_get_all_projects", {})
            
            if isinstance(projects_result, str):
                projects_data = json.loads(projects_result)
            else:
                projects_data = projects_result
                
            projects = projects_data.get("projects", [])
            project = next((p for p in projects if p["name"] == "Task Master Test"), None)
            
            if not project:
                print("❌ Project not found!")
                return
                
            project_id = project["id"]
            print(f"✅ Found project: {project['name']} (ID: {project_id})")
            
            # Get board
            boards_result = await session.call_tool("planka_get_boards_by_project", {
                "projectId": project_id
            })
            
            if isinstance(boards_result, str):
                boards_data = json.loads(boards_result)
            else:
                boards_data = boards_result
                
            boards = boards_data.get("boards", boards_data.get("included", {}).get("boards", []))
            if not boards:
                print("❌ No boards found!")
                return
                
            board = boards[0]
            board_id = board["id"]
            print(f"✅ Found board: {board['name']} (ID: {board_id})")
            
            # Clear existing cards
            print("\n🧹 Clearing existing cards...")
            lists_result = await session.call_tool("planka_get_lists_by_board", {
                "boardId": board_id
            })
            
            if isinstance(lists_result, str):
                lists_data = json.loads(lists_result)
            else:
                lists_data = lists_result
                
            lists = lists_data.get("lists", lists_data.get("included", {}).get("lists", []))
            backlog_list = next((l for l in lists if l["name"] == "Backlog"), None)
            
            if backlog_list:
                await clear_board(session, backlog_list["id"])
            
            # Create cards
            print("\n📝 Creating minimal cards...")
            cards_created = 0
            
            for card_key, card_data in TODO_APP_DATA["cards"].items():
                card_num = cards_created + 1
                print(f"\n[{card_num}/17] Creating: {card_data['title']}")
                
                # Get minimal info
                minimal_info = MINIMAL_CARDS.get(card_key, {})
                description = minimal_info.get("description", "")
                subtasks = minimal_info.get("subtasks", [])
                
                try:
                    # Create the card with just title and description
                    result = await session.call_tool("planka_create_card", {
                        "listId": backlog_list["id"],
                        "name": card_data["title"],
                        "description": description,
                        "position": card_data["position"]
                    })
                    
                    if isinstance(result, str):
                        result_data = json.loads(result)
                    else:
                        result_data = result
                        
                    card_id = result_data.get("card", {}).get("id") or result_data.get("id")
                    print(f"  ✅ Created card")
                    
                    # Add only High Priority label if specified
                    if "High Priority" in card_data.get("labels", []):
                        await session.call_tool("planka_add_label_to_card", {
                            "cardId": card_id,
                            "labelId": "High Priority"  # This will need to be fixed to use label ID
                        })
                        print(f"  ✅ Added High Priority label")
                    
                    # Add minimal subtasks
                    if subtasks:
                        for i, subtask in enumerate(subtasks):
                            await session.call_tool("planka_create_task", {
                                "cardId": card_id,
                                "name": subtask,
                                "position": i
                            })
                        print(f"  ✅ Added {len(subtasks)} subtasks")
                    
                    cards_created += 1
                    
                except Exception as e:
                    print(f"  ❌ Error: {e}")
            
            print(f"\n✅ Created {cards_created}/17 minimal cards!")
            print("\n✨ Minimal Todo App board ready!")

if __name__ == "__main__":
    asyncio.run(create_minimal_cards())