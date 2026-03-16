"""
Unit tests for verifying labels are fetched from Planka and filtered correctly.

As of feature/fix-card-label-filtering in kanban-mcp:
- kanban-mcp NOW returns FILTERED labels (only assigned labels)
- Marcus no longer needs to do client-side filtering
- The 'labels' array in get_details only contains labels assigned to that card

These tests verify that Marcus correctly uses the filtered labels from kanban-mcp.
"""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

from src.integrations.kanban_client import KanbanClient


class TestLabelFetchWithFilteredLabels:
    """
    Tests for label handling with filtered labels from kanban-mcp.

    kanban-mcp now filters labels server-side, so the 'labels' array
    in get_details responses only contains labels actually assigned to the card.
    """

    @pytest.fixture
    def mock_client_session(self) -> AsyncMock:
        """Create a mock MCP client session."""
        session = AsyncMock()
        session.call_tool = AsyncMock()
        session.initialize = AsyncMock()
        return session

    @pytest.fixture
    def mock_stdio_client(self, mock_client_session: AsyncMock) -> Any:
        """Create a mock stdio client context manager."""

        @asynccontextmanager
        async def mock_stdio_context(
            *args: Any, **kwargs: Any
        ) -> AsyncIterator[tuple[AsyncMock, AsyncMock]]:
            read = AsyncMock()
            write = AsyncMock()
            yield (read, write)

        return mock_stdio_context

    @pytest.fixture
    def mock_session_context(self, mock_client_session: AsyncMock) -> Any:
        """Create a mock ClientSession context manager."""

        @asynccontextmanager
        async def mock_session_ctx(
            *args: Any, **kwargs: Any
        ) -> AsyncIterator[AsyncMock]:
            yield mock_client_session

        return mock_session_ctx

    @pytest.fixture
    def kanban_client(self) -> KanbanClient:
        """Create KanbanClient instance."""
        client = KanbanClient()
        client.board_id = "test-board-123"
        client.project_id = "test-project-456"
        return client

    @pytest.mark.asyncio
    async def test_get_available_tasks_uses_filtered_labels(
        self,
        kanban_client: KanbanClient,
        mock_client_session: AsyncMock,
        mock_stdio_client: Any,
        mock_session_context: Any,
    ) -> None:
        """
        Verify get_available_tasks uses filtered labels from kanban-mcp.

        kanban-mcp now returns ONLY assigned labels in get_details,
        so Marcus should use them directly without filtering.
        """
        # Arrange: Mock responses
        lists_response = MagicMock()
        lists_response.content = [
            TextContent(
                type="text", text=json.dumps([{"id": "list_1", "name": "TODO"}])
            )
        ]

        # Card (no labelIds needed in card list response)
        cards_response = MagicMock()
        cards_response.content = [
            TextContent(
                type="text",
                text=json.dumps([{"id": "card_1", "name": "Test Card"}]),
            )
        ]

        # get_details returns ONLY assigned labels (already filtered)
        card_details_response = MagicMock()
        card_details_response.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "id": "card_1",
                        "name": "Test Card",
                        "labels": [
                            {"id": "l1", "name": "implementation"}
                        ],  # ONLY assigned
                    }
                ),
            )
        ]

        # Configure mock to return responses in sequence
        mock_client_session.call_tool.side_effect = [
            lists_response,
            cards_response,
            card_details_response,
        ]

        # Act: Call with mocked context managers
        with patch("src.integrations.kanban_client.stdio_client", mock_stdio_client):
            with patch(
                "src.integrations.kanban_client.ClientSession",
                mock_session_context,
            ):
                tasks = await kanban_client.get_available_tasks()

        # Assert: Verify get_details was called
        assert mock_client_session.call_tool.call_count == 3

        # Check the third call was get_details
        third_call = mock_client_session.call_tool.call_args_list[2]
        assert third_call[0][0] == "mcp_kanban_card_manager"
        assert third_call[0][1]["action"] == "get_details"
        assert third_call[0][1]["cardId"] == "card_1"

        # Verify task has the labels from get_details (already filtered)
        assert len(tasks) == 1
        assert tasks[0].labels == ["implementation"]

    @pytest.mark.asyncio
    async def test_get_all_tasks_uses_multiple_filtered_labels(
        self,
        kanban_client: KanbanClient,
        mock_client_session: AsyncMock,
        mock_stdio_client: Any,
        mock_session_context: Any,
    ) -> None:
        """
        Verify get_all_tasks uses filtered labels when card has multiple labels.

        kanban-mcp returns all assigned labels (but ONLY assigned ones).
        """
        # Arrange: Mock responses
        lists_response = MagicMock()
        lists_response.content = [
            TextContent(
                type="text", text=json.dumps([{"id": "list_1", "name": "Backlog"}])
            )
        ]

        # Card
        cards_response = MagicMock()
        cards_response.content = [
            TextContent(
                type="text",
                text=json.dumps([{"id": "card_2", "name": "Backend Task"}]),
            )
        ]

        # get_details returns ONLY assigned labels (2 labels assigned)
        card_details_response = MagicMock()
        card_details_response.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "id": "card_2",
                        "name": "Backend Task",
                        "labels": [
                            {"id": "l1", "name": "backend"},
                            {"id": "l2", "name": "api"},
                        ],  # ONLY these 2 are assigned
                    }
                ),
            )
        ]

        # Configure mock
        mock_client_session.call_tool.side_effect = [
            lists_response,
            cards_response,
            card_details_response,
        ]

        # Act
        with patch("src.integrations.kanban_client.stdio_client", mock_stdio_client):
            with patch(
                "src.integrations.kanban_client.ClientSession",
                mock_session_context,
            ):
                tasks = await kanban_client.get_all_tasks()

        # Assert: Verify get_details was called
        assert mock_client_session.call_tool.call_count == 3
        third_call = mock_client_session.call_tool.call_args_list[2]
        assert third_call[0][1]["action"] == "get_details"

        # Verify task has the labels from get_details
        assert len(tasks) == 1
        assert len(tasks[0].labels) == 2
        assert "backend" in tasks[0].labels
        assert "api" in tasks[0].labels

    @pytest.mark.asyncio
    async def test_handles_card_without_labels(
        self,
        kanban_client: KanbanClient,
        mock_client_session: AsyncMock,
        mock_stdio_client: Any,
        mock_session_context: Any,
    ) -> None:
        """
        Verify handling when card has no labels assigned.

        kanban-mcp returns empty labels array if no labels assigned.
        """
        # Arrange: Card without labels
        lists_response = MagicMock()
        lists_response.content = [
            TextContent(
                type="text", text=json.dumps([{"id": "list_1", "name": "TODO"}])
            )
        ]

        cards_response = MagicMock()
        cards_response.content = [
            TextContent(
                type="text",
                text=json.dumps([{"id": "card_3", "name": "No Labels Card"}]),
            )
        ]

        # get_details returns empty labels array (no labels assigned)
        card_details_response = MagicMock()
        card_details_response.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "id": "card_3",
                        "name": "No Labels Card",
                        "labels": [],  # Empty - no labels assigned
                    }
                ),
            )
        ]

        mock_client_session.call_tool.side_effect = [
            lists_response,
            cards_response,
            card_details_response,
        ]

        # Act
        with patch("src.integrations.kanban_client.stdio_client", mock_stdio_client):
            with patch(
                "src.integrations.kanban_client.ClientSession",
                mock_session_context,
            ):
                tasks = await kanban_client.get_available_tasks()

        # Assert: Task has empty labels
        assert len(tasks) == 1
        assert tasks[0].labels == []

    @pytest.mark.asyncio
    async def test_handles_missing_labels_field(
        self,
        kanban_client: KanbanClient,
        mock_client_session: AsyncMock,
        mock_stdio_client: Any,
        mock_session_context: Any,
    ) -> None:
        """
        Verify graceful handling when get_details doesn't include labels field.
        """
        # Arrange: get_details response without labels field
        lists_response = MagicMock()
        lists_response.content = [
            TextContent(
                type="text", text=json.dumps([{"id": "list_1", "name": "TODO"}])
            )
        ]

        cards_response = MagicMock()
        cards_response.content = [
            TextContent(
                type="text",
                text=json.dumps([{"id": "card_4", "name": "Missing Labels Field"}]),
            )
        ]

        # get_details without labels field at all
        card_details_response = MagicMock()
        card_details_response.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "id": "card_4",
                        "name": "Missing Labels Field",
                        # No 'labels' field
                    }
                ),
            )
        ]

        mock_client_session.call_tool.side_effect = [
            lists_response,
            cards_response,
            card_details_response,
        ]

        # Act
        with patch("src.integrations.kanban_client.stdio_client", mock_stdio_client):
            with patch(
                "src.integrations.kanban_client.ClientSession",
                mock_session_context,
            ):
                tasks = await kanban_client.get_available_tasks()

        # Assert: Task created with empty labels (default)
        assert len(tasks) == 1
        assert tasks[0].labels == []

    @pytest.mark.asyncio
    async def test_handles_get_details_exception(
        self,
        kanban_client: KanbanClient,
        mock_client_session: AsyncMock,
        mock_stdio_client: Any,
        mock_session_context: Any,
    ) -> None:
        """
        Verify graceful handling when get_details raises exception.
        """
        # Arrange: get_details raises exception
        lists_response = MagicMock()
        lists_response.content = [
            TextContent(
                type="text", text=json.dumps([{"id": "list_1", "name": "TODO"}])
            )
        ]

        cards_response = MagicMock()
        cards_response.content = [
            TextContent(
                type="text",
                text=json.dumps([{"id": "card_5", "name": "Error Card"}]),
            )
        ]

        # Simulate network error on get_details
        mock_client_session.call_tool.side_effect = [
            lists_response,
            cards_response,
            Exception("Network timeout"),
        ]

        # Act: Should not crash
        with patch("src.integrations.kanban_client.stdio_client", mock_stdio_client):
            with patch(
                "src.integrations.kanban_client.ClientSession",
                mock_session_context,
            ):
                tasks = await kanban_client.get_available_tasks()

        # Assert: Task created without labels
        assert len(tasks) == 1
        assert tasks[0].labels == []

    @pytest.mark.asyncio
    async def test_handles_multiple_cards_with_different_labels(
        self,
        kanban_client: KanbanClient,
        mock_client_session: AsyncMock,
        mock_stdio_client: Any,
        mock_session_context: Any,
    ) -> None:
        """
        Verify get_details called for each card and labels used correctly.

        Each card gets its own filtered labels from kanban-mcp.
        """
        # Arrange: Multiple cards
        lists_response = MagicMock()
        lists_response.content = [
            TextContent(
                type="text", text=json.dumps([{"id": "list_1", "name": "TODO"}])
            )
        ]

        cards_response = MagicMock()
        cards_response.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    [
                        {"id": "card_a", "name": "Card A"},
                        {"id": "card_b", "name": "Card B"},
                    ]
                ),
            )
        ]

        # Each card gets ONLY its assigned labels from get_details
        details_a = MagicMock()
        details_a.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "id": "card_a",
                        "labels": [{"id": "l1", "name": "frontend"}],  # Only this label
                    }
                ),
            )
        ]

        details_b = MagicMock()
        details_b.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "id": "card_b",
                        "labels": [{"id": "l2", "name": "backend"}],  # Different label
                    }
                ),
            )
        ]

        mock_client_session.call_tool.side_effect = [
            lists_response,
            cards_response,
            details_a,
            details_b,
        ]

        # Act
        with patch("src.integrations.kanban_client.stdio_client", mock_stdio_client):
            with patch(
                "src.integrations.kanban_client.ClientSession",
                mock_session_context,
            ):
                tasks = await kanban_client.get_available_tasks()

        # Assert: get_details called for both cards
        assert mock_client_session.call_tool.call_count == 4

        # Verify each task has its assigned labels from get_details
        assert len(tasks) == 2
        assert tasks[0].labels == ["frontend"]
        assert tasks[1].labels == ["backend"]
