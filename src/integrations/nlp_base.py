"""Base class for Natural Language task creation.

Provides shared functionality for create_project and add_feature tools.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from src.core.models import Task
from src.core.task_graph_validator import TaskGraphValidator
from src.integrations.enhanced_task_classifier import EnhancedTaskClassifier
from src.integrations.nlp_task_utils import (
    SafetyChecker,
    TaskBuilder,
    TaskType,
)

logger = logging.getLogger(__name__)


class NaturalLanguageTaskCreator(ABC):
    """
    Base class for natural language task creation tools.

    Provides common functionality for:
    - Task creation on kanban boards
    - Safety checks and validation
    - Task classification
    - Error handling
    """

    def __init__(
        self,
        kanban_client: Any,
        ai_engine: Any = None,
        subtask_manager: Any = None,
        complexity: str = "standard",
    ) -> None:
        """
        Initialize the base task creator.

        Parameters
        ----------
        kanban_client : Any
            Kanban board client with create_task method
        ai_engine : Any, optional
            Optional AI engine for enhanced processing
        subtask_manager : Any, optional
            Optional SubtaskManager for registering decomposed subtasks
        complexity : str, default="standard"
            Project complexity level: "prototype", "standard", "enterprise"
        """
        self.kanban_client = kanban_client
        self.ai_engine = ai_engine
        self.subtask_manager = subtask_manager
        self.complexity = complexity
        self.task_classifier = EnhancedTaskClassifier()
        self.task_builder = TaskBuilder()
        self.safety_checker = SafetyChecker()

    async def create_tasks_on_board(
        self,
        tasks: List[Task],
        skip_validation: bool = False,
        update_dependencies: bool = True,
    ) -> List[Task]:
        """
        Create tasks on the kanban board.

        This is the main shared functionality between create_project and add_feature.

        Parameters
        ----------
        tasks : List[Task]
            List of tasks to create
        skip_validation : bool
            Skip dependency validation if True
        update_dependencies : bool
            Update task dependencies with new IDs after creation

        Returns
        -------
        List[Task]
            List of created tasks

        Raises
        ------
        RuntimeError
            If kanban client doesn't support task creation
        """
        # CRITICAL: Auto-fix task graph issues BEFORE committing to Kanban
        # This fixes problems automatically rather than raising exceptions
        if not skip_validation:
            # Auto-fix task graph issues
            fixed_tasks, user_warnings = TaskGraphValidator.validate_and_fix(tasks)
            tasks = fixed_tasks  # Use the fixed version

            # Log user-friendly warnings
            if user_warnings:
                logger.warning(
                    f"Task graph auto-fixed: {len(user_warnings)} issues corrected"
                )
                for warning in user_warnings:
                    logger.info(f"  • {warning}")

            # Also run legacy safety checker (diagnostic warnings)
            errors = self.safety_checker.validate_dependencies(tasks)
            if errors:
                logger.warning(f"Dependency validation errors: {errors}")

        # Check if kanban client supports task creation
        if not hasattr(self.kanban_client, "create_task"):
            from src.core.error_framework import ErrorContext, KanbanIntegrationError

            raise KanbanIntegrationError(
                board_name=getattr(self.kanban_client, "board_id", "unknown"),
                operation="task_creation_validation",
                context=ErrorContext(
                    operation="create_tasks_on_board",
                    integration_name="natural_language_tools",
                    custom_context={
                        "client_type": type(self.kanban_client).__name__,
                        "details": (
                            f"Kanban client "
                            f"{type(self.kanban_client).__name__} does not "
                            f"support task creation. Expected "
                            f"KanbanClientWithCreate or compatible "
                            f"implementation. Current client type: "
                            f"{type(self.kanban_client).__module__}."
                            f"{type(self.kanban_client).__name__}"
                        ),
                    },
                ),
            )

        created_tasks = []
        failed_tasks = []

        for task in tasks:
            try:
                # Build task data using utility
                task_data = self.task_builder.build_task_data(task)

                # Create task on board
                logger.info(f"Creating task: {task.name}")
                kanban_task = await self.kanban_client.create_task(task_data)
                created_tasks.append(kanban_task)

            except Exception as e:
                from src.core.error_framework import (
                    ErrorContext,
                    KanbanIntegrationError,
                )
                from src.core.error_monitoring import record_error_for_monitoring

                # Create proper error with context
                kanban_error = KanbanIntegrationError(
                    board_name=getattr(self.kanban_client, "board_id", "unknown"),
                    operation="individual_task_creation",
                    context=ErrorContext(
                        operation="create_tasks_on_board",
                        integration_name="natural_language_tools",
                        custom_context={
                            "task_name": task.name,
                            "task_type": getattr(task, "task_type", "unknown"),
                            "details": f"Failed to create task '{task.name}': {str(e)}",
                        },
                    ),
                )

                # Record for monitoring but continue processing
                record_error_for_monitoring(kanban_error)
                logger.error(f"Failed to create task '{task.name}': {kanban_error}")
                failed_tasks.append((task, str(kanban_error)))
                # Continue with other tasks even if one fails

        # Log summary
        logger.info(
            f"Task creation complete: {len(created_tasks)} succeeded, "
            f"{len(failed_tasks)} failed"
        )

        if failed_tasks:
            logger.error(f"Failed tasks: {[(t.name, e) for t, e in failed_tasks]}")

        # Check if no tasks were created at all
        if not created_tasks and tasks:
            from src.core.error_framework import ErrorContext, KanbanIntegrationError

            raise KanbanIntegrationError(
                board_name=getattr(self.kanban_client, "board_id", "unknown"),
                operation="batch_task_creation",
                context=ErrorContext(
                    operation="create_tasks_on_board",
                    integration_name="natural_language_tools",
                    custom_context={
                        "total_tasks": len(tasks),
                        "failed_tasks": len(failed_tasks),
                        "details": (
                            f"Failed to create any of {len(tasks)} tasks. "
                            f"All task creation attempts failed. This "
                            f"indicates a fundamental issue with the kanban "
                            f"integration or board configuration."
                        ),
                    },
                ),
            )

        # Decompose tasks that meet criteria and add as checklist items
        await self._decompose_and_add_subtasks(created_tasks, tasks)

        # Wire cross-parent dependencies after decomposition completes
        await self._wire_cross_parent_dependencies()

        return created_tasks

    async def _decompose_and_add_subtasks(
        self, created_tasks: List[Task], original_tasks: List[Task]
    ) -> None:
        """
        Decompose tasks that meet criteria and add subtasks as Planka checklist items.

        Uses parallel AI calls for performance - all task decompositions are
        executed concurrently instead of sequentially.

        Parameters
        ----------
        created_tasks : List[Task]
            Tasks that were created on the Kanban board
        original_tasks : List[Task]
            Original task objects with estimated_hours
        """
        # Skip decomposition if no AI engine is available
        if not self.ai_engine:
            logger.debug("No AI engine available for task decomposition - skipping")
            return

        # Log decomposition context
        logger.debug(
            f"Task decomposition started: {len(created_tasks)} tasks, "
            f"SubtaskManager available: {self.subtask_manager is not None}"
        )

        # Note: AI engine now uses LLMAbstraction which automatically
        # checks provider availability and supports local models (Ollama),
        # Anthropic, and OpenAI. If no provider is configured,
        # decompose_task will raise a clear error message.

        import asyncio

        from src.marcus_mcp.coordinator import decompose_task, should_decompose

        # Create mapping of task names to original tasks (for estimated_hours)
        task_map = {task.name: task for task in original_tasks}

        # Collect all tasks that need decomposition for parallel execution
        decomposition_jobs = []
        task_metadata = []  # Track (created_task, original_task) pairs

        for created_task in created_tasks:
            # Get original task to check estimated hours
            original_task = task_map.get(created_task.name)
            if not original_task:
                continue

            # Check if task should be decomposed
            # Pass complexity for prototype mode check
            if not should_decompose(original_task, project_complexity=self.complexity):
                continue

            logger.info(
                f"Queueing task '{created_task.name}' for decomposition "
                f"({original_task.estimated_hours}h)"
            )

            # Add decomposition job to parallel execution list
            # CRITICAL: Pass created_task which has the real Planka ID,
            # not original_task. We need to create a task object that has
            # both the real ID and the original details
            task_with_real_id = Task(
                id=created_task.id,  # Real Planka ID
                name=original_task.name,
                description=original_task.description,
                status=original_task.status,
                priority=original_task.priority,
                assigned_to=original_task.assigned_to,
                created_at=original_task.created_at,
                updated_at=original_task.updated_at,
                due_date=original_task.due_date,
                estimated_hours=original_task.estimated_hours,
                actual_hours=original_task.actual_hours,
                dependencies=original_task.dependencies,
                labels=original_task.labels,
                project_id=getattr(original_task, "project_id", None),
                project_name=getattr(original_task, "project_name", None),
            )
            # Pass complexity through project_context for time budgets and validation
            project_context = {"complexity": self.complexity}
            decomposition_jobs.append(
                decompose_task(
                    task_with_real_id, self.ai_engine, project_context=project_context
                )
            )
            task_metadata.append((created_task, original_task))

        # Execute all decompositions in parallel
        if not decomposition_jobs:
            logger.debug("No tasks require decomposition")
            return

        logger.info(f"Decomposing {len(decomposition_jobs)} tasks in parallel...")

        decomposition_results = await asyncio.gather(
            *decomposition_jobs, return_exceptions=True
        )

        # Process results and add checklist items
        successful_count = 0
        failed_count = 0

        for idx, result in enumerate(decomposition_results):
            created_task, original_task = task_metadata[idx]

            try:
                # Handle exceptions from gather (both Exception and BaseException)
                if isinstance(result, BaseException):
                    failed_count += 1
                    logger.error(
                        (
                            f"Decomposition failed for task "
                            f"'{created_task.name}': {result}"
                        ),
                        exc_info=result if isinstance(result, Exception) else None,
                    )
                    continue

                # Handle failed decomposition responses
                if not result.get("success"):
                    failed_count += 1
                    logger.warning(
                        f"Failed to decompose task '{created_task.name}': "
                        f"{result.get('error')}"
                    )
                    continue

                # Successfully decomposed - add subtasks
                subtasks = result.get("subtasks", [])
                shared_conventions = result.get("shared_conventions", {})
                num_subtasks = len(subtasks)
                logger.info(
                    f"Task '{created_task.name}' decomposed into "
                    f"{num_subtasks} subtasks"
                )

                # Register subtasks with SubtaskManager (GH-62 fix)
                if self.subtask_manager:
                    from src.marcus_mcp.coordinator.subtask_manager import (
                        SubtaskMetadata,
                    )

                    metadata = SubtaskMetadata(
                        shared_conventions=shared_conventions,
                        decomposed_by="ai",
                    )
                    self.subtask_manager.add_subtasks(
                        parent_task_id=created_task.id,
                        subtasks=subtasks,
                        metadata=metadata,
                    )
                    logger.info(
                        f"Registered {num_subtasks} subtasks with SubtaskManager "
                        f"for task '{created_task.name}'"
                    )
                else:
                    logger.warning(
                        "SubtaskManager not available - subtasks will only exist as "
                        "checklist items (GH-62)"
                    )

                # Add subtasks as checklist items in Planka
                await self._add_subtasks_as_checklist(created_task.id, subtasks)
                successful_count += 1

            except Exception as e:
                failed_count += 1
                logger.error(
                    (
                        f"Error processing decomposition for task "
                        f"'{created_task.name}': {e}"
                    ),
                    exc_info=True,
                )
                # Continue with other tasks even if processing fails

        # Log summary
        logger.info(
            f"Task decomposition complete: {successful_count} succeeded, "
            f"{failed_count} failed"
        )

    async def _wire_cross_parent_dependencies(self) -> None:
        """
        Wire cross-parent dependencies after decomposition completes.

        This is called after all tasks have been decomposed to create
        fine-grained dependencies between subtasks of different parent tasks.
        """
        # Skip if no subtask manager or AI engine
        if not self.subtask_manager or not self.ai_engine:
            logger.debug(
                "Skipping cross-parent dependency wiring - "
                "required components not available"
            )
            return

        # Note: Cross-parent dependency wiring is implemented in
        # server.refresh_project_state() where we have access to unified
        # project_tasks storage
        logger.info(
            "Cross-parent dependency wiring will be performed "
            "during project state refresh"
        )

    async def _add_subtasks_as_checklist(
        self, parent_card_id: str, subtasks: List[Dict[str, Any]]
    ) -> None:
        """
        Add subtasks as checklist items (tasks) in Planka.

        Parameters
        ----------
        parent_card_id : str
            ID of the parent card in Planka
        subtasks : List[Dict[str, Any]]
            List of subtask definitions from decomposition
        """
        try:
            import os

            from mcp.client.stdio import stdio_client

            from mcp import ClientSession, StdioServerParameters

            # Use same server params as PlankaKanban
            # Use local path for kanban-mcp
            kanban_mcp_path = os.path.expanduser("~/dev/kanban-mcp/dist/index.js")
            server_params = StdioServerParameters(
                command="node",
                args=[kanban_mcp_path],
                env=os.environ.copy(),
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # Create checklist item for each subtask
                    for idx, subtask in enumerate(subtasks):
                        subtask_name = subtask.get("name", f"Subtask {idx + 1}")

                        # Create task (checklist item) in Planka
                        result = await session.call_tool(
                            "mcp_kanban_task_manager",
                            {
                                "action": "create",
                                "cardId": parent_card_id,
                                "name": subtask_name,
                                "position": (idx + 1) * 65535,
                            },
                        )

                        if result:
                            logger.info(
                                f"Created checklist item '{subtask_name}' "
                                f"on card {parent_card_id}"
                            )

            num_added = len(subtasks)
            logger.info(
                f"Added {num_added} subtasks as checklist items "
                f"to card {parent_card_id}"
            )

        except Exception as e:
            logger.error(
                f"Error adding subtasks as checklist items to card "
                f"{parent_card_id}: {e}",
                exc_info=True,
            )

    async def apply_safety_checks(self, tasks: List[Task]) -> List[Task]:
        """
        Apply safety checks to ensure logical task ordering.

        This method can be overridden by subclasses for custom safety logic.

        Parameters
        ----------
        tasks : List[Task]
            List of tasks to check

        Returns
        -------
        List[Task]
            List of tasks with updated dependencies
        """
        # Import phase dependency enforcer
        from src.core.phase_dependency_enforcer import PhaseDependencyEnforcer

        # First apply phase-based dependencies for proper ordering
        phase_enforcer = PhaseDependencyEnforcer()
        tasks = phase_enforcer.enforce_phase_dependencies(tasks)

        # Then apply legacy safety checks for additional constraints
        # These may add extra dependencies but won't conflict with phase ordering

        # Apply implementation dependencies (implementation depends on design)
        tasks = self.safety_checker.apply_implementation_dependencies(tasks)

        # Apply testing dependencies (testing depends on implementation)
        tasks = self.safety_checker.apply_testing_dependencies(tasks)

        # Apply deployment dependencies (deployment depends on everything)
        tasks = self.safety_checker.apply_deployment_dependencies(tasks)

        return tasks

    def classify_tasks(self, tasks: List[Task]) -> Dict[TaskType, List[Task]]:
        """
        Classify tasks by their type.

        Parameters
        ----------
        tasks : List[Task]
            List of tasks to classify

        Returns
        -------
        Dict[TaskType, List[Task]]
            Dictionary mapping task types to lists of tasks
        """
        classified: Dict[TaskType, List[Task]] = {
            task_type: [] for task_type in list(TaskType)
        }

        for task in tasks:
            task_type = self.task_classifier.classify(task)
            classified[task_type].append(task)

        return classified

    def classify_tasks_with_details(
        self, tasks: List[Task]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Classify tasks and return detailed classification info per task.

        Parameters
        ----------
        tasks : List[Task]
            List of tasks to classify

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Dictionary mapping task IDs to classification details
        """
        from src.integrations.enhanced_task_classifier import EnhancedTaskClassifier

        classifier = EnhancedTaskClassifier()
        results = {}

        for task in tasks:
            result = classifier.classify_with_confidence(task)
            results[task.id] = {
                "type": result.task_type.value,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
            }

        return results

    def get_tasks_by_type(self, tasks: List[Task], task_type: TaskType) -> List[Any]:
        """Get all tasks of a specific type."""
        return self.task_classifier.filter_by_type(tasks, task_type)

    def is_deployment_task(self, task: Task) -> Any:
        """Check if task is deployment-related."""
        return self.task_classifier.is_type(task, TaskType.DEPLOYMENT)

    def is_implementation_task(self, task: Task) -> Any:
        """Check if task is implementation-related."""
        return self.task_classifier.is_type(task, TaskType.IMPLEMENTATION)

    def is_testing_task(self, task: Task) -> Any:
        """Check if task is testing-related."""
        return self.task_classifier.is_type(task, TaskType.TESTING)

    @abstractmethod
    async def process_natural_language(
        self, description: str, **kwargs: Any
    ) -> List[Task]:
        """
        Process natural language description into tasks.

        This method must be implemented by subclasses.

        Parameters
        ----------
        description : str
            Natural language description
        **kwargs : Any
            Additional parameters specific to the implementation

        Returns
        -------
        List[Task]
            List of generated tasks
        """
        pass

    async def create_from_description(
        self, description: str, apply_safety: bool = True, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Create tasks from natural language description.

        Parameters
        ----------
        description : str
            Natural language description
        apply_safety : bool
            Whether to apply safety checks
        **kwargs : Any
            Additional parameters for processing

        Returns
        -------
        Dict[str, Any]
            Dictionary with creation results
        """
        try:
            # Process natural language into tasks
            tasks = await self.process_natural_language(description, **kwargs)

            # Apply safety checks if requested
            if apply_safety:
                tasks = await self.apply_safety_checks(tasks)

            # Create tasks on board
            created_tasks = await self.create_tasks_on_board(tasks)

            # Build result
            result = {
                "success": True,
                "tasks_created": len(created_tasks),
                "tasks": [
                    {
                        "id": task.id,
                        "name": task.name,
                        "type": self.task_classifier.classify(task).value,
                    }
                    for task in created_tasks
                ],
                "task_types": {
                    task_type.value: len(
                        self.get_tasks_by_type(created_tasks, task_type)
                    )
                    for task_type in list(TaskType)
                },
            }

            return result

        except Exception as e:
            logger.error(f"Error in create_from_description: {str(e)}")
            return {"success": False, "error": str(e), "tasks_created": 0}
