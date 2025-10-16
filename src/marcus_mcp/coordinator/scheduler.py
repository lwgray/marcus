"""
Task Scheduling and Critical Path Method (CPM) for Marcus.

This module implements scheduling algorithms to calculate optimal agent counts
and project timelines using the Critical Path Method.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List

from src.core.models import Task, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class ProjectSchedule:
    """
    Scheduling analysis for optimal agent allocation.

    Parameters
    ----------
    optimal_agents : int
        Recommended number of agents for maximum efficiency
    critical_path_hours : float
        Duration of the longest dependency chain
    max_parallelism : int
        Maximum number of tasks that can run simultaneously
    estimated_completion_hours : float
        Expected project completion time with optimal agents
    single_agent_hours : float
        Total time if using only one agent
    efficiency_gain : float
        Percentage improvement from using optimal agents (0.0-1.0)
    parallel_opportunities : List[Dict[str, Any]]
        Time points where multiple tasks can run in parallel
    """

    optimal_agents: int
    critical_path_hours: float
    max_parallelism: int
    estimated_completion_hours: float
    single_agent_hours: float
    efficiency_gain: float
    parallel_opportunities: List[Dict[str, Any]] = field(default_factory=list)


def topological_sort(tasks: List[Task]) -> List[Task]:
    """
    Sort tasks in topological order (dependencies before dependents).

    Uses Kahn's algorithm for topological sorting.

    Parameters
    ----------
    tasks : List[Task]
        List of tasks to sort

    Returns
    -------
    List[Task]
        Tasks sorted in dependency order

    Raises
    ------
    ValueError
        If the dependency graph contains a cycle
    """
    # Build adjacency list and in-degree count
    task_map = {task.id: task for task in tasks}
    in_degree = {task.id: 0 for task in tasks}
    adjacency = defaultdict(list)

    for task in tasks:
        for dep_id in task.dependencies:
            if dep_id in task_map:
                adjacency[dep_id].append(task.id)
                in_degree[task.id] += 1

    # Start with tasks that have no dependencies
    queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
    sorted_tasks = []

    while queue:
        # Remove a task with no dependencies
        current_id = queue.pop(0)
        sorted_tasks.append(task_map[current_id])

        # Reduce in-degree for all dependents
        for dependent_id in adjacency[current_id]:
            in_degree[dependent_id] -= 1
            if in_degree[dependent_id] == 0:
                queue.append(dependent_id)

    # If we couldn't sort all tasks, there's a cycle
    if len(sorted_tasks) != len(tasks):
        raise ValueError(
            f"Dependency cycle detected: sorted {len(sorted_tasks)} of "
            f"{len(tasks)} tasks"
        )

    return sorted_tasks


def detect_cycles(tasks: List[Task]) -> bool:
    """
    Detect if there are any cycles in the task dependency graph.

    Uses depth-first search with colored nodes (white/gray/black).

    Parameters
    ----------
    tasks : List[Task]
        List of tasks to check

    Returns
    -------
    bool
        True if a cycle exists, False otherwise
    """
    task_map = {task.id: task for task in tasks}
    adjacency = defaultdict(list)

    # Build adjacency list
    for task in tasks:
        for dep_id in task.dependencies:
            if dep_id in task_map:
                adjacency[task.id].append(dep_id)

    # Color states: white (unvisited), gray (visiting), black (visited)
    WHITE, GRAY, BLACK = 0, 1, 2
    colors = {task.id: WHITE for task in tasks}

    def has_cycle_dfs(task_id: str) -> bool:
        """DFS helper to detect cycles."""
        if colors[task_id] == GRAY:
            # Back edge found - cycle exists
            return True
        if colors[task_id] == BLACK:
            # Already fully explored
            return False

        # Mark as currently visiting
        colors[task_id] = GRAY

        # Check all dependencies
        for dep_id in adjacency[task_id]:
            if has_cycle_dfs(dep_id):
                return True

        # Mark as fully explored
        colors[task_id] = BLACK
        return False

    # Check all tasks
    for task_id in colors:
        if colors[task_id] == WHITE:
            if has_cycle_dfs(task_id):
                return True

    return False


def calculate_task_times(tasks: List[Task]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate earliest start and finish times for each task using CPM.

    Parameters
    ----------
    tasks : List[Task]
        List of tasks (must be in topological order)

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Mapping of task_id to {start, finish, task} times
    """
    # Sort tasks topologically first
    try:
        sorted_tasks = topological_sort(tasks)
    except ValueError as e:
        logger.error(f"Cannot calculate task times: {e}")
        raise

    task_times: Dict[str, Dict[str, Any]] = {}

    for task in sorted_tasks:
        # Earliest start = latest finish of all dependencies
        earliest_start = 0.0
        if task.dependencies:
            dep_finish_times: List[float] = [
                task_times[dep_id]["finish"]
                for dep_id in task.dependencies
                if dep_id in task_times
            ]
            if dep_finish_times:
                earliest_start = max(dep_finish_times)

        task_times[task.id] = {
            "start": earliest_start,
            "finish": earliest_start + task.estimated_hours,
            "task": task,
        }

    return task_times


