"""
Base class for Natural Language task creation

Provides shared functionality for create_project and add_feature tools.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

from src.core.models import Task, TaskStatus
from src.integrations.nlp_task_utils import (
    TaskClassifier, TaskBuilder, SafetyChecker, TaskType
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
    
    def __init__(self, kanban_client, ai_engine=None):
        """
        Initialize the base task creator.
        
        Args:
            kanban_client: Kanban board client with create_task method
            ai_engine: Optional AI engine for enhanced processing
        """
        self.kanban_client = kanban_client
        self.ai_engine = ai_engine
        self.task_classifier = TaskClassifier()
        self.task_builder = TaskBuilder()
        self.safety_checker = SafetyChecker()
    
    async def create_tasks_on_board(
        self, 
        tasks: List[Task],
        skip_validation: bool = False
    ) -> List[Task]:
        """
        Create tasks on the kanban board.
        
        This is the main shared functionality between create_project and add_feature.
        
        Args:
            tasks: List of tasks to create
            skip_validation: Skip dependency validation if True
            
        Returns:
            List of created tasks
            
        Raises:
            RuntimeError: If kanban client doesn't support task creation
        """
        # Validate dependencies if requested
        if not skip_validation:
            errors = self.safety_checker.validate_dependencies(tasks)
            if errors:
                logger.warning(f"Dependency validation errors: {errors}")
        
        # Check if kanban client supports task creation
        if not hasattr(self.kanban_client, 'create_task'):
            from src.core.error_framework import KanbanIntegrationError, ErrorContext
            
            raise KanbanIntegrationError(
                board_name=getattr(self.kanban_client, 'board_id', 'unknown'),
                operation="task_creation_validation",
                details=f"Kanban client {type(self.kanban_client).__name__} does not support task creation. "
                       f"Expected KanbanClientWithCreate or compatible implementation. "
                       f"Current client type: {type(self.kanban_client).__module__}.{type(self.kanban_client).__name__}",
                context=ErrorContext(
                    operation="create_tasks_on_board",
                    integration_name="natural_language_tools",
                    client_type=type(self.kanban_client).__name__
                )
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
                from src.core.error_framework import KanbanIntegrationError, ErrorContext
                from src.core.error_monitoring import record_error_for_monitoring
                
                # Create proper error with context
                kanban_error = KanbanIntegrationError(
                    board_name=getattr(self.kanban_client, 'board_id', 'unknown'),
                    operation="individual_task_creation",
                    details=f"Failed to create task '{task.name}': {str(e)}",
                    context=ErrorContext(
                        operation="create_tasks_on_board",
                        integration_name="natural_language_tools",
                        custom_context={
                            "task_name": task.name,
                            "task_type": getattr(task, 'task_type', 'unknown')
                        }
                    )
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
            from src.core.error_framework import KanbanIntegrationError, ErrorContext
            
            raise KanbanIntegrationError(
                board_name=getattr(self.kanban_client, 'board_id', 'unknown'),
                operation="batch_task_creation",
                details=f"Failed to create any of {len(tasks)} tasks. All task creation attempts failed. "
                       f"This indicates a fundamental issue with the kanban integration or board configuration.",
                context=ErrorContext(
                    operation="create_tasks_on_board",
                    integration_name="natural_language_tools",
                    total_tasks=len(tasks),
                    failed_tasks=len(failed_tasks)
                )
            )
        
        return created_tasks
    
    async def apply_safety_checks(self, tasks: List[Task]) -> List[Task]:
        """
        Apply safety checks to ensure logical task ordering.
        
        This method can be overridden by subclasses for custom safety logic.
        
        Args:
            tasks: List of tasks to check
            
        Returns:
            List of tasks with updated dependencies
        """
        # Apply deployment dependencies
        tasks = self.safety_checker.apply_deployment_dependencies(tasks)
        
        # Apply testing dependencies
        tasks = self.safety_checker.apply_testing_dependencies(tasks)
        
        return tasks
    
    def classify_tasks(self, tasks: List[Task]) -> Dict[TaskType, List[Task]]:
        """
        Classify tasks by their type.
        
        Args:
            tasks: List of tasks to classify
            
        Returns:
            Dictionary mapping task types to lists of tasks
        """
        classified = {task_type: [] for task_type in list(TaskType)}
        
        for task in tasks:
            task_type = self.task_classifier.classify(task)
            classified[task_type].append(task)
        
        return classified
    
    def get_tasks_by_type(self, tasks: List[Task], task_type: TaskType) -> List[Task]:
        """Get all tasks of a specific type"""
        return self.task_classifier.filter_by_type(tasks, task_type)
    
    def is_deployment_task(self, task: Task) -> bool:
        """Check if task is deployment-related"""
        return self.task_classifier.is_type(task, TaskType.DEPLOYMENT)
    
    def is_implementation_task(self, task: Task) -> bool:
        """Check if task is implementation-related"""
        return self.task_classifier.is_type(task, TaskType.IMPLEMENTATION)
    
    def is_testing_task(self, task: Task) -> bool:
        """Check if task is testing-related"""
        return self.task_classifier.is_type(task, TaskType.TESTING)
    
    @abstractmethod
    async def process_natural_language(
        self, 
        description: str,
        **kwargs
    ) -> List[Task]:
        """
        Process natural language description into tasks.
        
        This method must be implemented by subclasses.
        
        Args:
            description: Natural language description
            **kwargs: Additional parameters specific to the implementation
            
        Returns:
            List of generated tasks
        """
        pass
    
    async def create_from_description(
        self,
        description: str,
        apply_safety: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Main entry point for natural language task creation.
        
        Args:
            description: Natural language description
            apply_safety: Whether to apply safety checks
            **kwargs: Additional parameters for processing
            
        Returns:
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
                        "type": self.task_classifier.classify(task).value
                    }
                    for task in created_tasks
                ],
                "task_types": {
                    task_type.value: len(self.get_tasks_by_type(created_tasks, task_type))
                    for task_type in list(TaskType)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in create_from_description: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "tasks_created": 0
            }