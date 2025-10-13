"""
Unit tests for SubtaskManager.

Tests the subtask decomposition and tracking functionality.
"""

import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pytest

from src.core.models import Priority, TaskStatus
from src.marcus_mcp.coordinator.subtask_manager import (
    Subtask,
    SubtaskManager,
    SubtaskMetadata,
)


class TestSubtaskManager:
    """Test suite for SubtaskManager."""

    @pytest.fixture
    def temp_state_file(self):
        """Create temporary state file for testing."""
        with TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "subtasks.json"
            yield state_file

    @pytest.fixture
    def manager(self, temp_state_file):
        """Create SubtaskManager instance for testing."""
        return SubtaskManager(state_file=temp_state_file)

    @pytest.fixture
    def sample_subtasks(self):
        """Sample subtask data for testing."""
        return [
            {
                "name": "Create User model",
                "description": "Define User model in src/models/user.py",
                "estimated_hours": 2.0,
                "file_artifacts": ["src/models/user.py"],
                "provides": "User model with email validation",
            },
            {
                "name": "Build login endpoint",
                "description": "Create POST /api/login endpoint",
                "estimated_hours": 3.0,
                "dependencies": ["task-1_sub_1"],
                "file_artifacts": ["src/api/auth/login.py"],
                "requires": "User model",
            },
        ]

    def test_manager_initialization_creates_state_file(self, temp_state_file):
        """Test manager creates state file directory on initialization."""
        # Arrange & Act
        manager = SubtaskManager(state_file=temp_state_file)

        # Assert
        assert temp_state_file.parent.exists()
        assert manager.state_file == temp_state_file

    def test_add_subtasks_creates_subtasks_correctly(self, manager, sample_subtasks):
        """Test adding subtasks creates correct Subtask objects."""
        # Arrange
        parent_id = "task-1"

        # Act
        created_subtasks = manager.add_subtasks(parent_id, sample_subtasks)

        # Assert
        assert len(created_subtasks) == 2
        assert created_subtasks[0].name == "Create User model"
        assert created_subtasks[0].parent_task_id == parent_id
        assert created_subtasks[0].id == "task-1_sub_1"
        assert created_subtasks[0].status == TaskStatus.TODO
        assert created_subtasks[0].file_artifacts == ["src/models/user.py"]

    def test_add_subtasks_tracks_parent_relationship(self, manager, sample_subtasks):
        """Test subtasks are properly linked to parent task."""
        # Arrange
        parent_id = "task-1"

        # Act
        manager.add_subtasks(parent_id, sample_subtasks)

        # Assert
        assert parent_id in manager.parent_to_subtasks
        assert len(manager.parent_to_subtasks[parent_id]) == 2
        assert "task-1_sub_1" in manager.parent_to_subtasks[parent_id]
        assert "task-1_sub_2" in manager.parent_to_subtasks[parent_id]

    def test_get_subtasks_returns_ordered_list(self, manager, sample_subtasks):
        """Test get_subtasks returns subtasks in execution order."""
        # Arrange
        parent_id = "task-1"
        manager.add_subtasks(parent_id, sample_subtasks)

        # Act
        subtasks = manager.get_subtasks(parent_id)

        # Assert
        assert len(subtasks) == 2
        assert subtasks[0].order == 0
        assert subtasks[1].order == 1
        assert subtasks[0].name == "Create User model"

    def test_get_subtasks_returns_empty_for_unknown_parent(self, manager):
        """Test get_subtasks returns empty list for non-existent parent."""
        # Arrange & Act
        subtasks = manager.get_subtasks("non-existent-task")

        # Assert
        assert subtasks == []

    def test_get_next_available_subtask_returns_first_ready(
        self, manager, sample_subtasks
    ):
        """Test getting next available subtask with dependencies."""
        # Arrange
        parent_id = "task-1"
        manager.add_subtasks(parent_id, sample_subtasks)
        completed = set()

        # Act
        next_subtask = manager.get_next_available_subtask(parent_id, completed)

        # Assert
        assert next_subtask is not None
        assert next_subtask.name == "Create User model"
        assert next_subtask.dependencies == []

    def test_get_next_available_subtask_respects_dependencies(
        self, manager, sample_subtasks
    ):
        """Test subtask with dependencies is blocked until deps complete."""
        # Arrange
        parent_id = "task-1"
        manager.add_subtasks(parent_id, sample_subtasks)
        completed = set()

        # Mark first subtask as in progress
        manager.update_subtask_status("task-1_sub_1", TaskStatus.IN_PROGRESS)

        # Act
        next_subtask = manager.get_next_available_subtask(parent_id, completed)

        # Assert - should not return second subtask as first is not complete
        assert next_subtask is None

    def test_get_next_available_subtask_with_completed_dependencies(
        self, manager, sample_subtasks
    ):
        """Test subtask becomes available when dependencies complete."""
        # Arrange
        parent_id = "task-1"
        manager.add_subtasks(parent_id, sample_subtasks)
        completed = {"task-1_sub_1"}

        # Mark first as done
        manager.update_subtask_status("task-1_sub_1", TaskStatus.DONE)

        # Act
        next_subtask = manager.get_next_available_subtask(parent_id, completed)

        # Assert
        assert next_subtask is not None
        assert next_subtask.name == "Build login endpoint"

    def test_update_subtask_status_changes_status(self, manager, sample_subtasks):
        """Test updating subtask status works correctly."""
        # Arrange
        parent_id = "task-1"
        manager.add_subtasks(parent_id, sample_subtasks)

        # Act
        result = manager.update_subtask_status(
            "task-1_sub_1", TaskStatus.IN_PROGRESS, assigned_to="agent-1"
        )

        # Assert
        assert result is True
        subtask = manager.subtasks["task-1_sub_1"]
        assert subtask.status == TaskStatus.IN_PROGRESS
        assert subtask.assigned_to == "agent-1"

    def test_update_subtask_status_returns_false_for_unknown_subtask(self, manager):
        """Test updating non-existent subtask returns False."""
        # Arrange & Act
        result = manager.update_subtask_status("non-existent", TaskStatus.DONE)

        # Assert
        assert result is False

    def test_is_parent_complete_returns_false_when_incomplete(
        self, manager, sample_subtasks
    ):
        """Test parent completion check when subtasks incomplete."""
        # Arrange
        parent_id = "task-1"
        manager.add_subtasks(parent_id, sample_subtasks)
        manager.update_subtask_status("task-1_sub_1", TaskStatus.DONE)

        # Act
        is_complete = manager.is_parent_complete(parent_id)

        # Assert
        assert is_complete is False

    def test_is_parent_complete_returns_true_when_all_done(
        self, manager, sample_subtasks
    ):
        """Test parent completion check when all subtasks complete."""
        # Arrange
        parent_id = "task-1"
        manager.add_subtasks(parent_id, sample_subtasks)
        manager.update_subtask_status("task-1_sub_1", TaskStatus.DONE)
        manager.update_subtask_status("task-1_sub_2", TaskStatus.DONE)

        # Act
        is_complete = manager.is_parent_complete(parent_id)

        # Assert
        assert is_complete is True

    def test_get_completion_percentage_calculates_correctly(
        self, manager, sample_subtasks
    ):
        """Test completion percentage calculation."""
        # Arrange
        parent_id = "task-1"
        manager.add_subtasks(parent_id, sample_subtasks)
        manager.update_subtask_status("task-1_sub_1", TaskStatus.DONE)

        # Act
        percentage = manager.get_completion_percentage(parent_id)

        # Assert
        assert percentage == 50.0

    def test_get_subtask_context_includes_all_info(self, manager, sample_subtasks):
        """Test subtask context includes parent, conventions, and dependencies."""
        # Arrange
        parent_id = "task-1"
        metadata = SubtaskMetadata(
            shared_conventions={
                "base_path": "src/api/",
                "response_format": {"status": "success"},
            }
        )
        manager.add_subtasks(parent_id, sample_subtasks, metadata)

        # Act
        context = manager.get_subtask_context("task-1_sub_2")

        # Assert
        assert context["parent_task_id"] == parent_id
        assert context["shared_conventions"]["base_path"] == "src/api/"
        assert "task-1_sub_1" in context["dependency_artifacts"]
        assert len(context["sibling_subtasks"]) == 1  # Excludes self

    def test_has_subtasks_returns_true_when_subtasks_exist(
        self, manager, sample_subtasks
    ):
        """Test has_subtasks correctly identifies decomposed tasks."""
        # Arrange
        parent_id = "task-1"
        manager.add_subtasks(parent_id, sample_subtasks)

        # Act & Assert
        assert manager.has_subtasks(parent_id) is True
        assert manager.has_subtasks("task-2") is False

    def test_remove_subtasks_deletes_all_related_data(self, manager, sample_subtasks):
        """Test removing subtasks clears all tracking data."""
        # Arrange
        parent_id = "task-1"
        manager.add_subtasks(parent_id, sample_subtasks)

        # Act
        result = manager.remove_subtasks(parent_id)

        # Assert
        assert result is True
        assert parent_id not in manager.parent_to_subtasks
        assert "task-1_sub_1" not in manager.subtasks
        assert "task-1_sub_2" not in manager.subtasks
        assert parent_id not in manager.metadata

    def test_state_persistence_saves_and_loads(self, temp_state_file, sample_subtasks):
        """Test subtasks persist to disk and reload correctly."""
        # Arrange
        parent_id = "task-1"

        # Create manager and add subtasks
        manager1 = SubtaskManager(state_file=temp_state_file)
        manager1.add_subtasks(parent_id, sample_subtasks)
        manager1.update_subtask_status("task-1_sub_1", TaskStatus.IN_PROGRESS)

        # Act - Create new manager instance
        manager2 = SubtaskManager(state_file=temp_state_file)

        # Assert
        assert len(manager2.subtasks) == 2
        assert manager2.subtasks["task-1_sub_1"].status == TaskStatus.IN_PROGRESS
        assert manager2.subtasks["task-1_sub_1"].name == "Create User model"
        assert parent_id in manager2.parent_to_subtasks

    def test_state_file_format_is_valid_json(self, temp_state_file, sample_subtasks):
        """Test persisted state file is valid JSON."""
        # Arrange
        parent_id = "task-1"
        manager = SubtaskManager(state_file=temp_state_file)
        manager.add_subtasks(parent_id, sample_subtasks)

        # Act
        with open(temp_state_file, "r") as f:
            state = json.load(f)

        # Assert
        assert "subtasks" in state
        assert "parent_to_subtasks" in state
        assert "metadata" in state
        assert "task-1_sub_1" in state["subtasks"]


