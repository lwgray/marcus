"""
Unit tests for sync_projects MCP tool.

Tests the sync_projects functionality that syncs projects
from external providers (like Planka) into Marcus's registry.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.project_registry import ProjectConfig


class TestSyncProjects:
    """Test suite for sync_projects tool"""

    @pytest.fixture
    def mock_server(self):
        """Create mock server with project registry"""
        server = Mock()
        server.project_registry = Mock()
        server.project_registry.list_projects = AsyncMock(return_value=[])
        server.project_registry.add_project = AsyncMock(
            return_value="new-project-id-123"
        )
        server.project_registry.get_project = AsyncMock(return_value=None)
        server.project_registry.remove_project = AsyncMock()
        return server

    @pytest.fixture
    def sample_project_definitions(self):
        """Sample project definitions to sync"""
        return [
            {
                "name": "Project Alpha",
                "provider": "planka",
                "config": {"project_id": "planka-proj-1", "board_id": "board-1"},
            },
            {
                "name": "Project Beta",
                "provider": "planka",
                "config": {"project_id": "planka-proj-2", "board_id": "board-2"},
            },
        ]

    @pytest.fixture
    def existing_project(self):
        """Create an existing project in registry"""
        return ProjectConfig(
            id="existing-id-123",
            name="Existing Project",
            provider="planka",
            provider_config={"project_id": "old-id", "board_id": "old-board"},
            created_at=datetime.now(),
            last_used=datetime.now(),
        )

    async def test_sync_projects_adds_new_projects(
        self, mock_server, sample_project_definitions
    ):
        """Test syncing new projects to empty registry"""
        from src.marcus_mcp.tools.project_management import sync_projects

        result = await sync_projects(
            mock_server, {"projects": sample_project_definitions}
        )

        assert result["success"] is True
        assert result["summary"]["added"] == 2
        assert result["summary"]["updated"] == 0
        assert result["summary"]["skipped"] == 0
        assert len(result["details"]["added"]) == 2
        added_names = [proj["name"] for proj in result["details"]["added"]]
        assert "Project Alpha" in added_names
        assert "Project Beta" in added_names

    async def test_sync_projects_updates_existing(self, mock_server, existing_project):
        """
        Test updating existing project with same provider_config.

        Since duplicate detection now uses provider_config (project_id + board_id),
        only projects with matching provider_config will be updated.
        """
        from src.marcus_mcp.tools.project_management import sync_projects

        # Mock existing project in registry
        mock_server.project_registry.list_projects = AsyncMock(
            return_value=[existing_project]
        )

        # Sync with SAME provider_config but potentially updated name/tags
        updated_definition = [
            {
                "name": "Existing Project - Updated Name",  # Name can change
                "provider": "planka",
                "config": {
                    "project_id": "old-id",  # Same as existing
                    "board_id": "old-board",  # Same as existing
                },
                "tags": ["updated"],
            }
        ]

        result = await sync_projects(mock_server, {"projects": updated_definition})

        assert result["success"] is True
        assert result["summary"]["added"] == 0
        assert result["summary"]["updated"] == 1
        assert result["summary"]["skipped"] == 0
        updated_names = [proj["name"] for proj in result["details"]["updated"]]
        assert "Existing Project - Updated Name" in updated_names

        # Verify the project was actually updated
        assert existing_project.name == "Existing Project - Updated Name"
        assert "updated" in existing_project.tags

    async def test_sync_projects_skips_invalid(self, mock_server):
        """Test that projects without names are skipped"""
        from src.marcus_mcp.tools.project_management import sync_projects

        # Sync with missing name
        invalid_definition = [
            {
                "provider": "planka",
                "config": {"project_id": "123", "board_id": "456"},
            }
        ]

        result = await sync_projects(mock_server, {"projects": invalid_definition})

        assert result["success"] is True
        assert result["summary"]["added"] == 0
        assert result["summary"]["updated"] == 0
        assert result["summary"]["skipped"] == 1
        assert "Missing name" in result["details"]["skipped"][0]["error"]

    async def test_sync_projects_mixed_operations(
        self, mock_server, existing_project, sample_project_definitions
    ):
        """Test sync with mix of add, update, and skip"""
        from src.marcus_mcp.tools.project_management import sync_projects

        # Mock one existing project
        mock_server.project_registry.list_projects = AsyncMock(
            return_value=[existing_project]
        )

        # Mix of operations: 2 new + 1 existing (which gets updated)
        mixed_definitions = sample_project_definitions + [
            {
                "name": "Existing Project",
                "provider": "planka",
                "config": {"project_id": "old-id", "board_id": "old-board"},
            }
        ]

        result = await sync_projects(mock_server, {"projects": mixed_definitions})

        assert result["success"] is True
        assert result["summary"]["added"] == 2  # Project Alpha, Project Beta
        assert result["summary"]["updated"] == 1  # Existing Project
        assert result["summary"]["skipped"] == 0

    async def test_sync_projects_empty_list(self, mock_server):
        """Test syncing with empty project list returns error"""
        from src.marcus_mcp.tools.project_management import sync_projects

        result = await sync_projects(mock_server, {"projects": []})

        assert result["success"] is False
        assert "error" in result
        assert "No projects provided" in result["error"]

    async def test_sync_projects_handles_errors(self, mock_server):
        """Test error handling when add_project fails"""
        from src.marcus_mcp.tools.project_management import sync_projects

        # Make add_project raise an exception
        mock_server.project_registry.add_project = AsyncMock(
            side_effect=Exception("Database error")
        )

        result = await sync_projects(
            mock_server,
            {
                "projects": [
                    {
                        "name": "Test Project",
                        "provider": "planka",
                        "config": {"project_id": "123"},
                    }
                ]
            },
        )

        assert result["success"] is False
        assert "error" in result
        assert "Database error" in result["error"]

    async def test_select_project_with_auto_sync_hint(self, mock_server):
        """Test that select_project provides helpful hint when auto_sync enabled"""
        from src.marcus_mcp.tools.project_management import select_project

        # Mock config with auto_sync enabled
        mock_server.config = Mock()
        mock_server.config.get = Mock(
            side_effect=lambda k, default=False: (
                True if k == "auto_sync_projects" else default
            )
        )

        # Mock find_or_create_project to return not_found
        from unittest.mock import patch

        with patch(
            "src.marcus_mcp.tools.project_management.find_or_create_project",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = {"action": "not_found"}

            result = await select_project(
                mock_server, {"project_name": "NonExistent Project"}
            )

            assert result["success"] is False
            assert result["action"] == "not_found"
            assert "sync_projects" in result["hint"]
            assert "auto_sync_projects is enabled" in result["hint"]

    async def test_sync_prevents_duplicates_by_provider_config(self, mock_server):
        """
        Test that syncing same Planka board with different name updates instead
        of creating duplicates.

        This verifies the fix for the autosync duplication issue where
        projects were created with names like "Project - Board" and
        duplicate detection by name failed.
        """
        from src.marcus_mcp.tools.project_management import sync_projects

        # Create existing project with old name format
        existing = ProjectConfig(
            id="existing-123",
            name="1st Project",  # Old format: just project name
            provider="planka",
            provider_config={
                "project_id": "1612478574885864456",
                "board_id": "1612478920202912778",
            },
            created_at=datetime.now(),
            last_used=datetime.now(),
        )

        mock_server.project_registry.list_projects = AsyncMock(return_value=[existing])

        # Sync same board with new name format
        new_format_definition = [
            {
                "name": "1st Project - todo",  # New format: project - board
                "provider": "planka",
                "config": {
                    "project_id": "1612478574885864456",
                    "board_id": "1612478920202912778",
                },
                "tags": ["discovered", "planka"],
            }
        ]

        result = await sync_projects(mock_server, {"projects": new_format_definition})

        # Should update existing, not create duplicate
        assert result["success"] is True
        assert result["summary"]["added"] == 0
        assert result["summary"]["updated"] == 1
        assert result["summary"]["skipped"] == 0

        # Verify the name was updated
        assert existing.name == "1st Project - todo"

    async def test_sync_creates_separate_entries_for_different_boards(
        self, mock_server
    ):
        """
        Test that different boards in same project create separate entries.

        Verifies that the provider_config matching correctly identifies
        different boards as separate projects.
        """
        from src.marcus_mcp.tools.project_management import sync_projects

        # Create existing project for board 1
        existing = ProjectConfig(
            id="existing-123",
            name="1st Project - Board A",
            provider="planka",
            provider_config={
                "project_id": "1612478574885864456",
                "board_id": "board-a-id",
            },
            created_at=datetime.now(),
            last_used=datetime.now(),
        )

        mock_server.project_registry.list_projects = AsyncMock(return_value=[existing])

        # Sync different board in same project
        different_board = [
            {
                "name": "1st Project - Board B",
                "provider": "planka",
                "config": {
                    "project_id": "1612478574885864456",  # Same project
                    "board_id": "board-b-id",  # Different board
                },
            }
        ]

        result = await sync_projects(mock_server, {"projects": different_board})

        # Should add as new, not update
        assert result["success"] is True
        assert result["summary"]["added"] == 1
        assert result["summary"]["updated"] == 0

    async def test_sync_github_matches_by_owner_and_repo(self, mock_server):
        """Test GitHub projects match by owner and repo, not name"""
        from src.marcus_mcp.tools.project_management import sync_projects

        # Create existing GitHub project
        existing = ProjectConfig(
            id="github-123",
            name="MyRepo",
            provider="github",
            provider_config={"owner": "myorg", "repo": "myrepo"},
            created_at=datetime.now(),
            last_used=datetime.now(),
        )

        mock_server.project_registry.list_projects = AsyncMock(return_value=[existing])

        # Sync same repo with different name
        updated_name = [
            {
                "name": "MyOrg - MyRepo",  # Different name format
                "provider": "github",
                "config": {"owner": "myorg", "repo": "myrepo"},
            }
        ]

        result = await sync_projects(mock_server, {"projects": updated_name})

        # Should update, not create duplicate
        assert result["success"] is True
        assert result["summary"]["updated"] == 1
        assert result["summary"]["added"] == 0
        assert existing.name == "MyOrg - MyRepo"

    async def test_sync_linear_matches_by_project_id(self, mock_server):
        """Test Linear projects match by project_id, not name"""
        from src.marcus_mcp.tools.project_management import sync_projects

        # Create existing Linear project
        existing = ProjectConfig(
            id="linear-123",
            name="ENG Project",
            provider="linear",
            provider_config={"project_id": "lin-proj-456"},
            created_at=datetime.now(),
            last_used=datetime.now(),
        )

        mock_server.project_registry.list_projects = AsyncMock(return_value=[existing])
        mock_server.project_registry.remove_project = AsyncMock()

        # Sync same project with different name
        updated_name = [
            {
                "name": "Engineering - Q1 Project",  # Different name
                "provider": "linear",
                "config": {"project_id": "lin-proj-456"},
            }
        ]

        result = await sync_projects(mock_server, {"projects": updated_name})

        # Should update, not create duplicate
        assert result["success"] is True
        assert result["summary"]["updated"] == 1
        assert result["summary"]["added"] == 0
        assert existing.name == "Engineering - Q1 Project"

    async def test_automatic_deduplication_on_sync(self, mock_server):
        """
        Test that sync_projects automatically removes duplicates before syncing.

        This ensures users don't need to manually clean up duplicates.
        """
        from src.marcus_mcp.tools.project_management import sync_projects

        # Create duplicate projects (same provider_config, different names)
        now = datetime.now()
        old_duplicate = ProjectConfig(
            id="old-dup-123",
            name="1st Project",  # Old name
            provider="planka",
            provider_config={
                "project_id": "proj-123",
                "board_id": "board-456",
            },
            created_at=now,
            last_used=now,  # Used at same time
        )

        new_duplicate = ProjectConfig(
            id="new-dup-456",
            name="1st Project - Main Board",  # New name format
            provider="planka",
            provider_config={
                "project_id": "proj-123",
                "board_id": "board-456",
            },
            created_at=now,
            last_used=datetime(2025, 10, 5, 12, 0, 0),  # Used more recently
        )

        mock_server.project_registry.list_projects = AsyncMock(
            return_value=[old_duplicate, new_duplicate]
        )
        mock_server.project_registry.remove_project = AsyncMock()

        # Sync empty list (just triggers deduplication)
        result = await sync_projects(
            mock_server,
            {
                "projects": [
                    {
                        "name": "Different Project",
                        "provider": "planka",
                        "config": {"project_id": "other", "board_id": "other"},
                    }
                ]
            },
        )

        # Should have removed 1 duplicate
        assert result["success"] is True
        assert result["summary"]["duplicates_removed"] == 1

        # Should have removed the older one
        mock_server.project_registry.remove_project.assert_called_once_with(
            "old-dup-123"
        )

        # Verify deduplication details
        assert len(result["details"]["deduplicated"]) == 1
        assert result["details"]["deduplicated"][0]["id"] == "old-dup-123"
        assert result["details"]["deduplicated"][0]["name"] == "1st Project"
        assert (
            result["details"]["deduplicated"][0]["kept"] == "1st Project - Main Board"
        )

    async def test_deduplication_keeps_most_recently_used(self, mock_server):
        """Test that deduplication keeps the most recently used project"""
        from src.marcus_mcp.tools.project_management import sync_projects

        # Create duplicates with different last_used times
        recent_project = ProjectConfig(
            id="recent-123",
            name="Recent Project",
            provider="planka",
            provider_config={"project_id": "proj-1", "board_id": "board-1"},
            created_at=datetime(2025, 1, 1),
            last_used=datetime(2025, 10, 5, 10, 0, 0),  # Most recent
        )

        old_project = ProjectConfig(
            id="old-456",
            name="Old Project",
            provider="planka",
            provider_config={"project_id": "proj-1", "board_id": "board-1"},
            created_at=datetime(2025, 1, 1),
            last_used=datetime(2025, 9, 1),  # Older
        )

        mock_server.project_registry.list_projects = AsyncMock(
            return_value=[recent_project, old_project]
        )
        mock_server.project_registry.remove_project = AsyncMock()

        # Trigger sync with a different project
        result = await sync_projects(
            mock_server,
            {
                "projects": [
                    {
                        "name": "Different",
                        "provider": "planka",
                        "config": {"project_id": "diff", "board_id": "diff"},
                    }
                ]
            },
        )

        # Should remove the older project
        mock_server.project_registry.remove_project.assert_called_once_with("old-456")

        assert result["details"]["deduplicated"][0]["kept"] == "Recent Project"
