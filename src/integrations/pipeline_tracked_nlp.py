"""Pipeline-tracked Natural Language Processing.

Wraps the NLP tools with comprehensive pipeline flow tracking
for visualization of the entire processing pipeline.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from src.integrations.nlp_tools import NaturalLanguageProjectCreator
from src.visualization.pipeline_conversation_bridge import PipelineConversationBridge

try:
    from src.visualization.pipeline_flow import PipelineStage
except ImportError:
    # Fallback if PipelineStage is not available
    class PipelineStage:  # type: ignore[no-redef]
        """Fallback pipeline stage definitions."""

        MCP_REQUEST = "mcp_request"
        TASK_COMPLETION = "task_completion"


from src.visualization.shared_pipeline_events import SharedPipelineVisualizer

logger = logging.getLogger(__name__)


class PipelineTrackedProjectCreator:
    """Wrapper for NaturalLanguageProjectCreator that adds pipeline tracking."""

    def __init__(
        self,
        kanban_client: Any,
        ai_engine: Any,
        pipeline_visualizer: SharedPipelineVisualizer,
        conversation_logger: Any = None,
        subtask_manager: Any = None,
    ) -> None:
        self.creator = NaturalLanguageProjectCreator(
            kanban_client, ai_engine, subtask_manager
        )
        self.pipeline_visualizer = pipeline_visualizer
        self.prd_parser = self.creator.prd_parser

        # Initialize conversation bridge for rich insights
        self.bridge = PipelineConversationBridge(
            conversation_logger=conversation_logger,
            pipeline_visualizer=pipeline_visualizer,
        )

        # Monkey-patch the PRD parser to track events
        self._wrap_prd_parser()

    def _wrap_prd_parser(self) -> None:
        """Wrap PRD parser methods to track pipeline events."""
        # Store original methods only if they exist
        original_analyze = getattr(self.prd_parser, "analyze_prd_deeply", None)
        original_parse = getattr(self.prd_parser, "parse_prd_to_tasks", None)

        if not original_parse:
            # PRD parser methods not available, skip wrapping
            return

        async def tracked_analyze_prd(prd_content: str) -> Any:
            flow_id = getattr(self, "current_flow_id", None)
            if not flow_id or not original_analyze:
                # Fallback to original method if available
                if original_analyze:
                    return await original_analyze(prd_content)
                else:
                    # Method doesn't exist, raise appropriate error
                    raise AttributeError("PRD parser missing analyze_prd_deeply method")

            # Track AI analysis
            start_time = datetime.now()
            self.pipeline_visualizer.add_event(
                flow_id=flow_id,
                stage=PipelineStage.AI_ANALYSIS,
                event_type="ai_prd_analysis_started",
                data={
                    "prd_length": len(prd_content),
                    "prd_preview": (
                        prd_content[:200] + "..."
                        if len(prd_content) > 200
                        else prd_content
                    ),
                },
                status="in_progress",
            )

            try:
                result = await original_analyze(prd_content)

                # Track success with rich insights
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                # Determine AI provider and model from the engine
                ai_provider = "unknown"
                model = "unknown"
                tokens_used = 0

                if hasattr(self.creator.ai_engine, "provider"):
                    ai_provider = self.creator.ai_engine.provider
                if hasattr(self.creator.ai_engine, "model"):
                    model = self.creator.ai_engine.model
                if hasattr(result, "token_usage"):
                    tokens_used = result.token_usage

                # Use bridge for rich tracking
                self.bridge.log_ai_analysis_with_context(
                    flow_id=flow_id,
                    prd_text=prd_content,
                    analysis_result={
                        "functionalRequirements": getattr(
                            result, "functional_requirements", []
                        ),
                        "nonFunctionalRequirements": getattr(
                            result, "non_functional_requirements", []
                        ),
                        "confidence": getattr(result, "confidence", 0.8),
                        "ambiguities": getattr(result, "ambiguities", []),
                    },
                    duration_ms=duration_ms,
                    ai_provider=ai_provider,
                    model=model,
                    tokens_used=tokens_used,
                )

                return result

            except Exception as e:
                # Track failure
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                self.pipeline_visualizer.add_event(
                    flow_id=flow_id,
                    stage=PipelineStage.AI_ANALYSIS,
                    event_type="ai_prd_analysis_failed",
                    data={"error_type": type(e).__name__},
                    duration_ms=duration_ms,
                    status="failed",
                    error=str(e),
                )
                raise

        async def tracked_parse_prd(prd_content: str, constraints: Any = None) -> Any:
            flow_id = getattr(self, "current_flow_id", None)
            if not flow_id:
                return await original_parse(prd_content, constraints)

            # Track PRD parsing
            start_time = datetime.now()
            self.pipeline_visualizer.add_event(
                flow_id=flow_id,
                stage=PipelineStage.PRD_PARSING,
                event_type="prd_parsing_started",
                data={
                    "has_constraints": constraints is not None,
                    "team_size": (
                        getattr(constraints, "team_size", None) if constraints else None
                    ),
                },
                status="in_progress",
            )

            try:
                result = await original_parse(prd_content, constraints)

                # Track task generation with rich context
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                if result and result.tasks:
                    # Build task data with dependencies
                    task_data = []
                    for t in result.tasks:
                        task_info = {
                            "id": t.id,
                            "name": t.name,
                            "priority": (
                                t.priority.value
                                if hasattr(t.priority, "value")
                                else str(t.priority)
                            ),
                            "estimatedHours": getattr(t, "estimated_hours", 8),
                            "dependencies": getattr(t, "dependencies", []),
                        }
                        task_data.append(task_info)

                    # Extract requirements that led to these tasks
                    requirements = []
                    if hasattr(result, "requirements"):
                        requirements = result.requirements

                    # Use bridge for rich tracking
                    self.bridge.log_task_generation_with_reasoning(
                        flow_id=flow_id,
                        requirements=requirements,
                        generated_tasks=task_data,
                        duration_ms=duration_ms,
                        generation_strategy="prd_based_decomposition",
                    )

                    # Also assess quality
                    self.bridge.log_quality_assessment(
                        flow_id=flow_id, requirements=requirements, tasks=task_data
                    )
                else:
                    self.pipeline_visualizer.add_event(
                        flow_id=flow_id,
                        stage=PipelineStage.TASK_GENERATION,
                        event_type="no_tasks_generated",
                        data={"reason": "PRD parsing returned no tasks"},
                        duration_ms=duration_ms,
                        status="completed",
                    )

                return result

            except Exception as e:
                # Track failure
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                self.pipeline_visualizer.add_event(
                    flow_id=flow_id,
                    stage=PipelineStage.PRD_PARSING,
                    event_type="prd_parsing_failed",
                    data={"error_type": type(e).__name__},
                    duration_ms=duration_ms,
                    status="failed",
                    error=str(e),
                )
                raise

        if original_analyze:
            setattr(self.prd_parser, "analyze_prd_deeply", tracked_analyze_prd)
        if original_parse:
            setattr(self.prd_parser, "parse_prd_to_tasks", tracked_parse_prd)

    async def create_project_from_description(
        self,
        description: str,
        project_name: str,
        options: Optional[Dict[str, Any]] = None,
        flow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create project with pipeline tracking."""
        # Store flow ID for wrapped methods
        self.current_flow_id = flow_id

        try:
            # Track project creation start
            if flow_id:
                self.pipeline_visualizer.add_event(
                    flow_id=flow_id,
                    stage=PipelineStage.TASK_CREATION,
                    event_type="project_creation_started",
                    data={"project_name": project_name},
                    status="in_progress",
                )

            # Create the project
            result = await self.creator.create_project_from_description(
                description=description, project_name=project_name, options=options
            )

            # Track individual task creation
            if flow_id and result.get("success") and "tasks" in result:
                for task in result["tasks"]:
                    if hasattr(self.pipeline_visualizer, "track_task_creation"):
                        self.pipeline_visualizer.track_task_creation(
                            flow_id=flow_id,
                            task_id=task.get("id", "unknown"),
                            task_name=task.get("name", "Unnamed"),
                            success=True,
                        )

            return result

        finally:
            # Clear flow ID
            self.current_flow_id = None


