"""
Integration tests for automatic task decomposition with Planka checklist integration.

Tests the complete workflow from project creation through task decomposition
to checklist item creation and completion in Planka.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from pathlib import Path

from src.core.models import Priority, Task, TaskStatus


# Create a concrete implementation for testing
class _TaskCreatorHelper:
    """Concrete test implementation with only the methods we need to test."""

    def __init__(self, kanban_client, ai_engine=None):
        """Initialize test creator."""
        self.kanban_client = kanban_client
        self.ai_engine = ai_engine

    async def create_tasks_on_board(self, tasks):
        """
        Create tasks and apply decomposition.

        This is a simplified version that just calls the nlp_base method.
        """
        from src.integrations.nlp_base import NaturalLanguageTaskCreator

        # Import the method directly as a standalone function
        creator = type(
            "ConcreteCreator",
            (NaturalLanguageTaskCreator,),
            {"process_natural_language": lambda self, *args, **kwargs: None},
        )(self.kanban_client, self.ai_engine)

        return await creator.create_tasks_on_board(tasks)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAutomaticDecompositionPlanka:
    """Test suite for automatic decomposition with Planka integration."""

    @pytest.fixture
    def mock_kanban_client(self):
        """Create mock Kanban client."""
        client = Mock()
        client.create_task = AsyncMock()
        client.update_task_progress = AsyncMock()
        client.add_comment = AsyncMock()
        client.update_task = AsyncMock()
        return client

    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine."""
        engine = Mock()
        engine.generate_structured_response = AsyncMock()
        return engine

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks with varying estimated hours."""
        return [
            Task(
                id="task-1",
                name="Build authentication system",
                description="Create user authentication with JWT tokens",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,  # Should be decomposed
                labels=["backend", "security"],
            ),
            Task(
                id="task-2",
                name="Add logging",
                description="Add basic logging functionality",
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,  # Should NOT be decomposed
                labels=["backend"],
            ),
        ]

    @pytest.fixture
    def sample_decomposition(self):
        """Sample decomposition response from AI."""
        return {
            "subtasks": [
                {
                    "name": "Create User model",
                    "description": "Define User model with email and password",
                    "estimated_hours": 2.0,
                    "dependencies": [],
                    "file_artifacts": ["src/models/user.py"],
                    "provides": "User model",
                    "requires": "None",
                },
                {
                    "name": "Build login endpoint",
                    "description": "Create POST /api/login",
                    "estimated_hours": 3.0,
                    "dependencies": [0],  # Use index, not ID
                    "file_artifacts": ["src/api/auth/login.py"],
                    "provides": "Login endpoint",
                    "requires": "User model",
                },
                {
                    "name": "Integrate and validate Build authentication system",
                    "description": "Final integration step",
                    "estimated_hours": 1.5,
                    "dependencies": [0, 1],  # Use indices, not IDs
                    "file_artifacts": [
                        "docs/integration_report.md",
                        "tests/integration/test_integration.py",
                    ],
                    "provides": "Fully integrated solution",
                    "requires": "All components",
                },
            ],
            "shared_conventions": {
                "base_path": "src/api/",
                "response_format": {"success": {"status": "success"}},
            },
        }

    @pytest.mark.asyncio
    async def test_large_task_automatically_decomposed(
        self, mock_kanban_client, mock_ai_engine, sample_tasks, sample_decomposition
    ):
        """Test that tasks >= 4 hours are automatically decomposed."""
        # Arrange
        creator = _TaskCreatorHelper(mock_kanban_client, mock_ai_engine)

        # Mock task creation to return created tasks
        created_tasks = [
            Task(
                id="card-1",
                name="Build authentication system",
                description="Create user authentication with JWT tokens",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=["backend", "security"],
            ),
            Task(
                id="card-2",
                name="Add logging",
                description="Add basic logging functionality",
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                labels=["backend"],
            ),
        ]

        mock_kanban_client.create_task.side_effect = created_tasks

        # Mock AI decomposition
        mock_ai_engine.generate_structured_response.return_value = (
            sample_decomposition
        )

        # Mock MCP client for checklist items
        with patch(
            "mcp.client.stdio.stdio_client"
        ) as mock_stdio, patch(
            "mcp.ClientSession"
        ) as mock_session_class:
            # Setup the context manager for stdio_client
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)

            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock()
            mock_session.call_tool = AsyncMock(return_value=Mock())
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Act
            result_tasks = await creator.create_tasks_on_board(sample_tasks)

            # Assert
            assert len(result_tasks) == 2

            # AI should be called once for the large task
            assert mock_ai_engine.generate_structured_response.call_count == 1

            # Checklist items should be created (3 subtasks + 1 auto integration = 4)
            assert mock_session.call_tool.call_count == 4

            # Verify checklist items were created for the large task
            call_args_list = mock_session.call_tool.call_args_list
            for call_args in call_args_list:
                args, kwargs = call_args
                assert args[0] == "mcp_kanban_task_manager"
                assert args[1]["action"] == "create"
                assert args[1]["cardId"] == "card-1"

    @pytest.mark.asyncio
    async def test_small_task_not_decomposed(
        self, mock_kanban_client, mock_ai_engine, sample_tasks
    ):
        """Test that tasks < 4 hours are not decomposed."""
        # Arrange
        creator = _TaskCreatorHelper(mock_kanban_client, mock_ai_engine)

        # Only include the small task
        small_task = [sample_tasks[1]]

        created_task = Task(
            id="card-2",
            name="Add logging",
            description="Add basic logging functionality",
            status=TaskStatus.TODO,
            priority=Priority.LOW,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            labels=["backend"],
        )

        mock_kanban_client.create_task.return_value = created_task

        # Act
        result_tasks = await creator.create_tasks_on_board(small_task)

        # Assert
        assert len(result_tasks) == 1

        # AI should NOT be called for small tasks
        assert mock_ai_engine.generate_structured_response.call_count == 0

    @pytest.mark.asyncio
    async def test_decomposition_with_no_ai_engine(
        self, mock_kanban_client, sample_tasks
    ):
        """Test that decomposition is skipped when no AI engine is available."""
        # Arrange
        creator = _TaskCreatorHelper(mock_kanban_client, ai_engine=None)

        created_task = Task(
            id="card-1",
            name="Build authentication system",
            description="Create user authentication with JWT tokens",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["backend", "security"],
        )

        mock_kanban_client.create_task.return_value = created_task

        # Act
        result_tasks = await creator.create_tasks_on_board([sample_tasks[0]])

        # Assert
        assert len(result_tasks) == 1
        # No decomposition should happen without AI engine

    @pytest.mark.asyncio
    async def test_checklist_item_names_match_subtasks(
        self, mock_kanban_client, mock_ai_engine, sample_tasks, sample_decomposition
    ):
        """Test that checklist items are created with correct subtask names."""
        # Arrange
        creator = _TaskCreatorHelper(mock_kanban_client, mock_ai_engine)

        created_task = Task(
            id="card-1",
            name="Build authentication system",
            description="Create user authentication with JWT tokens",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["backend", "security"],
        )

        mock_kanban_client.create_task.return_value = created_task
        mock_ai_engine.generate_structured_response.return_value = (
            sample_decomposition
        )

        # Mock MCP client
        with patch("mcp.client.stdio.stdio_client") as mock_stdio, patch(
            "mcp.ClientSession"
        ) as mock_session_class:
            # Setup the context manager for stdio_client
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)

            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock()
            mock_session.call_tool = AsyncMock(return_value=Mock())
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Act
            await creator.create_tasks_on_board([sample_tasks[0]])

            # Assert - Check that checklist items have correct names
            call_args_list = mock_session.call_tool.call_args_list

            # The decomposer adds an automatic integration subtask
            expected_names = [
                "Create User model",
                "Build login endpoint",
                "Integrate and validate Build authentication system",
                "Integrate and validate Build authentication system",  # Auto integration
            ]

            actual_names = [
                call_args[0][1]["name"] for call_args in call_args_list
            ]

            # Check that we got all expected names (4 total, with integration appearing twice)
            assert len(actual_names) == 4
            assert "Create User model" in actual_names
            assert "Build login endpoint" in actual_names
            assert actual_names.count("Integrate and validate Build authentication system") == 2

    @pytest.mark.asyncio
    async def test_decomposition_error_handling(
        self, mock_kanban_client, mock_ai_engine, sample_tasks
    ):
        """Test that decomposition errors are handled gracefully."""
        # Arrange
        creator = _TaskCreatorHelper(mock_kanban_client, mock_ai_engine)

        created_task = Task(
            id="card-1",
            name="Build authentication system",
            description="Create user authentication with JWT tokens",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["backend", "security"],
        )

        mock_kanban_client.create_task.return_value = created_task

        # Mock AI to return failure
        mock_ai_engine.generate_structured_response.return_value = {
            "success": False,
            "error": "AI service unavailable",
        }

        # Act - Should not raise exception
        result_tasks = await creator.create_tasks_on_board([sample_tasks[0]])

        # Assert - Task still created, just not decomposed
        assert len(result_tasks) == 1

    @pytest.mark.asyncio
    async def test_checklist_creation_error_handling(
        self, mock_kanban_client, mock_ai_engine, sample_tasks, sample_decomposition
    ):
        """Test that checklist creation errors don't fail task creation."""
        # Arrange
        creator = _TaskCreatorHelper(mock_kanban_client, mock_ai_engine)

        created_task = Task(
            id="card-1",
            name="Build authentication system",
            description="Create user authentication with JWT tokens",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["backend", "security"],
        )

        mock_kanban_client.create_task.return_value = created_task
        mock_ai_engine.generate_structured_response.return_value = (
            sample_decomposition
        )

        # Mock MCP client to raise error
        with patch(
            "mcp.client.stdio.stdio_client", side_effect=Exception("MCP error")
        ):
            # Act - Should not raise exception
            result_tasks = await creator.create_tasks_on_board([sample_tasks[0]])

            # Assert - Task still created
            assert len(result_tasks) == 1
