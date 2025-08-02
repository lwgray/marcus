"""
MCP Tool Definitions.

This module provides the tool definitions for the Marcus MCP server,
organizing all tool schemas and definitions in a centralized location.
"""

from typing import Dict, List

import mcp.types as types

from ..tools.audit_tools import USAGE_REPORT_TOOL
from ..tools.auth import AUTHENTICATE_TOOL


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
                    }
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
                "required": ["task_id", "filename", "content", "artifact_type"],
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
