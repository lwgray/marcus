#!/usr/bin/env python3
"""
Setup script to prepare the "Task Master Test" project for testing.

This script initializes the test environment by connecting to the MCP kanban server,
creating test tasks, and ensuring proper test data exists for integration testing.

Notes
-----
This script should be run before running integration tests to ensure the test
environment is properly configured with realistic test data.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.models import Priority
from src.integrations.mcp_kanban_client import MCPKanbanClient


async def setup_test_project() -> bool:
    """
    Set up the Task Master Test project with test data.

    This function connects to the MCP kanban server, finds or creates the test project,
    and populates it with sample tasks in various states for testing purposes.

    Returns
    -------
    bool
        True if setup completed successfully, False otherwise.

    Notes
    -----
    Requires a running Planka instance and MCP kanban server.
    Environment variables can be set via .env file or directly.

    Examples
    --------
    >>> success = asyncio.run(setup_test_project())
    >>> if success:
    ...     print("Test environment ready")
    """
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

        # Find Task Master Test project
        boards = await client._call_tool(
            "mcp_kanban_project_board_manager", {"action": "get_boards"}
        )

        test_board = None
        for board in boards:
            if "Task Master Test" in board.get("name", ""):
                test_board = board
                break

        if not test_board:
            print("ERROR: Task Master Test project not found!")
            print(
                "Please create a project named 'Task Master Test' on your kanban board"
            )
            return False

        client.board_id = test_board["id"]
        print(f"Found Task Master Test project (ID: {client.board_id})")

        # Check existing tasks
        existing_tasks = await client.get_available_tasks()
        print(f"Found {len(existing_tasks)} existing tasks")

        # Create test tasks if needed
        if len(existing_tasks) < 5:
            print("Creating test tasks...")

            test_tasks = [
                {
                    "name": "Implement user authentication",
                    "description": "Add OAuth2 login with Google and GitHub",
                    "priority": "high",
                    "labels": ["backend", "security", "oauth"],
                    "estimated_hours": 16,
                },
                {
                    "name": "Create dashboard UI",
                    "description": "Design and implement analytics dashboard",
                    "priority": "medium",
                    "labels": ["frontend", "react", "ui/ux"],
                    "estimated_hours": 24,
                },
                {
                    "name": "Fix payment processing bug",
                    "description": "Payments failing for international cards",
                    "priority": "urgent",
                    "labels": ["backend", "payments", "bug"],
                    "estimated_hours": 4,
                },
                {
                    "name": "Add unit tests for API",
                    "description": "Increase test coverage to 80%",
                    "priority": "medium",
                    "labels": ["testing", "backend", "quality"],
                    "estimated_hours": 12,
                },
                {
                    "name": "Optimize database queries",
                    "description": "Improve query performance for reports",
                    "priority": "low",
                    "labels": ["backend", "database", "performance"],
                    "estimated_hours": 8,
                },
            ]

            for task_data in test_tasks:
                task = await client.create_task(task_data)
                print(f"  Created: {task.name}")

        # Create some tasks in different states
        all_tasks = await client._call_tool(
            "mcp_kanban_card_manager", {"action": "get_all", "boardId": client.board_id}
        )

        if len(all_tasks) > 3:
            # Move one task to IN PROGRESS
            await client.update_task_status(all_tasks[0]["id"], "in_progress")
            print(f"Moved '{all_tasks[0]['title']}' to IN PROGRESS")

            # Move one task to BLOCKED
            if len(all_tasks) > 4:
                await client.update_task_status(all_tasks[1]["id"], "blocked")
                await client.add_comment(
                    all_tasks[1]["id"], "🚧 Blocked: Waiting for API documentation"
                )
                print(f"Moved '{all_tasks[1]['title']}' to BLOCKED")

        print("\n✅ Task Master Test project is ready for testing!")
        print(f"   Total tasks: {len(all_tasks)}")
        print(
            "   Run tests with: pytest tests/integration/test_real_kanban_integration.py -v -s"
        )

        return True

    except Exception as e:
        print(f"ERROR: Failed to set up test project: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # Disconnect from MCP server
        if client:
            await client.disconnect()


if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("WARNING: ANTHROPIC_API_KEY not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key'")

    # Run setup
    success = asyncio.run(setup_test_project())
    sys.exit(0 if success else 1)
