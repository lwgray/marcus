"""
Verify Project Completion: Did we build what we said we would build?

This script analyzes project execution to show what was completed,
what's blocked, and overall project health.

Note: Full spec comparison requires original task list. This version
analyzes actual execution data available from Phase 1.

Usage:
    python examples/verify_project_completion.py <project_id>
    python examples/verify_project_completion.py --list
"""

import asyncio
import sys

from src.analysis.aggregator import ProjectHistoryAggregator
from src.analysis.query_api import ProjectHistoryQuery


async def verify_project_completion(project_id: str) -> None:
    """
    Analyze project execution and completion status.

    Parameters
    ----------
    project_id : str
        The project to verify
    """
    # Initialize query API
    aggregator = ProjectHistoryAggregator()
    query = ProjectHistoryQuery(aggregator)

    print("=" * 80)
    print(f"PROJECT COMPLETION ANALYSIS: {project_id}")
    print("=" * 80)

    # =========================================================================
    # STEP 1: Get project summary
    # =========================================================================
    print("\n📊 PROJECT SUMMARY")
    print("-" * 80)

    try:
        summary = await query.get_project_summary(project_id)
    except Exception as e:
        print(f"❌ Error loading project: {e}")
        print("\nMake sure the project has history data in:")
        print("  data/project_history/{project_id}/")
        return

    print(f"Project: {summary['project_name']}")
    print(f"Total Tasks: {summary['total_tasks']}")
    print(f"Completed: {summary['completed_tasks']}")
    print(f"Blocked: {summary['blocked_tasks']}")
    print(f"Completion Rate: {summary['completion_rate']}%")
    print(f"Duration: {summary['project_duration_hours']:.1f} hours")
    print(f"Active Agents: {summary['active_agents']}")
    print(f"Decisions Made: {summary['total_decisions']}")
    print(f"Artifacts Produced: {summary['total_artifacts']}")

    # =========================================================================
    # STEP 2: Completed tasks breakdown
    # =========================================================================
    print("\n✅ COMPLETED TASKS")
    print("-" * 80)

    completed_tasks = await query.find_tasks_by_status(project_id, "completed")

    if completed_tasks:
        print(f"\nTotal: {len(completed_tasks)} tasks\n")
        for i, task in enumerate(completed_tasks[:10], 1):  # Show first 10
            print(f"{i:2}. {task.name}")
            if task.assigned_to:
                print(f"    Agent: {task.assigned_to}")
            if task.actual_hours:
                print(f"    Time: {task.actual_hours:.1f} hours")
        if len(completed_tasks) > 10:
            print(f"\n... and {len(completed_tasks) - 10} more")
    else:
        print("No completed tasks found.")

    # =========================================================================
    # STEP 3: Blocked tasks analysis
    # =========================================================================
    print("\n⚠️  BLOCKED TASKS")
    print("-" * 80)

    blocked_tasks = await query.find_blocked_tasks(project_id)

    if blocked_tasks:
        print(f"\nTotal: {len(blocked_tasks)} tasks with blockers\n")
        for i, task in enumerate(blocked_tasks[:5], 1):  # Show first 5
            print(f"{i}. {task.name}")
            print(f"   Blockers: {len(task.blockers_reported)}")
            for blocker in task.blockers_reported[:2]:  # First 2 blockers
                desc = blocker.get(
                    "description", blocker.get("blocker_description", "Unknown")
                )
                print(f"     - {desc}")
            print()
    else:
        print("✅ No blocked tasks!")

    # =========================================================================
    # STEP 4: In-progress tasks
    # =========================================================================
    print("\n🔨 IN-PROGRESS TASKS")
    print("-" * 80)

    in_progress = await query.find_tasks_by_status(project_id, "in_progress")

    if in_progress:
        print(f"\nTotal: {len(in_progress)} tasks\n")
        for i, task in enumerate(in_progress[:5], 1):
            print(f"{i}. {task.name}")
            if task.assigned_to:
                print(f"   Agent: {task.assigned_to}")
    else:
        print("No tasks currently in progress.")

    # =========================================================================
    # STEP 5: Agent performance
    # =========================================================================
    print("\n👥 AGENT PERFORMANCE")
    print("-" * 80)

    history = await query.get_project_history(project_id)

    if history.agents:
        print(f"\nTotal Agents: {len(history.agents)}\n")
        for agent in history.agents[:5]:  # Show first 5
            metrics = await query.get_agent_performance_metrics(
                project_id, agent.agent_id
            )
            print(f"Agent: {agent.agent_id}")
            print(f"  Completed: {metrics['tasks_completed']}")
            print(f"  Blocked: {metrics['tasks_blocked']}")
            print(f"  Avg Hours/Task: {metrics['avg_task_hours']:.1f}")
            print(f"  Decisions: {metrics['decisions_made']}")
            print(f"  Artifacts: {metrics['artifacts_produced']}")
            print()
    else:
        print("No agent data available.")

    # =========================================================================
    # STEP 6: Deliverables
    # =========================================================================
    print("\n📦 DELIVERABLES")
    print("-" * 80)

    specs = await query.find_artifacts_by_type(project_id, "specification")
    designs = await query.find_artifacts_by_type(project_id, "design")
    apis = await query.find_artifacts_by_type(project_id, "api")

    print("\nArtifacts Produced:")
    print(f"  Specifications: {len(specs)}")
    print(f"  Design Docs: {len(designs)}")
    print(f"  API Docs: {len(apis)}")
    print(f"  Total: {summary['total_artifacts']}")

    if specs:
        print("\n  Key Specifications:")
        for spec in specs[:3]:
            print(f"    - {spec.filename}")

    # =========================================================================
    # STEP 7: Architectural decisions
    # =========================================================================
    print("\n🔬 ARCHITECTURAL DECISIONS")
    print("-" * 80)

    all_decisions = history.decisions

    if all_decisions:
        print(f"\nTotal Decisions: {len(all_decisions)}\n")
        for i, decision in enumerate(all_decisions[:5], 1):
            print(f"{i}. {decision.what}")
            print(f"   Why: {decision.why}")
            print(f"   Agent: {decision.agent_id}")
            if decision.affected_tasks:
                print(f"   Affects: {len(decision.affected_tasks)} tasks")
            print()
    else:
        print("No architectural decisions logged.")

    # =========================================================================
    # FINAL VERDICT
    # =========================================================================
    print("=" * 80)
    print("🎯 PROJECT HEALTH")
    print("=" * 80)

    completion_rate = summary["completion_rate"]

    if completion_rate >= 90:
        verdict = "✅ EXCELLENT"
        health = "Project is nearly complete!"
    elif completion_rate >= 75:
        verdict = "👍 GOOD"
        health = "Most work is done, minor cleanup remaining."
    elif completion_rate >= 50:
        verdict = "⚠️  FAIR"
        health = "Halfway there, still significant work ahead."
    else:
        verdict = "❌ NEEDS ATTENTION"
        health = "Project is behind, needs focus."

    print(f"\n{verdict}")
    print(f"{health}\n")
    print(f"Completion Rate: {completion_rate:.1f}%")
    print(f"Tasks: {summary['completed_tasks']}/{summary['total_tasks']}")
    print(f"Blocked: {len(blocked_tasks)} tasks")
    print(f"Duration: {summary['project_duration_hours']:.1f} hours")

    print("\n" + "=" * 80)


