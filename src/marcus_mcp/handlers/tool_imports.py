"""
Tool imports for MCP handlers.

This module centralizes all tool imports from various Marcus modules.
"""

# Agent tools
from ..tools import (
    add_feature,
    check_assignment_health,
    create_project,
    get_agent_status,
    get_project_status,
    get_task_context,
    list_registered_agents,
    log_artifact,
    ping,
    register_agent,
    report_blocker,
    report_task_progress,
    request_next_task,
)

# Analytics tools
from ..tools.analytics import (
    get_agent_metrics,
    get_project_metrics,
    get_system_metrics,
    get_task_metrics,
)

# Audit tools
from ..tools.audit_tools import (
    USAGE_REPORT_TOOL,
    get_usage_report,
)

# Auth tools
from ..tools.auth import (
    AUTHENTICATE_TOOL,
    authenticate,
    get_client_tools,
)

# Board health tools
from ..tools.board_health import (
    check_board_health,
    check_task_dependencies,
)

# Code metrics tools
from ..tools.code_metrics import (
    analyze_code_changes,
    analyze_pr_impact,
    get_pr_complexity,
)

# NLP tools
from ..tools.nlp import (
    analyze_task_clarity,
    extract_entities,
    generate_task_summary,
    suggest_task_labels,
)

# Plugin tools
from ..tools.plugins import (
    discover_plugins,
    execute_plugin,
    list_plugins,
)

# Prediction tools
from ..tools.prediction import (
    analyze_patterns,
    get_pattern_insights,
    predict_task_outcome,
)

# Project management tools
from ..tools.project_management import (
    add_project,
    get_current_project,
    list_projects,
    remove_project,
    switch_project,
    update_project,
)

# Pattern learning tools - disabled, only accessible via visualization UI API
# from ..tools.pattern_learning import (
#     analyze_patterns,
#     get_pattern_insights,
#     predict_task_outcome,
# )


__all__ = [
    # Agent tools
    "add_feature",
    "check_assignment_health",
    "create_project",
    "get_agent_status",
    "get_project_status",
    "get_task_context",
    "list_registered_agents",
    "log_artifact",
    "ping",
    "register_agent",
    "report_blocker",
    "report_task_progress",
    "request_next_task",
    # Analytics tools
    "get_agent_metrics",
    "get_project_metrics",
    "get_system_metrics",
    "get_task_metrics",
    # Audit tools
    "USAGE_REPORT_TOOL",
    "get_usage_report",
    # Auth tools
    "AUTHENTICATE_TOOL",
    "authenticate",
    "get_client_tools",
    # Board health tools
    "check_board_health",
    "check_task_dependencies",
    # Code metrics tools
    "analyze_code_changes",
    "analyze_pr_impact",
    "get_pr_complexity",
    # NLP tools
    "analyze_task_clarity",
    "extract_entities",
    "generate_task_summary",
    "suggest_task_labels",
    # Plugin tools
    "discover_plugins",
    "execute_plugin",
    "list_plugins",
    # Prediction tools
    "analyze_patterns",
    "get_pattern_insights",
    "predict_task_outcome",
    # Project management tools
    "add_project",
    "get_current_project",
    "list_projects",
    "remove_project",
    "switch_project",
    "update_project",
]
