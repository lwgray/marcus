#!/usr/bin/env python3
"""
Example: Agent selecting and working on existing project.

This demonstrates the select_project workflow for autonomous agents:
1. List available projects
2. Select a project to work on (without creating new tasks)
3. Request tasks from that project
4. Work on assigned tasks

This is the recommended workflow for agents that want to work on
existing project backlogs rather than creating new work.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.worker.new_client import Inspector  # noqa: E402


def pretty_print(label: str, result: Any) -> None:
    """Pretty print MCP tool results."""
    print(f"\n{label}")
    if hasattr(result, "content") and result.content:
        text = result.content[0].text if result.content else str(result)
        try:
            data = json.loads(text)
            print(json.dumps(data, indent=2))
        except (json.JSONDecodeError, AttributeError):
            print(text)
    else:
        print(result)


async def agent_workflow() -> None:
    """
    Demonstrate agent selecting existing project workflow.

    Steps:
    1. Connect and authenticate as admin
    2. List available projects
    3. Select a project using mode='select_project'
    4. Request tasks from the selected project
    5. Work on tasks
    """
    print("\n" + "=" * 60)
    print("AGENT WORKFLOW: Select Existing Project")
    print("=" * 60)

    client = Inspector(connection_type="stdio")

    try:
        async with client.connect() as session:
            # Step 1: Authenticate as admin for full access
            print("\n🔐 Step 1: Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "agent-1",
                    "client_type": "admin",
                    "role": "admin",
                },
            )
            print("✅ Authenticated")

            # Step 2: List available projects
            print("\n📂 Step 2: Listing available projects...")
            projects_result = await session.call_tool("list_projects", arguments={})
            pretty_print("Available projects:", projects_result)

            # Parse the result to get project names
            projects_text = projects_result.content[0].text
            projects_data = json.loads(projects_text)

            if not projects_data:
                print("\n⚠️  No projects found. Create one first:")
                print("    python examples/worker_client_demo.py")
                return

            # Step 3: Select a project using mode='select_project'
            print("\n🎯 Step 3: Selecting project to work on...")

            # Option A: Select by exact project name (if you know it)
            first_project_name = projects_data[0]["name"]
            print(f"   Selecting project: '{first_project_name}'")

            select_result = await session.call_tool(
                "create_project",
                arguments={
                    "description": "",  # Not required for select_project mode
                    "project_name": first_project_name,
                    "options": {"mode": "select_project"},
                },
            )
            pretty_print("✅ Project selected:", select_result)

            # Verify we selected correctly
            select_data = json.loads(select_result.content[0].text)
            if not select_data.get("success"):
                print(f"\n❌ Failed to select project: {select_data.get('error')}")
                return

            print(f"\n✅ Now working on: {select_data['project']['name']}")
            print(f"   Available tasks: {select_data['project']['task_count']}")

            # Step 4: Register as agent
            print("\n🤖 Step 4: Registering as agent...")
            await client.register_agent(
                agent_id="agent-1",
                name="Backend Agent",
                role="Developer",
                skills=["python", "api", "testing"],
            )
            print("✅ Agent registered")

            # Step 5: Request task from the selected project
            print("\n📋 Step 5: Requesting task from selected project...")
            task = await client.request_next_task("agent-1")
            pretty_print("Task assigned:", task)

            # Step 6: Work on the task
            print("\n🔧 Step 6: Working on task...")
            print("   (Agent would implement the task here)")

            # Example: Report progress
            if hasattr(task, "content") and task.content:
                task_text = task.content[0].text
                task_data = json.loads(task_text)
                if task_data.get("task"):
                    task_id = task_data["task"].get("task_id")
                else:
                    task_id = None
            else:
                task_id = None

            if task_id:
                print(f"\n📊 Reporting progress on task {task_id}...")
                await client.report_task_progress(
                    agent_id="agent-1",
                    task_id=task_id,
                    status="in_progress",
                    progress=50,
                    message="Implementing feature...",
                )
                print("✅ Progress reported")

            print("\n" + "=" * 60)
            print("✅ Agent workflow complete!")
            print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


async def select_project_by_id_example() -> None:
    """
    Select project using explicit project ID.

    Use this when you know the exact project ID you want to work on.
    This is the most reliable method for agents.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE: Select Project by ID")
    print("=" * 60)

    client = Inspector(connection_type="stdio")

    try:
        async with client.connect() as session:
            # Authenticate
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "agent-2",
                    "client_type": "admin",
                    "role": "admin",
                },
            )

            # Get list of projects to find an ID
            projects_result = await session.call_tool("list_projects", arguments={})
            projects_text = projects_result.content[0].text
            projects_data = json.loads(projects_text)

            if projects_data:
                # Select first project by ID (most reliable)
                project_id = projects_data[0]["id"]
                print(f"\n🎯 Selecting project by ID: {project_id}")

                select_result = await session.call_tool(
                    "create_project",
                    arguments={
                        "description": "",
                        "project_name": "",  # Can be empty when using project_id
                        "options": {"mode": "select_project", "project_id": project_id},
                    },
                )
                pretty_print("✅ Project selected by ID:", select_result)
            else:
                print("\n⚠️  No projects available")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def main() -> None:
    """Run the agent workflow examples."""
    print("\n🤖 Agent Project Selection Examples")
    print("=" * 60)
    print("\nThese examples show how autonomous agents can:")
    print("1. Discover existing projects")
    print("2. Select a project to work on (without creating new tasks)")
    print("3. Request and complete tasks from that project")
    print("\n" + "=" * 60)

    # Run the main workflow
    await agent_workflow()

    # Run the ID-based selection example
    print("\n\n")
    await select_project_by_id_example()


if __name__ == "__main__":
    asyncio.run(main())
