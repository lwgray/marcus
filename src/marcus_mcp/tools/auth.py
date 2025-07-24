"""
Authentication and role management tools for Marcus MCP.

This module provides tools for client registration and role-based access control.
"""

from typing import Any, Dict, List, Optional

from mcp.types import TextContent, Tool

# Define role-based tool access
ROLE_TOOLS = {
    "observer": [
        # Basic connectivity and authentication
        "ping",
        "register_client",
        # Read-only project visibility
        "get_project_status",
        "get_current_project",
        "list_projects",
        # Read-only agent visibility
        "list_registered_agents",
        "get_agent_status",
        # Read-only board health monitoring
        "check_board_health",
        "check_task_dependencies",
        # Analytics and monitoring (Seneca use case)
        "pipeline_monitor_dashboard",
        "pipeline_monitor_flow",
        "pipeline_report",
        "pipeline_predict_risk",
        "pipeline_find_similar",
    ],
    "developer": [
        # Everything observers have (read access)
        "ping",
        "register_client",
        "get_project_status",
        "get_current_project",
        "list_projects",
        "list_registered_agents",
        "get_agent_status",
        "check_board_health",
        "check_task_dependencies",
        # Project creation and management
        "create_project",  # NLP project creation
        "add_feature",  # NLP feature addition
        "switch_project",  # Change active project
        "add_project",  # Add existing project
        "update_project",  # Modify project config
        # Task context (read-only)
        "get_task_context",  # View task details
    ],
    "agent": [
        # Basic connectivity
        "ping",
        "register_client",
        # Minimal project awareness
        "get_project_status",
        # Core agent workflow
        "request_next_task",  # Get assignments
        "report_task_progress",  # Update progress
        "report_blocker",  # Report issues
        # Context and collaboration
        "get_task_context",  # Full task context
        "log_decision",  # Document choices
        "log_artifact",  # Store outputs
        # Dependency awareness
        "check_task_dependencies",  # Understand relationships
    ],
    "coordinator": [
        # Everything developers have
        "ping",
        "register_client",
        "get_project_status",
        "get_current_project",
        "list_projects",
        "list_registered_agents",
        "get_agent_status",
        "check_board_health",
        "check_task_dependencies",
        "create_project",
        "add_feature",
        "switch_project",
        "add_project",
        "update_project",
        "get_task_context",
        # Additional coordination capabilities
        "register_agent",  # Manage agent roster
        "remove_project",  # Delete projects
        "check_assignment_health",  # Debug assignments
        # All pipeline tools for analysis
        "pipeline_monitor_dashboard",
        "pipeline_monitor_flow",
        "pipeline_report",
        "pipeline_predict_risk",
        "pipeline_find_similar",
        "pipeline_compare",
        "pipeline_replay_start",
        "pipeline_replay_forward",
        "pipeline_replay_backward",
        "pipeline_replay_jump",
    ],
    "admin": [
        # Admins get all tools
        "*"
    ],
}

# Default tools available before registration
# These allow basic connectivity and authentication
DEFAULT_TOOLS = ["ping", "register_client"]


async def register_client(
    client_id: str,
    client_type: str,
    role: str,
    metadata: Optional[Dict[str, Any]] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Register a client with Marcus and assign role-based access.

    Parameters
    ----------
    client_id : str
        Unique identifier for the client (e.g., "seneca-001", "user-john", "agent-backend-01")
    client_type : str
        Type of client: "observer", "developer", "agent", "coordinator", "admin"
    role : str
        Specific role within the client type (e.g., "analytics", "developer", "backend")
    metadata : Optional[Dict[str, Any]]
        Additional client metadata
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Registration result with available tools
    """
    # Store client registration
    if not hasattr(state, "_registered_clients"):
        state._registered_clients = {}

    client_info = {
        "client_id": client_id,
        "client_type": client_type,
        "role": role,
        "metadata": metadata or {},
        "registered_at": (
            state._get_timestamp() if hasattr(state, "_get_timestamp") else None
        ),
    }

    state._registered_clients[client_id] = client_info

    # Log the registration
    state.log_event(
        "client_registered",
        {
            "client_id": client_id,
            "client_type": client_type,
            "role": role,
        },
    )

    # Get available tools for this client type
    available_tools = ROLE_TOOLS.get(client_type, DEFAULT_TOOLS)

    return {
        "success": True,
        "client_id": client_id,
        "client_type": client_type,
        "role": role,
        "available_tools": available_tools,
        "message": f"Client '{client_id}' registered as {client_type} with role '{role}'",
    }


def get_client_tools(client_id: Optional[str], state: Any) -> List[str]:
    """
    Get list of tools available to a specific client.

    Parameters
    ----------
    client_id : Optional[str]
        Client identifier, None for unregistered clients
    state : Any
        Marcus server state

    Returns
    -------
    List[str]
        List of available tool names
    """
    # If no client_id, return default tools
    if not client_id:
        return DEFAULT_TOOLS

    # Check if client is registered
    if not hasattr(state, "_registered_clients"):
        return DEFAULT_TOOLS

    client_info = state._registered_clients.get(client_id)
    if not client_info:
        return DEFAULT_TOOLS

    # Get tools based on client type
    client_type = client_info.get("client_type", "user")
    tools = ROLE_TOOLS.get(client_type, DEFAULT_TOOLS)

    # If admin, return all tools
    if "*" in tools:
        # Return all tool names from the registry
        from ..handlers import get_all_tool_names

        return get_all_tool_names()

    return tools


def get_tool_definitions_for_client(client_id: Optional[str], state: Any) -> List[Tool]:
    """
    Get tool definitions filtered by client access.

    Parameters
    ----------
    client_id : Optional[str]
        Client identifier
    state : Any
        Marcus server state

    Returns
    -------
    List[Tool]
        List of tool definitions available to the client
    """
    from ..handlers import get_tool_definitions

    # Get allowed tools for this client
    allowed_tools = get_client_tools(client_id, state)

    # Get all tool definitions
    all_tools = get_tool_definitions("admin")  # Get all tools

    # Filter based on client access
    if "*" in allowed_tools:
        return all_tools

    return [tool for tool in all_tools if tool.name in allowed_tools]


# Tool definition for registration
REGISTER_CLIENT_TOOL = Tool(
    name="register_client",
    description="Register a client with Marcus and get role-based tool access",
    input_schema={
        "type": "object",
        "properties": {
            "client_id": {
                "type": "string",
                "description": "Unique client identifier (e.g., 'seneca-001', 'user-john')",
            },
            "client_type": {
                "type": "string",
                "enum": ["observer", "developer", "agent", "coordinator", "admin"],
                "description": "Type of client determining tool access",
            },
            "role": {
                "type": "string",
                "description": "Specific role (e.g., 'analytics', 'developer', 'backend')",
            },
            "metadata": {
                "type": "object",
                "description": "Optional metadata about the client",
                "additionalProperties": True,
            },
        },
        "required": ["client_id", "client_type", "role"],
    },
)
