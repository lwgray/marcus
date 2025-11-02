"""Natural Language Processing Tools for Marcus MCP.

This module contains tools for natural language project/task creation:
- create_project: Create complete project from natural language description
- add_feature: Add feature to existing project using natural language
"""

import logging
from typing import Any, Dict, Optional

from src.integrations.nlp_tools import add_feature_natural_language

logger = logging.getLogger(__name__)

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
    Create a NEW project from natural language description.

    This tool ALWAYS creates a new project - it does not search for or reuse
    existing projects. For working with existing projects, use select_project
    or create_tasks tools instead.

    Uses AI to parse natural language project requirements and automatically:
    - Breaks down into tasks and subtasks
    - Assigns priorities and dependencies
    - Estimates time requirements
    - Creates organized kanban board structure
    - Registers the new project in Marcus

    Parameters
    ----------
    description : str
        Natural language project description
    project_name : str
        Name for the new project
    options : Optional[Dict[str, Any]]
        Optional configuration dictionary with the following keys:

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

        On error:
        {
            "success": False,
            "error": str
        }

    Examples
    --------
    Create new project with defaults:
        >>> create_project(
        ...     description="Build a REST API with user authentication",
        ...     project_name="MyAPI"
        ... )

    Create with advanced configuration:
        >>> create_project(
        ...     description="E-commerce platform with payment integration",
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
    from datetime import datetime, timezone

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

    start_time = datetime.now(timezone.utc)

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
            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

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

            # Add Marcus project_id from registry for auto-select
            if result.get("success") and "project_id" not in result:
                if hasattr(state, "project_registry"):
                    active_project = await state.project_registry.get_active_project()
                    if active_project:
                        result["project_id"] = active_project.id
                        logger.info(
                            f"Added project_id to result: {result['project_id']}"
                        )

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

        # Auto-select the newly created project
        if result.get("success") and result.get("project_id"):
            from .project_management import select_project

            logger.info(
                f"🔄 AUTO-SELECT STARTING for project '{project_name}' "
                f"(ID: {result['project_id']})"
            )
            state.log_event(
                "create_project_auto_select_starting",
                {
                    "project_name": project_name,
                    "project_id": result["project_id"],
                },
            )

            select_result = await select_project(
                state, {"project_id": result["project_id"]}
            )

            # Log result - success or failure
            if select_result.get("success"):
                logger.info(
                    f"✅ AUTO-SELECT SUCCEEDED for project '{project_name}' "
                    f"(ID: {result['project_id']})"
                )
                state.log_event(
                    "create_project_auto_select_succeeded",
                    {
                        "project_name": project_name,
                        "project_id": result["project_id"],
                    },
                )
            else:
                # Log if selection failed, but don't fail the whole operation
                logger.warning(
                    f"⚠️  AUTO-SELECT FAILED for project '{project_name}' "
                    f"(ID: {result['project_id']}): {select_result.get('error')}"
                )
                state.log_event(
                    "create_project_auto_select_failed",
                    {
                        "project_name": project_name,
                        "project_id": result["project_id"],
                        "error": select_result.get("error"),
                    },
                )
        else:
            # Log why auto-select was skipped
            has_success = result.get("success") if isinstance(result, dict) else False
            has_project_id = (
                "project_id" in result if isinstance(result, dict) else False
            )
            logger.warning(
                f"⚠️  AUTO-SELECT SKIPPED for project '{project_name}': "
                f"has_success={has_success}, has_project_id={has_project_id}"
            )
            state.log_event(
                "create_project_auto_select_skipped",
                {
                    "project_name": project_name,
                    "has_success": (
                        result.get("success") if isinstance(result, dict) else False
                    ),
                    "has_project_id": (
                        "project_id" in result if isinstance(result, dict) else False
                    ),
                    "result_type": type(result).__name__,
                },
            )

        return result

    except Exception as exc:
        # Track error (non-blocking)
        if hasattr(state, "pipeline_visualizer"):
            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
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
            state, {"name": project_name, "board_name": board_name}
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
                "hint": "Use select_project or provide name parameter",
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

    # Use AI to intelligently parse and break down the task description
    try:
        # Use the same natural language project creator that create_project uses
        from src.integrations.nlp_tools import NaturalLanguageProjectCreator

        # Create a temporary project name for AI processing
        temp_project_name = current_project.name or "Task Breakdown"

        # Get subtask_manager if available (GH-62 fix)
        subtask_manager = getattr(state, "subtask_manager", None)

        # Initialize project creator
        creator = NaturalLanguageProjectCreator(
            kanban_client=kanban_client,
            ai_engine=state.ai_engine,
            subtask_manager=subtask_manager,
        )

        # Use the creator to parse tasks from description
        result = await creator.create_project_from_description(
            description=task_description,
            project_name=temp_project_name,
            options=options or {},
        )

        if not result.get("success"):
            return result

        return {
            "success": True,
            "tasks_created": result.get("tasks_created", 0),
            "board": {
                "project_id": project_id,
                "board_id": board_id,
                "board_name": board_name or current_board_name,
            },
            "tasks": result.get("tasks", []),
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create task: {str(e)}",
        }
