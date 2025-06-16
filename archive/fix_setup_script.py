#!/usr/bin/env python3
"""
Fixed version of setup_test_project.py that addresses the common issues.
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from src.integrations.mcp_kanban_client import MCPKanbanClient
from src.core.models import Priority


async def setup_test_project():
    """Set up the Task Master Test project with test data."""
    
    print("Setting up Task Master Test project...")
    
    # Set environment variables for kanban-mcp to connect to Planka
    os.environ["PLANKA_BASE_URL"] = "http://localhost:3333"
    os.environ["PLANKA_AGENT_EMAIL"] = "demo@demo.demo"
    os.environ["PLANKA_AGENT_PASSWORD"] = "demo"
    
    # Create client
    client = MCPKanbanClient()
    
    try:
        # Connect to MCP server
        print("Connecting to MCP kanban server...")
        await client.connect()
        
        # Find Task Master Test project - FIXED with pagination
        print("Getting projects...")
        projects_result = await client._call_tool("mcp_kanban_project_board_manager", {
            "action": "get_projects",
            "page": 1,
            "perPage": 25
        })
        
        # Handle both direct list and paginated response
        if isinstance(projects_result, dict) and "items" in projects_result:
            projects = projects_result["items"]
        else:
            projects = projects_result if isinstance(projects_result, list) else [projects_result]
        
        test_project = None
        for project in projects:
            if "Task Master Test" in project.get("name", ""):
                test_project = project
                break
        
        if not test_project:
            print("ERROR: Task Master Test project not found!")
            print("Available projects:")
            for project in projects:
                print(f"  - {project.get('name', 'Unknown')}")
            print("\nPlease create a project named 'Task Master Test' on your kanban board")
            return False
        
        client.project_id = test_project["id"]
        print(f"Found Task Master Test project (ID: {client.project_id})")
        
        # Get boards for this project - FIXED with pagination
        print("Getting boards...")
        boards_result = await client._call_tool("mcp_kanban_project_board_manager", {
            "action": "get_boards",
            "page": 1,
            "perPage": 25
        })
        
        # Handle both direct list and paginated response
        if isinstance(boards_result, dict) and "items" in boards_result:
            boards = boards_result["items"]
        else:
            boards = boards_result if isinstance(boards_result, list) else [boards_result]
        
        # Filter boards for our project
        project_boards = [b for b in boards if b.get("projectId") == client.project_id]
        
        if not project_boards:
            print("ERROR: No boards found for Task Master Test project!")
            return False
        
        client.board_id = project_boards[0]["id"]
        print(f"Found board (ID: {client.board_id})")
        
        # Check existing tasks - FIXED to use correct API
        print("Checking existing tasks...")
        existing_cards = await client._call_tool("mcp_kanban_card_manager", {
            "action": "get_all",
            "boardId": client.board_id
        })
        
        cards_list = existing_cards if isinstance(existing_cards, list) else [existing_cards] if existing_cards else []
        print(f"Found {len(cards_list)} existing cards")
        
        # Create test tasks if needed
        if len(cards_list) < 5:
            print("Creating test tasks...")
            
            test_tasks = [
                {
                    "name": "Implement user authentication",
                    "description": "Add OAuth2 login with Google and GitHub",
                    "priority": "high",
                    "labels": ["backend", "security", "oauth"],
                    "estimated_hours": 16
                },
                {
                    "name": "Create dashboard UI",
                    "description": "Design and implement analytics dashboard",
                    "priority": "medium",
                    "labels": ["frontend", "react", "ui/ux"],
                    "estimated_hours": 24
                },
                {
                    "name": "Fix payment processing bug",
                    "description": "Payments failing for international cards",
                    "priority": "urgent",
                    "labels": ["backend", "payments", "bug"],
                    "estimated_hours": 4
                },
                {
                    "name": "Add unit tests for API",
                    "description": "Increase test coverage to 80%",
                    "priority": "medium",
                    "labels": ["testing", "backend", "quality"],
                    "estimated_hours": 12
                },
                {
                    "name": "Optimize database queries",
                    "description": "Improve query performance for reports",
                    "priority": "low",
                    "labels": ["backend", "database", "performance"],
                    "estimated_hours": 8
                }
            ]
            
            # Get lists for the board
            lists_result = await client._call_tool("mcp_kanban_list_manager", {
                "action": "get_all",
                "boardId": client.board_id
            })
            
            lists = lists_result if isinstance(lists_result, list) else [lists_result] if lists_result else []
            todo_list = None
            for lst in lists:
                if lst.get("name", "").upper() in ["TODO", "TO DO", "BACKLOG"]:
                    todo_list = lst
                    break
            
            if not todo_list and lists:
                todo_list = lists[0]  # Use first list if no TODO found
            
            if todo_list:
                for task_data in test_tasks:
                    try:
                        # Create card using correct API
                        card = await client._call_tool("mcp_kanban_card_manager", {
                            "action": "create",
                            "listId": todo_list["id"],
                            "name": task_data["name"],
                            "description": task_data["description"]
                        })
                        print(f"  Created: {task_data['name']}")
                    except Exception as e:
                        print(f"  Failed to create {task_data['name']}: {e}")
            else:
                print("ERROR: No lists found on board to create tasks")
        
        print("\n✅ Task Master Test project is ready for testing!")
        print(f"   Total cards: {len(cards_list)}")
        print("   Run tests with: pytest tests/integration/test_real_kanban_integration.py -v -s")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to set up test project: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Disconnect from MCP server
        if client:
            try:
                await client.disconnect()
            except:
                pass


if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("WARNING: ANTHROPIC_API_KEY not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key'")
    
    # Run setup
    success = asyncio.run(setup_test_project())
    sys.exit(0 if success else 1)
