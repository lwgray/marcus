#!/usr/bin/env python3
"""
Example: Autonomous agent workflow with project creation and completion tracking.

This demonstrates a complete autonomous agent lifecycle:
1. Create a new project (simple todo app)
2. Register as a general-purpose agent
3. Continuously request and "complete" tasks
4. Report progress for each task
5. Generate final report when no tasks remain

This simulates task completion without actually implementing the work.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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


class TaskTracker:
    """Track completed and remaining tasks for final report."""

    def __init__(self) -> None:
        self.completed_tasks: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None

    def add_completed_task(self, task_id: str, title: str, order: int) -> None:
        """Record a completed task."""
        self.completed_tasks.append(
            {
                "order": order,
                "task_id": task_id,
                "title": title,
                "completed_at": datetime.now().isoformat(),
            }
        )

    def finalize(self, remaining_count: int) -> None:
        """Mark the workflow as complete."""
        self.end_time = datetime.now()

    def generate_report(self, remaining_count: int) -> str:
        """Generate a final report of the agent's work."""
        if self.end_time is None:
            raise ValueError("Cannot generate report before workflow is finalized")
        duration = (self.end_time - self.start_time).total_seconds()

        report = "\n" + "=" * 70 + "\n"
        report += "📊 AUTONOMOUS AGENT WORKFLOW REPORT\n"
        report += "=" * 70 + "\n\n"

        report += f"⏱️  Duration: {duration:.2f} seconds\n"
        report += f"✅ Tasks Completed: {len(self.completed_tasks)}\n"
        report += f"📋 Tasks Remaining: {remaining_count}\n\n"

        if self.completed_tasks:
            report += "COMPLETED TASKS (in order):\n"
            report += "-" * 70 + "\n"
            for task in self.completed_tasks:
                report += f"{task['order']}. [{task['task_id']}] {task['title']}\n"
                report += f"   Completed at: {task['completed_at']}\n"
        else:
            report += "No tasks were completed.\n"

        report += "\n" + "=" * 70 + "\n"

        return report


async def simulate_task_work(task_title: str, task_id: str) -> None:
    """Simulate doing work on a task."""
    print(f"\n🔧 Working on task: {task_title}")
    print(f"   Task ID: {task_id}")

    # Simulate some work (just wait a bit)
    await asyncio.sleep(1)

    print(f"✅ Completed task: {task_title}")


