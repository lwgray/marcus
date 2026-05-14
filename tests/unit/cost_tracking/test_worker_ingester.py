"""
Unit tests for src.cost_tracking.worker_ingester.

The ingester reads Claude Code session JSONL files (one per spawned worker
agent) and inserts a ``token_events`` row for every ``type == "assistant"``
record that carries a ``message.usage`` block. These tests use synthetic
fixture JSONL written to ``tmp_path`` so no real Claude Code session is
required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

pytestmark = pytest.mark.unit

from src.cost_tracking.cost_store import CostStore
from src.cost_tracking.worker_ingester import (
    AgentBinding,
    WorkerJSONLIngester,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> CostStore:
    """Tmp store seeded with the default Anthropic prices."""
    s = CostStore(db_path=tmp_path / "costs.db")
    s.load_seed_prices()
    return s


def _assistant_record(
    *,
    session_id: str = "sess_1",
    uuid: str = "u_1",
    request_id: str = "req_1",
    timestamp: str = "2026-05-10T14:00:00.000Z",
    cwd: str = "/Users/me/exp/agent_1",
    model: str = "claude-sonnet-4-6",
    input_tokens: int = 100,
    cache_creation_input_tokens: int = 200,
    cache_read_input_tokens: int = 400,
    output_tokens: int = 50,
) -> Dict[str, Any]:
    """Build an ``assistant``-type JSONL record matching the real shape."""
    return {
        "type": "assistant",
        "uuid": uuid,
        "sessionId": session_id,
        "requestId": request_id,
        "timestamp": timestamp,
        "cwd": cwd,
        "message": {
            "model": model,
            "usage": {
                "input_tokens": input_tokens,
                "cache_creation_input_tokens": cache_creation_input_tokens,
                "cache_read_input_tokens": cache_read_input_tokens,
                "output_tokens": output_tokens,
            },
        },
    }


def _user_record() -> Dict[str, Any]:
    """Non-assistant record that the ingester must skip."""
    return {"type": "user", "sessionId": "sess_1", "content": "hi"}


def _queue_op_record() -> Dict[str, Any]:
    """A queue-operation record (no usage block) — must be skipped."""
    return {"type": "queue-operation", "operation": "enqueue"}


def _write_jsonl(path: Path, records: list[Dict[str, Any]]) -> None:
    """Serialize records as one JSON object per line."""
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


def _binding(
    agent_id: str = "agent_unicorn_1",
    run_id: str = "exp_1",
    project_id: str = "proj_1",
) -> AgentBinding:
    """Convenience binding constructor for tests."""
    return AgentBinding(agent_id=agent_id, run_id=run_id, project_id=project_id)


# ---------------------------------------------------------------------------
# ingest_file
# ---------------------------------------------------------------------------


class TestIngestFile:
    """Single-file batch ingestion."""

    def test_ingests_assistant_records(self, store: CostStore, tmp_path: Path) -> None:
        """Each assistant record produces one token_events row."""
        path = tmp_path / "sess.jsonl"
        _write_jsonl(
            path,
            [
                _assistant_record(uuid="u1", request_id="req_1"),
                _assistant_record(uuid="u2", request_id="req_2", input_tokens=200),
            ],
        )

        ingester = WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        )
        inserted = ingester.ingest_file(path)

        assert inserted == 2
        rows = store.conn.execute("SELECT COUNT(*) FROM token_events").fetchone()[0]
        assert rows == 2

    def test_skips_non_assistant_records(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """user and queue-operation records are filtered out."""
        path = tmp_path / "sess.jsonl"
        _write_jsonl(
            path,
            [
                _user_record(),
                _queue_op_record(),
                _assistant_record(),
            ],
        )

        inserted = WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)

        assert inserted == 1

    def test_skips_assistant_without_usage(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """Assistant records lacking ``message.usage`` are skipped."""
        rec = _assistant_record()
        del rec["message"]["usage"]
        path = tmp_path / "sess.jsonl"
        _write_jsonl(path, [rec])

        inserted = WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)

        assert inserted == 0

    def test_records_persist_token_fields(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """All four token counts round-trip through the DB."""
        path = tmp_path / "sess.jsonl"
        _write_jsonl(
            path,
            [
                _assistant_record(
                    input_tokens=100,
                    cache_creation_input_tokens=200,
                    cache_read_input_tokens=400,
                    output_tokens=50,
                )
            ],
        )

        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)

        row = store.conn.execute(
            "SELECT input_tokens, cache_creation_tokens, cache_read_tokens, "
            "output_tokens, agent_role, provider FROM token_events"
        ).fetchone()
        assert row == (100, 200, 400, 50, "worker", "anthropic")

    def test_uses_binding_ids(self, store: CostStore, tmp_path: Path) -> None:
        """Resolved binding's ids land on the row."""
        path = tmp_path / "sess.jsonl"
        _write_jsonl(path, [_assistant_record()])

        binding = _binding(agent_id="agent_42", run_id="exp_42", project_id="proj_42")
        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: binding
        ).ingest_file(path)

        row = store.conn.execute(
            "SELECT agent_id, run_id, project_id FROM token_events"
        ).fetchone()
        assert row == ("agent_42", "exp_42", "proj_42")

    def test_skips_record_when_resolver_returns_none(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """If resolve_binding returns None, the event is dropped."""
        path = tmp_path / "sess.jsonl"
        _write_jsonl(path, [_assistant_record()])

        inserted = WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: None
        ).ingest_file(path)
        assert inserted == 0

    def test_skips_malformed_lines(self, store: CostStore, tmp_path: Path) -> None:
        """Lines that aren't valid JSON are skipped, not fatal."""
        path = tmp_path / "sess.jsonl"
        path.write_text(
            "{not valid json\n"
            + json.dumps(_assistant_record())
            + "\n"
            + "\n"  # blank line
        )

        inserted = WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)
        assert inserted == 1


