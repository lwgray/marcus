"""
Project Management Tools for Marcus MCP

Provides tools for managing multiple projects, switching between them,
and handling project configurations.
"""

import logging
from typing import Any, Dict, List

from src.core.project_registry import ProjectConfig
from src.logging.conversation_logger import conversation_logger

logger = logging.getLogger(__name__)


async def list_projects(server: Any, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    List all available projects

    Args:
        server: MarcusServer instance
        arguments: Optional filters:
            - filter_tags: List of tags to filter by
            - provider: Provider to filter by (planka, linear, github)

    Returns:
        List of project summaries
    """
    filter_tags = arguments.get("filter_tags")
    provider = arguments.get("provider")

    # Get projects from registry
    projects = await server.project_registry.list_projects(
        filter_tags=filter_tags, provider=provider
    )

    # Get active project
    active_project = await server.project_registry.get_active_project()
    active_id = active_project.id if active_project else None

    # Format response
    result = []
    for project in projects:
        result.append(
            {
                "id": project.id,
                "name": project.name,
                "provider": project.provider,
                "tags": project.tags,
                "is_active": project.id == active_id,
                "last_used": project.last_used.isoformat(),
            }
        )

    # Log the query
    conversation_logger.log_pm_thinking(
        thought=f"User queried projects list - Found {len(result)} projects",
        context={
            "filter_tags": filter_tags,
            "provider": provider,
            "project_count": len(result),
        },
    )

    return result


async def switch_project(server: Any, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Switch to a different project

    Args:
        server: MarcusServer instance
        arguments:
            - project_id: ID of project to switch to
            - project_name: Alternative - name of project (if unique)

    Returns:
        Success status and project details
    """
    project_id = arguments.get("project_id")
    project_name = arguments.get("project_name")

    if not project_id and not project_name:
        return {
            "success": False,
            "error": "Either project_id or project_name must be provided",
        }

    # Find project by name if ID not provided
    if not project_id and project_name:
        projects = await server.project_registry.list_projects()
        matching = [p for p in projects if p.name.lower() == project_name.lower()]

        if not matching:
            return {
                "success": False,
                "error": f"No project found with name: {project_name}",
            }
        elif len(matching) > 1:
            return {
                "success": False,
                "error": f"Multiple projects found with name: {project_name}",
                "matching_projects": [
                    {"id": p.id, "name": p.name, "provider": p.provider}
                    for p in matching
                ],
            }
        else:
            project_id = matching[0].id

    # Switch project
    success = await server.project_manager.switch_project(project_id)

    if success:
        # Update server's kanban client reference
        server.kanban_client = await server.project_manager.get_kanban_client()

        # Get the switched project details
        project = await server.project_registry.get_project(project_id)

        return {
            "success": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "provider": project.provider,
                "tags": project.tags,
            },
        }
    else:
        return {"success": False, "error": f"Failed to switch to project: {project_id}"}


async def get_current_project(server: Any, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get the currently active project

    Args:
        server: MarcusServer instance
        arguments: None required

    Returns:
        Current project details
    """
    project = await server.project_registry.get_active_project()

    if project:
        # Get additional context
        kanban_connected = False
        if server.project_manager.active_project_id in server.project_manager.contexts:
            context = server.project_manager.contexts[
                server.project_manager.active_project_id
            ]
            kanban_connected = context.is_connected

        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "provider": project.provider,
                "tags": project.tags,
                "kanban_connected": kanban_connected,
            }
        }
    else:
        return {"project": None, "error": "No active project"}


async def add_project(server: Any, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a new project configuration

    Args:
        server: MarcusServer instance
        arguments:
            - name: Project name
            - provider: Provider type (planka, linear, github)
            - config: Provider-specific configuration
            - tags: Optional list of tags
            - make_active: Whether to switch to this project (default: True)

    Returns:
        Created project details
    """
    name = arguments.get("name")
    provider = arguments.get("provider")
    config = arguments.get("config", {})
    tags = arguments.get("tags", [])
    make_active = arguments.get("make_active", True)

    # Validate required fields
    if not name or not provider:
        return {"success": False, "error": "name and provider are required"}

    # Validate provider
    if provider not in ["planka", "linear", "github"]:
        return {"success": False, "error": f"Invalid provider: {provider}"}

    # Create project config
    project = ProjectConfig(
        id="",  # Will be generated
        name=name,
        provider=provider,
        provider_config=config,
        tags=tags,
    )

    # Add to registry
    project_id = await server.project_registry.add_project(project)

    # Log project creation
    conversation_logger.log_pm_decision(
        decision=f"Created new project '{name}'",
        rationale="User requested new project configuration",
        decision_factors={"project_id": project_id, "provider": provider, "tags": tags},
    )

    # Switch to new project if requested
    if make_active:
        await server.project_manager.switch_project(project_id)
        server.kanban_client = await server.project_manager.get_kanban_client()

    return {
        "success": True,
        "project": {
            "id": project_id,
            "name": name,
            "provider": provider,
            "tags": tags,
            "is_active": make_active,
        },
    }


async def remove_project(server: Any, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove a project from the registry

    Args:
        server: MarcusServer instance
        arguments:
            - project_id: ID of project to remove
            - confirm: Must be True to confirm deletion

    Returns:
        Success status
    """
    project_id = arguments.get("project_id")
    confirm = arguments.get("confirm", False)

    if not project_id:
        return {"success": False, "error": "project_id is required"}

    if not confirm:
        return {"success": False, "error": "Set confirm=true to delete project"}

    # Get project details before deletion
    project = await server.project_registry.get_project(project_id)
    if not project:
        return {"success": False, "error": f"Project not found: {project_id}"}

    # Check if it's the active project
    active_project = await server.project_registry.get_active_project()
    was_active = active_project and active_project.id == project_id

    # Delete project
    success = await server.project_registry.delete_project(project_id)

    if success:
        # Log deletion
        conversation_logger.log_pm_decision(
            decision=f"Deleted project '{project.name}'",
            rationale="User requested project deletion",
            decision_factors={"project_id": project_id, "was_active": was_active},
        )

        # If it was active, update server's kanban client
        if was_active:
            new_active = await server.project_registry.get_active_project()
            if new_active:
                server.kanban_client = await server.project_manager.get_kanban_client()
            else:
                server.kanban_client = None

        return {"success": True, "deleted_project": project.name}
    else:
        return {"success": False, "error": "Failed to delete project"}


async def update_project(server: Any, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update project configuration

    Args:
        server: MarcusServer instance
        arguments:
            - project_id: ID of project to update
            - name: New name (optional)
            - tags: New tags (optional)
            - config: Updated provider config (optional)

    Returns:
        Updated project details
    """
    project_id = arguments.get("project_id")

    if not project_id:
        return {"success": False, "error": "project_id is required"}

    # Build updates dict
    updates = {}
    if "name" in arguments:
        updates["name"] = arguments["name"]
    if "tags" in arguments:
        updates["tags"] = arguments["tags"]
    if "config" in arguments:
        updates["provider_config"] = arguments["config"]

    if not updates:
        return {"success": False, "error": "No updates provided"}

    # Update project
    success = await server.project_registry.update_project(project_id, updates)

    if success:
        # Get updated project
        project = await server.project_registry.get_project(project_id)

        return {
            "success": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "provider": project.provider,
                "tags": project.tags,
            },
        }
    else:
        return {"success": False, "error": f"Failed to update project: {project_id}"}
