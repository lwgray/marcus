#!/usr/bin/env python3
"""
Analyze 100 Independent Tasks with Scheduler.

This script loads the 100 pre-generated independent tasks and runs
the optimal agent calculation to verify the sweep-line algorithm works correctly.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.models import Priority, Task, TaskStatus  # noqa: E402
from src.marcus_mcp.coordinator.scheduler import calculate_optimal_agents  # noqa: E402


def load_tasks_from_json(json_path: Path) -> list[Task]:
    """Load Task objects from JSON file."""
    with open(json_path, "r") as f:
        tasks_data = json.load(f)

    tasks = []
    for task_dict in tasks_data:
        created_at = datetime.fromisoformat(task_dict["created_at"])
        updated_at = datetime.fromisoformat(task_dict["updated_at"])
        due_date = (
            datetime.fromisoformat(task_dict["due_date"])
            if task_dict["due_date"]
            else None
        )

        task = Task(
            id=task_dict["id"],
            name=task_dict["name"],
            description=task_dict["description"],
            status=TaskStatus(task_dict["status"]),
            priority=Priority(task_dict["priority"]),
            assigned_to=task_dict["assigned_to"],
            created_at=created_at,
            updated_at=updated_at,
            due_date=due_date,
            estimated_hours=task_dict["estimated_hours"],
            actual_hours=task_dict["actual_hours"],
            dependencies=task_dict["dependencies"],
            labels=task_dict["labels"],
            project_id=task_dict["project_id"],
            project_name=task_dict["project_name"],
            is_subtask=task_dict["is_subtask"],
            parent_task_id=task_dict["parent_task_id"],
            subtask_index=task_dict["subtask_index"],
        )
        tasks.append(task)

    return tasks


def main() -> None:
    """Analyze 100 independent tasks."""
    print("\n" + "=" * 70)
    print("ANALYZING 100 INDEPENDENT TASKS")
    print("=" * 70)

    # Load tasks
    json_path = Path(__file__).parent / "100_independent_tasks.json"
    if not json_path.exists():
        print(f"\n❌ Task file not found: {json_path}")
        print("   Run generate_100_tasks_direct.py first!")
        sys.exit(1)

    print(f"\n📂 Loading tasks from: {json_path}")
    tasks = load_tasks_from_json(json_path)
    print(f"✅ Loaded {len(tasks)} tasks")

    # Verify all tasks are independent
    tasks_with_deps = [t for t in tasks if t.dependencies]
    print("\n🔍 Verifying independence:")
    print(f"   Tasks with dependencies: {len(tasks_with_deps)}")
    print(f"   Independent tasks: {len(tasks) - len(tasks_with_deps)}")

    if tasks_with_deps:
        print(f"\n⚠️  WARNING: Found {len(tasks_with_deps)} tasks with dependencies!")
        print("   This test expects ALL tasks to be independent.")
    else:
        print(f"   ✅ ALL {len(tasks)} tasks are independent!")

    # Run optimal agent calculation
    print("\n📊 Running optimal agent calculation...")
    print("   (Testing sweep-line algorithm fix)")

    schedule = calculate_optimal_agents(tasks)

    print("\n" + "=" * 70)
    print("OPTIMAL AGENT ANALYSIS RESULTS")
    print("=" * 70)

    print("\n📊 Scheduling Analysis:")
    print(f"   Total tasks: {len(tasks)}")
    print(f"   Workable tasks (subtasks): {len([t for t in tasks if t.is_subtask])}")
    print(f"   Max parallelism: {schedule.max_parallelism}")
    print(f"   Optimal agents: {schedule.optimal_agents}")
    print(f"   Critical path: {schedule.critical_path_hours:.2f} hours")
    print(f"   Single agent time: {schedule.single_agent_hours:.2f} hours")
    print(f"   Efficiency gain: {schedule.efficiency_gain:.1%}")

    # Verify correctness
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    expected_max_parallelism = len([t for t in tasks if t.is_subtask])
    actual_max_parallelism = schedule.max_parallelism

    print("\n🧪 Expected Results:")
    print("   Since ALL tasks are independent with NO dependencies:")
    print(f"   - Expected max_parallelism: {expected_max_parallelism}")
    print(f"   - Expected optimal_agents: {expected_max_parallelism}")

    print("\n📈 Actual Results:")
    print(f"   - Actual max_parallelism: {actual_max_parallelism}")
    print(f"   - Actual optimal_agents: {schedule.optimal_agents}")

    if actual_max_parallelism == expected_max_parallelism:
        print("\n✅ SWEEP-LINE ALGORITHM WORKS CORRECTLY!")
        print(
            f"   All {expected_max_parallelism} tasks detected as running in parallel."
        )
        print("   This proves the bug fix handles truly independent tasks.")
    else:
        print("\n❌ UNEXPECTED RESULT!")
        print(
            f"   Expected {expected_max_parallelism} but got {actual_max_parallelism}"
        )
        print("   The scheduler may not be handling independent tasks correctly.")

    # Show timeline
    if schedule.parallel_opportunities:
        print("\n📈 Parallelism Timeline (showing first 10):")
        print("   Time (h) │ Tasks │ Utilization")
        print("   ─────────┼───────┼────────────")

        for opp in schedule.parallel_opportunities[:10]:
            time_h = opp["time"]
            count = opp["task_count"]
            util = opp["utilization_percent"]
            bar = "█" * min(int(util / 10), 10)
            print(f"   {time_h:>7.2f}  │  {count:>3}  │ {util:>3.0f}% {bar}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
