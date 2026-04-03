"""
Natural Language MCP Tools for Marcus (Refactored).

These tools expose Marcus's AI capabilities for:
1. Creating projects from natural language descriptions
2. Adding features to existing projects

This refactored version eliminates code duplication by using base classes and utilities.
"""

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
from src.detection.board_analyzer import BoardAnalyzer  # noqa: E402
from src.detection.context_detector import ContextDetector, MarcusMode  # noqa: E402

# Import refactored base classes and utilities
from src.integrations.nlp_base import NaturalLanguageTaskCreator  # noqa: E402
from src.integrations.nlp_task_utils import TaskType  # noqa: E402
from src.integrations.project_auto_setup import ProjectAutoSetup  # noqa: E402
from src.modes.adaptive.basic_adaptive import BasicAdaptiveMode  # noqa: E402

logger = logging.getLogger(__name__)


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
    ) -> None:
        super().__init__(kanban_client, ai_engine, subtask_manager, complexity)
        self.prd_parser = AdvancedPRDParser()
        self.board_analyzer = BoardAnalyzer()
        self.context_detector = ContextDetector(self.board_analyzer)

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

            # Phase A (GH-297): Generate design artifacts + decisions
            # and set design tasks to DONE BEFORE they hit the board.
            # This prevents the race condition where agents grab
            # design tasks before Marcus can complete them.
            design_content: Dict[str, Any] = {}
            project_root = options.get("project_root") if options else None
            if project_root:
                try:
                    design_content = await _generate_design_content(
                        tasks=safe_tasks,
                        project_description=description,
                        project_name=project_name,
                        project_root=project_root,
                    )
                except Exception as e:
                    logger.warning(
                        f"[design_autocomplete] Phase A failed " f"(non-fatal): {e}"
                    )

                # Phase A.5: Generate project scaffold from architecture doc
                # Shared infrastructure committed to main so worktrees inherit it.
                # See: GH-300
                if design_content:
                    try:
                        await _generate_project_scaffold(
                            tasks=safe_tasks,
                            project_description=description,
                            project_name=project_name,
                            project_root=project_root,
                            design_content=design_content,
                        )
                    except Exception as e:
                        logger.warning(
                            f"[scaffold] Generation failed " f"(non-fatal): {e}"
                        )

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

            # Pass design content for Phase B (MCP registration)
            if design_content:
                result["design_content"] = design_content

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

Good: "The time display updates every second using the browser's \
Date API and supports timezone conversion."
Bad: "TimeWidget (src/components/TimeWidget.tsx) takes props \
timeFormat: '24h' | '12h' and uses setInterval(1000)."

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
]


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


