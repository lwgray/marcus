"""
Unit tests for unified subtask storage in project_tasks.

Tests the Phase 3 refactoring that moves subtasks from separate
SubtaskManager storage into the unified project_tasks list as
first-class Task objects.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.subtask_manager import (
    Subtask,
    SubtaskManager,
    SubtaskMetadata,
)


class TestUnifiedSubtaskStorage:
    """Test suite for unified subtask storage."""

    @pytest.fixture
    def temp_state_file(self):
        """Create temporary state file for testing."""
        with TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "subtasks.json"
            yield state_file

    @pytest.fixture
    def project_tasks(self) -> List[Task]:
        """Create a list simulating server.project_tasks."""
        return []

    @pytest.fixture
    def parent_task(self) -> Task:
        """Create a parent task that will be decomposed."""
        return Task(
            id="task-1",
            name="Implement authentication system",
            description="Build complete auth with login, registration, and JWT",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=8.0,
            dependencies=[],
            labels=["backend", "authentication"],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
        )

    def test_add_subtasks_creates_task_objects_with_subtask_fields(
        self, temp_state_file, project_tasks, parent_task
    ):
        """Test that add_subtasks creates Task objects with subtask fields."""
        # Arrange
        manager = SubtaskManager(state_file=temp_state_file)

        subtask_data = [
            {
                "name": "Create User model",
                "description": "Define User model with email validation",
                "estimated_hours": 2.0,
                "file_artifacts": ["src/models/user.py"],
                "provides": "User model",
            },
            {
                "name": "Build login endpoint",
                "description": "POST /api/login",
                "estimated_hours": 3.0,
                "dependencies": ["task-1_sub_1"],
                "dependency_types": ["soft"],
                "file_artifacts": ["src/api/auth/login.py"],
            },
        ]

        # Act
        created_subtasks = manager.add_subtasks(
            parent_task.id, subtask_data, project_tasks
        )

        # Assert - subtasks are created as Task objects
        assert len(created_subtasks) == 2
        assert all(isinstance(st, Task) for st in created_subtasks)

        # Check first subtask fields
        subtask1 = created_subtasks[0]
        assert subtask1.id == "task-1_sub_1"
        assert subtask1.name == "Create User model"
        assert subtask1.is_subtask is True
        assert subtask1.parent_task_id == "task-1"
        assert subtask1.subtask_index == 0
        assert subtask1.status == TaskStatus.TODO
        assert subtask1.dependencies == []

        # Check second subtask
        subtask2 = created_subtasks[1]
        assert subtask2.id == "task-1_sub_2"
        assert subtask2.is_subtask is True
        assert subtask2.parent_task_id == "task-1"
        assert subtask2.subtask_index == 1
        assert subtask2.dependencies == ["task-1_sub_1"]

    def test_add_subtasks_appends_to_project_tasks(
        self, temp_state_file, project_tasks, parent_task
    ):
        """Test that subtasks are appended to project_tasks list."""
        # Arrange
        manager = SubtaskManager(state_file=temp_state_file)
        project_tasks.append(parent_task)  # Parent is already in project_tasks

        subtask_data = [
            {
                "name": "Subtask 1",
                "description": "First subtask",
                "estimated_hours": 2.0,
            },
        ]

        # Act
        manager.add_subtasks(parent_task.id, subtask_data, project_tasks)

        # Assert - project_tasks now has parent + subtask
        assert len(project_tasks) == 2
        assert project_tasks[0].id == "task-1"  # Parent
        assert project_tasks[1].id == "task-1_sub_1"  # Subtask
        assert project_tasks[1].is_subtask is True

    def test_get_subtasks_queries_project_tasks(
        self, temp_state_file, project_tasks, parent_task
    ):
        """Test that get_subtasks filters project_tasks by parent_task_id."""
        # Arrange
        manager = SubtaskManager(state_file=temp_state_file)
        project_tasks.append(parent_task)

        subtask_data = [
            {"name": "Subtask 1", "description": "First", "estimated_hours": 2.0},
            {"name": "Subtask 2", "description": "Second", "estimated_hours": 3.0},
        ]

        manager.add_subtasks(parent_task.id, subtask_data, project_tasks)

        # Add another parent with its own subtasks
        other_parent = Task(
            id="task-2",
            name="Other task",
            description="Different task",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=5.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
        )
        project_tasks.append(other_parent)
        manager.add_subtasks(
            other_parent.id,
            [{"name": "Other subtask", "description": "Other", "estimated_hours": 1.0}],
            project_tasks,
        )

        # Act
        task1_subtasks = manager.get_subtasks(parent_task.id, project_tasks)
        task2_subtasks = manager.get_subtasks(other_parent.id, project_tasks)

        # Assert - get_subtasks only returns matching subtasks
        assert len(task1_subtasks) == 2
        assert all(st.parent_task_id == "task-1" for st in task1_subtasks)
        assert task1_subtasks[0].subtask_index == 0
        assert task1_subtasks[1].subtask_index == 1

        assert len(task2_subtasks) == 1
        assert task2_subtasks[0].parent_task_id == "task-2"

    def test_get_next_available_subtask_from_project_tasks(
        self, temp_state_file, project_tasks, parent_task
    ):
        """Test finding next available subtask from unified storage."""
        # Arrange
        manager = SubtaskManager(state_file=temp_state_file)
        project_tasks.append(parent_task)

        subtask_data = [
            {
                "name": "Subtask 1",
                "description": "First",
                "estimated_hours": 2.0,
                "dependencies": [],
            },
            {
                "name": "Subtask 2",
                "description": "Second",
                "estimated_hours": 3.0,
                "dependencies": ["task-1_sub_1"],
                "dependency_types": ["hard"],
            },
        ]

        manager.add_subtasks(parent_task.id, subtask_data, project_tasks)
        completed = set()

        # Act - Get first available
        next_task = manager.get_next_available_subtask(
            parent_task.id, completed, project_tasks
        )

        # Assert - Should return first subtask
        assert next_task is not None
        assert next_task.id == "task-1_sub_1"
        assert next_task.dependencies == []

        # Mark first as done
        next_task.status = TaskStatus.DONE
        completed.add(next_task.id)

        # Act - Get second available
        next_task2 = manager.get_next_available_subtask(
            parent_task.id, completed, project_tasks
        )

        # Assert - Should return second subtask now
        assert next_task2 is not None
        assert next_task2.id == "task-1_sub_2"

    def test_update_subtask_status_updates_project_tasks(
        self, temp_state_file, project_tasks, parent_task
    ):
        """Test that updating subtask status modifies the Task in project_tasks."""
        # Arrange
        manager = SubtaskManager(state_file=temp_state_file)
        project_tasks.append(parent_task)

        subtask_data = [
            {"name": "Subtask 1", "description": "First", "estimated_hours": 2.0}
        ]

        manager.add_subtasks(parent_task.id, subtask_data, project_tasks)
        subtask_id = "task-1_sub_1"

        # Act
        result = manager.update_subtask_status(
            subtask_id, TaskStatus.IN_PROGRESS, project_tasks, assigned_to="agent-1"
        )

        # Assert - Status updated in project_tasks
        assert result is True
        subtask = next(t for t in project_tasks if t.id == subtask_id)
        assert subtask.status == TaskStatus.IN_PROGRESS
        assert subtask.assigned_to == "agent-1"  # type: ignore[attr-defined]

    def test_is_parent_complete_checks_project_tasks(
        self, temp_state_file, project_tasks, parent_task
    ):
        """Test that is_parent_complete checks subtasks in project_tasks."""
        # Arrange
        manager = SubtaskManager(state_file=temp_state_file)
        project_tasks.append(parent_task)

        subtask_data = [
            {"name": "Subtask 1", "description": "First", "estimated_hours": 2.0},
            {"name": "Subtask 2", "description": "Second", "estimated_hours": 3.0},
        ]

        manager.add_subtasks(parent_task.id, subtask_data, project_tasks)

        # Act & Assert - Initially incomplete
        assert manager.is_parent_complete(parent_task.id, project_tasks) is False

        # Mark first subtask done
        project_tasks[1].status = TaskStatus.DONE
        assert manager.is_parent_complete(parent_task.id, project_tasks) is False

        # Mark second subtask done
        project_tasks[2].status = TaskStatus.DONE
        assert manager.is_parent_complete(parent_task.id, project_tasks) is True

    def test_get_completion_percentage_from_project_tasks(
        self, temp_state_file, project_tasks, parent_task
    ):
        """Test completion percentage calculation from unified storage."""
        # Arrange
        manager = SubtaskManager(state_file=temp_state_file)
        project_tasks.append(parent_task)

        subtask_data = [
            {"name": f"Subtask {i}", "description": f"Task {i}", "estimated_hours": 2.0}
            for i in range(1, 5)
        ]

        manager.add_subtasks(parent_task.id, subtask_data, project_tasks)

        # Act & Assert - 0% initially
        assert manager.get_completion_percentage(parent_task.id, project_tasks) == 0.0

        # Mark one done (25%)
        project_tasks[1].status = TaskStatus.DONE
        assert manager.get_completion_percentage(parent_task.id, project_tasks) == 25.0

        # Mark two more done (75%)
        project_tasks[2].status = TaskStatus.DONE
        project_tasks[3].status = TaskStatus.DONE
        assert manager.get_completion_percentage(parent_task.id, project_tasks) == 75.0

    def test_remove_subtasks_removes_from_project_tasks(
        self, temp_state_file, project_tasks, parent_task
    ):
        """Test that remove_subtasks deletes Task objects from project_tasks."""
        # Arrange
        manager = SubtaskManager(state_file=temp_state_file)
        project_tasks.append(parent_task)

        subtask_data = [
            {"name": "Subtask 1", "description": "First", "estimated_hours": 2.0},
            {"name": "Subtask 2", "description": "Second", "estimated_hours": 3.0},
        ]

        manager.add_subtasks(parent_task.id, subtask_data, project_tasks)
        assert len(project_tasks) == 3  # Parent + 2 subtasks

        # Act
        result = manager.remove_subtasks(parent_task.id, project_tasks)

        # Assert - Subtasks removed from project_tasks
        assert result is True
        assert len(project_tasks) == 1  # Only parent remains
        assert project_tasks[0].id == "task-1"
        assert not any(t.is_subtask for t in project_tasks)

    def test_has_subtasks_queries_project_tasks(
        self, temp_state_file, project_tasks, parent_task
    ):
        """Test that has_subtasks checks project_tasks for subtasks."""
        # Arrange
        manager = SubtaskManager(state_file=temp_state_file)
        project_tasks.append(parent_task)

        # Act & Assert - No subtasks initially
        assert manager.has_subtasks(parent_task.id, project_tasks) is False

        # Add subtasks
        subtask_data = [
            {"name": "Subtask 1", "description": "First", "estimated_hours": 2.0}
        ]
        manager.add_subtasks(parent_task.id, subtask_data, project_tasks)

        # Act & Assert - Has subtasks now
        assert manager.has_subtasks(parent_task.id, project_tasks) is True
        assert manager.has_subtasks("nonexistent-task", project_tasks) is False

    def test_backwards_compatibility_with_old_state_format(self, temp_state_file):
        """Test loading old state format with separate subtask storage."""
        # Arrange - Create old format state file
        old_state = {
            "subtasks": {
                "task-1_sub_1": {
                    "id": "task-1_sub_1",
                    "parent_task_id": "task-1",
                    "name": "Old subtask",
                    "description": "From old format",
                    "status": "in_progress",
                    "priority": "medium",
                    "assigned_to": "agent-1",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "estimated_hours": 2.0,
                    "dependencies": [],
                    "dependency_types": [],
                    "file_artifacts": [],
                    "provides": None,
                    "requires": None,
                    "order": 0,
                }
            },
            "parent_to_subtasks": {"task-1": ["task-1_sub_1"]},
            "metadata": {
                "task-1": {
                    "shared_conventions": {},
                    "decomposed_at": datetime.now(timezone.utc).isoformat(),
                    "decomposed_by": "ai",
                }
            },
        }

        with open(temp_state_file, "w") as f:
            json.dump(old_state, f)

        # Act - Load with new manager (should migrate to unified storage)
        # In production, parent tasks are loaded from Kanban before migration
        project_tasks: List[Task] = [
            Task(
                id="task-1",
                name="Parent task",
                description="Parent for old subtask",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=5.0,
                dependencies=[],
                labels=[],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=False,
            )
        ]
        manager = SubtaskManager(state_file=temp_state_file)
        manager.migrate_to_unified_storage(project_tasks)

        # Assert - Old subtask migrated to project_tasks as Task
        # Should have 1 parent + 1 subtask = 2 tasks
        assert len(project_tasks) == 2

        # First task should be the parent
        parent = project_tasks[0]
        assert parent.id == "task-1"
        assert parent.is_subtask is False

        # Second task should be the migrated subtask
        subtask = project_tasks[1]
        assert isinstance(subtask, Task)
        assert subtask.id == "task-1_sub_1"
        assert subtask.is_subtask is True
        assert subtask.parent_task_id == "task-1"
        assert subtask.subtask_index == 0
        assert subtask.status == TaskStatus.IN_PROGRESS
