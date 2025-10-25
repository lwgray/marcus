#!/usr/bin/env python3
"""
Quickly run through all available tasks on the board.

This script spawns multiple agents that request tasks, complete them immediately,
and move on to the next task. Useful for testing task flow and board behavior.
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.worker.inspector import Inspector


async def worker_agent(agent_num: int, max_tasks: int = 5):
    """
    Worker agent that requests and immediately completes tasks.

    Parameters
    ----------
    agent_num : int
        Agent number for unique ID
    max_tasks : int
        Maximum number of tasks to complete before stopping
    """
    agent_id = f"speed-worker-{agent_num:03d}"
    inspector = Inspector(connection_type="http")
    completed_count = 0

    print(f"\n[Agent {agent_num}] Starting...")

    try:
        async with inspector.connect(url="http://localhost:4298/mcp") as session:
            # Authenticate
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": agent_id,
                    "client_type": "agent",
                    "role": "software-engineer",
                    "metadata": {"speed_run": True},
                },
            )

            # Register
            await inspector.register_agent(
                agent_id=agent_id,
                name=f"Speed Worker {agent_num}",
                role="software-engineer",
                skills=["python", "design", "testing", "implementation"],
            )
            print(f"[Agent {agent_num}] ✅ Registered")

            # Work loop
            while completed_count < max_tasks:
                # Request task
                task_result = await inspector.request_next_task(agent_id)

                if not task_result.get("success"):
                    print(f"[Agent {agent_num}] No more tasks available")
                    break

                task = task_result.get("task", {})
                task_id = task.get("id", "")
                task_name = task.get("name", "")

                print(f"[Agent {agent_num}] 📥 Got: {task_name[:50]}...")

                # Report 25% progress
                await inspector.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="in_progress",
                    progress=25,
                    message="Started work",
                )
                await asyncio.sleep(0.5)

                # Report 50% progress
                await inspector.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="in_progress",
                    progress=50,
                    message="Halfway done",
                )
                await asyncio.sleep(0.5)

                # Report 75% progress
                await inspector.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="in_progress",
                    progress=75,
                    message="Almost done",
                )
                await asyncio.sleep(0.5)

                # Complete task
                await inspector.report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status="completed",
                    progress=100,
                    message="Task completed successfully",
                )
                completed_count += 1
                print(
                    f"[Agent {agent_num}] ✅ Completed: {task_name[:50]}... ({completed_count}/{max_tasks})"
                )

                await asyncio.sleep(0.5)

            print(f"[Agent {agent_num}] 🏁 Finished! Completed {completed_count} tasks")

    except Exception as e:
        print(f"[Agent {agent_num}] ❌ Error: {e}")
        import traceback

        traceback.print_exc()


async def main(num_agents: int = 3, tasks_per_agent: int = 10):
    """
    Spawn multiple agents to run through the board quickly.

    Parameters
    ----------
    num_agents : int
        Number of parallel agents to spawn
    tasks_per_agent : int
        Maximum number of tasks each agent should complete
    """
    print("🚀 Speed Run Through Board")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  Agents: {num_agents}")
    print(f"  Tasks per agent: {tasks_per_agent}")
    print(f"  Max total tasks: {num_agents * tasks_per_agent}")
    print("=" * 70)

    workers = [
        worker_agent(i, max_tasks=tasks_per_agent) for i in range(1, num_agents + 1)
    ]

    # Run all agents concurrently
    await asyncio.gather(*workers)

    print("\n" + "=" * 70)
    print("✅ Speed run complete!")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Quickly run through all tasks on the board with multiple agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use defaults (3 agents, 10 tasks each)
  python3 run_through_board.py

  # Run with 5 agents, 20 tasks each
  python3 run_through_board.py --agents 5 --tasks 20

  # Single agent doing 50 tasks
  python3 run_through_board.py -a 1 -t 50
        """,
    )

    parser.add_argument(
        "-a",
        "--agents",
        type=int,
        default=3,
        help="Number of parallel agents to spawn (default: 3)",
    )

    parser.add_argument(
        "-t",
        "--tasks",
        type=int,
        default=10,
        help="Maximum number of tasks per agent (default: 10)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.agents < 1:
        parser.error("Number of agents must be at least 1")
    if args.tasks < 1:
        parser.error("Number of tasks must be at least 1")

    asyncio.run(main(num_agents=args.agents, tasks_per_agent=args.tasks))
