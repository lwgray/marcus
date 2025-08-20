"""
Tool group definitions for multi-endpoint Marcus server.

This module defines which tools are available on each endpoint
to provide role-based access without dynamic tool switching.
"""

from typing import Dict, List, Set

# Define tool groups for each endpoint
TOOL_GROUPS: Dict[str, Set[str]] = {
    "human": {
        # Essential tools for human developers using Claude Code
        "ping",
        "authenticate",
        "get_project_status",
        "list_projects",
        "switch_project",
        "get_current_project",
        "create_project",  # NLP project creation
        "add_feature",  # NLP feature addition
        "get_usage_report",
    },
    "agent": {
        # Core workflow tools for autonomous agents
        "ping",
        "register_agent",
        "request_next_task",
        "report_task_progress",
        "report_blocker",
        "get_task_context",
        "log_decision",
        "log_artifact",
        "check_task_dependencies",
        "get_agent_status",
        "create_project",  # NLP project creation for autonomous agents
    },
    "analytics": {
        # All tools for comprehensive analytics (Seneca)
        # This includes all tools from all groups plus analytics-specific ones
        "ping",
        "authenticate",
        "get_usage_report",
        # Project management
        "get_project_status",
        "list_projects",
        "switch_project",
        "get_current_project",
        "add_project",
        "remove_project",
        "update_project",
        # Agent management
        "register_agent",
        "get_agent_status",
        "list_registered_agents",
        # Task management
        "request_next_task",
        "report_task_progress",
        "report_blocker",
        "get_task_context",
        "check_task_dependencies",
        # Context and artifacts
        "log_decision",
        "log_artifact",
        # NLP tools
        "create_project",
        "add_feature",
        # System health
        "check_assignment_health",
        "check_board_health",
        # Pipeline analysis tools
        "pipeline_replay_start",
        "pipeline_replay_forward",
        "pipeline_replay_backward",
        "pipeline_replay_jump",
        "what_if_start",
        "what_if_simulate",
        "what_if_compare",
        "pipeline_compare",
        "pipeline_report",
        "pipeline_monitor_dashboard",
        "pipeline_monitor_flow",
        "pipeline_predict_risk",
        "pipeline_recommendations",
        "pipeline_find_similar",
        # Prediction and AI intelligence tools
        "predict_completion_time",
        "predict_task_outcome",
        "predict_blockage_probability",
        "predict_cascade_effects",
        "get_task_assignment_score",
        # Analytics and metrics tools
        "get_system_metrics",
        "get_agent_metrics",
        "get_project_metrics",
        "get_task_metrics",
        # Code production metrics tools
        "get_code_metrics",
        "get_repository_metrics",
        "get_code_review_metrics",
        "get_code_quality_metrics",
    },
}


def get_tools_for_endpoint(endpoint_type: str) -> Set[str]:
    """
    Get the set of tool names available for a specific endpoint type.

    Parameters
    ----------
    endpoint_type : str
        The type of endpoint ('human', 'agent', or 'analytics')

    Returns
    -------
    Set[str]
        Set of tool names available for this endpoint
    """
    return TOOL_GROUPS.get(endpoint_type, set())


def is_tool_allowed(endpoint_type: str, tool_name: str) -> bool:
    """
    Check if a tool is allowed for a specific endpoint type.

    Parameters
    ----------
    endpoint_type : str
        The type of endpoint ('human', 'agent', or 'analytics')
    tool_name : str
        The name of the tool to check

    Returns
    -------
    bool
        True if the tool is allowed for this endpoint
    """
    allowed_tools = get_tools_for_endpoint(endpoint_type)
    return tool_name in allowed_tools
