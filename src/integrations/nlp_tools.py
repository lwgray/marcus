"""
Natural Language MCP Tools for Marcus (Refactored).

These tools expose Marcus's AI capabilities for:
1. Creating projects from natural language descriptions
2. Adding features to existing projects

This refactored version eliminates code duplication by using base classes and utilities.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.ai.advanced.prd.advanced_parser import (  # noqa: E402
    AdvancedPRDParser,
    ProjectConstraints,
)
from src.core.models import Priority, Task, TaskStatus  # noqa: E402
from src.core.resilience import RetryConfig, with_retry  # noqa: E402
from src.detection.board_analyzer import BoardAnalyzer  # noqa: E402
from src.detection.context_detector import ContextDetector, MarcusMode  # noqa: E402

# Import refactored base classes and utilities
from src.integrations.nlp_base import NaturalLanguageTaskCreator  # noqa: E402
from src.integrations.nlp_task_utils import TaskType  # noqa: E402
from src.modes.adaptive.basic_adaptive import BasicAdaptiveMode  # noqa: E402

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Design autocomplete parallelism helpers (GH-304)
#
# Concurrency cap: ``_DESIGN_LLM_CONCURRENCY`` limits in-flight ``llm.analyze``
# calls across all design tasks in a single ``_generate_design_content()``
# invocation. For a 10-task enterprise project with 5 LLM calls per task (4
# artifacts + 1 decisions), uncapped parallelism would burst up to 50 calls
# simultaneously and risk tripping Anthropic's per-minute rate limit. 10 is a
# safe ceiling for Claude Sonnet at paid-tier rate limits while preserving
# most of the wall-clock speedup.
# ---------------------------------------------------------------------------
_DESIGN_LLM_CONCURRENCY = 10


@with_retry(RetryConfig(max_attempts=3, base_delay=2.0, jitter=True))
async def _bounded_llm_analyze(
    llm: Any,
    prompt: str,
    context: Any,
    semaphore: asyncio.Semaphore,
) -> str:
    """Call ``llm.analyze`` under a concurrency cap with retry + backoff.

    Wraps a single LLM call so that:

    - at most ``semaphore._value`` calls run concurrently (rate-limit guard),
    - transient failures retry up to 3 times with jittered exponential
      backoff (``RetryConfig(max_attempts=3, base_delay=2.0, jitter=True)``).

    If all retries fail the last exception propagates to the caller, which
    aborts the surrounding ``asyncio.gather`` and fails the whole design
    autocomplete phase (hard-fail semantics — see GH-304).

    Parameters
    ----------
    llm : Any
        An LLM client exposing an async ``analyze(prompt, context)`` method.
    prompt : str
        Prompt text passed through unchanged.
    context : Any
        Context object passed through unchanged (typically provides
        ``max_tokens`` and similar knobs).
    semaphore : asyncio.Semaphore
        Concurrency guard. Must be created inside a running event loop so
        it binds to the correct loop (created per-call in
        :func:`_generate_design_content`).

    Returns
    -------
    str
        Raw LLM response text.

    Raises
    ------
    Exception
        Re-raises the last exception from ``llm.analyze`` after retries are
        exhausted.
    """
    async with semaphore:
        response: str = await llm.analyze(prompt=prompt, context=context)
        return response


class NaturalLanguageProjectCreator(NaturalLanguageTaskCreator):
    """
    Handles creation of projects from natural language descriptions.

    Refactored to use base class and eliminate code duplication.
    """

    def __init__(
        self,
        kanban_client: Any,
        ai_engine: Any,
        subtask_manager: Any = None,
        complexity: str = "standard",
        state: Any = None,
    ) -> None:
        """Initialize the natural language project creator.

        Parameters
        ----------
        kanban_client : Any
            Kanban board client for task creation.
        ai_engine : Any
            AI engine for PRD parsing and task generation.
        subtask_manager : Any, optional
            Subtask manager for decomposed task tracking.
        complexity : str, default="standard"
            Project complexity mode: prototype / standard / enterprise.
        state : Any, optional
            Marcus MCP server state. Required for the Phase A → Phase B
            design artifact registration chain (GH-320): when present,
            the background design phase closure calls
            ``_register_design_via_mcp`` with this state so design
            contract artifacts reach ``state.task_artifacts`` and
            become discoverable to downstream implementation tasks via
            ``get_task_context``. When ``None``, design artifacts are
            still written to disk but are not registered in MCP state
            (legacy behavior).
        """
        super().__init__(kanban_client, ai_engine, subtask_manager, complexity)
        self.prd_parser = AdvancedPRDParser()
        self.board_analyzer = BoardAnalyzer()
        self.context_detector = ContextDetector(self.board_analyzer)
        self.state = state

    async def process_natural_language(
        self,
        description: str,
        **kwargs: Any,
    ) -> List[Task]:
        """
        Process project description into tasks.

        Implementation of abstract method from base class.
        """
        # Extract arguments from kwargs
        project_name = kwargs.get("project_name")  # noqa: F841
        options = kwargs.get("options")

        # Detect context (Phase 1)
        await self.board_analyzer.analyze_board("default", [])
        context = await self.context_detector.detect_optimal_mode(
            user_id="system", board_id="default", tasks=[]
        )

        if context.recommended_mode != MarcusMode.CREATOR:
            logger.warning(f"Expected creator mode but got {context.recommended_mode}")

        # Parse PRD with AI (Phase 4)
        constraints = self._build_constraints(options)
        logger.info(f"Parsing PRD with constraints: {constraints}")

        prd_result = await self.prd_parser.parse_prd_to_tasks(description, constraints)

        task_count = len(prd_result.tasks) if prd_result.tasks else 0
        logger.info(f"PRD parser returned {task_count} tasks")
        if not prd_result.tasks:
            logger.warning("PRD parser returned no tasks!")
            logger.debug(f"PRD result: {prd_result}")
            return []

        # Apply the inferred dependencies to the task objects
        if prd_result.dependencies:
            dep_count = len(prd_result.dependencies)
            logger.info(f"Applying {dep_count} inferred dependencies to tasks")

            # Create a mapping of task IDs to tasks for quick lookup
            task_map = {task.id: task for task in prd_result.tasks}

            # Apply each dependency
            for dep in prd_result.dependencies:
                dependent_task_id = dep.get("dependent_task_id")
                dependency_task_id = dep.get("dependency_task_id")

                if dependent_task_id in task_map and dependency_task_id in task_map:
                    dependent_task = task_map[dependent_task_id]

                    # Add the dependency if not already present
                    if dependency_task_id not in dependent_task.dependencies:
                        dependent_task.dependencies.append(dependency_task_id)
                        logger.debug(
                            f"Added dependency: {task_map[dependent_task_id].name} "
                            f"depends on {task_map[dependency_task_id].name} "
                            f"(reason: {dep.get('reasoning', 'inferred')})"
                        )
                else:
                    logger.warning(
                        f"Could not apply dependency: "
                        f"{dependent_task_id} -> {dependency_task_id} "
                        f"(task not found in task map)"
                    )
        else:
            logger.info("No dependencies returned from PRD parser")

        return prd_result.tasks

    async def create_project_from_description(
        self,
        description: str,
        project_name: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a complete project from natural language description.

        Uses the base class implementation for common functionality.
        """
        try:
            logger.info(f"Creating project '{project_name}' from natural language")
            logger.debug(f"Description: {description[:200]}...")
            logger.debug(f"Options: {options}")

            # Create a new project/board for each create_project call
            # Clear any existing project/board IDs to force new project creation
            if self.kanban_client:
                logger.info(
                    f"Creating new project '{project_name}' "
                    f"(clearing any existing project/board IDs)"
                )

                # Default from config, experiment options can override
                from src.config.marcus_config import get_config

                default_provider = get_config().kanban.provider or "sqlite"
                provider = (
                    options.get("provider", default_provider)
                    if options
                    else default_provider
                )

                if provider == "sqlite":
                    # SQLite: create a project scope (unique IDs)
                    # so this experiment's tasks are isolated
                    if hasattr(self.kanban_client, "auto_setup_project"):
                        await self.kanban_client.auto_setup_project(
                            project_name=project_name,
                            board_name="Main Board",
                            project_root=(
                                options.get("project_root") if options else None
                            ),
                        )
                    elif hasattr(self.kanban_client, "connect"):
                        await self.kanban_client.connect()
                    # Set active_project_id so task_metadata in marcus.db
                    # gets the correct project_id for Cato filtering.
                    # Only set if not already assigned (caller may have
                    # set it to the Marcus registry ID).
                    if not self.active_project_id:
                        self.active_project_id = getattr(
                            self.kanban_client, "project_id", None
                        )
                    logger.info(
                        f"Using SQLite provider for project "
                        f"'{project_name}' — "
                        f"project_id={self.active_project_id}"
                    )
                else:
                    # Clear IDs on non-SQLite providers (Planka, etc.)
                    if hasattr(self.kanban_client, "client"):
                        self.kanban_client.client.project_id = None
                        self.kanban_client.client.board_id = None
                    elif hasattr(self.kanban_client, "project_id"):
                        self.kanban_client.project_id = None
                        self.kanban_client.board_id = None

                    # Create project/board via provider-specific setup
                    from src.integrations.project_auto_setup import (
                        ProjectAutoSetup,
                    )

                    auto_setup = ProjectAutoSetup()
                    try:
                        client_to_use = (
                            self.kanban_client.client
                            if hasattr(self.kanban_client, "client")
                            else self.kanban_client
                        )
                        project_config = await auto_setup.setup_new_project(
                            kanban_client=client_to_use,
                            provider=provider,
                            project_name=project_name,
                            options=options,
                        )
                        proj_id = project_config.provider_config.get("project_id")
                        bd_id = project_config.provider_config.get("board_id")
                        logger.info(
                            f"Created new {provider} project: "
                            f"project_id={proj_id}, board_id={bd_id}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to create new project: {e}")
                        raise

            # Parse tasks
            from src.core.error_framework import ErrorContext, error_context

            with error_context(
                "task_parsing",
                custom_context={
                    "project_name": project_name,
                    "description_length": len(description),
                },
            ):
                tasks = await self.process_natural_language(
                    description, project_name=project_name, options=options
                )
                logger.info(f"process_natural_language returned {len(tasks)} tasks")

                # Log detailed task breakdown for debugging
                if tasks:
                    task_types: Dict[str, int] = {}
                    for task in tasks:
                        task_type = getattr(task, "task_type", "unknown")
                        task_types[task_type] = task_types.get(task_type, 0) + 1
                    logger.info(f"Task type breakdown: {task_types}")
                else:
                    desc_len = len(description)
                    logger.warning(
                        f"No tasks generated for project '{project_name}' "
                        f"with description length {desc_len}"
                    )

            if not tasks:
                from src.core.error_framework import (  # noqa: F811
                    BusinessLogicError,
                    ErrorContext,
                )

                logger.warning("No tasks generated from natural language processing!")

                error_msg = (
                    f"Failed to generate any tasks from project description. "
                    f"The description may be too vague, missing key details, "
                    f"or not match expected patterns. "
                    f"Description: '{description[:200]}...'"
                )
                raise BusinessLogicError(
                    error_msg,
                    context=ErrorContext(
                        operation="create_project",
                        integration_name="nlp_tools",
                        custom_context={
                            "project_name": project_name,
                            "description_length": len(description),
                        },
                    ),
                )

            # Apply safety checks using base class
            with error_context(
                "safety_checks",
                custom_context={
                    "project_name": project_name,
                    "original_task_count": len(tasks),
                },
            ):
                safe_tasks = await self.apply_safety_checks(tasks)
                logger.info(f"Safety checks passed, {len(safe_tasks)} tasks ready")

                # Add integration verification task if appropriate
                # Must be added BEFORE documentation so doc task
                # depends on integration task
                from src.integrations.integration_verification import (
                    enhance_project_with_integration,
                )

                safe_tasks = enhance_project_with_integration(
                    safe_tasks, description, project_name
                )
                logger.info(
                    "After integration enhancement: " f"{len(safe_tasks)} tasks"
                )

                # Add documentation task if appropriate
                from src.integrations.documentation_tasks import (
                    enhance_project_with_documentation,
                )

                safe_tasks = enhance_project_with_documentation(
                    safe_tasks, description, project_name
                )
                logger.info(
                    "After documentation enhancement: " f"{len(safe_tasks)} tasks"
                )

                # Log safety check impact
                added_tasks = len(safe_tasks) - len(tasks)
                if added_tasks > 0:
                    logger.info(f"Safety checks added {added_tasks} dependency tasks")

            # Design tasks go on the board as TODO but assigned to
            # Marcus so workers can't grab them. Phase A (design
            # artifact generation) runs in the background AFTER the
            # response is returned. Workers can't grab implementation
            # tasks because _are_dependencies_satisfied() checks that
            # design (hard) dependencies are DONE. Once the background
            # task completes, it marks design tasks DONE on the board
            # and workers' next request_next_task call will succeed.
            project_root = options.get("project_root") if options else None
            for task in safe_tasks:
                if _is_design_task(task):
                    task.assigned_to = "Marcus"

            # Create tasks on board using base class (this also triggers decomposition)
            with error_context(
                "kanban_task_creation",
                custom_context={
                    "project_name": project_name,
                    "task_count": len(safe_tasks),
                },
            ):
                created_tasks = await self.create_tasks_on_board(safe_tasks)
                logger.info(f"Created {len(created_tasks)} tasks on board")

                # NOW create About task AFTER decomposition with real task IDs
                # Map created tasks to original tasks to preserve details
                tasks_with_real_ids = []
                for i, created in enumerate(created_tasks):
                    if i < len(safe_tasks):
                        original = safe_tasks[i]
                        task_with_id = Task(
                            id=created.id,  # Real Planka/Kanban ID
                            name=original.name,
                            description=original.description,
                            status=original.status,
                            priority=original.priority,
                            assigned_to=original.assigned_to,
                            created_at=original.created_at,
                            updated_at=original.updated_at,
                            due_date=original.due_date,
                            estimated_hours=original.estimated_hours,
                            dependencies=original.dependencies,
                            labels=original.labels,
                        )
                        tasks_with_real_ids.append(task_with_id)

                # Create About task with hierarchical subtask information
                about_kanban_task = None
                about_task = self._create_about_task(
                    description, project_name, tasks_with_real_ids
                )

                # Add About task to board at the beginning
                about_task_data = self.task_builder.build_task_data(about_task)
                about_kanban_task = await self.kanban_client.create_task(
                    about_task_data
                )
                logger.info(
                    f"Created 'About' task card with ID: {about_kanban_task.id}"
                )

                # Persist About task metadata and outcome to marcus.db
                # so Cato can see it (same pattern as nlp_base.py)
                try:
                    from pathlib import Path

                    from src.core.persistence import SQLitePersistence

                    marcus_root = Path(__file__).parent.parent.parent
                    db_path = marcus_root / "data" / "marcus.db"
                    persistence = SQLitePersistence(db_path=db_path)

                    about_id = about_kanban_task.id
                    if about_id:
                        now_iso = datetime.now(timezone.utc).isoformat()
                        await persistence.store(
                            "task_metadata",
                            str(about_id),
                            {
                                "task_id": str(about_id),
                                "name": about_task.name,
                                "description": about_task.description,
                                "priority": "low",
                                "estimated_hours": 0.0,
                                "labels": about_task.labels,
                                "dependencies": [],
                                "project_id": self.active_project_id,
                                "created_at": now_iso,
                            },
                        )
                        # About task is created as done, so add outcome
                        await persistence.store(
                            "task_outcomes",
                            f"{about_id}_system_{now_iso}",
                            {
                                "task_id": str(about_id),
                                "agent_id": "system",
                                "task_name": about_task.name,
                                "estimated_hours": 0.0,
                                "actual_hours": 0.0,
                                "success": True,
                                "blockers": [],
                                "started_at": now_iso,
                                "completed_at": now_iso,
                            },
                        )
                except Exception as about_log_err:
                    logger.warning(
                        f"Failed to persist About task metadata: " f"{about_log_err}"
                    )

                # Persist design task metadata and outcomes to marcus.db
                # so Cato can show them in Swim Lane (same pattern as About task)
                try:
                    for task_with_id in tasks_with_real_ids:
                        if not _is_design_task(task_with_id):
                            continue
                        if task_with_id.status != TaskStatus.DONE:
                            continue
                        design_id = str(task_with_id.id)
                        now_iso = datetime.now(timezone.utc).isoformat()
                        await persistence.store(
                            "task_metadata",
                            design_id,
                            {
                                "task_id": design_id,
                                "name": task_with_id.name,
                                "description": task_with_id.description,
                                "priority": getattr(task_with_id, "priority", "medium"),
                                "estimated_hours": getattr(
                                    task_with_id, "estimated_hours", 0.0
                                ),
                                "labels": getattr(task_with_id, "labels", []),
                                "dependencies": getattr(
                                    task_with_id, "dependencies", []
                                ),
                                "project_id": self.active_project_id,
                                "created_at": now_iso,
                            },
                        )
                        await persistence.store(
                            "task_outcomes",
                            f"{design_id}_Marcus_{now_iso}",
                            {
                                "task_id": design_id,
                                "agent_id": "Marcus",
                                "task_name": task_with_id.name,
                                "estimated_hours": getattr(
                                    task_with_id, "estimated_hours", 0.0
                                ),
                                "actual_hours": 0.0,
                                "success": True,
                                "blockers": [],
                                "started_at": now_iso,
                                "completed_at": now_iso,
                            },
                        )
                        logger.info(
                            f"Persisted design task outcome: "
                            f"{task_with_id.name} (id={design_id})"
                        )
                except Exception as design_log_err:
                    logger.warning(
                        f"Failed to persist design task metadata: " f"{design_log_err}"
                    )

                # Include About task in created list
                if about_kanban_task and hasattr(about_kanban_task, "id"):
                    created_tasks.append(about_kanban_task)

                # Log creation success rate
                success_rate = (
                    (len(created_tasks) / len(safe_tasks)) * 100 if safe_tasks else 0
                )
                logger.info(f"Task creation success rate: {success_rate:.1f}%")

            # Skip classification for dictionaries - just count them
            # created_tasks are dictionaries from kanban API, not Task objects
            task_breakdown = {"total": len(created_tasks)}

            # Add breakdown by original task types if available
            if safe_tasks:
                classified_original = self.classify_tasks(safe_tasks)
                for task_type, tasks in classified_original.items():
                    if tasks:
                        task_breakdown[task_type.value] = len(tasks)

            # Collect task IDs for backfill
            task_ids = []
            for ct in created_tasks:
                if isinstance(ct, dict):
                    tid = ct.get("id")
                elif hasattr(ct, "id"):
                    tid = ct.id
                else:
                    tid = None
                if tid:
                    task_ids.append(str(tid))

            result = {
                "success": True,
                "project_name": project_name,
                "tasks_created": len(created_tasks),
                "task_ids": task_ids,
                "task_breakdown": task_breakdown,
                "phases": self._extract_phases(safe_tasks),
                "estimated_days": self._estimate_duration(safe_tasks),
                "dependencies_mapped": self._count_dependencies(safe_tasks),
                "risk_level": self._assess_risk_by_count(len(created_tasks)),
                "confidence": 0.85,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Successfully created project with {len(created_tasks)} tasks")

            # Phase A+B (background): Generate design artifacts,
            # register via MCP, mark design tasks DONE, generate
            # scaffold. Runs AFTER response is returned so Claude
            # doesn't timeout on long LLM calls. Workers are blocked
            # by hard dependencies until design tasks reach DONE
            # status on the kanban board.
            has_design_tasks = any(_is_design_task(t) for t in safe_tasks)
            if project_root and has_design_tasks:
                import asyncio as _aio

                _aio.ensure_future(
                    _run_design_phase(
                        state=self.state,
                        kanban_client=self.kanban_client,
                        safe_tasks=safe_tasks,
                        created_tasks=created_tasks,
                        description=description,
                        project_name=project_name,
                        project_root=project_root,
                    )
                )
                logger.info(
                    "[design_autocomplete] Phase A scheduled as " "background task"
                )

            # Run cleanup synchronously with a short timeout
            # This ensures resources are cleaned up without hanging
            import asyncio

            try:
                await asyncio.wait_for(self._cleanup_background(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Cleanup timed out after 5.0s, continuing anyway")

            return result

        except Exception as e:
            from src.core.error_framework import MarcusBaseError
            from src.core.error_responses import handle_mcp_tool_error

            # If it's already a Marcus error, let it propagate properly
            if isinstance(e, MarcusBaseError):
                logger.error(f"Marcus error during project creation: {e}")
                # Return proper MCP error response
                return handle_mcp_tool_error(
                    e,
                    "create_project",
                    {
                        "description": description,
                        "project_name": project_name,
                        "options": options,
                    },
                )
            else:
                # Convert other exceptions to proper Marcus errors
                from src.core.error_framework import BusinessLogicError, ErrorContext

                unexpected_error = BusinessLogicError(
                    f"Unexpected error during project creation: {str(e)}",
                    context=ErrorContext(
                        operation="create_project",
                        integration_name="nlp_tools",
                        custom_context={"project_name": project_name},
                    ),
                )

                logger.error(f"Unexpected error creating project: {unexpected_error}")
                return handle_mcp_tool_error(
                    unexpected_error,
                    "create_project",
                    {
                        "description": description,
                        "project_name": project_name,
                        "options": options,
                    },
                )

    async def _cleanup_background(self) -> None:
        """Cleanup AI engine after response is sent."""
        try:
            # Only cleanup AI engine, skip task cancellation
            # Task cancellation was causing issues
            if hasattr(self.ai_engine, "cleanup"):
                try:
                    await self.ai_engine.cleanup()
                except Exception as cleanup_error:
                    logger.warning(f"AI engine cleanup failed: {cleanup_error}")
        except Exception as e:
            logger.warning(f"Background cleanup failed: {e}")

    def _build_constraints(
        self, options: Optional[Dict[str, Any]]
    ) -> ProjectConstraints:
        """Build project constraints from options."""
        if not options:
            return ProjectConstraints()

        # Get complexity and deployment options (backwards compatible)
        complexity = options.get("complexity", options.get("project_size", "standard"))
        deployment = options.get("deployment", options.get("deployment_target", "none"))

        # Map new complexity levels to appropriate defaults
        complexity_defaults = {
            "prototype": {"team_size": 1, "deployment_target": "local"},
            "standard": {"team_size": 3, "deployment_target": "dev"},
            "enterprise": {"team_size": 5, "deployment_target": "prod"},
            # Legacy mappings for backwards compatibility
            "mvp": {"team_size": 1, "deployment_target": "local"},
            "small": {"team_size": 2, "deployment_target": "local"},
            "medium": {"team_size": 3, "deployment_target": "dev"},
            "large": {"team_size": 5, "deployment_target": "prod"},
        }

        # Map new deployment options to legacy deployment_target values
        deployment_mapping = {
            "none": "local",
            "internal": "dev",
            "production": "prod",
            # Keep legacy values for backwards compatibility
            "local": "local",
            "dev": "dev",
            "prod": "prod",
            "remote": "prod",
        }

        defaults = complexity_defaults.get(complexity, complexity_defaults["standard"])
        mapped_deployment = deployment_mapping.get(deployment, "local")

        constraints = ProjectConstraints(
            team_size=options.get("team_size", defaults["team_size"]),
            available_skills=options.get("tech_stack", []),
            technology_constraints=options.get("tech_stack", []),
            deployment_target=mapped_deployment,
            complexity_mode=self.complexity,  # Pass explicit complexity mode
        )

        # Pass complexity info via quality_requirements for parser to use
        constraints.quality_requirements = {
            "project_size": complexity,  # Parser still uses project_size internally
            "complexity": (
                "simple" if complexity in ["prototype", "mvp"] else "moderate"
            ),
        }

        if "deadline" in options:
            try:
                constraints.deadline = datetime.fromisoformat(options["deadline"])
            except (ValueError, TypeError):
                # Invalid date format, use default (no deadline)
                pass  # nosec B110

        return constraints

    def _extract_phases(self, tasks: List[Task]) -> List[str]:
        """Extract project phases from tasks."""
        phases = set()
        for task in tasks:
            for label in task.labels:
                if label in [
                    "infrastructure",
                    "backend",
                    "frontend",
                    "testing",
                    "deployment",
                ]:
                    phases.add(label)
        return sorted(phases)

    def _estimate_duration(self, tasks: List[Task]) -> int:
        """Estimate project duration in days."""
        total_hours = sum(
            task.estimated_hours for task in tasks if task.estimated_hours
        )
        # Assume 8 hours per day, with some parallelization factor
        return int(total_hours / (8 * 2))  # 2 developers working in parallel

    def _count_dependencies(self, tasks: List[Task]) -> int:
        """Count total dependencies."""
        return sum(len(task.dependencies) for task in tasks)

    def _assess_risk(self, classified_tasks: Dict[TaskType, List[Task]]) -> str:
        """Assess project risk level."""
        # Create a list to avoid modification during iteration
        total_tasks = sum(len(tasks) for tasks in list(classified_tasks.values()))

        if total_tasks > 50:
            return "high"
        elif total_tasks > 20:
            return "medium"
        else:
            return "low"

    def _assess_risk_by_count(self, task_count: int) -> str:
        """Assess project risk level by task count."""
        if task_count > 50:
            return "high"
        elif task_count > 20:
            return "medium"
        else:
            return "low"

    def _create_about_task(
        self, description: str, project_name: str, tasks: List[Task]
    ) -> Task:
        """
        Create an 'About' task card that documents the project.

        Supports hierarchical formatting when subtasks are present.
        Tasks with subtasks show their children indented underneath.

        Parameters
        ----------
        description : str
            Original user description of the project
        project_name : str
            Name of the project
        tasks : List[Task]
            List of tasks generated for the project

        Returns
        -------
        Task
            About task card with project documentation
        """
        # Get subtask manager if available
        subtask_manager = getattr(self, "subtask_manager", None)

        # Format task list with hierarchical structure
        task_list_md = "## Generated Tasks\n\n"
        for idx, task in enumerate(tasks, 1):
            # Format parent/standalone task
            task_list_md += f"### {idx}. {task.name}\n"
            task_list_md += f"**Description:** {task.description}\n"
            task_list_md += f"**Estimated Hours:** {task.estimated_hours}\n"
            task_list_md += f"**Labels:** {', '.join(task.labels)}\n"

            # Add subtasks if they exist (using legacy storage since
            # we don't have project_tasks here)
            if subtask_manager and subtask_manager.has_subtasks(task.id, None):
                subtasks = subtask_manager.get_subtasks(task.id, None)
                if subtasks:
                    task_list_md += "\n**Subtasks:**\n"
                    for sub_idx, subtask in enumerate(subtasks, 1):
                        task_list_md += f"  {idx}.{sub_idx}. {subtask.name}\n"
                        task_list_md += f"     - {subtask.description}\n"
                        task_list_md += (
                            f"     - Estimated: {subtask.estimated_hours}h\n"
                        )

            task_list_md += "\n"

        # Create the About card description
        about_description = f"""# {project_name} - Project Overview

## Original Description

{description}

{task_list_md}

---
*This card provides an overview of the project and is not assignable to agents.*
"""

        # Create the About task
        about_task = Task(
            id="about_project",
            name=f"About: {project_name}",
            description=about_description,
            status=TaskStatus.DONE,  # Mark as completed
            priority=Priority.LOW,
            assigned_to=None,  # Not assignable
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0,  # No time estimate
            dependencies=[],
            labels=["documentation"],  # Documentation label
            source_type="project_about",
            source_context={"project_name": project_name},
        )

        return about_task


class NaturalLanguageFeatureAdder(NaturalLanguageTaskCreator):
    """
    Handles adding features to existing projects using natural language.

    Refactored to use base class and eliminate code duplication.
    """

    def __init__(self, kanban_client: Any, ai_engine: Any, project_tasks: Any) -> None:
        super().__init__(kanban_client, ai_engine)
        self.project_tasks = project_tasks
        self.adaptive_mode = BasicAdaptiveMode()
        from src.modes.enricher.basic_enricher import BasicEnricher

        self.enricher = BasicEnricher()

    async def process_natural_language(
        self, description: str, integration_point: str = "auto_detect", **kwargs: Any
    ) -> List[Task]:
        """
        Process feature description into tasks.

        Implementation of abstract method from base class.
        """
        # Parse feature into tasks
        feature_tasks = await self._parse_feature_to_tasks(description)

        # Enrich the parsed tasks
        for i, task in enumerate(feature_tasks):
            feature_tasks[i] = self.enricher.enrich_task(task)

        # Detect integration points
        if integration_point == "auto_detect":
            integration_info = await self._detect_integration_points(
                feature_tasks, self.project_tasks
            )
        else:
            integration_info = {"tasks": [], "phase": integration_point}

        # Map dependencies to existing tasks
        for feature_task in feature_tasks:
            for integration_task_id in integration_info.get("tasks", []):
                if integration_task_id not in feature_task.dependencies:
                    feature_task.dependencies.append(integration_task_id)

        # Store integration info for later use
        self._integration_info = integration_info

        return feature_tasks

    async def add_feature_from_description(
        self, feature_description: str, integration_point: str = "auto_detect"
    ) -> Dict[str, Any]:
        """
        Add a feature to existing project from natural language.

        Uses the base class implementation for common functionality.
        """
        try:
            logger.info(f"Adding feature: {feature_description}")

            # Parse and process tasks
            tasks = await self.process_natural_language(
                feature_description, integration_point=integration_point
            )

            # Apply safety checks using base class
            safe_tasks = await self.apply_safety_checks(tasks)

            # Create tasks on board using base class
            created_tasks = await self.create_tasks_on_board(safe_tasks)

            # Skip classification for dictionaries - just count them
            # created_tasks are dictionaries from kanban API, not Task objects
            task_breakdown = {"total": len(created_tasks)}

            # Add breakdown by original task types if available
            if safe_tasks:
                classified_original = self.classify_tasks(safe_tasks)
                for task_type, tasks in classified_original.items():
                    if tasks:
                        task_breakdown[task_type.value] = len(tasks)

            result = {
                "success": True,
                "tasks_created": len(created_tasks),
                "task_breakdown": task_breakdown,
                "integration_points": self._integration_info.get("tasks", []),
                "integration_detected": integration_point == "auto_detect",
                "confidence": self._integration_info.get("confidence", 0.8),
                "feature_phase": self._integration_info.get("phase", "current"),
                "complexity": self._calculate_complexity(created_tasks),
            }

            logger.info(f"Successfully added feature with {len(created_tasks)} tasks")
            return result

        except Exception as e:
            logger.error(f"Error adding feature: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _parse_feature_to_tasks(self, feature_description: str) -> List[Task]:
        """Parse feature description into tasks using AI."""
        try:
            # Use AI engine to analyze the feature request
            feature_analysis = await self.ai_engine.analyze_feature_request(
                feature_description
            )
        except Exception as e:
            logger.warning(f"AI analysis failed, using fallback: {str(e)}")
            feature_analysis = self._generate_fallback_tasks(feature_description)

        # Generate tasks based on analysis
        tasks = []
        task_id_counter = len(self.project_tasks) + 1

        for task_info in feature_analysis.get("required_tasks", []):
            task = Task(
                id=str(task_id_counter),
                name=task_info["name"],
                description=task_info.get("description", ""),
                status=TaskStatus.TODO,
                priority=(
                    Priority.HIGH if task_info.get("critical") else Priority.MEDIUM
                ),
                labels=task_info.get("labels", ["feature"]),
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                estimated_hours=task_info.get("estimated_hours", 8),
                dependencies=[],
                due_date=None,
            )
            tasks.append(task)
            task_id_counter += 1

        return tasks

    async def _detect_integration_points(
        self, feature_tasks: List[Task], existing_tasks: List[Task]
    ) -> Dict[str, Any]:
        """Detect where feature should integrate with existing project."""
        try:
            # Use AI engine to analyze integration points
            integration_analysis = await self.ai_engine.analyze_integration_points(
                feature_tasks, existing_tasks
            )
        except Exception as e:
            logger.warning(f"AI integration analysis failed, using fallback: {str(e)}")
            integration_analysis = self._analyze_integration_fallback(
                feature_tasks, existing_tasks
            )

        # Use AI-detected dependencies or fall back to label matching
        if "dependent_task_ids" in integration_analysis:
            integration_tasks = integration_analysis["dependent_task_ids"]
        else:
            # Use utility to find related tasks
            integration_tasks = []
            for existing_task in existing_tasks:
                related_features = self.safety_checker._find_related_tasks(
                    existing_task, feature_tasks
                )
                if related_features:
                    integration_tasks.append(existing_task.id)

        return {
            "tasks": integration_tasks,
            "phase": integration_analysis.get("suggested_phase", "current"),
            "confidence": integration_analysis.get("confidence", 0.8),
            "complexity": integration_analysis.get("integration_complexity", "medium"),
            "risks": integration_analysis.get("integration_risks", []),
        }

    def _calculate_complexity(self, tasks: List[Task]) -> str:
        """Calculate feature complexity based on tasks."""
        total_hours = sum(
            task.estimated_hours for task in tasks if task.estimated_hours
        )

        if total_hours > 40:
            return "high"
        elif total_hours > 20:
            return "medium"
        else:
            return "low"

    def _analyze_integration_fallback(
        self, feature_tasks: List[Task], existing_tasks: List[Task]
    ) -> Dict[str, Any]:
        """Analyze integration points without AI."""
        # Determine project phase based on existing tasks
        completed_tasks = [t for t in existing_tasks if t.status == TaskStatus.DONE]
        [t for t in existing_tasks if t.status == TaskStatus.IN_PROGRESS]

        # Classify existing tasks
        classified_existing = self.classify_tasks(existing_tasks)

        # Determine phase based on task types
        if classified_existing[TaskType.DEPLOYMENT]:
            phase = "post-deployment"
            confidence = 0.8
        elif classified_existing[TaskType.TESTING]:
            phase = "testing"
            confidence = 0.85
        elif classified_existing[TaskType.IMPLEMENTATION]:
            phase = "development"
            confidence = 0.85
        else:
            phase = "initial"
            confidence = 0.9

        return {
            "suggested_phase": phase,
            "confidence": confidence,
            "project_maturity": (
                len(completed_tasks) / len(existing_tasks) if existing_tasks else 0
            ),
        }

    def _generate_fallback_tasks(self, feature_description: str) -> Dict[str, Any]:
        """Generate intelligent fallback tasks based on feature description keywords."""
        feature_lower = feature_description.lower()
        tasks = []

        # Analyze feature type
        feature_types = {
            "api": ["api", "endpoint", "rest", "graphql"],
            "ui": ["ui", "interface", "screen", "page", "component", "frontend"],
            "auth": ["auth", "login", "user", "permission", "security"],
            "data": ["database", "model", "schema", "data", "storage"],
            "integration": ["integrate", "connect", "sync", "webhook"],
        }

        detected_types = []
        for ftype, keywords in list(feature_types.items()):
            if any(word in feature_lower for word in keywords):
                detected_types.append(ftype)

        # Always start with design/planning task
        tasks.append(
            {
                "name": f"Design {feature_description}",
                "description": (
                    f"Create technical design and plan for implementing "
                    f"{feature_description}"
                ),
                "estimated_hours": 4,
                "labels": ["feature", "design", "planning"],
                "critical": False,
            }
        )

        # Add type-specific tasks
        task_templates = {
            "data": {
                "name": f"Create database schema for {feature_description}",
                "description": "Design and implement database models and migrations",
                "estimated_hours": 6,
                "labels": ["feature", "database", "backend"],
                "critical": True,
            },
            "api": {
                "name": f"Implement backend for {feature_description}",
                "description": "Create backend services, APIs, and business logic",
                "estimated_hours": 12,
                "labels": ["feature", "backend", "api"],
                "critical": True,
            },
            "ui": {
                "name": f"Build UI components for {feature_description}",
                "description": "Create frontend components and user interface",
                "estimated_hours": 10,
                "labels": ["feature", "frontend", "ui"],
                "critical": True,
            },
            "auth": {
                "name": f"Implement security for {feature_description}",
                "description": (
                    "Add authentication, authorization, and security measures"
                ),
                "estimated_hours": 8,
                "labels": ["feature", "security", "auth"],
                "critical": True,
            },
            "integration": {
                "name": f"Build integration layer for {feature_description}",
                "description": "Implement integration points and data synchronization",
                "estimated_hours": 8,
                "labels": ["feature", "integration", "backend"],
                "critical": True,
            },
        }

        # Add tasks for detected types
        for dtype in detected_types:
            if dtype in task_templates:
                tasks.append(task_templates[dtype])

        # If no specific type detected, add generic implementation
        if not detected_types:
            tasks.append(task_templates["api"])  # Default to backend

        # Always add testing and documentation
        tasks.extend(
            [
                {
                    "name": f"Test {feature_description}",
                    "description": (
                        "Write unit tests, integration tests, and perform QA"
                    ),
                    "estimated_hours": 6,
                    "labels": ["feature", "testing", "qa"],
                    "critical": False,
                },
                {
                    "name": f"Document {feature_description}",
                    "description": "Create user documentation and API documentation",
                    "estimated_hours": 3,
                    "labels": ["feature", "documentation"],
                    "critical": False,
                },
            ]
        )

        return {"required_tasks": tasks}


# --- Design Task Auto-Completion (GH-297) ---
#
# Two-phase approach to prevent context contamination:
#
# Phase A (_generate_design_content): Runs BEFORE create_tasks_on_board.
#   Calls LLM, writes artifact files to disk, sets task status=DONE.
#   Design tasks hit the board already DONE — no agent can grab them.
#
# Phase B (_register_design_via_mcp): Runs AFTER refresh_project_state.
#   Registers artifacts + decisions through MCP tools (log_artifact,
#   log_decision) so state.task_artifacts and state.context.decisions
#   are populated for get_task_context. Workers discover everything.

# Each artifact is generated by a separate LLM call, just like an
# agent would create separate documents via separate log_artifact calls.
# This avoids the giant-JSON-blob problem that caused truncation failures.

_ARTIFACT_PROMPT = """\
You are a senior software architect working on: {project_name}

## Project Description
{project_description}

## Your Design Task
{task_description}

## Your Current Assignment
Generate the {artifact_label} document for this design.

Describe WHAT each component does and HOW components connect to each \
other. Focus on behavior, responsibilities, data flow, and integration \
boundaries.

Do NOT specify file names, function signatures, prop interfaces, class \
names, or internal implementation details. The implementing developer \
decides those. Your job is to define the WHAT and WHY, not the HOW.

However, you MUST be concrete and specific about any identifier, name, \
or value that will be shared across module boundaries — field names in \
data models, storage keys, event names, environment variable names, \
port numbers, API response shapes, and status/enum values. When \
multiple modules must agree on a name or value to interoperate, that \
name or value is an interface contract, not an implementation detail. \
State it explicitly.

Good: "The time display updates every second using the browser's \
Date API and supports timezone conversion."
Bad: "TimeWidget (src/components/TimeWidget.tsx) takes props \
timeFormat: '24h' | '12h' and uses setInterval(1000)."

Good: "The todo entity fields are: id (string), title (string), \
description (string|null), completed (boolean), created_at \
(ISO 8601 timestamp). All modules that produce or consume todo \
data must use these exact field names."
Good: "Auth tokens are stored under the key `auth_token`. Both \
the auth module and any module making authenticated requests must \
use this key."
Good: "The API server listens on port 3001 (configurable via \
PORT environment variable)."

Respond with ONLY the document content in markdown format. \
No JSON wrapping, no code fences around the whole response. \
Just the markdown document starting with a # heading.
"""

_DECISIONS_PROMPT = """\
You are a senior software architect working on: {project_name}

## Project Description
{project_description}

## Design Task
{task_description}

## Your Current Assignment
List the key architectural decisions for this design. Focus on \
technology choices, patterns, and boundaries — not implementation \
details like file names or function signatures.

Good: "Use browser Date API for time, not a library — reduces bundle size."
Bad: "Use setInterval(1000) in useCurrentTime.ts hook."

Respond with ONLY a JSON array (no wrapping object, no markdown fences):
[{{"what":"Chose X over Y","why":"Because of Z","impact":"Affects A and B"}}]
"""

# Standard artifacts a design task produces, matching what the task
# description requests in advanced_parser.py:912-927
_DESIGN_ARTIFACT_SPECS = [
    {
        "artifact_type": "architecture",
        "label": "architecture",
        "filename_template": "{domain_slug}-architecture.md",
        "description_template": ("Component boundaries and data flows for {domain}"),
    },
    {
        "artifact_type": "api",
        "label": "API contracts",
        "filename_template": "{domain_slug}-api-contracts.md",
        "description_template": (
            "Endpoint definitions and request/response schemas " "for {domain}"
        ),
    },
    {
        "artifact_type": "specification",
        "label": "data models",
        "filename_template": "{domain_slug}-data-models.md",
        "description_template": (
            "Database schemas and entity relationships for {domain}"
        ),
    },
    {
        "artifact_type": "specification",
        "label": "interface contracts",
        "filename_template": "{domain_slug}-interface-contracts.md",
        "description_template": (
            "Shared identifiers and values that must be consistent "
            "across all modules in {domain}"
        ),
    },
]

_INTERFACE_CONTRACTS_PROMPT = """\
You are a senior software architect working on: {project_name}

## Project Description
{project_description}

## Your Design Task
{task_description}

## Your Current Assignment
Generate the interface contracts document for this design.

Interface contracts define the EXACT identifiers, names, values, and \
shapes that multiple modules must agree on to interoperate. These are \
NOT implementation details — they are coordination constraints. Each \
implementing agent independently decides HOW to build their module, \
but they MUST use these exact names and shapes at module boundaries.

List every shared boundary explicitly. For each one, specify:
- The exact identifier/key/name that must be used
- The data type or shape
- Which modules produce it and which consume it

Categories to cover:

### Data Entity Fields
For every shared data entity (user, todo, session, etc.), list the \
exact field names and types that all modules must use when producing \
or consuming that entity. Example:
- `todo.id` (string) — unique identifier
- `todo.title` (string) — display title
- `todo.completed` (boolean) — completion status

### Storage Keys
For any value stored in a shared medium (localStorage, cookies, \
environment variables, database, cache, message queue), specify \
the exact key. Example:
- Auth token stored under key: `auth_token`
- User session stored under key: `session_id`

### Configuration Values
For any value referenced by multiple modules (ports, hostnames, \
base URLs, timeouts), specify the canonical value and how to \
override it. Example:
- API server port: `3001` (override via `PORT` env var)
- API base URL: `/api`

### API Response Shapes
For every endpoint that returns data consumed by another module, \
specify the exact response structure. Example:
- `GET /api/todos` returns: `{{ "status": "success", "data": {{ \
"todos": [...], "total": number, "limit": number, "offset": number }} }}`

### Status/Enum Values
For any status field, category, or enum used across modules, \
specify the exact valid values. Example:
- Todo status filter values: `all`, `active`, `completed`

Respond with ONLY the document content in markdown format. \
No JSON wrapping, no code fences around the whole response. \
Just the markdown document starting with a # heading.
"""


def _is_design_task(task: Any) -> bool:
    """Check if a task is a bundled design task."""
    labels = getattr(task, "labels", []) or []
    name = getattr(task, "name", "")
    return "design" in labels and name.lower().startswith("design")


def _domain_slug(task_name: str) -> str:
    """Extract a slug from a design task name like 'Design Authentication'."""
    name = task_name.lower()
    if name.startswith("design "):
        name = name[7:]
    return name.strip().replace(" ", "-")


async def _generate_single_artifact(
    llm: Any,
    spec: Dict[str, Any],
    domain_name: str,
    domain_description: str,
    project_name: str,
    project_description: str,
    project_root_path: Any,
    context: Any,
    semaphore: asyncio.Semaphore,
) -> Optional[Dict[str, Any]]:
    """Generate one design artifact document via a single bounded LLM call.

    Builds the artifact prompt from the domain description, calls the LLM
    under the concurrency cap (see :func:`_bounded_llm_analyze`), writes
    the response to disk under ``project_root_path``, and returns the
    artifact metadata dict for later registration in Phase B.

    Returns ``None`` (and logs a warning) when the LLM response is empty
    or shorter than 20 characters — the caller treats that as "no
    artifact produced for this spec" without aborting the domain.

    This helper is domain-keyed, not task-keyed, so it can be called
    both from the feature-based path (where the caller derives
    ``domain_name`` / ``domain_description`` from a Task object via
    :func:`_generate_design_content`) and from the contract-first path
    (where the caller has a ``PRDAnalysis`` domains dict and never
    materializes Task objects — see GH-320 PR 1).

    Parameters
    ----------
    llm : Any
        LLM client instance.
    spec : Dict[str, Any]
        One entry from ``_DESIGN_ARTIFACT_SPECS`` describing the
        filename template, artifact type, and prompt label.
    domain_name : str
        Human-readable domain name without the ``"Design "`` prefix
        (e.g. ``"Authentication"``, not ``"Design Authentication"``).
        Used for the filename slug and the artifact description.
    domain_description : str
        Detailed description of the domain for the LLM prompt. Same
        shape as the task description generated by
        ``_create_bundled_design_tasks``.
    project_name : str
        Project name for prompt templating.
    project_description : str
        Full project description for prompt templating.
    project_root_path : pathlib.Path
        Absolute path to the project implementation directory.
    context : Any
        Context object passed to ``llm.analyze``.
    semaphore : asyncio.Semaphore
        Concurrency guard shared across all domain coroutines in the
        current invocation.

    Returns
    -------
    Optional[Dict[str, Any]]
        Artifact metadata dict with keys ``filename``, ``artifact_type``,
        ``content``, ``description``, ``relative_path`` — or ``None`` if
        the LLM returned an empty/short response.

    Raises
    ------
    Exception
        Propagates any unrecoverable LLM error after ``_bounded_llm_analyze``
        exhausts its retries. Also propagates disk I/O failures.
    """
    from pathlib import Path

    from src.marcus_mcp.tools.attachment import ARTIFACT_PATHS

    domain = _domain_slug(domain_name)
    fname = spec["filename_template"].format(domain_slug=domain)
    desc = spec["description_template"].format(domain=domain_name)

    if spec["label"] == "interface contracts":
        prompt = _INTERFACE_CONTRACTS_PROMPT.format(
            project_name=project_name,
            project_description=project_description,
            task_description=domain_description,
        )
    else:
        prompt = _ARTIFACT_PROMPT.format(
            project_name=project_name,
            project_description=project_description,
            task_description=domain_description,
            artifact_label=spec["label"],
        )

    response = await _bounded_llm_analyze(llm, prompt, context, semaphore)

    if not response or len(response.strip()) < 20:
        logger.warning(
            f"[design_autocomplete] Phase A: "
            f"empty/short response for "
            f"'{domain_name}' {spec['label']}"
        )
        return None

    # Write document to disk
    atype = spec["artifact_type"]
    base = ARTIFACT_PATHS.get(atype, "docs/artifacts")
    rel_path = Path(base) / fname
    full_path = project_root_path / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(response.strip(), encoding="utf-8")

    logger.info(f"[design_autocomplete] Phase A: wrote {rel_path}")

    return {
        "filename": fname,
        "artifact_type": atype,
        "content": response.strip(),
        "description": desc,
        "relative_path": str(rel_path),
    }


async def _generate_single_decisions(
    llm: Any,
    domain_name: str,
    domain_description: str,
    project_name: str,
    project_description: str,
    context: Any,
    semaphore: asyncio.Semaphore,
) -> List[Dict[str, Any]]:
    """Generate the decisions list for one domain via one LLM call.

    The decisions prompt is self-contained: it depends only on the
    domain description and project metadata, not on the artifact
    outputs, which is why it can run in parallel with the artifact
    calls (see GH-304).

    Domain-keyed like :func:`_generate_single_artifact` so the
    contract-first decomposition path (GH-320 PR 2) can call it
    directly with a ``PRDAnalysis`` domains dict, without needing
    Task objects.

    Parameters
    ----------
    llm : Any
        LLM client instance.
    domain_name : str
        Human-readable domain name, used only for log messages.
    domain_description : str
        Detailed description of the domain for the LLM prompt.
    project_name : str
        Project name for prompt templating.
    project_description : str
        Full project description for prompt templating.
    context : Any
        Context object passed to ``llm.analyze``.
    semaphore : asyncio.Semaphore
        Shared concurrency guard for the current invocation.

    Returns
    -------
    List[Dict[str, Any]]
        List of decision dicts, each with at least ``what``, ``why``,
        and ``impact`` keys. Empty list if the response could not be
        parsed as JSON (a warning is logged in that case).

    Raises
    ------
    Exception
        Propagates any unrecoverable LLM error after retries exhaust.
    """
    import json

    dec_prompt = _DECISIONS_PROMPT.format(
        project_name=project_name,
        project_description=project_description,
        task_description=domain_description,
    )

    dec_response = await _bounded_llm_analyze(llm, dec_prompt, context, semaphore)

    if not dec_response:
        return []

    try:
        from src.utils.json_parser import clean_json_response

        cleaned = clean_json_response(dec_response)
        parsed = json.loads(cleaned)
        # Response could be a list or {"decisions": [...]}
        if isinstance(parsed, list):
            dec_list = parsed
        elif isinstance(parsed, dict):
            dec_list = parsed.get("decisions", [])
        else:
            dec_list = []

        # Guard against malformed list elements (mixed types from the LLM:
        # strings, numbers, None) BEFORE checking for required keys.
        # Without the isinstance check, ``"what" in d`` raises TypeError on
        # non-iterables (or matches a substring on a string), which under
        # the GH-304 fail-fast gather would abort the entire design phase
        # for a recoverable formatting issue. See PR #319 Codex review.
        logged_decisions: List[Dict[str, Any]] = [
            d
            for d in dec_list
            if isinstance(d, dict) and all(k in d for k in ("what", "why", "impact"))
        ]

        logger.info(
            f"[design_autocomplete] Phase A: "
            f"{len(logged_decisions)} decision(s) "
            f"for '{domain_name}'"
        )
        return logged_decisions

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(
            f"[design_autocomplete] Phase A: "
            f"could not parse decisions for "
            f"'{domain_name}': {e}"
        )
        return []


async def _process_design_domain(
    llm: Any,
    domain_name: str,
    domain_description: str,
    project_name: str,
    project_description: str,
    project_root_path: Any,
    context: Any,
    semaphore: asyncio.Semaphore,
) -> Optional[Dict[str, Any]]:
    """Run all LLM calls for one domain concurrently (Level 2).

    Kicks off 4 artifact coroutines plus 1 decisions coroutine under a
    single ``asyncio.gather``, so all 5 LLM calls for a domain run in
    parallel, capped by the shared semaphore. Returns ``None`` when no
    artifacts were produced (the corresponding design task — if any —
    should stay TODO in that case).

    This helper is domain-keyed so it can be invoked both from the
    task-centric ``_generate_design_content`` (which converts tasks to
    domains before delegating here) and from the contract-first
    decomposition path (GH-320 PR 2) which has domain information from
    the PRD analysis before any tasks exist.

    Parameters
    ----------
    llm : Any
        LLM client instance.
    domain_name : str
        Human-readable domain name without the ``"Design "`` prefix.
    domain_description : str
        Detailed description of the domain for the LLM prompts.
    project_name : str
        Project name for prompt templating.
    project_description : str
        Full project description for prompt templating.
    project_root_path : pathlib.Path
        Absolute path to the project implementation directory.
    context : Any
        Context object passed through to each LLM call.
    semaphore : asyncio.Semaphore
        Shared concurrency guard across all domains.

    Returns
    -------
    Optional[Dict[str, Any]]
        ``{"artifacts": [...], "decisions": [...]}`` on success, or
        ``None`` if no artifacts survived the empty/short filter.

    Raises
    ------
    Exception
        Propagates the first unrecoverable LLM error (after retries)
        from any of the 5 parallel calls. Fail-fast: the caller aborts
        the whole design phase. See GH-304 decision rationale.
    """
    artifact_coros = [
        _generate_single_artifact(
            llm=llm,
            spec=spec,
            domain_name=domain_name,
            domain_description=domain_description,
            project_name=project_name,
            project_description=project_description,
            project_root_path=project_root_path,
            context=context,
            semaphore=semaphore,
        )
        for spec in _DESIGN_ARTIFACT_SPECS
    ]
    decisions_coro = _generate_single_decisions(
        llm=llm,
        domain_name=domain_name,
        domain_description=domain_description,
        project_name=project_name,
        project_description=project_description,
        context=context,
        semaphore=semaphore,
    )

    # Level 2 parallelism: 4 artifact calls + 1 decisions call all in flight
    # at once for this domain. The nested ``asyncio.gather`` shape lets mypy
    # infer the two result slots (list of artifacts, list of decisions)
    # without a ``cast``. gather() propagates the first exception (after
    # retries exhaust) and cancels the remaining coroutines.
    artifact_results, decisions = await asyncio.gather(
        asyncio.gather(*artifact_coros),
        decisions_coro,
    )

    written_artifacts: List[Dict[str, Any]] = [
        a for a in artifact_results if a is not None
    ]

    if not written_artifacts:
        logger.warning(
            f"[design_autocomplete] Phase A: no "
            f"artifacts for '{domain_name}' — "
            f"stays TODO"
        )
        return None

    n_a = len(written_artifacts)
    n_d = len(decisions)
    logger.info(
        f"[design_autocomplete] Phase A: "
        f"'{domain_name}' → {n_a} artifact(s), "
        f"{n_d} decision(s)"
    )

    return {"artifacts": written_artifacts, "decisions": decisions}


async def _generate_contracts_by_domain(
    domains: Dict[str, str],
    project_description: str,
    project_name: str,
    project_root: str,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """Generate contract artifacts for each domain in parallel.

    Standalone, task-free entry point for the Phase A design content
    generation. Takes a ``{domain_name: domain_description}`` mapping
    and produces one set of contract artifacts (architecture, API
    contracts, data models, interface contracts) plus a decisions log
    per domain.

    This is the domain-keyed sibling of :func:`_generate_design_content`:

    - :func:`_generate_design_content` starts from a list of Task
      objects, filters the design tasks, derives domains from their
      names/descriptions, and mutates the task list in-place to mark
      design tasks DONE on success (the feature-based path).
    - :func:`_generate_contracts_by_domain` starts from a domains dict
      directly and returns results keyed by domain name. It does not
      know about tasks and does not mutate any task state. This is
      what the contract-first decomposition path (GH-320 PR 2) will
      call once it has discovered domains from the PRD analysis but
      before any tasks exist.

    Both paths share the same inner Level 1 / Level 2 parallelism,
    the same ``Semaphore(10)`` concurrency cap, and the same
    ``@with_retry`` retry layer via the shared helpers
    :func:`_process_design_domain`, :func:`_generate_single_artifact`,
    and :func:`_generate_single_decisions`.

    Parameters
    ----------
    domains : Dict[str, str]
        Mapping of domain name -> detailed description. Domain names
        should NOT include a ``"Design "`` prefix — e.g. use
        ``"Authentication"``, not ``"Design Authentication"``. The
        descriptions are passed verbatim to the LLM prompts and
        should contain enough context for the model to produce a
        coherent contract.
    project_description : str
        Full project description for LLM context.
    project_name : str
        Project name.
    project_root : str
        Absolute path to project implementation directory. Artifact
        files are written under ``{project_root}/docs/...``.

    Returns
    -------
    Dict[str, Optional[Dict[str, Any]]]
        Mapping of domain name -> ``{"artifacts": [...], "decisions":
        [...]}`` on success, or ``None`` for domains where no artifacts
        were produced (the empty/short response path in
        :func:`_generate_single_artifact`). Domains that produced at
        least one artifact are non-None.

    Raises
    ------
    Exception
        Any unrecoverable LLM or I/O error from the parallel contract
        generation (fail-fast semantics — see GH-304). Disk side
        effects (partial artifact files under ``project_root``) may
        still be present on failure — this matches the
        :func:`_generate_design_content` behavior.

    See Also
    --------
    GH-297 : Phase A / Phase B design autocomplete design.
    GH-304 : Parallelization decision.
    GH-320 : Contract-first task decomposition (consumer in PR 2).
    """
    from pathlib import Path

    from src.ai.providers.llm_abstraction import LLMAbstraction

    project_root_path = Path(project_root)

    if not domains:
        return {}

    logger.info(
        f"[design_autocomplete] Phase A: generating contracts "
        f"for {len(domains)} domain(s) "
        f"(concurrency cap={_DESIGN_LLM_CONCURRENCY})"
    )

    llm = LLMAbstraction()

    class _Ctx:
        max_tokens = 4000

    # Create the semaphore inside the function so it binds to the
    # currently running event loop. See the comment in
    # :func:`_generate_design_content` for the rationale.
    semaphore = asyncio.Semaphore(_DESIGN_LLM_CONCURRENCY)

    domain_items = list(domains.items())

    domain_coros = [
        _process_design_domain(
            llm=llm,
            domain_name=domain_name,
            domain_description=domain_description,
            project_name=project_name,
            project_description=project_description,
            project_root_path=project_root_path,
            context=_Ctx(),
            semaphore=semaphore,
        )
        for domain_name, domain_description in domain_items
    ]

    # Level 1 parallelism. return_exceptions=False so the first
    # unrecoverable failure propagates immediately (fail-fast semantics
    # per GH-304). The thin try/except adds the batch size and domain
    # names to the error log so failures are diagnosable from logs
    # alone — the @with_retry layer only knows about a single failing
    # call, not the surrounding batch.
    try:
        domain_results = await asyncio.gather(*domain_coros)
    except Exception as exc:
        domain_names = ", ".join(repr(name) for name, _ in domain_items)
        logger.error(
            f"[design_autocomplete] Phase A: aborted batch of "
            f"{len(domain_items)} domain(s) due to "
            f"{type(exc).__name__}: {exc}. "
            f"domains in batch: {domain_names}"
        )
        raise

    return {
        domain_name: result
        for (domain_name, _), result in zip(domain_items, domain_results)
    }


async def _generate_design_content(
    tasks: List[Any],
    project_description: str,
    project_name: str,
    project_root: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Phase A: Generate design artifacts + decisions and set status to DONE.

    Makes separate LLM calls per artifact document, just like an agent
    would make separate ``log_artifact`` calls. Writes files to disk and
    marks design tasks as DONE. Runs BEFORE ``create_tasks_on_board`` so
    design tasks are born DONE on the kanban board.

    Parallelism (GH-304)
    --------------------
    Level 1 — across design tasks: all design tasks run concurrently via
    ``asyncio.gather``.
    Level 2 — within each task: the 4 artifact LLM calls and the 1
    decisions LLM call run concurrently for that task.

    Combined with the per-invocation ``asyncio.Semaphore`` cap of
    ``_DESIGN_LLM_CONCURRENCY`` (10), this brings a 10-task enterprise
    project from ~25–33 min (sequential) down to ~1–3 min wall-clock
    without exceeding rate limits.

    Failure semantics
    -----------------
    Fail-fast. Each LLM call is wrapped with
    ``@with_retry(RetryConfig(max_attempts=3, base_delay=2.0, jitter=True))``
    via :func:`_bounded_llm_analyze`. If retries exhaust for any single
    call, the exception propagates out of the inner ``gather``, aborts
    the outer ``gather``, and this function raises — no task state
    mutations happen, and the caller must retry project creation.

    This is a behavior change from pre-GH-304 code, which warned and
    continued on a per-task basis. Rationale: partial design results
    (some tasks designed, some not) silently corrupt downstream agent
    work. Hard-fail surfaces the problem immediately.

    Parameters
    ----------
    tasks : List[Any]
        All tasks (design + implementation). Design tasks are modified
        in-place on success: status set to DONE, ``assigned_to="Marcus"``,
        and ``"auto_completed"`` label added. No mutations happen on
        failure — state updates are atomic across all design tasks.
    project_description : str
        Full project description for LLM context.
    project_name : str
        Project name.
    project_root : str
        Absolute path to project implementation directory.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Mapping of task name -> ``{"artifacts": [...], "decisions": [...]}``
        for Phase B.

    Raises
    ------
    Exception
        Any unrecoverable LLM or I/O error from the parallel design calls
        (fail-fast). Disk side effects (partial artifact files under
        ``project_root_path``) may still be present on failure — this
        matches pre-GH-304 behavior.

    See Also
    --------
    GH-297 : Phase A / Phase B design autocomplete design.
    GH-304 : Parallelization decision and Kaia architectural review.
    """
    from pathlib import Path

    from src.ai.providers.llm_abstraction import LLMAbstraction

    project_root_path = Path(project_root)

    design_tasks = [t for t in tasks if _is_design_task(t)]
    if not design_tasks:
        return {}

    logger.info(
        f"[design_autocomplete] Phase A: generating content "
        f"for {len(design_tasks)} design task(s) "
        f"(concurrency cap={_DESIGN_LLM_CONCURRENCY})"
    )

    llm = LLMAbstraction()

    class _Ctx:
        max_tokens = 4000

    # Create the semaphore inside the function so it binds to the
    # currently running event loop. A module-level semaphore leaks
    # across pytest-asyncio function-scoped loops and causes confusing
    # test failures; binding per-call is cheap and guarantees
    # correctness.
    semaphore = asyncio.Semaphore(_DESIGN_LLM_CONCURRENCY)

    # Iterate per-task instead of collapsing into a ``{domain: task}``
    # dict. If two design tasks happen to share the same stripped
    # domain name, dict-keying would silently drop one of them — only
    # the second task would get its LLM calls made and its state
    # mutated. Per-task iteration preserves the pre-#320 behavior
    # exactly: each task gets its own LLM calls, each task gets its
    # own ``status=DONE`` mutation, and the task-keyed
    # ``design_content`` dict has whatever write-order semantics the
    # old code had. The contract-first decomposer in PR 2 uses
    # ``_generate_contracts_by_domain`` directly instead — that path
    # operates on a ``Dict[str, str]`` where uniqueness is a dict
    # invariant, so the collision case can't arise. See the Codex
    # review on PR #322.
    task_coros = []
    for task in design_tasks:
        task_name = task.name
        if task_name.startswith("Design "):
            domain_name = task_name[len("Design ") :]
        else:
            domain_name = task_name
        task_coros.append(
            _process_design_domain(
                llm=llm,
                domain_name=domain_name,
                domain_description=task.description,
                project_name=project_name,
                project_description=project_description,
                project_root_path=project_root_path,
                context=_Ctx(),
                semaphore=semaphore,
            )
        )

    # Level 1 parallelism. return_exceptions=False so the first
    # unrecoverable failure propagates immediately (fail-fast semantics
    # per GH-304). The thin try/except adds the batch size and task
    # names to the error log so failures are diagnosable from logs
    # alone — the @with_retry layer only knows about a single failing
    # call, not the surrounding batch.
    try:
        task_results = await asyncio.gather(*task_coros)
    except Exception as exc:
        task_names = ", ".join(repr(t.name) for t in design_tasks)
        logger.error(
            f"[design_autocomplete] Phase A: aborted batch of "
            f"{len(design_tasks)} design task(s) due to "
            f"{type(exc).__name__}: {exc}. "
            f"tasks in batch: {task_names}"
        )
        raise

    # All tasks finished without raising. Atomically update task state
    # on the board-bound Task objects and assemble the design_content
    # mapping for Phase B. The task-keyed shape of design_content is
    # preserved exactly, including the overwrite-on-collision semantics
    # of the pre-#320 code (if two tasks share a name, the second one
    # wins the dict slot, but both have their LLM calls made and both
    # are marked DONE).
    design_content: Dict[str, Dict[str, Any]] = {}
    for task, result in zip(design_tasks, task_results):
        if result is None:
            # No artifacts produced — task stays TODO, warning already
            # logged inside ``_process_design_domain``. Skip state
            # mutation for this task.
            continue

        design_content[task.name] = result

        # Mark task as DONE before it hits the board
        task.status = TaskStatus.DONE
        task.assigned_to = "Marcus"
        if not hasattr(task, "labels") or task.labels is None:
            task.labels = []
        if "auto_completed" not in task.labels:
            task.labels.append("auto_completed")

        logger.info(f"[design_autocomplete] Phase A: " f"'{task.name}' status=DONE")

    return design_content


_SCAFFOLD_PROMPT = """\
You are a senior software architect. Generate the project scaffold \
for the following project.

## Project
{project_name}: {project_description}

## Architecture Document
{architecture_content}

## Implementation Tasks
{impl_task_list}

## Instructions
Generate ONLY the shared build/tooling infrastructure. The implementing \
agents decide everything about the application code.

ALLOWED files (generate these):
- Package manifest (package.json, pyproject.toml, Cargo.toml, etc.)
- Build configuration (tsconfig, vite.config, eslint config, etc.)
- Entry point (main.tsx, main.py, main.rs — minimal, just mounts app)
- App shell (App.tsx or equivalent — imports components, no styling logic)
- Tooling config (.gitignore, .env.example)
- ONE placeholder file per implementation task (see below)

FORBIDDEN — do NOT generate these:
- TypeScript interfaces, types, or data model definitions
- Utility functions, helpers, or service implementations
- CSS files, stylesheets, or design tokens
- Test files or test configuration
- Any file with more than 3 lines of actual code (configs excepted)

Placeholder files must contain EXACTLY one comment line:
// TimeWidget — implementation task for agent

The .gitignore MUST include: node_modules/, dist/, *.js (in src/), \
.env, and build artifacts appropriate for the project type.

Respond with ONLY a JSON array of files. No markdown fencing:
[{{"path": "package.json", "content": "..."}}, \
{{"path": "src/main.tsx", "content": "..."}}]
"""


async def _generate_project_scaffold(
    tasks: List[Any],
    project_description: str,
    project_name: str,
    project_root: str,
    design_content: Dict[str, Dict[str, Any]],
) -> bool:
    """
    Generate project scaffold and write to disk on main.

    Reads the architecture doc from design_content, generates
    shared infrastructure files (package manifest, config, entry
    point) and empty placeholder files per implementation task.
    Written to project_root so worktrees inherit them.

    Parameters
    ----------
    tasks : List[Any]
        All tasks including implementation tasks.
    project_description : str
        Project description.
    project_name : str
        Project name.
    project_root : str
        Path to implementation/ directory on main.
    design_content : Dict[str, Dict]
        From _generate_design_content, contains architecture doc.

    Returns
    -------
    bool
        True if scaffold was generated successfully.

    See: https://github.com/lwgray/marcus/issues/300
    """
    import json
    from pathlib import Path

    from src.ai.providers.llm_abstraction import LLMAbstraction

    project_root_path = Path(project_root)

    # Get the architecture doc content from design_content
    arch_content = ""
    for task_name, content in design_content.items():
        for art in content.get("artifacts", []):
            if art.get("artifact_type") == "architecture":
                arch_content = art.get("content", "")
                break
        if arch_content:
            break

    if not arch_content:
        logger.warning(
            "[scaffold] No architecture doc found — " "skipping scaffold generation"
        )
        return False

    # Build implementation task list
    impl_tasks = [
        t
        for t in tasks
        if not _is_design_task(t)
        and getattr(t, "name", "").lower().startswith("implement")
    ]
    impl_task_list = "\n".join(
        f"- {t.name}: {(t.description or '')[:100]}" for t in impl_tasks
    )

    if not impl_task_list:
        logger.warning(
            "[scaffold] No implementation tasks found — " "skipping scaffold generation"
        )
        return False

    llm = LLMAbstraction()

    class _Ctx:
        max_tokens = 4000

    prompt = _SCAFFOLD_PROMPT.format(
        project_name=project_name,
        project_description=project_description,
        architecture_content=arch_content,
        impl_task_list=impl_task_list,
    )

    try:
        response = await llm.analyze(prompt=prompt, context=_Ctx())

        if not response:
            logger.warning("[scaffold] Empty LLM response")
            return False

        # Parse JSON array of files
        from src.utils.json_parser import clean_json_response

        cleaned = clean_json_response(response)
        files = json.loads(cleaned)

        if not isinstance(files, list):
            logger.warning("[scaffold] Expected JSON array")
            return False

        # Filter out over-generated files (GH-307)
        # Config files can be any length. Non-config files must be
        # ≤3 lines (placeholder comment only). This prevents the LLM
        # from generating types, utils, CSS, or implementation code.
        config_extensions = {
            ".json",
            ".toml",
            ".yaml",
            ".yml",
            ".cjs",
            ".mjs",
            ".config.ts",
            ".config.js",
        }
        config_names = {
            ".gitignore",
            ".env.example",
            ".eslintrc",
            "tsconfig.json",
            "tsconfig.node.json",
            "vite.config.ts",
            "vite.config.js",
        }

        # Write each file to disk
        written = 0
        rejected = 0
        for f in files:
            fpath = f.get("path")
            fcontent = f.get("content")
            if not fpath or fcontent is None:
                continue

            # Check if this is a config/tooling file
            fname = Path(fpath).name
            is_config = (
                any(fname.endswith(ext) for ext in config_extensions)
                or fname in config_names
                or fname == "index.html"
                or "main." in fname
                or "App." in fname
            )

            # Non-config files must be ≤3 lines
            if not is_config:
                line_count = len(fcontent.strip().splitlines())
                if line_count > 3:
                    logger.info(
                        f"[scaffold] Rejected {fpath} "
                        f"({line_count} lines — over limit)"
                    )
                    rejected += 1
                    continue

            full_path = project_root_path / fpath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(fcontent, encoding="utf-8")
            written += 1

        if rejected > 0:
            logger.info(f"[scaffold] Rejected {rejected} over-generated " f"file(s)")

        logger.info(
            f"[scaffold] Wrote {written} scaffold file(s) " f"to {project_root}"
        )

        # Commit scaffold to main so worktrees inherit it
        import subprocess

        subprocess.run(
            ["git", "add", "-A"],
            cwd=project_root,
            capture_output=True,
        )
        result = subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "scaffold: project infrastructure (Marcus)",
            ],
            cwd=project_root,
            capture_output=True,
        )
        if result.returncode == 0:
            logger.info("[scaffold] Committed scaffold to main")
        else:
            logger.warning(f"[scaffold] Commit failed: " f"{result.stderr.decode()}")

        return written > 0

    except Exception as e:
        logger.warning(f"[scaffold] Failed: {e}")
        return False


async def _register_design_via_mcp(
    state: Any,
    design_content: Dict[str, Dict[str, Any]],
    project_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Phase B: Register pre-generated artifacts + decisions via MCP tools.

    Runs AFTER state.refresh_project_state() so we have real kanban
    UUIDs and the MCP state object. Calls log_artifact and log_decision
    through the proper codepaths so state.task_artifacts and
    state.context.decisions are populated for get_task_context.

    Parameters
    ----------
    state : Any
        MCP server state (fully initialized after refresh).
    design_content : Dict[str, Dict]
        From Phase A: task name → {artifacts, decisions}.
    project_root : Optional[str]
        Project root for log_artifact.

    Returns
    -------
    Dict[str, Any]
        Summary counts.
    """
    from src.marcus_mcp.tools.attachment import log_artifact
    from src.marcus_mcp.tools.context import log_decision

    result = {
        "tasks_completed": 0,
        "artifacts_registered": 0,
        "decisions_logged": 0,
    }

    if not design_content or not state.project_tasks:
        return result

    # Match state tasks to Phase A content by name
    for task in state.project_tasks:
        name = getattr(task, "name", "")
        if name not in design_content:
            continue

        content = design_content[name]
        task_id = task.id  # Real kanban UUID

        # Register artifacts via MCP tool
        if project_root:
            for art in content.get("artifacts", []):
                art_result = await log_artifact(
                    task_id=task_id,
                    filename=art["filename"],
                    content=art["content"],
                    artifact_type=art["artifact_type"],
                    project_root=project_root,
                    description=art.get("description", ""),
                    state=state,
                )
                if art_result.get("success"):
                    result["artifacts_registered"] += 1
                    loc = art_result["data"]["location"]
                    logger.info(f"[design_autocomplete] Phase B: " f"registered {loc}")

        # Register decisions via MCP tool
        for dec in content.get("decisions", []):
            required = ("what", "why", "impact")
            if not all(k in dec for k in required):
                continue
            dec_text = (
                f"{dec['what']} because {dec['why']}. " f"This affects {dec['impact']}"
            )
            dec_result = await log_decision(
                agent_id="Marcus",
                task_id=task_id,
                decision=dec_text,
                state=state,
            )
            if dec_result.get("success"):
                result["decisions_logged"] += 1
                logger.info(
                    f"[design_autocomplete] Phase B: " f"decision \"{dec['what']}\""
                )

        result["tasks_completed"] += 1

    return result


async def _run_design_phase(
    state: Any,
    kanban_client: Any,
    safe_tasks: List[Task],
    created_tasks: List[Task],
    description: str,
    project_name: str,
    project_root: str,
) -> None:
    """
    Run the full background design phase: Phase A + Phase B + kanban + scaffold.

    This orchestrates four steps in a fixed order:

    1. **Phase A** — :func:`_generate_design_content` produces design
       artifacts and decisions for each design task via parallel LLM
       calls (GH-297, GH-304). Fail-fast: any unrecoverable LLM error
       aborts the entire phase and no downstream steps run.
    2. **Phase B** — :func:`_register_design_via_mcp` registers the
       generated artifacts into ``state.task_artifacts`` keyed by the
       real kanban UUIDs, so downstream implementation tasks discover
       them via the dependency walk in
       :func:`_collect_task_artifacts` (GH-320).
    3. **Kanban DONE update** — mark design task cards as done,
       which unblocks implementation tasks from hard dependencies.
    4. **Scaffold generation** — :func:`_generate_project_scaffold`
       writes initial project scaffolding files.

    Ordering is load-bearing
    ------------------------
    Phase B (step 2) MUST run before the kanban DONE update (step 3).
    The DONE update is what unblocks implementation tasks from hard
    dependencies — if Phase B runs after, there is a window where:

    1. Design task marked DONE on kanban
    2. Implementation task unblocked
    3. Agent requests implementation task
    4. :func:`_collect_task_artifacts` walks dependencies, finds
       empty ``state.task_artifacts[design_task_id]``
    5. Agent receives no contracts

    The window is sub-second but races don't care about narrow
    windows. The ordering pinned here and tested by
    ``TestRunDesignPhaseHandoff`` prevents it entirely.

    Regression history
    ------------------
    Before GH-314 (commit 1c5c7f7, April 6, 2026), Phase A was
    synchronous inside ``create_project_from_description`` and its
    output was stored in ``result["design_content"]``. Phase B ran
    separately inside ``src/marcus_mcp/tools/nlp.py`` after
    ``refresh_project_state``, reading ``design_content`` out of the
    result dict.

    GH-314 moved Phase A to a background closure and deleted the
    line ``result["design_content"] = design_content``. This
    orphaned the Phase B call in nlp.py, which continued to read
    ``result.get("design_content", {})`` — an empty dict forever.
    The Phase B handoff was dead for 5 days until GH-320 caught it.

    This function is the fix: Phase A and Phase B run together in
    the same closure, so the handoff cannot be broken by refactoring
    one without touching the other. The dead Phase B block in
    nlp.py was removed as part of the same fix.

    Parameters
    ----------
    state : Any
        Marcus MCP server state. Required for Phase B — used to
        populate ``state.task_artifacts`` via ``log_artifact``. If
        ``None``, Phase B is skipped with a warning (legacy behavior
        preserved for callers that don't pass state).
    kanban_client : Any
        Kanban client for marking design tasks DONE.
    safe_tasks : List[Any]
        Pre-board-creation task objects used to derive design task
        names and descriptions.
    created_tasks : List[Any]
        Post-board-creation task objects with real kanban UUIDs. The
        index must align with ``safe_tasks``.
    description : str
        Original project description (passed to Phase A LLM calls).
    project_name : str
        Project name (passed to Phase A and scaffold).
    project_root : str
        Absolute path where artifacts will be written.

    Returns
    -------
    None
        This is a background task — callers fire-and-forget via
        :func:`asyncio.ensure_future`. All failures are logged and
        non-fatal by design.

    See Also
    --------
    _generate_design_content : Phase A implementation.
    _register_design_via_mcp : Phase B implementation.
    tests.unit.integrations.test_design_autocomplete.TestRunDesignPhaseHandoff :
        Regression guard for the ordering invariant.

    Notes
    -----
    GH-297 : Original two-phase design autocomplete.
    GH-304 : Parallelization (Phase A 25-33min → 1-3min).
    GH-314 : Moved Phase A to background (accidentally orphaned Phase B).
    GH-320 : Reconnected Phase A → Phase B handoff (this function).
    """
    design_content: Dict[str, Any] = {}
    try:
        design_content = await _generate_design_content(
            tasks=safe_tasks,
            project_description=description,
            project_name=project_name,
            project_root=project_root,
        )
        logger.info("[design_autocomplete] Background Phase A complete")
    except Exception as e:
        logger.warning(
            f"[design_autocomplete] Background Phase A failed (non-fatal): {e}"
        )
        # Fail-fast semantics: partial design outputs silently
        # corrupt downstream agent work (#304). Return early so no
        # Phase B, no kanban DONE updates, no scaffold.
        return

    if not design_content:
        logger.info(
            "[design_autocomplete] Phase A produced no content, skipping Phase B"
        )
        return

    # Phase B — MUST run before kanban DONE update. See docstring
    # "Ordering is load-bearing" section for why.
    #
    # Race avoidance: Phase B matches ``state.project_tasks`` to
    # ``design_content`` by task name. Because this closure runs as a
    # background task, ``state.project_tasks`` may still be stale at
    # the moment Phase B fires — the MCP tool caller's
    # ``refresh_project_state()`` might not have completed yet. To
    # close that race, refresh state ourselves before Phase B so the
    # name match sees current kanban UUIDs. Codex review on PR #326
    # caught the original hole: without this refresh, Phase B could
    # silently register zero artifacts against an empty task list
    # and the closure would still mark design tasks DONE, leaving
    # impl tasks to unblock without contracts — the exact silent
    # failure mode this function is supposed to eliminate.
    phase_b_registered = 0
    if state is not None:
        if hasattr(state, "refresh_project_state"):
            try:
                await state.refresh_project_state()
            except Exception as e:
                logger.warning(
                    f"[design_autocomplete] Pre-Phase-B state refresh "
                    f"failed: {e}. Phase B may see stale project_tasks."
                )
        try:
            phase_b_result = await _register_design_via_mcp(
                state=state,
                design_content=design_content,
                project_root=project_root,
            )
            phase_b_registered = int(phase_b_result.get("artifacts_registered", 0))
            logger.info(
                f"[design_autocomplete] Phase B: registered "
                f"{phase_b_registered} "
                f"artifact(s), "
                f"{phase_b_result.get('decisions_logged', 0)} "
                f"decision(s) via MCP tools"
            )
        except Exception as e:
            logger.warning(f"[design_autocomplete] Phase B failed (non-fatal): {e}")
    else:
        logger.warning(
            "[design_autocomplete] Phase B skipped: state is None "
            "(design artifacts written to disk but not registered in "
            "state.task_artifacts; downstream tasks will not discover "
            "them via get_task_context)"
        )

    # Zero-registration guard (Codex review on PR #326).
    #
    # When ``state`` is provided and Phase A produced design content,
    # Phase B MUST have registered at least one artifact for the
    # kanban DONE update to be safe. If it registered zero, something
    # is badly wrong — most likely ``state.project_tasks`` was still
    # empty or none of the names matched. Marking design tasks DONE
    # now would unblock impl tasks and they would walk dependencies
    # into empty ``state.task_artifacts`` entries, reintroducing the
    # silent-failure mode PR #326 was designed to eliminate.
    #
    # Skipping the DONE updates means impl tasks stay blocked on
    # their design deps. That's the correct degenerate state: the
    # user sees "design tasks never completed" in the kanban and can
    # investigate, rather than seeing "implementation agents
    # produced code that doesn't integrate and nobody knows why."
    # Loud failure > silent corruption.
    #
    # The ``state is None`` path is exempt from this guard because
    # legacy callers explicitly opt out of Phase B entirely — for
    # them, the DONE updates are the only thing moving design tasks
    # to the next state and skipping them would hang the project.
    if state is not None and design_content and phase_b_registered == 0:
        logger.error(
            "[design_autocomplete] Phase B registered 0 artifacts "
            "despite Phase A producing design_content. Refusing to "
            "mark design tasks DONE — impl tasks would unblock "
            "without contracts (exact silent failure mode from "
            "#314). Design tasks will stay TODO; investigate why "
            "state.project_tasks did not match design_content names. "
            f"design_content keys: {list(design_content.keys())}"
        )
        return

    # Kanban DONE update — unblocks implementation tasks. Runs
    # AFTER Phase B so that state.task_artifacts is already
    # populated when dependents walk the dependency graph.
    #
    # ``created_tasks`` and ``safe_tasks`` are index-aligned by
    # construction in ``create_project_from_description``: each
    # ``created_tasks[i]`` is the kanban-created counterpart of
    # ``safe_tasks[i]``. ``zip`` is O(n) and handles the shorter-list
    # case gracefully if the two arrays ever get out of sync.
    for ct, orig in zip(created_tasks, safe_tasks):
        if _is_design_task(orig) and orig.name in design_content:
            try:
                await kanban_client.update_task(
                    ct.id,
                    {"status": "done"},
                )
                logger.info(
                    f"[design_autocomplete] Marked '{orig.name}' " f"DONE on board"
                )
            except Exception as e:
                logger.warning(
                    f"[design_autocomplete] Failed to update board "
                    f"for '{orig.name}': {e}"
                )

    # Scaffold generation — best effort, non-fatal on failure
    try:
        await _generate_project_scaffold(
            tasks=safe_tasks,
            project_description=description,
            project_name=project_name,
            project_root=project_root,
            design_content=design_content,
        )
        logger.info("[scaffold] Background generation complete")
    except Exception as e:
        logger.warning(f"[scaffold] Background generation failed (non-fatal): {e}")


async def add_feature_natural_language(
    feature_description: str, integration_point: str = "auto_detect", state: Any = None
) -> Dict[str, Any]:
    """
    MCP tool to add a feature to existing project using natural language.

    This is the main entry point that Claude will call.
    """
    try:
        # Validate required parameters
        if not feature_description or not feature_description.strip():
            return {
                "success": False,
                "error": "Feature description is required and cannot be empty",
            }

        # Check if state was provided
        if state is None:
            raise ValueError("State parameter is required")

        # Initialize kanban client if needed
        if not state.kanban_client:
            try:
                await state.initialize_kanban()
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to initialize kanban client: {str(e)}",
                }

        # Verify kanban client supports create_task
        if not hasattr(state.kanban_client, "create_task"):
            return {
                "success": False,
                "error": (
                    "Kanban client does not support task creation. "
                    "Please ensure KanbanClientWithCreate is being used."
                ),
            }

        # Check if there are existing tasks (required for feature addition)
        if not state.project_tasks or len(state.project_tasks) == 0:
            return {
                "success": False,
                "error": (
                    "No existing project found. "
                    "Please create a project first before adding features."
                ),
            }

        # Initialize feature adder
        adder = NaturalLanguageFeatureAdder(
            kanban_client=state.kanban_client,
            ai_engine=state.ai_engine,
            project_tasks=state.project_tasks,
        )

        # Add feature
        result = await adder.add_feature_from_description(
            feature_description=feature_description, integration_point=integration_point
        )

        # Update Marcus state if successful
        if result.get("success"):
            try:
                await state.refresh_project_state()
            except Exception as e:
                # Log but don't fail the operation
                logger.warning(f"Failed to refresh project state: {str(e)}")

        return result

    except Exception as e:
        logger.error(f"Unexpected error in add_feature_natural_language: {str(e)}")
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
