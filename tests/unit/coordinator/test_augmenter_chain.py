"""Unit tests for ``run_augmenter_chain`` (issue #456 — Stage 3).

The chain orchestrator runs registered augmenters sequentially over a
task graph.  Each augmenter sees the post-previous-augmenter task list
so synthesized tasks can flow forward (e.g., outcome_coverage's
gap-fill task is visible to spec_coverage's coverage check).

Defense-in-depth requirement (Kaia review #2, Simon ``c26c7ec5``):
the orchestrator wraps every augmenter call in ``try/except`` so an
unexpected raise from a future augmenter never crashes the decomposer.
This is independent of each augmenter's own internal exception
handling — the chain is the last line of defense.

Telemetry is namespaced by augmenter ``name`` so future augmenters
add their payload alongside outcome_coverage's without key collisions.
The contract-first consumer at ``nlp_tools.py`` reads the
``outcome_coverage`` slice to emit ``PLANNING_INTENT_FIDELITY``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from src.core.models import Priority, Task, TaskStatus

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(task_id: str, name: str = "Implement Foo") -> Task:
    """Minimal Task for chain tests."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name=name,
        description="...",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=2.0,
    )


class _RecordingAugmenter:
    """Augmenter stub that records calls and returns canned results."""

    def __init__(
        self,
        *,
        name: str,
        tasks_to_append: Optional[List[Task]] = None,
        telemetry: Optional[Dict[str, Any]] = None,
        raises: Optional[BaseException] = None,
    ) -> None:
        self.name = name
        self._tasks_to_append = tasks_to_append or []
        self._telemetry = telemetry or {}
        self._raises = raises
        self.calls: List[Dict[str, Any]] = []

    async def augment(
        self,
        *,
        prd_analysis: Any,
        tasks: List[Task],
        contract_artifacts: Optional[Dict[str, Any]] = None,
    ) -> Any:
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
        )

        self.calls.append(
            {
                "prd_analysis": prd_analysis,
                "tasks": list(tasks),
                "contract_artifacts": contract_artifacts,
            }
        )
        if self._raises is not None:
            raise self._raises

        appended = self._tasks_to_append
        return AugmentationResult(
            augmented_tasks=list(tasks) + appended,
            synthesized_ids=[t.id for t in appended],
            telemetry=dict(self._telemetry),
        )


# ---------------------------------------------------------------------------
# Module export
# ---------------------------------------------------------------------------


class TestRunAugmenterChainExport:
    """The chain orchestrator is exported from the canonical module."""

    def test_module_exports_run_augmenter_chain(self) -> None:
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        assert run_augmenter_chain is not None


# ---------------------------------------------------------------------------
# Empty chain / single-augmenter passthrough
# ---------------------------------------------------------------------------


