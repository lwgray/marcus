#!/usr/bin/env python3
"""
Quick Start Script for PM Agent
Creates a simple Hello World API project with tasks
"""

import os
import sys
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations.kanban_factory import KanbanFactory
from src.config.settings import Settings


async def create_hello_world_project():
    """Create a simple Hello World API project with tasks."""
    print("🚀 PM Agent Quick Start - Creating Hello World API Project")
    print("=" * 60)
    
    try:
        # Initialize settings and kanban client
        settings = Settings()
        kanban = KanbanFactory.create(
            provider=settings.KANBAN_PROVIDER,
            config=settings.get_provider_config()
        )
        
        print(f"📋 Using {settings.KANBAN_PROVIDER} as task board provider")
        
        # Get or create the project/board
        print("🔍 Finding or creating project board...")
        
        if settings.KANBAN_PROVIDER == "github":
            # For GitHub, we'll use the main repo project
            project_name = f"{settings.GITHUB_OWNER}/{settings.GITHUB_REPO}"
        else:
            project_name = "Hello World API"
        
        boards = await kanban.get_boards()
        board = None
        
        for b in boards:
            if b["name"] == project_name:
                board = b
                break
        
        if not board:
            print(f"📝 Creating new board: {project_name}")
            board = await kanban.create_board(project_name)
        else:
            print(f"✅ Using existing board: {project_name}")
        
        board_id = board["id"]
        
        # Define the tasks for a Hello World API
        tasks = [
            {
                "name": "Set up Node.js project structure",
                "description": "Initialize a new Node.js project with package.json, create src directory structure, and set up basic configuration files (.gitignore, .env.example)",
                "labels": ["setup", "backend"],
                "priority": "high"
            },
            {
                "name": "Create Express.js server",
                "description": "Set up Express.js server with basic middleware (cors, body-parser, helmet). Server should listen on port 3000 with environment variable support.",
                "labels": ["backend", "api"],
                "priority": "high"
            },
            {
                "name": "Implement GET /hello endpoint",
                "description": "Create a GET endpoint at /hello that returns JSON response: {\"message\": \"Hello, World!\", \"timestamp\": \"<current-time>\"}",
                "labels": ["backend", "api", "endpoint"],
                "priority": "medium"
            },
            {
                "name": "Add error handling middleware",
                "description": "Implement global error handling middleware that catches all errors and returns proper HTTP status codes with error messages in JSON format",
                "labels": ["backend", "error-handling"],
                "priority": "medium"
            },
            {
                "name": "Create README documentation",
                "description": "Write comprehensive README.md with: project description, installation instructions, API documentation, example usage with curl commands",
                "labels": ["documentation"],
                "priority": "low"
            },
            {
                "name": "Add basic tests",
                "description": "Set up Jest testing framework and write tests for the /hello endpoint. Include test for successful response and error cases.",
                "labels": ["testing", "backend"],
                "priority": "low"
            }
        ]
        
        # Get the lists/columns
        lists = await kanban.get_lists(board_id)
        
        # Find the "To Do" list (or equivalent)
        todo_list = None
        for lst in lists:
            if lst["name"].lower() in ["to do", "todo", "backlog", "open"]:
                todo_list = lst
                break
        
        if not todo_list and lists:
            todo_list = lists[0]  # Use first list if no "To Do" found
        
        if not todo_list:
            print("❌ No lists found in board. Creating default lists...")
            # This would need to be implemented based on provider
            raise Exception("No lists available in board")
        
        # Create the tasks
        print(f"\n📝 Creating {len(tasks)} tasks in {todo_list['name']} list...")
        created_count = 0
        
        for i, task_data in enumerate(tasks, 1):
            try:
                print(f"  [{i}/{len(tasks)}] Creating: {task_data['name']}")
                
                # Prepare card data
                card_data = {
                    "name": task_data["name"],
                    "description": task_data["description"]
                }
                
                # Add labels if supported
                if hasattr(kanban, 'create_label'):
                    for label in task_data.get("labels", []):
                        try:
                            await kanban.create_label(board_id, label, "#0066cc")
                        except:
                            pass  # Label might already exist
                
                # Create the card
                await kanban.create_card(
                    board_id=board_id,
                    list_id=todo_list["id"],
                    **card_data
                )
                
                created_count += 1
                
            except Exception as e:
                print(f"    ⚠️  Failed: {str(e)}")
        
        print(f"\n✅ Successfully created {created_count}/{len(tasks)} tasks!")
        print(f"\n🎯 Next steps:")
        print(f"  1. Start PM Agent if not already running: ./start.sh")
        print(f"  2. Watch AI workers pick up and complete tasks: docker-compose logs -f pm-agent")
        print(f"  3. Check your {settings.KANBAN_PROVIDER} board to see progress")
        print(f"  4. Find generated code in: output/hello-world-api/")
        
        return board_id
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\n💡 Troubleshooting tips:")
        print("  1. Check your .env file has valid API keys")
        print("  2. Ensure your task board provider is accessible")
        print("  3. Run: docker-compose logs pm-agent")
        raise


def main():
    """Main entry point."""
    try:
        board_id = asyncio.run(create_hello_world_project())
        print(f"\n🚀 Project created successfully!")
    except KeyboardInterrupt:
        print("\n\n👋 Quick start cancelled.")
    except Exception as e:
        print(f"\n❌ Quick start failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()