async def autonomous_workflow() -> None:
    """
    Run the complete autonomous agent workflow.

    Steps:
    1. Create project (simple todo app)
    2. Register general-purpose agent
    3. Request tasks in a loop
    4. Simulate completing each task with progress reports
    5. Generate final report when done
    """
    print("\n" + "=" * 70)
    print("🤖 AUTONOMOUS AGENT WORKFLOW")
    print("=" * 70)
    print("\nThis agent will:")
    print("1. Create a 'Simple Todo App' project")
    print("2. Register as a general-purpose developer")
    print("3. Request and complete tasks continuously")
    print("4. Generate a final report")
    print("\n" + "=" * 70)

    client = Inspector(connection_type="stdio")
    tracker = TaskTracker()
    agent_id = "autonomous-agent-1"

    try:
        async with client.connect() as session:
            # Step 1: Authenticate as admin
            print("\n🔐 Step 1: Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": agent_id,
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"workflow": "autonomous", "test_mode": True},
                },
            )
            print("✅ Authenticated")

            # Step 2: Create a new project
            print("\n📂 Step 2: Creating 'Simple Todo App' project...")
            create_result = await session.call_tool(
                "create_project",
                arguments={
                    "description": (
                        "Create a simple todo application with the following features: "
                        "user authentication, create/read/update/delete tasks, "
                        "task priorities, due dates, and basic search functionality. "
                        "Use Python with FastAPI for backend and React for frontend."
                    ),
                    "project_name": "Simple Todo App",
                    "options": {
                        "mode": "auto",
                        "complexity": "prototype",
                    },
                },
            )
            pretty_print("✅ Project created:", create_result)

            # Parse project creation result
            if not create_result.content:
                print("\n❌ Failed to create project: No response content")
                return
            content_item = create_result.content[0]
            if not hasattr(content_item, "text"):
                print("\n❌ Failed to create project: Invalid response format")
                return
            create_data = json.loads(content_item.text)
            if not create_data.get("success"):
                print(f"\n❌ Failed to create project: {create_data.get('error')}")
                return

            total_tasks = create_data.get("tasks_created", 0)
            print(f"\n📊 Project created with {total_tasks} tasks")

            # Step 3: Register agent
            print("\n🤖 Step 3: Registering as general-purpose agent...")
            register_result = await client.register_agent(
                agent_id=agent_id,
                name="General Purpose Agent",
                role="Developer",
                skills=[
                    "python",
                    "javascript",
                    "react",
                    "fastapi",
                    "database",
                    "api-design",
                    "frontend",
                    "backend",
                ],
            )
            pretty_print("✅ Agent registered:", register_result)

            # Step 4: Task execution loop
            print("\n" + "=" * 70)
            print("🔄 Step 4: Entering task execution loop...")
            print("=" * 70)

            task_count = 0
            while True:
                # Request next task
                print(f"\n📋 Requesting task #{task_count + 1}...")
                task_data = await client.request_next_task(agent_id)

                if not task_data.get("task"):
                    print("\n✅ No more tasks available!")
                    remaining = task_data.get("message", "")
                    print(f"   {remaining}")
                    break

                task = task_data["task"]
                task_id = task.get("task_id", "unknown")
                task_title = task.get("title", "Untitled Task")
                task_count += 1

                print(f"\n{'=' * 70}")
                print(f"📌 TASK #{task_count}: {task_title}")
                print(f"{'=' * 70}")
                print(f"ID: {task_id}")
                print(f"Description: {task.get('description', 'No description')}")
                print(f"Priority: {task.get('priority', 'N/A')}")

                # Report starting work (0% progress)
                print("\n📊 Reporting task started...")
                await client.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="in_progress",
                    progress=0,
                    message=f"Starting work on: {task_title}",
                )

                # Simulate work and report progress milestones
                await simulate_task_work(task_title, task_id)

                # Report 50% progress
                print("📊 Reporting 50% progress...")
                await client.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="in_progress",
                    progress=50,
                    message=f"Halfway through implementing: {task_title}",
                )

                await asyncio.sleep(0.5)

                # Report 100% completion
                print("📊 Reporting task completion...")
                await client.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="completed",
                    progress=100,
                    message=f"Successfully completed: {task_title}",
                )

                # Track the completed task
                tracker.add_completed_task(task_id, task_title, task_count)

                print(f"\n✅ Task #{task_count} marked as complete!")

            # Step 5: Finalize and generate report
            tracker.finalize(remaining_count=total_tasks - task_count)
            report = tracker.generate_report(remaining_count=total_tasks - task_count)

            print(report)

            # Save report to file
            report_path = project_root / "autonomous_agent_report.txt"
            with open(report_path, "w") as f:
                f.write(report)
            print(f"📄 Report saved to: {report_path}\n")

    except Exception as e:
        print(f"\n❌ Error in autonomous workflow: {e}")
        import traceback

        traceback.print_exc()


async def main() -> None:
    """Run the autonomous agent workflow."""
    print("\n🚀 Starting Autonomous Agent Workflow Demo")
    print("=" * 70)
    print("\nThis demo creates a project, assigns tasks to an agent,")
    print("and simulates the complete task lifecycle with reporting.")
    print("\nNote: This may take 10-15 seconds to initialize...\n")

    await autonomous_workflow()

    print("\n" + "=" * 70)
    print("✅ Autonomous workflow complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
