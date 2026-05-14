"""
Unit tests for :mod:`src.cost_tracking.worker_intent`.

Two pure parsers tested in isolation: tool-intent classification of an
assistant message's content blocks (Marcus #527 Phase 2) and task_id
extraction from a user-message tool_result (Marcus #527 Phase 1.5).
Both functions are deterministic and take dict input only, so tests
construct payloads by hand rather than rendering real JSONL.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import pytest

pytestmark = pytest.mark.unit

from src.cost_tracking.worker_intent import (
    classify_tool_intent,
    extract_task_id_from_tool_result,
    extract_task_id_from_user_message,
)


def _tool_use(name: str) -> Dict[str, Any]:
    """Build a minimal ``tool_use`` content block."""
    return {"type": "tool_use", "name": name, "input": {}}


def _text(t: str = "hi") -> Dict[str, Any]:
    """Build a minimal ``text`` content block."""
    return {"type": "text", "text": t}


def _result(content: Any) -> Dict[str, Any]:
    """Build a minimal ``tool_result`` content block."""
    return {"type": "tool_result", "content": content}


# ---------------------------------------------------------------------------
# classify_tool_intent
# ---------------------------------------------------------------------------


class TestClassifyToolIntent:
    """Each tool-use bucket maps to its priority label."""

    def test_marcus_call_wins_over_other_tools(self) -> None:
        """Marcus MCP coordination dominates the intent ladder."""
        content: List[Dict[str, Any]] = [
            _tool_use("Edit"),
            _tool_use("mcp__marcus__report_task_progress"),
            _tool_use("Bash"),
        ]
        assert classify_tool_intent(content) == "worker_marcus_call"

    def test_other_mcp_call_when_no_marcus_tool(self) -> None:
        """A non-Marcus MCP tool buckets as worker_mcp_call."""
        content = [_tool_use("mcp__puppeteer__navigate")]
        assert classify_tool_intent(content) == "worker_mcp_call"

    def test_edit_when_no_mcp_call(self) -> None:
        """Edit / Write / NotebookEdit beat Bash and Read."""
        content = [_tool_use("Read"), _tool_use("Edit"), _tool_use("Bash")]
        assert classify_tool_intent(content) == "worker_edit"

    def test_bash_when_no_edit(self) -> None:
        """Bash wins over Read/Grep when there's no Edit."""
        content = [_tool_use("Read"), _tool_use("Bash")]
        assert classify_tool_intent(content) == "worker_bash"

    def test_search_for_grep_glob_toolsearch(self) -> None:
        """Search bucket covers all three search tools."""
        for name in ("Grep", "Glob", "ToolSearch"):
            assert classify_tool_intent([_tool_use(name)]) == "worker_search"

    def test_read_when_only_read_tool(self) -> None:
        """A Read-only turn classifies as worker_read."""
        assert classify_tool_intent([_tool_use("Read")]) == "worker_read"

    def test_text_only_message_is_worker_text(self) -> None:
        """No tool_use blocks → worker_text."""
        assert classify_tool_intent([_text()]) == "worker_text"

    def test_text_with_thinking_is_still_text(self) -> None:
        """thinking blocks don't promote intent above worker_text."""
        content = [{"type": "thinking", "thinking": "..."}, _text()]
        assert classify_tool_intent(content) == "worker_text"

    def test_none_content_is_unknown(self) -> None:
        """Defensive: None content returns 'unknown'."""
        assert classify_tool_intent(None) == "unknown"

    def test_non_list_content_is_unknown(self) -> None:
        """Defensive: malformed content returns 'unknown'."""
        assert classify_tool_intent("not a list") == "unknown"  # type: ignore[arg-type]

    def test_unknown_tool_falls_through_to_text(self) -> None:
        """Unclassified tool (TodoWrite, WebFetch, ...) → worker_text."""
        # These are real Claude Code tools that don't yet have a bucket;
        # they should not get misclassified as worker_edit or _bash.
        assert classify_tool_intent([_tool_use("TodoWrite")]) == "worker_text"
        assert classify_tool_intent([_tool_use("WebFetch")]) == "worker_text"


