"""
MCP Tool Registration and Handlers.

This module provides the tool registration and handling functionality
for the Marcus MCP server, organizing all tool definitions and handlers
in a centralized location.
"""

import json
import time
from typing import Any, Dict, List, Optional

import mcp.types as types

from .audit import get_audit_logger
from .tools import (  # Agent tools; Task tools; Project tools; System tools; NLP tools
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
from .tools.analytics import (  # Analytics tools
    get_agent_metrics,
    get_project_metrics,
    get_system_metrics,
    get_task_metrics,
)
from .tools.audit_tools import (
    USAGE_REPORT_TOOL,
    get_usage_report,
)
from .tools.auth import (
    AUTHENTICATE_TOOL,
    authenticate,
    get_client_tools,
)
from .tools.board_health import (  # Board health tools
    check_board_health,
    check_task_dependencies,
)
from .tools.code_metrics import (  # Code metrics tools
    get_code_metrics,
    get_code_quality_metrics,
    get_code_review_metrics,
    get_repository_metrics,
)
from .tools.context import (  # Context tools
    log_decision,
)

# Pattern learning tools disabled - only accessible via visualization UI API
# from .tools.pattern_learning import (  # Pattern learning tools
#     assess_project_quality,
#     get_pattern_recommendations,
#     get_project_patterns,
#     get_quality_trends,
#     get_similar_projects,
#     learn_from_completed_project,
# )
from .tools.pipeline import (  # Pipeline tools
    compare_pipelines,
    compare_what_if_scenarios,
    find_similar_flows,
    generate_report,
    get_live_dashboard,
    get_recommendations,
    predict_failure_risk,
    replay_jump_to,
    replay_step_backward,
    replay_step_forward,
    simulate_modification,
    start_replay,
    start_what_if_analysis,
    track_flow_progress,
)
from .tools.predictions import (  # Prediction tools
    get_task_assignment_score,
    predict_blockage_probability,
    predict_cascade_effects,
    predict_completion_time,
    predict_task_outcome,
)
from .tools.project_management import (  # Project management tools
    add_project,
    get_current_project,
    list_projects,
    remove_project,
    switch_project,
    update_project,
)


def get_all_tool_definitions() -> Dict[str, types.Tool]:
    """
    Get all tool definitions as a mapping.

    Returns
    -------
        Dict mapping tool name to Tool definition
    """
    # Build complete tool map
    all_tools = {}

    # Get all tools from both agent and human definitions
    for tool in get_tool_definitions("agent"):
        all_tools[tool.name] = tool
    for tool in get_tool_definitions("human"):
        all_tools[tool.name] = tool

    # Add auth and audit tools
    all_tools["authenticate"] = AUTHENTICATE_TOOL
    all_tools["get_usage_report"] = USAGE_REPORT_TOOL

    return all_tools


def get_all_tool_names() -> List[str]:
    """Get list of all available tool names."""
    return list(get_all_tool_definitions().keys())


def get_tool_definitions(role: str = "agent") -> List[types.Tool]:
    """
    Return list of available tool definitions for MCP based on role.

    Args:
        role: User role - "agent" for coding agents, "human" for full access

    Returns
    -------
        List of Tool objects with schemas for Marcus tools based on role
    """
    # Core agent tools available to all coding agents
    agent_tools = [
        # Agent Management Tools
        types.Tool(
            name="register_agent",
            description="Register a new agent with the Marcus system",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Unique agent identifier",
                    },
                    "name": {"type": "string", "description": "Agent's display name"},
                    "role": {
                        "type": "string",
                        "description": "Agent's role (e.g., 'Backend Developer')",
                    },
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of agent's skills",
                        "default": [],
                    },
                },
                "required": ["agent_id", "name", "role"],
            },
        ),
        types.Tool(
            name="get_agent_status",
            description="Get status and current assignment for an agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent to check status for",
                    }
                },
                "required": ["agent_id"],
            },
        ),
        # Task Management Tools
        types.Tool(
            name="request_next_task",
            description="Request the next optimal task assignment for an agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent requesting the task",
                    }
                },
                "required": ["agent_id"],
            },
        ),
        types.Tool(
            name="report_task_progress",
            description="Report progress on a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent reporting progress",
                    },
                    "task_id": {"type": "string", "description": "Task being updated"},
                    "status": {
                        "type": "string",
                        "description": "Task status: in_progress, completed, blocked",
                    },
                    "progress": {
                        "type": "integer",
                        "description": "Progress percentage (0-100)",
                        "default": 0,
                    },
                    "message": {
                        "type": "string",
                        "description": "Progress message",
                        "default": "",
                    },
                },
                "required": ["agent_id", "task_id", "status"],
            },
        ),
        types.Tool(
            name="report_blocker",
            description="Report a blocker on a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent reporting the blocker",
                    },
                    "task_id": {"type": "string", "description": "Blocked task ID"},
                    "blocker_description": {
                        "type": "string",
                        "description": "Description of the blocker",
                    },
                    "severity": {
                        "type": "string",
                        "description": "Blocker severity: low, medium, high",
                        "default": "medium",
                    },
                },
                "required": ["agent_id", "task_id", "blocker_description"],
            },
        ),
        # Project Monitoring Tools
        types.Tool(
            name="get_project_status",
            description="Get current project status and metrics",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        # System Health Tools
        types.Tool(
            name="ping",
            description="""Check Marcus status and connectivity with special diagnostic commands.

Special commands:
- 'health': Get detailed system health including lease statistics and assignment state
- 'cleanup': Force cleanup of stuck task assignments (safe recovery operation)
- 'reset': Clear ALL assignment state - WARNING: use only when system is stuck!

Examples:
- ping("hello") - Simple connectivity check
- ping("health") - Full system health report
- ping("cleanup") - Clean stuck assignments after interruption
- ping("reset") - Complete assignment reset""",
            inputSchema={
                "type": "object",
                "properties": {
                    "echo": {
                        "type": "string",
                        "description": "Message to echo or command: 'health'|'cleanup'|'reset'",
                        "default": "",
                    }
                },
                "required": [],
            },
        ),
        # Context Tools (for agents to log decisions)
        types.Tool(
            name="log_decision",
            description="Log an architectural decision that might affect other tasks",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent making the decision",
                    },
                    "task_id": {"type": "string", "description": "Current task ID"},
                    "decision": {
                        "type": "string",
                        "description": (
                            "Decision description. Format: "
                            "'I chose X because Y. This affects Z.'"
                        ),
                    },
                },
                "required": ["agent_id", "task_id", "decision"],
            },
        ),
        types.Tool(
            name="get_task_context",
            description=(
                "Get the full context for a specific task including "
                "dependencies, decisions, and artifacts stored in the repository"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID to get context for",
                    },
                    "project_root": {
                        "type": "string",
                        "description": (
                            "Absolute path to the project root directory. "
                            "Used to discover artifacts created in the project workspace. "
                            "All agents working on this project should pass the same path "
                            "to see each other's artifacts."
                        ),
                    },
                },
                "required": ["task_id"],
            },
        ),
        types.Tool(
            name="log_artifact",
            description=(
                "Store an artifact with smart location management. "
                "Artifacts are automatically stored in organized directories based on type "
                "(e.g., API specs → docs/api/, designs → docs/design/). "
                "You can optionally override the location for special cases."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The current task ID"},
                    "filename": {
                        "type": "string",
                        "description": "Name for the artifact file",
                    },
                    "content": {
                        "type": "string",
                        "description": "The artifact content to store",
                    },
                    "artifact_type": {
                        "type": "string",
                        "description": "Type of artifact",
                        "enum": [
                            "specification",
                            "api",
                            "design",
                            "architecture",
                            "documentation",
                            "reference",
                            "temporary",
                        ],
                    },
                    "project_root": {
                        "type": "string",
                        "description": (
                            "Absolute path to the project root directory where artifacts should be created. "
                            "All agents working on this project should pass the same path. "
                            "Artifacts will be created relative to this path based on their type "
                            "(e.g., an 'api' artifact will go in {project_root}/docs/api/). "
                            "Typically this is os.getcwd() when the agent is running from the project root."
                        ),
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the artifact",
                        "default": "",
                    },
                    "location": {
                        "type": "string",
                        "description": "Optional override for storage location (relative path)",
                        "default": None,
                    },
                },
                "required": [
                    "task_id",
                    "filename",
                    "content",
                    "artifact_type",
                    "project_root",
                ],
            },
        ),
        # Natural Language Tools (also available to agents)
        types.Tool(
            name="create_project",
            description=(
                "Create a complete project from natural language description. "
                "Automatically generates tasks, assigns priorities, and creates "
                "kanban board structure based on project complexity and deployment needs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": (
                            "Natural language description of what you want to build. "
                            "Be specific about features and functionality. "
                            "Example: 'Create a todo app with user authentication, "
                            "task categories, and email reminders'"
                        ),
                    },
                    "project_name": {
                        "type": "string",
                        "description": (
                            "A short, memorable name for your project. "
                            "This will be used as the kanban board title. "
                            "Example: 'TodoMaster' or 'Task Tracker Pro'"
                        ),
                    },
                    "options": {
                        "type": "object",
                        "description": (
                            "Optional configuration to control project scope and complexity. "
                            "All fields are optional - sensible defaults will be used."
                        ),
                        "properties": {
                            "complexity": {
                                "type": "string",
                                "description": (
                                    "Project complexity level (default: 'standard'). "
                                    "- 'prototype': Quick MVP with minimal features (3-8 tasks) "
                                    "- 'standard': Full-featured project (10-20 tasks) "
                                    "- 'enterprise': Production-ready with all features (25+ tasks)"
                                ),
                                "enum": ["prototype", "standard", "enterprise"],
                                "default": "standard",
                            },
                            "deployment": {
                                "type": "string",
                                "description": (
                                    "Deployment scope (default: 'none'). "
                                    "- 'none': Local development only, no deployment tasks "
                                    "- 'internal': Include staging/team deployment tasks "
                                    "- 'production': Full production deployment with monitoring"
                                ),
                                "enum": ["none", "internal", "production"],
                                "default": "none",
                            },
                            "team_size": {
                                "type": "integer",
                                "description": (
                                    "Number of developers (1-20). "
                                    "Defaults based on complexity: prototype=1, standard=3, enterprise=5. "
                                    "Affects task parallelization and estimates."
                                ),
                                "minimum": 1,
                                "maximum": 20,
                            },
                            "tech_stack": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Technologies/frameworks to use. "
                                    "Example: ['Python', 'React', 'PostgreSQL', 'Docker']. "
                                    "Helps generate appropriate setup and configuration tasks."
                                ),
                            },
                            "deadline": {
                                "type": "string",
                                "format": "date",
                                "description": (
                                    "Project deadline in ISO format (YYYY-MM-DD). "
                                    "Example: '2024-12-31'. "
                                    "Used to assess timeline risks and adjust priorities."
                                ),
                            },
                        },
                    },
                },
                "required": ["description", "project_name"],
            },
        ),
    ]

    # If role is "agent", return only agent tools
    if role == "agent":
        return agent_tools

    # For "human" role, include all tools including pipeline enhancements
    human_tools = agent_tools + [
        # Administrative Tools (human only)
        types.Tool(
            name="list_registered_agents",
            description="List all registered agents",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="check_assignment_health",
            description="Check the health of the assignment tracking system",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="check_board_health",
            description="""Analyze overall board health and detect systemic issues.

Detects:
- Skill mismatches: Tasks no agent can handle
- Circular dependencies: Task cycles that block progress
- Bottlenecks: Tasks blocking many others
- Chain blocks: Long sequential dependency chains
- Stale tasks: In-progress tasks not updated recently
- Workload issues: Overloaded or idle agents

Returns health score (0-100) with detailed issue analysis and recommendations.

Usage: check_board_health()""",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="check_task_dependencies",
            description="""Check dependencies for a specific task and analyze its position in the workflow.

Shows:
- What this task depends on (upstream dependencies)
- What depends on this task (downstream impact)
- Whether task is part of circular dependencies
- If task is a bottleneck (blocking 3+ tasks)
- Recommended completion order

Helps identify critical path tasks and dependency issues.

Usage: check_task_dependencies("task-123")""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task to analyze (e.g., 'task-123')",
                    },
                },
                "required": ["task_id"],
            },
        ),
        # Project Management Tools (human only)
        types.Tool(
            name="list_projects",
            description="List all available projects",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter projects by tags",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Filter by provider (planka, linear, github)",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="switch_project",
            description="Switch to a different project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "ID of project to switch to",
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Name of project (alternative to ID)",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_current_project",
            description="Get the currently active project",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="add_project",
            description="Add a new project configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                    "provider": {
                        "type": "string",
                        "description": "Provider type (planka, linear, github)",
                        "enum": ["planka", "linear", "github"],
                    },
                    "config": {
                        "type": "object",
                        "description": "Provider-specific configuration",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Project tags",
                        "default": [],
                    },
                    "make_active": {
                        "type": "boolean",
                        "description": "Switch to this project after creation",
                        "default": True,
                    },
                },
                "required": ["name", "provider"],
            },
        ),
        types.Tool(
            name="remove_project",
            description="Remove a project from the registry",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "ID of project to remove",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirm deletion",
                        "default": False,
                    },
                },
                "required": ["project_id"],
            },
        ),
        types.Tool(
            name="update_project",
            description="Update project configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "ID of project to update",
                    },
                    "name": {"type": "string", "description": "New project name"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New project tags",
                    },
                    "config": {
                        "type": "object",
                        "description": "Updated provider configuration",
                    },
                },
                "required": ["project_id"],
            },
        ),
        # Natural Language Tools (also available to humans)
        types.Tool(
            name="create_project",
            description=(
                "Create a complete project from natural language description. "
                "Automatically generates tasks, assigns priorities, and creates "
                "kanban board structure based on project complexity and deployment needs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": (
                            "Natural language description of what you want to build. "
                            "Be specific about features and functionality. "
                            "Example: 'Create a todo app with user authentication, "
                            "task categories, and email reminders'"
                        ),
                    },
                    "project_name": {
                        "type": "string",
                        "description": (
                            "A short, memorable name for your project. "
                            "This will be used as the kanban board title. "
                            "Example: 'TodoMaster' or 'Task Tracker Pro'"
                        ),
                    },
                    "options": {
                        "type": "object",
                        "description": (
                            "Optional configuration to control project scope and complexity. "
                            "All fields are optional - sensible defaults will be used."
                        ),
                        "properties": {
                            "complexity": {
                                "type": "string",
                                "description": (
                                    "Project complexity level (default: 'standard'). "
                                    "- 'prototype': Quick MVP with minimal features (3-8 tasks) "
                                    "- 'standard': Full-featured project (10-20 tasks) "
                                    "- 'enterprise': Production-ready with all features (25+ tasks)"
                                ),
                                "enum": ["prototype", "standard", "enterprise"],
                                "default": "standard",
                            },
                            "deployment": {
                                "type": "string",
                                "description": (
                                    "Deployment scope (default: 'none'). "
                                    "- 'none': Local development only, no deployment tasks "
                                    "- 'internal': Include staging/team deployment tasks "
                                    "- 'production': Full production deployment with monitoring"
                                ),
                                "enum": ["none", "internal", "production"],
                                "default": "none",
                            },
                            "team_size": {
                                "type": "integer",
                                "description": (
                                    "Number of developers (1-20). "
                                    "Defaults based on complexity: prototype=1, standard=3, enterprise=5. "
                                    "Affects task parallelization and estimates."
                                ),
                                "minimum": 1,
                                "maximum": 20,
                            },
                            "tech_stack": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Technologies/frameworks to use. "
                                    "Example: ['Python', 'React', 'PostgreSQL', 'Docker']. "
                                    "Helps generate appropriate setup and configuration tasks."
                                ),
                            },
                            "deadline": {
                                "type": "string",
                                "format": "date",
                                "description": (
                                    "Project deadline in ISO format (YYYY-MM-DD). "
                                    "Example: '2024-12-31'. "
                                    "Used to assess timeline risks and adjust priorities."
                                ),
                            },
                        },
                    },
                },
                "required": ["description", "project_name"],
            },
        ),
        types.Tool(
            name="add_feature",
            description="Add a feature to existing project using natural language",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_description": {
                        "type": "string",
                        "description": (
                            "Natural language description of the feature to add"
                        ),
                    },
                    "integration_point": {
                        "type": "string",
                        "description": "How to integrate the feature",
                        "enum": [
                            "auto_detect",
                            "after_current",
                            "parallel",
                            "new_phase",
                        ],
                        "default": "auto_detect",
                    },
                },
                "required": ["feature_description"],
            },
        ),
        # Pipeline Enhancement Tools (only for humans)
        types.Tool(
            name="pipeline_replay_start",
            description="Start replay session for a pipeline flow",
            inputSchema={
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID to replay"}
                },
                "required": ["flow_id"],
            },
        ),
        types.Tool(
            name="pipeline_replay_forward",
            description="Step forward in pipeline replay",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="pipeline_replay_backward",
            description="Step backward in pipeline replay",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="pipeline_replay_jump",
            description="Jump to specific position in replay",
            inputSchema={
                "type": "object",
                "properties": {
                    "position": {
                        "type": "integer",
                        "description": "Position to jump to",
                    }
                },
                "required": ["position"],
            },
        ),
        types.Tool(
            name="what_if_start",
            description="Start what-if analysis session",
            inputSchema={
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID to analyze"}
                },
                "required": ["flow_id"],
            },
        ),
        types.Tool(
            name="what_if_simulate",
            description="Simulate pipeline with modifications",
            inputSchema={
                "type": "object",
                "properties": {
                    "modifications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "parameter_type": {"type": "string"},
                                "parameter_name": {"type": "string"},
                                "new_value": {},
                                "old_value": {},
                                "description": {"type": "string"},
                            },
                            "required": [
                                "parameter_type",
                                "parameter_name",
                                "new_value",
                            ],
                        },
                    }
                },
                "required": ["modifications"],
            },
        ),
        types.Tool(
            name="what_if_compare",
            description="Compare all what-if scenarios",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="pipeline_compare",
            description="Compare multiple pipeline flows",
            inputSchema={
                "type": "object",
                "properties": {
                    "flow_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of flow IDs to compare",
                    }
                },
                "required": ["flow_ids"],
            },
        ),
        types.Tool(
            name="pipeline_report",
            description="Generate pipeline report",
            inputSchema={
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID"},
                    "format": {
                        "type": "string",
                        "enum": ["html", "markdown", "json"],
                        "description": "Report format",
                        "default": "html",
                    },
                },
                "required": ["flow_id"],
            },
        ),
        types.Tool(
            name="pipeline_monitor_dashboard",
            description="Get live monitoring dashboard data",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="pipeline_monitor_flow",
            description="Track specific flow progress",
            inputSchema={
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID to track"}
                },
                "required": ["flow_id"],
            },
        ),
        types.Tool(
            name="pipeline_predict_risk",
            description="Predict failure risk for a flow",
            inputSchema={
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID to assess"}
                },
                "required": ["flow_id"],
            },
        ),
        types.Tool(
            name="pipeline_recommendations",
            description="Get recommendations for a pipeline flow",
            inputSchema={
                "type": "object",
                "properties": {"flow_id": {"type": "string", "description": "Flow ID"}},
                "required": ["flow_id"],
            },
        ),
        types.Tool(
            name="pipeline_find_similar",
            description="Find similar pipeline flows",
            inputSchema={
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID"},
                    "limit": {
                        "type": "integer",
                        "description": "Max similar flows to return",
                        "default": 5,
                    },
                },
                "required": ["flow_id"],
            },
        ),
        # Pattern Learning Tools removed - only accessible via visualization UI API
        # Audit and analytics tools
        USAGE_REPORT_TOOL,
    ]

    return human_tools


async def handle_tool_call(
    name: str, arguments: Optional[Dict[str, Any]], state: Any
) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool calls by routing to appropriate tool functions.

    Args:
        name: Name of the tool to call
        arguments: Tool arguments
        state: Marcus server state instance

    Returns
    -------
        List of MCP content objects with tool results
    """
    if arguments is None:
        arguments = {}

    # Track timing
    start_time = time.time()

    # Get client info if available
    client_id = None
    client_type = None
    if hasattr(state, "_current_client_id"):
        client_id = state._current_client_id
    if hasattr(state, "_registered_clients") and client_id:
        client_info = state._registered_clients.get(client_id, {})
        client_type = client_info.get("client_type")

    # Get audit logger
    audit_logger = get_audit_logger()

    # Check access control
    allowed_tools = get_client_tools(client_id, state)
    if name not in allowed_tools and "*" not in allowed_tools:
        # Audit access denied
        await audit_logger.log_access_denied(
            client_id=client_id,
            client_type=client_type,
            tool_name=name,
            reason=f"Tool '{name}' not allowed for client type '{client_type or 'unregistered'}'",
        )

        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Access denied: Tool '{name}' not available for your client type",
                        "client_type": client_type or "unregistered",
                        "allowed_tools": allowed_tools,
                    },
                    indent=2,
                ),
            )
        ]

    try:
        # Initialize result variable with proper type
        result: Any = None

        # Authentication tools (special handling)
        if name == "authenticate":
            result = await authenticate(
                client_id=arguments.get("client_id"),
                client_type=arguments.get("client_type"),
                role=arguments.get("role"),
                metadata=arguments.get("metadata"),
                state=state,
            )
            # Client has been registered, update tracking
            client_id = arguments.get("client_id")
            client_type = arguments.get("client_type")

        # Agent management tools
        elif name == "register_agent":
            agent_id = arguments.get("agent_id") if arguments else None
            agent_name = arguments.get("name") if arguments else None
            role = arguments.get("role") if arguments else None

            if not agent_id or not agent_name or not role:
                result = {"error": "agent_id, name, and role are required"}
            else:
                result = await register_agent(
                    agent_id=agent_id,
                    name=agent_name,
                    role=role,
                    skills=arguments.get("skills", []),
                    state=state,
                )

        elif name == "get_agent_status":
            agent_id = arguments.get("agent_id") if arguments else None
            if not agent_id:
                result = {"error": "agent_id is required"}
            else:
                result = await get_agent_status(agent_id=agent_id, state=state)

        elif name == "list_registered_agents":
            result = await list_registered_agents(state=state)

        # Task management tools
        elif name == "request_next_task":
            agent_id = arguments.get("agent_id") if arguments else None
            if not agent_id:
                result = {"error": "agent_id is required"}
            else:
                result = await request_next_task(agent_id=agent_id, state=state)

        elif name == "report_task_progress":
            agent_id = arguments.get("agent_id") if arguments else None
            task_id = arguments.get("task_id") if arguments else None
            status = arguments.get("status") if arguments else None

            if not agent_id or not task_id or not status:
                result = {"error": "agent_id, task_id, and status are required"}
            else:
                result = await report_task_progress(
                    agent_id=agent_id,
                    task_id=task_id,
                    status=status,
                    progress=arguments.get("progress", 0),
                    message=arguments.get("message", ""),
                    state=state,
                )

        elif name == "report_blocker":
            agent_id = arguments.get("agent_id") if arguments else None
            task_id = arguments.get("task_id") if arguments else None
            blocker_description = (
                arguments.get("blocker_description") if arguments else None
            )

            if not agent_id or not task_id or not blocker_description:
                result = {
                    "error": "agent_id, task_id, and blocker_description are required"
                }
            else:
                result = await report_blocker(
                    agent_id=agent_id,
                    task_id=task_id,
                    blocker_description=blocker_description,
                    severity=arguments.get("severity", "medium"),
                    state=state,
                )

        # Project monitoring tools
        elif name == "get_project_status":
            result = await get_project_status(state=state)

        # System health tools
        elif name == "ping":
            result = await ping(echo=arguments.get("echo", ""), state=state)

        elif name == "check_assignment_health":
            result = await check_assignment_health(state=state)

        elif name == "get_usage_report":
            days = arguments.get("days", 7) if arguments else 7
            result = await get_usage_report(days=days, state=state)

        elif name == "check_board_health":
            result = await check_board_health(state=state)

        elif name == "check_task_dependencies":
            task_id = arguments.get("task_id") if arguments else None
            if not task_id:
                result = {"error": "task_id is required"}
            else:
                result = await check_task_dependencies(task_id=task_id, state=state)

        # Natural language tools
        elif name == "create_project":
            # Log tool call start
            state.log_event(
                "mcp_tool_call_start",
                {
                    "tool": "create_project",
                    "project_name": arguments.get("project_name", "unknown"),
                },
            )

            description = arguments.get("description") if arguments else None
            project_name = arguments.get("project_name") if arguments else None

            if not description or not project_name:
                result = {"error": "description and project_name are required"}
            else:
                result = await create_project(
                    description=description,
                    project_name=project_name,
                    options=arguments.get("options"),
                    state=state,
                )

            # Log tool call complete
            state.log_event(
                "mcp_tool_call_complete",
                {
                    "tool": "create_project",
                    "project_name": arguments.get("project_name", "unknown"),
                    "success": (
                        result.get("success", False)
                        if isinstance(result, dict)
                        else False
                    ),
                },
            )

        elif name == "add_feature":
            feature_description = (
                arguments.get("feature_description") if arguments else None
            )

            if not feature_description:
                result = {"error": "feature_description is required"}
            else:
                result = await add_feature(
                    feature_description=feature_description,
                    integration_point=arguments.get("integration_point", "auto_detect"),
                    state=state,
                )

        # Context Tools
        elif name == "log_decision":
            agent_id = arguments.get("agent_id") if arguments else None
            task_id = arguments.get("task_id") if arguments else None
            decision = arguments.get("decision") if arguments else None

            if not agent_id or not task_id or not decision:
                result = {"error": "agent_id, task_id, and decision are required"}
            else:
                result = await log_decision(
                    agent_id=agent_id,
                    task_id=task_id,
                    decision=decision,
                    state=state,
                )

        elif name == "get_task_context":
            task_id = arguments.get("task_id") if arguments else None

            if not task_id:
                result = {"error": "task_id is required"}
            else:
                result = await get_task_context(task_id=task_id, state=state)

        elif name == "log_artifact":
            task_id = arguments.get("task_id") if arguments else None
            filename = arguments.get("filename") if arguments else None
            content = arguments.get("content") if arguments else None
            artifact_type = arguments.get("artifact_type") if arguments else None

            if not task_id or not filename or not content or not artifact_type:
                result = {
                    "error": "task_id, filename, content, and artifact_type are required"
                }
            else:
                result = await log_artifact(
                    task_id=task_id,
                    filename=filename,
                    content=content,
                    artifact_type=artifact_type,
                    description=arguments.get("description", ""),
                    location=arguments.get("location"),  # Optional override
                    state=state,
                )

        # Project Management Tools
        elif name == "list_projects":
            result = await list_projects(state, arguments)
        elif name == "switch_project":
            result = await switch_project(state, arguments)
        elif name == "get_current_project":
            result = await get_current_project(state, arguments)
        elif name == "add_project":
            result = await add_project(state, arguments)
        elif name == "remove_project":
            result = await remove_project(state, arguments)
        elif name == "update_project":
            result = await update_project(state, arguments)

        # Pipeline Enhancement Tools
        elif name == "pipeline_replay_start":
            result = await start_replay(state, arguments)

        elif name == "pipeline_replay_forward":
            result = await replay_step_forward(state, arguments)

        elif name == "pipeline_replay_backward":
            result = await replay_step_backward(state, arguments)

        elif name == "pipeline_replay_jump":
            result = await replay_jump_to(state, arguments)

        elif name == "what_if_start":
            result = await start_what_if_analysis(state, arguments)

        elif name == "what_if_simulate":
            result = await simulate_modification(state, arguments)

        elif name == "what_if_compare":
            result = await compare_what_if_scenarios(state, arguments)

        elif name == "pipeline_compare":
            result = await compare_pipelines(state, arguments)

        elif name == "pipeline_report":
            result = await generate_report(state, arguments)

        elif name == "pipeline_monitor_dashboard":
            result = await get_live_dashboard(state, arguments)

        elif name == "pipeline_monitor_flow":
            result = await track_flow_progress(state, arguments)

        elif name == "pipeline_predict_risk":
            result = await predict_failure_risk(state, arguments)

        elif name == "pipeline_recommendations":
            result = await get_recommendations(state, arguments)

        elif name == "pipeline_find_similar":
            result = await find_similar_flows(state, arguments)

        # Prediction and AI intelligence tools
        elif name == "predict_completion_time":
            result = await predict_completion_time(
                project_id=arguments.get("project_id"),
                include_confidence=arguments.get("include_confidence", True),
                state=state,
            )

        elif name == "predict_task_outcome":
            task_id = arguments.get("task_id") if arguments else None
            if not task_id:
                result = {"error": "task_id is required"}
            else:
                result = await predict_task_outcome(
                    task_id=task_id,
                    agent_id=arguments.get("agent_id"),
                    state=state,
                )

        elif name == "predict_blockage_probability":
            task_id = arguments.get("task_id") if arguments else None
            if not task_id:
                result = {"error": "task_id is required"}
            else:
                result = await predict_blockage_probability(
                    task_id=task_id,
                    include_mitigation=arguments.get("include_mitigation", True),
                    state=state,
                )

        elif name == "predict_cascade_effects":
            task_id = arguments.get("task_id") if arguments else None
            if not task_id:
                result = {"error": "task_id is required"}
            else:
                result = await predict_cascade_effects(
                    task_id=task_id,
                    delay_days=arguments.get("delay_days", 1),
                    state=state,
                )

        elif name == "get_task_assignment_score":
            task_id = arguments.get("task_id") if arguments else None
            agent_id = arguments.get("agent_id") if arguments else None
            if not task_id or not agent_id:
                result = {"error": "task_id and agent_id are required"}
            else:
                result = await get_task_assignment_score(
                    task_id=task_id,
                    agent_id=agent_id,
                    state=state,
                )

        # Analytics and metrics tools
        elif name == "get_system_metrics":
            result = await get_system_metrics(
                time_window=arguments.get("time_window", "1h"),
                state=state,
            )

        elif name == "get_agent_metrics":
            agent_id = arguments.get("agent_id") if arguments else None
            if not agent_id:
                result = {"error": "agent_id is required"}
            else:
                result = await get_agent_metrics(
                    agent_id=agent_id,
                    time_window=arguments.get("time_window", "7d"),
                    state=state,
                )

        elif name == "get_project_metrics":
            result = await get_project_metrics(
                project_id=arguments.get("project_id"),
                time_window=arguments.get("time_window", "7d"),
                state=state,
            )

        elif name == "get_task_metrics":
            result = await get_task_metrics(
                time_window=arguments.get("time_window", "30d"),
                group_by=arguments.get("group_by", "status"),
                state=state,
            )

        # Code production metrics tools
        elif name == "get_code_metrics":
            agent_id = arguments.get("agent_id") if arguments else None
            if not agent_id:
                result = {"error": "agent_id is required"}
            else:
                result = await get_code_metrics(
                    agent_id=agent_id,
                    start_date=arguments.get("start_date"),
                    end_date=arguments.get("end_date"),
                    state=state,
                )

        elif name == "get_repository_metrics":
            repository = arguments.get("repository") if arguments else None
            if not repository:
                result = {"error": "repository is required"}
            else:
                result = await get_repository_metrics(
                    repository=repository,
                    time_window=arguments.get("time_window", "7d"),
                    state=state,
                )

        elif name == "get_code_review_metrics":
            result = await get_code_review_metrics(
                agent_id=arguments.get("agent_id"),
                time_window=arguments.get("time_window", "7d"),
                state=state,
            )

        elif name == "get_code_quality_metrics":
            repository = arguments.get("repository") if arguments else None
            if not repository:
                result = {"error": "repository is required"}
            else:
                result = await get_code_quality_metrics(
                    repository=repository,
                    branch=arguments.get("branch", "main"),
                    state=state,
                )

        # Pattern Learning Tools removed - only accessible via visualization UI API
        elif name in [
            "get_similar_projects",
            "get_project_patterns",
            "assess_project_quality",
            "get_pattern_recommendations",
            "learn_from_completed_project",
            "get_quality_trends",
        ]:
            result = {
                "error": (
                    f"Pattern learning tool '{name}' is not available through MCP. "
                    "Please use the visualization UI API endpoints instead."
                ),
                "suggestion": (
                    "Pattern learning tools are now only accessible through "
                    "the web UI at http://localhost:8080"
                ),
            }

        else:
            result = {"error": f"Unknown tool: {name}"}

        # Log response creation
        state.log_event(
            "mcp_creating_response",
            {
                "tool": name,
                "has_result": result is not None,
                "result_type": type(result).__name__ if result else "None",
            },
        )

        response: List[
            types.TextContent | types.ImageContent | types.EmbeddedResource
        ] = [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        # Ensure stdio buffer is flushed for immediate response delivery
        import sys

        sys.stdout.flush()
        sys.stderr.flush()

        # Log response return
        state.log_event(
            "mcp_returning_response",
            {
                "tool": name,
                "response_length": (
                    len(response[0].text)
                    if response and isinstance(response[0], types.TextContent)
                    else 0
                ),
            },
        )

        # Audit successful tool call
        duration_ms = (time.time() - start_time) * 1000
        await audit_logger.log_tool_call(
            client_id=client_id,
            client_type=client_type,
            tool_name=name,
            arguments=arguments,
            result=result,
            duration_ms=duration_ms,
            success=True,
        )

        return response

    except Exception as e:
        # Audit failed tool call
        duration_ms = (time.time() - start_time) * 1000
        await audit_logger.log_tool_call(
            client_id=client_id,
            client_type=client_type,
            tool_name=name,
            arguments=arguments,
            result=None,
            duration_ms=duration_ms,
            success=False,
            error=str(e),
        )

        error_response: List[
            types.TextContent | types.ImageContent | types.EmbeddedResource
        ] = [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Tool execution failed: {str(e)}", "tool": name},
                    indent=2,
                ),
            )
        ]

        # Ensure stdio buffer is flushed for immediate error delivery
        import sys

        sys.stdout.flush()
        sys.stderr.flush()

        return error_response
