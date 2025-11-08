"""
Unit tests for TaskGraphValidator auto-fix functionality.

Tests that the validator can automatically fix common task graph issues
without raising exceptions.
"""

from datetime import datetime

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.core.task_graph_validator import TaskGraphValidator


class TestTaskGraphAutoFix:
    """Test suite for auto-fix functionality"""

    def test_fix_orphaned_dependencies_removes_invalid_refs(self):
        """Test that orphaned dependencies are automatically removed."""
        task1 = Task(
            id="task_1",
            name="Valid Task",
            description="Task",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["task_999", "task_888"],  # Both orphaned
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        fixed_tasks, warnings = TaskGraphValidator.validate_and_fix([task1])

        # Dependencies should be removed
        assert len(fixed_tasks[0].dependencies) == 0
        # Warning should be present
        assert len(warnings) == 1
        assert "Removed 2 invalid dependencies" in warnings[0]
        assert "Valid Task" in warnings[0]

    def test_fix_orphaned_dependencies_keeps_valid_ones(self):
        """Test that valid dependencies are preserved."""
        task1 = Task(
            id="task_1",
            name="Task 1",
            description="Task",
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

        task2 = Task(
            id="task_2",
            name="Task 2",
            description="Task",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["task_1", "task_999"],  # One valid, one orphaned
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        fixed_tasks, warnings = TaskGraphValidator.validate_and_fix([task1, task2])

        # Should keep task_1, remove task_999
        fixed_task2 = [t for t in fixed_tasks if t.id == "task_2"][0]
        assert fixed_task2.dependencies == ["task_1"]
        assert len(warnings) == 1
        assert "Removed 1 invalid dependency" in warnings[0]

    def test_fix_circular_dependencies_breaks_cycle(self):
        """Test that circular dependencies are broken."""
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
            dependencies=["task_a"],  # Creates cycle
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        fixed_tasks, warnings = TaskGraphValidator.validate_and_fix([task_a, task_b])

        # Cycle should be broken
        assert len(warnings) == 1
        assert "Broke circular dependency" in warnings[0]

        # Verify no cycle exists after fix
        is_valid, error = TaskGraphValidator.validate_and_log(fixed_tasks)
        assert is_valid

    def test_fix_complex_circular_dependencies(self):
        """Test breaking complex circular dependency (A→B→C→A)."""
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
            dependencies=["task_a"],  # Completes cycle
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        fixed_tasks, warnings = TaskGraphValidator.validate_and_fix(
            [task_a, task_b, task_c]
        )

        # Cycle should be broken
        assert len(warnings) == 1
        assert "Broke circular dependency" in warnings[0]

        # Verify no cycle after fix
        is_valid, error = TaskGraphValidator.validate_and_log(fixed_tasks)
        assert is_valid

    def test_fix_final_task_no_dependencies_adds_impl_deps(self):
        """Test that final tasks get implementation dependencies added."""
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
            name="PROJECT_SUCCESS",
            description="Final documentation",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["final", "verification"],
            dependencies=[],  # Missing dependencies!
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        fixed_tasks, warnings = TaskGraphValidator.validate_and_fix(
            [impl_task, final_task]
        )

        # Final task should now depend on impl task
        fixed_final = [t for t in fixed_tasks if t.id == "final_task"][0]
        assert "impl_task" in fixed_final.dependencies
        assert len(warnings) == 1
        assert "Added 1 implementation task dependency" in warnings[0]
        assert "PROJECT_SUCCESS" in warnings[0]

    def test_fix_multiple_issues_simultaneously(self):
        """Test fixing orphaned deps + final task deps together."""
        impl_task = Task(
            id="impl_1",
            name="Implementation",
            description="Work",
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

        task_with_orphan = Task(
            id="task_2",
            name="Task with orphan",
            description="Task",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["impl_1", "orphan_999"],  # One valid, one orphaned
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        final_task = Task(
            id="final",
            name="PROJECT_SUCCESS",
            description="Final",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["final"],
            dependencies=[],  # Missing deps
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        fixed_tasks, warnings = TaskGraphValidator.validate_and_fix(
            [impl_task, task_with_orphan, final_task]
        )

        # Should have 2 warnings: orphan removal + final task deps
        assert len(warnings) == 2
        assert any("orphan" in w.lower() or "invalid" in w.lower() for w in warnings)
        assert any("final" in w.lower() or "PROJECT_SUCCESS" in w for w in warnings)

        # Verify fixed graph is valid
        is_valid, error = TaskGraphValidator.validate_and_log(fixed_tasks)
        assert is_valid

    def test_no_warnings_for_valid_graph(self):
        """Test that valid graphs produce no warnings."""
        task1 = Task(
            id="task_1",
            name="Implementation",
            description="Work",
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

        task2 = Task(
            id="task_2",
            name="Tests",
            description="Tests",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
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
            name="PROJECT_SUCCESS",
            description="Final",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["final"],
            dependencies=["task_1", "task_2"],  # Proper dependencies
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        fixed_tasks, warnings = TaskGraphValidator.validate_and_fix(
            [task1, task2, task3]
        )

        # No warnings for valid graph
        assert len(warnings) == 0

    def test_empty_task_list_returns_empty(self):
        """Test that empty task list is handled gracefully."""
        fixed_tasks, warnings = TaskGraphValidator.validate_and_fix([])

        assert len(fixed_tasks) == 0
        assert len(warnings) == 0

    def test_self_referencing_task_fixed(self):
        """Test that self-referencing dependency is removed."""
        task = Task(
            id="task_1",
            name="Self-referencing task",
            description="Bug",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["type:feature"],
            dependencies=["task_1"],  # Self-reference (creates cycle)
            estimated_hours=4.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        fixed_tasks, warnings = TaskGraphValidator.validate_and_fix([task])

        # Cycle should be broken
        assert len(warnings) == 1
        assert "Broke circular dependency" in warnings[0]

        # Verify valid after fix
        is_valid, error = TaskGraphValidator.validate_and_log(fixed_tasks)
        assert is_valid
