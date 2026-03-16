"""
Unit tests for project_management tools with MarcusConfig dataclass.

Tests that project management tools correctly access MarcusConfig dataclass
attributes instead of using dictionary .get() methods. This prevents
AttributeError regressions from PR #162.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.config.marcus_config import KanbanSettings, MarcusConfig


class TestProjectManagementWithMarcusConfig:
    """Test suite for project_management tools with MarcusConfig dataclass."""

    @pytest.fixture
    def mock_marcus_config(self):
        """Create a real MarcusConfig instance for testing.

        This ensures tests use actual dataclass attributes,
        not dictionary .get() methods.
        """
        config = MarcusConfig()
        # Set Planka config
        config.kanban = KanbanSettings(
            provider="planka",
            planka_base_url="http://localhost:3333",
            planka_email="demo@demo.demo",
            planka_password="demo",
        )
        return config

    @pytest.fixture
    def mock_server(self, mock_marcus_config):
        """Create mock server with real MarcusConfig."""
        server = Mock()
        server.config = mock_marcus_config
        # Mock project registry
        server.project_registry = Mock()
        server.project_registry.list_projects = AsyncMock(return_value=[])
        server.project_registry.delete_project = AsyncMock()
        return server

    @pytest.mark.asyncio
    async def test_discover_planka_accesses_kanban_config(self, mock_server):
        """Test discover_planka_projects uses config.kanban, not .get('planka')."""
        from src.marcus_mcp.tools.project_management import discover_planka_projects

        with patch("src.integrations.providers.planka.Planka") as mock_planka_class:
            mock_planka = Mock()
            mock_planka.client = Mock()
            mock_planka.client.get_projects = AsyncMock(return_value=[])
            mock_planka.connect = AsyncMock()
            mock_planka.disconnect = AsyncMock()
            mock_planka_class.return_value = mock_planka

            # This should NOT raise AttributeError: 'MarcusConfig' has no attribute 'get'
            result = await discover_planka_projects(mock_server, {"auto_sync": False})

            assert result["success"] is True
            # Verify Planka was initialized with correct config dict
            call_args = mock_planka_class.call_args[0][0]
            assert call_args["base_url"] == "http://localhost:3333"
            assert call_args["email"] == "demo@demo.demo"
            assert call_args["password"] == "demo"

    @pytest.mark.asyncio
    async def test_discover_planka_missing_config(self):
        """Test discover_planka_projects handles missing Planka config."""
        from src.marcus_mcp.tools.project_management import discover_planka_projects

        # Create config with empty Planka settings
        config = MarcusConfig()
        config.kanban = KanbanSettings(
            provider="planka",
            planka_base_url="",  # Empty base_url
            planka_email="",
            planka_password="",
        )

        server = Mock()
        server.config = config

        result = await discover_planka_projects(server, {})

        assert result["success"] is False
        assert "not configured" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_select_project_accesses_auto_sync_with_getattr(self, mock_server):
        """Test select_project uses getattr for auto_sync_projects attribute."""
        from src.marcus_mcp.tools.project_management import select_project

        # Set auto_sync_projects attribute
        mock_server.config.auto_sync_projects = True

        # Mock find_or_create_project to return not_found
        with patch(
            "src.marcus_mcp.tools.project_management.find_or_create_project"
        ) as mock_find:
            mock_find.return_value = {"action": "not_found"}

            # This should NOT raise AttributeError
            result = await select_project(mock_server, {"name": "NonexistentProject"})

            assert result["success"] is False
            # Should include auto_sync hint since auto_sync_projects is True
            assert "auto_sync" in result["hint"].lower()

    @pytest.mark.asyncio
    async def test_select_project_handles_missing_auto_sync_attr(self, mock_server):
        """Test select_project handles missing auto_sync_projects with getattr."""
        from src.marcus_mcp.tools.project_management import select_project

        # Don't set auto_sync_projects - test that getattr default works
        # Remove the attribute if it exists
        if hasattr(mock_server.config, "auto_sync_projects"):
            delattr(mock_server.config, "auto_sync_projects")

        with patch(
            "src.marcus_mcp.tools.project_management.find_or_create_project"
        ) as mock_find:
            mock_find.return_value = {"action": "not_found"}

            # This should NOT raise AttributeError due to getattr with default
            result = await select_project(mock_server, {"name": "NonexistentProject"})

            assert result["success"] is False
            # Should NOT include auto_sync hint since auto_sync is False (default)
            assert "auto_sync" not in result["hint"].lower()

    @pytest.mark.asyncio
    async def test_config_get_raises_attribute_error(self):
        """Test that calling .get() on MarcusConfig raises AttributeError.

        This test documents the bug that was fixed - calling .get()
        on a dataclass raises AttributeError.
        """
        config = MarcusConfig()

        # This should raise AttributeError
        with pytest.raises(AttributeError, match="has no attribute 'get'"):
            config.get("planka", {})

        # This should also raise
        with pytest.raises(AttributeError, match="has no attribute 'get'"):
            config.get("auto_sync_projects", False)

    def test_kanban_settings_has_required_attributes(self):
        """Test that KanbanSettings has all required Planka attributes."""
        kanban_config = KanbanSettings(
            provider="planka",
            planka_base_url="http://test",
            planka_email="test@test.com",
            planka_password="testpass",
        )

        # Verify attributes exist and can be accessed
        assert kanban_config.planka_base_url == "http://test"
        assert kanban_config.planka_email == "test@test.com"
        assert kanban_config.planka_password == "testpass"

        # Verify .get() doesn't exist
        with pytest.raises(AttributeError):
            kanban_config.get("planka_base_url")