class TestTurnIndex:
    """Per-session turn counter."""

    def test_assigns_increasing_turn_index_within_session(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """Three assistant records in one session → turn_index 1, 2, 3."""
        path = tmp_path / "sess.jsonl"
        _write_jsonl(
            path,
            [
                _assistant_record(session_id="s_a", uuid="u1", request_id="r1"),
                _assistant_record(session_id="s_a", uuid="u2", request_id="r2"),
                _assistant_record(session_id="s_a", uuid="u3", request_id="r3"),
            ],
        )

        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)

        turns = [
            r[0]
            for r in store.conn.execute(
                "SELECT turn_index FROM token_events ORDER BY event_id"
            )
        ]
        assert turns == [1, 2, 3]

    def test_separate_sessions_have_independent_counters(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """Each session_id gets its own 1..N counter."""
        path = tmp_path / "sess.jsonl"
        _write_jsonl(
            path,
            [
                _assistant_record(session_id="s_a", uuid="u1", request_id="r1"),
                _assistant_record(session_id="s_b", uuid="u2", request_id="r2"),
                _assistant_record(session_id="s_a", uuid="u3", request_id="r3"),
            ],
        )

        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)

        rows = list(
            store.conn.execute(
                "SELECT session_id, turn_index FROM token_events ORDER BY event_id"
            )
        )
        assert rows == [("s_a", 1), ("s_b", 1), ("s_a", 2)]


class TestIdempotency:
    """Re-ingesting the same file must not duplicate events."""

    def test_dedups_on_uuid(self, store: CostStore, tmp_path: Path) -> None:
        """Re-running ingest_file with same records inserts nothing the second time."""
        path = tmp_path / "sess.jsonl"
        _write_jsonl(path, [_assistant_record(uuid="u1")])

        ingester = WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        )
        ingester.ingest_file(path)
        second = ingester.ingest_file(path)

        assert second == 0
        count = store.conn.execute("SELECT COUNT(*) FROM token_events").fetchone()[0]
        assert count == 1


class TestIngestDirectory:
    """Bulk ingest of every .jsonl file in a directory tree."""

    def test_ingests_all_jsonl_files(self, store: CostStore, tmp_path: Path) -> None:
        """Two files in two subdirs → 4 events total."""
        d1 = tmp_path / "agent_1"
        d2 = tmp_path / "agent_2"
        d1.mkdir()
        d2.mkdir()
        _write_jsonl(
            d1 / "s_a.jsonl",
            [
                _assistant_record(session_id="s_a", uuid="u1"),
                _assistant_record(session_id="s_a", uuid="u2"),
            ],
        )
        _write_jsonl(
            d2 / "s_b.jsonl",
            [
                _assistant_record(session_id="s_b", uuid="u3"),
                _assistant_record(session_id="s_b", uuid="u4"),
            ],
        )

        inserted = WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_directory(tmp_path)
        assert inserted == 4


# ---------------------------------------------------------------------------
# Marcus #527 Phase 1.5 + 2: task_id tracker + tool_intent classification
# ---------------------------------------------------------------------------


def _assistant_with_tool(
    *,
    session_id: str = "sess_1",
    uuid: str = "u_1",
    request_id: str = "req_1",
    tool_name: str = "Edit",
) -> Dict[str, Any]:
    """Assistant record whose content carries one tool_use block."""
    rec = _assistant_record(session_id=session_id, uuid=uuid, request_id=request_id)
    rec["message"]["content"] = [{"type": "tool_use", "name": tool_name, "input": {}}]
    return rec


