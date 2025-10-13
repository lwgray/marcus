#!/usr/bin/env python3
r"""
Example: Twitter Swarm with MLflow Experiment Tracking.

This demonstrates a complete autonomous agent swarm with comprehensive
MLflow tracking for experiment comparison and analysis.

Features:
- 50 specialized agents working in parallel
- MLflow tracking of all metrics and conditions
- Configurable experimental conditions:
  * Blocker reporting
  * Artifact logging
  * Decision logging
  * Context requests
- Automatic comparison with previous runs

Prerequisites
-------------
- Marcus server must be running in HTTP mode
- MLflow installed: pip install mlflow
- Start server with: python -m src.marcus_mcp.server --http or ./marcus start

Usage
-----
python examples/twitter_clone_with_mlflow.py --experiment-name "my-test" \
    --enable-blockers --enable-artifacts --enable-decisions
"""

import asyncio
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.types import TextContent  # noqa: E402

from src.experiments import MarcusExperiment  # noqa: E402
from src.worker.inspector import Inspector  # noqa: E402


class MLflowTaskTracker:
    """Track task timing for MLflow."""

    def __init__(self, experiment: MarcusExperiment):
        self.experiment = experiment
        self.task_start_times: Dict[str, float] = {}
        self.completed_tasks: List[tuple[str, float]] = []  # (task_id, completion_time)
        self.start_time = asyncio.get_event_loop().time()

    def start_task(self, task_id: str) -> None:
        """Record task start time."""
        self.task_start_times[task_id] = asyncio.get_event_loop().time()

    def complete_task(self, task_id: str, agent_id: str) -> None:
        """Log task completion to MLflow."""
        if task_id in self.task_start_times:
            duration = asyncio.get_event_loop().time() - self.task_start_times[task_id]
            completion_time = asyncio.get_event_loop().time()

            self.experiment.log_task_completion(
                task_id=task_id, duration_seconds=duration, agent_id=agent_id
            )

            self.completed_tasks.append((task_id, completion_time))
            del self.task_start_times[task_id]

    def calculate_velocity(self) -> float:
        """Calculate simple velocity as tasks per hour."""
        if not self.completed_tasks:
            return 0.0

        current_time = asyncio.get_event_loop().time()
        elapsed_hours = (current_time - self.start_time) / 3600

        if elapsed_hours < 0.01:  # Avoid division by zero
            return 0.0

        return len(self.completed_tasks) / elapsed_hours

    def get_avg_completion_time(self) -> float:
        """Get average task completion time in seconds."""
        if not self.completed_tasks or len(self.completed_tasks) < 2:
            return 0.0

        # Calculate time between consecutive completions
        completion_times = [t[1] for t in self.completed_tasks]
        intervals = [
            completion_times[i] - completion_times[i - 1]
            for i in range(1, len(completion_times))
        ]

        return sum(intervals) / len(intervals) if intervals else 0.0


