#!/usr/bin/env python3
"""
Test script to verify board lock fix.

This script:
1. Creates a simple API project (1 or 2 endpoints)
2. Registers a test agent
3. Loops through all tasks:
   - request_next_task
   - immediately report as completed
4. Monitors for stalls/board lock

Usage:
    python examples/test_board_lock_fix.py --endpoints 1
    python examples/test_board_lock_fix.py --endpoints 2
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.worker.inspector import Inspector  # noqa: E402


def pretty_print(label: str, data: Any) -> None:
    """Pretty print JSON data."""
    print(f"\n{label}")
    try:
        if isinstance(data, str):
            data = json.loads(data)
        print(json.dumps(data, indent=2))
    except (json.JSONDecodeError, TypeError):
        print(data)


async def create_test_project(
    client: Inspector, session: Any, num_endpoints: int
) -> Dict[str, Any]:
    """Create a simple API test project."""
    print(f"\n{'='*70}")
    print(f"📦 CREATING TEST PROJECT ({num_endpoints} endpoint(s))")
    print("=" * 70)

    if num_endpoints == 1:
        description = """
        Create a simple REST API with 1 endpoint:

        GET /api/health - Returns API health status
        """
        project_name = "Test API - Single Endpoint"
    elif num_endpoints == 2:
        description = """
        Create a simple REST API with 2 endpoints:

        GET /api/health - Returns API health status
        GET /api/version - Returns API version info
        """
        project_name = "Test API - Two Endpoints"
    else:
        raise ValueError("Only 1 or 2 endpoints supported")

    print(f"\n📝 Creating project: {project_name}")
    result = await session.call_tool(
        "create_project",
        arguments={
            "description": description,
            "project_name": project_name,
            "options": {
                "mode": "new_project",
                "complexity": "prototype",
            },
        },
    )

    # Extract result
    project_data: Dict[str, Any]
    if hasattr(result, "content") and result.content:
        text = result.content[0].text if result.content else str(result)
        project_data = json.loads(text)
    else:
        project_data = dict(result) if result else {}

    print(f"✅ Project created: {project_data.get('project_id')}")
    print(f"   Tasks created: {project_data.get('tasks_created', 0)}")

    return project_data


async def test_task_completion_loop(
    client: Inspector, agent_id: str, max_iterations: int = 50
) -> Dict[str, Any]:
    """
    Test task completion loop.

    Request tasks and immediately mark them as completed,
    monitoring for stalls or board lock.
    """
    print(f"\n{'='*70}")
    print("🔄 TESTING TASK COMPLETION LOOP")
    print("=" * 70)

    completed_count = 0
    no_task_count = 0
    iteration = 0
    task_ids_completed = []

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")

        # Request next task
        print(f"📋 Requesting task for {agent_id}...")
        task_result = await client.request_next_task(agent_id)

        # Parse result
        if hasattr(task_result, "content") and task_result.content:
            text = (
                task_result.content[0].text if task_result.content else str(task_result)
            )
            task_data = json.loads(text)
        else:
            task_data = task_result

        # Check if task was assigned
        if not task_data.get("success"):
            no_task_count += 1
            reason = task_data.get("retry_reason", "unknown")
            print(f"⏸️  No task available (reason: {reason})")

            if no_task_count >= 3:
                print("\n🏁 No tasks available for 3 consecutive iterations - done!")
                break

            # Wait a bit before retrying
            await asyncio.sleep(1)
            continue

        # Task assigned!
        task_id = task_data.get("task_id") or task_data.get("task", {}).get("id")
        task_title = task_data.get("task", {}).get("name", "Unknown")
        print(f"✅ Task assigned: {task_id}")
        print(f"   Title: {task_title}")

        no_task_count = 0  # Reset counter

        # Immediately report as completed
        print(f"📊 Marking task {task_id} as completed...")
        progress_result = await client.report_task_progress(
            agent_id=agent_id,
            task_id=task_id,
            status="completed",
            progress=100,
            message="Test completion",
        )

        # Parse progress result
        if hasattr(progress_result, "content") and progress_result.content:
            text = (
                progress_result.content[0].text
                if progress_result.content
                else str(progress_result)
            )
            progress_data = json.loads(text)
        else:
            progress_data = progress_result

        if progress_data.get("success"):
            completed_count += 1
            task_ids_completed.append(task_id)
            print(f"✅ Task completed! (Total: {completed_count})")
        else:
            print(f"❌ Failed to complete task: {progress_data.get('error')}")

        # Brief pause before next iteration
        await asyncio.sleep(0.5)

    print(f"\n{'='*70}")
    print("📊 TEST RESULTS")
    print("=" * 70)
    print(f"Total iterations: {iteration}")
    print(f"Tasks completed: {completed_count}")
    print(f"Tasks IDs completed: {task_ids_completed}")

    return {
        "iterations": iteration,
        "completed": completed_count,
        "task_ids": task_ids_completed,
    }


async def main(num_endpoints: int = 1) -> None:
    """Run the board lock test."""
    print("\n🚀 Board Lock Fix Test")
    print("=" * 70)
    print(f"Testing with {num_endpoints} endpoint(s)")
    print("\nThis test will:")
    print("  1. Create a new API project")
    print("  2. Register a test agent")
    print("  3. Loop: request task → complete immediately")
    print("  4. Monitor for stalls or board lock")
    print("=" * 70)

    # Use stdio mode for more reliable testing
    client = Inspector(connection_type="stdio")
    agent_id = f"test-agent-{num_endpoints}ep"

    try:
        # Connect via stdio (spawns isolated Marcus instance)
        print("\n📡 Starting isolated Marcus instance for testing...")
        async with client.connect() as session:
            # Authenticate as admin
            print("🔐 Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": agent_id,
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"test_mode": True, "test_type": "board_lock_fix"},
                },
            )
            print("✅ Authenticated")

            # Create test project
            project_data = await create_test_project(client, session, num_endpoints)

            # Register agent
            print(f"\n{'='*70}")
            print("🤖 REGISTERING TEST AGENT")
            print("=" * 70)
            print(f"\n🔧 Registering agent: {agent_id}")
            await client.register_agent(
                agent_id=agent_id,
                name=f"Test Agent ({num_endpoints}EP)",
                role="Developer",
                skills=["python", "fastapi", "testing"],
            )
            print("✅ Agent registered")

            # Run task completion loop
            test_results = await test_task_completion_loop(client, agent_id)

            # Final status
            print(f"\n{'='*70}")
            print("✅ TEST COMPLETE")
            print("=" * 70)
            print("\n📊 Summary:")
            print(f"   Project: {project_data.get('project_name')}")
            print(f"   Expected tasks: {project_data.get('tasks_created', 0)}")
            print(f"   Completed tasks: {test_results['completed']}")
            print(f"   Iterations: {test_results['iterations']}")

            if test_results["completed"] == project_data.get("tasks_created", 0):
                print("\n✅ SUCCESS: All tasks completed!")
                print("   No board lock detected!")
            else:
                print(
                    f"\n⚠️  WARNING: Only {test_results['completed']} of "
                    f"{project_data.get('tasks_created', 0)} tasks completed"
                )
                print("   Possible board lock or stall detected!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure Marcus server is running in HTTP mode")
        print("   2. Start server with: python -m src.marcus_mcp.server --http")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test board lock fix")
    parser.add_argument(
        "--endpoints",
        type=int,
        default=1,
        choices=[1, 2],
        help="Number of endpoints in test project (1 or 2)",
    )
    args = parser.parse_args()

    asyncio.run(main(num_endpoints=args.endpoints))
