"""
Task Decomposition System Demo.

This script demonstrates the hierarchical task decomposition workflow.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator import (
    SubtaskManager,
    SubtaskMetadata,
    decompose_task,
    should_decompose,
)


async def demo_task_decomposition() -> None:
    """Demonstrate task decomposition workflow."""
    print("=" * 60)
    print("Task Decomposition System Demo")
    print("=" * 60)

    # 1. Create a large task
    print("\n1. Creating a large task...")
    task = Task(
        id="task-001",
        name="Build task management API",
        description=(
            "Create a REST API for task management with authentication, "
            "CRUD operations, and real-time updates via WebSocket"
        ),
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=10.0,
        labels=["backend", "api", "websocket"],
    )
    print(f"   Task: {task.name}")
    print(f"   Estimated hours: {task.estimated_hours}")
    print(f"   Labels: {', '.join(task.labels)}")

    # 2. Check if should decompose
    print("\n2. Checking if task should be decomposed...")
    if should_decompose(task):
        print("   ✓ Task meets decomposition criteria")
        print("     - Large task (>4 hours)")
        print("     - Multiple components detected")
    else:
        print("   ✗ Task should not be decomposed")
        return

    # 3. Mock AI engine for decomposition
    print("\n3. Decomposing task with AI...")
    mock_ai_engine = Mock()
    mock_ai_engine.generate_structured_response = AsyncMock(
        return_value={
            "subtasks": [
                {
                    "name": "Create Task model",
                    "description": (
                        "Define Task model in src/models/task.py "
                        "with fields: id, title, status, priority"
                    ),
                    "estimated_hours": 2.0,
                    "dependencies": [],
                    "file_artifacts": ["src/models/task.py"],
                    "provides": "Task model with validation",
                    "requires": "None",
                },
                {
                    "name": "Build authentication middleware",
                    "description": (
                        "Create JWT authentication middleware "
                        "in src/middleware/auth.py"
                    ),
                    "estimated_hours": 2.5,
                    "dependencies": [],
                    "file_artifacts": ["src/middleware/auth.py"],
                    "provides": "JWT authentication middleware",
                    "requires": "None",
                },
                {
                    "name": "Implement CRUD endpoints",
                    "description": (
                        "Create REST endpoints: " "POST/GET/PUT/DELETE /api/tasks"
                    ),
                    "estimated_hours": 3.0,
                    "dependencies": [0, 1],
                    "file_artifacts": [
                        "src/api/tasks/create.py",
                        "src/api/tasks/read.py",
                        "src/api/tasks/update.py",
                        "src/api/tasks/delete.py",
                    ],
                    "provides": "Full CRUD API for tasks",
                    "requires": "Task model, Auth middleware",
                },
                {
                    "name": "Add WebSocket support",
                    "description": (
                        "Implement real-time task updates "
                        "via WebSocket in src/websocket/tasks.py"
                    ),
                    "estimated_hours": 2.0,
                    "dependencies": [0, 2],
                    "file_artifacts": ["src/websocket/tasks.py"],
                    "provides": "Real-time task updates",
                    "requires": "Task model, CRUD endpoints",
                },
            ],
            "shared_conventions": {
                "base_path": "src/api/",
                "file_structure": "src/{component}/{feature}.py",
                "response_format": {
                    "success": {"status": "success", "data": "..."},
                    "error": {"status": "error", "message": "..."},
                },
                "naming_conventions": {
                    "files": "snake_case",
                    "classes": "PascalCase",
                    "functions": "snake_case",
                },
            },
        }
    )

    decomposition = await decompose_task(task, mock_ai_engine)

    if decomposition["success"]:
        print(f"   ✓ Task decomposed into {len(decomposition['subtasks'])} subtasks")
        print("\n   Subtasks created:")
        for i, subtask in enumerate(decomposition["subtasks"], 1):
            deps = (
                f" (depends on: {', '.join(subtask['dependencies'])})"
                if subtask.get("dependencies")
                else ""
            )
            print(f"     {i}. {subtask['name']}{deps}")
            print(f"        Estimated: {subtask['estimated_hours']}h")
            print(f"        Files: {', '.join(subtask['file_artifacts'])}")

        # Note the automatic integration subtask
        last_subtask = decomposition["subtasks"][-1]
        if "Integrate" in last_subtask["name"]:
            print("\n   ✓ Automatic integration subtask added!")
            print(f"     '{last_subtask['name']}'")
    else:
        print(f"   ✗ Decomposition failed: {decomposition.get('error')}")
        return

    # 4. Store subtasks in manager
    print("\n4. Storing subtasks...")
    manager = SubtaskManager()
    metadata = SubtaskMetadata(
        shared_conventions=decomposition["shared_conventions"],
        decomposed_by="ai",
    )
    subtasks = manager.add_subtasks(task.id, decomposition["subtasks"], metadata)
    print(f"   ✓ {len(subtasks)} subtasks stored in manager")

    # 5. Simulate subtask assignment workflow
    print("\n5. Simulating subtask assignment workflow...")
    completed_subtasks: set[str] = set()

    for i in range(len(subtasks)):
        # Get next available subtask
        next_subtask = manager.get_next_available_subtask(task.id, completed_subtasks)

        if next_subtask:
            print("\n   Agent requests task...")
            print(f"   → Assigned: {next_subtask.name}")
            print(f"     ID: {next_subtask.id}")
            print(f"     Files: {', '.join(next_subtask.file_artifacts)}")
            if next_subtask.requires:
                print(f"     Requires: {next_subtask.requires}")

            # Simulate work
            manager.update_subtask_status(
                next_subtask.id, TaskStatus.IN_PROGRESS, f"agent-{i+1}"
            )
            print("   ⚙️  Agent working...")

            # Complete subtask
            manager.update_subtask_status(
                next_subtask.id, TaskStatus.DONE, f"agent-{i+1}"
            )
            completed_subtasks.add(next_subtask.id)
            print("   ✓ Subtask completed!")

            # Show progress
            progress = manager.get_completion_percentage(task.id)
            print(f"   📊 Overall progress: {progress:.0f}%")

    # 6. Check parent completion
    print("\n6. Checking parent task completion...")
    if manager.is_parent_complete(task.id):
        print("   ✓ All subtasks complete!")
        print("   → Parent task can be auto-completed")
        print("\n   Final status:")
        print(f"     Total subtasks: {len(subtasks)}")
        print(f"     Completed: {len(completed_subtasks)}")
        print("     Progress: 100%")
    else:
        incomplete = len(subtasks) - len(completed_subtasks)
        print(f"   ⏳ {incomplete} subtasks still in progress")

    # 7. Show context for a subtask
    print("\n7. Example subtask context (for Agent)...")
    context = manager.get_subtask_context(subtasks[2].id)
    print(f"   Subtask: {context['subtask']['name']}")
    print(f"   Parent: {context['parent_task_id']}")
    print("   Shared conventions:")
    for key, value in context["shared_conventions"].items():
        print(f"     - {key}: {value}")
    if context["dependency_artifacts"]:
        print("   Dependencies completed:")
        for dep_id, dep_info in context["dependency_artifacts"].items():
            print(f"     - {dep_info['name']}: {dep_info['status']}")

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_task_decomposition())
