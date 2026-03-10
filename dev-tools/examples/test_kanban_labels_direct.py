#!/usr/bin/env python3
"""
Direct test of KanbanClient label filtering.

This script directly tests the KanbanClient to verify label filtering
works correctly WITHOUT running a full project or using MCP.

This is the FASTEST way to test the fix (< 5 seconds).
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.integrations.kanban_client_with_create import (  # noqa: E402
    KanbanClientWithCreate,
)


async def main() -> None:
    """Test label filtering directly using KanbanClient."""
    print("\n" + "=" * 70)
    print("🧪 DIRECT KANBAN LABEL FILTERING TEST")
    print("=" * 70)
    print("\nThis test:")
    print("1. Creates a KanbanClient instance")
    print("2. Fetches tasks from the current project")
    print("3. Checks that labels are correctly filtered\n")

    try:
        # Create KanbanClient (uses environment variables for config)
        print("📡 Creating KanbanClient...")
        client = KanbanClientWithCreate()

        if not client.board_id:
            print("❌ ERROR: No board_id configured!")
            print("   Set PLANKA_BOARD_ID environment variable")
            return

        print(f"✅ Connected to board: {client.board_id}")
        print(f"   Project: {client.project_id}")

        # Get all tasks
        print("\n📋 Fetching all tasks from board...")
        tasks = await client.get_all_tasks()

        if not tasks:
            print("⚠️  No tasks found on board")
            print("   Make sure a project is loaded with tasks")
            return

        print(f"✅ Found {len(tasks)} tasks")

        # Analyze labels
        print("\n" + "=" * 70)
        print("🔍 LABEL ANALYSIS")
        print("=" * 70)

        for i, task in enumerate(tasks, 1):
            print(f"\n{i}. Task: {task.name}")
            print(f"   ID: {task.id}")
            print(f"   Labels: {task.labels}")
            print(f"   Label count: {len(task.labels)}")

            # Check for issues
            if len(task.labels) == 0:
                print("   ⚠️  WARNING: Task has NO labels")
            elif len(task.labels) > 10:
                print(
                    f"   ❌ ERROR: Task has {len(task.labels)} labels "
                    "(ALL board labels - filtering NOT working!)"
                )
                print("   Expected: Only 1-3 assigned labels per task")
            else:
                print(f"   ✅ OK: Task has {len(task.labels)} labels")

        # Summary
        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)

        empty_label_tasks = [t for t in tasks if not t.labels]
        many_label_tasks = [t for t in tasks if len(t.labels) > 10]
        normal_tasks = [t for t in tasks if 0 < len(t.labels) <= 10]

        print(f"Total tasks: {len(tasks)}")
        print(f"Tasks with NO labels: {len(empty_label_tasks)}")
        print(f"Tasks with >10 labels (ALL board labels): " f"{len(many_label_tasks)}")
        print(f"Tasks with normal labels (1-10): {len(normal_tasks)}")

        # Verdict
        print("\n" + "=" * 70)
        if empty_label_tasks:
            print("⚠️  ISSUE DETECTED: Tasks have empty labels")
            print("   Problem: labelIds not being read from card_details")
            print("   Solution: Check that card_details.get('labelIds') is used")
        elif many_label_tasks:
            print("❌ ISSUE DETECTED: Tasks have ALL board labels")
            print("   Problem: Label filtering not working")
            print("   Solution: Verify filtering logic in get_all_tasks()")
        else:
            print("✅ SUCCESS: Label filtering is working correctly!")
            print("   All tasks have 1-10 labels (properly filtered)")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure PLANKA_BOARD_ID is set in environment")
        print("   2. Make sure PLANKA_PROJECT_ID is set in environment")
        print("   3. Make sure Planka MCP server is running")
        print("   4. Make sure a project with tasks exists")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
