"""
MCP tool response logger for Marcus.

This module provides activity tracking for MCP tool responses, logging
when tools succeed or fail. It acts as a "table of contents" for MCP
tool activity, pointing operators to detailed diagnostic logs when needed.

For root cause analysis of failures (especially request_next_task), check
the Python logs (logs/marcus_*.log) for "Diagnostic Report" entries near
the failure timestamp.
"""

from typing import Any

from src.logging.conversation_logger import conversation_logger


def log_mcp_tool_response(
    tool_name: str,
    arguments: dict[str, Any],
    response: dict[str, Any],
) -> None:
    """
    Log MCP tool response for activity tracking.

    This function logs all MCP tool responses as an activity tracker,
    recording WHAT failed and WHEN. It does not attempt to determine
    WHY failures occurred (root cause analysis is in diagnostic logs).

    Parameters
    ----------
    tool_name : str
        Name of the MCP tool that was called
    arguments : dict[str, Any]
        Arguments passed to the tool
    response : dict[str, Any]
        Response returned by the tool

    Notes
    -----
    - Success cases are logged at DEBUG level
    - Failure cases are logged at WARNING level
    - For root cause analysis, check Python logs for "Diagnostic Report"
    """
    success = response.get("success", False)

    if success:
        # Log successful responses at DEBUG level
        conversation_logger.log_pm_thinking(
            f"MCP tool '{tool_name}' succeeded",
            context={
                "tool_name": tool_name,
                "arguments": arguments,
                "response": response,
            },
        )
    else:
        # Log failures without categorization
        _log_mcp_tool_failure(tool_name, arguments, response)


def _log_mcp_tool_failure(
    tool_name: str,
    arguments: dict[str, Any],
    response: dict[str, Any],
) -> None:
    """
    Log MCP tool failure for activity tracking.

    Records that a failure occurred without attempting to determine the
    root cause. For request_next_task failures, points operators to
    diagnostic logs for detailed analysis.

    Parameters
    ----------
    tool_name : str
        Name of the MCP tool that failed
    arguments : dict[str, Any]
        Arguments passed to the tool
    response : dict[str, Any]
        Failure response from the tool
    """
    error_msg = response.get("error", "Unknown error")
    retry_reason = response.get("retry_reason", "")

    # Build context for logging
    context = {
        "tool_name": tool_name,
        "arguments": arguments,
        "error": error_msg,
        "retry_reason": retry_reason,
        "response": response,
    }

    # Log the failure at WARNING level
    conversation_logger.pm_logger.warning(
        f"MCP tool '{tool_name}' returned failure",
        **context,
    )

    # For request_next_task, add pointer to diagnostic logs
    if tool_name == "request_next_task":
        conversation_logger.log_pm_thinking(
            "For root cause analysis of request_next_task failure, "
            "check Python logs (logs/marcus_*.log) for 'Diagnostic Report' "
            "entries near this timestamp",
            context={"hint": "Diagnostics run automatically when no tasks assignable"},
        )


def log_request_next_task_failure(
    agent_id: str,
    response: dict[str, Any],
) -> None:
    """
    Log request_next_task failures with diagnostic pointers.

    This is a convenience function specifically for the request_next_task
    tool, which is the most critical tool to monitor for failures.

    Parameters
    ----------
    agent_id : str
        ID of the agent requesting the task
    response : dict[str, Any]
        Failure response from request_next_task

    Notes
    -----
    Logs the failure and points to diagnostic logs for root cause analysis.
    The diagnostic system runs automatically when no tasks can be assigned.
    """
    log_mcp_tool_response(
        tool_name="request_next_task",
        arguments={"agent_id": agent_id},
        response=response,
    )