async def _generate_design_content(
    tasks: List[Any],
    project_description: str,
    project_name: str,
    project_root: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Phase A: Generate design artifacts + decisions and set status to DONE.

    Makes separate LLM calls per artifact document, just like an agent
    would make separate log_artifact calls. Writes files to disk and
    marks design tasks as DONE. Runs BEFORE create_tasks_on_board so
    design tasks are born DONE on the kanban board.

    Parameters
    ----------
    tasks : List[Any]
        All tasks (design + implementation). Design tasks are
        modified in-place: status set to DONE, auto_completed
        label added.
    project_description : str
        Full project description for LLM context.
    project_name : str
        Project name.
    project_root : str
        Absolute path to project implementation directory.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Mapping of task name -> {artifacts, decisions} for Phase B.

    See: https://github.com/lwgray/marcus/issues/297
    """
    import json
    from pathlib import Path

    from src.ai.providers.llm_abstraction import LLMAbstraction
    from src.marcus_mcp.tools.attachment import ARTIFACT_PATHS

    design_content: Dict[str, Dict[str, Any]] = {}
    project_root_path = Path(project_root)

    design_tasks = [t for t in tasks if _is_design_task(t)]
    if not design_tasks:
        return design_content

    logger.info(
        f"[design_autocomplete] Phase A: generating content "
        f"for {len(design_tasks)} design task(s)"
    )

    llm = LLMAbstraction()

    class _Ctx:
        max_tokens = 4000

    for task in design_tasks:
        try:
            domain = _domain_slug(task.name)
            written_artifacts: List[Dict[str, Any]] = []
            logged_decisions: List[Dict[str, Any]] = []

            # Generate each artifact document separately
            for spec in _DESIGN_ARTIFACT_SPECS:
                fname = spec["filename_template"].format(domain_slug=domain)
                desc = spec["description_template"].format(
                    domain=task.name.replace("Design ", "")
                )

                prompt = _ARTIFACT_PROMPT.format(
                    project_name=project_name,
                    project_description=project_description,
                    task_description=task.description,
                    artifact_label=spec["label"],
                )

                response = await llm.analyze(prompt=prompt, context=_Ctx())

                if not response or len(response.strip()) < 20:
                    logger.warning(
                        f"[design_autocomplete] Phase A: "
                        f"empty/short response for "
                        f"'{task.name}' {spec['label']}"
                    )
                    continue

                # Write document to disk
                atype = spec["artifact_type"]
                base = ARTIFACT_PATHS.get(atype, "docs/artifacts")
                rel_path = Path(base) / fname
                full_path = project_root_path / rel_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(response.strip(), encoding="utf-8")

                written_artifacts.append(
                    {
                        "filename": fname,
                        "artifact_type": atype,
                        "content": response.strip(),
                        "description": desc,
                        "relative_path": str(rel_path),
                    }
                )

                logger.info(f"[design_autocomplete] Phase A: " f"wrote {rel_path}")

            # Generate decisions separately
            dec_prompt = _DECISIONS_PROMPT.format(
                project_name=project_name,
                project_description=project_description,
                task_description=task.description,
            )

            dec_response = await llm.analyze(prompt=dec_prompt, context=_Ctx())

            if dec_response:
                try:
                    from src.utils.json_parser import (
                        clean_json_response,
                    )

                    cleaned = clean_json_response(dec_response)
                    parsed = json.loads(cleaned)
                    # Response could be a list or {"decisions": [...]}
                    if isinstance(parsed, list):
                        dec_list = parsed
                    elif isinstance(parsed, dict):
                        dec_list = parsed.get("decisions", [])
                    else:
                        dec_list = []

                    for d in dec_list:
                        if all(k in d for k in ("what", "why", "impact")):
                            logged_decisions.append(d)

                    logger.info(
                        f"[design_autocomplete] Phase A: "
                        f"{len(logged_decisions)} decision(s) "
                        f"for '{task.name}'"
                    )
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(
                        f"[design_autocomplete] Phase A: "
                        f"could not parse decisions for "
                        f"'{task.name}': {e}"
                    )

            # Only mark DONE if we produced at least one artifact
            if not written_artifacts:
                logger.warning(
                    f"[design_autocomplete] Phase A: no "
                    f"artifacts for '{task.name}' — "
                    f"stays TODO"
                )
                continue

            # Store for Phase B
            design_content[task.name] = {
                "artifacts": written_artifacts,
                "decisions": logged_decisions,
            }

            # Mark task as DONE before it hits the board
            task.status = TaskStatus.DONE
            task.assigned_to = "Marcus"
            if not hasattr(task, "labels") or task.labels is None:
                task.labels = []
            if "auto_completed" not in task.labels:
                task.labels.append("auto_completed")

            n_a = len(written_artifacts)
            n_d = len(logged_decisions)
            logger.info(
                f"[design_autocomplete] Phase A: "
                f"'{task.name}' → {n_a} artifact(s), "
                f"{n_d} decision(s), status=DONE"
            )

        except Exception as e:
            logger.warning(
                f"[design_autocomplete] Phase A: failed "
                f"for '{task.name}': {e} — stays TODO"
            )
            continue

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
Generate the project scaffold — the shared infrastructure files that \
ALL developers need before they can start working on their components. \
This includes:

- Package manifest (package.json, pyproject.toml, Cargo.toml, etc.)
- Build configuration (tsconfig, vite.config, eslint, etc.)
- Entry point file (main.tsx, main.py, main.rs, etc.)
- Base app shell that imports/renders components
- Any shared configuration (.gitignore, .env.example, etc.)

Also create ONE empty placeholder file per implementation task. Each \
placeholder should contain ONLY a comment with the component name — \
no function stubs, no exports, no implementation code. Example:
// TimeWidget — implementation task for agent

The placeholder file paths should match the architecture document's \
conventions.

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

        # Write each file to disk
        written = 0
        for f in files:
            fpath = f.get("path")
            fcontent = f.get("content")
            if not fpath or fcontent is None:
                continue
            full_path = project_root_path / fpath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(fcontent, encoding="utf-8")
            written += 1

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


# MCP Tool Functions remain the same
# Simplified version - just the create_project function
async def create_project_from_natural_language(
    description: str,
    project_name: str,
    state: Any = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    MCP tool to create a NEW project from natural language description.

    This tool ALWAYS creates a new project - it does not search for or reuse
    existing projects. For working with existing projects, use select_project
    or create_tasks tools instead.

    This is the main entry point that Claude will call.
    """
    try:
        # Initialize options with default mode
        if options is None:
            options = {}
        if "mode" not in options:
            options["mode"] = "new_project"

        # Validate required parameters
        if not description or not description.strip():
            return {
                "success": False,
                "error": "Description is required and cannot be empty",
            }

        if not project_name or not project_name.strip():
            return {
                "success": False,
                "error": "Project name is required and cannot be empty",
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

        # Always clear stale project/board IDs to force new project creation
        if state.kanban_client:
            state.kanban_client.project_id = None
            state.kanban_client.board_id = None
            logger.info(f"Creating NEW project '{project_name}'")

        # Default from config, experiment options can override
        from src.config.marcus_config import get_config

        default_provider = get_config().kanban.provider or "sqlite"
        provider = options.get("provider", default_provider)

        logger.info(f"Auto-creating {provider} project '{project_name}'")

        try:
            # Use ProjectAutoSetup for provider-agnostic creation
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
                marcus_project_id = await state.project_registry.add_project(
                    project_config
                )
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

        # Verify kanban client supports create_task
        if not hasattr(state.kanban_client, "create_task"):
            return {
                "success": False,
                "error": (
                    "Kanban client does not support task creation. "
                    "Please ensure KanbanClientWithCreate is being used."
                ),
            }

        # Get subtask_manager if available (GH-62 fix)
        subtask_manager = getattr(state, "subtask_manager", None)

        # Extract complexity from options (default to "standard")
        complexity = options.get("complexity", "standard") if options else "standard"

        # Initialize project creator with complexity
        creator = NaturalLanguageProjectCreator(
            kanban_client=state.kanban_client,
            ai_engine=state.ai_engine,
            subtask_manager=subtask_manager,
            complexity=complexity,
        )
        creator.active_project_id = marcus_project_id

        # Create project
        result = await creator.create_project_from_description(
            description=description, project_name=project_name, options=options
        )

        # Add Marcus project_id to result for auto-select functionality
        if result.get("success") and marcus_project_id:
            result["project_id"] = marcus_project_id

        # Update Marcus state if successful
        if result.get("success"):
            try:
                await state.refresh_project_state()
                logger.info(
                    f"[DEBUG] After refresh_project_state: project_tasks has "
                    f"{len(state.project_tasks) if state.project_tasks else 0} tasks"
                )
            except Exception as e:
                # Log but don't fail the operation
                logger.error(
                    f"Failed to refresh project state: {str(e)}", exc_info=True
                )

            # Phase B (GH-297): Register design artifacts + decisions
            # via MCP tools so state.task_artifacts and
            # state.context.decisions are populated for get_task_context.
            # Design tasks are already DONE on the board (Phase A ran
            # before create_tasks_on_board in create_project_from_description).
            design_content = result.get("design_content", {})
            if design_content:
                try:
                    project_root = options.get("project_root") if options else None
                    phase_b = await _register_design_via_mcp(
                        state=state,
                        design_content=design_content,
                        project_root=project_root,
                    )
                    if phase_b.get("tasks_completed", 0) > 0:
                        logger.info(
                            f"[design_autocomplete] Phase B: "
                            f"registered "
                            f"{phase_b['artifacts_registered']}"
                            f" artifact(s), "
                            f"{phase_b['decisions_logged']}"
                            f" decision(s) via MCP tools"
                        )
                    result["design_autocomplete"] = phase_b
                except Exception as e:
                    logger.warning(
                        f"[design_autocomplete] Phase B " f"failed (non-fatal): {e}"
                    )

        return result

    except Exception as e:
        logger.error(
            f"Unexpected error in create_project_from_natural_language: {str(e)}"
        )
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


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
