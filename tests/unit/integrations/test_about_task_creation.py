"""
Unit tests for About task creation with hierarchical formatting.

Tests the _create_about_task method in NaturalLanguageProjectCreator
to ensure proper hierarchical formatting when tasks have subtasks.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.nlp_tools import NaturalLanguageProjectCreator
from src.marcus_mcp.coordinator.subtask_manager import Subtask


class TestAboutTaskCreation:
    """Test suite for About task creation with hierarchical formatting."""

    @pytest.fixture
    def mock_kanban_client(self):
        """Create mock kanban client."""
        client = Mock()
        client.project_id = "test_project"
        client.board_id = "test_board"
        return client

    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine."""
        return Mock()

    @pytest.fixture
    def mock_subtask_manager(self):
        """Create mock subtask manager."""
        manager = Mock()
        manager.has_subtasks = Mock(return_value=False)
        manager.get_subtasks = Mock(return_value=[])
        return manager

    @pytest.fixture
    def creator_with_subtasks(
        self, mock_kanban_client, mock_ai_engine, mock_subtask_manager
    ):
        """Create NaturalLanguageProjectCreator with subtask manager."""
        creator = NaturalLanguageProjectCreator(
            kanban_client=mock_kanban_client,
            ai_engine=mock_ai_engine,
            subtask_manager=mock_subtask_manager,
        )
        return creator

    @pytest.fixture
    def creator_without_subtasks(self, mock_kanban_client, mock_ai_engine):
        """Create NaturalLanguageProjectCreator without subtask manager."""
        creator = NaturalLanguageProjectCreator(
            kanban_client=mock_kanban_client,
            ai_engine=mock_ai_engine,
            subtask_manager=None,
        )
        return creator

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        return [
            Task(
                id="task_1",
                name="Setup Database",
                description="Configure PostgreSQL database",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=4.0,
                dependencies=[],
                labels=["backend", "database"],
            ),
            Task(
                id="task_2",
                name="Create API Endpoints",
                description="Build REST API endpoints",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=8.0,
                dependencies=["task_1"],
                labels=["backend", "api"],
            ),
            Task(
                id="task_3",
                name="Write Documentation",
                description="Create user documentation",
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                estimated_hours=3.0,
                dependencies=[],
                labels=["documentation"],
            ),
        ]

    def test_create_about_task_without_subtasks(
        self, creator_without_subtasks, sample_tasks
    ):
        """Test about task creation without subtask manager (flat list)."""
        description = "Build a REST API for task management"
        project_name = "Task Manager API"

        about_task = creator_without_subtasks._create_about_task(
            description, project_name, sample_tasks
        )

        # Verify task metadata
        assert about_task.name == "About: Task Manager API"
        assert about_task.status == TaskStatus.DONE
        assert about_task.priority == Priority.LOW
        assert about_task.estimated_hours == 0
        assert "documentation" in about_task.labels
        assert about_task.source_type == "project_about"

        # Verify description contains original description
        assert "Build a REST API for task management" in about_task.description
        assert "## Original Description" in about_task.description

        # Verify flat task list formatting
        assert "## Generated Tasks" in about_task.description
        assert "### 1. Setup Database" in about_task.description
        assert "### 2. Create API Endpoints" in about_task.description
        assert "### 3. Write Documentation" in about_task.description
        assert (
            "**Description:** Configure PostgreSQL database" in about_task.description
        )
        assert "**Estimated Hours:** 4.0" in about_task.description
        assert "**Labels:** backend, database" in about_task.description

    def test_create_about_task_with_subtasks_hierarchical(
        self, creator_with_subtasks, sample_tasks, mock_subtask_manager
    ):
        """Test about task creation with subtasks shows hierarchical structure."""
        description = "Build a REST API for task management"
        project_name = "Task Manager API"

        # Configure mock: task_1 has subtasks, others don't
        def has_subtasks_side_effect(task_id, project_tasks=None):
            return task_id == "task_1"

        mock_subtask_manager.has_subtasks.side_effect = has_subtasks_side_effect

        # Create mock subtasks for task_1
        mock_subtasks = [
            Subtask(
                id="task_1_sub_1",
                parent_task_id="task_1",
                name="Install PostgreSQL",
                description="Install PostgreSQL on server",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                estimated_hours=1.0,
                order=0,
            ),
            Subtask(
                id="task_1_sub_2",
                parent_task_id="task_1",
                name="Create Database Schema",
                description="Design and create database schema",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                estimated_hours=2.0,
                order=1,
            ),
            Subtask(
                id="task_1_sub_3",
                parent_task_id="task_1",
                name="Configure Connection Pool",
                description="Set up database connection pooling",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                estimated_hours=1.0,
                order=2,
            ),
        ]

        def get_subtasks_side_effect(task_id, project_tasks=None):
            if task_id == "task_1":
                return mock_subtasks
            return []

        mock_subtask_manager.get_subtasks.side_effect = get_subtasks_side_effect

        about_task = creator_with_subtasks._create_about_task(
            description, project_name, sample_tasks
        )

        # Verify hierarchical formatting for parent task with subtasks
        assert "### 1. Setup Database" in about_task.description
        assert "**Subtasks:**" in about_task.description
        assert "  1.1. Install PostgreSQL" in about_task.description
        assert "     - Install PostgreSQL on server" in about_task.description
        assert "     - Estimated: 1.0h" in about_task.description
        assert "  1.2. Create Database Schema" in about_task.description
        assert "     - Design and create database schema" in about_task.description
        assert "     - Estimated: 2.0h" in about_task.description
        assert "  1.3. Configure Connection Pool" in about_task.description
        assert "     - Set up database connection pooling" in about_task.description
        assert "     - Estimated: 1.0h" in about_task.description

        # Verify tasks without subtasks remain flat
        assert "### 2. Create API Endpoints" in about_task.description
        assert "**Description:** Build REST API endpoints" in about_task.description

        # Verify has_subtasks was called for each task
        assert mock_subtask_manager.has_subtasks.call_count == len(sample_tasks)

        # Verify get_subtasks was called only for task_1
        assert mock_subtask_manager.get_subtasks.call_count == 1
        mock_subtask_manager.get_subtasks.assert_called_with("task_1", None)

    def test_create_about_task_all_tasks_have_subtasks(
        self, creator_with_subtasks, sample_tasks, mock_subtask_manager
    ):
        """Test about task creation when all tasks have subtasks."""
        description = "Complex project with all hierarchical tasks"
        project_name = "Complex Project"

        # All tasks have subtasks
        mock_subtask_manager.has_subtasks.return_value = True

        # Create subtasks for each parent
        def get_subtasks_side_effect(task_id, project_tasks=None):
            return [
                Subtask(
                    id=f"{task_id}_sub_1",
                    parent_task_id=task_id,
                    name=f"Subtask 1 of {task_id}",
                    description=f"First subtask of {task_id}",
                    status=TaskStatus.TODO,
                    priority=Priority.MEDIUM,
                    assigned_to=None,
                    created_at=datetime.now(timezone.utc),
                    estimated_hours=2.0,
                    order=0,
                ),
                Subtask(
                    id=f"{task_id}_sub_2",
                    parent_task_id=task_id,
                    name=f"Subtask 2 of {task_id}",
                    description=f"Second subtask of {task_id}",
                    status=TaskStatus.TODO,
                    priority=Priority.LOW,
                    assigned_to=None,
                    created_at=datetime.now(timezone.utc),
                    estimated_hours=1.5,
                    order=1,
                ),
            ]

        mock_subtask_manager.get_subtasks.side_effect = get_subtasks_side_effect

        about_task = creator_with_subtasks._create_about_task(
            description, project_name, sample_tasks
        )

        # Verify all tasks show subtasks
        for idx, task in enumerate(sample_tasks, 1):
            assert f"### {idx}. {task.name}" in about_task.description
            assert "**Subtasks:**" in about_task.description
            assert f"  {idx}.1. Subtask 1 of {task.id}" in about_task.description
            assert f"  {idx}.2. Subtask 2 of {task.id}" in about_task.description

    def test_create_about_task_empty_tasks_list(self, creator_without_subtasks):
        """Test about task creation with empty tasks list."""
        description = "Empty project"
        project_name = "Empty Project"
        tasks = []

        about_task = creator_without_subtasks._create_about_task(
            description, project_name, tasks
        )

        # Should still create valid about task
        assert about_task.name == "About: Empty Project"
        assert "## Generated Tasks" in about_task.description
        # Should have no task entries
        assert "### 1." not in about_task.description

    def test_create_about_task_single_task_with_subtasks(
        self, creator_with_subtasks, mock_subtask_manager
    ):
        """Test about task with single parent task having multiple subtasks."""
        description = "Single complex task project"
        project_name = "Single Task Project"

        parent_task = Task(
            id="main_task",
            name="Complete Project",
            description="Main task with many subtasks",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=20.0,
            dependencies=[],
            labels=["main"],
        )

        mock_subtask_manager.has_subtasks.return_value = True
        mock_subtask_manager.get_subtasks.return_value = [
            Subtask(
                id=f"main_task_sub_{i}",
                parent_task_id="main_task",
                name=f"Subtask {i}",
                description=f"Description for subtask {i}",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                estimated_hours=2.0,
                order=i - 1,
            )
            for i in range(1, 6)
        ]

        about_task = creator_with_subtasks._create_about_task(
            description, project_name, [parent_task]
        )

        # Verify parent task
        assert "### 1. Complete Project" in about_task.description
        assert "**Subtasks:**" in about_task.description

        # Verify all 5 subtasks
        for i in range(1, 6):
            assert f"  1.{i}. Subtask {i}" in about_task.description
            assert f"     - Description for subtask {i}" in about_task.description
            assert "     - Estimated: 2.0h" in about_task.description

    def test_create_about_task_preserves_parent_info(
        self, creator_with_subtasks, mock_subtask_manager
    ):
        """Test that parent task info is preserved when showing subtasks."""
        description = "Test parent info preservation"
        project_name = "Parent Info Test"

        parent_task = Task(
            id="parent_1",
            name="Parent Task",
            description="Parent task description",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=10.0,
            dependencies=[],
            labels=["backend", "api", "critical"],
        )

        mock_subtask_manager.has_subtasks.return_value = True
        mock_subtask_manager.get_subtasks.return_value = [
            Subtask(
                id="parent_1_sub_1",
                parent_task_id="parent_1",
                name="Child Task",
                description="Child task description",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                estimated_hours=5.0,
                order=0,
            )
        ]

        about_task = creator_with_subtasks._create_about_task(
            description, project_name, [parent_task]
        )

        # Verify parent task info is still shown
        assert "### 1. Parent Task" in about_task.description
        assert "**Description:** Parent task description" in about_task.description
        assert "**Estimated Hours:** 10.0" in about_task.description
        assert "**Labels:** backend, api, critical" in about_task.description

        # Verify subtasks are added below parent info
        assert "**Subtasks:**" in about_task.description
        assert "  1.1. Child Task" in about_task.description

    def test_create_about_task_mixed_parents_and_standalone(
        self, creator_with_subtasks, sample_tasks, mock_subtask_manager
    ):
        """Test about task with mix of parent tasks and standalone tasks."""
        description = "Mixed task structure"
        project_name = "Mixed Project"

        # Only middle task has subtasks
        def has_subtasks_side_effect(task_id, project_tasks=None):
            return task_id == "task_2"

        mock_subtask_manager.has_subtasks.side_effect = has_subtasks_side_effect

        mock_subtask_manager.get_subtasks.return_value = [
            Subtask(
                id="task_2_sub_1",
                parent_task_id="task_2",
                name="API Subtask",
                description="Subtask for API",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                estimated_hours=3.0,
                order=0,
            )
        ]

        about_task = creator_with_subtasks._create_about_task(
            description, project_name, sample_tasks
        )

        # First task: standalone (no subtasks marker)
        assert "### 1. Setup Database" in about_task.description
        assert (
            "**Description:** Configure PostgreSQL database" in about_task.description
        )

        # Second task: has subtasks
        assert "### 2. Create API Endpoints" in about_task.description
        assert "**Subtasks:**" in about_task.description
        assert "  2.1. API Subtask" in about_task.description

        # Third task: standalone (no subtasks marker)
        assert "### 3. Write Documentation" in about_task.description
        assert "**Description:** Create user documentation" in about_task.description

    def test_create_about_task_no_subtask_manager_attribute(
        self, mock_kanban_client, mock_ai_engine, sample_tasks
    ):
        """Test graceful handling when subtask_manager attribute doesn't exist."""
        # Create creator without subtask_manager
        creator = NaturalLanguageProjectCreator(
            kanban_client=mock_kanban_client,
            ai_engine=mock_ai_engine,
            subtask_manager=None,
        )

        description = "Test without subtask manager"
        project_name = "No Subtask Manager"

        # Should not raise an error
        about_task = creator._create_about_task(description, project_name, sample_tasks)

        # Should create flat list
        assert about_task.name == "About: No Subtask Manager"
        assert "### 1. Setup Database" in about_task.description
        assert "### 2. Create API Endpoints" in about_task.description
        # Should not have subtask formatting
        assert "**Subtasks:**" not in about_task.description
