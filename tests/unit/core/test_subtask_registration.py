"""
Unit tests for subtask registration during task decomposition (GH-62).

Tests verify that subtasks created during task decomposition are properly
registered with SubtaskManager so they can be assigned individually to agents.
"""

from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.nlp_base import NaturalLanguageTaskCreator
from src.marcus_mcp.coordinator.subtask_manager import SubtaskMetadata


class MockNaturalLanguageTaskCreator(NaturalLanguageTaskCreator):
    """Mock implementation of abstract NaturalLanguageTaskCreator for testing."""

    async def process_natural_language(
        self, description: str, **kwargs: Any
    ) -> list[Task]:
        """Dummy implementation for testing."""
        return []


class TestSubtaskRegistration:
    """Test suite for subtask registration with SubtaskManager."""

    @pytest.fixture
    def mock_kanban_client(self):
        """Create mock Kanban client."""
        mock = Mock()
        mock.create_task = AsyncMock(return_value=Mock(id="task-123"))
        mock.add_checklist_item = AsyncMock()
        return mock

    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine."""
        mock = Mock()
        return mock

    @pytest.fixture
    def mock_subtask_manager(self):
        """Create mock SubtaskManager."""
        mock = Mock()
        mock.add_subtasks = Mock()
        return mock

    @pytest.fixture
    def sample_task(self):
        """Create sample task for decomposition."""
        now = datetime.now()
        return Task(
            id="task-123",
            name="Implement Get Current Time",
            description="Create endpoint that returns current server time",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=16.0,
            dependencies=[],
        )

    @pytest.fixture
    def sample_subtasks(self):
        """Create sample subtasks returned by decomposition."""
        return [
            {
                "id": "task-123_sub_1",
                "name": "Create endpoint route",
                "description": "Define GET /time endpoint",
                "estimated_hours": 4.0,
                "dependencies": [],
            },
            {
                "id": "task-123_sub_2",
                "name": "Implement time logic",
                "description": "Create function to get current time",
                "estimated_hours": 4.0,
                "dependencies": ["task-123_sub_1"],
            },
            {
                "id": "task-123_sub_3",
                "name": "Add response formatting",
                "description": "Format time response as JSON",
                "estimated_hours": 4.0,
                "dependencies": ["task-123_sub_2"],
            },
            {
                "id": "task-123_sub_4",
                "name": "Write tests",
                "description": "Create unit tests for endpoint",
                "estimated_hours": 4.0,
                "dependencies": ["task-123_sub_3"],
            },
        ]

    @pytest.fixture
    def task_creator_with_manager(
        self, mock_kanban_client, mock_ai_engine, mock_subtask_manager
    ):
        """Create MockNaturalLanguageTaskCreator with SubtaskManager."""
        return MockNaturalLanguageTaskCreator(
            kanban_client=mock_kanban_client,
            ai_engine=mock_ai_engine,
            subtask_manager=mock_subtask_manager,
        )

    @pytest.fixture
    def task_creator_without_manager(self, mock_kanban_client, mock_ai_engine):
        """Create MockNaturalLanguageTaskCreator without SubtaskManager."""
        return MockNaturalLanguageTaskCreator(
            kanban_client=mock_kanban_client,
            ai_engine=mock_ai_engine,
            subtask_manager=None,
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_subtasks_registered_with_manager(
        self,
        task_creator_with_manager,
        sample_task,
        sample_subtasks,
        mock_subtask_manager,
    ):
        """Test subtasks are registered with SubtaskManager after decomposition."""
        # Arrange
        decomposition_result = {
            "success": True,
            "subtasks": sample_subtasks,
            "shared_conventions": {"code_style": "PEP8"},
        }

        with (
            patch(
                "src.marcus_mcp.coordinator.decompose_task",
                new=AsyncMock(return_value=decomposition_result),
            ),
            patch.object(
                task_creator_with_manager, "_add_subtasks_as_checklist", new=AsyncMock()
            ),
        ):
            # Act
            await task_creator_with_manager._decompose_and_add_subtasks(
                created_tasks=[sample_task], original_tasks=[sample_task]
            )

            # Assert - verify SubtaskManager.add_subtasks was called
            assert mock_subtask_manager.add_subtasks.called
            call_args = mock_subtask_manager.add_subtasks.call_args

            # Verify parent_task_id
            assert call_args[1]["parent_task_id"] == "task-123"

            # Verify subtasks list
            assert call_args[1]["subtasks"] == sample_subtasks
            assert len(call_args[1]["subtasks"]) == 4

            # Verify metadata
            metadata = call_args[1]["metadata"]
            assert isinstance(metadata, SubtaskMetadata)
            assert metadata.decomposed_by == "ai"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_subtasks_not_registered_without_manager(
        self, task_creator_without_manager, sample_task, sample_subtasks
    ):
        """Test subtasks are not registered when SubtaskManager is None."""
        # Arrange
        decomposition_result = {
            "success": True,
            "subtasks": sample_subtasks,
            "shared_conventions": {},
        }

        with (
            patch(
                "src.marcus_mcp.coordinator.decompose_task",
                new=AsyncMock(return_value=decomposition_result),
            ),
            patch.object(
                task_creator_without_manager,
                "_add_subtasks_as_checklist",
                new=AsyncMock(),
            ),
        ):
            # Act & Assert - should not raise error even without manager
            await task_creator_without_manager._decompose_and_add_subtasks(
                created_tasks=[sample_task], original_tasks=[sample_task]
            )

            # Verify SubtaskManager was not called (because it's None)
            assert task_creator_without_manager.subtask_manager is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_warning_logged_without_manager(
        self, task_creator_without_manager, sample_task, sample_subtasks, caplog
    ):
        """Test warning is logged when SubtaskManager is None."""
        # Arrange
        decomposition_result = {
            "success": True,
            "subtasks": sample_subtasks,
            "shared_conventions": {},
        }

        with (
            patch(
                "src.marcus_mcp.coordinator.decompose_task",
                new=AsyncMock(return_value=decomposition_result),
            ),
            patch.object(
                task_creator_without_manager,
                "_add_subtasks_as_checklist",
                new=AsyncMock(),
            ),
        ):
            # Act
            with caplog.at_level("WARNING"):
                await task_creator_without_manager._decompose_and_add_subtasks(
                    created_tasks=[sample_task], original_tasks=[sample_task]
                )

            # Assert - verify warning was logged
            assert any(
                "SubtaskManager not available" in record.message
                for record in caplog.records
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_success_logged_with_manager(
        self, task_creator_with_manager, sample_task, sample_subtasks, caplog
    ):
        """Test success message is logged when subtasks are registered."""
        # Arrange
        decomposition_result = {
            "success": True,
            "subtasks": sample_subtasks,
            "shared_conventions": {},
        }

        with (
            patch(
                "src.marcus_mcp.coordinator.decompose_task",
                new=AsyncMock(return_value=decomposition_result),
            ),
            patch.object(
                task_creator_with_manager, "_add_subtasks_as_checklist", new=AsyncMock()
            ),
        ):
            # Act
            with caplog.at_level("INFO"):
                await task_creator_with_manager._decompose_and_add_subtasks(
                    created_tasks=[sample_task], original_tasks=[sample_task]
                )

            # Assert - verify success was logged with correct count
            assert any(
                "Registered 4 subtasks with SubtaskManager" in record.message
                for record in caplog.records
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_shared_conventions_included_in_metadata(
        self,
        task_creator_with_manager,
        sample_task,
        sample_subtasks,
        mock_subtask_manager,
    ):
        """Test shared conventions are included in SubtaskMetadata."""
        # Arrange
        shared_conventions = {
            "code_style": "PEP8",
            "testing_framework": "pytest",
        }
        decomposition_result = {
            "success": True,
            "subtasks": sample_subtasks,
            "shared_conventions": shared_conventions,
        }

        with (
            patch(
                "src.marcus_mcp.coordinator.decompose_task",
                new=AsyncMock(return_value=decomposition_result),
            ),
            patch.object(
                task_creator_with_manager, "_add_subtasks_as_checklist", new=AsyncMock()
            ),
        ):
            # Act
            await task_creator_with_manager._decompose_and_add_subtasks(
                created_tasks=[sample_task], original_tasks=[sample_task]
            )

            # Assert
            call_args = mock_subtask_manager.add_subtasks.call_args
            metadata = call_args[1]["metadata"]

            assert hasattr(metadata, "shared_conventions")
            assert metadata.shared_conventions == shared_conventions

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_empty_subtasks_list_handled(
        self, task_creator_with_manager, sample_task, mock_subtask_manager
    ):
        """Test empty subtasks list is handled gracefully."""
        # Arrange - decompose_task returns empty list
        decomposition_result = {
            "success": True,
            "subtasks": [],
            "shared_conventions": {},
        }

        with (
            patch(
                "src.marcus_mcp.coordinator.decompose_task",
                new=AsyncMock(return_value=decomposition_result),
            ),
            patch.object(
                task_creator_with_manager, "_add_subtasks_as_checklist", new=AsyncMock()
            ),
        ):
            # Act
            await task_creator_with_manager._decompose_and_add_subtasks(
                created_tasks=[sample_task], original_tasks=[sample_task]
            )

            # Assert - SubtaskManager should still be called but with empty list
            assert mock_subtask_manager.add_subtasks.called
            call_args = mock_subtask_manager.add_subtasks.call_args
            assert len(call_args[1]["subtasks"]) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_checklist_items_still_created(
        self, task_creator_with_manager, sample_task, sample_subtasks
    ):
        """Test checklist items are still created in addition to registration."""
        # Arrange
        decomposition_result = {
            "success": True,
            "subtasks": sample_subtasks,
            "shared_conventions": {},
        }

        mock_checklist = AsyncMock()
        with (
            patch(
                "src.marcus_mcp.coordinator.decompose_task",
                new=AsyncMock(return_value=decomposition_result),
            ),
            patch.object(
                task_creator_with_manager, "_add_subtasks_as_checklist", mock_checklist
            ),
        ):
            # Act
            await task_creator_with_manager._decompose_and_add_subtasks(
                created_tasks=[sample_task], original_tasks=[sample_task]
            )

            # Assert - verify _add_subtasks_as_checklist was called
            assert mock_checklist.called
            call_args = mock_checklist.call_args
            assert call_args[0][0] == "task-123"  # parent_card_id
            assert call_args[0][1] == sample_subtasks  # subtasks


class TestNaturalLanguageProjectCreatorIntegration:
    """Integration tests for NaturalLanguageProjectCreator with subtask_manager."""

    @pytest.fixture
    def mock_state(self):
        """Create mock state with all required components."""
        mock = Mock()
        mock.kanban_client = Mock()
        mock.kanban_client.create_task = AsyncMock(return_value=Mock(id="task-123"))
        mock.kanban_client.add_checklist_item = AsyncMock()
        mock.ai_engine = Mock()
        mock.subtask_manager = Mock()
        mock.subtask_manager.add_subtasks = Mock()
        return mock

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_project_creator_receives_subtask_manager(self, mock_state):
        """Test NaturalLanguageProjectCreator receives subtask_manager from state."""
        # Arrange
        from src.integrations.nlp_tools import NaturalLanguageProjectCreator

        # Act
        creator = NaturalLanguageProjectCreator(
            kanban_client=mock_state.kanban_client,
            ai_engine=mock_state.ai_engine,
            subtask_manager=mock_state.subtask_manager,
        )

        # Assert
        assert creator.subtask_manager is not None
        assert creator.subtask_manager == mock_state.subtask_manager

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_pipeline_tracked_creator_receives_subtask_manager(self, mock_state):
        """Test PipelineTrackedProjectCreator receives subtask_manager."""
        # Arrange
        from src.integrations.pipeline_tracked_nlp import PipelineTrackedProjectCreator
        from src.visualization.shared_pipeline_events import SharedPipelineVisualizer

        mock_visualizer = Mock(spec=SharedPipelineVisualizer)

        # Act
        creator = PipelineTrackedProjectCreator(
            kanban_client=mock_state.kanban_client,
            ai_engine=mock_state.ai_engine,
            pipeline_visualizer=mock_visualizer,
            subtask_manager=mock_state.subtask_manager,
        )

        # Assert
        assert creator.creator.subtask_manager is not None
        assert creator.creator.subtask_manager == mock_state.subtask_manager
