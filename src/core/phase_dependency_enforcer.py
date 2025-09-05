"""
Phase Dependency Enforcer.

Enforces strict development lifecycle phase dependencies within features,
ensuring tasks follow the correct order:
Design → Implementation → Testing → Documentation
"""

import logging
from collections import defaultdict
from dataclasses import dataclass

# Define enums locally to avoid import issues
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.core.models import Task
from src.integrations.enhanced_task_classifier import EnhancedTaskClassifier
from src.integrations.nlp_task_utils import TaskType


class TaskPhase(Enum):
    """Development lifecycle phases in execution order."""

    DESIGN = 1
    INFRASTRUCTURE = 2
    IMPLEMENTATION = 3
    TESTING = 4
    DOCUMENTATION = 5
    DEPLOYMENT = 6

    @classmethod
    def get_dependencies(cls, phase: "TaskPhase") -> List["TaskPhase"]:
        """Get all phases that must complete before this phase."""
        return [p for p in cls if p.value < phase.value]


class DependencyType(Enum):
    """Types of task dependencies."""

    PHASE = "phase"
    FEATURE = "feature"
    TECHNICAL = "technical"
    DATA = "data"
    GLOBAL = "global"
    MANUAL = "manual"


# For now, use regular Task model instead of EnhancedTask to avoid circular imports
EnhancedTask = Task

logger = logging.getLogger(__name__)


@dataclass
class FeatureGroup:
    """Represents a group of tasks belonging to the same feature."""

    feature_name: str
    tasks: List[Task]
    phase_tasks: Dict[TaskPhase, List[Task]]

    def get_tasks_by_phase(self, phase: TaskPhase) -> List[Task]:
        """Get all tasks in a specific phase."""
        return self.phase_tasks.get(phase, [])

    def has_phase(self, phase: TaskPhase) -> bool:
        """Check if feature has tasks in a specific phase."""
        return phase in self.phase_tasks and len(self.phase_tasks[phase]) > 0


