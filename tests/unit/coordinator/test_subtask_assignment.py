"""
Unit tests for subtask assignment logic.

Tests the bug fix for parallel subtask assignment.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.subtask_assignment import (
    convert_subtask_to_task,
    find_next_available_subtask,
)
from src.marcus_mcp.coordinator.subtask_manager import Subtask, SubtaskManager


class TestSubtaskAssignment:
    """Test suite for subtask assignment logic."""

    @pytest.fixture
    def subtask_manager(self, tmp_path):
        """Create a subtask manager with test data."""
        manager = SubtaskManager(state_file=tmp_path / "subtasks_test.json")
        return manager

    @pytest.fixture
    def parent_task_todo(self):
        """Create a parent task in TODO status."""
        return Task(
            id="parent-task-1",
            name="Parent Task 1",
            description="Parent task with subtasks",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["backend", "api"],
        )

    @pytest.fixture
    def parent_task_in_progress(self):
        """Create a parent task in IN_PROGRESS status."""
        return Task(
            id="parent-task-2",
            name="Parent Task 2",
            description="Parent task with subtasks in progress",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            assigned_to="agent-1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["backend", "api"],
        )

    @pytest.fixture
    def parent_task_done(self):
        """Create a parent task in DONE status."""
        return Task(
            id="parent-task-3",
            name="Parent Task 3",
            description="Completed parent task",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            assigned_to="agent-1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["backend", "api"],
        )

    def test_find_subtask_from_todo_parent(self, subtask_manager, parent_task_todo):
        """Test finding subtask from parent in TODO status."""
        # Add subtasks to parent
        subtasks_data = [
            {
                "name": "Subtask 1",
                "description": "First subtask",
                "estimated_hours": 2.0,
                "dependencies": [],
            },
            {
                "name": "Subtask 2",
                "description": "Second subtask",
                "estimated_hours": 2.0,
                "dependencies": [],
            },
        ]
        subtask_manager.add_subtasks(parent_task_todo.id, subtasks_data)

        # Find next available subtask
        subtask = find_next_available_subtask(
            agent_id="agent-1",
            project_tasks=[parent_task_todo],
            subtask_manager=subtask_manager,
            assigned_task_ids=set(),
        )

        assert subtask is not None
        assert subtask.name == "Subtask 1"
        assert subtask.parent_task_id == parent_task_todo.id

    def test_find_subtask_from_in_progress_parent(
        self, subtask_manager, parent_task_in_progress
    ):
        """
        Test finding subtask from parent in IN_PROGRESS status.

        This is the critical bug fix test - previously this would fail
        because IN_PROGRESS parents were skipped.
        """
        # Add subtasks to parent
        subtasks_data = [
            {
                "name": "Subtask 1",
                "description": "First subtask",
                "estimated_hours": 2.0,
                "dependencies": [],
            },
            {
                "name": "Subtask 2",
                "description": "Second subtask",
                "estimated_hours": 2.0,
                "dependencies": [],
            },
        ]
        created_subtasks = subtask_manager.add_subtasks(
            parent_task_in_progress.id, subtasks_data
        )

        # Mark first subtask as IN_PROGRESS (simulating it being assigned)
        subtask_manager.update_subtask_status(
            created_subtasks[0].id, TaskStatus.IN_PROGRESS, "agent-1"
        )

        # Try to find next available subtask
        # This should return Subtask 2, not None
        subtask = find_next_available_subtask(
            agent_id="agent-2",
            project_tasks=[parent_task_in_progress],
            subtask_manager=subtask_manager,
            assigned_task_ids={created_subtasks[0].id},  # First subtask assigned
        )

        # BUG FIX: This should now work (previously returned None)
        assert subtask is not None
        assert subtask.name == "Subtask 2"
        assert subtask.parent_task_id == parent_task_in_progress.id

    def test_skip_done_parent_task(self, subtask_manager, parent_task_done):
        """Test that DONE parent tasks are skipped."""
        # Add subtasks to done parent
        subtasks_data = [
            {
                "name": "Subtask 1",
                "description": "First subtask",
                "estimated_hours": 2.0,
                "dependencies": [],
            },
        ]
        subtask_manager.add_subtasks(parent_task_done.id, subtasks_data)

        # Try to find subtask from done parent
        subtask = find_next_available_subtask(
            agent_id="agent-1",
            project_tasks=[parent_task_done],
            subtask_manager=subtask_manager,
            assigned_task_ids=set(),
        )

        # Should return None because parent is DONE
        assert subtask is None

    def test_parallel_assignment_scenario(
        self, subtask_manager, parent_task_in_progress
    ):
        """
        Test realistic parallel assignment scenario.

        Simulates: 3 parent tasks, each with 5 subtasks, 15 workers
        Should be able to assign all 15 subtasks in parallel.
        """
        # Create 3 parent tasks with 5 subtasks each
        parent_tasks = []
        all_subtask_ids = []

        for i in range(3):
            parent = Task(
                id=f"parent-{i}",
                name=f"Parent Task {i}",
                description="Parent with subtasks",
                status=TaskStatus.IN_PROGRESS if i > 0 else TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=10.0,
                labels=["backend"],
            )
            parent_tasks.append(parent)

            # Add 5 subtasks
            subtasks_data = [
                {
                    "name": f"Subtask {j+1}",
                    "description": f"Subtask {j+1} for parent {i}",
                    "estimated_hours": 2.0,
                    "dependencies": [],
                }
                for j in range(5)
            ]
            created = subtask_manager.add_subtasks(parent.id, subtasks_data)
            all_subtask_ids.extend([s.id for s in created])

        # Simulate 15 workers requesting tasks
        assigned_subtasks = []
        assigned_ids: set[str] = set()

        for worker_num in range(15):
            subtask = find_next_available_subtask(
                agent_id=f"agent-{worker_num}",
                project_tasks=parent_tasks,
                subtask_manager=subtask_manager,
                assigned_task_ids=assigned_ids,
            )

            if subtask:
                assigned_subtasks.append(subtask)
                assigned_ids.add(subtask.id)
                # Mark as IN_PROGRESS
                subtask_manager.update_subtask_status(
                    subtask.id, TaskStatus.IN_PROGRESS, f"agent-{worker_num}"
                )
                # Update parent to IN_PROGRESS after first assignment
                parent = next(p for p in parent_tasks if p.id == subtask.parent_task_id)
                if parent.status == TaskStatus.TODO:
                    parent.status = TaskStatus.IN_PROGRESS

        # BUG FIX: All 15 subtasks should be assigned
        assert len(assigned_subtasks) == 15
        assert len(assigned_ids) == 15

        # Verify all subtasks were assigned
        assert set(assigned_ids) == set(all_subtask_ids)

    def test_convert_subtask_to_task(self, parent_task_todo):
        """Test converting a subtask to a Task object."""
        subtask = Subtask(
            id="parent-task-1_sub_1",
            parent_task_id=parent_task_todo.id,
            name="Test Subtask",
            description="Test subtask description",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            estimated_hours=2.0,
            dependencies=[],
            file_artifacts=["test.py"],
            provides="Test functionality",
            requires="None",
        )

        task = convert_subtask_to_task(subtask, parent_task_todo)

        assert task.id == subtask.id
        assert task.name == subtask.name
        assert task.description == subtask.description
        assert task.status == subtask.status
        assert task.priority == subtask.priority
        assert task.estimated_hours == subtask.estimated_hours
        assert task.labels == parent_task_todo.labels
        assert task.due_date == parent_task_todo.due_date

    def test_respects_already_assigned_subtasks(
        self, subtask_manager, parent_task_todo
    ):
        """Test that already assigned subtasks are skipped."""
        subtasks_data = [
            {
                "name": "Subtask 1",
                "description": "First subtask",
                "estimated_hours": 2.0,
                "dependencies": [],
            },
            {
                "name": "Subtask 2",
                "description": "Second subtask",
                "estimated_hours": 2.0,
                "dependencies": [],
            },
        ]
        created_subtasks = subtask_manager.add_subtasks(
            parent_task_todo.id, subtasks_data
        )

        # First assignment
        subtask1 = find_next_available_subtask(
            agent_id="agent-1",
            project_tasks=[parent_task_todo],
            subtask_manager=subtask_manager,
            assigned_task_ids=set(),
        )

        assert subtask1 is not None
        assert subtask1.name == "Subtask 1"

        # Mark first subtask as IN_PROGRESS and update parent status
        subtask_manager.update_subtask_status(
            created_subtasks[0].id, TaskStatus.IN_PROGRESS, "agent-1"
        )
        parent_task_todo.status = TaskStatus.IN_PROGRESS

        # Second assignment - should skip already assigned subtask
        subtask2 = find_next_available_subtask(
            agent_id="agent-2",
            project_tasks=[parent_task_todo],
            subtask_manager=subtask_manager,
            assigned_task_ids={created_subtasks[0].id},  # First subtask assigned
        )

        assert subtask2 is not None
        assert subtask2.name == "Subtask 2"
        assert subtask1 is not None
        assert subtask2.id != subtask1.id