async def agent_worker(
    agent_id: str,
    agent_name: str,
    skills: List[str],
    url: str,
    experiment: MarcusExperiment,
    task_tracker: MLflowTaskTracker,
    conditions: Dict[str, bool],
    logger: Any,
) -> None:
    """
    Worker function for a single agent with MLflow tracking.

    Parameters
    ----------
    agent_id : str
        Unique identifier for this agent
    agent_name : str
        Display name for this agent
    skills : List[str]
        List of skills this agent has
    url : str
        Marcus server URL
    experiment : MarcusExperiment
        MLflow experiment tracker
    task_tracker : MLflowTaskTracker
        Task timing tracker
    conditions : Dict[str, bool]
        Experimental conditions to enable/disable
    logger : Any
        Conversation logger
    """
    client = Inspector(connection_type="http")
    tasks_completed = 0
    task_durations: List[float] = []

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
            logger.log(
                "agent_registration", f"{agent_id} registered with skills: {skills}"
            )

            # Task execution loop
            while True:
                # Request next task
                logger.log("task_request", f"{agent_id} requesting task")

                # Simulate context request if enabled
                if (
                    conditions.get("enable_context_requests")
                    and random.random() < 0.3  # nosec B311
                ):
                    experiment.log_context_request(
                        agent_id, "pending-task", "task_context"
                    )

                task_result = await client.request_next_task(agent_id)

                # Handle different response formats
                if hasattr(task_result, "content") and task_result.content:
                    content_item = task_result.content[0]
                    if isinstance(content_item, TextContent):
                        task_text = content_item.text
                        task_data = json.loads(task_text)
                    else:
                        task_data = task_result
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

                print(f"\n📌 [{agent_id}] Starting: {task_title} ({task_id})")

                # Start tracking task time
                task_tracker.start_task(task_id)

                logger.log(
                    "task_received",
                    f"{agent_id} received task: {task_title}",
                    {"agent_id": agent_id, "task_id": task_id},
                )

                # Report starting work
                await client.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="in_progress",
                    progress=0,
                    message=f"[{agent_id}] Starting work on: {task_title}",
                )

                # Simulate work with conditional behaviors
                work_duration = random.uniform(0.5, 2.0)  # nosec B311

                # Simulate blocker if enabled
                if (
                    conditions.get("enable_blockers")
                    and random.random() < 0.15  # nosec B311
                ):
                    blocker_desc = f"Dependency on external service for {task_title}"
                    severity = random.choice(["low", "medium", "high"])  # nosec B311

                    experiment.log_blocker(
                        agent_id=agent_id,
                        task_id=task_id,
                        blocker_description=blocker_desc,
                        severity=severity,
                    )
                    print(f"⚠️  [{agent_id}] Blocker reported: {blocker_desc}")
                    work_duration += 1.0  # Blockers add delay

                await asyncio.sleep(work_duration)

                # Report 50% progress
                await client.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="in_progress",
                    progress=50,
                    message=f"[{agent_id}] Halfway through: {task_title}",
                )

                # Simulate artifact creation if enabled
                if (
                    conditions.get("enable_artifacts")
                    and random.random() < 0.25  # nosec B311
                ):
                    artifact_types = ["specification", "api", "design", "documentation"]
                    artifact_type = random.choice(artifact_types)  # nosec B311

                    experiment.log_artifact_event(
                        task_id=task_id,
                        artifact_type=artifact_type,
                        filename=f"{task_id}_{artifact_type}.md",
                        description=f"Generated {artifact_type} for {task_title}",
                    )
                    print(f"📄 [{agent_id}] Artifact created: {artifact_type}")

                await asyncio.sleep(work_duration)

                # Simulate decision logging if enabled
                if (
                    conditions.get("enable_decisions")
                    and random.random() < 0.20  # nosec B311
                ):
                    decisions = [
                        "Chose PostgreSQL for data persistence",
                        "Using JWT tokens for authentication",
                        "Implementing REST API with FastAPI",
                        "Using Redis for caching layer",
                    ]
                    decision = random.choice(decisions)  # nosec B311

                    experiment.log_decision(
                        agent_id=agent_id, task_id=task_id, decision=decision
                    )
                    print(f"💡 [{agent_id}] Decision logged: {decision}")

                # Report completion
                await client.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="completed",
                    progress=100,
                    message=f"[{agent_id}] Successfully completed: {task_title}",
                )

                # Track completion in MLflow
                task_tracker.complete_task(task_id, agent_id)
                tasks_completed += 1

                print(f"✅ [{agent_id}] Completed: {task_title}")

    except Exception as e:
        error_msg = f"[{agent_id}] Error: {e}"
        print(f"\n❌ {error_msg}")
        logger.log("error", error_msg)
        import traceback

        traceback.print_exc()

    finally:
        # Log final agent metrics
        if task_durations:
            avg_duration = sum(task_durations) / len(task_durations)
            success_rate = tasks_completed / max(len(task_durations), 1)
            experiment.log_agent_metrics(
                agent_id=agent_id,
                tasks_completed=tasks_completed,
                avg_task_duration=avg_duration,
                success_rate=success_rate,
            )


