"""
Pure content parsers for worker JSONL records (Marcus #527 Phase 1.5 + 2).

Walks the ``message.content`` block list on Claude Code session records
to answer two questions per record:

1. **What tool did the agent use on this LLM call?** Used by the ingester
   to populate ``token_events.tool_intent`` so the dashboard can break
   worker spend down by what the agent was *doing* (editing code,
   running tests, talking to Marcus, ...). This makes the
   ``operation='turn'`` catch-all addressable — see issue #527.

2. **Which kanban task was the agent working on?** Extracted from any
   Marcus MCP tool_result that echoes a ``task_id`` back. The ingester
   maintains a per-session running task tracker; this module supplies
   the extraction logic. Closes the audit gap from PR #528 where every
   worker row had ``task_id = NULL``.

Both functions are **pure**: they take raw dict input and return plain
values, with no IO and no React/DOM coupling. The ingester owns the
walking, dedup, and DB writes; this module owns the parsing. Same
split as ``operationsPanel.logic.ts`` on the Cato side.

Notes
-----
The two extraction paths cover the two ``task_id`` shapes that real
Marcus tools emit:

- ``request_next_task`` returns ``{"result": {"task": {"id": "..."}}}``
  (task object with a bare ``id``).
- ``log_artifact`` / ``report_blocker`` / ``report_task_progress``
  return ``{"result": {"data": {"task_id": "..."}}}`` (data envelope
  with ``task_id``).

Both are accepted so any Marcus interaction updates the tracker, not
just the assignment call. This makes the tracker robust against
sessions whose first record we missed (the agent's task is recoverable
from any subsequent log_artifact call).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Tool-intent classification (#527 Phase 2)
# ---------------------------------------------------------------------------

# Intent buckets, in priority order. The first matching rule wins per
# turn — so an Edit + Bash in the same assistant message classifies as
# ``worker_edit`` because the agent's primary action was code-writing.
# Coordination calls (``mcp__marcus__*``) outrank everything else so
# coordination overhead surfaces as its own line item; that's the metric
# nobody can see today and the one we most want to optimize.
TOOL_INTENT_VALUES = {
    "worker_marcus_call",
    "worker_mcp_call",
    "worker_edit",
    "worker_bash",
    "worker_search",
    "worker_read",
    "worker_text",
    "unknown",
}


def classify_tool_intent(content: Optional[List[Dict[str, Any]]]) -> str:
    """Pick a single ``tool_intent`` label for one assistant message.

    Walks the content block list looking for ``tool_use`` blocks and
    returns the highest-priority bucket that matches any of them. If
    the message contains no tool_use blocks (the agent only wrote
    text) the result is ``worker_text``. If ``content`` is missing or
    not a list the result is ``unknown`` — those records typically
    don't get ingested anyway but the parser stays defensive.

    The ordering of the priority list is the load-bearing piece:
    ``mcp__marcus__*`` calls dominate so coordination overhead is
    visible; ``Edit`` / ``Write`` / ``NotebookEdit`` come next so
    code-writing turns are distinguishable from tool-only chores like
    running tests or reading files.

    Parameters
    ----------
    content : list of dict or None
        ``record["message"]["content"]`` from a Claude Code JSONL
        record. May be ``None`` on records with no message body.

    Returns
    -------
    str
        One of :data:`TOOL_INTENT_VALUES`.
    """
    if not isinstance(content, list):
        return "unknown"

    tool_names: List[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            name = block.get("name")
            if isinstance(name, str):
                tool_names.append(name)

    if not tool_names:
        return "worker_text"

    # Priority order. First match wins. Marcus coordination tools
    # come first so coordination tax is its own slice in the chart.
    for name in tool_names:
        if name.startswith("mcp__marcus__"):
            return "worker_marcus_call"
    for name in tool_names:
        if name.startswith("mcp__"):
            return "worker_mcp_call"
    for name in tool_names:
        if name in {"Edit", "Write", "NotebookEdit"}:
            return "worker_edit"
    for name in tool_names:
        if name == "Bash":
            return "worker_bash"
    for name in tool_names:
        if name in {"Grep", "Glob", "ToolSearch"}:
            return "worker_search"
    for name in tool_names:
        if name == "Read":
            return "worker_read"
    # Any other tool we don't yet classify (TodoWrite, WebFetch, ...)
    # falls through to mcp_call when applicable above; here we just
    # mark it as text since the agent's intent wasn't a coding action.
    return "worker_text"


# ---------------------------------------------------------------------------
# task_id extraction (#527 Phase 1.5)
# ---------------------------------------------------------------------------


def extract_task_id_from_tool_result(content: Any) -> Optional[str]:
    """Pull a kanban ``task_id`` out of one tool_result content block.

    Handles both Marcus MCP result shapes:

    - ``{"result": {"task": {"id": "..."}}}`` — emitted by
      ``request_next_task`` (the task object carries ``id``, not
      ``task_id``).
    - ``{"result": {"data": {"task_id": "..."}}}`` — emitted by
      ``log_artifact`` / ``report_blocker`` /
      ``report_task_progress`` / similar (Marcus wraps the response
      in a ``data`` envelope and uses the dashless ``task_id`` key).

    Also accepts a top-level ``task_id`` for forward compatibility
    with any future tool that emits the bare key. Returns ``None``
    when no recognizable shape matches.

    The content arrives in two encodings depending on how Claude Code
    chose to serialize the MCP result:

    1. A JSON string — the ``content`` field on the tool_result
       block is a stringified payload.
    2. A pre-parsed dict — some clients emit structured content
       directly.

    Both are handled so the parser doesn't fail on either path.

    Parameters
    ----------
    content : Any
        The ``content`` field of a tool_result block. Typically a
        string but occasionally a dict.

    Returns
    -------
    str or None
        Hex task_id when one is found; otherwise ``None``.
    """
    parsed: Any
    if isinstance(content, str):
        # Bail fast on empty / non-JSON strings without raising.
        if not content or content[0] not in "{[":
            return None
        try:
            parsed = json.loads(content)
        except (ValueError, json.JSONDecodeError):
            return None
    elif isinstance(content, dict):
        parsed = content
    else:
        return None

    if not isinstance(parsed, dict):
        return None

    # Shape 1: result.task.id  (request_next_task)
    result = parsed.get("result")
    if isinstance(result, dict):
        task = result.get("task")
        if isinstance(task, dict):
            tid = task.get("id")
            if isinstance(tid, str) and tid:
                return tid

        # Shape 2: result.data.task_id  (log_artifact, report_blocker, ...)
        data = result.get("data")
        if isinstance(data, dict):
            tid = data.get("task_id")
            if isinstance(tid, str) and tid:
                return tid

        # Shape 3: top-level task_id on result (some error responses)
        tid = result.get("task_id")
        if isinstance(tid, str) and tid:
            return tid

    # Shape 4: top-level task_id (forward compat)
    tid = parsed.get("task_id")
    if isinstance(tid, str) and tid:
        return tid

    return None


def extract_task_id_from_user_message(
    content: Optional[List[Dict[str, Any]]],
) -> Optional[str]:
    """Scan a user-message content list for a Marcus task_id.

    User messages in Claude Code JSONL carry tool_result blocks (the
    return value of an earlier tool_use). This walks them and returns
    the first task_id found via
    :func:`extract_task_id_from_tool_result`. Multiple results in one
    message are rare but possible (parallel tool calls); the first
    hit wins because Marcus's tool_results all reference the same
    active task anyway.

    Parameters
    ----------
    content : list of dict or None
        ``record["message"]["content"]`` from a Claude Code ``user``
        record.

    Returns
    -------
    str or None
        A task_id when a Marcus tool_result is present and parseable.
    """
    if not isinstance(content, list):
        return None
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_result":
            tid = extract_task_id_from_tool_result(block.get("content"))
            if tid is not None:
                return tid
    return None
