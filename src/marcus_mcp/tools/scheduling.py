"""
Scheduling and optimal agent calculation tools.

This module provides MCP tools for calculating optimal agent counts
using Critical Path Method (CPM) analysis on the unified dependency graph.
"""

import logging
from typing import Any, Dict

from src.marcus_mcp.coordinator.scheduler import calculate_optimal_agents

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