async def twitter_mlflow_workflow(
    num_agents: int = 50,
    complexity: str = "enterprise",
    enable_blockers: bool = True,
    enable_artifacts: bool = True,
    enable_decisions: bool = True,
    enable_context_requests: bool = True,
    experiment_name: str = "twitter-swarm-test",
    run_name: Optional[str] = None,
) -> None:
    """
    Run Twitter swarm workflow with MLflow tracking.

    Parameters
    ----------
    num_agents : int
        Number of agents to deploy
    complexity : str
        Project complexity level
    enable_blockers : bool
        Enable blocker reporting
    enable_artifacts : bool
        Enable artifact logging
    enable_decisions : bool
        Enable decision logging
    enable_context_requests : bool
        Enable context requests
    experiment_name : str
        MLflow experiment name
    run_name : str, optional
        Specific run name
    """
    print("\n" + "=" * 70)
    print(f"🐦 Twitter Project - MLflow Experiment Tracking ({num_agents} AGENTS)")
    print("=" * 70)
    print("\nExperimental Conditions:")
    print(f"  📊 Agents: {num_agents}")
    print(f"  📈 Complexity: {complexity}")
    print(f"  🚫 Blockers: {'Enabled' if enable_blockers else 'Disabled'}")
    print(f"  📄 Artifacts: {'Enabled' if enable_artifacts else 'Disabled'}")
    print(f"  💡 Decisions: {'Enabled' if enable_decisions else 'Disabled'}")
    print(
        f"  🔍 Context Requests: {'Enabled' if enable_context_requests else 'Disabled'}"
    )
    print("=" * 70)

    # Initialize MLflow experiment
    experiment = MarcusExperiment(
        experiment_name=experiment_name, tracking_uri="./mlruns"
    )

    # Prepare experiment parameters
    params = {
        "num_agents": num_agents,
        "complexity": complexity,
        "enable_blockers": enable_blockers,
        "enable_artifacts": enable_artifacts,
        "enable_decisions": enable_decisions,
        "enable_context_requests": enable_context_requests,
        "project_type": "twitter-clone",
    }

    # Shared resources
    url = "http://localhost:4298/mcp"

    # Import loggers
    from examples.twitter_clone import ConversationLogger

    logger = ConversationLogger()
    task_tracker = MLflowTaskTracker(experiment)

    conditions = {
        "enable_blockers": enable_blockers,
        "enable_artifacts": enable_artifacts,
        "enable_decisions": enable_decisions,
        "enable_context_requests": enable_context_requests,
    }

    # Start MLflow run
    if run_name is None:
        run_name = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    with experiment.start_run(run_name=run_name, params=params):
        client = Inspector(connection_type="http")

        try:
            async with client.connect(url=url) as session:
                # Create project
                print("\n📂 Creating Twitter project...")

                await session.call_tool(
                    "authenticate",
                    arguments={
                        "client_id": "swarm-coordinator",
                        "client_type": "admin",
                        "role": "admin",
                        "metadata": {"workflow": "twitter-swarm", "connection": "http"},
                    },
                )

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
                            "mode": "new_project",
                            "complexity": complexity,
                            "planka_project_name": "Twitter",
                            "planka_board_name": "Development Board",
                        },
                    },
                )

                # Extract and parse the result
                content_item = create_result.content[0]
                if isinstance(content_item, TextContent):
                    create_data = json.loads(content_item.text)
                    total_tasks = create_data.get("tasks_created", 0)
                else:
                    total_tasks = 0

                print(f"✅ Project created with {total_tasks} tasks")
                experiment.log_param("total_tasks_created", total_tasks)

            # Create agent swarm
            print(f"\n🚀 Deploying {num_agents} specialized agents...")

            agent_templates = [
                {
                    "type": "backend-dev",
                    "name": "Backend Developer",
                    "skills": ["python", "api", "database", "fastapi", "backend"],
                },
                {
                    "type": "frontend-dev",
                    "name": "Frontend Developer",
                    "skills": ["javascript", "react", "ui", "frontend", "css"],
                },
                {
                    "type": "database-expert",
                    "name": "Database Specialist",
                    "skills": ["database", "sql", "postgresql", "schema", "migration"],
                },
                {
                    "type": "testing-engineer",
                    "name": "Testing Engineer",
                    "skills": [
                        "testing",
                        "pytest",
                        "qa",
                        "integration-tests",
                        "python",
                    ],
                },
                {
                    "type": "devops-engineer",
                    "name": "DevOps Engineer",
                    "skills": [
                        "docker",
                        "deployment",
                        "ci-cd",
                        "infrastructure",
                        "monitoring",
                    ],
                },
            ]

            swarm_agents = []
            agents_per_type = num_agents // len(agent_templates)
            for i in range(agents_per_type):
                for template in agent_templates:
                    swarm_agents.append(
                        {
                            "agent_id": f"{template['type']}-{i+1:02d}",
                            "name": f"{template['name']} #{i+1}",
                            "skills": template["skills"],
                        }
                    )

            # Launch agents
            agent_tasks = []
            for agent_config in swarm_agents:
                agent_task = asyncio.create_task(
                    agent_worker(
                        agent_id=str(agent_config["agent_id"]),
                        agent_name=str(agent_config["name"]),
                        skills=list(agent_config["skills"]),
                        url=url,
                        experiment=experiment,
                        task_tracker=task_tracker,
                        conditions=conditions,
                        logger=logger,
                    )
                )
                agent_tasks.append(agent_task)

            print(f"✅ All {len(swarm_agents)} agents deployed!")
            print("⏳ Agents working in parallel...")

            # Background task to monitor and log metrics periodically
            async def monitor_metrics() -> None:
                """Periodically log project metrics to MLflow."""
                step = 0
                try:
                    from src.monitoring.project_monitor import ProjectMonitor

                    monitor = ProjectMonitor()

                    while True:
                        await asyncio.sleep(30)  # Log every 30 seconds
                        try:
                            state = await monitor.get_project_state()
                            experiment.log_project_state(
                                total_tasks=state.total_tasks,
                                completed_tasks=state.completed_tasks,
                                in_progress_tasks=state.in_progress_tasks,
                                blocked_tasks=state.blocked_tasks,
                                progress_percent=state.progress_percent,
                                velocity=state.team_velocity,
                                step=step,
                            )
                            step += 1
                        except Exception as e:
                            logger.log(
                                "monitoring_error", f"Failed to log metrics: {e}"
                            )
                except Exception as e:
                    logger.log(
                        "monitoring_error", f"Monitor initialization failed: {e}"
                    )

            # Start monitoring task
            monitor_task = asyncio.create_task(monitor_metrics())

            # Wait for all agents (monitoring will continue in background)
            await asyncio.gather(*agent_tasks, return_exceptions=True)

            # Cancel monitoring task
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

            print("\n✅ All agents completed!")

            # Get final project state and metrics from Marcus
            try:
                from src.monitoring.project_monitor import ProjectMonitor

                # Initialize monitoring to get velocity
                monitor = ProjectMonitor()
                project_state = await monitor.get_project_state()

                # Log final project metrics to MLflow
                experiment.log_project_state(
                    total_tasks=project_state.total_tasks,
                    completed_tasks=project_state.completed_tasks,
                    in_progress_tasks=project_state.in_progress_tasks,
                    blocked_tasks=project_state.blocked_tasks,
                    progress_percent=project_state.progress_percent,
                    velocity=project_state.team_velocity,
                )

                # Also log velocity separately for easier viewing
                experiment.log_velocity(project_state.team_velocity)

                print("\n📊 Final Metrics:")
                print(f"  Velocity: {project_state.team_velocity:.2f} tasks/week")
                print(f"  Progress: {project_state.progress_percent:.1f}%")
                print(
                    f"  Completed: {project_state.completed_tasks}/"
                    f"{project_state.total_tasks}"
                )

            except Exception as e:
                print(f"⚠️  Could not fetch project state from Marcus: {e}")
                # Log what we can calculate from task tracker as fallback
                calculated_velocity = task_tracker.calculate_velocity()
                avg_completion_time = task_tracker.get_avg_completion_time()

                experiment.log_velocity(calculated_velocity)
                experiment.log_metric(
                    "tasks_completed_total", len(task_tracker.completed_tasks)
                )
                experiment.log_metric(
                    "avg_completion_time_seconds", avg_completion_time
                )

                print("\n📊 Calculated Metrics (Fallback):")
                print(f"  Velocity: {calculated_velocity:.2f} tasks/hour")
                print(f"  Avg Completion Time: {avg_completion_time:.2f} seconds")
                print(f"  Completed: {len(task_tracker.completed_tasks)}")

            # Generate final summary
            summary = f"""
Twitter Swarm Experiment Summary
================================

Configuration:
- Agents: {num_agents}
- Complexity: {complexity}
- Blockers: {'Enabled' if enable_blockers else 'Disabled'}
- Artifacts: {'Enabled' if enable_artifacts else 'Disabled'}
- Decisions: {'Enabled' if enable_decisions else 'Disabled'}
- Context Requests: {'Enabled' if enable_context_requests else 'Disabled'}

Results tracked in MLflow.
Use 'mlflow ui' to view detailed metrics and compare runs.
            """

            experiment.end_run(summary=summary.strip())
            print(summary)

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback

            traceback.print_exc()
            experiment.end_run()


