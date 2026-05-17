"""
Unit tests for src.cost_tracking.cost_recorder.

The recorder is a singleton that providers call after each successful LLM
request. It writes one row to the configured CostStore using the active
planner context (run_id/project_id). These tests verify:

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
    canonical_project_id,
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
            PlannerContext(run_id="exp_42", project_id="proj_42")
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
            "SELECT run_id, project_id, agent_role, operation, "
            "input_tokens, cache_creation_tokens, cache_read_tokens, "
            "output_tokens FROM token_events"
        ).fetchone()
        assert row == ("exp_42", "proj_42", "planner", "parse_prd", 100, 200, 400, 50)

    def test_uses_unassigned_fallback_when_no_context(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """No active context → run_id and project_id default to 'unassigned'."""
        recorder.record_planner_call(
            operation="parse_prd",
            provider="anthropic",
            model="claude-sonnet-4-6",
            input_tokens=10,
            output_tokens=5,
        )
        exp, proj = store.conn.execute(
            "SELECT run_id, project_id FROM token_events"
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


class TestRetryAttempt:
    """``retry_attempt`` stamps was_retry / retry_reason (#546 Phase 0)."""

    def test_call_inside_retry_block_is_tagged(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """An LLM call recorded inside retry_attempt() gets was_retry=1."""
        with recorder.planner_context(PlannerContext(run_id="r1", project_id="p1")):
            with recorder.retry_attempt("truncation"):
                recorder.record_planner_call(
                    operation="parse_prd",
                    provider="anthropic",
                    model="claude-sonnet-4-6",
                    input_tokens=10,
                    output_tokens=5,
                )
        row = store.conn.execute(
            "SELECT was_retry, retry_reason FROM token_events"
        ).fetchone()
        assert row == (1, "truncation")

    def test_call_outside_retry_block_is_not_tagged(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """A first-attempt call leaves was_retry NULL.

        Falsification recipe: make ``record`` always set
        ``was_retry=False``.  Confirm this test fails because the
        column reads 0 instead of NULL — losing the first-try vs
        retry distinction.
        """
        with recorder.planner_context(PlannerContext(run_id="r1", project_id="p1")):
            recorder.record_planner_call(
                operation="parse_prd",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=10,
                output_tokens=5,
            )
        row = store.conn.execute(
            "SELECT was_retry, retry_reason FROM token_events"
        ).fetchone()
        assert row == (None, None)

    def test_retry_marker_resets_after_block(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """The retry tag does not leak to calls after the block exits."""
        with recorder.planner_context(PlannerContext(run_id="r1", project_id="p1")):
            with recorder.retry_attempt("truncation"):
                recorder.record_planner_call(
                    operation="parse_prd",
                    provider="anthropic",
                    model="claude-sonnet-4-6",
                    input_tokens=10,
                    output_tokens=5,
                    request_id="inside",
                )
            recorder.record_planner_call(
                operation="parse_prd",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=10,
                output_tokens=5,
                request_id="outside",
            )
        inside = store.conn.execute(
            "SELECT was_retry FROM token_events WHERE request_id='inside'"
        ).fetchone()[0]
        outside = store.conn.execute(
            "SELECT was_retry FROM token_events WHERE request_id='outside'"
        ).fetchone()[0]
        assert inside == 1
        assert outside is None


class TestPlannerContextStack:
    """Nested contexts behave LIFO (innermost wins)."""

    def test_nested_context_uses_innermost(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """Innermost context's ids are used while it's active."""
        with recorder.planner_context(PlannerContext(run_id="outer", project_id="p")):
            with recorder.planner_context(
                PlannerContext(run_id="inner", project_id="p")
            ):
                recorder.record_planner_call(
                    operation="op",
                    provider="anthropic",
                    model="claude-sonnet-4-6",
                    input_tokens=1,
                    output_tokens=1,
                )
        exp = store.conn.execute("SELECT run_id FROM token_events").fetchone()[0]
        assert exp == "inner"

    def test_context_pops_correctly(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """After leaving inner context, outer is restored."""
        with recorder.planner_context(PlannerContext(run_id="outer", project_id="p")):
            with recorder.planner_context(
                PlannerContext(run_id="inner", project_id="p")
            ):
                pass
            recorder.record_planner_call(
                operation="op",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=1,
                output_tokens=1,
            )
        exp = store.conn.execute("SELECT run_id FROM token_events").fetchone()[0]
        assert exp == "outer"


class TestCanonicalProjectId:
    """Project-ID normalization for cost data consistency.

    Marcus has two project-id generators: ProjectRegistry uses dashed
    UUIDs, SQLiteKanban auto-discovery uses dashless hex. Both flow
    into PlannerContext / WorkerJSONLIngester. The normalizer picks
    one canonical form so every token_events row matches.
    """

    def test_strips_dashes_from_canonical_uuid(self) -> None:
        """A dashed UUID becomes dashless hex."""
        assert (
            canonical_project_id("a18b7050-fe0e-492f-a0cf-008c1be8197d")
            == "a18b7050fe0e492fa0cf008c1be8197d"
        )

    def test_passes_through_already_dashless(self) -> None:
        """An already-canonical id is returned unchanged."""
        assert (
            canonical_project_id("9b54dff366fa4a09bbb46d26eb18dddc")
            == "9b54dff366fa4a09bbb46d26eb18dddc"
        )

    def test_preserves_unassigned_sentinel(self) -> None:
        """The 'unassigned' bucket sentinel is not normalized."""
        assert canonical_project_id("unassigned") == "unassigned"

    def test_passes_through_none(self) -> None:
        """None passes through so the recorder's unassigned fallback fires."""
        assert canonical_project_id(None) is None

    def test_planner_context_normalizes_on_construction(self) -> None:
        """PlannerContext stores the dashless form regardless of input."""
        ctx = PlannerContext(
            run_id="e",
            project_id="a18b7050-fe0e-492f-a0cf-008c1be8197d",
        )
        assert ctx.project_id == "a18b7050fe0e492fa0cf008c1be8197d"


class TestNameSnapshot:
    """planner_context snapshots project_name into project_names on push.

    This is what keeps the cost dashboard from showing 'Unnamed' after a
    project is deleted from Marcus's registry: every cost-attributed
    request burns the name into ``project_names`` for posterity.
    """

    def test_push_snapshots_project_name(self, recorder: CostRecorder) -> None:
        """A context with project_name upserts into project_names."""
        with recorder.planner_context(
            PlannerContext(
                run_id="e",
                project_id="proj_snap",
                project_name="hangman",
            )
        ):
            pass
        assert recorder.store.get_project_name("proj_snap") == "hangman"

    def test_push_without_name_does_not_snapshot(self, recorder: CostRecorder) -> None:
        """Contexts without project_name leave project_names untouched."""
        with recorder.planner_context(
            PlannerContext(run_id="e", project_id="proj_nameless")
        ):
            pass
        assert recorder.store.get_project_name("proj_nameless") is None

    def test_unassigned_sentinel_not_snapshotted(self, recorder: CostRecorder) -> None:
        """'unassigned' is a sentinel, not a real project — skip the upsert."""
        with recorder.planner_context(
            PlannerContext(
                run_id="e",
                project_id="unassigned",
                project_name="should_not_persist",
            )
        ):
            pass
        assert recorder.store.get_project_name("unassigned") is None

    def test_repeated_push_does_not_repeat_sql(
        self, recorder: CostRecorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Repeated pushes of the same (id, name) hit SQL only once.

        The recorder caches snapshotted pairs in-process to keep the
        planner_context hot path out of SQLite for already-seen names
        (Kaia review on PR #515). The first push writes; subsequent
        identical pushes short-circuit.
        """
        calls: list[tuple[str, str]] = []
        original = recorder.store.upsert_project_name

        def counting(pid: str, name: str) -> None:
            calls.append((pid, name))
            original(pid, name)

        monkeypatch.setattr(recorder.store, "upsert_project_name", counting)

        ctx = PlannerContext(
            run_id="e",
            project_id="proj_dedup",
            project_name="dedup-me",
        )
        for _ in range(5):
            with recorder.planner_context(ctx):
                pass

        assert calls == [("proj_dedup", "dedup-me")]

    def test_rename_invalidates_dedup(
        self, recorder: CostRecorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A new (id, name) pair bypasses the cache and re-writes."""
        calls: list[tuple[str, str]] = []
        original = recorder.store.upsert_project_name

        def counting(pid: str, name: str) -> None:
            calls.append((pid, name))
            original(pid, name)

        monkeypatch.setattr(recorder.store, "upsert_project_name", counting)

        with recorder.planner_context(
            PlannerContext(run_id="e", project_id="proj_r", project_name="old")
        ):
            pass
        with recorder.planner_context(
            PlannerContext(run_id="e", project_id="proj_r", project_name="new")
        ):
            pass

        assert calls == [("proj_r", "old"), ("proj_r", "new")]
        assert recorder.store.get_project_name("proj_r") == "new"

    def test_disabled_recorder_does_not_snapshot(self, store: CostStore) -> None:
        """When the recorder is disabled, no side effects fire."""
        r = CostRecorder(store=store, enabled=False)
        with r.planner_context(
            PlannerContext(
                run_id="e",
                project_id="p",
                project_name="name",
            )
        ):
            pass
        assert store.get_project_name("p") is None


class TestOperationContext:
    """``operation_context`` stamps ``operation_override`` on the active context.

    The recorder's ``record_planner_call`` reads ``operation_override``
    and uses it in place of the operation argument the provider passes,
    so call sites can label which logical operation they belong to
    without touching every provider's HTTP path.
    """

    def test_overrides_operation_when_parent_exists(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """Inside operation_context, the override beats the caller's op."""
        with recorder.planner_context(PlannerContext(run_id="e", project_id="p")):
            with recorder.operation_context("decompose_prd"):
                recorder.record_planner_call(
                    operation="generic_provider_default",
                    provider="anthropic",
                    model="claude-sonnet-4-6",
                    input_tokens=10,
                    output_tokens=5,
                )
        op = store.conn.execute("SELECT operation FROM token_events").fetchone()[0]
        assert op == "decompose_prd"

    def test_pops_to_parent_after_exit(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """After exiting operation_context, the parent's op (or caller's) wins."""
        with recorder.planner_context(PlannerContext(run_id="e", project_id="p")):
            with recorder.operation_context("decompose_prd"):
                pass
            # Outside the operation_context, caller's op is recorded.
            recorder.record_planner_call(
                operation="analyze",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=1,
                output_tokens=1,
            )
        op = store.conn.execute("SELECT operation FROM token_events").fetchone()[0]
        assert op == "analyze"

    def test_synthesizes_unassigned_parent_when_no_context(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """Without an active PlannerContext, operation_context still pushes.

        Codex P2 on PR #517: the original implementation yielded
        ``None`` when no parent existed, which meant ``record_planner_call``
        never saw the ``operation_override`` and the resulting
        token_events row recorded the provider's generic ``'analyze'``
        bucket instead of the call site's intended operation. Fix
        synthesizes an ``'unassigned'`` PlannerContext carrying just
        the override, so the operation tag is preserved even when
        project/experiment attribution falls through.
        """
        with recorder.operation_context("decompose_prd") as ctx:
            assert ctx is not None
            assert ctx.project_id == "unassigned"
            assert ctx.run_id == "unassigned"
            assert ctx.operation_override == "decompose_prd"
            # Recording inside this scope should stamp the override
            # onto token_events.operation even without a real parent.
            recorder.record_planner_call(
                operation="provider_default",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=1,
                output_tokens=1,
            )
        row = store.conn.execute(
            "SELECT operation, project_id FROM token_events"
        ).fetchone()
        assert row == ("decompose_prd", "unassigned")

    def test_empty_operation_yields_current(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """Empty operation key short-circuits to current() without pushing."""
        with recorder.planner_context(PlannerContext(run_id="e", project_id="p")):
            with recorder.operation_context(""):
                recorder.record_planner_call(
                    operation="caller_op",
                    provider="anthropic",
                    model="claude-sonnet-4-6",
                    input_tokens=1,
                    output_tokens=1,
                )
        op = store.conn.execute("SELECT operation FROM token_events").fetchone()[0]
        assert op == "caller_op"


class TestUnregisteredOperationWarning:
    """Drift detection: warn once per unregistered operation key.

    A typo or new-but-uncatalogued operation silently lands in the
    dashboard's fallback bucket — which defeats the taxonomy. The
    recorder logs a single WARNING per unknown key so the gap shows
    up in dev logs without spamming production at every call.
    """

    def test_warns_once_for_unknown_operation(
        self, recorder: CostRecorder, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Unknown key triggers exactly one WARNING regardless of repeats."""
        with caplog.at_level("WARNING", logger="src.cost_tracking.cost_recorder"):
            with recorder.planner_context(PlannerContext(run_id="e", project_id="p")):
                for _ in range(5):
                    recorder.record_planner_call(
                        operation="totally_typo_op",
                        provider="anthropic",
                        model="claude-sonnet-4-6",
                        input_tokens=1,
                        output_tokens=1,
                    )
        # Exactly one warning, no matter how many calls share the typo
        warns = [
            r
            for r in caplog.records
            if "totally_typo_op" in r.getMessage() and r.levelname == "WARNING"
        ]
        assert len(warns) == 1

    def test_does_not_warn_for_registered_operation(
        self, recorder: CostRecorder, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Known catalog keys log no drift WARNING."""
        with caplog.at_level("WARNING", logger="src.cost_tracking.cost_recorder"):
            with recorder.planner_context(PlannerContext(run_id="e", project_id="p")):
                recorder.record_planner_call(
                    operation="decompose_prd",
                    provider="anthropic",
                    model="claude-sonnet-4-6",
                    input_tokens=1,
                    output_tokens=1,
                )
        # No catalog-drift WARNINGs for a known key
        drift_warns = [
            r for r in caplog.records if "is not registered" in r.getMessage()
        ]
        assert drift_warns == []

    def test_warns_for_operation_override_typo(
        self, recorder: CostRecorder, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A typo in operation_override (not the caller's op) also warns.

        This is the case the WARNING is specifically designed for:
        call sites pass a typo through ``operation_context`` and the
        provider's correctly-spelled default gets shadowed by it.
        """
        with caplog.at_level("WARNING", logger="src.cost_tracking.cost_recorder"):
            with recorder.planner_context(PlannerContext(run_id="e", project_id="p")):
                with recorder.operation_context("decopmose_prd"):  # typo
                    recorder.record_planner_call(
                        operation="decompose_prd",  # correct caller op
                        provider="anthropic",
                        model="claude-sonnet-4-6",
                        input_tokens=1,
                        output_tokens=1,
                    )
        warns = [
            r
            for r in caplog.records
            if "decopmose_prd" in r.getMessage() and r.levelname == "WARNING"
        ]
        assert len(warns) == 1


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
