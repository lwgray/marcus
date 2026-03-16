"""
Example: How to use Phase 1 Project History Query API.

This script demonstrates querying project execution history
to answer questions like "Did we build what we said we would build?"
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path so we can import src modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.aggregator import ProjectHistoryAggregator  # noqa: E402
from src.analysis.query_api import ProjectHistoryQuery  # noqa: E402


async def main(project_id: str) -> None:
    """Demonstrate Phase 1 usage patterns."""
    # Initialize the query API
    aggregator = ProjectHistoryAggregator()
    query = ProjectHistoryQuery(aggregator)

    print("=" * 60)
    print("Phase 1: Project History Query Examples")
    print("=" * 60)

    # =========================================================================
    # 1. Get Project Summary
    # =========================================================================
    print("\n1. PROJECT SUMMARY")
    print("-" * 60)
    summary = await query.get_project_summary(project_id)
    print(f"Project: {summary['project_name']}")
    print(f"Total Tasks: {summary['total_tasks']}")
    print(f"Completed: {summary['completed_tasks']}")
    print(f"Blocked: {summary['blocked_tasks']}")
    print(f"Completion Rate: {summary['completion_rate']}%")
    print(f"Active Agents: {summary['active_agents']}")
    print(f"Total Decisions: {summary['total_decisions']}")
    print(f"Total Artifacts: {summary['total_artifacts']}")
    print(f"Duration: {summary['project_duration_hours']:.1f} hours")

    # =========================================================================
    # 2. Find Completed Tasks
    # =========================================================================
    print("\n2. COMPLETED TASKS")
    print("-" * 60)
    completed = await query.find_tasks_by_status(project_id, "completed")
    for task in completed[:5]:  # Show first 5
        print(f"  - {task.name}")
        print(f"    Status: {task.status}")
        print(f"    Agent: {task.assigned_to}")
        if task.actual_hours:
            print(f"    Time: {task.actual_hours:.1f} hours")

    # =========================================================================
    # 3. Find Blocked Tasks (requires attention)
    # =========================================================================
    print("\n3. BLOCKED TASKS (Require Attention)")
    print("-" * 60)
    blocked = await query.find_blocked_tasks(project_id)
    if blocked:
        for task in blocked:
            print(f"  - {task.name}")
            print(f"    Blockers: {task.blockers_reported}")
    else:
        print("  No blocked tasks!")

    # =========================================================================
    # 4. Search Recent Activity (last 7 days)
    # =========================================================================
    print("\n4. RECENT ACTIVITY (Last 7 Days)")
    print("-" * 60)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    recent_tasks = await query.find_tasks_in_timerange(project_id, week_ago, now)
    print(f"  Tasks in last 7 days: {len(recent_tasks)}")

    # =========================================================================
    # 5. Analyze Agent Performance
    # =========================================================================
    print("\n5. AGENT PERFORMANCE")
    print("-" * 60)
    # Get all agents from project history
    history = await query.get_project_history(project_id)
    for agent in history.agents[:3]:  # Show first 3 agents
        metrics = await query.get_agent_performance_metrics(project_id, agent.agent_id)
        print(f"  Agent: {agent.agent_id}")
        print(f"    Tasks Completed: {metrics['tasks_completed']}")
        print(f"    Avg Task Hours: {metrics['avg_task_hours']}")
        print(f"    Decisions Made: {metrics['decisions_made']}")
        print(f"    Artifacts Produced: {metrics['artifacts_produced']}")

    # =========================================================================
    # 6. Find Architectural Decisions
    # =========================================================================
    print("\n6. ARCHITECTURAL DECISIONS")
    print("-" * 60)
    # Get all decisions
    all_decisions = history.decisions
    for decision in all_decisions[:5]:  # Show first 5
        print(f"  - {decision.what}")
        print(f"    Why: {decision.why}")
        print(f"    Agent: {decision.agent_id}")
        print(f"    Task: {decision.task_id}")
        if decision.affected_tasks:
            print(f"    Affects: {len(decision.affected_tasks)} other tasks")

    # =========================================================================
    # 7. Find Artifacts by Type
    # =========================================================================
    print("\n7. ARTIFACTS PRODUCED")
    print("-" * 60)
    # Find all specification artifacts
    specs = await query.find_artifacts_by_type(project_id, "specification")
    print(f"  Specifications: {len(specs)}")
    for artifact in specs[:3]:  # Show first 3
        print(f"    - {artifact.filename}")
        print(f"      Path: {artifact.relative_path}")

    # Find all design artifacts
    designs = await query.find_artifacts_by_type(project_id, "design")
    print(f"  Design Docs: {len(designs)}")

    # =========================================================================
    # 8. Search Conversations
    # =========================================================================
    print("\n8. CONVERSATION SEARCH")
    print("-" * 60)
    # Search for conversations mentioning "API"
    api_messages = await query.search_conversations(project_id, keyword="API")
    print(f"  Messages mentioning 'API': {len(api_messages)}")

    # =========================================================================
    # 9. Analyze Task Dependencies
    # =========================================================================
    print("\n9. TASK DEPENDENCY ANALYSIS")
    print("-" * 60)
    # Pick a task with dependencies
    if history.tasks:
        sample_task = history.tasks[0]
        deps = await query.get_task_dependency_chain(project_id, sample_task.task_id)
        print(f"  Task: {sample_task.name}")
        print(f"  Depends on {len(deps)} other tasks:")
        for dep in deps[:3]:  # Show first 3
            print(f"    - {dep.name}")

    # =========================================================================
    # 10. Search Timeline Events
    # =========================================================================
    print("\n10. TIMELINE EVENTS")
    print("-" * 60)
    # Find all task_started events
    started_events = await query.search_timeline(project_id, event_type="task_started")
    print(f"  Tasks started: {len(started_events)}")

    # Find events from specific agent
    if history.agents:
        agent_id = history.agents[0].agent_id
        agent_events = await query.search_timeline(project_id, agent_id=agent_id)
        print(f"  Events from {agent_id}: {len(agent_events)}")

    print("\n" + "=" * 60)
    print("Phase 1 Query Examples Complete!")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query_project_history_example.py <project_id>")
        print("\nExample:")
        print("  python query_project_history_example.py <uuid>")
        sys.exit(1)

    project_id = sys.argv[1]
    asyncio.run(main(project_id))
