"""
MCP tool response logger for Marcus.

This module provides logging functionality specifically for MCP tool responses,
with emphasis on logging failures and their reasons to help diagnose issues
like dependency problems, skill mismatches, and agent availability.
"""

from typing import Any

from src.logging.conversation_logger import conversation_logger


def log_mcp_tool_response(
    tool_name: str,
    arguments: dict[str, Any],
    response: dict[str, Any],
) -> None:
    """
    Log MCP tool response with detailed failure analysis.

    This function logs all MCP tool responses, with special attention to
    failures (success=False). For failures, it categorizes the failure type
    and logs diagnostic context to help investigate issues.

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
    - Dependency-related failures are logged at CRITICAL level
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
        # Categorize and log failures
        _log_mcp_tool_failure(tool_name, arguments, response)


def _log_mcp_tool_failure(
    tool_name: str,
    arguments: dict[str, Any],
    response: dict[str, Any],
) -> None:
    """
    Log MCP tool failure with categorization and diagnostic context.

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
    blocking_task = response.get("blocking_task")

    # Categorize failure type
    failure_category = _categorize_failure(response)

    # Build context for logging
    context = {
        "tool_name": tool_name,
        "arguments": arguments,
        "error": error_msg,
        "failure_category": failure_category,
        "response": response,
    }

    # Determine log level based on failure category
    if failure_category == "dependency_issue":
        # Dependency issues are critical - need investigation
        conversation_logger.pm_logger.critical(
            "MCP tool failed due to dependency issue",
            **context,
        )

        # Log additional diagnostic info
        if blocking_task:
            conversation_logger.log_pm_thinking(
                "Dependency diagnostic: blocking task details",
                context={
                    "blocking_task": blocking_task,
                    "retry_after_seconds": response.get("retry_after_seconds"),
                },
            )
    elif failure_category == "agent_busy":
        # Agent busy is expected, log at WARNING
        conversation_logger.pm_logger.warning(
            "MCP tool failed: agent busy",
            **context,
        )
    elif failure_category == "no_suitable_tasks":
        # No suitable tasks is informational
        conversation_logger.pm_logger.warning(
            "MCP tool failed: no suitable tasks available",
            **context,
        )
    else:
        # Unknown failures warrant investigation
        conversation_logger.pm_logger.warning(
            f"MCP tool '{tool_name}' failed",
            **context,
        )

    # Log the decision context for better tracking
    conversation_logger.log_pm_decision(
        decision=f"MCP tool '{tool_name}' returned failure",
        rationale=f"{failure_category}: {error_msg}",
        decision_factors={
            "retry_reason": retry_reason,
            "failure_category": failure_category,
        },
    )


def _categorize_failure(response: dict[str, Any]) -> str:
    """
    Categorize MCP tool failure based on response content.

    Parameters
    ----------
    response : dict[str, Any]
        Failure response from the tool

    Returns
    -------
    str
        Failure category: 'dependency_issue', 'agent_busy',
        'no_suitable_tasks', or 'unknown'
    """
    error_msg = response.get("error", "").lower()
    retry_reason = response.get("retry_reason", "").lower()
    blocking_task = response.get("blocking_task")

    # Check for dependency-related keywords
    dependency_keywords = [
        "dependency",
        "dependencies",
        "waiting for",
        "blocked by",
        "incomplete",
        "circular",
    ]

    if blocking_task or any(kw in error_msg for kw in dependency_keywords):
        return "dependency_issue"

    if any(kw in retry_reason for kw in dependency_keywords):
        return "dependency_issue"

    # Check for agent busy indicators
    if "busy" in error_msg or "busy" in retry_reason:
        return "agent_busy"

    if "working on" in error_msg or "working on" in retry_reason:
        return "agent_busy"

    # Check for no suitable tasks
    if "no suitable" in error_msg or "no tasks" in error_msg:
        return "no_suitable_tasks"

    if "skills" in error_msg or "skill" in error_msg:
        return "no_suitable_tasks"

    return "unknown"


def log_request_next_task_failure(
    agent_id: str,
    response: dict[str, Any],
) -> None:
    """
    Specialized logger for request_next_task failures.

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
    This function provides additional context specific to task assignment
    failures, including dependency chain analysis when available.
    """
    log_mcp_tool_response(
        tool_name="request_next_task",
        arguments={"agent_id": agent_id},
        response=response,
    )

    # Additional diagnostic logging for dependency issues
    failure_category = _categorize_failure(response)
    if failure_category == "dependency_issue":
        conversation_logger.log_pm_thinking(
            f"Agent {agent_id} blocked by dependencies - "
            "investigate dependency chain",
            context={
                "agent_id": agent_id,
                "blocking_task": response.get("blocking_task"),
                "retry_after_seconds": response.get("retry_after_seconds"),
                "suggestion": "Check for circular dependencies or "
                "incomplete dependency chains",
            },
        )
