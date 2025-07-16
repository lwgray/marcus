"""
Natural Language Processing Tools for Marcus MCP

This module contains tools for natural language project/task creation:
- create_project: Create complete project from natural language description
- add_feature: Add feature to existing project using natural language
"""

import asyncio
from typing import Any, Dict, Optional

from src.integrations.nlp_tools import add_feature_natural_language
# Use type: ignore to suppress the export warning and avoid redefinition
try:
    from src.visualization.pipeline_flow import PipelineStage  # type: ignore
except ImportError:
    # Fallback if PipelineStage is not available
    class PipelineStage:  # type: ignore[misc]
        MCP_REQUEST = "mcp_request"
        TASK_COMPLETION = "task_completion"


async def create_project(
    description: str, project_name: str, options: Optional[Dict[str, Any]], state: Any
) -> Dict[str, Any]:
    """
    Create a complete project from natural language description.

    Uses AI to parse natural language project requirements and automatically:
    - Breaks down into tasks and subtasks
    - Assigns priorities and dependencies
    - Estimates time requirements
    - Creates organized kanban board structure

    Args:
        description: Natural language project description
        project_name: Name for the project board
        options: Optional configuration (deadline, team_size, tech_stack,
                 deployment_target)
            - deployment_target: "local" (default), "dev", "prod", "remote"
                - local: No deployment tasks, just local development
                - dev: Basic deployment to development environment
                - prod: Full production deployment with monitoring, scaling
                - remote: Deploy to cloud/remote servers
        state: Marcus server state instance

    Returns:
        Dict with created project details and task list
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
                    "description": "Create a task management app with user authentication and team collaboration",
                    "project_name": "TeamTasks",
                    "options": {"complexity": "standard", "deployment": "internal"},
                },
                {
                    "description": "Build a simple blog with markdown support",
                    "project_name": "MiniBlog",
                    "options": {"complexity": "prototype", "deployment": "none"},
                },
                {
                    "description": "Develop an e-commerce platform with inventory management, payment processing, and analytics",
                    "project_name": "ShopFlow",
                    "options": {
                        "complexity": "enterprise",
                        "deployment": "production",
                        "tech_stack": ["React", "Node.js", "PostgreSQL", "Stripe"],
                        "team_size": 5,
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

        # Run in background without blocking
        asyncio.create_task(asyncio.to_thread(track_start))

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

        # Ensure we have a proper response structure
        if result is None:
            result = {
                "success": False,
                "error": "No result returned from task creation",
            }

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

            # Run in background without blocking
            asyncio.create_task(asyncio.to_thread(track_completion))

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

            # Run in background without blocking
            asyncio.create_task(asyncio.to_thread(track_error))

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

    Args:
        feature_description: Natural language description of the feature
        integration_point: How to integrate (auto_detect, after_current,
                           parallel, new_phase)
        state: Marcus server state instance

    Returns:
        Dict with created feature tasks and integration details
    """
    # Add feature using natural language processing
    return await add_feature_natural_language(
        feature_description=feature_description,
        integration_point=integration_point,
        state=state,
    )
