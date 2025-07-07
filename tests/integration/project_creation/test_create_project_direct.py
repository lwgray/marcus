#!/usr/bin/env python3
"""
Test creating a project directly using the integration
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config_loader import get_config
from src.core.models import ProjectState
from src.integrations.kanban_factory import KanbanFactory
from src.integrations.nlp_tools import create_project_from_natural_language


async def test_create_todo_project():
    """Create a simple todo project to test task generation"""

    # Load config
    config = get_config()

    # Create Kanban client
    kanban_client = await KanbanFactory.create_client(
        provider=config.get("kanban.provider", "planka"), config=config
    )

    # Create a minimal state object
    class MinimalState:
        def __init__(self, kanban_client):
            self.kanban_client = kanban_client
            self.project_tasks = []
            self.project_state = None

        def log_event(self, event_type, data):
            print(f"Event: {event_type} - {data}")

    state = MinimalState(kanban_client)

    project_description = """
    Create a Simple Todo API with the following features:
    - CRUD operations for todos (Create, Read, Update, Delete)
    - Each todo should have: title, description, completed status, timestamps
    - User authentication using JWT tokens
    - Input validation and sanitization
    - Performance: Handle 100 requests per second
    - Security: JWT authentication for all endpoints
    """

    print("Creating project with fixed PRD parser...")

    try:
        result = await create_project_from_natural_language(
            description=project_description,
            project_name="Simple Todo API Test",
            state=state,
            options={"team_size": 3},
        )

        print(f"\nProject created successfully!")
        print(f"Tasks generated: {result.get('task_count', 0)}")

        if "tasks" in result:
            print("\nGenerated tasks:")
            for i, task in enumerate(result["tasks"], 1):
                print(
                    f"{i}. [{task.get('id', 'No ID')}] {task.get('name', 'Unnamed task')}"
                )

        # Check the board
        print("\n\nChecking Kanban board...")
        boards = await kanban_client.get_boards()

        # Find our board
        todo_board = None
        for board in boards:
            if "Simple Todo API Test" in board.get("name", ""):
                todo_board = board
                break

        if todo_board:
            print(f"\nFound board: {todo_board['name']}")

            # Get lists
            lists = await kanban_client.get_lists(todo_board["id"])

            # Get tasks for each list
            for list_item in lists:
                tasks = await kanban_client.get_tasks(list_item["id"])
                if tasks:
                    print(f"\n{list_item['name']}:")
                    for task in tasks:
                        print(f"  - {task['name']}")
        else:
            print("\nBoard not found on Kanban!")

        return result

    except Exception as e:
        print(f"Error creating project: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if kanban_client:
            await kanban_client.close()


if __name__ == "__main__":
    asyncio.run(test_create_todo_project())