async def create_project_from_natural_language_tracked(
    description: str,
    project_name: str,
    state: Any,
    options: Optional[Dict[str, Any]] = None,
    flow_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create project with full pipeline tracking."""
    if not hasattr(state, "pipeline_visualizer"):
        # Fallback to untracked version
        from src.integrations.nlp_tools import create_project_from_natural_language

        return await create_project_from_natural_language(
            description=description,
            project_name=project_name,
            state=state,
            options=options,
        )

    # Initialize options with default mode
    if options is None:
        options = {}
    if "mode" not in options:
        options["mode"] = "new_project"

    # Get provider from options or default to planka
    provider = options.get("provider", "planka")

    logger.info(f"Auto-creating {provider} project '{project_name}' (tracked)")

    # Create and register the project in Marcus registry
    try:
        from src.integrations.project_auto_setup import ProjectAutoSetup

        auto_setup = ProjectAutoSetup()
        project_config = await auto_setup.setup_new_project(
            kanban_client=state.kanban_client,
            provider=provider,
            project_name=project_name,
            options=options,
        )

        logger.info(
            f"Auto-created {provider} project: {project_config.provider_config}"
        )

        # Register new project in ProjectRegistry
        marcus_project_id = None
        if hasattr(state, "project_registry"):
            marcus_project_id = await state.project_registry.add_project(project_config)
            logger.info(f"Registered new project in registry: {marcus_project_id}")

            # Switch to new project
            await state.project_manager.switch_project(marcus_project_id)
            state.kanban_client = await state.project_manager.get_kanban_client()
        else:
            logger.warning("ProjectRegistry not available - project not registered")

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to auto-create {provider} project: {str(e)}",
        }

    # Get conversation logger if available
    conversation_logger = None
    if hasattr(state, "conversation_logger"):
        conversation_logger = state.conversation_logger

    # Get subtask_manager if available (GH-62 fix)
    subtask_manager = getattr(state, "subtask_manager", None)

    # Initialize tracked creator
    tracked_creator = PipelineTrackedProjectCreator(
        kanban_client=state.kanban_client,
        ai_engine=state.ai_engine,
        pipeline_visualizer=state.pipeline_visualizer,
        conversation_logger=conversation_logger,
        subtask_manager=subtask_manager,
    )

    # Create project
    result = await tracked_creator.create_project_from_description(
        description=description,
        project_name=project_name,
        options=options,
        flow_id=flow_id,
    )

    # Add Marcus project_id to result for auto-select functionality
    if result.get("success") and marcus_project_id:
        result["project_id"] = marcus_project_id

    # Update Marcus state if successful
    if result.get("success"):
        try:
            await state.refresh_project_state()
        except Exception as e:
            # Log but don't fail the operation
            logger.warning(f"Failed to refresh project state: {str(e)}")

    return result
