"""Natural Language Task Processing Utilities.

Shared utilities for natural language task creation tools.
Eliminates code duplication between create_project and add_feature.
"""

import logging
from enum import Enum
from typing import Any, Dict, List

from src.core.models import Task

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task type classification."""

    DESIGN = "design"
    DEPLOYMENT = "deployment"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"


class TaskClassifier:
    """Classify tasks by their type based on keywords."""

    # Keyword mappings for task classification
    TASK_KEYWORDS = {
        TaskType.DESIGN: [
            "design",
            "architect",
            "plan",
            "specification",
            "wireframe",
            "mockup",
            "diagram",
            "blueprint",
            "prototype",
            "architecture",
            "planning",
        ],
        TaskType.DEPLOYMENT: [
            "deploy",
            "release",
            "production",
            "launch",
            "rollout",
            "publish",
            "go-live",
            "deliver",
            "staging",
            "live",
        ],
        TaskType.IMPLEMENTATION: [
            "implement",
            "build",
            "create",
            "develop",
            "code",
            "construct",
            "write",
            "refactor",
            "program",
            "engineer",
        ],
        TaskType.TESTING: [
            "test",
            "qa",
            "quality",
            "verify",
            "validate",
            "check",
            "assert",
            "unittest",
            "integration",
            "e2e",
            "coverage",
        ],
        TaskType.DOCUMENTATION: [
            "document",
            "docs",
            "readme",
            "guide",
            "tutorial",
            "manual",
            "wiki",
            "annotate",
            "comment",
        ],
        TaskType.INFRASTRUCTURE: [
            "setup",
            "configure",
            "install",
            "provision",
            "infrastructure",
            "database",
            "server",
            "environment",
            "docker",
            "kubernetes",
        ],
    }

    @classmethod
    def classify(cls, task: Task) -> TaskType:
        """
        Classify a task based on its name and description.

        Parameters
        ----------
        task : Task
            Task to classify

        Returns
        -------
        TaskType
            TaskType enum value
        """
        # Combine name and description for better classification
        text_to_check = f"{task.name} {task.description}".lower()

        # Check in priority order - more specific types first
        # Testing should be checked before Implementation to catch "Write tests" tasks
        priority_order = [
            TaskType.DEPLOYMENT,  # Most specific - deployment keywords are unique
            TaskType.TESTING,  # Check before implementation to catch "write tests"
            TaskType.DOCUMENTATION,  # Check before implementation to catch "write docs"
            TaskType.DESIGN,  # Check before implementation to catch "design API"
            TaskType.INFRASTRUCTURE,  # Specific setup/config tasks
            TaskType.IMPLEMENTATION,  # Most general - catches remaining dev work
        ]

        for task_type in priority_order:
            keywords = cls.TASK_KEYWORDS.get(task_type, [])
            if any(keyword in text_to_check for keyword in keywords):
                return task_type

        return TaskType.OTHER

    @classmethod
    def is_type(cls, task: Task, task_type: TaskType) -> bool:
        """Check if a task is of a specific type."""
        return cls.classify(task) == task_type

    @classmethod
    def filter_by_type(cls, tasks: List[Task], task_type: TaskType) -> List[Task]:
        """Filter tasks by type."""
        return [task for task in tasks if cls.classify(task) == task_type]


class TaskBuilder:
    """Build task data structures for kanban board creation."""

    @staticmethod
    def build_task_data(task: Task) -> Dict[str, Any]:
        """
        Build a dictionary of task data for kanban board creation.

        Parameters
        ----------
        task : Task
            Task object to convert

        Returns
        -------
        Dict[str, Any]
            Dictionary with task data ready for kanban API
        """
        return {
            "name": task.name,
            "description": task.description,
            "priority": (
                task.priority.value
                if hasattr(task.priority, "value")
                else task.priority
            ),
            "labels": task.labels,
            "estimated_hours": task.estimated_hours,
            "dependencies": task.dependencies,
            # Store the original task ID for dependency mapping
            "original_id": task.id,
            # Include acceptance criteria if available
            "acceptance_criteria": getattr(task, "acceptance_criteria", []),
            # Include subtasks if available
            "subtasks": getattr(task, "subtasks", []),
            # Additional fields that might be needed
            "status": (
                task.status.value if hasattr(task.status, "value") else task.status
            ),
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "metadata": {"ai_generated": True, "source": "natural_language"},
        }

    @staticmethod
    def build_minimal_task_data(task: Task) -> Dict[str, Any]:
        """Build minimal task data (for APIs with fewer fields)."""
        return {
            "name": task.name,
            "description": task.description,
            "priority": (
                task.priority.value
                if hasattr(task.priority, "value")
                else task.priority
            ),
            "labels": task.labels,
        }


class SafetyChecker:
    """Apply safety checks to ensure logical task ordering."""

    def __init__(self) -> None:
        """Initialize SafetyChecker with enhanced task classifier."""
        from src.integrations.enhanced_task_classifier import EnhancedTaskClassifier

        self.task_classifier = EnhancedTaskClassifier()

    def apply_deployment_dependencies(self, tasks: List[Task]) -> List[Task]:
        """
        Ensure deployment tasks depend on implementation and testing tasks.

        This prevents premature deployment by establishing proper dependencies.

        Parameters
        ----------
        tasks : List[Task]
            List of tasks to check

        Returns
        -------
        List[Task]
            List of tasks with updated dependencies
        """
        deployment_tasks = self.task_classifier.filter_by_type(
            tasks, TaskType.DEPLOYMENT
        )
        implementation_tasks = self.task_classifier.filter_by_type(
            tasks, TaskType.IMPLEMENTATION
        )
        testing_tasks = self.task_classifier.filter_by_type(tasks, TaskType.TESTING)

        for deploy_task in deployment_tasks:
            # Ensure deployment depends on ALL implementation tasks
            for impl_task in implementation_tasks:
                if impl_task.id not in deploy_task.dependencies:
                    deploy_task.dependencies.append(impl_task.id)
                    logger.debug(
                        f"Added dependency: {deploy_task.name} depends on {impl_task.name}"
                    )

            # Ensure deployment depends on ALL testing tasks
            for test_task in testing_tasks:
                if test_task.id not in deploy_task.dependencies:
                    deploy_task.dependencies.append(test_task.id)
                    logger.debug(
                        f"Added dependency: {deploy_task.name} depends on {test_task.name}"
                    )

        return tasks

    def apply_testing_dependencies(self, tasks: List[Task]) -> List[Task]:
        """
        Ensure testing tasks depend on implementation tasks.

        Parameters
        ----------
        tasks : List[Task]
            List of tasks to check

        Returns
        -------
        List[Task]
            List of tasks with updated dependencies
        """
        testing_tasks = self.task_classifier.filter_by_type(tasks, TaskType.TESTING)
        implementation_tasks = self.task_classifier.filter_by_type(
            tasks, TaskType.IMPLEMENTATION
        )

        for test_task in testing_tasks:
            # Find related implementation tasks (by matching labels or keywords)
            related_impl_tasks = SafetyChecker._find_related_tasks(
                test_task, implementation_tasks
            )

            if not related_impl_tasks:
                logger.warning(
                    f"No related implementation tasks found for test task '{test_task.name}' "
                    f"with labels: {test_task.labels}"
                )
            else:
                logger.info(
                    f"Found {len(related_impl_tasks)} related implementation tasks for '{test_task.name}'"
                )

            for impl_task in related_impl_tasks:
                if impl_task.id not in test_task.dependencies:
                    test_task.dependencies.append(impl_task.id)
                    logger.info(
                        f"Added dependency: {test_task.name} depends on {impl_task.name}"
                    )

        return tasks

    def apply_implementation_dependencies(self, tasks: List[Task]) -> List[Task]:
        """
        Ensure implementation tasks depend on design tasks.

        Parameters
        ----------
        tasks : List[Task]
            List of tasks to check

        Returns
        -------
        List[Task]
            List of tasks with updated dependencies
        """
        design_tasks = self.task_classifier.filter_by_type(tasks, TaskType.DESIGN)
        implementation_tasks = self.task_classifier.filter_by_type(
            tasks, TaskType.IMPLEMENTATION
        )

        for impl_task in implementation_tasks:
            # Find related design tasks (by matching labels or keywords)
            related_design_tasks = SafetyChecker._find_related_tasks(
                impl_task, design_tasks
            )

            if not related_design_tasks:
                logger.warning(
                    f"No related design tasks found for implementation task '{impl_task.name}' "
                    f"with labels: {impl_task.labels}"
                )
            else:
                logger.info(
                    f"Found {len(related_design_tasks)} related design tasks for '{impl_task.name}'"
                )

            for design_task in related_design_tasks:
                if design_task.id not in impl_task.dependencies:
                    impl_task.dependencies.append(design_task.id)
                    logger.info(
                        f"Added dependency: {impl_task.name} depends on {design_task.name}"
                    )

        return tasks

    @staticmethod
    def _find_related_tasks(task: Task, candidate_tasks: List[Task]) -> List[Task]:
        """Find tasks that are related based on labels and keywords."""
        related = []

        # Extract feature labels from task
        task_feature_labels = {
            label for label in task.labels if label.startswith("feature:")
        }

        for candidate in candidate_tasks:
            # First priority: Check feature label overlap (tasks in same feature)
            candidate_feature_labels = {
                label for label in candidate.labels if label.startswith("feature:")
            }
            if task_feature_labels & candidate_feature_labels:
                related.append(candidate)
                continue

            # Second priority: Check component label overlap
            task_component_labels = {
                label for label in task.labels if label.startswith("component:")
            }
            candidate_component_labels = {
                label for label in candidate.labels if label.startswith("component:")
            }
            if task_component_labels & candidate_component_labels:
                related.append(candidate)
                continue

            # Third priority: Check any label overlap (excluding type labels)
            task_other_labels = set(task.labels) - {
                label for label in task.labels if label.startswith("type:")
            }
            candidate_other_labels = set(candidate.labels) - {
                label for label in candidate.labels if label.startswith("type:")
            }
            if task_other_labels & candidate_other_labels:
                related.append(candidate)
                continue

            # Fourth priority: Check keyword similarity in names
            task_words = set(task.name.lower().split())
            candidate_words = set(candidate.name.lower().split())
            # Remove common words
            common_words = {
                "the",
                "a",
                "an",
                "and",
                "or",
                "for",
                "to",
                "in",
                "of",
                "design",
                "implement",
                "test",
                "create",
                "build",
                "develop",
            }
            task_words -= common_words
            candidate_words -= common_words

            # Need at least 2 matching words for keyword-based relation
            if len(task_words & candidate_words) >= 2:
                related.append(candidate)

        return related

    @staticmethod
    def validate_dependencies(tasks: List[Task]) -> List[str]:
        """
        Validate that all dependencies reference existing tasks.

        Parameters
        ----------
        tasks : List[Task]
            List of tasks to validate

        Returns
        -------
        List[str]
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