async def main() -> None:
    """Parse CLI arguments and run Twitter swarm workflow."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Twitter Swarm with MLflow Experiment Tracking"
    )
    parser.add_argument(
        "--num-agents",
        type=int,
        default=50,
        help="Number of agents to deploy (default: 50)",
    )
    parser.add_argument(
        "--complexity",
        choices=["prototype", "standard", "enterprise"],
        default="enterprise",
        help="Project complexity level",
    )
    parser.add_argument(
        "--enable-blockers", action="store_true", help="Enable blocker reporting"
    )
    parser.add_argument(
        "--enable-artifacts", action="store_true", help="Enable artifact logging"
    )
    parser.add_argument(
        "--enable-decisions", action="store_true", help="Enable decision logging"
    )
    parser.add_argument(
        "--enable-context-requests", action="store_true", help="Enable context requests"
    )
    parser.add_argument(
        "--enable-all", action="store_true", help="Enable all experimental conditions"
    )
    parser.add_argument(
        "--experiment-name", default="twitter-swarm-test", help="MLflow experiment name"
    )
    parser.add_argument("--run-name", help="Specific MLflow run name")

    args = parser.parse_args()

    # If --enable-all, enable all conditions
    if args.enable_all:
        enable_blockers = True
        enable_artifacts = True
        enable_decisions = True
        enable_context_requests = True
    else:
        enable_blockers = args.enable_blockers
        enable_artifacts = args.enable_artifacts
        enable_decisions = args.enable_decisions
        enable_context_requests = args.enable_context_requests

    await twitter_mlflow_workflow(
        num_agents=args.num_agents,
        complexity=args.complexity,
        enable_blockers=enable_blockers,
        enable_artifacts=enable_artifacts,
        enable_decisions=enable_decisions,
        enable_context_requests=enable_context_requests,
        experiment_name=args.experiment_name,
        run_name=args.run_name,
    )

    print("\n" + "=" * 70)
    print("📊 View results with: mlflow ui")
    print("   Then open: http://localhost:5000")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
