"""Natural Language Processing Tools for Marcus MCP.

This module contains tools for natural language project/task creation:
- create_project: Create complete project from natural language description
- add_feature: Add feature to existing project using natural language
"""

from typing import Any, Dict, Optional

from src.integrations.nlp_tools import add_feature_natural_language

# Import PipelineStage with fallback for compatibility
try:
    from src.visualization.pipeline_flow import PipelineStage
except ImportError:
    # Fallback if PipelineStage is not available
    class PipelineStage:  # type: ignore[no-redef]
        """Fallback for PipelineStage when not available."""

        MCP_REQUEST = "mcp_request"
        TASK_COMPLETION = "task_completion"


async def create_project(
    description: str, project_name: str, options: Optional[Dict[str, Any]], state: Any
) -> Dict[str, Any]:
    """
    Create a complete project from natural language description.

    Includes smart project discovery.

    Uses AI to parse natural language project requirements and automatically:
    - Discovers existing projects by name (exact and fuzzy matching)
    - Breaks down into tasks and subtasks
    - Assigns priorities and dependencies
    - Estimates time requirements
    - Creates organized kanban board structure
    - Auto-creates and registers new projects if needed

    Project Discovery Workflow:
    1. If options.project_id provided → use that specific project
    2. If options.mode="new_project" → force creation (skip discovery)
    3. Otherwise → search for existing projects by name:
       - Exact match found → automatically use existing project
       - Similar matches found → return suggestions, require clarification
       - No matches → create and register new project

    Parameters
    ----------
    description : str
        Natural language project description
    project_name : str
        Name for the project (used for discovery and creation)
    options : Optional[Dict[str, Any]]
        Optional configuration dictionary with the following keys:

        Project Selection:
        - project_id (str): Explicit project ID to use (skips discovery)
        - mode (str): Creation mode - "auto" (default), "new_project"

        Provider Config:
        - provider (str): Kanban provider - "planka" (default), "github", "linear"
        - planka_project_name (str): Custom Planka project name
          (defaults to project_name)
        - planka_board_name (str): Custom Planka board name
          (defaults to "Main Board")

        Project Settings:
        - complexity (str): "prototype", "standard" (default), "enterprise"
        - deployment (str): "none" (default), "internal", "production"
        - team_size (int): Team size 1-20 for estimation (default: 1)
        - tech_stack (List[str]): Technologies to use (e.g., ["React", "Python"])
        - deadline (str): Project deadline in YYYY-MM-DD format
        - tags (List[str]): Tags for project organization

        Legacy Options:
        - deployment_target (str): "local", "dev", "prod", "remote"
          (mapped to deployment setting for backwards compatibility)
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        On success:
        {
            "success": True,
            "project_id": str,  # Marcus project ID
            "tasks_created": int,
            "board": {
                "project_id": str,  # Provider project ID
                "board_id": str,
                "provider": str
            },
            "phases": List[str],
            "estimated_duration": str,
            "complexity_score": float
        }

        On similar matches found:
        {
            "success": False,
            "action": "found_similar",
            "message": str,
            "matches": List[Dict],
            "next_steps": List[str],
            "hint": str
        }

        On error:
        {
            "success": False,
            "error": str
        }

    Examples
    --------
    Auto-discover or create:
        >>> create_project(
        ...     description="Build a REST API",
        ...     project_name="MyAPI"
        ... )

    Force new project creation:
        >>> create_project(
        ...     description="Build OAuth 2.0 system",
        ...     project_name="MyAPI-v2",
        ...     options={"mode": "new_project"}
        ... )

    Use specific existing project:
        >>> create_project(
        ...     description="Add password reset",
        ...     project_name="MyAPI",
        ...     options={"project_id": "proj-123"}
        ... )

    Advanced configuration:
        >>> create_project(
        ...     description="E-commerce platform",
        ...     project_name="ShopFlow",
        ...     options={
        ...         "complexity": "enterprise",
        ...         "deployment": "production",
        ...         "team_size": 5,
        ...         "tech_stack": ["React", "Node.js", "PostgreSQL"],
        ...         "tags": ["client:acme", "priority:high"]
        ...     }
        ... )
    """
    import uuid
    from datetime import datetime

    # Validate required parameters
    if (
        not description
        or not description.strip()
        or description.lower() in ["test", "dummy", "example", "help"]
    ):
        return {
            "success": False,
            "error": "Please provide a real project description",
            "usage": {
                "description": "Natural language description of what you want to build",
                "project_name": "A short name for your project",
                "options": {
                    "complexity": "prototype | standard | enterprise",
                    "deployment": "none | internal | production",
                    "team_size": "1-20 (optional)",
                    "tech_stack": ["array", "of", "technologies"],
                    "deadline": "YYYY-MM-DD",
                },
            },
            "examples": [
                {
                    "description": (
                        "Create a task management app with user "
                        "authentication and team collaboration"
                    ),
                    "project_name": "TeamTasks",
                    "options": {
                        "complexity": "standard",
                        "deployment": "internal",
                        "planka_project_name": "Team Tasks Project",
                        "planka_board_name": "Development Board",
                    },
                },
                {
                    "description": "Build a simple blog with markdown support",
                    "project_name": "MiniBlog",
                    "options": {"complexity": "prototype", "deployment": "none"},
                },
                {
                    "description": (
                        "Develop an e-commerce platform with inventory "
                        "management, payment processing, and analytics"
                    ),
                    "project_name": "ShopFlow",
                    "options": {
                        "complexity": "enterprise",
                        "deployment": "production",
                        "tech_stack": [
                            "React",
                            "Node.js",
                            "PostgreSQL",
                            "Stripe",
                        ],
                        "team_size": 5,
                        "planka_project_name": "ShopFlow Production",
                    },
                },
            ],
        }

    if not project_name or not project_name.strip():
        return {
            "success": False,
            "error": "Missing required parameter: 'project_name'",
            "hint": "Please provide a name for your project",
        }

    # Validate options if provided
    if options:
        # Validate complexity
        if "complexity" in options:
            valid_complexity = ["prototype", "standard", "enterprise"]
            if options["complexity"] not in valid_complexity:
                return {
                    "success": False,
                    "error": f"Invalid complexity: '{options['complexity']}'",
                    "valid_options": valid_complexity,
                    "description": {
                        "prototype": "Quick MVP with minimal features (3-8 tasks)",
                        "standard": "Full-featured project (10-20 tasks)",
                        "enterprise": "Production-ready with all features (25+ tasks)",
                    },
                }

        # Validate deployment
        if "deployment" in options:
            valid_deployment = ["none", "internal", "production"]
            if options["deployment"] not in valid_deployment:
                return {
                    "success": False,
                    "error": f"Invalid deployment: '{options['deployment']}'",
                    "valid_options": valid_deployment,
                    "description": {
                        "none": "Local development only",
                        "internal": "Deploy for team/staging use",
                        "production": "Deploy for customers with full infrastructure",
                    },
                }

        # Validate team_size
        if "team_size" in options:
            try:
                team_size = int(options["team_size"])
                if team_size < 1 or team_size > 20:
                    return {
                        "success": False,
                        "error": "team_size must be between 1 and 20",
                        "current_value": options["team_size"],
                    }
            except (ValueError, TypeError):
                return {
                    "success": False,
                    "error": "team_size must be a number",
                    "current_value": options["team_size"],
                }

    # Start tracking pipeline flow
    flow_id = str(uuid.uuid4())
    if hasattr(state, "pipeline_visualizer"):
        # Make pipeline tracking non-blocking
        def track_start() -> None:
            state.pipeline_visualizer.start_flow(flow_id, project_name)
            # Track the MCP request
            state.pipeline_visualizer.add_event(
                flow_id=flow_id,
                stage=PipelineStage.MCP_REQUEST,
                event_type="create_project_request",
                data={
                    "project_name": project_name,
                    "description_length": len(description),
                    "options": options or {},
                },
                status="completed",
            )

        # Run tracking synchronously to avoid hanging
        # This is fast enough to not impact response time
        track_start()

        # Also log to real-time log for UI server
        state.log_event(
            "pipeline_flow_started",
            {
                "flow_id": flow_id,
                "project_name": project_name,
                "stage": "mcp_request",
                "event_type": "create_project_request",
            },
        )

    start_time = datetime.now()

    try:
        # Create project using natural language processing with pipeline tracking
        from src.integrations.pipeline_tracked_nlp import (
            create_project_from_natural_language_tracked,
        )

        # Log before calling the function
        state.log_event("create_project_calling", {"project_name": project_name})

        # Ensure we await the result properly
        try:
            result = await create_project_from_natural_language_tracked(
                description=description,
                project_name=project_name,
                state=state,
                options=options,
                flow_id=flow_id,
            )
        except Exception as e:
            state.log_event(
                "create_project_exception",
                {
                    "project_name": project_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            # Re-raise to be handled by outer try/catch
            raise
        else:
            # Log after function returns
            state.log_event(
                "create_project_returned",
                {
                    "project_name": project_name,
                    "success": result.get("success", False) if result else False,
                    "task_count": result.get("tasks_created", 0) if result else 0,
                },
            )

        # Log immediately before returning to MCP
        state.log_event(
            "create_project_returning_to_mcp",
            {
                "project_name": project_name,
                "result_keys": (
                    list(result.keys()) if isinstance(result, dict) else "not_dict"
                ),
                "success": (
                    result.get("success", False) if isinstance(result, dict) else False
                ),
            },
        )

        # Track successful completion (non-blocking)
        if hasattr(state, "pipeline_visualizer"):
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            def track_completion() -> None:
                state.pipeline_visualizer.add_event(
                    flow_id=flow_id,
                    stage=PipelineStage.TASK_COMPLETION,
                    event_type="pipeline_completed",
                    data={
                        "success": result.get("success", False),
                        "task_count": result.get(
                            "tasks_created", result.get("task_count", 0)
                        ),
                        "total_duration_ms": duration_ms,
                    },
                    duration_ms=duration_ms,
                    status="completed",
                )
                # Complete the flow
                state.pipeline_visualizer.complete_flow(flow_id)

            # Run tracking synchronously to avoid hanging
            track_completion()

        # Normalize result to include task_count
        if isinstance(result, dict):
            if "tasks_created" in result and "task_count" not in result:
                result["task_count"] = result["tasks_created"]

        # Final log before return
        state.log_event(
            "create_project_final_return",
            {
                "project_name": project_name,
                "returning": True,
                "result_type": type(result).__name__,
            },
        )

        # No need to wait for background tasks
        # They are fire-and-forget for tracking purposes

        return result

    except Exception as exc:
        # Track error (non-blocking)
        if hasattr(state, "pipeline_visualizer"):
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            error_type = type(exc).__name__
            error_str = str(exc)

            def track_error() -> None:
                state.pipeline_visualizer.add_event(
                    flow_id=flow_id,
                    stage=PipelineStage.TASK_COMPLETION,
                    event_type="pipeline_failed",
                    data={"error_type": error_type},
                    duration_ms=duration_ms,
                    status="failed",
                    error=error_str,
                )

            # Run tracking synchronously to avoid hanging
            track_error()

        raise


async def add_feature(
    feature_description: str, integration_point: str, state: Any
) -> Dict[str, Any]:
    """
    Add a feature to existing project using natural language.

    Uses AI to understand feature requirements and:
    - Creates appropriate tasks for implementation
    - Integrates with existing project structure
    - Sets dependencies and priorities
    - Updates project timeline

    Parameters
    ----------
    feature_description : str
        Natural language description of the feature
    integration_point : str
        How to integrate (auto_detect, after_current, parallel, new_phase)
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dict with created feature tasks and integration details
    """
    # Add feature using natural language processing
    return await add_feature_natural_language(
        feature_description=feature_description,
        integration_point=integration_point,
        state=state,
    )


async def create_tasks(
    task_description: str,
    board_name: Optional[str] = None,
    project_name: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Create tasks on an existing project and board using natural language.

    This tool is similar to create_project but works on existing projects.
    It can either use an existing board or create a new board within the project.

    Parameters
    ----------
    task_description : str
        Natural language description of the tasks to create
    board_name : Optional[str]
        Board name to use. If not provided, uses the active project's board.
        If the board doesn't exist, it will be created.
    project_name : Optional[str]
        Project name to use. If not provided, uses the active project.
    options : Optional[Dict[str, Any]]
        Optional configuration:
        - complexity: "prototype", "standard" (default), "enterprise"
        - team_size: 1-20 for estimation (default: 1)
        - create_board: bool - Force create new board (default: False)
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        On success:
        {
            "success": True,
            "tasks_created": int,
            "board": {
                "project_id": str,
                "board_id": str,
                "board_name": str
            }
        }

        On error:
        {
            "success": False,
            "error": str
        }

    Examples
    --------
    Create tasks on active project's active board:
        >>> create_tasks(
        ...     task_description="Add user authentication with OAuth2"
        ... )

    Create tasks on specific project and board:
        >>> create_tasks(
        ...     task_description="Implement payment processing",
        ...     project_name="E-commerce",
        ...     board_name="Sprint 2"
        ... )

    Create tasks on new board:
        >>> create_tasks(
        ...     task_description="Add admin dashboard",
        ...     board_name="Admin Features",
        ...     options={"create_board": True}
        ... )
    """
    if not task_description or not task_description.strip():
        return {
            "success": False,
            "error": "Please provide a task description",
            "hint": "Describe the tasks you want to create in natural language",
        }

    options = options or {}

    # Get or validate project
    if project_name:
        # Select the specified project
        from .project_management import select_project

        select_result = await select_project(
            state, {"project_name": project_name, "board_name": board_name}
        )
        if not select_result.get("success"):
            return select_result
    else:
        # Use active project
        active_project = await state.project_registry.get_active_project()
        if not active_project:
            return {
                "success": False,
                "error": "No active project. Please select a project first.",
                "hint": "Use select_project or provide project_name parameter",
            }

    # Get current project info
    current_project = await state.project_registry.get_active_project()
    if not current_project:
        return {
            "success": False,
            "error": "Failed to get current project",
        }

    # Handle board selection/creation
    kanban_client = await state.project_manager.get_kanban_client()
    if not kanban_client:
        return {
            "success": False,
            "error": "No kanban client available",
        }

    project_id = current_project.provider_config.get("project_id")
    board_id = current_project.provider_config.get("board_id")
    current_board_name = current_project.provider_config.get("board_name")

    # Check if we need to use a different board or create one
    if board_name and board_name != current_board_name:
        # Need to switch to or create the specified board
        if options.get("create_board", False):
            # Create new board
            try:
                new_board = await kanban_client.create_board(
                    project_id=project_id, name=board_name
                )
                board_id = new_board.get("id")
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to create board: {str(e)}",
                }
        else:
            # Try to find existing board by name
            try:
                boards = await kanban_client.list_boards(project_id=project_id)
                matching_board = next(
                    (b for b in boards if b.get("name") == board_name), None
                )
                if matching_board:
                    board_id = matching_board.get("id")
                else:
                    return {
                        "success": False,
                        "error": (
                            f"Board '{board_name}' not found in project "
                            f"'{current_project.name}'"
                        ),
                        "hint": "Set options.create_board=True to create a new board",
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to list boards: {str(e)}",
                }

    if not board_id:
        return {
            "success": False,
            "error": "No board_id available",
        }

    # For now, create a simple task with the description
    # TODO: Integrate with AI task parsing in the future
    try:
        # Create a single task with the description
        task = await kanban_client.create_task(
            board_id=board_id,
            name=task_description[:100],  # Use first 100 chars as name
            description=task_description,
            priority="medium",
            labels=[],
        )

        return {
            "success": True,
            "tasks_created": 1,
            "board": {
                "project_id": project_id,
                "board_id": board_id,
                "board_name": board_name or current_board_name,
            },
            "tasks": [task],
            "note": (
                "Created a single task with your description. "
                "For AI-powered multi-task generation from descriptions, "
                "use create_project or add_feature instead."
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create task: {str(e)}",
        }
