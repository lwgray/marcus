"""
Natural Language Task Processing Utilities

Shared utilities for natural language task creation tools.
Eliminates code duplication between create_project and add_feature.
"""

from enum import Enum
from typing import Dict, Any, List
from src.core.models import Task, TaskStatus, Priority
import logging

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task type classification"""
    DEPLOYMENT = "deployment"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"


class TaskClassifier:
    """Classify tasks by their type based on keywords"""
    
    # Keyword mappings for task classification
    TASK_KEYWORDS = {
        TaskType.DEPLOYMENT: [
            "deploy", "release", "production", "launch", "rollout",
            "publish", "ship", "go-live", "deliver"
        ],
        TaskType.IMPLEMENTATION: [
            "implement", "build", "create", "develop", "code",
            "construct", "write", "design", "architect", "refactor"
        ],
        TaskType.TESTING: [
            "test", "qa", "quality", "verify", "validate",
            "check", "assert", "spec", "unittest", "integration"
        ],
        TaskType.DOCUMENTATION: [
            "document", "docs", "readme", "guide", "tutorial",
            "manual", "wiki", "annotate", "comment"
        ],
        TaskType.INFRASTRUCTURE: [
            "setup", "configure", "install", "provision", "infrastructure",
            "database", "server", "environment", "docker", "kubernetes"
        ]
    }
    
    @classmethod
    def classify(cls, task: Task) -> TaskType:
        """
        Classify a task based on its name and description.
        
        Args:
            task: Task to classify
            
        Returns:
            TaskType enum value
        """
        # Combine name and description for better classification
        text_to_check = f"{task.name} {task.description}".lower()
        
        # Check each task type's keywords
        for task_type, keywords in list(cls.TASK_KEYWORDS.items()):
            if any(keyword in text_to_check for keyword in keywords):
                return task_type
        
        return TaskType.OTHER
    
    @classmethod
    def is_type(cls, task: Task, task_type: TaskType) -> bool:
        """Check if a task is of a specific type"""
        return cls.classify(task) == task_type
    
    @classmethod
    def filter_by_type(cls, tasks: List[Task], task_type: TaskType) -> List[Task]:
        """Filter tasks by type"""
        return [task for task in tasks if cls.classify(task) == task_type]


class TaskBuilder:
    """Build task data structures for kanban board creation"""
    
    @staticmethod
    def build_task_data(task: Task) -> Dict[str, Any]:
        """
        Build a dictionary of task data for kanban board creation.
        
        Args:
            task: Task object to convert
            
        Returns:
            Dictionary with task data ready for kanban API
        """
        return {
            "name": task.name,
            "description": task.description,
            "priority": task.priority.value if hasattr(task.priority, 'value') else task.priority,
            "labels": task.labels,
            "estimated_hours": task.estimated_hours,
            "dependencies": task.dependencies,
            # Additional fields that might be needed
            "status": task.status.value if hasattr(task.status, 'value') else task.status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "metadata": {
                "ai_generated": True,
                "source": "natural_language"
            }
        }
    
    @staticmethod
    def build_minimal_task_data(task: Task) -> Dict[str, Any]:
        """Build minimal task data (for APIs with fewer fields)"""
        return {
            "name": task.name,
            "description": task.description,
            "priority": task.priority.value if hasattr(task.priority, 'value') else task.priority,
            "labels": task.labels
        }


class SafetyChecker:
    """Apply safety checks to ensure logical task ordering"""
    
    @staticmethod
    def apply_deployment_dependencies(tasks: List[Task]) -> List[Task]:
        """
        Ensure deployment tasks depend on implementation and testing tasks.
        
        This prevents premature deployment by establishing proper dependencies.
        
        Args:
            tasks: List of tasks to check
            
        Returns:
            List of tasks with updated dependencies
        """
        deployment_tasks = TaskClassifier.filter_by_type(tasks, TaskType.DEPLOYMENT)
        implementation_tasks = TaskClassifier.filter_by_type(tasks, TaskType.IMPLEMENTATION)
        testing_tasks = TaskClassifier.filter_by_type(tasks, TaskType.TESTING)
        
        for deploy_task in deployment_tasks:
            # Ensure deployment depends on ALL implementation tasks
            for impl_task in implementation_tasks:
                if impl_task.id not in deploy_task.dependencies:
                    deploy_task.dependencies.append(impl_task.id)
                    logger.debug(f"Added dependency: {deploy_task.name} depends on {impl_task.name}")
            
            # Ensure deployment depends on ALL testing tasks
            for test_task in testing_tasks:
                if test_task.id not in deploy_task.dependencies:
                    deploy_task.dependencies.append(test_task.id)
                    logger.debug(f"Added dependency: {deploy_task.name} depends on {test_task.name}")
        
        return tasks
    
    @staticmethod
    def apply_testing_dependencies(tasks: List[Task]) -> List[Task]:
        """
        Ensure testing tasks depend on implementation tasks.
        
        Args:
            tasks: List of tasks to check
            
        Returns:
            List of tasks with updated dependencies
        """
        testing_tasks = TaskClassifier.filter_by_type(tasks, TaskType.TESTING)
        implementation_tasks = TaskClassifier.filter_by_type(tasks, TaskType.IMPLEMENTATION)
        
        for test_task in testing_tasks:
            # Find related implementation tasks (by matching labels or keywords)
            related_impl_tasks = SafetyChecker._find_related_tasks(
                test_task, implementation_tasks
            )
            
            for impl_task in related_impl_tasks:
                if impl_task.id not in test_task.dependencies:
                    test_task.dependencies.append(impl_task.id)
                    logger.debug(f"Added dependency: {test_task.name} depends on {impl_task.name}")
        
        return tasks
    
    @staticmethod
    def _find_related_tasks(task: Task, candidate_tasks: List[Task]) -> List[Task]:
        """Find tasks that are related based on labels and keywords"""
        related = []
        
        # Check label overlap
        task_labels = set(task.labels)
        for candidate in candidate_tasks:
            candidate_labels = set(candidate.labels)
            if task_labels & candidate_labels:  # If there's any overlap
                related.append(candidate)
                continue
            
            # Check keyword similarity in names
            task_words = set(task.name.lower().split())
            candidate_words = set(candidate.name.lower().split())
            # Remove common words
            common_words = {"the", "a", "an", "and", "or", "for", "to", "in", "of"}
            task_words -= common_words
            candidate_words -= common_words
            
            if task_words & candidate_words:  # If there's any overlap
                related.append(candidate)
        
        return related
    
    @staticmethod
    def validate_dependencies(tasks: List[Task]) -> List[str]:
        """
        Validate that all dependencies reference existing tasks.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        task_ids = {task.id for task in tasks}
        
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    errors.append(
                        f"Task '{task.name}' has invalid dependency '{dep_id}'"
                    )
        
        return errors