#!/usr/bin/env python3
"""
Example: Complete Calculator Project Workflow with HTTP Connection.

This demonstrates a complete autonomous agent lifecycle:
1. Connect to Marcus via HTTP using streamablehttp_client
2. List available projects
3. Create a new "Calculator" project
4. Register as an agent
5. Request and simulate completing tasks
6. Report progress for each task
7. Generate task completion report and conversation log
8. Display remaining tasks when workflow completes

Prerequisites
-------------
- Marcus server must be running in HTTP mode
- Start server with: python -m src.marcus_mcp.server --http or ./marcus start

Note
----
- Uses the new Inspector client from src/worker/new_client.py
- This unified client supports both stdio and HTTP connections
- Uses streamablehttp_client for proper FastMCP compatibility
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


class ConversationLogger:
    """Log all interactions with Marcus for debugging and analysis."""

    def __init__(self) -> None:
        """Initialize the conversation logger."""
        self.entries: List[Dict[str, Any]] = []
        self.start_time = datetime.now()

    def log(
        self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a conversation event.

        Parameters
        ----------
        event_type : str
            Type of event (e.g., 'request', 'response', 'progress')
        message : str
            Human-readable message describing the event
        data : Optional[Dict[str, Any]]
            Additional structured data about the event
        """
        entry: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "message": message,
        }
        if data:
            entry["data"] = data
        self.entries.append(entry)

    def generate_log(self) -> str:
        """
        Generate a formatted conversation log.

        Returns
        -------
        str
            Formatted conversation log as a string
        """
        log = "\n" + "=" * 70 + "\n"
        log += "💬 MARCUS CONVERSATION LOG\n"
        log += "=" * 70 + "\n\n"
        log += f"Session started: {self.start_time.isoformat()}\n"
        log += f"Total events: {len(self.entries)}\n\n"

        log += "CONVERSATION TIMELINE:\n"
        log += "-" * 70 + "\n\n"

        for i, entry in enumerate(self.entries, 1):
            log += f"{i}. [{entry['timestamp']}] {entry['event_type'].upper()}\n"
            log += f"   {entry['message']}\n"
            if "data" in entry:
                log += f"   Data: {json.dumps(entry['data'], indent=6)}\n"
            log += "\n"

        log += "=" * 70 + "\n"
        return log


class TaskTracker:
    """Track completed and remaining tasks for final report."""

    def __init__(self) -> None:
        """Initialize the task tracker."""
        self.completed_tasks: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None

    def add_completed_task(self, task_id: str, title: str, order: int) -> None:
        """
        Record a completed task.

        Parameters
        ----------
        task_id : str
            Unique identifier for the task
        title : str
            Task title/description
        order : int
            Order in which the task was received
        """
        self.completed_tasks.append(
            {
                "order": order,
                "task_id": task_id,
                "title": title,
                "completed_at": datetime.now().isoformat(),
            }
        )

    def finalize(self) -> None:
        """Mark the workflow as complete."""
        self.end_time = datetime.now()

    def generate_report(self, remaining_count: int) -> str:
        """
        Generate a final report of the agent's work.

        Parameters
        ----------
        remaining_count : int
            Number of tasks remaining on the board

        Returns
        -------
        str
            Formatted report as a string
        """
        if self.end_time is None:
            raise ValueError("Cannot generate report before workflow is finalized")
        duration = (self.end_time - self.start_time).total_seconds()

        report = "\n" + "=" * 70 + "\n"
        report += "📊 CALCULATOR PROJECT WORKFLOW REPORT\n"
        report += "=" * 70 + "\n\n"

        report += f"⏱️  Duration: {duration:.2f} seconds\n"
        report += f"✅ Tasks Completed: {len(self.completed_tasks)}\n"
        report += f"📋 Tasks Remaining: {remaining_count}\n\n"

        if self.completed_tasks:
            report += "COMPLETED TASKS (in order received from Marcus):\n"
            report += "-" * 70 + "\n"
            for task in self.completed_tasks:
                report += f"{task['order']}. [{task['task_id']}] {task['title']}\n"
                report += f"   Completed at: {task['completed_at']}\n"
        else:
            report += "No tasks were completed.\n"

        report += "\n" + "=" * 70 + "\n"

        return report


def pretty_print(label: str, result: Any) -> None:
    """
    Pretty print MCP tool results.

    Parameters
    ----------
    label : str
        Label to display before the result
    result : Any
        Result object to print
    """
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


