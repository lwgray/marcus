"""
Unit tests for the runner's MCP-over-HTTP client (issue #595 Fix 3, chunk 3b).

parse_mcp_tool_result is pure and fully tested here. MarcusMCPClient is
network I/O; its tool-call path is exercised with urllib mocked so the
session/parse wiring is covered without a live server.
"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# conftest.py puts dev-tools/experiments/ on sys.path so `runners` imports.
from runners.marcus_client import MarcusMCPClient, parse_mcp_tool_result

pytestmark = pytest.mark.unit


def _sse(envelope: dict) -> bytes:
    """Encode a JSON-RPC envelope as a one-line SSE response body."""
    return f"data: {json.dumps(envelope)}\n".encode()


class TestParseMcpToolResult:
    """parse_mcp_tool_result extracts the structured tool result."""

    def test_extracts_structured_result(self) -> None:
        """The tool's dict at result.structuredContent.result is returned."""
        raw = _sse(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "structuredContent": {
                        "result": {"desired_agent_count": 3, "unclaimed_tasks": 2}
                    }
                },
            }
        )

        assert parse_mcp_tool_result(raw) == {
            "desired_agent_count": 3,
            "unclaimed_tasks": 2,
        }

    def test_returns_none_when_no_structured_content(self) -> None:
        """A response without structuredContent yields None."""
        raw = _sse({"jsonrpc": "2.0", "id": 2, "result": {"content": []}})

        assert parse_mcp_tool_result(raw) is None

    def test_returns_none_on_non_data_lines(self) -> None:
        """Lines that are not SSE `data:` frames are ignored."""
        assert parse_mcp_tool_result(b": keep-alive\n\n") is None

    def test_returns_none_on_malformed_json(self) -> None:
        """A `data:` line with broken JSON is skipped, not raised."""
        assert parse_mcp_tool_result(b"data: {not json\n") is None

    def test_returns_none_on_empty_body(self) -> None:
        """An empty response body yields None."""
        assert parse_mcp_tool_result(b"") is None


class TestMarcusMCPClientUrlNormalization:
    """The endpoint URL is forced to the trailing-slash /mcp/ form."""

    def test_missing_trailing_slash_is_added(self) -> None:
        """A /mcp URL is normalized to /mcp/ — avoids the 307 redirect."""
        client = MarcusMCPClient("http://localhost:4298/mcp")

        assert client._url == "http://localhost:4298/mcp/"

    def test_existing_trailing_slash_preserved(self) -> None:
        """An already-correct /mcp/ URL is left as a single trailing slash."""
        client = MarcusMCPClient("http://localhost:4298/mcp/")

        assert client._url == "http://localhost:4298/mcp/"


class TestMarcusMCPClient:
    """MarcusMCPClient connects once and reuses the session per call."""

    def test_not_connected_before_connect(self) -> None:
        """A fresh client is not connected and call_tool returns None."""
        client = MarcusMCPClient()

        assert client.connected is False
        assert client.call_tool("get_desired_agent_count", {"max_agents": 5}) is None

    def test_connect_then_call_tool(self) -> None:
        """After connect(), call_tool posts a tools/call and parses the result."""
        client = MarcusMCPClient()

        # initialize response: carries the mcp-session-id header
        init_resp = MagicMock()
        init_resp.headers = {"mcp-session-id": "sess-123"}
        init_resp.read.return_value = b""
        init_resp.__enter__ = lambda s: s
        init_resp.__exit__ = lambda s, *a: False

        # notifications/initialized + tools/call responses
        note_resp = MagicMock()
        note_resp.read.return_value = b""
        note_resp.__enter__ = lambda s: s
        note_resp.__exit__ = lambda s, *a: False

        call_resp = MagicMock()
        call_resp.read.return_value = _sse(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"structuredContent": {"result": {"desired_agent_count": 4}}},
            }
        )
        call_resp.__enter__ = lambda s: s
        call_resp.__exit__ = lambda s, *a: False

        with patch(
            "runners.marcus_client.urllib.request.urlopen",
            side_effect=[init_resp, note_resp, call_resp],
        ):
            assert client.connect() is True
            assert client.connected is True
            result = client.call_tool("get_desired_agent_count", {"max_agents": 6})

        assert result == {"desired_agent_count": 4}

    def test_connect_fails_without_session_header(self) -> None:
        """No mcp-session-id header → connect returns False, stays disconnected."""
        client = MarcusMCPClient()

        init_resp = MagicMock()
        init_resp.headers = {}
        init_resp.read.return_value = b""
        init_resp.__enter__ = lambda s: s
        init_resp.__exit__ = lambda s, *a: False

        with patch(
            "runners.marcus_client.urllib.request.urlopen",
            return_value=init_resp,
        ):
            assert client.connect() is False

        assert client.connected is False
