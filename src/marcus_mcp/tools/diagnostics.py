"""
MCP Tools for Task Diagnostics.

Provides on-demand diagnostic tools for agents and users.
"""

import logging
from typing import Any, Dict

from src.core.models import TaskStatus
from src.core.task_diagnostics import (
    format_diagnostic_report,
    run_automatic_diagnostics,
)
from src.marcus_mcp.tools.project_stall_analyzer import (
    capture_project_stall_snapshot,
    replay_stall_conversations,
)

logger = logging.getLogger(__name__)


async def diagnose_project(state: Any) -> Dict[str, Any]:
    """
    Run comprehensive diagnostics on the current project.

    This tool can be called by agents or users to understand why
    tasks aren't being assigned or completed.

    Parameters
    ----------
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Diagnostic report with issues and recommendations
    """
    try:
        # Initialize kanban if needed
        await state.initialize_kanban()

        # Get current project state
        await state.refresh_project_state()

        if not state.project_tasks:
            return {
                "success": False,
                "error": "No project tasks found. Please select a project first.",
            }

        # Get completed and assigned task IDs
        completed_task_ids = {
            t.id for t in state.project_tasks if t.status == TaskStatus.DONE
        }
        assigned_task_ids = {a.task_id for a in state.agent_tasks.values()}

        # Run diagnostics
        diagnostic_report = await run_automatic_diagnostics(
            project_tasks=state.project_tasks,
            completed_task_ids=completed_task_ids,
            assigned_task_ids=assigned_task_ids,
        )

        # Format for output
        formatted_report = format_diagnostic_report(diagnostic_report)

        # Create structured response
        return {
            "success": True,
            "report": formatted_report,
            "summary": {
                "total_tasks": diagnostic_report.total_tasks,
                "available_tasks": diagnostic_report.available_tasks,
                "blocked_tasks": diagnostic_report.blocked_tasks,
                "issues_found": len(diagnostic_report.issues),
            },
            "issues": [
                {
                    "type": issue.issue_type,
                    "severity": issue.severity,
                    "description": issue.description,
                    "recommendation": issue.recommendation,
                    "affected_task_count": len(issue.affected_tasks),
                }
                for issue in diagnostic_report.issues
            ],
            "recommendations": diagnostic_report.recommendations,
            "task_breakdown": diagnostic_report.task_breakdown,
        }

    except Exception as e:
        logger.error(f"Error running diagnostics: {e}", exc_info=True)
        return {"success": False, "error": f"Diagnostic error: {str(e)}"}


async def diagnose_task_blockage(task_id: str, state: Any) -> Dict[str, Any]:
    """
    Diagnose why a specific task cannot be assigned.

    Parameters
    ----------
    task_id : str
        ID of the task to diagnose
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Diagnosis of why the task is blocked
    """
    try:
        # Initialize kanban if needed
        await state.initialize_kanban()

        # Get current project state
        await state.refresh_project_state()

        # Find the task
        task = next((t for t in state.project_tasks if t.id == task_id), None)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        # Check status
        if task.status != TaskStatus.TODO:
            return {
                "success": True,
                "blocked": False,
                "reason": f"Task status is {task.status.value}, not TODO",
            }

        # Check if already assigned
        assigned_task_ids = {a.task_id for a in state.agent_tasks.values()}
        if task_id in assigned_task_ids:
            return {
                "success": True,
                "blocked": True,
                "reason": "Task is already assigned to an agent",
            }

        # Check dependencies
        if not task.dependencies:
            return {
                "success": True,
                "blocked": False,
                "reason": "Task has no dependencies and should be available",
            }

        # Check which dependencies are incomplete
        completed_task_ids = {
            t.id for t in state.project_tasks if t.status == TaskStatus.DONE
        }
        incomplete_deps = [d for d in task.dependencies if d not in completed_task_ids]

        if not incomplete_deps:
            return {
                "success": True,
                "blocked": False,
                "reason": "All dependencies are complete",
            }

        # Get details about incomplete dependencies
        dep_details = []
        for dep_id in incomplete_deps:
            dep_task = next((t for t in state.project_tasks if t.id == dep_id), None)
            if dep_task:
                dep_details.append(
                    {
                        "id": dep_id,
                        "name": dep_task.name,
                        "status": dep_task.status.value,
                        "assigned_to": dep_task.assigned_to,
                    }
                )
            else:
                dep_details.append(
                    {
                        "id": dep_id,
                        "name": "Unknown",
                        "status": "missing",
                        "error": "Dependency task not found",
                    }
                )

        return {
            "success": True,
            "blocked": True,
            "reason": f"Blocked by {len(incomplete_deps)} incomplete dependencies",
            "incomplete_dependencies": dep_details,
            "recommendation": (
                f"Complete the {len(incomplete_deps)} blocking task(s) first: "
                + ", ".join([d["name"] for d in dep_details])
            ),
        }

    except Exception as e:
        logger.error(f"Error diagnosing task {task_id}: {e}", exc_info=True)
        return {"success": False, "error": f"Diagnostic error: {str(e)}"}


async def capture_stall_snapshot(
    state: Any,
    include_conversation_hours: int = 24,
) -> Dict[str, Any]:
    """
    Capture comprehensive snapshot when project development stalls.

    This tool captures:
    - Complete diagnostic report
    - Conversation history leading up to the stall
    - Task completion timeline
    - Dependency lock visualization
    - Early/anomalous task completions (e.g., "Project Success" completed early)
    - Actionable recommendations

    Parameters
    ----------
    state : Any
        Marcus server state instance
    include_conversation_hours : int
        Hours of conversation history to include (default: 24)

    Returns
    -------
    Dict[str, Any]
        Complete stall snapshot saved to file with analysis

    Examples
    --------
    >>> result = await capture_stall_snapshot(state)
    >>> print(result['summary'])
    {
        'stall_reason': 'all_tasks_blocked: All 5 TODO tasks blocked',
        'total_issues': 3,
        'dependency_locks': 5,
        'early_completions': 1,
        'recommendations_count': 7
    }
    """
    return await capture_project_stall_snapshot(state, include_conversation_hours)


async def replay_snapshot_conversations(
    snapshot_file: str,
) -> Dict[str, Any]:
    """
    Replay and analyze conversations from a stall snapshot.

    Analyzes conversation patterns to identify what led to the stall,
    including error patterns, repeated failures, and activity gaps.

    Parameters
    ----------
    snapshot_file : str
        Path to the stall snapshot JSON file

    Returns
    -------
    Dict[str, Any]
        Conversation analysis with timeline and key events

    Examples
    --------
    >>> result = await replay_snapshot_conversations(
    ...     "logs/stall_snapshots/stall_snapshot_20251006_220000.json"
    ... )
    >>> print(result['analysis']['key_events'])
    """
    return await replay_stall_conversations(snapshot_file)
