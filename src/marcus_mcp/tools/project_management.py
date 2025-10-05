"""
Project Management Tools for Marcus MCP.

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
    List all available projects.

    Parameters
    ----------
    server : Any
        MarcusServer instance
    arguments : Dict[str, Any]
        Optional filters:
        - filter_tags: List of tags to filter by
        - provider: Provider to filter by (planka, linear, github)

    Returns
    -------
    List[Dict[str, Any]]
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
    Switch to a different project.

    Parameters
    ----------
    server : Any
        MarcusServer instance
    arguments : Dict[str, Any]
        - project_id: ID of project to switch to
        - project_name: Alternative - name of project (if unique)

    Returns
    -------
    Dict[str, Any]
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
    Get the currently active project.

    Parameters
    ----------
    server : Any
        MarcusServer instance
    arguments : Dict[str, Any]
        None required

    Returns
    -------
    Dict[str, Any]
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
    Add a new project configuration.

    Parameters
    ----------
    server : Any
        MarcusServer instance
    arguments : Dict[str, Any]
        - name: Project name
        - provider: Provider type (planka, linear, github)
        - config: Provider-specific configuration
        - tags: Optional list of tags
        - make_active: Whether to switch to this project (default: True)

    Returns
    -------
    Dict[str, Any]
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
    Remove a project from the registry.

    Parameters
    ----------
    server : Any
        MarcusServer instance
    arguments : Dict[str, Any]
        - project_id: ID of project to remove
        - confirm: Must be True to confirm deletion

    Returns
    -------
    Dict[str, Any]
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
    Update project configuration.

    Parameters
    ----------
    server : Any
        MarcusServer instance
    arguments : Dict[str, Any]
        - project_id: ID of project to update
        - name: New name (optional)
        - tags: New tags (optional)
        - config: Updated provider config (optional)

    Returns
    -------
    Dict[str, Any]
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


async def get_task_count(server: Any, project_id: str) -> int:
    """
    Get count of tasks for a project.

    Parameters
    ----------
    server : Any
        MarcusServer instance
    project_id : str
        Project ID

    Returns
    -------
    int
        Number of tasks in the project
    """
    try:
        # Switch to project to get its task count
        current_project = await server.project_registry.get_active_project()
        current_id = current_project.id if current_project else None

        # Temporarily switch to target project
        await server.project_manager.switch_project(project_id)
        kanban_client = await server.project_manager.get_kanban_client()

        # Get task count
        tasks = await kanban_client.get_available_tasks()
        task_count = len(tasks) if tasks else 0

        # Switch back to original project
        if current_id:
            await server.project_manager.switch_project(current_id)

        return task_count
    except Exception as e:
        logger.warning(f"Failed to get task count for project {project_id}: {e}")
        return 0


def calculate_similarity(query: str, target: str) -> float:
    """
    Calculate simple similarity score between two strings.

    Parameters
    ----------
    query : str
        Query string
    target : str
        Target string to compare

    Returns
    -------
    float
        Similarity score (0.0 to 1.0)

    Notes
    -----
    Uses simple substring matching. Can be enhanced with
    fuzzy matching algorithms (Levenshtein, etc.) if needed.
    """
    query_lower = query.lower()
    target_lower = target.lower()

    # Exact match
    if query_lower == target_lower:
        return 1.0

    # Query is substring of target
    if query_lower in target_lower:
        return 0.8

    # Target is substring of query
    if target_lower in query_lower:
        return 0.7

    # Count common words
    query_words = set(query_lower.split())
    target_words = set(target_lower.split())
    common_words = query_words & target_words

    if not query_words:
        return 0.0

    return len(common_words) / len(query_words)


async def select_project(server: Any, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Select an existing project to work on.

    This is the primary tool for choosing which project to work on.
    It searches for projects by name or ID and switches context.

    Parameters
    ----------
    server : Any
        MarcusServer instance
    arguments : Dict[str, Any]
        - project_name: Name to search for (optional if project_id provided)
        - project_id: Exact project ID (optional if project_name provided)

    Returns
    -------
    Dict[str, Any]
        Success status and project details with task count

    Examples
    --------
    >>> # Select by name
    >>> result = await select_project(server, {"project_name": "MyAPI"})

    >>> # Select by ID
    >>> result = await select_project(server, {"project_id": "proj-123"})
    """
    project_name = arguments.get("project_name")
    project_id = arguments.get("project_id")

    if not project_name and not project_id:
        return {
            "success": False,
            "error": "Either project_name or project_id must be provided",
        }

    # If project_id provided, use it directly
    if project_id:
        try:
            await server.project_manager.switch_project(project_id)
            server.kanban_client = await server.project_manager.get_kanban_client()

            # Get project details
            current = await server.project_registry.get_active_project()
            task_count = (
                len(server.project_tasks) if hasattr(server, "project_tasks") else 0
            )

            return {
                "success": True,
                "action": "selected_existing",
                "project": {
                    "id": current.id,
                    "name": current.name,
                    "provider": current.provider,
                    "task_count": task_count,
                },
                "message": f"Selected project '{current.name}' - ready to work",
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to select project: {str(e)}"}

    # Otherwise, search by name using find_or_create_project
    discovery_result = await find_or_create_project(
        server=server,
        arguments={"project_name": project_name, "create_if_missing": False},
    )

    if discovery_result["action"] == "found_existing":
        # Switch to the found project
        await server.project_manager.switch_project(discovery_result["project"]["id"])
        server.kanban_client = await server.project_manager.get_kanban_client()

        # Add task count
        project_info = discovery_result["project"].copy()
        task_count = (
            len(server.project_tasks) if hasattr(server, "project_tasks") else 0
        )
        project_info["task_count"] = task_count

        return {
            "success": True,
            "action": "selected_existing",
            "project": project_info,
            "message": f"Selected project '{discovery_result['project']['name']}' - ready to work",
        }

    elif discovery_result["action"] == "found_similar":
        # Return suggestions
        return {
            "success": False,
            "action": "found_similar",
            "message": discovery_result["suggestion"],
            "matches": discovery_result["matches"],
            "next_steps": discovery_result["next_steps"],
            "hint": "To select: use exact project_name or provide project_id",
        }

    else:  # not_found
        return {
            "success": False,
            "action": "not_found",
            "message": f"Project '{project_name}' not found",
            "hint": "Use list_projects to see available projects, or create_project to create a new one",
        }


async def find_or_create_project(
    server: Any, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Smart helper to find existing project or guide creation.

    This tool helps users navigate the "which project?" decision tree.
    It searches for existing projects by name and provides guidance
    on how to proceed based on what it finds.

    Parameters
    ----------
    server : Any
        MarcusServer instance
    arguments : Dict[str, Any]
        - project_name: Name to search for (required)
        - create_if_missing: Auto-create if not found (default: False)
        - provider: Provider for auto-creation (default: "planka")

    Returns
    -------
    Dict[str, Any]
        Dictionary with action and relevant information:
        - action: "found_existing" | "found_similar" | "not_found" | "guide_creation"
        - project: Project details (if found)
        - matches: List of similar projects (if fuzzy match)
        - next_steps: Guidance on what to do next

    Examples
    --------
    >>> # Search for exact project
    >>> result = await find_or_create_project(
    ...     server,
    ...     {"project_name": "MyAPI"}
    ... )
    >>> if result["action"] == "found_existing":
    ...     project_id = result["project"]["id"]

    >>> # Get creation guidance
    >>> result = await find_or_create_project(
    ...     server,
    ...     {"project_name": "NewProject", "create_if_missing": True}
    ... )
    >>> if result["action"] == "guide_creation":
    ...     print(result["options"])
    """
    project_name = arguments.get("project_name")
    create_if_missing = arguments.get("create_if_missing", False)

    if not project_name:
        return {
            "success": False,
            "error": "project_name is required",
            "usage": "find_or_create_project(project_name='MyProject')",
        }

    # Search for existing projects
    projects = await server.project_registry.list_projects()
    exact_matches = [p for p in projects if p.name == project_name]
    fuzzy_matches = [
        p
        for p in projects
        if project_name.lower() in p.name.lower() and p not in exact_matches
    ]

    if exact_matches:
        # Found exact match
        project = exact_matches[0]
        task_count = await get_task_count(server, project.id)

        return {
            "action": "found_existing",
            "project": {
                "id": project.id,
                "name": project.name,
                "provider": project.provider,
                "task_count": task_count,
            },
            "next_steps": [
                f"Use project: switch_project(project_id='{project.id}')",
                (
                    f"Add tasks: create_project(..., "
                    f"options={{'project_id': '{project.id}'}})"
                ),
            ],
        }

    elif fuzzy_matches:
        # Found similar projects
        return {
            "action": "found_similar",
            "matches": [
                {
                    "id": p.id,
                    "name": p.name,
                    "provider": p.provider,
                    "similarity": calculate_similarity(project_name, p.name),
                }
                for p in fuzzy_matches
            ],
            "suggestion": "Did you mean one of these projects?",
            "next_steps": [
                "Use similar: switch_project(project_name='...')",
                (f"Create new: create_project(..., " f"project_name='{project_name}')"),
            ],
        }

    else:
        # No matches found
        if create_if_missing:
            return {
                "action": "guide_creation",
                "message": f"No project '{project_name}' found. Ready to create.",
                "options": [
                    {
                        "option": "Create from description",
                        "tool": "create_project",
                        "example": (
                            f"create_project(description='...', "
                            f"project_name='{project_name}')"
                        ),
                    },
                    {
                        "option": "Connect existing Planka/GitHub project",
                        "tool": "add_project",
                        "example": (
                            f"add_project(name='{project_name}', "
                            f"provider='planka', config={{...}})"
                        ),
                    },
                ],
            }
        else:
            return {
                "action": "not_found",
                "message": f"No project named '{project_name}' found in Marcus",
                "total_projects": len(projects),
                "suggestion": "List all projects with: list_projects()",
                "next_steps": [
                    "Create new: create_project(...)",
                    "Connect existing: add_project(...)",
                    "View all: list_projects()",
                ],
            }
