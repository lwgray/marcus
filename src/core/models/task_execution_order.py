"""
Data Models for Task Execution Order System.

This module defines the enhanced data models required for the task execution
order fix, including task phases, validation results, and dependency metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

# Note: Task, Priority, TaskStatus are imported from src.core.models
# but we can't import them here due to circular imports
# They are used for type hints only in this file


class TaskPhase(Enum):
    """
    Development lifecycle phases in execution order.

    The integer values represent the execution order priority,
    where lower numbers must be completed before higher numbers.
    """

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

    @classmethod
    def can_depend_on(cls, dependent: "TaskPhase", dependency: "TaskPhase") -> bool:
        """Check if dependent phase can validly depend on dependency phase."""
        return dependency.value < dependent.value


class DependencyType(Enum):
    """Types of task dependencies."""

    PHASE = "phase"  # Based on development lifecycle
    FEATURE = "feature"  # Same feature/component dependency
    TECHNICAL = "technical"  # Technical requirement (e.g., API before UI)
    DATA = "data"  # Data flow dependency
    GLOBAL = "global"  # Global rules (e.g., all->documentation)
    MANUAL = "manual"  # Manually specified dependency


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    ERROR = "error"  # Must be fixed
    WARNING = "warning"  # Should be reviewed
    INFO = "info"  # Informational only


@dataclass
class TaskTypeIdentification:
    """Result of task type identification."""

    task_id: str
    task_name: str
    identified_type: str  # TaskType value
    identified_phase: TaskPhase
    confidence: float  # 0.0 to 1.0
    reasoning: str
    keyword_matches: List[str]
    pattern_matches: List[str]
    alternative_types: List[Dict[str, Any]]  # [{"type": str, "confidence": float}]
    typical_dependencies: List[TaskPhase]

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if identification meets confidence threshold."""
        return self.confidence >= threshold


@dataclass
class DependencyValidationError:
    """Represents a dependency validation error."""

    task_id: str
    task_name: str
    error_type: str  # 'missing_dependency', 'circular', 'invalid_phase', etc.
    severity: ValidationSeverity
    message: str
    details: Dict[str, Any]
    suggested_fix: Optional["DependencyFix"] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "error_type": self.error_type,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "fix": self.suggested_fix.to_dict() if self.suggested_fix else None,
        }


@dataclass
class DependencyFix:
    """Suggested fix for a dependency issue."""

    action: str  # 'add_dependency', 'remove_dependency', 'change_phase'
    target_task_id: str
    dependencies_to_add: List[str] = field(default_factory=list)
    dependencies_to_remove: List[str] = field(default_factory=list)
    new_phase: Optional[TaskPhase] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "action": self.action,
            "target_task": self.target_task_id,
            "dependencies_to_add": self.dependencies_to_add,
            "dependencies_to_remove": self.dependencies_to_remove,
            "new_phase": self.new_phase.value if self.new_phase else None,
            "reason": self.reason,
        }


@dataclass
class ValidationResult:
    """Complete validation result for a set of tasks."""

    validation_id: str
    timestamp: datetime
    is_valid: bool
    errors: List[DependencyValidationError] = field(default_factory=list)
    warnings: List[DependencyValidationError] = field(default_factory=list)
    info: List[DependencyValidationError] = field(default_factory=list)
    task_count: int = 0
    valid_task_count: int = 0
    suggested_execution_order: List[str] = field(default_factory=list)
    dependency_graph: Optional["DependencyGraph"] = None
    validation_duration_ms: int = 0

    @property
    def error_count(self) -> int:
        """Get count of errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Get count of warnings."""
        return len(self.warnings)

    def get_errors_by_type(self, error_type: str) -> List[DependencyValidationError]:
        """Get all errors of a specific type."""
        return [e for e in self.errors if e.error_type == error_type]


