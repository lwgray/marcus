"""
Smoke tests for cross-parent dependency wiring.

Quick validation tests to ensure core functionality works before
running comprehensive test suite.
"""

from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.dependency_wiring import (
    validate_phase_order,
    would_create_cycle,
)


class TestCycleDetectionSmoke:
    """Smoke tests for cycle detection."""

    def test_simple_cycle_detection(self):
        """Test that we can detect a simple 2-node cycle."""
        # Arrange - A → B (A depends on B)
        task_a = Task(
            id="task_a",
            name="Task A",
            description="Task A",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=1.0,
            dependencies=["task_b"],  # A depends on B
        )

        task_b = Task(
            id="task_b",
            name="Task B",
            description="Task B",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=1.0,
            dependencies=[],
        )

        # Act - Try to add B → A (would create A → B → A cycle)
        creates_cycle = would_create_cycle("task_b", "task_a", [task_a, task_b])

        # Assert
        assert (
            creates_cycle is True
        ), "Should detect cycle when B → A would close loop with existing A → B"

    def test_no_cycle_for_valid_dependency(self):
        """Test that valid dependencies are allowed."""
        # Arrange - A → B (A depends on B)
        task_a = Task(
            id="task_a",
            name="Task A",
            description="Task A",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=1.0,
            dependencies=["task_b"],
        )

        task_b = Task(
            id="task_b",
            name="Task B",
            description="Task B",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=1.0,
            dependencies=[],
        )

        task_c = Task(
            id="task_c",
            name="Task C",
            description="Task C",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=1.0,
            dependencies=[],
        )

        # Act - Try to add C → B (valid, no cycle)
        creates_cycle = would_create_cycle("task_c", "task_b", [task_a, task_b, task_c])

        # Assert
        assert (
            creates_cycle is False
        ), "Should allow valid dependency that doesn't create cycle"


class TestPhaseOrderingSmoke:
    """Smoke tests for phase ordering validation."""

    def test_implement_can_depend_on_design(self):
        """Test that Implementation phase can depend on Design phase."""
        # Arrange
        design_task = Task(
            id="design_1",
            name="Design User Schema",
            description="Design the user schema",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            is_subtask=True,
            parent_task_id="parent_design",
        )

        implement_task = Task(
            id="impl_1",
            name="Implement User API",
            description="Implement the user API",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            is_subtask=True,
            parent_task_id="parent_impl",
        )

        # Act
        is_valid = validate_phase_order(implement_task, design_task)

        # Assert
        assert is_valid is True, "Implementation should be able to depend on Design"

    def test_design_cannot_depend_on_implement(self):
        """Test that Design phase cannot depend on Implementation phase."""
        # Arrange
        design_task = Task(
            id="design_1",
            name="Design User Schema",
            description="Design the user schema",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            is_subtask=True,
            parent_task_id="parent_design",
        )

        implement_task = Task(
            id="impl_1",
            name="Implement User API",
            description="Implement the user API",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
            is_subtask=True,
            parent_task_id="parent_impl",
        )

        # Act
        is_valid = validate_phase_order(design_task, implement_task)

        # Assert
        assert (
            is_valid is False
        ), "Design should NOT be able to depend on Implementation"


class TestProvidesRequiresFields:
    """Smoke tests for provides/requires fields on Task model."""

    def test_task_model_has_provides_and_requires_fields(self):
        """Test that Task model supports provides and requires fields."""
        # Arrange & Act
        task = Task(
            id="test_1",
            name="Test Task",
            description="Test",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=1.0,
            is_subtask=True,
            parent_task_id="parent_1",
            provides="User schema with field definitions",
            requires="API specification from Design phase",
        )

        # Assert
        assert task.provides == "User schema with field definitions"
        assert task.requires == "API specification from Design phase"
        assert hasattr(task, "provides"), "Task should have provides field"
        assert hasattr(task, "requires"), "Task should have requires field"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
