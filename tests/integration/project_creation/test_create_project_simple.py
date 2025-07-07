#!/usr/bin/env python3
"""
Simple test to create a project and verify it appears on the board
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config_loader import get_config
from src.integrations.kanban_factory import KanbanFactory
from src.integrations.nlp_tools import create_project_from_natural_language


async def main():
    """Create a project and check if tasks appear on the board"""

    # Load config
    config = get_config()

    # Create kanban client
    kanban_client = KanbanFactory.create(config.get("kanban.provider", "planka"))

    # Create a minimal state that has the kanban_client
    class MinimalState:
        def __init__(self):
            self.kanban_client = kanban_client
            self.project_tasks = []
            self.project_state = None

        def log_event(self, event_type, data):
            print(f"Event: {event_type} - {data}")

    state = MinimalState()

    project_description = """
    Create a Simple Todo API with the following features:
    - CRUD operations for todos
    - User authentication using JWT
    - Input validation
    - Performance: Handle 100 requests per second
    """

    print("Creating project...")

    try:
        # Create project
        result = await create_project_from_natural_language(
            description=project_description,
            project_name="Simple Todo API Demo",
            state=state,
            options={"team_size": 3},
        )

        print(f"\n✅ Project created!")
        print(f"Tasks generated: {result.get('task_count', 0)}")

        if "tasks" in result:
            print("\nGenerated tasks:")
            for i, task in enumerate(result["tasks"], 1):
                print(f"{i}. {task.get('name', 'Unnamed')} [{task.get('id', '')}]")

        # Now check the board
        print("\n\nChecking Kanban board...")

        # Get all boards
        boards = await kanban_client.get_boards()

        # Find our board
        todo_board = None
        for board in boards:
            if "Simple Todo API Demo" in board.get("name", ""):
                todo_board = board
                break

        if todo_board:
            print(f"\n✅ Found board: {todo_board['name']}")
            print(f"Board ID: {todo_board['id']}")

            # Get lists on the board
            lists = await kanban_client.get_lists(todo_board["id"])
            print(f"\nLists on board: {len(lists)}")

            total_tasks = 0
            for lst in lists:
                tasks = await kanban_client.get_tasks(lst["id"])
                if tasks:
                    print(f"\n{lst['name']}: {len(tasks)} tasks")
                    for task in tasks[:3]:  # Show first 3 tasks
                        print(f"  - {task['name']}")
                    if len(tasks) > 3:
                        print(f"  ... and {len(tasks) - 3} more")
                    total_tasks += len(tasks)

            print(f"\n✅ Total tasks on board: {total_tasks}")
        else:
            print("\n❌ Board not found on Kanban!")
            print("Available boards:")
            for board in boards[:5]:
                print(f"  - {board.get('name', 'Unnamed')}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Close the client
        if hasattr(kanban_client, "close"):
            await kanban_client.close()


if __name__ == "__main__":
    asyncio.run(main())
