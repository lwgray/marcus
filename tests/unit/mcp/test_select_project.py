"""
Unit tests for select_project MCP tool.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.project_registry import ProjectConfig


@pytest.mark.unit
class TestSelectProject:
    """Test suite for select_project tool"""

    @pytest.fixture
    def mock_server(self):
        """Create mock Marcus server"""
        server = Mock()
        server.project_manager = Mock()
        server.project_manager.switch_project = AsyncMock(return_value=True)
        server.project_manager.get_kanban_client = AsyncMock(return_value=Mock())
        server.project_registry = Mock()
        server.project_tasks = []
        return server

    @pytest.fixture
    def sample_project(self):
        """Create a sample project"""
        return ProjectConfig(
            id="proj-123",
            name="MyAPI",
            provider="planka",
            provider_config={"project_id": "planka-789", "board_id": "board-101"},
            created_at=datetime.now(),
            last_used=datetime.now(),
            tags=["backend"],
        )

    @pytest.mark.asyncio
    async def test_select_project_by_id(self, mock_server, sample_project):
        """Test selecting project by ID"""
        from src.marcus_mcp.tools.project_management import select_project

        # Arrange
        mock_server.project_registry.get_active_project = AsyncMock(
            return_value=sample_project
        )

        # Act
        result = await select_project(mock_server, {"project_id": "proj-123"})

        # Assert
        assert result["success"] is True
        assert result["action"] == "selected_existing"
        assert result["project"]["id"] == "proj-123"
        assert result["project"]["name"] == "MyAPI"
        mock_server.project_manager.switch_project.assert_called_with("proj-123")

    @pytest.mark.asyncio
    async def test_select_project_by_name_exact_match(
        self, mock_server, sample_project
    ):
        """Test selecting project by exact name match"""
        from unittest.mock import patch

        from src.marcus_mcp.tools.project_management import (
            find_or_create_project,
            select_project,
        )

        # Arrange
        mock_server.project_registry.list_projects = AsyncMock(
            return_value=[sample_project]
        )

        with patch(
            "src.marcus_mcp.tools.project_management.find_or_create_project",
            new=AsyncMock(
                return_value={
                    "action": "found_existing",
                    "project": {
                        "id": "proj-123",
                        "name": "MyAPI",
                        "provider": "planka",
                        "task_count": 5,
                    },
                }
            ),
        ):
            # Act
            result = await select_project(mock_server, {"project_name": "MyAPI"})

            # Assert
            assert result["success"] is True
            assert result["action"] == "selected_existing"
            assert result["project"]["name"] == "MyAPI"

    @pytest.mark.asyncio
    async def test_select_project_not_found(self, mock_server):
        """Test selecting non-existent project"""
        from unittest.mock import patch

        from src.marcus_mcp.tools.project_management import select_project

        # Arrange
        with patch(
            "src.marcus_mcp.tools.project_management.find_or_create_project",
            new=AsyncMock(
                return_value={
                    "action": "not_found",
                }
            ),
        ):
            # Act
            result = await select_project(mock_server, {"project_name": "NonExistent"})

            # Assert
            assert result["success"] is False
            assert result["action"] == "not_found"
            assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_select_project_missing_params(self, mock_server):
        """Test selecting project without name or ID"""
        from src.marcus_mcp.tools.project_management import select_project

        # Act
        result = await select_project(mock_server, {})

        # Assert
        assert result["success"] is False
        assert "Either project_name or project_id must be provided" in result["error"]
