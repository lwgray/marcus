"""Unit tests for Planka workspace state loading."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestPlankaWorkspaceState:
    """Test suite for Planka workspace state delegation."""

    @pytest.fixture
    def planka_instance(self):
        """Create a Planka instance for testing."""
        from src.integrations.providers.planka import Planka

        # Mock the environment variables
        with patch.dict(
            "os.environ",
            {
                "PLANKA_BASE_URL": "http://test.com",
                "PLANKA_AGENT_EMAIL": "test@test.com",
                "PLANKA_AGENT_PASSWORD": "password",
                "PLANKA_PROJECT_ID": "test_project",
                "PLANKA_BOARD_ID": "test_board",
            },
        ):
            planka = Planka({})
            return planka

    def test_planka_has_load_workspace_state_method(self, planka_instance):
        """Test that Planka has _load_workspace_state method."""
        # Arrange & Assert
        assert hasattr(
            planka_instance, "_load_workspace_state"
        ), "Planka should have _load_workspace_state method"

    def test_load_workspace_state_delegates_to_client(self, planka_instance, tmp_path):
        """Test that _load_workspace_state delegates to internal client."""
        # Arrange
        workspace_file = tmp_path / ".marcus_workspace.json"
        workspace_data = {
            "project_id": "test_project",
            "board_id": "test_board",
            "project_root": "/test/path",
        }
        workspace_file.write_text(json.dumps(workspace_data))

        # Mock the client's _load_workspace_state
        mock_result = {
            "project_id": "test_project",
            "board_id": "test_board",
            "project_root": "/test/path",
        }
        planka_instance.client._load_workspace_state = Mock(return_value=mock_result)

        # Act
        result = planka_instance._load_workspace_state()

        # Assert
        assert result == mock_result
        planka_instance.client._load_workspace_state.assert_called_once()

    def test_load_workspace_state_returns_none_when_no_file(self, planka_instance):
        """Test that _load_workspace_state returns None when no workspace file."""
        # Arrange
        planka_instance.client._load_workspace_state = Mock(return_value=None)

        # Act
        result = planka_instance._load_workspace_state()

        # Assert
        assert result is None
        planka_instance.client._load_workspace_state.assert_called_once()

    def test_load_workspace_state_returns_none_when_client_is_none(
        self, planka_instance
    ):
        """Test that _load_workspace_state returns None when client is None."""
        # Arrange - Simulate edge case where client is None
        planka_instance.client = None

        # Act
        result = planka_instance._load_workspace_state()

        # Assert
        assert result is None

    def test_validation_can_call_load_workspace_state(self, planka_instance, tmp_path):
        """
        Test validation code pattern - state.kanban_client._load_workspace_state().

        This mimics how work_analyzer.py calls the method.
        """
        # Arrange
        state = Mock()
        state.kanban_client = planka_instance

        mock_result = {
            "project_id": "test_project",
            "board_id": "test_board",
            "project_root": "/test/path",
        }
        planka_instance.client._load_workspace_state = Mock(return_value=mock_result)

        # Act - This is the pattern used in work_analyzer.py:290
        workspace_state = state.kanban_client._load_workspace_state()

        # Assert
        assert workspace_state == mock_result
        assert "project_root" in workspace_state
