"""
Unit tests for soft vs hard dependency support in subtask assignment.

Tests verify that:
1. Soft dependencies don't block task assignment
2. Hard dependencies do block task assignment
3. Empty dependency_types defaults to hard
4. Mixed soft/hard dependencies work correctly
"""

from datetime import datetime, timezone

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.subtask_assignment import (
    _are_dependencies_satisfied,
)


class TestSoftDependencySupport:
    """Test suite for soft vs hard dependency behavior."""

    def test_soft_dependencies_do_not_block_assignment(self):
        """Test that tasks with soft dependencies can be assigned immediately."""
        # Arrange
        dependency_task = Task(
            id="dep1",
            name="Design API Specs",
            description="Create API design",
            status=TaskStatus.TODO,  # NOT done
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=2.0,
        )

        main_task = Task(
            id="main",
            name="Implement API Endpoint",
            description="Build the endpoint",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
            dependencies=["dep1"],
            dependency_types=["soft"],  # Soft dependency
        )

        # Act
        result = _are_dependencies_satisfied(main_task, [dependency_task])

        # Assert - should be available despite dep being TODO
        assert result is True, "Soft dependency should not block assignment"

    def test_hard_dependencies_block_assignment(self):
        """Test that tasks with hard dependencies must wait for completion."""
        # Arrange
        dependency_task = Task(
            id="dep1",
            name="Setup Database",
            description="Initialize DB",
            status=TaskStatus.TODO,  # NOT done
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=1.0,
        )

        main_task = Task(
            id="main",
            name="Run Migrations",
            description="Apply DB migrations",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.5,
            dependencies=["dep1"],
            dependency_types=["hard"],  # Hard dependency
        )

        # Act
        result = _are_dependencies_satisfied(main_task, [dependency_task])

        # Assert - should be blocked
        assert result is False, "Hard dependency should block assignment"

    def test_empty_dependency_types_defaults_to_hard(self):
        """Test migration behavior: empty dependency_types means all hard."""
        # Arrange
        dependency_task = Task(
            id="dep1",
            name="Prepare Environment",
            description="Setup",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=1.0,
        )

        main_task = Task(
            id="main",
            name="Deploy Application",
            description="Deploy to prod",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=2.0,
            dependencies=["dep1"],
            dependency_types=[],  # Empty = default to hard
        )

        # Act
        result = _are_dependencies_satisfied(main_task, [dependency_task])

        # Assert - should be blocked (defaults to hard)
        assert result is False, "Empty dependency_types should default to hard"

    def test_mixed_soft_and_hard_dependencies(self):
        """Test tasks with both soft and hard dependencies."""
        # Arrange
        soft_dep = Task(
            id="soft1",
            name="Design Specs",
            description="Create design",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=2.0,
        )

        hard_dep = Task(
            id="hard1",
            name="Database Schema",
            description="Create schema",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=1.0,
        )

        done_dep = Task(
            id="done1",
            name="Environment Setup",
            description="Setup complete",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            assigned_to="agent1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.5,
        )

        main_task = Task(
            id="main",
            name="Implement Feature",
            description="Build feature",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
            dependencies=["soft1", "hard1", "done1"],
            dependency_types=["soft", "hard", "soft"],
        )

        # Act
        result = _are_dependencies_satisfied(main_task, [soft_dep, hard_dep, done_dep])

        # Assert - blocked because hard1 is TODO
        assert result is False, "Hard dependency hard1 should block"

    def test_all_soft_dependencies_with_todo_status(self):
        """Test that multiple soft dependencies don't block."""
        # Arrange
        dep1 = Task(
            id="dep1",
            name="Design Frontend",
            description="Frontend design",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=3.0,
        )

        dep2 = Task(
            id="dep2",
            name="Design Backend",
            description="Backend design",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=2.0,
        )

        main_task = Task(
            id="main",
            name="Implement Integration",
            description="Connect frontend and backend",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
            dependencies=["dep1", "dep2"],
            dependency_types=["soft", "soft"],
        )

        # Act
        result = _are_dependencies_satisfied(main_task, [dep1, dep2])

        # Assert - should be assignable (all soft)
        assert result is True, "All soft dependencies should allow assignment"

    def test_task_with_no_dependencies(self):
        """Test that tasks without dependencies are always assignable."""
        # Arrange
        task = Task(
            id="task1",
            name="Independent Task",
            description="No dependencies",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=2.0,
            dependencies=[],
            dependency_types=[],
        )

        # Act
        result = _are_dependencies_satisfied(task, [])

        # Assert
        assert result is True, "Task with no dependencies should be assignable"

    def test_dependency_types_length_mismatch_defaults_to_hard(self):
        """Test that missing dependency_types entries default to hard."""
        # Arrange
        dep1 = Task(
            id="dep1",
            name="Task 1",
            description="First dependency",
            status=TaskStatus.DONE,
            priority=Priority.MEDIUM,
            assigned_to="agent1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=1.0,
        )

        dep2 = Task(
            id="dep2",
            name="Task 2",
            description="Second dependency",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=1.0,
        )

        main_task = Task(
            id="main",
            name="Main Task",
            description="Depends on two tasks",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=2.0,
            dependencies=["dep1", "dep2"],
            dependency_types=["soft"],  # Only one type for two deps!
        )

        # Act
        result = _are_dependencies_satisfied(main_task, [dep1, dep2])

        # Assert - dep2 defaults to hard, blocks assignment
        assert result is False, "Missing dependency_type should default to hard"
