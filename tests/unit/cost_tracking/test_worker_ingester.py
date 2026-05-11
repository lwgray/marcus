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
    experiment_id: str = "exp_1",
    project_id: str = "proj_1",
) -> AgentBinding:
    """Convenience binding constructor for tests."""
    return AgentBinding(
        agent_id=agent_id, experiment_id=experiment_id, project_id=project_id
    )


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

        binding = _binding(
            agent_id="agent_42", experiment_id="exp_42", project_id="proj_42"
        )
        WorkerJSONLIngester(
            store=store, resolve_binding=lambda _r: binding
        ).ingest_file(path)

        row = store.conn.execute(
            "SELECT agent_id, experiment_id, project_id FROM token_events"
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