async def simulate_task_work(task_title: str, task_id: str) -> None:
    """
    Simulate doing work on a task.

    Parameters
    ----------
    task_title : str
        Title of the task being worked on
    task_id : str
        Unique identifier for the task
    """
    print(f"\n🔧 Working on task: {task_title}")
    print(f"   Task ID: {task_id}")

    # Simulate some work (just wait a bit)
    await asyncio.sleep(1)

    print(f"✅ Completed task: {task_title}")


async def calculator_workflow() -> None:
    """
    Run the complete calculator project workflow via HTTP.

    Steps:
    1. Connect to Marcus via HTTP
    2. List available projects
    3. Create "Calculator" project
    4. Register as agent
    5. Request and complete tasks in a loop
    6. Generate task report and conversation log
    """
    print("\n" + "=" * 70)
    print("🧮 CALCULATOR PROJECT WORKFLOW (HTTP)")
    print("=" * 70)
    print("\nThis agent will:")
    print("1. Connect to Marcus via HTTP")
    print("2. List available projects")
    print("3. Create a 'Calculator' project")
    print("4. Request and simulate completing tasks")
    print("5. Generate task report and conversation log")
    print("\n" + "=" * 70)

    client = Inspector(connection_type="http")
    tracker = TaskTracker()
    logger = ConversationLogger()
    agent_id = "calculator-agent"
    url = "http://localhost:4298/mcp"

    try:
        logger.log("connection", f"Connecting to Marcus at {url}")
        async with client.connect(url=url) as session:
            # Step 1: Authenticate as admin
            print("\n🔐 Step 1: Authenticating as admin...")
            logger.log("authentication", "Authenticating as admin for full access")

            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": agent_id,
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"workflow": "calculator", "connection": "http"},
                },
            )
            print("✅ Authenticated")
            logger.log("authentication", "Successfully authenticated as admin")

            # Step 2: List available projects
            print("\n📂 Step 2: Listing available projects...")
            logger.log("project_management", "Requesting list of available projects")

            projects_result = await session.call_tool("list_projects", arguments={})
            pretty_print("Available projects:", projects_result)

            projects_text = projects_result.content[0].text
            projects_data = json.loads(projects_text)
            logger.log(
                "project_management",
                f"Found {len(projects_data)} existing projects",
                {"project_count": len(projects_data)},
            )

            # Step 3: Create Calculator project
            print("\n📂 Step 3: Creating 'Calculator' project...")
            logger.log("project_creation", "Creating new Calculator project")

            create_result = await session.call_tool(
                "create_project",
                arguments={
                    "description": (
                        "Build a calculator application with these features: "
                        "add, subtract, multiply, and divide operations. "
                        "Include input validation, division by zero handling, "
                        "and a simple command-line interface. Use Python."
                    ),
                    "project_name": "Calculator",
                    "options": {
                        "mode": "new_project",  # Force creation of new project
                        "complexity": "prototype",
                        "planka_project_name": "Calculator",
                        "planka_board_name": "Development Board",
                    },
                },
            )
            pretty_print("✅ Project created:", create_result)

            # Parse project creation result
            if not create_result.content:
                error_msg = "Failed to create project: No response content"
                print(f"\n❌ {error_msg}")
                logger.log("error", error_msg)
                return

            content_item = create_result.content[0]
            if not hasattr(content_item, "text"):
                error_msg = "Failed to create project: Invalid response format"
                print(f"\n❌ {error_msg}")
                logger.log("error", error_msg)
                return

            create_data = json.loads(content_item.text)
            if not create_data.get("success"):
                error_msg = f"Failed to create project: {create_data.get('error')}"
                print(f"\n❌ {error_msg}")
                logger.log("error", error_msg)
                return

            total_tasks = create_data.get("tasks_created", 0)
            board_info = create_data.get("board", {})
            print(f"\n📊 Project created with {total_tasks} tasks")
            logger.log(
                "project_creation",
                f"Calculator project created successfully with {total_tasks} tasks",
                {"tasks_created": total_tasks, "board": board_info},
            )

            # Step 4: Register agent
            print("\n🤖 Step 4: Registering as calculator agent...")
            logger.log("agent_registration", "Registering agent with Marcus")

            register_result = await client.register_agent(
                agent_id=agent_id,
                name="Calculator Developer",
                role="Developer",
                skills=["python", "mathematics", "testing", "error-handling"],
            )
            pretty_print("✅ Agent registered:", register_result)
            logger.log("agent_registration", "Agent registered successfully")

            # Step 5: Task execution loop
            print("\n" + "=" * 70)
            print("🔄 Step 5: Entering task execution loop...")
            print("=" * 70)
            logger.log("task_execution", "Starting task execution loop")

            task_count = 0
            while True:
                # Request next task
                print(f"\n📋 Requesting task #{task_count + 1}...")
                logger.log("task_request", f"Requesting task #{task_count + 1}")

                task_result = await client.request_next_task(agent_id)

                # Handle different response formats
                if hasattr(task_result, "content") and task_result.content:
                    task_text = task_result.content[0].text
                    task_data = json.loads(task_text)
                else:
                    task_data = task_result

                if not task_data.get("task"):
                    remaining_msg = task_data.get("message", "No more tasks available")
                    print(f"\n✅ {remaining_msg}")
                    logger.log(
                        "task_completion",
                        "All tasks completed",
                        {"message": remaining_msg},
                    )
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

                logger.log(
                    "task_received",
                    f"Received task #{task_count}: {task_title}",
                    {
                        "task_id": task_id,
                        "order": task_count,
                        "priority": task.get("priority"),
                    },
                )

                # Report starting work (0% progress)
                print("\n📊 Reporting task started...")
                await client.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="in_progress",
                    progress=0,
                    message=f"Starting work on: {task_title}",
                )
                logger.log("progress_report", "Task started (0%)", {"task_id": task_id})

                # Simulate work
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
                logger.log("progress_report", "Task 50% complete", {"task_id": task_id})

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
                logger.log(
                    "progress_report", "Task completed (100%)", {"task_id": task_id}
                )

                # Track the completed task
                tracker.add_completed_task(task_id, task_title, task_count)

                print(f"\n✅ Task #{task_count} marked as complete!")

            # Step 6: Get remaining task count
            print("\n📊 Step 6: Checking remaining tasks...")
            logger.log("status_check", "Checking board status for remaining tasks")

            # Request one more task to confirm there are none left
            await client.request_next_task(agent_id)

            remaining_tasks = 0  # No tasks left if we got here
            logger.log(
                "status_check",
                f"Board status: {remaining_tasks} tasks remaining",
                {"remaining": remaining_tasks},
            )

            # Step 7: Finalize and generate reports
            tracker.finalize()
            task_report = tracker.generate_report(remaining_count=remaining_tasks)
            conversation_log = logger.generate_log()

            print(task_report)
            print(conversation_log)

            # Save reports to files
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_report_path = project_root / f"calculator_task_report_{timestamp}.txt"
            conv_log_path = (
                project_root / f"calculator_conversation_log_{timestamp}.txt"
            )

            with open(task_report_path, "w") as f:
                f.write(task_report)
            print(f"📄 Task report saved to: {task_report_path}")

            with open(conv_log_path, "w") as f:
                f.write(conversation_log)
            print(f"📄 Conversation log saved to: {conv_log_path}\n")

            logger.log(
                "workflow_complete",
                "Workflow completed successfully",
                {
                    "tasks_completed": len(tracker.completed_tasks),
                    "remaining_tasks": remaining_tasks,
                    "reports": [str(task_report_path), str(conv_log_path)],
                },
            )

    except Exception as e:
        error_msg = f"Error in calculator workflow: {e}"
        print(f"\n❌ {error_msg}")
        logger.log("error", error_msg)

        print("\n💡 Troubleshooting:")
        print("   1. Make sure Marcus server is running in HTTP mode")
        print("   2. Start server with: python -m src.marcus_mcp.server --http")
        print(f"   3. Verify the URL is correct: {url}")
        print("   4. Check that the server is configured for external HTTP access")

        import traceback

        traceback.print_exc()


async def main() -> None:
    """Run the calculator project workflow."""
    print("\n🚀 Starting Calculator Project Workflow Demo")
    print("=" * 70)
    print("\nThis demo demonstrates a complete agent workflow:")
    print("- Connects to Marcus via HTTP using streamablehttp_client")
    print("- Creates a Calculator project")
    print("- Completes all assigned tasks")
    print("- Generates detailed reports and logs")
    print("\nPrerequisites:")
    print("- Marcus server running in HTTP mode")
    print("- Check status: ./marcus status")
    print("=" * 70)

    await calculator_workflow()

    print("\n" + "=" * 70)
    print("✅ Calculator workflow complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
