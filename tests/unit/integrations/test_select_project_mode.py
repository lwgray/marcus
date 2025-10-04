"""
Unit tests for select_project mode in create_project.

Tests the ability for agents to select existing projects without creating new tasks.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.project_registry import ProjectConfig


class TestSelectProjectMode:
    """Test suite for select_project mode"""

    @pytest.fixture
    def mock_state(self):
        """Create mock Marcus server state"""
        state = Mock()
        state.kanban_client = Mock()
        state.kanban_client.project_id = "planka-123"
        state.kanban_client.board_id = "board-456"
        state.initialize_kanban = AsyncMock()
        state.project_registry = Mock()
        state.project_registry.get_active_project = AsyncMock()
        state.project_manager = Mock()
        state.project_manager.switch_project = AsyncMock(return_value=True)
        state.project_manager.get_kanban_client = AsyncMock(
            return_value=state.kanban_client
        )
        state.project_tasks = []  # Empty task list
        return state

    @pytest.fixture
    def sample_project(self) -> ProjectConfig:
        """Create a sample existing project"""
        return ProjectConfig(
            id="proj-123",
            name="ExistingAPI",
            provider="planka",
            provider_config={"project_id": "planka-123", "board_id": "board-456"},
            created_at=datetime.now(),
            last_used=datetime.now(),
            tags=["backend"],
        )

    @pytest.mark.asyncio
    async def test_select_project_by_id(self, mock_state, sample_project):
        """Test selecting project with explicit project_id"""
        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange
        mock_state.project_registry.get_active_project = AsyncMock(
            return_value=sample_project
        )

        # Act
        result = await create_project_from_natural_language(
            description="",  # Not used in select mode
            project_name="ExistingAPI",
            state=mock_state,
            options={"mode": "select_project", "project_id": "proj-123"},
        )

        # Assert
        assert result["success"] is True
        assert result["action"] == "selected_existing"
        assert result["project"]["name"] == "ExistingAPI"
        assert "ready to work" in result["message"]
        mock_state.project_manager.switch_project.assert_called_once_with("proj-123")

    @pytest.mark.asyncio
    async def test_select_project_by_name_exact_match(self, mock_state, sample_project):
        """Test selecting project by name with exact match"""
        from unittest.mock import patch

        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange
        mock_state.project_registry.list_projects = AsyncMock(
            return_value=[sample_project]
        )

        with patch(
            "src.integrations.nlp_tools.find_or_create_project",
            new=AsyncMock(
                return_value={
                    "action": "found_existing",
                    "project": {
                        "id": "proj-123",
                        "name": "ExistingAPI",
                        "provider": "planka",
                    },
                }
            ),
        ):
            # Act
            result = await create_project_from_natural_language(
                description="",
                project_name="ExistingAPI",
                state=mock_state,
                options={"mode": "select_project"},
            )

            # Assert
            assert result["success"] is True
            assert result["action"] == "selected_existing"
            mock_state.project_manager.switch_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_project_fuzzy_match_returns_suggestions(
        self, mock_state, sample_project
    ):
        """Test select_project with fuzzy matches returns suggestions"""
        from unittest.mock import patch

        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange
        with patch(
            "src.integrations.nlp_tools.find_or_create_project",
            new=AsyncMock(
                return_value={
                    "action": "found_similar",
                    "matches": [
                        {"id": "proj-123", "name": "ExistingAPI", "similarity": 0.8}
                    ],
                    "suggestion": "Did you mean one of these projects?",
                    "next_steps": ["Specify exact project_id"],
                }
            ),
        ):
            # Act
            result = await create_project_from_natural_language(
                description="",
                project_name="existingapi",  # Lowercase - fuzzy match
                state=mock_state,
                options={"mode": "select_project"},
            )

            # Assert
            assert result["success"] is False
            assert result["action"] == "found_similar"
            assert len(result["matches"]) == 1
            assert "specify exact project_id" in result["hint"].lower()

    @pytest.mark.asyncio
    async def test_select_project_not_found(self, mock_state):
        """Test select_project when project doesn't exist"""
        from unittest.mock import patch

        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange
        with patch(
            "src.integrations.nlp_tools.find_or_create_project",
            new=AsyncMock(
                return_value={"action": "not_found", "next_steps": ["Create project"]}
            ),
        ):
            # Act
            result = await create_project_from_natural_language(
                description="",
                project_name="NonExistentProject",
                state=mock_state,
                options={"mode": "select_project"},
            )

            # Assert
            assert result["success"] is False
            assert result["action"] == "not_found"
            assert "not found" in result["message"]
            assert "list_projects" in result["hint"]

    @pytest.mark.asyncio
    async def test_select_project_does_not_create_tasks(
        self, mock_state, sample_project
    ):
        """Test that select_project mode does NOT create new tasks"""
        from unittest.mock import patch

        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange
        mock_state.project_registry.get_active_project = AsyncMock(
            return_value=sample_project
        )

        # Act
        result = await create_project_from_natural_language(
            description="Add lots of features",  # Should be ignored
            project_name="ExistingAPI",
            state=mock_state,
            options={"mode": "select_project", "project_id": "proj-123"},
        )

        # Assert
        assert result["success"] is True
        # Should NOT have tasks_created field
        assert "tasks_created" not in result
        # Should have selected message
        assert "ready to work" in result["message"]

    @pytest.mark.asyncio
    async def test_select_project_returns_task_count(self, mock_state, sample_project):
        """Test that select_project returns existing task count"""
        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange
        mock_state.project_registry.get_active_project = AsyncMock(
            return_value=sample_project
        )
        mock_state.project_tasks = [Mock(), Mock(), Mock()]  # 3 existing tasks

        # Act
        result = await create_project_from_natural_language(
            description="",
            project_name="ExistingAPI",
            state=mock_state,
            options={"mode": "select_project", "project_id": "proj-123"},
        )

        # Assert
        assert result["success"] is True
        assert result["project"]["task_count"] == 3


