#!/usr/bin/env python3
"""
Unit tests for KanbanClient
Tests the client logic without real MCP connections
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, mock_open, patch

import pytest
import pytest_asyncio

# Add parent directory to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from src.core.models import Priority, Task, TaskStatus
from src.integrations.kanban_client import KanbanClient


class TestKanbanClient:
    """Test suite for KanbanClient"""

    @pytest.fixture
    def mock_config_file(self):
        """Create mock config file content"""
        return """
        {
            "project_id": "test-project-123",
            "board_id": "test-board-456",
            "planka": {
                "base_url": "http://localhost:3333",
                "email": "test@test.com",
                "password": "testpass"
            }
        }
        """

    @pytest.fixture
    def client_with_config(self, mock_config_file):
        """Create a client with mocked config"""
        with patch("builtins.open", mock_open(read_data=mock_config_file)):
            with patch("pathlib.Path.exists", return_value=True):
                return KanbanClient()

    def test_initialization(self, client_with_config):
        """Test client initialization"""
        client = client_with_config

        # Should load config values
        assert client.project_id == "test-project-123"
        assert client.board_id == "test-board-456"

        # Should set environment variables
        assert os.environ.get("PLANKA_BASE_URL") == "http://localhost:3333"
        assert os.environ.get("PLANKA_AGENT_EMAIL") == "test@test.com"
        assert os.environ.get("PLANKA_AGENT_PASSWORD") == "testpass"

    def test_initialization_no_config(self):
        """Test initialization when no config file exists"""
        # Clean up environment variables from previous tests
        env_vars_to_clean = [
            "PLANKA_BASE_URL",
            "PLANKA_AGENT_EMAIL",
            "PLANKA_AGENT_PASSWORD",
        ]
        old_values = {}
        for var in env_vars_to_clean:
            old_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

        try:
            with patch("pathlib.Path.exists", return_value=False):
                client = KanbanClient()

                # Should have None values for project/board
                assert client.project_id is None
                assert client.board_id is None

                # Should use default environment variables
                assert os.environ.get("PLANKA_BASE_URL") == "http://localhost:3333"
                assert os.environ.get("PLANKA_AGENT_EMAIL") == "demo@demo.demo"
                assert os.environ.get("PLANKA_AGENT_PASSWORD") == "demo"
        finally:
            # Restore original environment
            for var, value in old_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]

    @pytest.mark.asyncio
    async def test_get_available_tasks_no_board_id(self):
        """Test getting available tasks when board_id is not set"""
        with patch("pathlib.Path.exists", return_value=False):
            client = KanbanClient()

            with pytest.raises(RuntimeError, match="Board ID not set"):
                await client.get_available_tasks()

    @pytest.mark.asyncio
    async def test_get_all_tasks_no_board_id(self):
        """Test getting all tasks when board_id is not set"""
        with patch("pathlib.Path.exists", return_value=False):
            client = KanbanClient()

            with pytest.raises(RuntimeError, match="Board ID not set"):
                await client.get_all_tasks()

    @pytest.mark.asyncio
    async def test_get_board_summary_no_board_id(self):
        """Test getting board summary when board_id is not set"""
        with patch("pathlib.Path.exists", return_value=False):
            client = KanbanClient()

            with pytest.raises(RuntimeError, match="Board ID not set"):
                await client.get_board_summary()

    def test_card_to_task_conversion(self, client_with_config):
        """Test card to task conversion"""
        client = client_with_config

        # Test with complete card data
        card = {
            "id": "test-id",
            "name": "Test Card",
            "description": "Test description",
            "listName": "TODO",
            "users": [{"username": "testuser"}],
        }

        task = client._card_to_task(card)

        assert task.id == "test-id"
        assert task.name == "Test Card"
        assert task.description == "Test description"
        assert task.status == TaskStatus.TODO
        assert task.priority == Priority.MEDIUM
        assert task.assigned_to == "testuser"

    def test_card_to_task_minimal_data(self, client_with_config):
        """Test card to task conversion with minimal data"""
        client = client_with_config

        card = {"id": "minimal-id", "name": "Minimal Card"}

        task = client._card_to_task(card)

        assert task.id == "minimal-id"
        assert task.name == "Minimal Card"
        assert task.description == ""
        assert task.status == TaskStatus.TODO
        assert task.priority == Priority.MEDIUM
        assert task.assigned_to is None

    def test_status_mapping(self, client_with_config):
        """Test status mapping from list names"""
        client = client_with_config

        test_cases = [
            ("TODO", TaskStatus.TODO),
            ("DONE", TaskStatus.DONE),
            ("Done", TaskStatus.DONE),
            ("In Progress", TaskStatus.IN_PROGRESS),
            ("PROGRESS", TaskStatus.IN_PROGRESS),
            ("BLOCKED", TaskStatus.BLOCKED),
            ("Blocked", TaskStatus.BLOCKED),
            ("Other", TaskStatus.TODO),  # Default case
        ]

        for list_name, expected_status in test_cases:
            card = {"id": "test", "name": "Test", "listName": list_name}
            task = client._card_to_task(card)
            assert (
                task.status == expected_status
            ), f"List '{list_name}' should map to {expected_status}"

    def test_priority_default(self, client_with_config):
        """Test that priority defaults to MEDIUM"""
        client = client_with_config

        # The current implementation always sets priority to MEDIUM
        card = {"id": "test", "name": "Test"}
        task = client._card_to_task(card)
        assert task.priority == Priority.MEDIUM

    def test_is_available_task(self, client_with_config):
        """Test checking if a task is available"""
        client = client_with_config

        available_cases = [
            {"listName": "TODO"},
            {"listName": "TO DO"},
            {"listName": "BACKLOG"},
            {"listName": "READY"},
        ]

        unavailable_cases = [
            {"listName": "DONE"},
            {"listName": "IN PROGRESS"},
            {"listName": "BLOCKED"},
            {"listName": "TESTING"},
        ]

        for card in available_cases:
            assert client._is_available_task(
                card
            ), f"Card with listName '{card['listName']}' should be available"

        for card in unavailable_cases:
            assert not client._is_available_task(
                card
            ), f"Card with listName '{card['listName']}' should not be available"
