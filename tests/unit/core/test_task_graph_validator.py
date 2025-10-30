"""
Unit tests for TaskGraphValidator.

Tests the pre-commit validation that PREVENTS invalid task graphs.
"""

from datetime import datetime

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.core.task_graph_validator import TaskGraphValidator


class TestTaskGraphValidator:
    """Test suite for TaskGraphValidator"""

    @pytest.fixture
    def valid_tasks(self):
        """Create valid task graph."""
        task1 = Task(
            id="task_1",
            name="Implementation Task",
            description="Core implementation",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature", "component:backend"],
            dependencies=[],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        task2 = Task(
            id="task_2",
            name="Test Task",
            description="Tests for implementation",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            labels=["type:testing"],
            dependencies=["task_1"],
            estimated_hours=2.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        task3 = Task(
            id="task_3",
            name="Create README documentation",
            description="Documentation task",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["documentation", "final", "verification"],
            dependencies=["task_1", "task_2"],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        return [task1, task2, task3]

    def test_validate_valid_graph(self, valid_tasks):
        """Test that valid graph passes validation."""
        # Should not raise
        TaskGraphValidator.validate_before_commit(valid_tasks)

    def test_validate_empty_tasks(self):
        """Test validation with empty task list."""
        # Should not raise
        TaskGraphValidator.validate_before_commit([])

    def test_detect_orphaned_dependencies(self):
        """Test detection of dependencies referencing non-existent tasks."""
        task1 = Task(
            id="task_1",
            name="Task with orphaned dep",
            description="Bad task",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["nonexistent_task"],  # Orphaned dependency
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        with pytest.raises(ValueError) as exc_info:
            TaskGraphValidator.validate_before_commit([task1])

        error_msg = str(exc_info.value)
        assert "orphaned dependencies" in error_msg.lower()
        assert "nonexistent_task" in error_msg

    def test_detect_circular_dependencies_simple(self):
        """Test detection of simple circular dependency (A → B → A)."""
        task_a = Task(
            id="task_a",
            name="Task A",
            description="Task A",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["task_b"],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        task_b = Task(
            id="task_b",
            name="Task B",
            description="Task B",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["task_a"],  # Circular!
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        with pytest.raises(ValueError) as exc_info:
            TaskGraphValidator.validate_before_commit([task_a, task_b])

        error_msg = str(exc_info.value)
        assert "circular dependency" in error_msg.lower()
        assert "task_a" in error_msg.lower()
        assert "task_b" in error_msg.lower()

    def test_detect_circular_dependencies_complex(self):
        """Test detection of complex circular dependency (A → B → C → A)."""
        task_a = Task(
            id="task_a",
            name="Task A",
            description="Task A",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["task_b"],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        task_b = Task(
            id="task_b",
            name="Task B",
            description="Task B",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["task_c"],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        task_c = Task(
            id="task_c",
            name="Task C",
            description="Task C",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["task_a"],  # Completes the cycle
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        with pytest.raises(ValueError) as exc_info:
            TaskGraphValidator.validate_before_commit([task_a, task_b, task_c])

        error_msg = str(exc_info.value)
        assert "circular dependency" in error_msg.lower()
        # Should show the cycle path
        assert "task_a" in error_msg.lower()
        assert "task_b" in error_msg.lower()
        assert "task_c" in error_msg.lower()

    def test_detect_final_task_no_dependencies(self):
        """Test detection of final task with no dependencies."""
        impl_task = Task(
            id="impl_task",
            name="Implementation Task",
            description="Core work",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature", "component:backend"],
            dependencies=[],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        final_task = Task(
            id="final_task",
            name="Create README documentation",
            description="Final documentation",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["final", "verification"],
            dependencies=[],  # BUG: Should depend on impl_task
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        with pytest.raises(ValueError) as exc_info:
            TaskGraphValidator.validate_before_commit([impl_task, final_task])

        error_msg = str(exc_info.value)
        assert "final tasks have no dependencies" in error_msg.lower()
        assert "implementation tasks exist" in error_msg.lower()
        assert "README" in error_msg

    def test_final_task_ok_with_dependencies(self):
        """Test that final task WITH dependencies passes validation."""
        impl_task = Task(
            id="impl_task",
            name="Implementation Task",
            description="Core work",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature", "component:backend"],
            dependencies=[],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        final_task = Task(
            id="final_task",
            name="Create README documentation",
            description="Final documentation",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["final", "verification"],
            dependencies=["impl_task"],  # Correct!
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        # Should not raise
        TaskGraphValidator.validate_before_commit([impl_task, final_task])

    def test_final_task_ok_without_implementation_tasks(self):
        """Test that final task with no deps is OK if no implementation tasks."""
        final_task = Task(
            id="final_task",
            name="Create README documentation",
            description="Final documentation",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["final", "verification"],
            dependencies=[],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        # Should not raise - no implementation tasks exist
        TaskGraphValidator.validate_before_commit([final_task])

    def test_validate_and_log_valid_graph(self, valid_tasks):
        """Test non-raising validation method with valid graph."""
        is_valid, error_msg = TaskGraphValidator.validate_and_log(valid_tasks)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_and_log_invalid_graph(self):
        """Test non-raising validation method with invalid graph."""
        task_a = Task(
            id="task_a",
            name="Task A",
            description="Task A",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["task_b"],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        task_b = Task(
            id="task_b",
            name="Task B",
            description="Task B",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["task_a"],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        is_valid, error_msg = TaskGraphValidator.validate_and_log([task_a, task_b])

        assert is_valid is False
        assert len(error_msg) > 0
        assert "circular dependency" in error_msg.lower()

    def test_self_referencing_task(self):
        """Test detection of task depending on itself."""
        task = Task(
            id="task_1",
            name="Self-referencing task",
            description="Bug",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["task_1"],  # Self-reference
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        with pytest.raises(ValueError) as exc_info:
            TaskGraphValidator.validate_before_commit([task])

        error_msg = str(exc_info.value)
        assert "circular dependency" in error_msg.lower()

    def test_multiple_final_tasks_no_dependencies(self):
        """Test detection of multiple final tasks with no dependencies."""
        impl_task = Task(
            id="impl_task",
            name="Implementation Task",
            description="Core work",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=[],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        final_task_1 = Task(
            id="final_1",
            name="Documentation Task 1",
            description="Docs",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["final"],
            dependencies=[],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        final_task_2 = Task(
            id="final_2",
            name="Verification Task",
            description="Verify",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["verification"],
            dependencies=[],
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        with pytest.raises(ValueError) as exc_info:
            TaskGraphValidator.validate_before_commit(
                [impl_task, final_task_1, final_task_2]
            )

        error_msg = str(exc_info.value)
        assert "2 final tasks have no dependencies" in error_msg.lower()