@dataclass
class EnhancedTask:
    """Extended task model with phase and validation information."""

    # Core Task fields (duplicated to avoid circular imports)
    id: str
    name: str
    description: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)

    # Enhanced fields
    phase: Optional[TaskPhase] = None
    phase_confidence: float = 0.0
    feature_group: Optional[str] = None
    cross_feature_dependencies: List[str] = field(default_factory=list)
    validation_status: Optional[ValidationResult] = None
    dependency_metadata: Dict[str, DependencyType] = field(default_factory=dict)
    inferred_dependencies: List[str] = field(default_factory=list)
    manual_dependencies: List[str] = field(default_factory=list)

    def get_dependencies_by_type(self, dep_type: DependencyType) -> List[str]:
        """Get all dependencies of a specific type."""
        return [
            dep_id
            for dep_id, dtype in self.dependency_metadata.items()
            if dtype == dep_type
        ]

    def add_dependency(self, task_id: str, dep_type: DependencyType) -> None:
        """Add a dependency with metadata."""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)
        self.dependency_metadata[task_id] = dep_type

        if dep_type != DependencyType.MANUAL:
            if task_id not in self.inferred_dependencies:
                self.inferred_dependencies.append(task_id)
        else:
            if task_id not in self.manual_dependencies:
                self.manual_dependencies.append(task_id)

    def remove_dependency(self, task_id: str) -> None:
        """Remove a dependency and its metadata."""
        if task_id in self.dependencies:
            self.dependencies.remove(task_id)
        if task_id in self.dependency_metadata:
            del self.dependency_metadata[task_id]
        if task_id in self.inferred_dependencies:
            self.inferred_dependencies.remove(task_id)
        if task_id in self.manual_dependencies:
            self.manual_dependencies.remove(task_id)


@dataclass
class DependencyGraph:
    """Represents the complete dependency graph for a project."""

    nodes: Dict[str, EnhancedTask]  # task_id -> task
    edges: List[Tuple[str, str, DependencyType]]  # (from_id, to_id, type)
    adjacency_list: Dict[str, List[str]] = field(default_factory=dict)
    reverse_adjacency: Dict[str, List[str]] = field(default_factory=dict)

    def get_dependencies(self, task_id: str) -> List[str]:
        """Get direct dependencies of a task."""
        return self.reverse_adjacency.get(task_id, [])

    def get_dependents(self, task_id: str) -> List[str]:
        """Get tasks that depend on this task."""
        return self.adjacency_list.get(task_id, [])

    def get_all_dependencies(self, task_id: str) -> Set[str]:
        """Get all transitive dependencies of a task."""
        visited = set()
        queue = [task_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            for dep in self.get_dependencies(current):
                if dep not in visited:
                    queue.append(dep)

        visited.remove(task_id)  # Don't include self
        return visited

    def has_circular_dependency(self) -> bool:
        """Check if the graph has any circular dependencies."""
        visited = set()
        rec_stack = set()

        def has_cycle_util(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.adjacency_list.get(node, []):
                if neighbor not in visited:
                    if has_cycle_util(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in self.nodes:
            if node not in visited:
                if has_cycle_util(node):
                    return True

        return False

    def get_execution_order(self) -> List[str]:
        """Get topologically sorted execution order."""
        if self.has_circular_dependency():
            raise ValueError(
                "Cannot determine execution order: circular dependency exists"
            )

        in_degree = {node: 0 for node in self.nodes}

        for node in self.nodes:
            for dep in self.adjacency_list.get(node, []):
                in_degree[dep] += 1

        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in self.adjacency_list.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def get_critical_path(self) -> List[str]:
        """Get the critical path through the dependency graph."""
        # Simplified critical path - longest dependency chain
        execution_order = self.get_execution_order()
        path_lengths = {node: 0 for node in self.nodes}
        predecessors = {node: None for node in self.nodes}

        for node in execution_order:
            for dep in self.get_dependencies(node):
                if path_lengths[dep] + 1 > path_lengths[node]:
                    path_lengths[node] = path_lengths[dep] + 1
                    predecessors[node] = dep

        # Find node with longest path
        end_node = max(path_lengths.items(), key=lambda x: x[1])[0]

        # Reconstruct path
        path = []
        current: Optional[str] = end_node
        while current is not None:
            path.append(current)
            current = predecessors[current]

        return list(reversed(path))


@dataclass
class TaskAssignmentEligibility:
    """Result of checking if a task can be assigned."""

    task_id: str
    agent_id: str
    eligible: bool
    reasons: List[str]
    blocking_tasks: List[str] = field(default_factory=list)
    dependencies_status: Dict[str, int] = field(default_factory=dict)
    estimated_duration_hours: Optional[float] = None
    retry_after: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "eligible": self.eligible,
            "task_id": self.task_id,
            "reasons": self.reasons,
            "blocking_tasks": self.blocking_tasks,
            "dependencies_status": self.dependencies_status,
            "estimated_duration_hours": self.estimated_duration_hours,
            "retry_after": self.retry_after.isoformat() if self.retry_after else None,
        }


@dataclass
class PhaseTransition:
    """Represents a transition between development phases."""

    from_phase: TaskPhase
    to_phase: TaskPhase
    transition_type: str  # 'normal', 'skip', 'parallel'
    is_valid: bool
    reason: str

    def __str__(self) -> str:
        """Return string representation."""
        return (
            f"{self.from_phase.name} -> {self.to_phase.name} ({self.transition_type})"
        )
