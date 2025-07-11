"""
Natural Language Processing Tools for Marcus MCP

This module contains tools for natural language project/task creation:
- create_project: Create complete project from natural language description
- add_feature: Add feature to existing project using natural language
"""

from typing import Any, Dict, List, Optional

from src.integrations.nlp_tools import (
    add_feature_natural_language,
    create_project_from_natural_language,
)
from src.visualization.pipeline_flow import PipelineStage


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
        options: Optional configuration (deadline, team_size, tech_stack, deployment_target)
            - deployment_target: "local" (default), "dev", "prod", or "remote"
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

    # Start tracking pipeline flow
    flow_id = str(uuid.uuid4())
    if hasattr(state, "pipeline_visualizer"):
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

        result = await create_project_from_natural_language_tracked(
            description=description,
            project_name=project_name,
            state=state,
            options=options,
            flow_id=flow_id,
        )

        # Track successful completion
        if hasattr(state, "pipeline_visualizer"):
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            state.pipeline_visualizer.add_event(
                flow_id=flow_id,
                stage=PipelineStage.TASK_COMPLETION,
                event_type="pipeline_completed",
                data={
                    "success": result.get("success", False),
                    "task_count": result.get("task_count", 0),
                    "total_duration_ms": duration_ms,
                },
                duration_ms=duration_ms,
                status="completed",
            )

            # Complete the flow
            state.pipeline_visualizer.complete_flow(flow_id)

        return result

    except Exception as e:
        # Track error
        if hasattr(state, "pipeline_visualizer"):
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            state.pipeline_visualizer.add_event(
                flow_id=flow_id,
                stage=PipelineStage.TASK_COMPLETION,
                event_type="pipeline_failed",
                data={"error_type": type(e).__name__},
                duration_ms=duration_ms,
                status="failed",
                error=str(e),
            )

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
        integration_point: How to integrate (auto_detect, after_current, parallel, new_phase)
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
