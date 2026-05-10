"""
Unit tests for src.cost_tracking.cost_recorder.

The recorder is a singleton that providers call after each successful LLM
request. It writes one row to the configured CostStore using the active
planner context (experiment_id/project_id). These tests verify:

- Recorder writes rows when configured with a store.
- Cache tokens (creation + read) are persisted.
- When no context is set, events use the ``'unassigned'`` fallback.
- Disabling the recorder is a no-op (safe for tests / minimal deployments).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.cost_tracking.cost_recorder import (
    CostRecorder,
    PlannerContext,
    get_recorder,
    set_recorder,
)
from src.cost_tracking.cost_store import CostStore


@pytest.fixture
def store(tmp_path: Path) -> CostStore:
    """Tmp CostStore with default seed prices for cost-view checks."""
    s = CostStore(db_path=tmp_path / "costs.db")
    s.load_seed_prices()
    return s


@pytest.fixture
def recorder(store: CostStore) -> CostRecorder:
    """Recorder bound to a tmp store."""
    return CostRecorder(store=store, enabled=True)


class TestRecordPlannerCall:
    """The main provider-side entry point: ``record_planner_call``."""

    def test_writes_event_with_active_context(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """When a PlannerContext is active, event uses its ids."""
        with recorder.planner_context(
            PlannerContext(experiment_id="exp_42", project_id="proj_42")
        ):
            recorder.record_planner_call(
                operation="parse_prd",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=100,
                cache_creation_tokens=200,
                cache_read_tokens=400,
                output_tokens=50,
            )
        row = store.conn.execute(
            "SELECT experiment_id, project_id, agent_role, operation, "
            "input_tokens, cache_creation_tokens, cache_read_tokens, "
            "output_tokens FROM token_events"
        ).fetchone()
        assert row == ("exp_42", "proj_42", "planner", "parse_prd", 100, 200, 400, 50)

    def test_uses_unassigned_fallback_when_no_context(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """No active context → experiment_id and project_id default to 'unassigned'."""
        recorder.record_planner_call(
            operation="parse_prd",
            provider="anthropic",
            model="claude-sonnet-4-6",
            input_tokens=10,
            output_tokens=5,
        )
        exp, proj = store.conn.execute(
            "SELECT experiment_id, project_id FROM token_events"
        ).fetchone()
        assert exp == "unassigned"
        assert proj == "unassigned"

    def test_disabled_recorder_is_noop(self, store: CostStore) -> None:
        """A disabled recorder writes nothing — safe for tests / minimal deploys."""
        rec = CostRecorder(store=store, enabled=False)
        rec.record_planner_call(
            operation="parse_prd",
            provider="anthropic",
            model="claude-sonnet-4-6",
            input_tokens=100,
            output_tokens=50,
        )
        count = store.conn.execute("SELECT COUNT(*) FROM token_events").fetchone()[0]
        assert count == 0

    def test_swallows_store_errors(
        self, recorder: CostRecorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Recorder must never raise into the provider call path."""

        def boom(_: object) -> None:
            raise RuntimeError("simulated store failure")

        monkeypatch.setattr(recorder.store, "record_event", boom)
        # Should not raise
        recorder.record_planner_call(
            operation="parse_prd",
            provider="anthropic",
            model="claude-sonnet-4-6",
            input_tokens=10,
            output_tokens=5,
        )


class TestPlannerContextStack:
    """Nested contexts behave LIFO (innermost wins)."""

    def test_nested_context_uses_innermost(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """Innermost context's ids are used while it's active."""
        with recorder.planner_context(
            PlannerContext(experiment_id="outer", project_id="p")
        ):
            with recorder.planner_context(
                PlannerContext(experiment_id="inner", project_id="p")
            ):
                recorder.record_planner_call(
                    operation="op",
                    provider="anthropic",
                    model="claude-sonnet-4-6",
                    input_tokens=1,
                    output_tokens=1,
                )
        exp = store.conn.execute("SELECT experiment_id FROM token_events").fetchone()[0]
        assert exp == "inner"

    def test_context_pops_correctly(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """After leaving inner context, outer is restored."""
        with recorder.planner_context(
            PlannerContext(experiment_id="outer", project_id="p")
        ):
            with recorder.planner_context(
                PlannerContext(experiment_id="inner", project_id="p")
            ):
                pass
            recorder.record_planner_call(
                operation="op",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=1,
                output_tokens=1,
            )
        exp = store.conn.execute("SELECT experiment_id FROM token_events").fetchone()[0]
        assert exp == "outer"


class TestSingleton:
    """Module-level get/set helpers."""

    def test_get_recorder_returns_same_instance(self) -> None:
        """get_recorder is idempotent."""
        a = get_recorder()
        b = get_recorder()
        assert a is b

    def test_set_recorder_replaces_singleton(self, recorder: CostRecorder) -> None:
        """set_recorder swaps the module-level instance."""
        set_recorder(recorder)
        assert get_recorder() is recorder
        # Reset for downstream tests
        set_recorder(None)