class TestSubtaskDependencyTypes:
    """Test suite for dependency_types field functionality."""

    @pytest.fixture
    def temp_state_file(self):
        """Create temporary state file for testing."""
        with TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "subtasks.json"
            yield state_file

    @pytest.fixture
    def manager(self, temp_state_file):
        """Create SubtaskManager instance for testing."""
        return SubtaskManager(state_file=temp_state_file)

    def test_add_subtasks_with_dependency_types(self, manager):
        """Test subtasks with dependency_types are created correctly."""
        # Arrange
        parent_id = "task-1"
        subtasks = [
            {
                "name": "Task 1",
                "description": "First task",
                "estimated_hours": 2.0,
                "dependencies": [],
                "dependency_types": [],
            },
            {
                "name": "Task 2",
                "description": "Second task",
                "estimated_hours": 3.0,
                "dependencies": ["task-1_sub_1"],
                "dependency_types": ["soft"],
            },
        ]

        # Act
        created_subtasks = manager.add_subtasks(parent_id, subtasks)

        # Assert
        assert created_subtasks[0].dependency_types == []
        assert created_subtasks[1].dependency_types == ["soft"]

    def test_add_subtasks_migrates_missing_dependency_types(self, manager):
        """Test migration defaults missing dependency_types to hard."""
        # Arrange
        parent_id = "task-1"
        subtasks = [
            {
                "name": "Task 1",
                "description": "First task",
                "estimated_hours": 2.0,
                "dependencies": [],
                # No dependency_types field (old format)
            },
            {
                "name": "Task 2",
                "description": "Second task",
                "estimated_hours": 3.0,
                "dependencies": ["task-1_sub_1"],
                # No dependency_types field (old format)
            },
        ]

        # Act
        created_subtasks = manager.add_subtasks(parent_id, subtasks)

        # Assert
        assert created_subtasks[0].dependency_types == []  # No deps, empty list
        assert created_subtasks[1].dependency_types == ["hard"]  # Defaulted to hard

    def test_load_state_migrates_old_format_without_dependency_types(
        self, temp_state_file
    ):
        """Test loading old state file without dependency_types migrates correctly."""
        # Arrange - Create old format state file
        old_state = {
            "subtasks": {
                "task-1_sub_1": {
                    "id": "task-1_sub_1",
                    "parent_task_id": "task-1",
                    "name": "Task 1",
                    "description": "First task",
                    "status": "todo",
                    "priority": "medium",
                    "assigned_to": None,
                    "created_at": datetime.now().isoformat(),
                    "estimated_hours": 2.0,
                    "dependencies": [],
                    "file_artifacts": [],
                    "provides": None,
                    "requires": None,
                    "order": 0,
                    # Note: No dependency_types field
                },
                "task-1_sub_2": {
                    "id": "task-1_sub_2",
                    "parent_task_id": "task-1",
                    "name": "Task 2",
                    "description": "Second task",
                    "status": "todo",
                    "priority": "medium",
                    "assigned_to": None,
                    "created_at": datetime.now().isoformat(),
                    "estimated_hours": 3.0,
                    "dependencies": ["task-1_sub_1"],
                    "file_artifacts": [],
                    "provides": None,
                    "requires": None,
                    "order": 1,
                    # Note: No dependency_types field
                },
            },
            "parent_to_subtasks": {"task-1": ["task-1_sub_1", "task-1_sub_2"]},
            "metadata": {
                "task-1": {
                    "shared_conventions": {},
                    "decomposed_at": datetime.now().isoformat(),
                    "decomposed_by": "ai",
                }
            },
        }

        with open(temp_state_file, "w") as f:
            json.dump(old_state, f)

        # Act - Load state with new manager
        manager = SubtaskManager(state_file=temp_state_file)

        # Assert
        assert "task-1_sub_1" in manager.subtasks
        assert "task-1_sub_2" in manager.subtasks
        # First subtask has no dependencies, should get empty list
        assert manager.subtasks["task-1_sub_1"].dependency_types == []
        # Second subtask has 1 dependency, should get ["hard"]
        assert manager.subtasks["task-1_sub_2"].dependency_types == ["hard"]

    def test_dependency_types_persisted_correctly(self, temp_state_file):
        """Test dependency_types are saved and loaded correctly."""
        # Arrange
        parent_id = "task-1"
        subtasks = [
            {
                "name": "Task 1",
                "description": "First",
                "estimated_hours": 2.0,
                "dependencies": [],
                "dependency_types": [],
            },
            {
                "name": "Task 2",
                "description": "Second",
                "estimated_hours": 3.0,
                "dependencies": ["task-1_sub_1"],
                "dependency_types": ["soft"],
            },
            {
                "name": "Task 3",
                "description": "Third",
                "estimated_hours": 2.5,
                "dependencies": ["task-1_sub_1", "task-1_sub_2"],
                "dependency_types": ["hard", "soft"],
            },
        ]

        manager1 = SubtaskManager(state_file=temp_state_file)
        manager1.add_subtasks(parent_id, subtasks)

        # Act - Reload from disk
        manager2 = SubtaskManager(state_file=temp_state_file)

        # Assert
        assert manager2.subtasks["task-1_sub_1"].dependency_types == []
        assert manager2.subtasks["task-1_sub_2"].dependency_types == ["soft"]
        assert manager2.subtasks["task-1_sub_3"].dependency_types == ["hard", "soft"]
