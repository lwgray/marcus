"""
Board Health Analysis Tool for Marcus MCP.

This tool provides comprehensive analysis of the project board health,
detecting deadlocks, bottlenecks, and other issues that might prevent progress.
"""

import logging
from typing import Any, Dict, List, Tuple

from src.core.board_health_analyzer import BoardHealthAnalyzer
from src.logging.conversation_logger import log_thinking
from src.marcus_mcp.utils import serialize_for_mcp

logger = logging.getLogger(__name__)


async def check_board_health(state: Any) -> Dict[str, Any]:
    """
    Analyze overall board health and detect deadlocks.

    Performs comprehensive analysis including:
    - Skill mismatch detection
    - Circular dependency detection
    - Bottleneck identification
    - Chain block analysis
    - Agent workload analysis

    Parameters
    ----------
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dict with board health analysis results
    """
    try:
        # Initialize kanban if needed
        await state.initialize_kanban()

        log_thinking("marcus", "Analyzing board health and checking for deadlocks")

        # Get board health configuration
        health_config = {}

        # Check for project-specific config
        if hasattr(state, "project_registry") and state.project_registry:
            active_project = await state.project_registry.get_active_project()
            if active_project and hasattr(active_project, "board_health"):
                health_config = active_project.board_health

        # Fall back to global config
        if not health_config:
            health_config = state.config.get("board_health", {})

        # Create health analyzer
        analyzer = BoardHealthAnalyzer(
            state.kanban_client,
            stale_task_days=health_config.get("stale_task_days", 7),
            max_tasks_per_agent=health_config.get("max_tasks_per_agent", 3),
        )

        # Get current assignments
        active_assignments = {}
        for agent_id, assignment in state.agent_tasks.items():
            active_assignments[agent_id] = assignment.task_id

        # Perform health analysis
        health = await analyzer.analyze_board_health(
            state.agent_status, active_assignments
        )

        # Log critical issues
        critical_issues = [i for i in health.issues if i.severity.value == "critical"]
        if critical_issues:
            log_thinking(
                "marcus",
                f"Found {len(critical_issues)} critical issues!",
                {"critical_issues": [i.description for i in critical_issues]},
            )

        # Get lease statistics if available
        lease_stats = None
        if hasattr(state, "lease_manager") and state.lease_manager:
            lease_stats = state.lease_manager.get_lease_statistics()

        # Format response
        response = {
            "success": True,
            "health_score": health.health_score,
            "status": _get_health_status(health.health_score),
            "metrics": health.metrics,
            "issues": [
                {
                    "type": issue.type.value,
                    "severity": issue.severity.value,
                    "description": issue.description,
                    "affected_tasks": issue.affected_tasks,
                    "affected_agents": issue.affected_agents,
                    "recommendations": issue.recommendations,
                    "details": issue.details,
                }
                for issue in health.issues
            ],
            "recommendations": health.recommendations,
            "lease_statistics": lease_stats,
            "timestamp": health.timestamp.isoformat(),
        }

        # Add summary
        response["summary"] = _generate_health_summary(health)

        serialized = serialize_for_mcp(response)
        return dict(serialized) if isinstance(serialized, dict) else serialized

    except Exception as e:
        logger.error(f"Error analyzing board health: {e}")
        return {"success": False, "error": str(e)}


