#!/usr/bin/env python3
"""
Test script to verify About task status handling.

This tests the complete flow from Task object creation through
build_task_data to the status mapping logic in planka_kanban.py.
"""

from datetime import datetime

from src.core.models import Priority, Task, TaskStatus
from src.integrations.nlp_task_utils import TaskBuilder

# Create an About task exactly as nlp_tools.py does
about_task = Task(
    id="about_project",
    name="About: Test Project",
    description="Test About card",
    status=TaskStatus.DONE,  # Mark as completed
    priority=Priority.LOW,
    assigned_to=None,
    created_at=datetime.now(),
    updated_at=datetime.now(),
    due_date=None,
    estimated_hours=0,
    dependencies=[],
    labels=["documentation"],
)

# Build task data as nlp_base.py does
task_builder = TaskBuilder()
task_data = task_builder.build_task_data(about_task)

print("=" * 60)
print("About Task Status Test")
print("=" * 60)

print("\n1. Original Task object:")
print(f"   status type: {type(about_task.status)}")
print(f"   status value: {about_task.status}")
print(f"   status.value: {about_task.status.value}")

print("\n2. After build_task_data():")
print(f"   'status' in task_data: {'status' in task_data}")
if "status" in task_data:
    status = task_data["status"]
    print(f"   status type: {type(status)}")
    print(f"   status value: {status}")

    # Simulate the logic in planka_kanban.py create_task()
    print("\n3. Simulating planka_kanban.py logic:")
    target_list_name = "backlog"  # Default

    if isinstance(status, TaskStatus):
        print("   ✓ Status is TaskStatus enum")
        status_to_list = {
            TaskStatus.TODO: "backlog",
            TaskStatus.IN_PROGRESS: "in progress",
            TaskStatus.DONE: "done",
            TaskStatus.BLOCKED: "blocked",
        }
        target_list_name = status_to_list.get(status, "backlog")
        print(f"   → target_list_name = '{target_list_name}'")
    elif isinstance(status, str):
        print("   ✓ Status is string")
        status_lower = status.lower()
        print(f"   → status_lower = '{status_lower}'")

        if status_lower in ["done", "completed"]:
            target_list_name = "done"
            print("   ✓ Matched 'done' or 'completed'")
        elif status_lower in ["in_progress", "in progress", "active"]:
            target_list_name = "in progress"
        elif status_lower in ["blocked", "on hold"]:
            target_list_name = "blocked"

        print(f"   → target_list_name = '{target_list_name}'")
    else:
        print(f"   ✗ Status is neither TaskStatus nor str (type: {type(status)})")
        print(f"   → target_list_name = '{target_list_name}' (default)")

    print("\n4. Expected result:")
    if target_list_name == "done":
        print("   ✓ SUCCESS: About task should be created in 'Done' list")
    else:
        print(f"   ✗ FAILURE: About task would be created in '{target_list_name}' list")
else:
    print("   ✗ ERROR: 'status' field missing from task_data!")

print("\n5. Full task_data dict:")
for key, value in task_data.items():
    print(f"   {key}: {value}")

print("\n" + "=" * 60)
