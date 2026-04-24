"""Unit tests for issue #198: graceful handling of empty Planka MCP responses.

get_projects() and get_boards_for_project() must return [] without raising
JSONDecodeError or IndexError when kanban-mcp yields an empty response (e.g.
a fresh Planka instance that has no projects or boards yet).
"""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.kanban_client import KanbanClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_content(text: str) -> MagicMock:
    """Create a mock TextContent with the given text payload."""
    item = MagicMock()
    item.text = text
    return item


def _mcp_result(text: str) -> MagicMock:
    """Create a mock MCP call_tool result with one TextContent item."""
    result = MagicMock()
    result.content = [_text_content(text)]
    return result


def _empty_content_result() -> MagicMock:
    """Create a mock MCP result with an empty content list."""
    result = MagicMock()
    result.content = []
    return result


def _mock_session(call_tool_return: MagicMock) -> AsyncMock:
    """Build a mock async ClientSession that returns *call_tool_return*."""
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock(return_value=call_tool_return)
    return session


def _patch_mcp(session: AsyncMock) -> tuple:
    """
    Return (stdio_patch, client_session_patch) that inject *session*.

    Parameters
    ----------
    session : AsyncMock
        Pre-configured session mock to inject.

    Returns
    -------
    tuple
        Two context managers to be used with ``with p1, p2:``.
    """

    @asynccontextmanager
    async def fake_stdio(_params):  # type: ignore[misc]
        yield MagicMock(), MagicMock()

    class _FakeClientSession:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> AsyncMock:
            return session

        async def __aexit__(self, *args: object) -> None:
            pass

    return (
        patch("src.integrations.kanban_client.stdio_client", side_effect=fake_stdio),
        patch("src.integrations.kanban_client.ClientSession", _FakeClientSession),
    )


@pytest.fixture
def client() -> KanbanClient:
    """Provide an uninitialised KanbanClient (no real config needed)."""
    return KanbanClient()


# ---------------------------------------------------------------------------
# get_projects
# ---------------------------------------------------------------------------

class TestGetProjects:
    """Unit tests for KanbanClient.get_projects empty-response handling."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_projects_when_empty_string_then_returns_empty_list(
        self, client: KanbanClient
    ) -> None:
        """
        Test get_projects returns [] when MCP response text is empty string.

        Verifies the JSONDecodeError guard from issue #198.
        """
        session = _mock_session(_mcp_result(""))
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_projects()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_projects_when_whitespace_only_then_returns_empty_list(
        self, client: KanbanClient
    ) -> None:
        """
        Test get_projects returns [] when MCP response text is whitespace only.

        Whitespace responses can occur when kanban-mcp sends trailing newlines
        on an empty data set.
        """
        session = _mock_session(_mcp_result("   \n  "))
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_projects()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_projects_when_empty_content_list_then_returns_empty_list(
        self, client: KanbanClient
    ) -> None:
        """
        Test get_projects returns [] when MCP result.content is an empty list.

        Guards against IndexError on result.content[0] when content is [].
        """
        session = _mock_session(_empty_content_result())
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_projects()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_projects_when_valid_list_json_then_returns_projects(
        self, client: KanbanClient
    ) -> None:
        """
        Test get_projects returns projects when MCP returns a valid JSON list.

        Verifies the normal happy path is unaffected by the guard.
        """
        data = [{"id": "p1", "name": "Alpha"}, {"id": "p2", "name": "Beta"}]
        session = _mock_session(_mcp_result(json.dumps(data)))
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_projects()
        assert len(result) == 2
        assert result[0]["id"] == "p1"
        assert result[1]["name"] == "Beta"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_projects_when_dict_with_items_then_returns_items(
        self, client: KanbanClient
    ) -> None:
        """
        Test get_projects returns items list when MCP returns a paginated dict.

        Planka may wrap results in {items: [...], total: N}.
        """
        data = {"items": [{"id": "p3", "name": "Gamma"}], "total": 1}
        session = _mock_session(_mcp_result(json.dumps(data)))
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_projects()
        assert result == [{"id": "p3", "name": "Gamma"}]


# ---------------------------------------------------------------------------
# get_boards_for_project
# ---------------------------------------------------------------------------

class TestGetBoardsForProject:
    """Unit tests for KanbanClient.get_boards_for_project empty-response handling."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_boards_when_empty_string_then_returns_empty_list(
        self, client: KanbanClient
    ) -> None:
        """
        Test get_boards_for_project returns [] when MCP response text is empty.

        Applies the same empty-response guard as get_projects (issue #198).
        """
        session = _mock_session(_mcp_result(""))
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_boards_for_project("proj-1")
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_boards_when_valid_list_json_then_returns_boards(
        self, client: KanbanClient
    ) -> None:
        """
        Test get_boards_for_project returns boards when MCP returns valid JSON.

        Verifies the normal happy path is unaffected by the guard.
        """
        data = [{"id": "b1", "name": "Main Board"}]
        session = _mock_session(_mcp_result(json.dumps(data)))
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_boards_for_project("proj-1")
        assert result == [{"id": "b1", "name": "Main Board"}]
