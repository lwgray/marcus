#!/usr/bin/env python3
"""
Create Todo App cards with minimal information - simplified version
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

async def create_minimal_cards():
    """Create Todo App cards with minimal information"""
    print("🚀 Creating Todo App cards with minimal information...")
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected to kanban-mcp\n")
            
            # Get all projects
            print("📋 Finding Task Master Test project...")
            result = await session.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_projects",
                "page": 1,
                "perPage": 25
            })
            
            projects_data = json.loads(result.content[0].text)
            project = None
            
            for p in projects_data["items"]:
                if p["name"] == "Task Master Test":
                    project = p
                    break
            
            if not project:
                print("❌ Project not found!")
                return
                
            project_id = project["id"]
            print(f"✅ Found project: {project['name']} (ID: {project_id})")
            
            # Find the board in the included data
            board_id = None
            if "boards" in projects_data.get("included", {}):
                for board in projects_data["included"]["boards"]:
                    if board["projectId"] == project_id:
                        board_id = board["id"]
                        print(f"✅ Found board: {board['name']} (ID: {board_id})")
                        break
            
            if not board_id:
                print("❌ No board found for Task Master Test!")
                return
            
            # Get lists
            print("\n📋 Getting lists...")
            result = await session.call_tool("mcp_kanban_list_manager", {
                "action": "get_all",
                "boardId": board_id
            })
            
            lists = json.loads(result.content[0].text)
            backlog_list = next((l for l in lists if l["name"] == "Backlog"), None)
            
            if not backlog_list:
                print("❌ Backlog list not found!")
                return
                
            print(f"✅ Found list: {backlog_list['name']} (ID: {backlog_list['id']})")
            
            # Clear existing cards
            print("\n🧹 Clearing existing cards...")
            result = await session.call_tool("mcp_kanban_card_manager", {
                "action": "get_all",
                "listId": backlog_list["id"]
            })
            
            cards = []
            if result.content and result.content[0].text:
                try:
                    cards = json.loads(result.content[0].text)
                    if not isinstance(cards, list):
                        cards = []
                except:
                    cards = []
            for card in cards:
                await session.call_tool("mcp_kanban_card_manager", {
                    "action": "delete",
                    "cardId": card["id"]
                })
            print(f"  ✅ Cleared {len(cards)} existing cards")
            
            # Get labels for High Priority
            print("\n🏷️  Getting labels...")
            result = await session.call_tool("mcp_kanban_label_manager", {
                "action": "get_all",
                "boardId": board_id
            })
            
            labels = json.loads(result.content[0].text)
            high_priority_label_id = None
            for label in labels:
                if label["name"] == "High Priority":
                    high_priority_label_id = label["id"]
                    break
            
            # Create cards
            print("\n📝 Creating minimal cards...")
            cards_created = 0
            
            for i, card_data in enumerate(TODO_APP_DATA["cards"]):
                card_num = cards_created + 1
                card_key = card_data["id"]  # Use the card id as key
                print(f"\n[{card_num}/17] Creating: {card_data['title']}")
                
                # Get minimal info
                minimal_info = MINIMAL_CARDS.get(card_key, {})
                description = minimal_info.get("description", "")
                subtasks = minimal_info.get("subtasks", [])
                
                try:
                    # Create the card with just title and description
                    result = await session.call_tool("mcp_kanban_card_manager", {
                        "action": "create",
                        "listId": backlog_list["id"],
                        "name": card_data["title"],
                        "description": description
                    })
                    
                    card = json.loads(result.content[0].text)
                    card_id = card["id"]
                    print(f"  ✅ Created card")
                    
                    # Add only High Priority label if specified
                    if high_priority_label_id and "High Priority" in card_data.get("labels", []):
                        await session.call_tool("mcp_kanban_label_manager", {
                            "action": "add_to_card",
                            "cardId": card_id,
                            "labelId": high_priority_label_id
                        })
                        print(f"  ✅ Added High Priority label")
                    
                    # Add minimal subtasks
                    if subtasks:
                        for i, subtask in enumerate(subtasks):
                            await session.call_tool("mcp_kanban_task_manager", {
                                "action": "create",
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