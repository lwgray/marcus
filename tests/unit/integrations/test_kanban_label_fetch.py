"""
Unit tests for verifying labels are fetched from Planka and filtered correctly.

Tests verify that kanban-mcp returns ALL board labels in get_details,
and Marcus filters them based on card's labelIds field.
"""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

from src.integrations.kanban_client import KanbanClient


class TestLabelFetchDiscovery:
    """Discovery tests to understand label fetching behavior."""

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
    async def test_get_available_tasks_filters_labels_by_label_ids(
        self,
        kanban_client: KanbanClient,
        mock_client_session: AsyncMock,
        mock_stdio_client: Any,
        mock_session_context: Any,
    ) -> None:
        """
        Verify get_available_tasks filters labels based on card's labelIds.

        kanban-mcp returns ALL board labels in get_details, but only
        labels whose IDs are in the card's labelIds array should be kept.
        """
        # Arrange: Mock responses
        lists_response = MagicMock()
        lists_response.content = [
            TextContent(
                type="text", text=json.dumps([{"id": "list_1", "name": "TODO"}])
            )
        ]

        # Card has labelIds indicating which labels are assigned
        cards_response = MagicMock()
        cards_response.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    [{"id": "card_1", "name": "Test Card", "labelIds": ["l1"]}]
                ),
            )
        ]

        # get_details returns ALL board labels (not filtered)
        card_details_response = MagicMock()
        card_details_response.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "id": "card_1",
                        "name": "Test Card",
                        "labelIds": ["l1"],
                        "labels": [
                            {"id": "l1", "name": "implementation"},
                            {"id": "l2", "name": "design"},
                            {"id": "l3", "name": "documentation"},
                        ],
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

        # Verify task has ONLY the label in labelIds (filtered)
        assert len(tasks) == 1
        assert tasks[0].labels == ["implementation"]

    @pytest.mark.asyncio
    async def test_get_all_tasks_filters_multiple_labels(
        self,
        kanban_client: KanbanClient,
        mock_client_session: AsyncMock,
        mock_stdio_client: Any,
        mock_session_context: Any,
    ) -> None:
        """
        Verify get_all_tasks filters when card has multiple labelIds.
        """
        # Arrange: Mock responses
        lists_response = MagicMock()
        lists_response.content = [
            TextContent(
                type="text", text=json.dumps([{"id": "list_1", "name": "Backlog"}])
            )
        ]

        # Card has multiple labelIds
        cards_response = MagicMock()
        cards_response.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    [
                        {
                            "id": "card_2",
                            "name": "Backend Task",
                            "labelIds": ["l1", "l2"],
                        }
                    ]
                ),
            )
        ]

        # get_details returns ALL board labels
        card_details_response = MagicMock()
        card_details_response.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "id": "card_2",
                        "name": "Backend Task",
                        "labelIds": ["l1", "l2"],
                        "labels": [
                            {"id": "l1", "name": "backend"},
                            {"id": "l2", "name": "api"},
                            {"id": "l3", "name": "frontend"},
                            {"id": "l4", "name": "design"},
                        ],
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

        # Verify task has ONLY the labels in labelIds (filtered)
        assert len(tasks) == 1
        assert len(tasks[0].labels) == 2
        assert "backend" in tasks[0].labels
        assert "api" in tasks[0].labels
        # These should NOT be present (not in labelIds)
        assert "frontend" not in tasks[0].labels
        assert "design" not in tasks[0].labels

    @pytest.mark.asyncio
    async def test_handles_card_without_label_ids(
        self,
        kanban_client: KanbanClient,
        mock_client_session: AsyncMock,
        mock_stdio_client: Any,
        mock_session_context: Any,
    ) -> None:
        """
        Verify graceful handling when card has no labelIds field.

        If a card has no labelIds, it means no labels are assigned,
        even if get_details returns board labels.
        """
        # Arrange: Card without labelIds field
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

        # get_details returns board labels but card has no labelIds
        card_details_response = MagicMock()
        card_details_response.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "id": "card_3",
                        "name": "No Labels Card",
                        "labels": [
                            {"id": "l1", "name": "implementation"},
                            {"id": "l2", "name": "design"},
                        ],
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

        # Assert: Task created with empty labels (no labelIds means no labels)
        assert len(tasks) == 1
        assert tasks[0].labels == []

    @pytest.mark.asyncio
    async def test_handles_empty_label_ids_array(
        self,
        kanban_client: KanbanClient,
        mock_client_session: AsyncMock,
        mock_stdio_client: Any,
        mock_session_context: Any,
    ) -> None:
        """
        Verify graceful handling when card has empty labelIds array.
        """
        # Arrange: Card with empty labelIds
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
                    [{"id": "card_4", "name": "Empty Labels", "labelIds": []}]
                ),
            )
        ]

        # get_details returns board labels but labelIds is empty
        card_details_response = MagicMock()
        card_details_response.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "id": "card_4",
                        "name": "Empty Labels",
                        "labelIds": [],
                        "labels": [
                            {"id": "l1", "name": "implementation"},
                            {"id": "l2", "name": "design"},
                        ],
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

        # Assert: Task has empty labels (empty labelIds)
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
    async def test_handles_multiple_cards_with_different_label_ids(
        self,
        kanban_client: KanbanClient,
        mock_client_session: AsyncMock,
        mock_stdio_client: Any,
        mock_session_context: Any,
    ) -> None:
        """
        Verify get_details called for each card and labels filtered correctly.

        Each card should only get labels whose IDs are in its labelIds array.
        """
        # Arrange: Multiple cards with different labelIds
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
                        {"id": "card_a", "name": "Card A", "labelIds": ["l1"]},
                        {"id": "card_b", "name": "Card B", "labelIds": ["l2"]},
                    ]
                ),
            )
        ]

        # Both cards get ALL board labels from get_details
        details_a = MagicMock()
        details_a.content = [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "id": "card_a",
                        "labelIds": ["l1"],
                        "labels": [
                            {"id": "l1", "name": "frontend"},
                            {"id": "l2", "name": "backend"},
                            {"id": "l3", "name": "design"},
                        ],
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
                        "labelIds": ["l2"],
                        "labels": [
                            {"id": "l1", "name": "frontend"},
                            {"id": "l2", "name": "backend"},
                            {"id": "l3", "name": "design"},
                        ],
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

        # Verify each task has ONLY its assigned labels (filtered)
        assert len(tasks) == 2
        assert tasks[0].labels == ["frontend"]  # Only l1
        assert tasks[1].labels == ["backend"]  # Only l2