@pytest.mark.unit
class TestSelectProjectWorkflow:
    """Test complete agent workflow with select_project"""

    @pytest.mark.asyncio
    async def test_agent_workflow_select_then_work(self):
        """
        Test typical agent workflow:
        1. List projects
        2. Select project with mode=select_project
        3. Request tasks from that project
        """
        from unittest.mock import Mock, patch

        from src.integrations.nlp_tools import create_project_from_natural_language

        # Arrange
        mock_state = Mock()
        mock_state.project_registry = Mock()
        mock_state.project_manager = Mock()
        mock_state.project_manager.switch_project = AsyncMock(return_value=True)
        mock_state.project_manager.get_kanban_client = AsyncMock(
            return_value=Mock(project_id="p1", board_id="b1")
        )
        mock_state.project_registry.get_active_project = AsyncMock(
            return_value=ProjectConfig(
                id="proj-123",
                name="MyAPI",
                provider="planka",
                provider_config={"project_id": "p1", "board_id": "b1"},
            )
        )
        mock_state.project_tasks = [Mock(), Mock()]  # 2 tasks
        mock_state.kanban_client = Mock()

        with patch(
            "src.integrations.nlp_tools.find_or_create_project",
            new=AsyncMock(
                return_value={
                    "action": "found_existing",
                    "project": {"id": "proj-123", "name": "MyAPI"},
                }
            ),
        ):
            # Act - Step 1: Select project
            select_result = await create_project_from_natural_language(
                description="",
                project_name="MyAPI",
                state=mock_state,
                options={"mode": "select_project"},
            )

            # Assert
            assert select_result["success"] is True
            assert select_result["action"] == "selected_existing"
            assert select_result["project"]["task_count"] == 2

            # Now agent can call request_next_task() which will work on this project
            # This simulates the agent workflow
