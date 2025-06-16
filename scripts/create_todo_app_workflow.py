#!/usr/bin/env python3
"""
Create a complete Todo App workflow on the board
"""

import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set environment variables
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

# Configuration
PROJECT_ID = "1533678301472621705"
BOARD_ID = "1533859887128249584"


async def create_todo_app_workflow():
    """Create a complete todo app workflow"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🚀 Creating Todo App Workflow")
    print("=" * 60)
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("✅ Connected to kanban-mcp")
            
            # 1. Create Lists
            print("\n📋 Creating Lists...")
            lists = [
                {"name": "Backlog", "position": 1},
                {"name": "In Progress", "position": 2},
                {"name": "Testing", "position": 3},
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
                print(f"  ✅ Created list: {list_data['name']} (ID: {created_list['id']})")
            
            # 2. Create Labels
            print("\n🏷️  Creating Labels...")
            labels = [
                {"name": "Feature", "color": "lagoon-blue"},
                {"name": "Bug", "color": "berry-red"},
                {"name": "Enhancement", "color": "pumpkin-orange"},
                {"name": "Documentation", "color": "sunny-grass"},
                {"name": "Testing", "color": "pink-tulip"}
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
                print(f"  ✅ Created label: {label_data['name']} ({label_data['color']})")
            
            # 3. Create Cards with Tasks
            print("\n📝 Creating Cards with Tasks...")
            
            # Define todo app features
            todo_features = [
                {
                    "name": "Setup Project Structure",
                    "description": "Initialize a new React/Next.js project with TypeScript",
                    "list": "Done",
                    "labels": ["Feature"],
                    "tasks": [
                        "Create Next.js project with TypeScript",
                        "Setup ESLint and Prettier",
                        "Configure Tailwind CSS",
                        "Setup project folder structure"
                    ]
                },
                {
                    "name": "Design Database Schema",
                    "description": "Design and implement database schema for todos",
                    "list": "In Progress",
                    "labels": ["Feature"],
                    "tasks": [
                        "Define Todo model (id, title, description, status, createdAt, updatedAt)",
                        "Define User model",
                        "Setup Prisma or TypeORM",
                        "Create migration files"
                    ]
                },
                {
                    "name": "Implement Authentication",
                    "description": "Add user authentication using NextAuth.js",
                    "list": "Backlog",
                    "labels": ["Feature"],
                    "tasks": [
                        "Install and configure NextAuth.js",
                        "Create login/signup pages",
                        "Implement JWT token handling",
                        "Add protected routes"
                    ]
                },
                {
                    "name": "Create Todo CRUD API",
                    "description": "Build REST API endpoints for todo operations",
                    "list": "Backlog",
                    "labels": ["Feature"],
                    "tasks": [
                        "Create POST /api/todos endpoint",
                        "Create GET /api/todos endpoint",
                        "Create PUT /api/todos/:id endpoint",
                        "Create DELETE /api/todos/:id endpoint",
                        "Add pagination support"
                    ]
                },
                {
                    "name": "Build Todo UI Components",
                    "description": "Create React components for todo functionality",
                    "list": "Backlog",
                    "labels": ["Feature"],
                    "tasks": [
                        "Create TodoList component",
                        "Create TodoItem component",
                        "Create AddTodo form component",
                        "Create EditTodo modal",
                        "Add drag-and-drop support"
                    ]
                },
                {
                    "name": "Add State Management",
                    "description": "Implement state management with Zustand or Redux Toolkit",
                    "list": "Backlog",
                    "labels": ["Enhancement"],
                    "tasks": [
                        "Choose state management library",
                        "Create todo store/slice",
                        "Implement actions and reducers",
                        "Connect components to store"
                    ]
                },
                {
                    "name": "Write Unit Tests",
                    "description": "Add comprehensive test coverage",
                    "list": "Testing",
                    "labels": ["Testing"],
                    "tasks": [
                        "Setup Jest and React Testing Library",
                        "Write API endpoint tests",
                        "Write component tests",
                        "Add integration tests",
                        "Setup CI/CD pipeline"
                    ]
                },
                {
                    "name": "Create Documentation",
                    "description": "Write comprehensive documentation",
                    "list": "Backlog",
                    "labels": ["Documentation"],
                    "tasks": [
                        "Write README.md",
                        "Create API documentation",
                        "Add code comments",
                        "Create user guide"
                    ]
                },
                {
                    "name": "Fix Mobile Responsiveness",
                    "description": "Todo list doesn't display properly on mobile devices",
                    "list": "In Progress",
                    "labels": ["Bug"],
                    "tasks": [
                        "Identify breakpoint issues",
                        "Fix layout on small screens",
                        "Test on various devices",
                        "Update CSS media queries"
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
                print(f"\n  📋 Created card: {feature['name']}")
                print(f"     List: {feature['list']}")
                print(f"     ID: {card['id']}")
                
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
                        print(f"     🏷️  Added label: {label_name}")
                
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
                
                # Add a comment
                comment = f"This card was created as part of the Todo App development workflow. Priority: {'High' if idx < 3 else 'Medium'}"
                await session.call_tool(
                    "mcp_kanban_comment_manager",
                    {
                        "action": "create",
                        "cardId": card["id"],
                        "text": comment
                    }
                )
                print(f"     💬 Added comment")
            
            # 4. Get final board summary
            print("\n📊 Final Board Summary")
            print("=" * 60)
            
            summary_result = await session.call_tool(
                "mcp_kanban_project_board_manager",
                {
                    "action": "get_board_summary",
                    "boardId": BOARD_ID,
                    "includeTaskDetails": True
                }
            )
            
            summary = json.loads(summary_result.content[0].text)
            
            print(f"\nBoard: {summary['board']['name']}")
            print(f"Total Lists: {len(summary['lists'])}")
            print(f"Total Cards: {len(created_cards)}")
            
            total_tasks = sum(len(f["tasks"]) for f in todo_features)
            print(f"Total Tasks: {total_tasks}")
            
            print("\nCards by List:")
            for list_name, list_data in created_lists.items():
                cards_in_list = [f for f in todo_features if f["list"] == list_name]
                print(f"  - {list_name}: {len(cards_in_list)} cards")
            
            print("\n✅ Todo App workflow created successfully!")
            print(f"\nView your board at: http://localhost:3333")
            
            return {
                "board_id": BOARD_ID,
                "lists": created_lists,
                "cards": created_cards,
                "labels": created_labels
            }


if __name__ == "__main__":
    asyncio.run(create_todo_app_workflow())