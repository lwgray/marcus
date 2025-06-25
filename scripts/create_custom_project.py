#!/usr/bin/env python3
"""
Create Custom Project Script for PM Agent
Allows users to create their own project with custom tasks
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations.kanban_factory import KanbanFactory
from src.config.settings import Settings


async def create_custom_project(name: str, description: str, tasks: list = None):
    """Create a custom project with specified tasks."""
    print(f"🚀 Creating Custom Project: {name}")
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
        
        boards = await kanban.get_boards()
        board = None
        
        for b in boards:
            if b["name"] == name:
                board = b
                break
        
        if not board:
            print(f"📝 Creating new board: {name}")
            board = await kanban.create_board(name)
        else:
            print(f"✅ Using existing board: {name}")
        
        board_id = board["id"]
        
        # If no tasks provided, create default structure based on description
        if not tasks:
            tasks = generate_tasks_from_description(description)
        
        # Get the lists/columns
        lists = await kanban.get_lists(board_id)
        
        # Find the "To Do" list
        todo_list = None
        for lst in lists:
            if lst["name"].lower() in ["to do", "todo", "backlog", "open"]:
                todo_list = lst
                break
        
        if not todo_list and lists:
            todo_list = lists[0]
        
        if not todo_list:
            raise Exception("No lists available in board")
        
        # Create the tasks
        print(f"\n📝 Creating {len(tasks)} tasks...")
        created_count = 0
        
        for i, task_data in enumerate(tasks, 1):
            try:
                print(f"  [{i}/{len(tasks)}] Creating: {task_data['name']}")
                
                await kanban.create_card(
                    board_id=board_id,
                    list_id=todo_list["id"],
                    name=task_data["name"],
                    description=task_data.get("description", "")
                )
                
                created_count += 1
                
            except Exception as e:
                print(f"    ⚠️  Failed: {str(e)}")
        
        print(f"\n✅ Successfully created {created_count}/{len(tasks)} tasks!")
        print(f"\n🎯 Project '{name}' is ready!")
        print(f"   Board ID: {board_id}")
        print(f"   Provider: {settings.KANBAN_PROVIDER}")
        
        return board_id
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise


def generate_tasks_from_description(description: str) -> list:
    """Generate default tasks based on project description."""
    # Simple keyword-based task generation
    tasks = []
    
    # Always start with setup
    tasks.append({
        "name": "Set up project structure",
        "description": f"Initialize the project structure for: {description}"
    })
    
    # Check for common project types
    desc_lower = description.lower()
    
    if "api" in desc_lower or "backend" in desc_lower:
        tasks.extend([
            {
                "name": "Design API endpoints",
                "description": "Define all API endpoints, request/response formats, and authentication requirements"
            },
            {
                "name": "Implement data models",
                "description": "Create database schemas and model classes"
            },
            {
                "name": "Build API routes",
                "description": "Implement all API endpoint handlers with proper error handling"
            },
            {
                "name": "Add API tests",
                "description": "Write comprehensive tests for all API endpoints"
            }
        ])
    
    if "frontend" in desc_lower or "ui" in desc_lower or "dashboard" in desc_lower:
        tasks.extend([
            {
                "name": "Create UI mockups",
                "description": "Design the user interface layout and components"
            },
            {
                "name": "Set up frontend framework",
                "description": "Initialize React/Vue/Angular project with routing"
            },
            {
                "name": "Implement UI components",
                "description": "Build all UI components with responsive design"
            },
            {
                "name": "Connect to backend",
                "description": "Integrate frontend with API endpoints"
            }
        ])
    
    if "database" in desc_lower or "data" in desc_lower:
        tasks.extend([
            {
                "name": "Design database schema",
                "description": "Create entity relationship diagrams and define all tables"
            },
            {
                "name": "Set up database",
                "description": "Initialize database with migrations and seed data"
            }
        ])
    
    if "auth" in desc_lower or "user" in desc_lower:
        tasks.extend([
            {
                "name": "Implement authentication",
                "description": "Add user registration, login, and JWT token management"
            },
            {
                "name": "Add authorization",
                "description": "Implement role-based access control"
            }
        ])
    
    # Always end with documentation and deployment
    tasks.extend([
        {
            "name": "Write documentation",
            "description": "Create README, API docs, and user guides"
        },
        {
            "name": "Prepare for deployment",
            "description": "Set up Docker, CI/CD, and deployment configuration"
        }
    ])
    
    return tasks


def parse_task_string(task_str: str) -> dict:
    """Parse a task string into name and description."""
    # Format: "Task Name: Task description"
    if ":" in task_str:
        name, desc = task_str.split(":", 1)
        return {"name": name.strip(), "description": desc.strip()}
    else:
        return {"name": task_str.strip(), "description": ""}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create a custom project with tasks in PM Agent"
    )
    parser.add_argument(
        "--name", "-n",
        required=True,
        help="Project name"
    )
    parser.add_argument(
        "--description", "-d",
        required=True,
        help="Project description (helps generate appropriate tasks)"
    )
    parser.add_argument(
        "--tasks", "-t",
        nargs="+",
        help="Custom tasks (format: 'Task Name: Description')"
    )
    parser.add_argument(
        "--from-file", "-f",
        help="Read tasks from a file (one per line)"
    )
    
    args = parser.parse_args()
    
    # Collect tasks
    tasks = []
    
    if args.from_file:
        try:
            with open(args.from_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        tasks.append(parse_task_string(line))
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            sys.exit(1)
    
    elif args.tasks:
        for task_str in args.tasks:
            tasks.append(parse_task_string(task_str))
    
    # Create the project
    try:
        board_id = asyncio.run(create_custom_project(
            name=args.name,
            description=args.description,
            tasks=tasks if tasks else None
        ))
        print(f"\n🎉 Project created successfully!")
    except KeyboardInterrupt:
        print("\n\n👋 Project creation cancelled.")
    except Exception as e:
        print(f"\n❌ Project creation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()