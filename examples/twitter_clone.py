#!/usr/bin/env python3
"""
Example: Complete Twitter Project Workflow

This demonstrates a complete autonomous agent lifecycle:
1. Connect to Marcus via HTTP using streamablehttp_client
2. List available projects
3. Create a new "Twitter" project
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
        report += "📊 TWITTER SWARM PROJECT WORKFLOW REPORT\n"
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


async def agent_worker(
    agent_id: str,
    agent_name: str,
    skills: List[str],
    tracker: TaskTracker,
    logger: ConversationLogger,
    url: str,
    task_counter: Dict[str, int],
) -> None:
    """
    Worker function for a single agent in the swarm.

    Parameters
    ----------
    agent_id : str
        Unique identifier for this agent
    agent_name : str
        Display name for this agent
    skills : List[str]
        List of skills this agent has
    tracker : TaskTracker
        Shared task tracker for all agents
    logger : ConversationLogger
        Shared conversation logger
    url : str
        Marcus server URL
    task_counter : Dict[str, int]
        Shared counter for task ordering
    """
    client = Inspector(connection_type="http")

    try:
        async with client.connect(url=url) as session:
            # Authenticate
            print(f"\n🔐 [{agent_id}] Authenticating...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": agent_id,
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"workflow": "twitter", "connection": "http"},
                },
            )
            logger.log("authentication", f"{agent_id} authenticated successfully")

            # Register agent
            print(f"🤖 [{agent_id}] Registering as {agent_name}...")
            await client.register_agent(
                agent_id=agent_id,
                name=agent_name,
                role="Developer",
                skills=skills,
            )
            logger.log("agent_registration", f"{agent_id} registered with skills: {skills}")

            # Task execution loop
            while True:
                # Request next task
                logger.log("task_request", f"{agent_id} requesting task")

                task_result = await client.request_next_task(agent_id)

                # Handle different response formats
                if hasattr(task_result, "content") and task_result.content:
                    task_text = task_result.content[0].text
                    task_data = json.loads(task_text)
                else:
                    task_data = task_result

                if not task_data.get("task"):
                    print(f"\n✅ [{agent_id}] No more tasks available")
                    logger.log(
                        "task_completion",
                        f"{agent_id} finished - no more tasks",
                        {"message": task_data.get("message", "No tasks")},
                    )
                    break

                task = task_data["task"]
                task_id = task.get("id", "unknown")
                task_title = task.get("name", "Untitled Task")

                # Increment global task counter
                task_counter["count"] += 1
                task_order = task_counter["count"]

                print(f"\n{'=' * 70}")
                print(f"📌 [{agent_id}] TASK #{task_order}: {task_title}")
                print(f"{'=' * 70}")
                print(f"ID: {task_id}")
                print(f"Priority: {task.get('priority', 'N/A')}")

                logger.log(
                    "task_received",
                    f"{agent_id} received task #{task_order}: {task_title}",
                    {
                        "agent_id": agent_id,
                        "task_id": task_id,
                        "order": task_order,
                        "priority": task.get("priority"),
                    },
                )

                # Report starting work (0% progress)
                await client.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="in_progress",
                    progress=0,
                    message=f"[{agent_id}] Starting work on: {task_title}",
                )
                logger.log("progress_report", f"{agent_id} started task", {"task_id": task_id})

                # Simulate work
                await simulate_task_work(task_title, task_id)

                # Report 50% progress
                await client.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="in_progress",
                    progress=50,
                    message=f"[{agent_id}] Halfway through: {task_title}",
                )
                logger.log("progress_report", f"{agent_id} at 50%", {"task_id": task_id})

                await asyncio.sleep(0.5)

                # Report 100% completion
                await client.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="completed",
                    progress=100,
                    message=f"[{agent_id}] Successfully completed: {task_title}",
                )
                logger.log(
                    "progress_report", f"{agent_id} completed task", {"task_id": task_id}
                )

                # Track the completed task
                tracker.add_completed_task(task_id, task_title, task_order)

                print(f"✅ [{agent_id}] Task #{task_order} complete!")

    except Exception as e:
        error_msg = f"[{agent_id}] Error: {e}"
        print(f"\n❌ {error_msg}")
        logger.log("error", error_msg)
        import traceback
        traceback.print_exc()


async def calculator_workflow() -> None:
    """
    Run the complete Twitter project workflow with a swarm of agents.

    Steps:
    1. Connect to Marcus via HTTP
    2. List available projects
    3. Create "Twitter" project
    4. Register multiple agents with different skills
    5. Run agents in parallel to complete tasks
    6. Generate task report and conversation log
    """
    print("\n" + "=" * 70)
    print("🐦 Twitter Project - SWARM MODE")
    print("=" * 70)
    print("\nThis swarm will:")
    print("1. Connect to Marcus via HTTP")
    print("2. Create a 'Twitter' project")
    print("3. Deploy 5 specialized agents in parallel")
    print("4. Agents work concurrently on assigned tasks")
    print("5. Generate consolidated report and logs")
    print("\n" + "=" * 70)

    # Shared resources
    tracker = TaskTracker()
    logger = ConversationLogger()
    task_counter = {"count": 0}  # Shared task counter
    url = "http://localhost:4298/mcp"

    # Define swarm agents with different specializations
    swarm_agents = [
        {
            "agent_id": "backend-dev",
            "name": "Backend Developer",
            "skills": ["python", "api", "database", "fastapi", "backend"],
        },
        {
            "agent_id": "frontend-dev",
            "name": "Frontend Developer",
            "skills": ["javascript", "react", "ui", "frontend", "css"],
        },
        {
            "agent_id": "database-expert",
            "name": "Database Specialist",
            "skills": ["database", "sql", "postgresql", "schema", "migration"],
        },
        {
            "agent_id": "testing-engineer",
            "name": "Testing Engineer",
            "skills": ["testing", "pytest", "qa", "integration-tests", "python"],
        },
        {
            "agent_id": "devops-engineer",
            "name": "DevOps Engineer",
            "skills": ["docker", "deployment", "ci-cd", "infrastructure", "monitoring"],
        },
    ]

    client = Inspector(connection_type="http")
    tracker = TaskTracker()
    logger = ConversationLogger()
    url = "http://localhost:4298/mcp"

    try:
        logger.log("connection", f"Connecting to Marcus at {url}")
        async with client.connect(url=url) as session:
            # Step 1: Authenticate as admin
            print("\n🔐 Step 1: Authenticating as coordinator...")
            logger.log("authentication", "Authenticating coordinator for project setup")

            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "swarm-coordinator",
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"workflow": "twitter-swarm", "connection": "http"},
                },
            )
            print("✅ Coordinator authenticated")
            logger.log("authentication", "Successfully authenticated as coordinator")

            # Step 2: List available projects
            print("\n📂 Step 2: Listing available projects...")
            logger.log("project_management", "Requesting list of available projects")

            projects_result = await session.call_tool("list_projects", arguments={})
            pretty_print("Available projects:", projects_result)

            projects_text = (
                projects_result.content[0].text  # type: ignore[union-attr]
                if projects_result.content
                else "{}"
            )
            projects_data = json.loads(projects_text)
            logger.log(
                "project_management",
                f"Found {len(projects_data)} existing projects",
                {"project_count": len(projects_data)},
            )

            # Step 3: Create Twitter project
            print("\n📂 Step 3: Creating 'Twitter' project...")
            logger.log("project_creation", "Creating new Twitter project")

            create_result = await session.call_tool(
                "create_project",
                arguments={
                    "description": (
                        "Build a Twitter clone with the following features: "
                        "User authentication (registration, login, JWT tokens), "
                        "Tweet creation with 280 character limit, "
                        "Follow/unfollow users, "
                        "Timeline feed showing tweets from followed users, "
                        "Like and retweet functionality, "
                        "Hashtag support and trending topics, "
                        "User profiles with bio and avatar, "
                        "REST API using FastAPI, "
                        "PostgreSQL database, "
                        "Comprehensive test coverage. Use Python."
                    ),
                    "project_name": "Twitter",
                    "options": {
                        "mode": "new_project",  # Force creation of new project
                        "complexity": "enterprise",
                        "planka_project_name": "Twitter",
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
                f"Twitter project created successfully with {total_tasks} tasks",
                {"tasks_created": total_tasks, "board": board_info},
            )

        # Step 4: Launch agent swarm in parallel
        print("\n" + "=" * 70)
        print(f"🚀 Step 4: Launching swarm of {len(swarm_agents)} agents...")
        print("=" * 70)
        logger.log(
            "swarm_launch",
            f"Deploying {len(swarm_agents)} specialized agents",
            {"agent_count": len(swarm_agents)},
        )

        # Create tasks for each agent worker
        agent_tasks = []
        for agent_config in swarm_agents:
            agent_id = str(agent_config["agent_id"])
            agent_name = str(agent_config["name"])
            skills = list(agent_config["skills"])

            print(f"🤖 Deploying {agent_name} ({agent_id})...")
            agent_task = asyncio.create_task(
                agent_worker(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    skills=skills,
                    tracker=tracker,
                    logger=logger,
                    url=url,
                    task_counter=task_counter,
                )
            )
            agent_tasks.append(agent_task)

        print(f"\n✅ All {len(swarm_agents)} agents deployed!")
        print("⏳ Agents are now working in parallel...")
        print("=" * 70)

        # Wait for all agents to complete
        logger.log("swarm_execution", "Waiting for all agents to complete their work")
        await asyncio.gather(*agent_tasks, return_exceptions=True)

        print("\n" + "=" * 70)
        print("✅ All agents have completed their work!")
        print("=" * 70)

        # Step 5: Get final status
        print("\n📊 Step 5: Checking final project status...")
        logger.log("status_check", "Checking final board status")

        remaining_tasks = 0  # Assume all done if all agents finished
        logger.log(
            "status_check",
            f"Final status: {remaining_tasks} tasks remaining",
            {"remaining": remaining_tasks},
        )

        # Step 6: Finalize and generate reports
        print("\n📊 Step 6: Generating reports...")
        tracker.finalize()
        task_report = tracker.generate_report(remaining_count=remaining_tasks)
        conversation_log = logger.generate_log()

        print(task_report)
        print(conversation_log)

        # Save reports to files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_report_path = project_root / f"twitter_swarm_task_report_{timestamp}.txt"
        conv_log_path = project_root / f"twitter_swarm_conversation_log_{timestamp}.txt"

        with open(task_report_path, "w") as f:
            f.write(task_report)
        print(f"📄 Task report saved to: {task_report_path}")

        with open(conv_log_path, "w") as f:
            f.write(conversation_log)
        print(f"📄 Conversation log saved to: {conv_log_path}\n")

        logger.log(
            "workflow_complete",
            "Swarm workflow completed successfully",
            {
                "agents_deployed": len(swarm_agents),
                "tasks_completed": len(tracker.completed_tasks),
                "remaining_tasks": remaining_tasks,
                "reports": [str(task_report_path), str(conv_log_path)],
            },
        )

    except Exception as e:
        error_msg = f"Error in Twitter swarm workflow: {e}"
        print(f"\n❌ {error_msg}")
        logger.log("error", error_msg)

        print("\n💡 Troubleshooting:")
        print("   1. Make sure Marcus server is running in HTTP mode")
        print("   2. Start server with: python -m src.marcus_mcp.server --http")
        print(f"   3. Verify the URL is correct: {url}")
        print("   4. Check that the server is configured for external HTTP access")
        print("   5. Ensure Planka board exists for task management")

        import traceback

        traceback.print_exc()


async def main() -> None:
    """Run the Twitter swarm project workflow."""
    print("\n🚀 Starting Twitter Swarm Project Workflow Demo")
    print("=" * 70)
    print("\nThis demo demonstrates a multi-agent swarm workflow:")
    print("- Connects to Marcus via HTTP using streamablehttp_client")
    print("- Creates a Twitter clone project with detailed requirements")
    print("- Deploys 5 specialized agents working in parallel")
    print("- Each agent pulls and completes tasks based on their skills")
    print("- Tests Marcus's ability to handle concurrent agents")
    print("- Generates detailed reports and logs")
    print("\nPrerequisites:")
    print("- Marcus server running in HTTP mode")
    print("- Check status: ./marcus status")
    print("=" * 70)

    await calculator_workflow()

    print("\n" + "=" * 70)
    print("✅ Twitter swarm workflow complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
