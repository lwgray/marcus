"""
Unit tests for project_auto_setup module.

Tests provider-agnostic project auto-setup functionality.
"""

from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.project_registry import ProjectConfig
from src.integrations.project_auto_setup import ProjectAutoSetup


class TestProjectAutoSetup:
    """Test suite for ProjectAutoSetup class"""

    @pytest.fixture
    def auto_setup(self):
        """Create ProjectAutoSetup instance"""
        return ProjectAutoSetup()

    @pytest.fixture
    def mock_kanban_client(self):
        """Create mock Kanban client with auto_setup_project"""
        client = Mock()
        client.auto_setup_project = AsyncMock(
            return_value={"project_id": "planka-123", "board_id": "board-456"}
        )
        client.project_id = None
        client.board_id = None
        return client

    @pytest.mark.asyncio
    async def test_setup_planka_project_creates_config(
        self, auto_setup, mock_kanban_client
    ):
        """Test Planka project setup creates ProjectConfig"""
        # Arrange
        project_name = "TestProject"
        options = {
            "planka_project_name": "Test Planka Project",
            "planka_board_name": "Development Board",
        }

        # Act
        result = await auto_setup.setup_planka_project(
            kanban_client=mock_kanban_client,
            project_name=project_name,
            options=options,
        )

        # Assert
        assert isinstance(result, ProjectConfig)
        assert result.name == project_name
        assert result.provider == "planka"
        assert result.provider_config["project_id"] == "planka-123"
        assert result.provider_config["board_id"] == "board-456"

        # Verify auto_setup_project was called with correct params
        mock_kanban_client.auto_setup_project.assert_called_once_with(
            project_name="Test Planka Project", board_name="Development Board"
        )

    @pytest.mark.asyncio
    async def test_setup_planka_project_uses_defaults(
        self, auto_setup, mock_kanban_client
    ):
        """Test Planka setup uses default names when not provided"""
        # Arrange
        project_name = "MyAPI"
        options = {}  # No planka-specific options

        # Act
        result = await auto_setup.setup_planka_project(
            kanban_client=mock_kanban_client,
            project_name=project_name,
            options=options,
        )

        # Assert
        # Should default to project_name and "Main Board"
        mock_kanban_client.auto_setup_project.assert_called_once_with(
            project_name="MyAPI", board_name="Main Board"
        )

    @pytest.mark.asyncio
    async def test_setup_planka_project_handles_error(
        self, auto_setup, mock_kanban_client
    ):
        """Test Planka setup handles errors gracefully"""
        # Arrange
        mock_kanban_client.auto_setup_project = AsyncMock(
            side_effect=Exception("Planka API error")
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await auto_setup.setup_planka_project(
                kanban_client=mock_kanban_client,
                project_name="TestProject",
                options={},
            )

        assert "Planka API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_setup_new_project_dispatches_to_planka(self, auto_setup):
        """Test setup_new_project dispatches to correct provider"""
        # Arrange
        mock_kanban_client = Mock()
        mock_kanban_client.auto_setup_project = AsyncMock(
            return_value={"project_id": "123", "board_id": "456"}
        )

        with patch.object(
            auto_setup, "setup_planka_project", new=AsyncMock()
        ) as mock_setup:
            mock_setup.return_value = ProjectConfig(
                id="",
                name="Test",
                provider="planka",
                provider_config={"project_id": "123", "board_id": "456"},
            )

            # Act
            result = await auto_setup.setup_new_project(
                kanban_client=mock_kanban_client,
                provider="planka",
                project_name="TestProject",
                options={},
            )

            # Assert
            mock_setup.assert_called_once()
            assert result.provider == "planka"

    @pytest.mark.asyncio
    async def test_setup_new_project_github_not_implemented(self, auto_setup):
        """Test GitHub setup raises NotImplementedError"""
        # Arrange
        mock_kanban_client = Mock()

        # Act & Assert
        with pytest.raises(NotImplementedError) as exc_info:
            await auto_setup.setup_new_project(
                kanban_client=mock_kanban_client,
                provider="github",
                project_name="TestProject",
                options={},
            )

        assert "GitHub" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_setup_new_project_linear_not_implemented(self, auto_setup):
        """Test Linear setup raises NotImplementedError"""
        # Arrange
        mock_kanban_client = Mock()

        # Act & Assert
        with pytest.raises(NotImplementedError) as exc_info:
            await auto_setup.setup_new_project(
                kanban_client=mock_kanban_client,
                provider="linear",
                project_name="TestProject",
                options={},
            )

        assert "Linear" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_setup_new_project_invalid_provider(self, auto_setup):
        """Test invalid provider raises ValueError"""
        # Arrange
        mock_kanban_client = Mock()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await auto_setup.setup_new_project(
                kanban_client=mock_kanban_client,
                provider="invalid",
                project_name="TestProject",
                options={},
            )

        assert "Unsupported provider" in str(exc_info.value)


@pytest.mark.unit
class TestProjectAutoSetupHelpers:
    """Test helper methods for project auto-setup"""

    def test_extract_planka_options(self):
        """Test extracting Planka-specific options from general options dict"""
        # This will be implemented when we add option extraction logic
        pass

    def test_validate_project_config(self):
        """Test validation of created ProjectConfig"""
        # This will be implemented if we add validation logic
        pass
