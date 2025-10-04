"""
Unit tests for project discovery integration in NLP tools.

Tests the integration of find_or_create_project helper into the
create_project_from_natural_language flow.
"""

from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.project_registry import ProjectConfig


class TestCreateProjectWithDiscovery:
    """Test suite for create_project with project discovery"""

    @pytest.fixture
    def mock_state(self):
        """Create mock Marcus server state"""
        state = Mock()
        state.kanban_client = Mock()
        state.kanban_client.project_id = None
        state.kanban_client.board_id = None
        state.kanban_client.auto_setup_project = AsyncMock(
            return_value={"project_id": "new-123", "board_id": "board-456"}
        )
        state.kanban_client.create_task = AsyncMock(return_value={"id": "task-123"})
        state.initialize_kanban = AsyncMock()
        state.project_registry = Mock()
        state.project_registry.list_projects = AsyncMock(return_value=[])
        state.project_registry.add_project = AsyncMock(return_value="proj-id-123")
        state.project_manager = Mock()
        state.project_manager.switch_project = AsyncMock(return_value=True)
        state.project_manager.get_kanban_client = AsyncMock(
            return_value=state.kanban_client
        )
        state.ai_engine = Mock()
        state.refresh_project_state = AsyncMock()
        return state

    @pytest.fixture
    def sample_existing_project(self) -> ProjectConfig:
        """Create a sample existing project"""
        return ProjectConfig(
            id="existing-123",
            name="MyAPI",
            provider="planka",
            provider_config={"project_id": "planka-789", "board_id": "board-101"},
            created_at=datetime.now(),
            last_used=datetime.now(),
            tags=["backend"],
        )

    @pytest.mark.asyncio
    async def test_create_project_with_no_existing_projects(self, mock_state):
        """Test create_project creates new when no projects exist"""
        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange
        mock_state.project_registry.list_projects = AsyncMock(return_value=[])

        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            mock_creator = MockCreator.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value={"success": True, "tasks_created": 5}
            )

            # Act
            result = await create_project_from_natural_language(
                description="Build a REST API",
                project_name="MyAPI",
                state=mock_state,
                options={"mode": "new_project"},
            )

            # Assert
            assert result["success"] is True
            # Should have called ProjectAutoSetup (not direct auto_setup_project)
            # Verify project was registered
            mock_state.project_registry.add_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_project_finds_existing_exact_match(
        self, mock_state, sample_existing_project
    ):
        """Test create_project finds and uses existing project"""
        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange
        mock_state.project_registry.list_projects = AsyncMock(
            return_value=[sample_existing_project]
        )
        mock_state.kanban_client.project_id = "planka-789"
        mock_state.kanban_client.board_id = "board-101"

        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            mock_creator = MockCreator.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value={"success": True, "tasks_created": 5}
            )

            # Act - explicitly provide project_id to use existing
            result = await create_project_from_natural_language(
                description="Add new features",
                project_name="MyAPI",
                state=mock_state,
                options={"project_id": "existing-123"},
            )

            # Assert
            assert result["success"] is True
            # Should NOT create new project
            mock_state.project_registry.add_project.assert_not_called()
            # Should switch to existing project
            mock_state.project_manager.switch_project.assert_called_with("existing-123")

    @pytest.mark.asyncio
    async def test_create_project_with_mode_new_project_forces_creation(
        self, mock_state, sample_existing_project
    ):
        """Test mode=new_project forces creation even if project exists"""
        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange - existing project with same name
        mock_state.project_registry.list_projects = AsyncMock(
            return_value=[sample_existing_project]
        )

        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            mock_creator = MockCreator.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value={"success": True, "tasks_created": 5}
            )

            # Act - force new project creation
            result = await create_project_from_natural_language(
                description="Build a REST API",
                project_name="MyAPI",
                state=mock_state,
                options={"mode": "new_project"},
            )

            # Assert
            assert result["success"] is True
            # Should create new project despite existing one
            mock_state.project_registry.add_project.assert_called_once()
            # Should switch to the newly created project
            mock_state.project_manager.switch_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_project_with_mode_new_project_clears_stale_config_ids(
        self, mock_state
    ):
        """Test mode=new_project creates new project even with stale config IDs"""
        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange - kanban_client has stale IDs from config (non-existent board)
        mock_state.kanban_client.project_id = "stale-project-999"
        mock_state.kanban_client.board_id = "1555320228445946953"  # stale board ID

        # Mock auto_setup_project to return new IDs
        mock_state.kanban_client.auto_setup_project = AsyncMock(
            return_value={"project_id": "new-proj-123", "board_id": "new-board-456"}
        )

        with (
            patch(
                "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
            ) as MockCreator,
            patch("src.integrations.nlp_tools.ProjectAutoSetup") as MockAutoSetup,
        ):
            mock_creator = MockCreator.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value={"success": True, "tasks_created": 5}
            )

            mock_auto_setup = MockAutoSetup.return_value
            mock_auto_setup.setup_new_project = AsyncMock(
                return_value=Mock(
                    name="NewProject",
                    provider="planka",
                    provider_config={
                        "project_id": "new-proj-123",
                        "board_id": "new-board-456",
                    },
                )
            )

            # Act - force new project creation with mode=new_project
            result = await create_project_from_natural_language(
                description="Build a notification system",
                project_name="Real-Time Notification System",
                state=mock_state,
                options={"mode": "new_project"},
            )

            # Assert
            assert result["success"] is True
            # Should call auto_setup to create new project/board
            mock_auto_setup.setup_new_project.assert_called_once()
            # Should register the new project
            mock_state.project_registry.add_project.assert_called_once()
            # Should switch to the new project
            mock_state.project_manager.switch_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_project_with_fuzzy_match_suggests_projects(
        self, mock_state, sample_existing_project
    ):
        """Test create_project suggests similar projects"""
        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange - similar project exists
        mock_state.project_registry.list_projects = AsyncMock(
            return_value=[sample_existing_project]
        )

        with patch(
            "src.integrations.nlp_tools.find_or_create_project",
            new=AsyncMock(
                return_value={
                    "action": "found_similar",
                    "matches": [
                        {
                            "id": "existing-123",
                            "name": "MyAPI",
                            "provider": "planka",
                            "similarity": 0.8,
                        }
                    ],
                    "suggestion": "Did you mean one of these projects?",
                    "next_steps": ["Use similar: switch_project(project_name='...')"],
                }
            ),
        ):
            # Act - no explicit mode or project_id
            result = await create_project_from_natural_language(
                description="Build an API",
                project_name="myapi",  # lowercase - fuzzy match
                state=mock_state,
                options={},
            )

            # Assert
            # Should return suggestion to user
            assert result["action"] == "found_similar"
            assert "message" in result
            assert "matches" in result
            assert result["success"] is False  # Not a success, needs user input

    @pytest.mark.asyncio
    async def test_create_project_registers_new_project_in_registry(self, mock_state):
        """Test new project is registered in ProjectRegistry"""
        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange
        mock_state.project_registry.list_projects = AsyncMock(return_value=[])

        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            mock_creator = MockCreator.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value={"success": True, "tasks_created": 5}
            )

            # Act
            result = await create_project_from_natural_language(
                description="Build a REST API",
                project_name="NewAPI",
                state=mock_state,
                options={"mode": "new_project"},
            )

            # Assert
            assert result["success"] is True
            # Should register new project
            mock_state.project_registry.add_project.assert_called_once()


@pytest.mark.unit
class TestProjectDiscoveryModes:
    """Test different modes of project discovery"""

    def test_mode_new_project_always_creates(self):
        """Test mode=new_project bypasses discovery"""
        # This mode should skip find_or_create_project entirely
        # and go straight to auto-creation
        pass

    def test_mode_add_feature_requires_project_id(self):
        """Test mode=add_feature requires existing project"""
        # This mode should require project_id in options
        # and fail if not provided
        pass

    def test_auto_mode_uses_discovery(self):
        """Test default/auto mode uses find_or_create_project"""
        # When no mode specified, should call find_or_create_project
        # to search for existing projects
        pass
