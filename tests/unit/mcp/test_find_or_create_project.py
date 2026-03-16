"""
Unit tests for find_or_create_project MCP tool.

Tests the smart project discovery helper that guides users through
the "which project?" decision tree.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.project_registry import ProjectConfig
from src.marcus_mcp.tools.project_management import find_or_create_project


class TestFindOrCreateProject:
    """Test suite for find_or_create_project tool"""

    @pytest.fixture
    def mock_server(self):
        """Create mock server with project_registry"""
        server = Mock()
        server.project_registry = Mock()
        return server

    @pytest.fixture
    def sample_projects(self) -> List[ProjectConfig]:
        """Create sample projects for testing"""
        return [
            ProjectConfig(
                id="proj-123",
                name="MyAPI",
                provider="planka",
                provider_config={"project_id": "1", "board_id": "1"},
                created_at=datetime.now(timezone.utc),
                last_used=datetime.now(timezone.utc),
                tags=["backend"],
            ),
            ProjectConfig(
                id="proj-456",
                name="MyAPI-Dev",
                provider="planka",
                provider_config={"project_id": "2", "board_id": "2"},
                created_at=datetime.now(timezone.utc),
                last_used=datetime.now(timezone.utc),
                tags=["backend", "dev"],
            ),
            ProjectConfig(
                id="proj-789",
                name="Frontend-App",
                provider="github",
                provider_config={"owner": "test", "repo": "app", "project_number": 1},
                created_at=datetime.now(timezone.utc),
                last_used=datetime.now(timezone.utc),
                tags=["frontend"],
            ),
        ]

    @pytest.mark.asyncio
    async def test_find_exact_match_returns_project(self, mock_server, sample_projects):
        """Test finding exact project name match"""
        # Arrange
        mock_server.project_registry.list_projects = AsyncMock(
            return_value=sample_projects
        )

        # Mock task count
        with patch(
            "src.marcus_mcp.tools.project_management.get_task_count",
            new=AsyncMock(return_value=12),
        ):
            arguments = {"name": "MyAPI"}

            # Act
            result = await find_or_create_project(mock_server, arguments)

            # Assert
            assert result["action"] == "found_existing"
            assert result["project"]["name"] == "MyAPI"
            assert result["project"]["id"] == "proj-123"
            assert result["project"]["provider"] == "planka"
            assert result["project"]["task_count"] == 12
            assert "next_steps" in result
            assert len(result["next_steps"]) == 2

    @pytest.mark.asyncio
    async def test_find_fuzzy_matches_returns_suggestions(
        self, mock_server, sample_projects
    ):
        """Test finding similar project names"""
        # Arrange
        mock_server.project_registry.list_projects = AsyncMock(
            return_value=sample_projects
        )
        arguments = {"name": "myapi"}  # lowercase

        # Act
        result = await find_or_create_project(mock_server, arguments)

        # Assert
        assert result["action"] == "found_similar"
        assert "matches" in result
        assert len(result["matches"]) >= 2  # MyAPI and MyAPI-Dev
        assert result["suggestion"] == "Did you mean one of these projects?"
        assert "next_steps" in result

    @pytest.mark.asyncio
    async def test_not_found_returns_guidance(self, mock_server, sample_projects):
        """Test when project not found"""
        # Arrange
        mock_server.project_registry.list_projects = AsyncMock(
            return_value=sample_projects
        )
        arguments = {"name": "NonExistentProject"}

        # Act
        result = await find_or_create_project(mock_server, arguments)

        # Assert
        assert result["action"] == "not_found"
        assert "NonExistentProject" in result["message"]
        assert result["total_projects"] == 3
        assert result["suggestion"] == "List all projects with: list_projects()"
        assert "next_steps" in result
        assert len(result["next_steps"]) == 3

    @pytest.mark.asyncio
    async def test_not_found_with_create_if_missing(self, mock_server, sample_projects):
        """Test guidance when project not found and create_if_missing=True"""
        # Arrange
        mock_server.project_registry.list_projects = AsyncMock(
            return_value=sample_projects
        )
        arguments = {"name": "NewProject", "create_if_missing": True}

        # Act
        result = await find_or_create_project(mock_server, arguments)

        # Assert
        assert result["action"] == "guide_creation"
        assert "NewProject" in result["message"]
        assert "options" in result
        assert len(result["options"]) == 2
        # Verify options suggest both create_project and add_project
        option_tools = [opt["tool"] for opt in result["options"]]
        assert "create_project" in option_tools
        assert "add_project" in option_tools

    @pytest.mark.asyncio
    async def test_empty_project_list_returns_not_found(self, mock_server):
        """Test behavior when no projects exist"""
        # Arrange
        mock_server.project_registry.list_projects = AsyncMock(return_value=[])
        arguments = {"name": "FirstProject"}

        # Act
        result = await find_or_create_project(mock_server, arguments)

        # Assert
        assert result["action"] == "not_found"
        assert result["total_projects"] == 0
        assert "next_steps" in result

    @pytest.mark.asyncio
    async def test_case_insensitive_fuzzy_matching(self, mock_server, sample_projects):
        """Test that fuzzy matching is case-insensitive"""
        # Arrange
        mock_server.project_registry.list_projects = AsyncMock(
            return_value=sample_projects
        )
        arguments = {"name": "MYAPI"}  # ALL CAPS

        # Act
        result = await find_or_create_project(mock_server, arguments)

        # Assert
        # Should find fuzzy matches (MyAPI, MyAPI-Dev)
        assert result["action"] in ["found_similar", "found_existing"]
        if result["action"] == "found_similar":
            assert len(result["matches"]) >= 2

    @pytest.mark.asyncio
    async def test_partial_name_match_returns_fuzzy_results(
        self, mock_server, sample_projects
    ):
        """Test finding projects with partial name match"""
        # Arrange
        mock_server.project_registry.list_projects = AsyncMock(
            return_value=sample_projects
        )
        arguments = {"name": "API"}  # Partial match

        # Act
        result = await find_or_create_project(mock_server, arguments)

        # Assert
        assert result["action"] == "found_similar"
        assert len(result["matches"]) >= 2  # MyAPI and MyAPI-Dev
        # Verify all matches contain "API" in name
        for match in result["matches"]:
            assert "api" in match["name"].lower()

    @pytest.mark.asyncio
    async def test_missing_project_name_returns_error(self, mock_server):
        """Test that missing name parameter returns appropriate error"""
        # Arrange
        arguments = {}  # Missing name

        # Act & Assert
        # Should handle gracefully - implementation will define exact behavior
        # For now, test that it doesn't crash
        try:
            result = await find_or_create_project(mock_server, arguments)
            # If no error, verify response structure
            assert isinstance(result, dict)
        except (KeyError, ValueError) as e:
            # Expected to raise an error for missing required param
            assert "name" in str(e).lower()


@pytest.mark.unit
class TestFindOrCreateProjectHelpers:
    """Test helper functions used by find_or_create_project"""

    def test_calculate_similarity_placeholder(self):
        """
        Placeholder test for similarity calculation.

        When implementing calculate_similarity function, this test
        should verify that similar names get higher scores.
        """
        # This will be implemented when the actual similarity function is added
        # For now, simple substring matching is sufficient
        pass

    def test_get_task_count_placeholder(self):
        """
        Placeholder test for get_task_count helper.

        When implementing get_task_count, this should verify
        it correctly counts tasks for a project.
        """
        # This will be implemented when the helper is added
        pass