async def list_available_projects() -> None:
    """List all projects with history data."""
    aggregator = ProjectHistoryAggregator()
    projects = aggregator.history_persistence.list_projects()

    print("\n📁 Available Projects:")
    print("-" * 80)

    if not projects:
        print("No projects found with history data.")
        print("\nProjects are stored in: data/project_history/")
        print("\nTo populate history:")
        print("  1. Run a project with Marcus")
        print("  2. Use log_decision and log_artifact MCP tools")
        print("  3. History will be automatically saved")
        return

    for project_id in projects:
        # Try to get project name from snapshot
        snapshot = await aggregator.history_persistence.load_snapshot(project_id)
        project_name = snapshot.project_name if snapshot else project_id

        print(f"  • {project_id}")
        if snapshot:
            print(f"    Name: {project_name}")
            print(f"    Status: {snapshot.completion_status}")
            print(f"    Tasks: {snapshot.completed_tasks}/{snapshot.total_tasks}")

    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_project_completion.py <project_id>")
        print("\nOr to list available projects:")
        print("       python verify_project_completion.py --list")
        asyncio.run(list_available_projects())
        sys.exit(1)

    if sys.argv[1] == "--list":
        asyncio.run(list_available_projects())
    else:
        project_id = sys.argv[1]
        asyncio.run(verify_project_completion(project_id))
