"""
Unit tests for discover_planka_projects MCP tool.

Tests automatic discovery of projects from Planka.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestDiscoverPlankaProjects:
    """Test suite for discover_planka_projects tool"""

    @pytest.fixture
    def mock_server(self):
        """Create mock server"""
        server = Mock()
        server.config = Mock()
        server.config.get = Mock(
            return_value={
                "base_url": "http://localhost:3333",
                "email": "demo@demo.demo",
            }
        )
        # Mock project registry with async methods
        server.project_registry = Mock()
        server.project_registry.list_projects = AsyncMock(return_value=[])
        server.project_registry.delete_project = AsyncMock()
        return server

    @pytest.fixture
    def mock_planka_projects(self):
        """Sample Planka projects (without boards - boards fetched separately)"""
        return [
            {
                "id": "proj-1",
                "name": "1st Project",
            },
            {
                "id": "proj-2",
                "name": "Backend API",
            },
        ]

    @pytest.fixture
    def mock_boards_responses(self):
        """Mock board responses for each project"""
        return {
            "proj-1": [{"id": "board-1", "name": "Main Board"}],
            "proj-2": [
                {"id": "board-2a", "name": "Sprint 1"},
                {"id": "board-2b", "name": "Sprint 2"},
            ],
        }

    async def test_discover_without_auto_sync(
        self, mock_server, mock_planka_projects, mock_boards_responses
    ):
        """Test discovering projects without auto-syncing"""
        from src.marcus_mcp.tools.project_management import discover_planka_projects

        with patch("src.integrations.providers.planka.Planka") as mock_planka_class:
            mock_planka = Mock()
            mock_planka.client = Mock()
            mock_planka.client.get_projects = AsyncMock(
                return_value=mock_planka_projects
            )

            # Mock get_boards_for_project to return boards for each project
            async def get_boards_side_effect(project_id):
                return mock_boards_responses.get(project_id, [])

            mock_planka.client.get_boards_for_project = AsyncMock(
                side_effect=get_boards_side_effect
            )
            mock_planka.connect = AsyncMock()
            mock_planka.disconnect = AsyncMock()
            mock_planka_class.return_value = mock_planka

            result = await discover_planka_projects(mock_server, {"auto_sync": False})

            assert result["success"] is True
            assert result["discovered_count"] == 3  # 1 from proj-1, 2 from proj-2
            assert len(result["projects"]) == 3
            assert "sync_result" not in result

            # Check project format
            project = result["projects"][0]
            assert "name" in project
            assert "provider" in project
            assert project["provider"] == "planka"
            assert "config" in project
            assert "project_id" in project["config"]
            assert "board_id" in project["config"]

    async def test_discover_with_auto_sync(
        self, mock_server, mock_planka_projects, mock_boards_responses
    ):
        """Test discovering projects with auto-sync enabled"""
        from src.marcus_mcp.tools.project_management import discover_planka_projects

        with patch("src.integrations.providers.planka.Planka") as mock_planka_class:
            mock_planka = Mock()
            mock_planka.client = Mock()
            mock_planka.client.get_projects = AsyncMock(
                return_value=mock_planka_projects
            )

            # Mock get_boards_for_project to return boards for each project
            async def get_boards_side_effect(project_id):
                return mock_boards_responses.get(project_id, [])

            mock_planka.client.get_boards_for_project = AsyncMock(
                side_effect=get_boards_side_effect
            )
            mock_planka.connect = AsyncMock()
            mock_planka.disconnect = AsyncMock()
            mock_planka_class.return_value = mock_planka

            # Mock sync_projects
            with patch(
                "src.marcus_mcp.tools.project_management.sync_projects"
            ) as mock_sync:
                mock_sync.return_value = {
                    "success": True,
                    "summary": {"added": 3, "updated": 0, "skipped": 0},
                }

                result = await discover_planka_projects(
                    mock_server, {"auto_sync": True}
                )

                assert result["success"] is True
                assert result["discovered_count"] == 3
                assert "sync_result" in result
                assert result["sync_result"]["success"] is True
                mock_sync.assert_called_once()

    async def test_discover_no_planka_config(self, mock_server):
        """Test discovery fails gracefully when Planka not configured"""
        from src.marcus_mcp.tools.project_management import discover_planka_projects

        mock_server.config.get = Mock(return_value={})

        result = await discover_planka_projects(mock_server, {})

        assert result["success"] is False
        assert "not configured" in result["error"].lower()

    async def test_discover_handles_errors(self, mock_server):
        """Test discovery handles Planka connection errors"""
        from src.marcus_mcp.tools.project_management import discover_planka_projects

        with patch("src.integrations.providers.planka.Planka") as mock_planka_class:
            mock_planka = Mock()
            mock_planka.connect = AsyncMock(side_effect=Exception("Connection failed"))
            mock_planka.disconnect = AsyncMock()
            mock_planka_class.return_value = mock_planka

            result = await discover_planka_projects(mock_server, {})

            assert result["success"] is False
            assert "Connection failed" in result["error"]

    async def test_discover_removes_stale_boards(
        self, mock_server, mock_planka_projects, mock_boards_responses
    ):
        """Test that discovery removes boards from registry that no longer exist in Planka"""
        from src.core.project_registry import ProjectConfig
        from src.marcus_mcp.tools.project_management import discover_planka_projects

        # Setup mock project registry with stale board
        mock_registry = Mock()
        mock_registry.list_projects = AsyncMock(
            return_value=[
                ProjectConfig(
                    id="stale-1",
                    name="Stale Project",
                    provider="planka",
                    provider_config={
                        "project_id": "old-proj",
                        "board_id": "stale-board-999",  # This board doesn't exist
                    },
                    created_at=datetime.now(),
                    last_used=datetime.now(),
                    tags=["discovered"],
                ),
                ProjectConfig(
                    id="valid-1",
                    name="Valid Project",
                    provider="planka",
                    provider_config={
                        "project_id": "proj-1",
                        "board_id": "board-1",  # This board exists
                    },
                    created_at=datetime.now(),
                    last_used=datetime.now(),
                    tags=["discovered"],
                ),
            ]
        )
        mock_registry.delete_project = AsyncMock()
        mock_server.project_registry = mock_registry

        with patch("src.integrations.providers.planka.Planka") as mock_planka_class:
            mock_planka = Mock()
            mock_planka.client = Mock()
            mock_planka.client.get_projects = AsyncMock(
                return_value=mock_planka_projects
            )

            async def get_boards_side_effect(project_id):
                return mock_boards_responses.get(project_id, [])

            mock_planka.client.get_boards_for_project = AsyncMock(
                side_effect=get_boards_side_effect
            )
            mock_planka.connect = AsyncMock()
            mock_planka.disconnect = AsyncMock()
            mock_planka_class.return_value = mock_planka

            result = await discover_planka_projects(mock_server, {"auto_sync": False})

            assert result["success"] is True
            assert "stale_removed" in result

            # Verify stale board was removed
            stale_result = result["stale_removed"]
            assert stale_result["removed_count"] == 1
            assert len(stale_result["removed"]) == 1
            assert stale_result["removed"][0]["board_id"] == "stale-board-999"

            # Verify delete was called for the stale board
            mock_registry.delete_project.assert_called_once_with("stale-1")
