#!/usr/bin/env python3
"""
Test creating a project through the MCP server tools
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp.server import MarcusServer


async def test_create_project():
    """Test creating a project through MCP server"""

    # Create Marcus server instance
    server = MarcusServer()

    # Initialize kanban
    await server.initialize_kanban()

    # Tool arguments
    project_description = """
    Create a Simple Todo API with the following features:
    - CRUD operations for todos (Create, Read, Update, Delete)
    - Each todo should have: title, description, completed status, timestamps
    - User authentication using JWT tokens
    - Input validation and sanitization
    - Performance: Handle 100 requests per second
    - Security: JWT authentication for all endpoints
    """

    arguments = {
        "description": project_description,
        "project_name": "Simple Todo API Test",
        "options": {"team_size": 3},
    }

    print("Creating project through MCP...")

    # Import the handler
    from src.marcus_mcp.handlers import handle_tool_call

    try:
        # Call the tool
        result = await handle_tool_call("create_project", arguments, server)

        # Extract the text content
        if result and hasattr(result[0], "text"):
            import json

            response = json.loads(result[0].text)

            if response.get("success"):
                print(f"\n✅ Project created successfully!")
                print(f"Tasks generated: {response.get('task_count', 0)}")

                if "tasks" in response:
                    print("\nGenerated tasks:")
                    for i, task in enumerate(response["tasks"], 1):
                        print(
                            f"{i}. [{task.get('id', 'No ID')}] {task.get('name', 'Unnamed task')}"
                        )

                # Check the board
                print("\n\nChecking Kanban board...")

                # Get all tasks from the board
                all_tasks = await server.kanban_client.get_all_tasks()

                print(f"\n✅ Total tasks on board: {len(all_tasks)}")

                # Group tasks by status
                by_status = {}
                for task in all_tasks:
                    status = getattr(task, "status", "UNKNOWN")
                    if hasattr(status, "value"):
                        status = status.value
                    by_status.setdefault(str(status), []).append(task)

                for status, tasks in by_status.items():
                    print(f"\n{status}: {len(tasks)} tasks")
                    for task in tasks[:3]:
                        task_name = (
                            task.name
                            if hasattr(task, "name")
                            else task.get("name", "Unnamed")
                        )
                        print(f"  - {task_name}")
                    if len(tasks) > 3:
                        print(f"  ... and {len(tasks) - 3} more")

            else:
                print(
                    f"\n❌ Project creation failed: {response.get('error', 'Unknown error')}"
                )

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Clean up
        if hasattr(server.kanban_client, "close"):
            await server.kanban_client.close()


if __name__ == "__main__":
    asyncio.run(test_create_project())
