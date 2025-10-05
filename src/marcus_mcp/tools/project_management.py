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
                # includes project_id, board_id
                "provider_config": project.provider_config,
                "tags": project.tags,
                "is_active": project.id == active_id,
                "last_used": project.last_used.isoformat(),
                "created_at": project.created_at.isoformat(),
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
        - board_name: Board name to filter by (optional, used with project_name)
        - project_id: Exact project ID (optional if project_name provided)

    Returns
    -------
    Dict[str, Any]
        Success status and project details with task count

    Examples
    --------
    >>> # Select by name
    >>> result = await select_project(server, {"project_name": "MyAPI"})

    >>> # Select by project and board name
    >>> result = await select_project(server, {
    ...     "project_name": "Engineering",
    ...     "board_name": "Sprint 1"
    ... })

    >>> # Select by ID
    >>> result = await select_project(server, {"project_id": "proj-123"})
    """
    project_name = arguments.get("project_name")
    board_name = arguments.get("board_name")
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

    # If board_name is provided, search by both project and board name
    if board_name:
        # Get all projects and filter by provider_config
        all_projects = await server.project_registry.list_projects()
        matching_projects = [
            p
            for p in all_projects
            if p.provider_config.get("project_name") == project_name
            and p.provider_config.get("board_name") == board_name
        ]

        if len(matching_projects) == 0:
            return {
                "success": False,
                "error": (
                    f"No project found with project_name='{project_name}' "
                    f"and board_name='{board_name}'"
                ),
                "hint": (
                    "Use list_projects to see available projects and boards, "
                    "or run discover_planka_projects to sync from Planka"
                ),
            }
        elif len(matching_projects) > 1:
            return {
                "success": False,
                "error": (
                    f"Multiple projects found with project_name='{project_name}' "
                    f"and board_name='{board_name}'"
                ),
                "matches": [
                    {"id": p.id, "name": p.name, "provider": p.provider}
                    for p in matching_projects
                ],
                "hint": "Use project_id to select a specific project",
            }
        else:
            # Exactly one match - select it
            selected_project = matching_projects[0]
            await server.project_manager.switch_project(selected_project.id)
            server.kanban_client = await server.project_manager.get_kanban_client()

            task_count = (
                len(server.project_tasks) if hasattr(server, "project_tasks") else 0
            )

            return {
                "success": True,
                "action": "selected_existing",
                "project": {
                    "id": selected_project.id,
                    "name": selected_project.name,
                    "provider": selected_project.provider,
                    "provider_config": selected_project.provider_config,
                    "task_count": task_count,
                },
                "message": (
                    f"Selected project '{selected_project.name}' - ready to work"
                ),
            }

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
            "message": (
                f"Selected project '{discovery_result['project']['name']}' "
                "- ready to work"
            ),
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
        # Check if auto_sync is enabled and provide helpful guidance
        auto_sync_enabled = server.config.get("auto_sync_projects", False)

        if auto_sync_enabled:
            hint = (
                f"Project '{project_name}' not found in Marcus registry. "
                "Since auto_sync_projects is enabled, you may need to run "
                "sync_projects to import projects from Planka. Use "
                "list_projects to see currently registered projects."
            )
        else:
            hint = (
                "Use list_projects to see available projects, or "
                "create_project to create a new one"
            )

        return {
            "success": False,
            "action": "not_found",
            "message": f"Project '{project_name}' not found in Marcus registry",
            "hint": hint,
        }


async def discover_planka_projects(
    server: Any, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Discover all projects from Planka automatically.

    This tool fetches all projects from your Planka instance and returns
    them in a format ready to sync into Marcus's registry. Optionally,
    you can auto-sync them immediately.

    Parameters
    ----------
    server : Any
        MarcusServer instance
    arguments : Dict[str, Any]
        - auto_sync: bool (optional) - If True, automatically syncs discovered projects

    Returns
    -------
    Dict[str, Any]
        Discovered projects and sync status

    Examples
    --------
    >>> # Just discover (no sync)
    >>> result = await discover_planka_projects(server, {})
    >>> print(f"Found {len(result['projects'])} Planka projects")

    >>> # Discover and auto-sync
    >>> result = await discover_planka_projects(server, {"auto_sync": True})
    """
    from src.integrations.providers.planka import Planka

    auto_sync = arguments.get("auto_sync", False)

    # Get Planka config
    planka_config = server.config.get("planka", {})
    if not planka_config.get("base_url"):
        return {
            "success": False,
            "error": "Planka not configured. Check config_marcus.json",
        }

    # Create temporary Planka client to fetch projects
    planka = Planka(planka_config)

    try:
        await planka.connect()

        # Get all projects from Planka
        planka_projects = await planka.client.get_projects()

        # Convert to sync format
        projects_to_sync = []
        for proj in planka_projects:
            project_id = proj.get("id")
            project_name = proj.get("name", "Unnamed Project")

            # Skip projects without IDs
            if not project_id:
                logger.warning(f"Skipping project without ID: {project_name}")
                continue

            # Fetch boards for this project
            try:
                boards = await planka.client.get_boards_for_project(project_id)
                logger.info(f"Project '{project_name}' has {len(boards)} board(s)")

                for board in boards:
                    board_id = board.get("id")
                    board_name = board.get("name", "Unnamed Board")

                    # Include board name in project name for clarity
                    full_name = f"{project_name} - {board_name}"

                    projects_to_sync.append(
                        {
                            "name": full_name,
                            "provider": "planka",
                            "config": {
                                "project_id": project_id,
                                "project_name": project_name,
                                "board_id": board_id,
                                "board_name": board_name,
                            },
                            "tags": ["discovered", "planka"],
                        }
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to get boards for project '{project_name}': {e}"
                )
                continue

        result = {
            "success": True,
            "discovered_count": len(projects_to_sync),
            "projects": projects_to_sync,
        }

        # Auto-sync if requested
        if auto_sync and projects_to_sync:
            sync_result = await sync_projects(server, {"projects": projects_to_sync})
            result["sync_result"] = sync_result

        conversation_logger.log_pm_thinking(
            thought=f"Discovered {len(projects_to_sync)} projects from Planka",
            context={"auto_sync": auto_sync, "project_count": len(projects_to_sync)},
        )

        return result

    except Exception as e:
        import traceback

        logger.error(f"Failed to discover Planka projects: {e}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        return {"success": False, "error": str(e)}
    finally:
        await planka.disconnect()


def _get_provider_key(provider: str, config: Dict[str, Any]) -> str:
    """
    Generate a unique key for a project based on provider and config.

    This key is used to identify duplicate projects.
    """
    if provider == "planka":
        return f"planka:{config.get('project_id')}:{config.get('board_id')}"
    elif provider == "github":
        return f"github:{config.get('owner')}:{config.get('repo')}"
    elif provider == "linear":
        return f"linear:{config.get('project_id')}"
    else:
        # For unknown providers, use all config values
        config_str = ":".join(f"{k}={v}" for k, v in sorted(config.items()))
        return f"{provider}:{config_str}"


async def _deduplicate_registry(server: Any) -> Dict[str, Any]:
    """
    Remove duplicate projects from the registry automatically.

    Keeps the most recently used project for each unique provider_config.

    Returns
    -------
    Dict[str, Any]
        Summary with count of duplicates removed
    """
    from collections import defaultdict

    existing_projects = await server.project_registry.list_projects()

    # Group projects by their provider key
    project_groups = defaultdict(list)
    for project in existing_projects:
        key = _get_provider_key(project.provider, project.provider_config)
        project_groups[key].append(project)

    # Find and remove duplicates
    removed = []
    for key, projects in project_groups.items():
        if len(projects) > 1:
            # Sort by last_used (most recent first)
            projects_sorted = sorted(
                projects,
                key=lambda p: p.last_used if p.last_used else p.created_at,
                reverse=True,
            )

            # Keep the first (most recently used), remove the rest
            keep = projects_sorted[0]
            duplicates = projects_sorted[1:]

            for dup in duplicates:
                await server.project_registry.delete_project(dup.id)
                removed.append({"id": dup.id, "name": dup.name, "kept": keep.name})
                logger.info(
                    f"Removed duplicate project '{dup.name}' (kept '{keep.name}')"
                )

    return {"removed_count": len(removed), "removed": removed}


async def sync_projects(server: Any, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sync projects from Planka/provider into Marcus's registry.

    This tool allows you to register existing Planka projects in Marcus
    so they appear in list_projects and can be selected with select_project.

    Automatically deduplicates existing registry entries before syncing.

    Parameters
    ----------
    server : Any
        MarcusServer instance
    arguments : Dict[str, Any]
        - projects: List of project definitions to sync:
          [{
              "name": str,
              "provider": str (planka/github/linear),
              "config": {
                  "project_id": str,
                  "board_id": str  # for planka
              },
              "tags": List[str] (optional)
          }]

    Returns
    -------
    Dict[str, Any]
        Summary of sync operation with added/updated/skipped counts

    Examples
    --------
    >>> # Sync Planka projects into Marcus
    >>> sync_projects(server, {
    ...     "projects": [
    ...         {
    ...             "name": "1st Project",
    ...             "provider": "planka",
    ...             "config": {
    ...                 "project_id": "1234567890",
    ...                 "board_id": "9876543210"
    ...             },
    ...             "tags": ["production"]
    ...         }
    ...     ]
    ... })
    """
    from src.core.project_registry import ProjectConfig
    from src.logging.conversation_logger import conversation_logger

    projects_to_sync = arguments.get("projects", [])

    if not projects_to_sync:
        return {
            "success": False,
            "error": (
                "No projects provided. Provide 'projects' array with "
                "project definitions."
            ),
        }

    # First, automatically deduplicate the registry
    dedup_result = await _deduplicate_registry(server)

    added = []
    updated = []
    skipped = []

    try:
        for proj_def in projects_to_sync:
            name = proj_def.get("name")
            provider = proj_def.get("provider", "planka")
            config = proj_def.get("config", {})
            tags = proj_def.get("tags", ["synced"])

            if not name:
                skipped.append({"error": "Missing name", "definition": proj_def})
                continue

            # Check if project already exists by provider config (not just name)
            # This prevents duplicates when project names change format
            existing_projects = await server.project_registry.list_projects()

            # Find existing project by matching provider config
            existing = None
            for p in existing_projects:
                if p.provider == provider:
                    # For Planka, match by project_id and board_id
                    if provider == "planka":
                        if p.provider_config.get("project_id") == config.get(
                            "project_id"
                        ) and p.provider_config.get("board_id") == config.get(
                            "board_id"
                        ):
                            existing = p
                            break
                    # For GitHub, match by owner and repo
                    elif provider == "github":
                        if p.provider_config.get("owner") == config.get(
                            "owner"
                        ) and p.provider_config.get("repo") == config.get("repo"):
                            existing = p
                            break
                    # For Linear, match by team_id and project_id
                    elif provider == "linear":
                        if p.provider_config.get("project_id") == config.get(
                            "project_id"
                        ):
                            existing = p
                            break

            if existing:
                # Update existing project: config, name, and tags
                existing.provider_config.update(config)
                existing.name = name  # Update name if it changed
                existing.tags = list(set(existing.tags + tags))
                # Save happens automatically via registry
                updated.append({"id": existing.id, "name": name})
            else:
                # Add new project
                project = ProjectConfig(
                    id="",  # Will be generated
                    name=name,
                    provider=provider,
                    provider_config=config,
                    tags=tags,
                )
                project_id = await server.project_registry.add_project(project)
                added.append({"id": project_id, "name": name})
    except Exception as e:
        return {"success": False, "error": str(e)}

    # Log the sync operation
    dedup_count = dedup_result.get("removed_count", 0)
    log_message = (
        f"Synced {len(added)} new projects, updated {len(updated)}, "
        f"skipped {len(skipped)}"
    )
    if dedup_count > 0:
        log_message += f", removed {dedup_count} duplicates"

    conversation_logger.log_pm_decision(
        decision=log_message,
        rationale="User requested project sync from provider",
        decision_factors={
            "added_count": len(added),
            "updated_count": len(updated),
            "skipped_count": len(skipped),
            "duplicates_removed": dedup_count,
        },
    )

    return {
        "success": True,
        "summary": {
            "added": len(added),
            "updated": len(updated),
            "skipped": len(skipped),
            "duplicates_removed": dedup_count,
        },
        "details": {
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "deduplicated": dedup_result.get("removed", []),
        },
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
