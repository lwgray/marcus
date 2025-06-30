"""
MCP Tool Registration and Handlers

This module provides the tool registration and handling functionality
for the Marcus MCP server, organizing all tool definitions and handlers
in a centralized location.
"""

import json
from typing import List, Dict, Any, Optional
import mcp.types as types

from .tools import (
    # Agent tools
    register_agent,
    get_agent_status,
    list_registered_agents,
    # Task tools
    request_next_task,
    report_task_progress,
    report_blocker,
    # Project tools
    get_project_status,
    # System tools
    ping,
    check_assignment_health,
    # NLP tools
    create_project,
    add_feature
)


def get_tool_definitions() -> List[types.Tool]:
    """
    Return list of all available tool definitions for MCP.
    
    Returns:
        List of Tool objects with schemas for all Marcus tools
    """
    return [
        # Agent Management Tools
        types.Tool(
            name="register_agent",
            description="Register a new agent with the Marcus system",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Unique agent identifier"},
                    "name": {"type": "string", "description": "Agent's display name"},
                    "role": {"type": "string", "description": "Agent's role (e.g., 'Backend Developer')"},
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of agent's skills",
                        "default": []
                    }
                },
                "required": ["agent_id", "name", "role"]
            }
        ),
        types.Tool(
            name="get_agent_status",
            description="Get status and current assignment for an agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent to check status for"}
                },
                "required": ["agent_id"]
            }
        ),
        types.Tool(
            name="list_registered_agents",
            description="List all registered agents",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        # Task Management Tools
        types.Tool(
            name="request_next_task",
            description="Request the next optimal task assignment for an agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent requesting the task"}
                },
                "required": ["agent_id"]
            }
        ),
        types.Tool(
            name="report_task_progress",
            description="Report progress on a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent reporting progress"},
                    "task_id": {"type": "string", "description": "Task being updated"},
                    "status": {"type": "string", "description": "Task status: in_progress, completed, blocked"},
                    "progress": {"type": "integer", "description": "Progress percentage (0-100)", "default": 0},
                    "message": {"type": "string", "description": "Progress message", "default": ""}
                },
                "required": ["agent_id", "task_id", "status"]
            }
        ),
        types.Tool(
            name="report_blocker",
            description="Report a blocker on a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent reporting the blocker"},
                    "task_id": {"type": "string", "description": "Blocked task ID"},
                    "blocker_description": {"type": "string", "description": "Description of the blocker"},
                    "severity": {"type": "string", "description": "Blocker severity: low, medium, high", "default": "medium"}
                },
                "required": ["agent_id", "task_id", "blocker_description"]
            }
        ),
        
        # Project Monitoring Tools
        types.Tool(
            name="get_project_status",
            description="Get current project status and metrics",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        # System Health Tools
        types.Tool(
            name="ping",
            description="Check Marcus status and connectivity",
            inputSchema={
                "type": "object",
                "properties": {
                    "echo": {"type": "string", "description": "Optional message to echo back", "default": ""}
                },
                "required": []
            }
        ),
        types.Tool(
            name="check_assignment_health",
            description="Check the health of the assignment tracking system",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        # Natural Language Tools
        types.Tool(
            name="create_project",
            description="Create a complete project from natural language description",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Natural language project description or requirements"
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Name for the project board"
                    },
                    "options": {
                        "type": "object",
                        "description": "Optional project configuration",
                        "properties": {
                            "deadline": {"type": "string", "description": "Project deadline (ISO date format)"},
                            "team_size": {"type": "integer", "description": "Number of developers", "default": 3},
                            "tech_stack": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Technologies to use"
                            }
                        }
                    }
                },
                "required": ["description", "project_name"]
            }
        ),
        types.Tool(
            name="add_feature",
            description="Add a feature to existing project using natural language",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_description": {
                        "type": "string",
                        "description": "Natural language description of the feature to add"
                    },
                    "integration_point": {
                        "type": "string",
                        "description": "How to integrate the feature",
                        "enum": ["auto_detect", "after_current", "parallel", "new_phase"],
                        "default": "auto_detect"
                    }
                },
                "required": ["feature_description"]
            }
        )
    ]


async def handle_tool_call(
    name: str,
    arguments: Optional[Dict[str, Any]],
    state: Any
) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool calls by routing to appropriate tool functions.
    
    Args:
        name: Name of the tool to call
        arguments: Tool arguments
        state: Marcus server state instance
        
    Returns:
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
                state=state
            )
        
        elif name == "get_agent_status":
            result = await get_agent_status(
                agent_id=arguments.get("agent_id"),
                state=state
            )
        
        elif name == "list_registered_agents":
            result = await list_registered_agents(state=state)
        
        # Task management tools
        elif name == "request_next_task":
            result = await request_next_task(
                agent_id=arguments.get("agent_id"),
                state=state
            )
        
        elif name == "report_task_progress":
            result = await report_task_progress(
                agent_id=arguments.get("agent_id"),
                task_id=arguments.get("task_id"),
                status=arguments.get("status"),
                progress=arguments.get("progress", 0),
                message=arguments.get("message", ""),
                state=state
            )
        
        elif name == "report_blocker":
            result = await report_blocker(
                agent_id=arguments.get("agent_id"),
                task_id=arguments.get("task_id"),
                blocker_description=arguments.get("blocker_description"),
                severity=arguments.get("severity", "medium"),
                state=state
            )
        
        # Project monitoring tools
        elif name == "get_project_status":
            result = await get_project_status(state=state)
        
        # System health tools
        elif name == "ping":
            result = await ping(
                echo=arguments.get("echo", ""),
                state=state
            )
        
        elif name == "check_assignment_health":
            result = await check_assignment_health(state=state)
        
        # Natural language tools
        elif name == "create_project":
            result = await create_project(
                description=arguments.get("description"),
                project_name=arguments.get("project_name"),
                options=arguments.get("options"),
                state=state
            )
        
        elif name == "add_feature":
            result = await add_feature(
                feature_description=arguments.get("feature_description"),
                integration_point=arguments.get("integration_point", "auto_detect"),
                state=state
            )
        
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
        
    except Exception as e:
        # Log the full traceback for debugging
        import traceback
        print(f"\n{'='*80}")
        print(f"TOOL EXECUTION ERROR in {name}")
        print(f"Error: {str(e)}")
        print(f"{'='*80}")
        traceback.print_exc()
        print(f"{'='*80}\n")
        
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "error": f"Tool execution failed: {str(e)}",
                "tool": name
            }, indent=2)
        )]