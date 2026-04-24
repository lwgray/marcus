"""Regression tests for issue #198: JSONDecodeError on empty kanban-mcp response.

get_projects() and get_boards_for_project() must return [] gracefully when
kanban-mcp returns an empty string (e.g. fresh Planka instance with no data).
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
    item = MagicMock()
    item.text = text
    return item


def _mcp_result(text: str) -> MagicMock:
    result = MagicMock()
    result.content = [_text_content(text)]
    return result


def _mock_session(call_tool_return: MagicMock) -> AsyncMock:
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock(return_value=call_tool_return)
    return session


def _patch_mcp(session: AsyncMock) -> tuple:
    """Return (stdio_patch, client_session_patch) that inject *session*."""

    @asynccontextmanager
    async def fake_stdio(_params):
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
    return KanbanClient()


# ---------------------------------------------------------------------------
# get_projects
# ---------------------------------------------------------------------------

class TestGetProjectsEmptyResponse:
    """get_projects must return [] instead of raising JSONDecodeError."""

    @pytest.mark.asyncio
    async def test_empty_string_returns_empty_list(self, client: KanbanClient) -> None:
        session = _mock_session(_mcp_result(""))
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_projects()
        assert result == []

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_empty_list(self, client: KanbanClient) -> None:
        session = _mock_session(_mcp_result("   \n  "))
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_projects()
        assert result == []

    @pytest.mark.asyncio
    async def test_valid_list_response_returns_projects(self, client: KanbanClient) -> None:
        data = [{"id": "p1", "name": "Alpha"}, {"id": "p2", "name": "Beta"}]
        session = _mock_session(_mcp_result(json.dumps(data)))
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_projects()
        assert len(result) == 2
        assert result[0]["id"] == "p1"
        assert result[1]["name"] == "Beta"

    @pytest.mark.asyncio
    async def test_dict_with_items_response_returns_projects(self, client: KanbanClient) -> None:
        data = {"items": [{"id": "p3", "name": "Gamma"}], "total": 1}
        session = _mock_session(_mcp_result(json.dumps(data)))
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_projects()
        assert result == [{"id": "p3", "name": "Gamma"}]


# ---------------------------------------------------------------------------
# get_boards_for_project
# ---------------------------------------------------------------------------

class TestGetBoardsEmptyResponse:
    """get_boards_for_project must return [] on empty kanban-mcp response."""

    @pytest.mark.asyncio
    async def test_empty_string_returns_empty_list(self, client: KanbanClient) -> None:
        session = _mock_session(_mcp_result(""))
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_boards_for_project("proj-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_valid_list_response_returns_boards(self, client: KanbanClient) -> None:
        data = [{"id": "b1", "name": "Main Board"}]
        session = _mock_session(_mcp_result(json.dumps(data)))
        p1, p2 = _patch_mcp(session)
        with p1, p2:
            result = await client.get_boards_for_project("proj-1")
        assert result == [{"id": "b1", "name": "Main Board"}]
