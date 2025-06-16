#!/usr/bin/env python3
"""
Reset the board by cleaning all tasks and repopulating with fresh todo app tasks
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
    
    # Get all lists
    lists_result = await session.call_tool(
        "mcp_kanban_list_manager",
        {"action": "get_all", "boardId": BOARD_ID}
    )
    lists = json.loads(lists_result.content[0].text)
    
    # Get all cards across all lists
    total_cards = 0
    for lst in lists:
        cards_result = await session.call_tool(
            "mcp_kanban_card_manager",
            {"action": "get_all", "listId": lst['id']}
        )
        cards = json.loads(cards_result.content[0].text)
        
        # Delete each card
        for card in cards:
            await session.call_tool(
                "mcp_kanban_card_manager",
                {"action": "delete", "id": card['id']}
            )
            total_cards += 1
            print(f"  ❌ Deleted: {card['name']}")
    
    print(f"\n✅ Cleaned {total_cards} cards from the board")
    
    # Also delete all lists
    for lst in lists:
        await session.call_tool(
            "mcp_kanban_list_manager",
            {"action": "delete", "id": lst['id']}
        )
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
    
    # Define todo app features with realistic tasks
    todo_features = [
        {
            "name": "Setup Project Infrastructure",
            "description": "Initialize the project with modern tooling and structure",
            "list": "Done",
            "labels": ["Frontend", "Backend"],
            "tasks": [
                "Create Next.js 14 project with App Router",
                "Setup TypeScript configuration",
                "Install and configure Tailwind CSS",
                "Setup ESLint and Prettier",
                "Configure Git hooks with Husky",
                "Setup folder structure (components, hooks, utils, etc.)"
            ]
        },
        {
            "name": "Design Database Schema",
            "description": "Design and implement the database schema for todos",
            "list": "In Progress",
            "labels": ["Backend", "Database"],
            "tasks": [
                "Design Todo model (id, title, description, status, priority, due_date)",
                "Design User model with authentication fields",
                "Design Category/Tag model for todo organization",
                "Setup Prisma ORM with PostgreSQL",
                "Create database migrations",
                "Add seed data for development"
            ]
        },
        {
            "name": "Implement User Authentication",
            "description": "Add secure user authentication and authorization",
            "list": "In Progress",
            "labels": ["Backend", "Feature", "High Priority"],
            "tasks": [
                "Install and configure NextAuth.js",
                "Setup OAuth providers (Google, GitHub)",
                "Implement email/password authentication",
                "Create login and signup pages",
                "Add JWT token handling",
                "Implement password reset flow",
                "Add session management",
                "Create protected route middleware"
            ]
        },
        {
            "name": "Build Todo CRUD API",
            "description": "Create RESTful API endpoints for todo operations",
            "list": "Backlog",
            "labels": ["Backend", "Feature"],
            "tasks": [
                "Create POST /api/todos endpoint",
                "Create GET /api/todos with pagination",
                "Create GET /api/todos/:id endpoint",
                "Create PUT /api/todos/:id endpoint", 
                "Create DELETE /api/todos/:id endpoint",
                "Add filtering by status, priority, and tags",
                "Implement search functionality",
                "Add API rate limiting"
            ]
        },
        {
            "name": "Create Todo UI Components",
            "description": "Build reusable React components for the todo interface",
            "list": "Backlog",
            "labels": ["Frontend", "Feature"],
            "tasks": [
                "Create TodoList component with virtualization",
                "Create TodoItem component with actions",
                "Create AddTodo form with validation",
                "Create EditTodo modal component",
                "Build FilterBar component",
                "Create TodoSearch component",
                "Add drag-and-drop for todo reordering",
                "Implement keyboard shortcuts"
            ]
        },
        {
            "name": "Implement Real-time Updates",
            "description": "Add real-time synchronization across clients",
            "list": "Backlog",
            "labels": ["Backend", "Frontend", "Feature"],
            "tasks": [
                "Setup WebSocket server with Socket.io",
                "Implement real-time todo updates",
                "Add optimistic UI updates",
                "Handle connection state and reconnection",
                "Add presence indicators",
                "Implement collaborative editing locks"
            ]
        },
        {
            "name": "Add State Management",
            "description": "Implement global state management for the app",
            "list": "Backlog", 
            "labels": ["Frontend"],
            "tasks": [
                "Setup Zustand for state management",
                "Create todo store with actions",
                "Implement filter and sort state",
                "Add undo/redo functionality",
                "Setup state persistence",
                "Add state debugging tools"
            ]
        },
        {
            "name": "Write Comprehensive Tests",
            "description": "Add unit, integration, and e2e tests",
            "list": "Backlog",
            "labels": ["Testing"],
            "tasks": [
                "Setup Jest and React Testing Library",
                "Write unit tests for API endpoints",
                "Write component unit tests",
                "Setup Cypress for E2E testing",
                "Write E2E test scenarios",
                "Add API integration tests",
                "Setup CI/CD test pipeline",
                "Achieve 80% code coverage"
            ]
        },
        {
            "name": "Fix Mobile Responsive Issues",
            "description": "Ensure the app works perfectly on all devices",
            "list": "Review",
            "labels": ["Frontend", "Bug", "High Priority"],
            "tasks": [
                "Fix layout issues on small screens",
                "Optimize touch interactions",
                "Fix modal positioning on mobile",
                "Add swipe gestures for todo actions",
                "Test on various devices",
                "Fix iOS Safari specific issues"
            ]
        },
        {
            "name": "Implement Advanced Features",
            "description": "Add power user features",
            "list": "Backlog",
            "labels": ["Feature"],
            "tasks": [
                "Add recurring todos",
                "Implement todo templates",
                "Add bulk operations",
                "Create todo analytics dashboard",
                "Add todo export (CSV, JSON)",
                "Implement todo sharing",
                "Add email notifications",
                "Create mobile app with React Native"
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
        print(f"\n  📌 Created card: {feature['name']}")
        print(f"     List: {feature['list']}")
        
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
        print(f"     🏷️  Added {len(feature['labels'])} labels")
        
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
        
        # Add initial comment
        priority = "High" if "High Priority" in feature["labels"] else "Normal"
        comment = f"Priority: {priority}\nEstimated effort: {len(feature['tasks'])} tasks\nCreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        await session.call_tool(
            "mcp_kanban_comment_manager",
            {
                "action": "create",
                "cardId": card["id"],
                "text": comment
            }
        )
    
    # 4. Get final summary
    print("\n📊 Board Summary")
    print("=" * 60)
    
    summary_result = await session.call_tool(
        "mcp_kanban_project_board_manager",
        {
            "action": "get_board_summary",
            "boardId": BOARD_ID,
            "includeTaskDetails": False
        }
    )
    
    summary = json.loads(summary_result.content[0].text)
    
    print(f"\nBoard: Todo App Development")
    print(f"Total Lists: {len(created_lists)}")
    print(f"Total Cards: {len(created_cards)}")
    
    total_tasks = sum(len(f["tasks"]) for f in todo_features)
    print(f"Total Tasks: {total_tasks}")
    
    print("\nCards by List:")
    for list_name, list_data in created_lists.items():
        cards_in_list = [f for f in todo_features if f["list"] == list_name]
        tasks_in_list = sum(len(f["tasks"]) for f in cards_in_list)
        print(f"  - {list_name}: {len(cards_in_list)} cards, {tasks_in_list} tasks")
    
    print("\n✅ Todo App board created successfully!")
    print(f"\nView your board at: http://localhost:3333")
    
    return True


async def reset_board():
    """Main function to reset the board"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🔄 Todo Board Reset Tool")
    print("=" * 60)
    print(f"Project ID: {PROJECT_ID}")
    print(f"Board ID: {BOARD_ID}")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("\n✅ Connected to kanban-mcp")
            
            # Ask for confirmation
            print("\n⚠️  WARNING: This will delete ALL cards and lists on the board!")
            confirm = input("Are you sure you want to continue? (yes/no): ").strip().lower()
            
            if confirm != 'yes':
                print("\n❌ Operation cancelled")
                return
            
            # Clean the board
            await clean_board(session)
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Create new board
            await create_todo_app_board(session)
            
            print("\n🎉 Board reset complete!")


if __name__ == "__main__":
    asyncio.run(reset_board())