def calculate_optimal_agents(tasks: List[Task]) -> ProjectSchedule:
    """
    Calculate optimal number of agents using unified dependency graph.

    Uses critical path method (CPM) to find:
    1. Longest dependency chain (critical path)
    2. Maximum parallelism at any time point
    3. Optimal agent count for maximum efficiency

    Parameters
    ----------
    tasks : List[Task]
        All tasks in the project (parents + subtasks)

    Returns
    -------
    ProjectSchedule
        Complete scheduling analysis with optimal agent count

    Raises
    ------
    ValueError
        If dependency graph contains cycles
    """
    if not tasks:
        return ProjectSchedule(
            optimal_agents=0,
            critical_path_hours=0.0,
            max_parallelism=0,
            estimated_completion_hours=0.0,
            single_agent_hours=0.0,
            efficiency_gain=0.0,
            parallel_opportunities=[],
        )

    # Filter to only workable tasks:
    # 1. Subtasks only (not parent containers)
    # 2. Not already completed
    workable_tasks = [
        task for task in tasks if task.is_subtask and task.status != TaskStatus.DONE
    ]

    if not workable_tasks:
        logger.info("No workable tasks found (all tasks are parents or done)")
        return ProjectSchedule(
            optimal_agents=0,
            critical_path_hours=0.0,
            max_parallelism=0,
            estimated_completion_hours=0.0,
            single_agent_hours=0.0,
            efficiency_gain=0.0,
            parallel_opportunities=[],
        )

    # Check for cycles in workable tasks
    if detect_cycles(workable_tasks):
        raise ValueError("Dependency graph contains cycles - cannot schedule")

    # Calculate task times using workable tasks only
    task_times = calculate_task_times(workable_tasks)

    # Find critical path (longest path)
    critical_path = max(times["finish"] for times in task_times.values())

    # Find maximum parallelism (tasks that can run simultaneously)
    time_slices = defaultdict(list)
    for task_id, times in task_times.items():
        time_slices[times["start"]].append(task_id)

    max_parallelism = max(len(task_ids) for task_ids in time_slices.values())

    # Calculate total work from workable tasks only
    total_work = sum(task.estimated_hours for task in workable_tasks)

    # CRITICAL: Since agents cannot be dynamically scaled after start,
    # we must provision for PEAK parallelism, not average.
    # Idle agents have low cost (just polling), but insufficient agents
    # create a bottleneck that cannot be resolved without user intervention.
    #
    # Strategy: Use max_parallelism directly to handle peak demand.
    # Agents will idle during low-demand periods, which is acceptable.
    optimal = max_parallelism

    # Calculate efficiency gain
    single_agent_time = total_work
    multi_agent_time = critical_path
    efficiency_gain = (
        (single_agent_time - multi_agent_time) / single_agent_time
        if single_agent_time > 0
        else 0.0
    )

    # Find parallel opportunities (for reporting)
    # Include ALL time slices to show utilization over time
    parallel_opportunities = []
    for time, task_ids in sorted(time_slices.items()):
        parallel_opportunities.append(
            {
                "time": time,
                "task_count": len(task_ids),
                "utilization_percent": (
                    round((len(task_ids) / optimal * 100), 1) if optimal > 0 else 0
                ),
                "idle_agents": optimal - len(task_ids),
                "tasks": [task_times[tid]["task"].name for tid in task_ids],
            }
        )

    logger.info(
        f"Calculated optimal agents: {optimal} agents for "
        f"{len(workable_tasks)} workable tasks "
        f"({len(tasks) - len(workable_tasks)} parents/done filtered out)"
    )
    logger.info(f"Critical path: {critical_path}h, Max parallelism: {max_parallelism}")
    logger.info(
        f"Efficiency gain: {efficiency_gain:.1%} "
        f"({single_agent_time}h → {multi_agent_time}h)"
    )

    return ProjectSchedule(
        optimal_agents=optimal,
        critical_path_hours=critical_path,
        max_parallelism=max_parallelism,
        estimated_completion_hours=critical_path,
        single_agent_hours=single_agent_time,
        efficiency_gain=efficiency_gain,
        parallel_opportunities=parallel_opportunities,
    )
