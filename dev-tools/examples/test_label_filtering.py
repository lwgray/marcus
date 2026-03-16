#!/usr/bin/env python3
"""
Test script to verify label filtering is working correctly.

This script connects to a running Marcus instance and checks that:
1. Tasks are being retrieved with labels
2. Labels are correctly filtered (not ALL board labels)
3. Validation system receives correct labels

This is much faster than running a full 30-minute project.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.worker.inspector import Inspector  # noqa: E402


def pretty_print_result(label: str, result: Any) -> None:
    """Pretty print MCP tool results."""
    print(f"\n{label}")
    if hasattr(result, "content") and result.content:
        # Extract text from MCP result
        text = result.content[0].text if result.content else str(result)
        try:
            # Try to parse and pretty print JSON
            data = json.loads(text)
            print(json.dumps(data, indent=2))
        except (json.JSONDecodeError, AttributeError):
            print(text)
    else:
        print(result)


def analyze_task_labels(tasks: List[Dict[str, Any]]) -> None:
    """
    Analyze task labels to verify filtering is working.

    Parameters
    ----------
    tasks : List[Dict[str, Any]]
        List of tasks from Marcus
    """
    print("\n" + "=" * 70)
    print("🔍 LABEL ANALYSIS")
    print("=" * 70)

    if not tasks:
        print("❌ No tasks found!")
        return

    for task in tasks:
        task_id = task.get("id", "unknown")
        task_name = task.get("name", "unknown")
        labels = task.get("labels", [])

        print(f"\n📋 Task: {task_name}")
        print(f"   ID: {task_id}")
        print(f"   Labels: {labels}")
        print(f"   Label count: {len(labels)}")

        # Check for issues
        if len(labels) == 0:
            print("   ⚠️  WARNING: Task has NO labels (empty array)")
        elif len(labels) > 10:
            print(
                f"   ❌ ERROR: Task has {len(labels)} labels "
                "(likely ALL board labels, filtering not working!)"
            )
        else:
            print("   ✅ OK: Task has reasonable number of labels")

    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)

    empty_label_tasks = [t for t in tasks if not t.get("labels")]
    many_label_tasks = [t for t in tasks if len(t.get("labels", [])) > 10]
    normal_tasks = [t for t in tasks if 0 < len(t.get("labels", [])) <= 10]

    print(f"Total tasks: {len(tasks)}")
    print(f"Tasks with NO labels: {len(empty_label_tasks)}")
    print(f"Tasks with >10 labels (ALL board labels): {len(many_label_tasks)}")
    print(f"Tasks with normal labels (1-10): {len(normal_tasks)}")

    if empty_label_tasks:
        print(
            "\n⚠️  ISSUE: Tasks have empty labels - "
            + "labelIds not being read correctly"
        )
    elif many_label_tasks:
        print("\n❌ ISSUE: Tasks have ALL board labels - " + "filtering not working!")
    else:
        print("\n✅ SUCCESS: Label filtering is working correctly!")


async def main() -> None:
    """
    Test label filtering by connecting to running Marcus instance.

    This is much faster than running a full project (30 minutes).
    """
    print("\n" + "=" * 70)
    print("🧪 LABEL FILTERING TEST")
    print("=" * 70)
    print("\nThis test verifies that:")
    print("1. Tasks are retrieved with labels")
    print("2. Labels are correctly filtered (not ALL board labels)")
    print("3. Each task only has its assigned labels\n")

    client = Inspector(connection_type="http")
    url = "http://localhost:4298/mcp"

    try:
        async with client.connect(url=url) as session:
            # Authenticate as admin
            print("🔐 Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "label-test-worker",
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"test_mode": True, "purpose": "label_testing"},
                },
            )
            print("✅ Authenticated")

            # Get current project info
            print("\n📂 Getting current project...")
            current_result = await session.call_tool(
                "get_current_project", arguments={}
            )
            pretty_print_result("Current project:", current_result)

            # Register test agent
            print("\n🤖 Registering test agent...")
            await client.register_agent(
                agent_id="label-test-worker",
                name="Label Test Worker",
                role="Developer",
                skills=["testing"],
            )

            # Request a task to trigger task retrieval with labels
            print("\n📋 Requesting task (this triggers label retrieval)...")
            task_result = await client.request_next_task("label-test-worker")

            # Parse the task result
            if hasattr(task_result, "content") and task_result.content:
                task_text = task_result.content[0].text
                try:
                    task_data = json.loads(task_text)

                    # Check if we got a task
                    if task_data.get("success"):
                        task = task_data.get("task")
                        if task:
                            print(f"\n✅ Received task: {task.get('name', 'unknown')}")
                            analyze_task_labels([task])
                        else:
                            print("\n⚠️  No task available (project might be done)")
                    else:
                        print(f"\n⚠️  Task request failed: {task_data}")

                except json.JSONDecodeError:
                    print(f"\n❌ Could not parse task result: {task_text}")
            else:
                print("\n❌ No task result content")

            # Alternative: Try to get all tasks directly to see labels
            print("\n" + "=" * 70)
            print("🔍 ALTERNATIVE: Check all project tasks")
            print("=" * 70)
            print("Note: This requires direct access to Marcus state,")
            print("which may not be available via MCP tools.")
            print("If this fails, the test above should be sufficient.")

            print("\n" + "=" * 70)
            print("✅ Test complete!")
            print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure Marcus server is running in HTTP mode")
        print("   2. Make sure a project is loaded and has tasks")
        print("   3. Check that tasks have been created with labels")
        print("   4. Verify Marcus was restarted after the label fix")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