def _user_with_task_result(
    *,
    session_id: str,
    task_id: str,
    shape: str = "task",
) -> Dict[str, Any]:
    """User record with one tool_result echoing a task_id.

    ``shape='task'`` → ``result.task.id`` (request_next_task shape).
    ``shape='data'`` → ``result.data.task_id`` (log_artifact shape).
    """
    if shape == "task":
        payload = json.dumps({"result": {"success": True, "task": {"id": task_id}}})
    else:
        payload = json.dumps(
            {"result": {"success": True, "data": {"task_id": task_id}}}
        )
    return {
        "type": "user",
        "sessionId": session_id,
        "message": {
            "content": [{"type": "tool_result", "content": payload}],
        },
    }


class TestTaskIdTracker:
    """Per-session task tracker fills binding.task_id when resolver leaves it None."""

    def test_request_next_task_result_populates_subsequent_row(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """request_next_task result → next assistant turn gets that task_id."""
        path = tmp_path / "s.jsonl"
        _write_jsonl(
            path,
            [
                _user_with_task_result(session_id="s1", task_id="task_alpha"),
                _assistant_with_tool(session_id="s1", uuid="u1", request_id="r1"),
            ],
        )
        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)
        row = store.conn.execute(
            "SELECT task_id FROM token_events WHERE request_id = 'r1'"
        ).fetchone()
        assert row is not None
        assert row[0] == "task_alpha"

    def test_log_artifact_shape_also_populates(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """result.data.task_id is also tracked (log_artifact / report_blocker)."""
        path = tmp_path / "s.jsonl"
        _write_jsonl(
            path,
            [
                _user_with_task_result(
                    session_id="s1", task_id="task_beta", shape="data"
                ),
                _assistant_with_tool(session_id="s1", uuid="u1", request_id="r1"),
            ],
        )
        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)
        row = store.conn.execute(
            "SELECT task_id FROM token_events WHERE request_id = 'r1'"
        ).fetchone()
        assert row[0] == "task_beta"

    def test_tracker_overwrites_on_new_request_next_task(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """A session that does many tasks gets each turn tagged correctly."""
        path = tmp_path / "s.jsonl"
        _write_jsonl(
            path,
            [
                _user_with_task_result(session_id="s1", task_id="task_1"),
                _assistant_with_tool(session_id="s1", uuid="u1", request_id="r1"),
                _user_with_task_result(session_id="s1", task_id="task_2"),
                _assistant_with_tool(session_id="s1", uuid="u2", request_id="r2"),
            ],
        )
        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)
        rows = dict(
            store.conn.execute(
                "SELECT request_id, task_id FROM token_events ORDER BY request_id"
            ).fetchall()
        )
        assert rows == {"r1": "task_1", "r2": "task_2"}

    def test_pre_request_next_task_turns_remain_null(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """Turns before the session's first task assignment stay NULL."""
        # An agent's register_agent / ping turn comes before any task. The
        # tracker correctly reports NULL — these turns truly have no task.
        path = tmp_path / "s.jsonl"
        _write_jsonl(
            path,
            [
                _assistant_with_tool(session_id="s1", uuid="u1", request_id="r1"),
                _user_with_task_result(session_id="s1", task_id="task_x"),
                _assistant_with_tool(session_id="s1", uuid="u2", request_id="r2"),
            ],
        )
        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)
        rows = dict(
            store.conn.execute(
                "SELECT request_id, task_id FROM token_events ORDER BY request_id"
            ).fetchall()
        )
        assert rows == {"r1": None, "r2": "task_x"}

    def test_tracker_is_per_session(self, store: CostStore, tmp_path: Path) -> None:
        """Two sessions in the same file don't share task state."""
        path = tmp_path / "s.jsonl"
        _write_jsonl(
            path,
            [
                _user_with_task_result(session_id="s1", task_id="task_a"),
                _user_with_task_result(session_id="s2", task_id="task_b"),
                _assistant_with_tool(session_id="s1", uuid="u1", request_id="r1"),
                _assistant_with_tool(session_id="s2", uuid="u2", request_id="r2"),
            ],
        )
        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)
        rows = dict(
            store.conn.execute(
                "SELECT request_id, task_id FROM token_events ORDER BY request_id"
            ).fetchall()
        )
        assert rows == {"r1": "task_a", "r2": "task_b"}

    def test_binding_task_id_wins_over_tracker(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """If the resolver provides task_id, the tracker fallback is ignored."""
        path = tmp_path / "s.jsonl"
        _write_jsonl(
            path,
            [
                _user_with_task_result(session_id="s1", task_id="from_tracker"),
                _assistant_with_tool(session_id="s1", uuid="u1", request_id="r1"),
            ],
        )

        def explicit_binding(_r: Dict[str, Any]) -> AgentBinding:
            return AgentBinding(
                agent_id="agent_unicorn_1",
                run_id="exp_1",
                project_id="proj_1",
                task_id="from_binding",
            )

        WorkerJSONLIngester(store=store, resolve_binding=explicit_binding).ingest_file(
            path
        )
        row = store.conn.execute(
            "SELECT task_id FROM token_events WHERE request_id = 'r1'"
        ).fetchone()
        assert row[0] == "from_binding"


class TestToolIntent:
    """Tool intent classification lands on the token_events row."""

    def test_edit_classifies_correctly(self, store: CostStore, tmp_path: Path) -> None:
        """An Edit tool_use → tool_intent='worker_edit'."""
        path = tmp_path / "s.jsonl"
        _write_jsonl(
            path,
            [_assistant_with_tool(uuid="u1", request_id="r1", tool_name="Edit")],
        )
        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)
        row = store.conn.execute(
            "SELECT tool_intent FROM token_events WHERE request_id = 'r1'"
        ).fetchone()
        assert row[0] == "worker_edit"

    def test_marcus_mcp_call_classifies_correctly(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """A mcp__marcus__* tool_use → tool_intent='worker_marcus_call'."""
        path = tmp_path / "s.jsonl"
        _write_jsonl(
            path,
            [
                _assistant_with_tool(
                    uuid="u1",
                    request_id="r1",
                    tool_name="mcp__marcus__report_task_progress",
                )
            ],
        )
        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).ingest_file(path)
        row = store.conn.execute(
            "SELECT tool_intent FROM token_events WHERE request_id = 'r1'"
        ).fetchone()
        assert row[0] == "worker_marcus_call"


