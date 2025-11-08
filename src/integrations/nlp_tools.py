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

            # Check if project/board already set up (by tracked version)
            # If so, skip project creation to avoid duplication
            if self.kanban_client and (
                self.kanban_client.project_id and self.kanban_client.board_id
            ):
                proj_id = self.kanban_client.project_id
                bd_id = self.kanban_client.board_id
                logger.info(
                    f"Project already created: project_id={proj_id}, "
                    f"board_id={bd_id}"
                )
            elif options and options.get("mode") == "new_project":
                # Only create project if not already created
                if self.kanban_client:
                    logger.info(
                        f"Clearing project/board IDs for new_project mode "
                        f"(current: project_id={self.kanban_client.project_id}, "
                        f"board_id={self.kanban_client.board_id})"
                    )
                    # Set on the underlying client
                    # (Planka wrapper has read-only properties)
                    if hasattr(self.kanban_client, "client"):
                        self.kanban_client.client.project_id = None
                        self.kanban_client.client.board_id = None
                    else:
                        # Direct client (not a wrapper)
                        self.kanban_client.project_id = None
                        self.kanban_client.board_id = None
                    logger.info(
                        "Cleared project/board IDs to force new project creation"
                    )

                    # Now create the new project/board
                    from src.integrations.project_auto_setup import ProjectAutoSetup

                    auto_setup = ProjectAutoSetup()
                    try:
                        # Pass the underlying client (not the wrapper) if available
                        client_to_use = (
                            self.kanban_client.client
                            if hasattr(self.kanban_client, "client")
                            else self.kanban_client
                        )
                        project_config = await auto_setup.setup_planka_project(
                            kanban_client=client_to_use,
                            project_name=project_name,
                            options=options,
                        )
                        proj_id = project_config.provider_config.get("project_id")
                        bd_id = project_config.provider_config.get("board_id")
                        logger.info(
                            f"Created new Planka project: "
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

                # Add documentation task if appropriate
                from src.integrations.documentation_tasks import (
                    enhance_project_with_documentation,
                )

                safe_tasks = enhance_project_with_documentation(
                    safe_tasks, description, project_name
                )
                logger.info(f"After documentation enhancement: {len(safe_tasks)} tasks")

                # Log safety check impact
                added_tasks = len(safe_tasks) - len(tasks)
                if added_tasks > 0:
                    logger.info(f"Safety checks added {added_tasks} dependency tasks")

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

            result = {
                "success": True,
                "project_name": project_name,
                "tasks_created": len(created_tasks),
                "task_breakdown": task_breakdown,
                "phases": self._extract_phases(safe_tasks),
                "estimated_days": self._estimate_duration(safe_tasks),
                "dependencies_mapped": self._count_dependencies(safe_tasks),
                "risk_level": self._assess_risk_by_count(len(created_tasks)),
                "confidence": 0.85,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Successfully created project with {len(created_tasks)} tasks")

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

        # Get provider from options or default to planka
        provider = options.get("provider", "planka")

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