async def check_task_dependencies(task_id: str, state: Any) -> Dict[str, Any]:
    """
    Check dependencies for a specific task.

    Shows:
    - What this task depends on
    - What depends on this task
    - Whether dependencies form any cycles
    - Recommended completion order

    Parameters
    ----------
    task_id : str
        ID of the task to analyze
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dict with dependency analysis
    """
    try:
        # Initialize kanban if needed
        await state.initialize_kanban()

        # Get all tasks
        all_tasks = await state.kanban_client.get_all_tasks()
        task_map = {t.id: t for t in all_tasks}

        # Find the target task
        target_task = task_map.get(task_id)
        if not target_task:
            return {"success": False, "error": f"Task {task_id} not found"}

        # Find dependencies
        depends_on = []
        if target_task.dependencies:
            for dep_id in target_task.dependencies:
                dep_task = task_map.get(dep_id)
                if dep_task:
                    depends_on.append(
                        {
                            "id": dep_id,
                            "name": dep_task.name,
                            "status": dep_task.status.value,
                            "assigned_to": dep_task.assigned_to,
                        }
                    )

        # Find dependents
        depended_by = []
        for task in all_tasks:
            if task.dependencies and task_id in task.dependencies:
                depended_by.append(
                    {
                        "id": task.id,
                        "name": task.name,
                        "status": task.status.value,
                        "assigned_to": task.assigned_to,
                    }
                )

        # Check for cycles
        has_cycle, cycle_path = _check_for_cycle(task_id, task_map)

        # Calculate completion order
        completion_order = _calculate_completion_order(task_id, task_map)

        response = {
            "success": True,
            "task": {
                "id": target_task.id,
                "name": target_task.name,
                "status": target_task.status.value,
            },
            "depends_on": depends_on,
            "depended_by": depended_by,
            "has_circular_dependency": has_cycle,
            "cycle_path": cycle_path if has_cycle else None,
            "recommended_completion_order": completion_order,
            "analysis": {
                "is_bottleneck": len(depended_by) >= 3,
                "is_blocked": len(depends_on) > 0
                and any(d["status"] != "done" for d in depends_on),
                "blocking_count": len(depended_by),
                "dependency_depth": len(completion_order),
            },
        }

        serialized = serialize_for_mcp(response)
        return dict(serialized) if isinstance(serialized, dict) else serialized

    except Exception as e:
        logger.error(f"Error checking task dependencies: {e}")
        return {"success": False, "error": str(e)}


def _get_health_status(score: float) -> str:
    """Convert health score to status string."""
    if score >= 90:
        return "excellent"
    elif score >= 75:
        return "good"
    elif score >= 60:
        return "fair"
    elif score >= 40:
        return "poor"
    else:
        return "critical"


def _generate_health_summary(health: Any) -> str:
    """Generate a human-readable health summary."""
    status = _get_health_status(health.health_score)

    summary_parts = [
        f"Board health is {status} (score: {health.health_score:.0f}/100)."
    ]

    if health.issues:
        issue_counts: Dict[str, int] = {}
        for issue in health.issues:
            issue_type = issue.type.value
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

        summary_parts.append(
            f"Found {len(health.issues)} issues: "
            + ", ".join(f"{count} {type_}" for type_, count in issue_counts.items())
        )
    else:
        summary_parts.append("No major issues detected.")

    critical_count = health.metrics.get("critical_issues", 0)
    if critical_count > 0:
        summary_parts.append(
            f"⚠️ {critical_count} critical issues require immediate attention!"
        )

    return " ".join(summary_parts)


def _check_for_cycle(
    start_task_id: str, task_map: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """Check if task is part of a dependency cycle."""
    visited = set()
    rec_stack = set()

    def dfs(task_id: str, path: List[str]) -> Tuple[bool, List[str]]:
        if task_id in rec_stack:
            # Found cycle
            cycle_start = path.index(task_id)
            return True, path[cycle_start:] + [task_id]

        if task_id in visited:
            return False, []

        visited.add(task_id)
        rec_stack.add(task_id)
        path.append(task_id)

        task = task_map.get(task_id)
        if task and task.dependencies:
            for dep_id in task.dependencies:
                has_cycle, cycle_path = dfs(dep_id, path.copy())
                if has_cycle:
                    return True, cycle_path

        rec_stack.remove(task_id)
        return False, []

    return dfs(start_task_id, [])


def _calculate_completion_order(
    task_id: str, task_map: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Calculate the order in which dependencies should be completed."""
    order = []
    visited = set()

    def visit(tid: str) -> None:
        if tid in visited:
            return
        visited.add(tid)

        task = task_map.get(tid)
        if task and task.dependencies:
            for dep_id in task.dependencies:
                visit(dep_id)

        order.append(
            {
                "id": tid,
                "name": task.name if task else "Unknown",
                "status": task.status.value if task else "unknown",
            }
        )

    visit(task_id)
    return order