class TestEmptyAndSingleAugmenter:
    """Trivial chain shapes produce expected results."""

    @pytest.mark.asyncio
    async def test_empty_chain_returns_input_tasks_unchanged(self) -> None:
        """No augmenters → AugmentationResult mirrors input tasks."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        tasks = [_make_task("t1"), _make_task("t2")]
        result = await run_augmenter_chain([], prd_analysis=None, tasks=tasks)

        assert result.augmented_tasks == tasks
        assert result.synthesized_ids == []
        assert result.telemetry == {}

    @pytest.mark.asyncio
    async def test_single_augmenter_called_with_inputs(self) -> None:
        """Augmenter receives ``prd_analysis``, ``tasks``, ``contract_artifacts``."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        augmenter = _RecordingAugmenter(name="aug")
        tasks = [_make_task("t1")]
        await run_augmenter_chain(
            [augmenter],
            prd_analysis="PRD",
            tasks=tasks,
            contract_artifacts={"Auth": {"artifacts": []}},
        )

        assert len(augmenter.calls) == 1
        call = augmenter.calls[0]
        assert call["prd_analysis"] == "PRD"
        assert call["tasks"] == tasks
        assert call["contract_artifacts"] == {"Auth": {"artifacts": []}}

    @pytest.mark.asyncio
    async def test_single_augmenter_result_propagates(self) -> None:
        """Augmenter's augmented_tasks become chain output."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        synth = _make_task("synth_1", "Synthesized")
        augmenter = _RecordingAugmenter(
            name="aug",
            tasks_to_append=[synth],
            telemetry={"score": 0.8},
        )
        tasks = [_make_task("t1")]

        result = await run_augmenter_chain([augmenter], prd_analysis=None, tasks=tasks)

        assert result.augmented_tasks == tasks + [synth]
        assert result.synthesized_ids == ["synth_1"]


# ---------------------------------------------------------------------------
# Multi-augmenter chaining
# ---------------------------------------------------------------------------


class TestMultiAugmenterChaining:
    """Augmenters run sequentially; each sees previous augmenter's output."""

    @pytest.mark.asyncio
    async def test_second_augmenter_sees_first_augmenter_tasks(self) -> None:
        """Augmenter B's input includes augmenter A's synthesized tasks.

        This is the load-bearing property — the whole point of the
        chain is that downstream augmenters react to upstream
        synthesis (e.g., spec_coverage scores against the post-
        outcome_coverage graph).
        """
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        synth_a = _make_task("synth_a", "From A")
        aug_a = _RecordingAugmenter(name="A", tasks_to_append=[synth_a])
        aug_b = _RecordingAugmenter(name="B")
        original = _make_task("t1")

        await run_augmenter_chain([aug_a, aug_b], prd_analysis=None, tasks=[original])

        # B's `tasks` argument must include synth_a appended by A
        assert aug_b.calls[0]["tasks"] == [original, synth_a]

    @pytest.mark.asyncio
    async def test_synthesized_ids_accumulate_across_chain(self) -> None:
        """Final synthesized_ids contains IDs from every augmenter."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        aug_a = _RecordingAugmenter(name="A", tasks_to_append=[_make_task("synth_a")])
        aug_b = _RecordingAugmenter(name="B", tasks_to_append=[_make_task("synth_b")])

        result = await run_augmenter_chain(
            [aug_a, aug_b], prd_analysis=None, tasks=[_make_task("t1")]
        )

        assert result.synthesized_ids == ["synth_a", "synth_b"]

    @pytest.mark.asyncio
    async def test_telemetry_namespaced_by_augmenter_name(self) -> None:
        """Telemetry dict is keyed by ``augmenter.name`` per augmenter.

        Namespacing avoids key collisions when a future augmenter
        emits a key that another augmenter already uses.  Consumers
        that need outcome_coverage-shaped data read
        ``result.telemetry["outcome_coverage"]``.
        """
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        aug_a = _RecordingAugmenter(name="outcome_coverage", telemetry={"score": 0.8})
        aug_b = _RecordingAugmenter(name="spec_coverage", telemetry={"missing": 1})

        result = await run_augmenter_chain(
            [aug_a, aug_b], prd_analysis=None, tasks=[_make_task("t1")]
        )

        assert result.telemetry == {
            "outcome_coverage": {"score": 0.8},
            "spec_coverage": {"missing": 1},
        }

    @pytest.mark.asyncio
    async def test_empty_telemetry_omitted_from_namespace(self) -> None:
        """Augmenter that returns empty telemetry contributes no key.

        Saves consumers from a ``{"name": {}}`` no-op entry that
        signals "augmenter ran but produced no data" vs "augmenter
        didn't run".  Those should be distinguishable.
        """
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        aug_a = _RecordingAugmenter(name="A", telemetry={"k": 1})
        aug_b = _RecordingAugmenter(name="B")  # default empty telemetry

        result = await run_augmenter_chain(
            [aug_a, aug_b], prd_analysis=None, tasks=[_make_task("t1")]
        )

        assert "A" in result.telemetry
        assert "B" not in result.telemetry


# ---------------------------------------------------------------------------
# Defense-in-depth: try/except around each augmenter
# ---------------------------------------------------------------------------


class TestExceptionDefenseInDepth:
    """The chain catches per-augmenter exceptions so a buggy augmenter
    cannot crash the decomposer.  This is independent of each
    augmenter's own internal exception handling.
    """

    @pytest.mark.asyncio
    async def test_augmenter_exception_does_not_propagate(self) -> None:
        """Augmenter raise → chain swallows, returns valid result."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        aug = _RecordingAugmenter(name="bad", raises=RuntimeError("boom"))

        # Must not raise
        result = await run_augmenter_chain(
            [aug], prd_analysis=None, tasks=[_make_task("t1")]
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_failed_augmenter_preserves_prior_tasks(self) -> None:
        """When augmenter raises, chain continues with input tasks
        unchanged for that step."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        tasks = [_make_task("t1"), _make_task("t2")]
        aug = _RecordingAugmenter(name="bad", raises=ValueError("oops"))

        result = await run_augmenter_chain([aug], prd_analysis=None, tasks=tasks)

        assert result.augmented_tasks == tasks
        assert result.synthesized_ids == []

    @pytest.mark.asyncio
    async def test_failed_augmenter_omits_telemetry(self) -> None:
        """Failed augmenter contributes no telemetry namespace."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        aug = _RecordingAugmenter(name="bad", raises=RuntimeError("x"))
        result = await run_augmenter_chain(
            [aug], prd_analysis=None, tasks=[_make_task("t1")]
        )
        assert "bad" not in result.telemetry

    @pytest.mark.asyncio
    async def test_chain_continues_after_failure(self) -> None:
        """A failed augmenter does not abort the chain — subsequent
        augmenters still run with the pre-failure tasks.

        This is the load-bearing property.  Without it, one buggy
        future augmenter could silently neutralize all downstream
        augmenters in the chain.
        """
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        bad = _RecordingAugmenter(name="bad", raises=RuntimeError("x"))
        good = _RecordingAugmenter(
            name="good",
            tasks_to_append=[_make_task("synth_good")],
            telemetry={"k": 1},
        )
        original = _make_task("t1")

        result = await run_augmenter_chain(
            [bad, good],
            prd_analysis=None,
            tasks=[original],
        )

        # ``good`` ran with the original tasks (bad's failure was a no-op)
        assert good.calls[0]["tasks"] == [original]
        assert "synth_good" in result.synthesized_ids
        assert result.telemetry == {"good": {"k": 1}}

    @pytest.mark.asyncio
    async def test_exception_logged_with_augmenter_name(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Operators must know which augmenter failed.

        Silent swallow + no log = invisible regression.  Log line
        must include the augmenter's ``name`` so it's grep-able.
        """
        import logging

        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        aug = _RecordingAugmenter(name="myaug", raises=RuntimeError("boom"))
        with caplog.at_level(logging.WARNING):
            await run_augmenter_chain(
                [aug], prd_analysis=None, tasks=[_make_task("t1")]
            )

        assert any("myaug" in rec.getMessage() for rec in caplog.records), (
            "Augmenter name must appear in the warning log so failures "
            "are diagnosable in production."
        )


# ---------------------------------------------------------------------------
# Contract artifacts forwarding
# ---------------------------------------------------------------------------


class TestContractArtifactsForwarding:
    """Each augmenter receives the same ``contract_artifacts``.

    The chain is augmenter-agnostic about contract_artifacts — it
    forwards the same value to every augmenter.  Augmenters that
    don't care (spec_coverage today) ignore the parameter; those that
    do (outcome_coverage) read it.
    """

    @pytest.mark.asyncio
    async def test_contract_artifacts_forwarded_to_all_augmenters(
        self,
    ) -> None:
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        aug_a = _RecordingAugmenter(name="A")
        aug_b = _RecordingAugmenter(name="B")
        artifacts = {"Auth": {"artifacts": [{"content": "..."}]}}

        await run_augmenter_chain(
            [aug_a, aug_b],
            prd_analysis=None,
            tasks=[_make_task("t1")],
            contract_artifacts=artifacts,
        )

        assert aug_a.calls[0]["contract_artifacts"] == artifacts
        assert aug_b.calls[0]["contract_artifacts"] == artifacts

    @pytest.mark.asyncio
    async def test_contract_artifacts_default_none(self) -> None:
        """``contract_artifacts`` defaults to None when omitted."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        aug = _RecordingAugmenter(name="A")
        await run_augmenter_chain([aug], prd_analysis=None, tasks=[_make_task("t1")])
        assert aug.calls[0]["contract_artifacts"] is None


# ---------------------------------------------------------------------------
# Augmenter name uniqueness (Kaia review #4 concern #2, Simon ``f36c49c4``)
# ---------------------------------------------------------------------------


class TestAugmenterNameUniqueness:
    """Augmenter names must be unique within a chain.

    Pre-check rationale: telemetry is namespaced by ``augmenter.name``.
    Two augmenters with the same name silently overwrite each other's
    telemetry slice in the result dict — a confusing failure mode for
    plugin-developers and an observability hole.  The chain validates
    name uniqueness at entry and fails loud with a clear message.
    """

    @pytest.mark.asyncio
    async def test_duplicate_names_raise_value_error(self) -> None:
        """Two augmenters sharing a name → ValueError at chain entry."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        aug_a = _RecordingAugmenter(name="dup")
        aug_b = _RecordingAugmenter(name="dup")

        with pytest.raises(ValueError, match=r"duplicate"):
            await run_augmenter_chain(
                [aug_a, aug_b],
                prd_analysis=None,
                tasks=[_make_task("t1")],
            )

    @pytest.mark.asyncio
    async def test_duplicate_name_error_includes_name(self) -> None:
        """Error message names the duplicate so it's diagnosable."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        aug_a = _RecordingAugmenter(name="outcome_coverage")
        aug_b = _RecordingAugmenter(name="outcome_coverage")

        with pytest.raises(ValueError, match=r"outcome_coverage"):
            await run_augmenter_chain(
                [aug_a, aug_b],
                prd_analysis=None,
                tasks=[_make_task("t1")],
            )

    @pytest.mark.asyncio
    async def test_unique_names_no_error(self) -> None:
        """Distinct names → chain runs normally."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        aug_a = _RecordingAugmenter(name="A")
        aug_b = _RecordingAugmenter(name="B")

        # Must not raise
        result = await run_augmenter_chain(
            [aug_a, aug_b],
            prd_analysis=None,
            tasks=[_make_task("t1")],
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_uniqueness_check_runs_before_first_augment(self) -> None:
        """Validation is at chain entry, before any augmenter executes.

        Important so the failure mode is "fail fast at boot" rather
        than "first augmenter does work, then we crash on the second
        one."  Half-applied augmentation would leak side effects (LLM
        cost, log lines).
        """
        from src.marcus_mcp.coordinator.graph_augmentation import (
            run_augmenter_chain,
        )

        aug_a = _RecordingAugmenter(name="dup")
        aug_b = _RecordingAugmenter(name="dup")

        with pytest.raises(ValueError):
            await run_augmenter_chain(
                [aug_a, aug_b],
                prd_analysis=None,
                tasks=[_make_task("t1")],
            )

        # Neither augmenter ran
        assert aug_a.calls == []
        assert aug_b.calls == []