# ---------------------------------------------------------------------------
# extract_task_id_from_tool_result
# ---------------------------------------------------------------------------


class TestExtractTaskIdFromToolResult:
    """Both Marcus result shapes (task.id and data.task_id) are recognized."""

    def test_request_next_task_shape(self) -> None:
        """``result.task.id`` is recognized (request_next_task)."""
        payload = json.dumps(
            {"result": {"success": True, "task": {"id": "abc123", "name": "x"}}}
        )
        assert extract_task_id_from_tool_result(payload) == "abc123"

    def test_log_artifact_shape(self) -> None:
        """``result.data.task_id`` is recognized (log_artifact)."""
        payload = json.dumps({"result": {"success": True, "data": {"task_id": "abc"}}})
        assert extract_task_id_from_tool_result(payload) == "abc"

    def test_top_level_task_id_on_result(self) -> None:
        """Some error responses surface task_id on result directly."""
        payload = json.dumps({"result": {"success": False, "task_id": "abc"}})
        assert extract_task_id_from_tool_result(payload) == "abc"

    def test_top_level_task_id_forward_compat(self) -> None:
        """Bare top-level task_id (future tools) is recognized."""
        payload = json.dumps({"task_id": "abc"})
        assert extract_task_id_from_tool_result(payload) == "abc"

    def test_dict_content_not_just_string(self) -> None:
        """Pre-parsed dict content (not stringified) still works."""
        assert (
            extract_task_id_from_tool_result(
                {"result": {"task": {"id": "abc"}}},
            )
            == "abc"
        )

    def test_no_task_id_returns_none(self) -> None:
        """A result with no task_id anywhere returns None."""
        payload = json.dumps({"result": {"success": True, "data": {"foo": "bar"}}})
        assert extract_task_id_from_tool_result(payload) is None

    def test_empty_string_is_safe(self) -> None:
        """Empty content returns None, not a crash."""
        assert extract_task_id_from_tool_result("") is None

    def test_malformed_json_is_safe(self) -> None:
        """Unparseable string returns None, not an exception."""
        assert extract_task_id_from_tool_result("{not valid") is None

    def test_non_string_non_dict_is_safe(self) -> None:
        """List input (unexpected) returns None defensively."""
        assert extract_task_id_from_tool_result([1, 2, 3]) is None

    def test_empty_task_id_rejected(self) -> None:
        """An explicit empty-string task_id is rejected (treated as missing)."""
        payload = json.dumps({"result": {"task": {"id": ""}}})
        assert extract_task_id_from_tool_result(payload) is None


# ---------------------------------------------------------------------------
# extract_task_id_from_user_message
# ---------------------------------------------------------------------------


class TestExtractTaskIdFromUserMessage:
    """Walks a user-message content list for the first tool_result hit."""

    def test_first_tool_result_with_task_id_wins(self) -> None:
        """Multiple tool_result blocks: first one with a parseable task_id wins."""
        content = [
            _result(json.dumps({"result": {"success": False, "data": {}}})),
            _result(json.dumps({"result": {"task": {"id": "second"}}})),
            _result(json.dumps({"result": {"task": {"id": "third"}}})),
        ]
        # First parseable hit ('second') wins.
        assert extract_task_id_from_user_message(content) == "second"

    def test_returns_none_when_no_tool_results(self) -> None:
        """Content with only text blocks returns None."""
        assert extract_task_id_from_user_message([_text()]) is None

    def test_returns_none_for_unparseable_results(self) -> None:
        """All tool_results malformed → None, not an error."""
        content = [
            _result("not json"),
            _result(json.dumps({"result": {"data": {}}})),
        ]
        assert extract_task_id_from_user_message(content) is None

    def test_none_content_is_safe(self) -> None:
        """None content returns None."""
        assert extract_task_id_from_user_message(None) is None
