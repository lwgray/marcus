"""
Scheduling and optimal agent calculation tools.

This module provides MCP tools for calculating optimal agent counts
using Critical Path Method (CPM) analysis on the unified dependency graph.
"""

import logging
from typing import Any, Dict

from src.marcus_mcp.coordinator.scheduler import (
    calculate_optimal_agents,
    compute_active_layer_signal,
)

logger = logging.getLogger(__name__)


async def get_optimal_agent_count(
    include_details: bool = False,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Calculate optimal number of agents using CPM analysis.

    Uses the unified dependency graph (including parent tasks and subtasks)
    to determine the optimal agent count for maximum efficiency.

    Parameters
    ----------
    include_details : bool
        Whether to include detailed parallel opportunities
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Scheduling analysis with optimal agent count
    """
    if not state:
        return {
            "success": False,
            "error": "Server state not available",
        }

    try:
        # Get all tasks from project_tasks (includes parents + subtasks)
        tasks = getattr(state, "project_tasks", [])

        if not tasks:
            return {
                "success": True,
                "message": "No tasks available for scheduling",
                "optimal_agents": 0,
                "critical_path_hours": 0.0,
                "total_work_hours": 0.0,
            }

        # Calculate optimal agents using CPM
        schedule = calculate_optimal_agents(tasks)

        # Build response (explicitly typed to allow mixed value types)
        response: Dict[str, Any] = {
            "success": True,
            "optimal_agents": schedule.optimal_agents,
            "critical_path_hours": round(schedule.critical_path_hours, 2),
            "max_parallelism": schedule.max_parallelism,
            "estimated_completion_hours": round(schedule.estimated_completion_hours, 2),
            "single_agent_hours": round(schedule.single_agent_hours, 2),
            "efficiency_gain_percent": round(schedule.efficiency_gain * 100, 1),
            "total_tasks": len(tasks),
        }

        # Add detailed parallel opportunities if requested
        if include_details and schedule.parallel_opportunities:
            response["parallel_opportunities"] = schedule.parallel_opportunities

        logger.info(
            f"Calculated optimal agents: {schedule.optimal_agents} agents "
            f"for {len(tasks)} tasks "
            f"({schedule.efficiency_gain:.1%} efficiency gain)"
        )

        return response

    except ValueError as e:
        # Handle dependency cycles
        return {
            "success": False,
            "error": f"Cannot calculate optimal agents: {str(e)}",
            "suggestion": "Check for circular dependencies in your task graph",
        }
    except Exception as e:
        logger.error(f"Error calculating optimal agents: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to calculate optimal agents: {str(e)}",
        }


async def get_desired_agent_count(
    max_agents: int,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Return the layered-spawning signal for the runner controller (#595 Fix 3).

    Returns ``desired_agent_count`` (the width of the earliest DAG layer
    with incomplete work, capped at ``max_agents``) and ``unclaimed_tasks``
    (TODO tasks in that layer). The runner's spawn formula is
    ``max(0, min(desired_agent_count - live_agents, unclaimed_tasks))``.
    Both are 0 when every task is DONE.

    Recomputed from live board state on every call (no cursor — survives
    a rewind). Unlike ``get_optimal_agent_count`` (a one-shot whole-project
    estimate from unreliable time estimates), this is a live, structural,
    estimate-free signal meant to be polled repeatedly during a run.

    Parameters
    ----------
    max_agents : int
        Hard ceiling — the configured pool size acts as a cap.
    state : Any
        Marcus server state instance.

    Returns
    -------
    Dict[str, Any]
        ``{"success": True, "desired_agent_count": int, "unclaimed_tasks":
        int, ...}`` on success, or ``{"success": False, "error": str}``
        on failure.
    """
    if not state:
        return {
            "success": False,
            "error": "Server state not available",
        }

    try:
        tasks = getattr(state, "project_tasks", [])
        signal = compute_active_layer_signal(tasks, max_agents)
        return {
            "success": True,
            "desired_agent_count": signal.desired_agent_count,
            "unclaimed_tasks": signal.unclaimed_tasks,
            "max_agents": max_agents,
            "total_tasks": len(tasks),
        }

    except ValueError as e:
        # Dependency cycle — compute_dag_layers raises ValueError.
        return {
            "success": False,
            "error": f"Cannot compute desired agent count: {str(e)}",
            "suggestion": "Check for circular dependencies in your task graph",
        }
    except Exception as e:
        logger.error(f"Error computing desired agent count: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to compute desired agent count: {str(e)}",
        }
