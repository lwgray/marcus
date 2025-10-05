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
        return server

    @pytest.fixture
    def mock_planka_projects(self):
        """Sample Planka projects"""
        return [
            {
                "id": "proj-1",
                "name": "1st Project",
                "boards": [{"id": "board-1", "name": "Main Board"}],
            },
            {
                "id": "proj-2",
                "name": "Backend API",
                "boards": [
                    {"id": "board-2a", "name": "Sprint 1"},
                    {"id": "board-2b", "name": "Sprint 2"},
                ],
            },
        ]

    async def test_discover_without_auto_sync(self, mock_server, mock_planka_projects):
        """Test discovering projects without auto-syncing"""
        from src.marcus_mcp.tools.project_management import discover_planka_projects

        with patch("src.integrations.providers.planka.Planka") as mock_planka_class:
            mock_planka = Mock()
            mock_planka.client = Mock()
            mock_planka.client.get_projects = AsyncMock(
                return_value=mock_planka_projects
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

    async def test_discover_with_auto_sync(self, mock_server, mock_planka_projects):
        """Test discovering projects with auto-sync enabled"""
        from src.marcus_mcp.tools.project_management import discover_planka_projects

        with patch("src.integrations.providers.planka.Planka") as mock_planka_class:
            mock_planka = Mock()
            mock_planka.client = Mock()
            mock_planka.client.get_projects = AsyncMock(
                return_value=mock_planka_projects
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