class PhaseDependencyEnforcer:
    """
    Enforces development lifecycle phase dependencies.

    Ensures tasks within the same feature follow proper phase ordering:
    Design → Infrastructure → Implementation → Testing → Documentation → Deployment
    """

    # Define phase ordering
    PHASE_ORDER = [
        TaskPhase.DESIGN,
        TaskPhase.INFRASTRUCTURE,
        TaskPhase.IMPLEMENTATION,
        TaskPhase.TESTING,
        TaskPhase.DOCUMENTATION,
        TaskPhase.DEPLOYMENT,
    ]

    # Map TaskType to TaskPhase
    TYPE_TO_PHASE_MAP = {
        TaskType.DESIGN: TaskPhase.DESIGN,
        TaskType.INFRASTRUCTURE: TaskPhase.INFRASTRUCTURE,
        TaskType.IMPLEMENTATION: TaskPhase.IMPLEMENTATION,
        TaskType.TESTING: TaskPhase.TESTING,
        TaskType.DOCUMENTATION: TaskPhase.DOCUMENTATION,
        TaskType.DEPLOYMENT: TaskPhase.DEPLOYMENT,
        TaskType.OTHER: TaskPhase.IMPLEMENTATION,  # Default to implementation
    }

    def __init__(self) -> None:
        """Initialize the phase dependency enforcer."""
        self.task_classifier = EnhancedTaskClassifier()

    def enforce_phase_dependencies(self, tasks: List[Task]) -> List[Task]:
        """
        Apply phase-based dependencies to tasks.

        Args:
            tasks: List of tasks to process

        Returns:
            List of tasks with phase dependencies added
        """
        logger.info(f"Enforcing phase dependencies for {len(tasks)} tasks")

        # Group tasks by feature
        feature_groups = self._group_tasks_by_feature(tasks)
        logger.info(f"Identified {len(feature_groups)} feature groups")

        # Apply phase dependencies within each feature
        for feature_name, feature_group in feature_groups.items():
            logger.debug(
                f"Processing feature: {feature_name} with {len(feature_group.tasks)} tasks"
            )
            self._apply_phase_dependencies_to_feature(feature_group)

        # Log summary
        total_dependencies_added = sum(
            len(task.dependencies)
            for task in tasks
            if hasattr(task, "_phase_dependencies_added")
            and task._phase_dependencies_added
        )
        logger.info(
            f"Phase dependency enforcement complete. Added {total_dependencies_added} dependencies"
        )

        return tasks

    def _group_tasks_by_feature(self, tasks: List[Task]) -> Dict[str, FeatureGroup]:
        """
        Group tasks by their feature/component.

        Strategy:
        1. Use explicit feature labels if present
        2. Extract feature from task name patterns
        3. Group by shared keywords/context
        """
        feature_groups = defaultdict(list)

        for task in tasks:
            feature = self._identify_task_feature(task)
            feature_groups[feature].append(task)

        # Convert to FeatureGroup objects with phase classification
        result = {}
        for feature_name, feature_tasks in feature_groups.items():
            phase_tasks = self._classify_tasks_by_phase(feature_tasks)
            result[feature_name] = FeatureGroup(
                feature_name=feature_name, tasks=feature_tasks, phase_tasks=phase_tasks
            )

        return result

    def _identify_task_feature(self, task: Task) -> str:
        """
        Identify which feature/component a task belongs to.

        Priority:
        1. Explicit 'feature' label
        2. Component-specific labels (e.g., 'authentication', 'payment')
        3. Extract from task name
        4. Default to 'general'
        """
        # Check for explicit feature label
        if task.labels:
            for label in task.labels:
                if label.startswith("feature:"):
                    return label.replace("feature:", "")
                # Also check for feature-X pattern
                if label.startswith("feature-"):
                    return label

            # Check for component labels
            component_labels = [
                "authentication",
                "auth",
                "user-management",
                "user-mgmt",
                "payment",
                "dashboard",
                "api",
                "frontend",
                "backend",
                "database",
                "monitoring",
                "logging",
                "security",
                "notification",
                "infra",
                "infrastructure",
            ]
            for label in task.labels:
                label_lower = label.lower()
                # Check direct match
                if label_lower in component_labels:
                    return label_lower
                # Check with component: prefix
                if label_lower.startswith("component:"):
                    component = label_lower.replace("component:", "")
                    if component in component_labels:
                        return component

        # Extract from task name
        name_lower = task.name.lower()

        # Common feature patterns
        feature_patterns = [
            ("auth", ["login", "logout", "authentication", "password", "token"]),
            ("user", ["user", "profile", "account", "registration"]),
            ("payment", ["payment", "billing", "subscription", "checkout"]),
            ("dashboard", ["dashboard", "analytics", "metrics", "report"]),
            ("api", ["api", "endpoint", "rest", "graphql"]),
            ("ui", ["ui", "interface", "frontend", "component", "page"]),
        ]

        for feature, keywords in feature_patterns:
            if any(keyword in name_lower for keyword in keywords):
                return feature

        # Extract feature from patterns like "Design X system" or "Implement Y feature"
        import re

        patterns = [
            r"(?:design|implement|test|document)\s+(\w+)\s+(?:system|feature|service|component)",
            r"(?:create|build|develop)\s+(\w+)\s+(?:api|interface|module)",
        ]

        for pattern in patterns:
            match = re.search(pattern, name_lower)
            if match:
                return match.group(1)

        # Default to general
        return "general"

    def _classify_tasks_by_phase(
        self, tasks: List[Task]
    ) -> Dict[TaskPhase, List[Task]]:
        """Classify tasks into their development phases."""
        phase_tasks = defaultdict(list)

        for task in tasks:
            # Get task type from classifier
            task_type = self.task_classifier.classify(task)

            # Map to phase
            phase = self.TYPE_TO_PHASE_MAP.get(task_type, TaskPhase.IMPLEMENTATION)

            # Store phase info on task for later use if it supports it
            if hasattr(task, "phase"):
                task.phase = phase
                # Note: phase_confidence not available in base Task model

            phase_tasks[phase].append(task)

        return dict(phase_tasks)

    def _apply_phase_dependencies_to_feature(self, feature_group: FeatureGroup) -> None:
        """
        Apply phase ordering dependencies within a feature.

        Rules:
        - Tasks in phase N depend on ALL tasks in phases < N
        - Within the same phase, no automatic dependencies
        - Preserve existing manual dependencies
        """
        phase_tasks = feature_group.phase_tasks
        violations_corrected = 0

        # Process phases in order
        for i, current_phase in enumerate(self.PHASE_ORDER):
            if not feature_group.has_phase(current_phase):
                continue

            current_phase_tasks = phase_tasks[current_phase]

            # Find all tasks from previous phases
            previous_phase_tasks = []
            for prev_phase in self.PHASE_ORDER[:i]:
                if feature_group.has_phase(prev_phase):
                    previous_phase_tasks.extend(phase_tasks[prev_phase])

            # Add dependencies from previous phases
            if previous_phase_tasks:
                for task in current_phase_tasks:
                    violations = self._add_phase_dependencies(
                        task, previous_phase_tasks
                    )
                    violations_corrected += violations

        if violations_corrected > 0:
            logger.warning(
                f"Corrected {violations_corrected} phase ordering violations in feature '{feature_group.feature_name}'"
            )

    def _add_phase_dependencies(
        self, dependent_task: Task, dependency_tasks: List[Task]
    ) -> int:
        """
        Add phase-based dependencies to a task.

        Args:
            dependent_task: Task that will depend on others
            dependency_tasks: Tasks that must complete first

        Returns:
            Number of violations corrected
        """
        if not dependency_tasks:
            return 0

        # Track additions for logging
        added_count = 0
        violations_found = 0

        # Ensure dependencies list exists
        if (
            not hasattr(dependent_task, "dependencies")
            or dependent_task.dependencies is None
        ):
            dependent_task.dependencies = []

        for dep_task in dependency_tasks:
            if (
                dep_task.id not in dependent_task.dependencies
                and dep_task.id != dependent_task.id
            ):
                dependent_task.dependencies.append(dep_task.id)
                added_count += 1
                violations_found += 1

                # Add metadata if task supports it
                if hasattr(dependent_task, "add_dependency"):
                    dependent_task.add_dependency(dep_task.id, DependencyType.PHASE)

                logger.debug(
                    f"Added phase dependency: {dependent_task.name} "
                    f"({self._get_task_phase_name(dependent_task)}) depends on "
                    f"{dep_task.name} ({self._get_task_phase_name(dep_task)})"
                )

        # Note: _phase_dependencies_added not available in base Task model
        # Dependencies are tracked in task.dependencies list instead

        if added_count > 0:
            logger.debug(
                f"Added {added_count} phase dependencies to task: {dependent_task.name}"
            )

        return violations_found

    def _get_task_phase_name(self, task: Task) -> str:
        """Get the phase name for a task."""
        if hasattr(task, "phase") and task.phase:
            if hasattr(task.phase, "name"):
                return str(task.phase.name)
            else:
                return str(task.phase)

        # Fallback to type classification
        task_type = self.task_classifier.classify(task)
        phase = self.TYPE_TO_PHASE_MAP.get(task_type, TaskPhase.IMPLEMENTATION)
        return str(phase.name)

    def validate_phase_ordering(self, tasks: List[Task]) -> Tuple[bool, List[str]]:
        """
        Validate that tasks follow proper phase ordering.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        task_map = {task.id: task for task in tasks}

        for task in tasks:
            if not task.dependencies:
                continue

            task_phase = self._get_task_phase_enum(task)
            if not task_phase:
                continue

            for dep_id in task.dependencies:
                dep_task = task_map.get(dep_id)
                if not dep_task:
                    continue

                dep_phase = self._get_task_phase_enum(dep_task)
                if not dep_phase:
                    continue

                # Check if dependency violates phase ordering
                if dep_phase.value > task_phase.value:
                    error = (
                        f"Phase order violation: {task.name} ({task_phase.name}) "
                        f"depends on {dep_task.name} ({dep_phase.name})"
                    )
                    errors.append(error)

        return len(errors) == 0, errors

    def _get_task_phase_enum(self, task: Task) -> Optional[TaskPhase]:
        """Get the TaskPhase enum for a task."""
        if hasattr(task, "phase") and task.phase:
            from typing import cast

            # Cast to avoid mypy error - we check isinstance below
            phase = cast(TaskPhase, task.phase)
            if isinstance(phase, TaskPhase):
                return phase

        # Fallback to type classification
        task_type = self.task_classifier.classify(task)
        return self.TYPE_TO_PHASE_MAP.get(task_type, TaskPhase.IMPLEMENTATION)

    def _get_task_phase(self, task_type: TaskType) -> TaskPhase:
        """Convert TaskType to TaskPhase."""
        return self.TYPE_TO_PHASE_MAP.get(task_type, TaskPhase.IMPLEMENTATION)

    def _should_depend_on_phase(
        self, task_phase: TaskPhase, other_phase: TaskPhase
    ) -> bool:
        """Check if task_phase should depend on other_phase based on phase ordering."""
        return task_phase.value > other_phase.value

    def get_phase_statistics(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Get statistics about phase distribution and dependencies.

        Returns:
            Dictionary with phase statistics
        """
        stats: Dict[str, Any] = {
            "total_tasks": len(tasks),
            "phase_distribution": {},
            "dependency_count": 0,
            "phase_dependency_count": 0,
            "features_identified": set(),
        }

        # Count tasks by phase
        phase_counts: defaultdict[str, int] = defaultdict(int)
        for task in tasks:
            phase = self._get_task_phase_name(task)
            phase_counts[phase] += 1

            # Count dependencies
            if task.dependencies:
                stats["dependency_count"] += len(task.dependencies)

                # Count phase dependencies if enhanced task
                if hasattr(task, "get_dependencies_by_type"):
                    try:
                        phase_deps = task.get_dependencies_by_type(DependencyType.PHASE)
                        stats["phase_dependency_count"] += len(phase_deps)
                    except Exception as e:
                        # Skip if method not available or fails, but log the issue
                        logger.debug(
                            "Failed to get phase dependencies for task %s: %s",
                            getattr(task, "name", "unknown"),
                            str(e),
                        )

        stats["phase_distribution"] = dict(phase_counts)

        # Get feature count
        feature_groups = self._group_tasks_by_feature(tasks)
        stats["features_identified"] = list(feature_groups.keys())
        stats["feature_count"] = len(feature_groups)

        return stats
