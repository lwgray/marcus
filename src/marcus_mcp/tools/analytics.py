"""
Analytics and metrics collection tools for Marcus MCP.

This module provides tools for collecting system metrics, agent performance data,
and project analytics for visualization in Seneca dashboards.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from mcp.types import Tool

from ...core.models import TaskStatus


async def get_system_metrics(
    time_window: str = "1h",
    state: Any = None,
) -> Dict[str, Any]:
    """
    Get current system-wide metrics.

    Parameters
    ----------
    time_window : str
        Time window for metrics (1h, 24h, 7d, 30d)
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        System metrics including:
        - active_agents: number of active agents
        - total_throughput: tasks completed per hour
        - average_task_duration: mean time to complete tasks
        - system_health: overall health score
    """
    if not state:
        return {
            "success": False,
            "error": "Server state not available",
        }

    # Parse time window
    window_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = window_map.get(time_window, timedelta(hours=1))
    cutoff_time = datetime.now() - delta

    # Get all registered agents
    agents = []
    for project_id, context in state._project_contexts.items():
        if context.assignment_persistence:
            project_agents = context.assignment_persistence.get_all_agents()
            agents.extend(project_agents)

    # Count active agents (those with recent activity)
    active_agents = 0
    for agent in agents:
        if hasattr(agent, "last_activity") and agent.last_activity > cutoff_time:
            active_agents += 1

    # Calculate throughput
    completed_tasks = 0
    total_duration = 0
    task_count = 0

    for project_id, context in state._project_contexts.items():
        if context.kanban_provider:
            tasks = await context.kanban_provider.get_tasks()
            for task in tasks:
                if task.status == TaskStatus.DONE:
                    if hasattr(task, "updated_at") and task.updated_at > cutoff_time:
                        completed_tasks += 1
                        if hasattr(task, "actual_hours"):
                            total_duration += task.actual_hours
                            task_count += 1

    # Calculate metrics
    hours_in_window = delta.total_seconds() / 3600
    throughput = completed_tasks / max(1, hours_in_window)
    avg_duration = total_duration / max(1, task_count) if task_count > 0 else 0

    # Simple health score calculation
    health_score = min(
        100,
        (
            (active_agents * 10)  # More agents = better
            + (min(throughput * 5, 50))  # Good throughput
            + (40 if avg_duration < 24 else 20)  # Fast completion
        ),
    )

    return {
        "success": True,
        "time_window": time_window,
        "metrics": {
            "active_agents": active_agents,
            "total_agents": len(agents),
            "total_throughput": round(throughput, 2),
            "completed_tasks": completed_tasks,
            "average_task_duration": round(avg_duration, 1),
            "system_health": round(health_score, 1),
        },
        "timestamp": datetime.now().isoformat(),
    }


async def get_agent_metrics(
    agent_id: str,
    time_window: str = "7d",
    state: Any = None,
) -> Dict[str, Any]:
    """
    Get performance metrics for a specific agent.

    Parameters
    ----------
    agent_id : str
        ID of the agent to analyze
    time_window : str
        Time window for metrics (1h, 24h, 7d, 30d)
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Agent metrics including:
        - utilization: percentage of time working
        - tasks_completed: number of tasks finished
        - success_rate: percentage of successful completions
        - average_task_time: mean completion time
        - skill_distribution: breakdown by task type
    """
    if not state:
        return {
            "success": False,
            "error": "Server state not available",
        }

    # Find agent across all projects
    agent = None
    agent_context = None
    for project_id, context in state._project_contexts.items():
        if context.assignment_persistence:
            agent = context.assignment_persistence.get_agent(agent_id)
            if agent:
                agent_context = context
                break

    if not agent:
        return {
            "success": False,
            "error": f"Agent {agent_id} not found",
        }

    # Parse time window
    window_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = window_map.get(time_window, timedelta(days=7))
    cutoff_time = datetime.now() - delta

    # Get agent's task history
    all_tasks = await agent_context.kanban_provider.get_tasks()
    agent_tasks = [t for t in all_tasks if t.assigned_to == agent_id]

    # Calculate metrics
    completed_tasks = 0
    successful_tasks = 0
    total_time = 0
    skill_counts: Dict[str, int] = {}
    active_time = 0

    for task in agent_tasks:
        if hasattr(task, "updated_at") and task.updated_at > cutoff_time:
            if task.status == TaskStatus.DONE:
                completed_tasks += 1
                successful_tasks += 1
                if hasattr(task, "actual_hours"):
                    total_time += task.actual_hours
                    active_time += task.actual_hours

                # Track skills/labels
                for label in task.labels or []:
                    skill_counts[label] = skill_counts.get(label, 0) + 1

            elif task.status == TaskStatus.BLOCKED:
                # Blocked tasks count against success rate
                pass

    # Calculate utilization (assume 8 hour work days)
    work_days = delta.days or 1
    available_hours = work_days * 8
    utilization = min(100, (active_time / available_hours) * 100)

    # Success rate
    total_assigned = len(
        [
            t
            for t in agent_tasks
            if hasattr(t, "updated_at") and t.updated_at > cutoff_time
        ]
    )
    success_rate = (successful_tasks / max(1, total_assigned)) * 100

    # Average task time
    avg_task_time = total_time / max(1, completed_tasks)

    return {
        "success": True,
        "agent_id": agent_id,
        "time_window": time_window,
        "metrics": {
            "utilization": round(utilization, 1),
            "tasks_completed": completed_tasks,
            "tasks_assigned": total_assigned,
            "success_rate": round(success_rate, 1),
            "average_task_time": round(avg_task_time, 1),
            "total_hours_worked": round(active_time, 1),
            "skill_distribution": skill_counts,
        },
        "timestamp": datetime.now().isoformat(),
    }


async def get_project_metrics(
    project_id: Optional[str] = None,
    time_window: str = "7d",
    state: Any = None,
) -> Dict[str, Any]:
    """
    Get metrics for a specific project.

    Parameters
    ----------
    project_id : Optional[str]
        Project ID (uses current if not provided)
    time_window : str
        Time window for metrics (1h, 24h, 7d, 30d)
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Project metrics including:
        - velocity: tasks completed per day
        - progress_percentage: overall completion
        - blocked_task_ratio: percentage of blocked tasks
        - health_score: overall project health
        - burndown_data: completion trend
    """
    if not project_id and state.current_project:
        project_id = state.current_project.id

    if not project_id:
        return {
            "success": False,
            "error": "No project specified or active",
        }

    context = state.get_project_context(project_id)
    if not context:
        return {
            "success": False,
            "error": f"Project {project_id} not found",
        }

    # Parse time window
    window_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = window_map.get(time_window, timedelta(days=7))
    cutoff_time = datetime.now() - delta

    # Get all tasks
    tasks = await context.kanban_provider.get_tasks()

    # Calculate metrics
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.status == TaskStatus.DONE])
    blocked_tasks = len([t for t in tasks if t.status == TaskStatus.BLOCKED])
    in_progress_tasks = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])

    # Calculate velocity (tasks completed in time window)
    recent_completions = 0
    burndown_data = []

    # Group completions by day for burndown
    daily_completions: Dict[Any, int] = {}

    for task in tasks:
        if task.status == TaskStatus.DONE:
            if hasattr(task, "updated_at") and task.updated_at > cutoff_time:
                recent_completions += 1
                date_key = task.updated_at.date()
                daily_completions[date_key] = daily_completions.get(date_key, 0) + 1

    # Calculate velocity
    days_in_window = max(1, delta.days)
    velocity = recent_completions / days_in_window

    # Progress percentage
    progress = (completed_tasks / max(1, total_tasks)) * 100

    # Blocked ratio
    active_tasks = total_tasks - completed_tasks
    blocked_ratio = (
        (blocked_tasks / max(1, active_tasks)) * 100 if active_tasks > 0 else 0
    )

    # Health score calculation
    health_score = 100
    if blocked_ratio > 20:
        health_score -= 20
    if blocked_ratio > 40:
        health_score -= 20
    if velocity < 1:
        health_score -= 20
    if progress < 20 and days_in_window > 7:
        health_score -= 20

    # Build burndown data
    current_date = datetime.now().date()
    remaining = total_tasks
    for i in range(days_in_window):
        date = current_date - timedelta(days=days_in_window - i - 1)
        completed_on_date = daily_completions.get(date, 0)
        remaining -= completed_on_date
        burndown_data.append(
            {
                "date": date.isoformat(),
                "remaining_tasks": max(0, remaining),
                "completed_on_date": completed_on_date,
            }
        )

    return {
        "success": True,
        "project_id": project_id,
        "project_name": context.project_name,
        "time_window": time_window,
        "metrics": {
            "velocity": round(velocity, 2),
            "progress_percentage": round(progress, 1),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "blocked_tasks": blocked_tasks,
            "blocked_task_ratio": round(blocked_ratio, 1),
            "health_score": round(health_score, 1),
            "burndown_data": burndown_data,
        },
        "timestamp": datetime.now().isoformat(),
    }


async def get_task_metrics(
    time_window: str = "30d",
    group_by: str = "status",
    state: Any = None,
) -> Dict[str, Any]:
    """
    Get aggregated task metrics across all projects.

    Parameters
    ----------
    time_window : str
        Time window for metrics (1h, 24h, 7d, 30d)
    group_by : str
        Grouping field (status, priority, assignee, label)
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Task metrics grouped by specified field
    """
    if not state:
        return {
            "success": False,
            "error": "Server state not available",
        }

    # Parse time window
    window_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = window_map.get(time_window, timedelta(days=30))
    cutoff_time = datetime.now() - delta

    # Collect tasks from all projects
    all_tasks = []
    for project_id, context in state._project_contexts.items():
        if context.kanban_provider:
            tasks = await context.kanban_provider.get_tasks()
            all_tasks.extend(tasks)

    # Group tasks
    grouped_metrics: Dict[str, Dict[str, Any]] = {}

    for task in all_tasks:
        # Skip old tasks
        if hasattr(task, "updated_at") and task.updated_at < cutoff_time:
            continue

        # Determine group key
        if group_by == "status":
            key = (
                task.status.value if hasattr(task.status, "value") else str(task.status)
            )
        elif group_by == "priority":
            key = (
                task.priority.value
                if hasattr(task.priority, "value")
                else str(task.priority)
            )
        elif group_by == "assignee":
            key = task.assigned_to or "unassigned"
        elif group_by == "label":
            # Tasks can have multiple labels
            for label in task.labels or ["unlabeled"]:
                if label not in grouped_metrics:
                    grouped_metrics[label] = {
                        "count": 0,
                        "total_hours": 0,
                        "completed": 0,
                        "blocked": 0,
                    }
                grouped_metrics[label]["count"] += 1
                if task.status == TaskStatus.DONE:
                    grouped_metrics[label]["completed"] += 1
                    if hasattr(task, "actual_hours"):
                        grouped_metrics[label]["total_hours"] += task.actual_hours
                elif task.status == TaskStatus.BLOCKED:
                    grouped_metrics[label]["blocked"] += 1
            continue
        else:
            key = "unknown"

        # Initialize group if needed
        if key not in grouped_metrics:
            grouped_metrics[key] = {
                "count": 0,
                "total_hours": 0,
                "completed": 0,
                "blocked": 0,
            }

        # Update metrics
        grouped_metrics[key]["count"] += 1
        if task.status == TaskStatus.DONE:
            grouped_metrics[key]["completed"] += 1
            if hasattr(task, "actual_hours"):
                grouped_metrics[key]["total_hours"] += task.actual_hours
        elif task.status == TaskStatus.BLOCKED:
            grouped_metrics[key]["blocked"] += 1

    # Calculate percentages
    for key, metrics in grouped_metrics.items():
        metrics["completion_rate"] = round(
            (metrics["completed"] / max(1, metrics["count"])) * 100, 1
        )
        metrics["blockage_rate"] = round(
            (metrics["blocked"] / max(1, metrics["count"])) * 100, 1
        )
        metrics["average_hours"] = (
            round(metrics["total_hours"] / max(1, metrics["completed"]), 1)
            if metrics["completed"] > 0
            else 0
        )

    return {
        "success": True,
        "time_window": time_window,
        "group_by": group_by,
        "metrics": grouped_metrics,
        "total_tasks": sum(m["count"] for m in grouped_metrics.values()),
        "timestamp": datetime.now().isoformat(),
    }


# Tool definitions for MCP
analytics_tools = [
    Tool(
        name="get_system_metrics",
        description="Get current system-wide performance metrics",
        inputSchema={
            "type": "object",
            "properties": {
                "time_window": {
                    "type": "string",
                    "description": "Time window: 1h, 24h, 7d, 30d",
                    "default": "1h",
                    "enum": ["1h", "24h", "7d", "30d"],
                },
            },
        },
    ),
    Tool(
        name="get_agent_metrics",
        description="Get performance metrics for a specific agent",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to analyze",
                },
                "time_window": {
                    "type": "string",
                    "description": "Time window: 1h, 24h, 7d, 30d",
                    "default": "7d",
                    "enum": ["1h", "24h", "7d", "30d"],
                },
            },
            "required": ["agent_id"],
        },
    ),
    Tool(
        name="get_project_metrics",
        description="Get metrics for a project including velocity and health",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project ID (uses current if not provided)",
                },
                "time_window": {
                    "type": "string",
                    "description": "Time window: 1h, 24h, 7d, 30d",
                    "default": "7d",
                    "enum": ["1h", "24h", "7d", "30d"],
                },
            },
        },
    ),
    Tool(
        name="get_task_metrics",
        description="Get aggregated task metrics grouped by various fields",
        inputSchema={
            "type": "object",
            "properties": {
                "time_window": {
                    "type": "string",
                    "description": "Time window: 1h, 24h, 7d, 30d",
                    "default": "30d",
                    "enum": ["1h", "24h", "7d", "30d"],
                },
                "group_by": {
                    "type": "string",
                    "description": "Group tasks by: status, priority, assignee, label",
                    "default": "status",
                    "enum": ["status", "priority", "assignee", "label"],
                },
            },
        },
    ),
]
