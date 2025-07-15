"""
MCP Tool Registration and Handlers.

This module provides the tool registration and handling functionality
for the Marcus MCP server, organizing all tool definitions and handlers
in a centralized location.
"""

import json
from typing import Any, Dict, List, Optional

import mcp.types as types

from .tools import (  # Agent tools; Task tools; Project tools; System tools; NLP tools
    add_feature,
    check_assignment_health,
    create_project,
    get_agent_status,
    get_project_status,
    list_registered_agents,
    ping,
    register_agent,
    report_blocker,
    report_task_progress,
    request_next_task,
)
from .tools.context import (  # Context tools
    get_task_context,
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
from .tools.project_management import (  # Project management tools
    add_project,
    get_current_project,
    list_projects,
    remove_project,
    switch_project,
    update_project,
)


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
            description="Check Marcus status and connectivity",
            inputSchema={
                "type": "object",
                "properties": {
                    "echo": {
                        "type": "string",
                        "description": "Optional message to echo back",
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
                "dependencies and decisions"
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

    try:
        # Agent management tools
        if name == "register_agent":
            result = await register_agent(
                agent_id=arguments.get("agent_id"),
                name=arguments.get("name"),
                role=arguments.get("role"),
                skills=arguments.get("skills", []),
                state=state,
            )

        elif name == "get_agent_status":
            result = await get_agent_status(
                agent_id=arguments.get("agent_id"), state=state
            )

        elif name == "list_registered_agents":
            result = await list_registered_agents(state=state)

        # Task management tools
        elif name == "request_next_task":
            result = await request_next_task(
                agent_id=arguments.get("agent_id"), state=state
            )

        elif name == "report_task_progress":
            result = await report_task_progress(
                agent_id=arguments.get("agent_id"),
                task_id=arguments.get("task_id"),
                status=arguments.get("status"),
                progress=arguments.get("progress", 0),
                message=arguments.get("message", ""),
                state=state,
            )

        elif name == "report_blocker":
            result = await report_blocker(
                agent_id=arguments.get("agent_id"),
                task_id=arguments.get("task_id"),
                blocker_description=arguments.get("blocker_description"),
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

        # Natural language tools
        elif name == "create_project":
            result = await create_project(
                description=arguments.get("description"),
                project_name=arguments.get("project_name"),
                options=arguments.get("options"),
                state=state,
            )

        elif name == "add_feature":
            result = await add_feature(
                feature_description=arguments.get("feature_description"),
                integration_point=arguments.get("integration_point", "auto_detect"),
                state=state,
            )

        # Context Tools
        elif name == "log_decision":
            result = await log_decision(
                agent_id=arguments.get("agent_id"),
                task_id=arguments.get("task_id"),
                decision=arguments.get("decision"),
                state=state,
            )

        elif name == "get_task_context":
            result = await get_task_context(
                task_id=arguments.get("task_id"), state=state
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

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Tool execution failed: {str(e)}", "tool": name},
                    indent=2,
                ),
            )
        ]