class TestBackfill:
    """Historical rows can be backfilled by re-walking the JSONL."""

    def test_backfill_updates_existing_null_columns(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """Pre-existing NULL task_id / tool_intent get filled in."""
        # Step 1: insert a row directly with NULLs (simulating legacy data).
        from src.cost_tracking.cost_store import TokenEvent

        store.record_event(
            TokenEvent(
                run_id="exp_1",
                project_id="proj_1",
                agent_id="agent_unicorn_1",
                agent_role="worker",
                operation="turn",
                provider="anthropic",
                model="claude-sonnet-4-6",
                request_id="r_old",
                session_id="s1",
                input_tokens=100,
                output_tokens=50,
                # task_id and tool_intent intentionally not set.
            )
        )

        # Step 2: write a JSONL that contains the same request_id + the
        # task assignment that should now backfill it.
        path = tmp_path / "s.jsonl"
        _write_jsonl(
            path,
            [
                _user_with_task_result(session_id="s1", task_id="task_backfilled"),
                _assistant_with_tool(
                    session_id="s1",
                    uuid="u_old",
                    request_id="r_old",
                    tool_name="Bash",
                ),
            ],
        )

        # Step 3: backfill.
        updated = WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).backfill_file(path)

        # One row updated; columns now match the parsed values.
        assert updated == 1
        row = store.conn.execute(
            "SELECT task_id, tool_intent FROM token_events WHERE request_id = 'r_old'"
        ).fetchone()
        assert row == ("task_backfilled", "worker_bash")

    def test_backfill_does_not_overwrite_existing_values(
        self, store: CostStore, tmp_path: Path
    ) -> None:
        """Backfill respects COALESCE — non-NULL columns stay."""
        from src.cost_tracking.cost_store import TokenEvent

        store.record_event(
            TokenEvent(
                run_id="exp_1",
                project_id="proj_1",
                agent_id="agent_unicorn_1",
                agent_role="worker",
                operation="turn",
                provider="anthropic",
                model="claude-sonnet-4-6",
                request_id="r_keep",
                session_id="s1",
                task_id="task_preserved",  # already set — must not be overwritten
                tool_intent="worker_edit",  # already set — must not be overwritten
                input_tokens=10,
                output_tokens=5,
            )
        )
        path = tmp_path / "s.jsonl"
        _write_jsonl(
            path,
            [
                _user_with_task_result(session_id="s1", task_id="should_not_overwrite"),
                _assistant_with_tool(
                    session_id="s1",
                    uuid="u_keep",
                    request_id="r_keep",
                    tool_name="Bash",  # would compute to worker_bash, but ignored
                ),
            ],
        )
        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: _binding()
        ).backfill_file(path)
        row = store.conn.execute(
            "SELECT task_id, tool_intent FROM token_events WHERE request_id = 'r_keep'"
        ).fetchone()
        assert row == ("task_preserved", "worker_edit")
