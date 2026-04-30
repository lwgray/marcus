"""
Unit tests for ``OutcomeCoverageAugmenter`` (issue #456 — Stage 2).

Stage 2 wraps the existing
``AdvancedPRDParser._apply_outcome_coverage_to_graph`` and
``_apply_outcome_coverage_to_contract_graph`` helpers behind the
``GraphAugmenter`` Protocol from Stage 1.

**Critical concern from Kaia Stage-1 review (Simon ``0b97ec30``):**
the wrapper must produce ``telemetry`` dict keys matching the
existing ``PLANNING_INTENT_FIDELITY`` event payload exactly.  Silent
key drift would break Cato consumers who already expect:

- ``intent_fidelity_score``
- ``coverage_before_fill``
- ``coverage_after_fill``
- ``gap_filled_outcomes``

Tests pin those keys explicitly and the v32 behavior-preservation
snapshot guards against subtle migration drift.

Stage 2 contract: the wrapper delegates to the existing helpers — no
behavior change.  Stage 3 will switch the decomposer call sites to
the augmenter chain; Stage 5 will remove the now-unused helpers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.models import Priority, Task, TaskStatus

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(task_id: str, name: str = "Implement Foo") -> Task:
    """Minimal Task for wrapper tests."""
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
        labels=["contract_first", "implementation"],
        source_type="contract_first",
    )


def _gap_fill_task(task_id: str, name: str = "Render snake to canvas") -> Task:
    """Synthesized gap-fill task (matches what _build_gap_fill_task produces)."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name=name,
        description="draw on canvas",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=2.0,
        labels=["gap_fill", "intent_fidelity"],
    )


def _make_parser_outcome_coverage(
    augmented_tasks: List[Task],
    *,
    intent_fidelity_score: Optional[float] = None,
    coverage_before_fill: Optional[Dict[str, List[str]]] = None,
    coverage_after_fill: Optional[Dict[str, List[str]]] = None,
    gap_outcome_ids: Optional[List[str]] = None,
) -> Any:
    """Build a ParserOutcomeCoverage with optional OutcomeCoverageResult."""
    from src.ai.advanced.prd.advanced_parser import ParserOutcomeCoverage
    from src.ai.advanced.prd.outcome_extractor import UserOutcome
    from src.marcus_mcp.coordinator.outcome_coverage import (
        OutcomeCoverageResult,
    )

    coverage: Optional[OutcomeCoverageResult] = None
    if intent_fidelity_score is not None:
        gaps = [
            UserOutcome(id=oid, action="...", success_signal="...", scope="in_scope")
            for oid in (gap_outcome_ids or [])
        ]
        coverage = OutcomeCoverageResult(
            synthesized_tasks=[],
            intent_fidelity_score=intent_fidelity_score,
            coverage_before_fill=coverage_before_fill or {},
            coverage_after_fill=coverage_after_fill,
            gaps=gaps,
        )
    return ParserOutcomeCoverage(augmented_tasks=augmented_tasks, coverage=coverage)


def _make_mock_parser() -> Any:
    """Build a MagicMock standing in for AdvancedPRDParser."""
    parser = MagicMock()
    parser._apply_outcome_coverage_to_graph = AsyncMock()
    parser._apply_outcome_coverage_to_contract_graph = AsyncMock()
    return parser


def _make_prd_analysis() -> Any:
    """Minimal PRDAnalysis for wrapper input."""
    from src.ai.advanced.prd.advanced_parser import PRDAnalysis

    return PRDAnalysis(
        functional_requirements=[],
        non_functional_requirements=[],
        technical_constraints=[],
        business_objectives=[],
        user_personas=[],
        success_metrics=[],
        implementation_approach="iterative",
        complexity_assessment={},
        risk_factors=[],
        confidence=0.9,
        original_description="build a snake game",
    )


# ---------------------------------------------------------------------------
# Protocol satisfaction
# ---------------------------------------------------------------------------


class TestOutcomeCoverageAugmenterProtocolSatisfaction:
    """Augmenter satisfies the GraphAugmenter Protocol."""

    def test_module_exports_augmenter(self) -> None:
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        assert OutcomeCoverageAugmenter is not None

    def test_augmenter_is_graph_augmenter(self) -> None:
        """``isinstance(augmenter, GraphAugmenter)`` returns True."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            GraphAugmenter,
        )
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        augmenter = OutcomeCoverageAugmenter(parser=_make_mock_parser())
        assert isinstance(augmenter, GraphAugmenter)

    def test_name_is_outcome_coverage(self) -> None:
        """Canonical name keys telemetry / log lines / event filters."""
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        augmenter = OutcomeCoverageAugmenter(parser=_make_mock_parser())
        assert augmenter.name == "outcome_coverage"


# ---------------------------------------------------------------------------
# Path dispatch: feature-based vs contract-first
# ---------------------------------------------------------------------------


class TestPathDispatch:
    """Wrapper picks the right helper based on ``contract_artifacts``."""

    @pytest.mark.asyncio
    async def test_feature_based_path_when_no_contract_artifacts(self) -> None:
        """``contract_artifacts=None`` → feature-based helper called."""
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        parser = _make_mock_parser()
        parser._apply_outcome_coverage_to_graph.return_value = (
            _make_parser_outcome_coverage(augmented_tasks=[_make_task("t1")])
        )
        augmenter = OutcomeCoverageAugmenter(parser=parser)

        await augmenter.augment(
            prd_analysis=_make_prd_analysis(),
            tasks=[_make_task("t1")],
            contract_artifacts=None,
        )

        parser._apply_outcome_coverage_to_graph.assert_awaited_once()
        parser._apply_outcome_coverage_to_contract_graph.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_contract_first_path_when_contract_artifacts_provided(
        self,
    ) -> None:
        """``contract_artifacts`` non-None → contract-first helper called."""
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        parser = _make_mock_parser()
        parser._apply_outcome_coverage_to_contract_graph.return_value = (
            _make_parser_outcome_coverage(augmented_tasks=[_make_task("t1")])
        )
        augmenter = OutcomeCoverageAugmenter(parser=parser)

        await augmenter.augment(
            prd_analysis=_make_prd_analysis(),
            tasks=[_make_task("t1")],
            contract_artifacts={"Auth": {"artifacts": [{"content": "..."}]}},
        )

        parser._apply_outcome_coverage_to_contract_graph.assert_awaited_once()
        parser._apply_outcome_coverage_to_graph.assert_not_awaited()


# ---------------------------------------------------------------------------
# Telemetry key pinning (CRITICAL — Kaia Stage-1 concern #3)
# ---------------------------------------------------------------------------


class TestTelemetryKeyPinning:
    """Wrapper telemetry dict keys must match PLANNING_INTENT_FIDELITY
    event payload exactly.

    Existing event payload at ``nlp_tools.py:396-399``:

    .. code-block:: python

        {
            "project_name": project_name,
            "decomposer": decomposer,
            "intent_fidelity_score": intent_fidelity_score,
            "coverage_before_fill": coverage_before_fill,
            "coverage_after_fill": coverage_after_fill,
            "gap_filled_outcomes": gap_filled_outcomes,
        }

    Stage 2 wrapper produces the latter four (project_name +
    decomposer are orchestrator-side fields).  Silent key drift would
    break Cato consumers — these tests are the contract.
    """

    @pytest.mark.asyncio
    async def test_telemetry_has_intent_fidelity_score_key(self) -> None:
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        parser = _make_mock_parser()
        parser._apply_outcome_coverage_to_graph.return_value = (
            _make_parser_outcome_coverage(
                augmented_tasks=[_make_task("t1")],
                intent_fidelity_score=0.75,
            )
        )
        augmenter = OutcomeCoverageAugmenter(parser=parser)

        result = await augmenter.augment(
            prd_analysis=_make_prd_analysis(),
            tasks=[_make_task("t1")],
        )
        assert "intent_fidelity_score" in result.telemetry
        assert result.telemetry["intent_fidelity_score"] == 0.75

    @pytest.mark.asyncio
    async def test_telemetry_has_coverage_before_fill_key(self) -> None:
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        parser = _make_mock_parser()
        coverage_before = {"outcome_play": ["t1"], "outcome_pause": []}
        parser._apply_outcome_coverage_to_graph.return_value = (
            _make_parser_outcome_coverage(
                augmented_tasks=[_make_task("t1")],
                intent_fidelity_score=1.0,
                coverage_before_fill=coverage_before,
            )
        )
        augmenter = OutcomeCoverageAugmenter(parser=parser)

        result = await augmenter.augment(
            prd_analysis=_make_prd_analysis(),
            tasks=[_make_task("t1")],
        )
        assert "coverage_before_fill" in result.telemetry
        assert result.telemetry["coverage_before_fill"] == coverage_before

    @pytest.mark.asyncio
    async def test_telemetry_has_coverage_after_fill_key(self) -> None:
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        parser = _make_mock_parser()
        coverage_after = {"outcome_play": ["t1", "gap_fill_xyz"]}
        parser._apply_outcome_coverage_to_graph.return_value = (
            _make_parser_outcome_coverage(
                augmented_tasks=[_make_task("t1"), _gap_fill_task("gap_fill_xyz")],
                intent_fidelity_score=1.0,
                coverage_after_fill=coverage_after,
            )
        )
        augmenter = OutcomeCoverageAugmenter(parser=parser)

        result = await augmenter.augment(
            prd_analysis=_make_prd_analysis(),
            tasks=[_make_task("t1")],
        )
        assert "coverage_after_fill" in result.telemetry
        assert result.telemetry["coverage_after_fill"] == coverage_after

    @pytest.mark.asyncio
    async def test_telemetry_has_gap_filled_outcomes_key(self) -> None:
        """``gap_filled_outcomes`` is the list of UserOutcome IDs that
        had gaps in the initial coverage check.

        Per existing event payload at ``nlp_tools.py:399`` and the
        emission helper at ``nlp_tools.py:644``, the value is a list
        of outcome IDs (strings) — extracted from
        ``coverage.gaps`` (list of UserOutcome) via list comprehension.
        Wrapper must perform the same extraction.
        """
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        parser = _make_mock_parser()
        parser._apply_outcome_coverage_to_graph.return_value = (
            _make_parser_outcome_coverage(
                augmented_tasks=[_make_task("t1")],
                intent_fidelity_score=0.5,
                gap_outcome_ids=["outcome_play", "outcome_score"],
            )
        )
        augmenter = OutcomeCoverageAugmenter(parser=parser)

        result = await augmenter.augment(
            prd_analysis=_make_prd_analysis(),
            tasks=[_make_task("t1")],
        )
        assert "gap_filled_outcomes" in result.telemetry
        # Must be list of outcome IDs, not full UserOutcome objects
        assert result.telemetry["gap_filled_outcomes"] == [
            "outcome_play",
            "outcome_score",
        ]

    @pytest.mark.asyncio
    async def test_telemetry_keys_match_event_payload_exactly(self) -> None:
        """Anti-regression: pin the exact set of telemetry keys.

        If a Stage-2 refactor adds extra keys or removes existing
        ones, downstream consumers (Cato) break silently.  This test
        fails loud on either side of drift.
        """
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        parser = _make_mock_parser()
        parser._apply_outcome_coverage_to_graph.return_value = (
            _make_parser_outcome_coverage(
                augmented_tasks=[_make_task("t1")],
                intent_fidelity_score=1.0,
                coverage_before_fill={"outcome_play": ["t1"]},
                coverage_after_fill=None,
                gap_outcome_ids=[],
            )
        )
        augmenter = OutcomeCoverageAugmenter(parser=parser)

        result = await augmenter.augment(
            prd_analysis=_make_prd_analysis(),
            tasks=[_make_task("t1")],
        )

        expected_keys = {
            "intent_fidelity_score",
            "coverage_before_fill",
            "coverage_after_fill",
            "gap_filled_outcomes",
        }
        assert set(result.telemetry.keys()) == expected_keys, (
            f"Telemetry keys must match PLANNING_INTENT_FIDELITY event "
            f"payload exactly.  Expected {expected_keys}, "
            f"got {set(result.telemetry.keys())}"
        )


# ---------------------------------------------------------------------------
# No-op result handling (flag off / no outcomes / LLM failure)
# ---------------------------------------------------------------------------


class TestNoOpResult:
    """When the helper returns ``None`` (coverage didn't run), the
    wrapper produces a passthrough result: input tasks, no synthesized
    IDs, empty telemetry."""

    @pytest.mark.asyncio
    async def test_helper_returns_none_passthrough_input_tasks(self) -> None:
        """Wrapper passthrough behavior when coverage doesn't run."""
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        parser = _make_mock_parser()
        parser._apply_outcome_coverage_to_graph.return_value = None
        augmenter = OutcomeCoverageAugmenter(parser=parser)

        input_tasks = [_make_task("t1"), _make_task("t2")]
        result = await augmenter.augment(
            prd_analysis=_make_prd_analysis(),
            tasks=input_tasks,
        )

        assert result.augmented_tasks == input_tasks
        assert result.synthesized_ids == []
        assert result.telemetry == {}

    @pytest.mark.asyncio
    async def test_helper_returns_none_does_not_mutate_input(self) -> None:
        """Passthrough must return the same list contents but not mutate
        the caller's list as a side effect."""
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        parser = _make_mock_parser()
        parser._apply_outcome_coverage_to_graph.return_value = None
        augmenter = OutcomeCoverageAugmenter(parser=parser)

        input_tasks = [_make_task("t1"), _make_task("t2")]
        snapshot_ids = [t.id for t in input_tasks]

        await augmenter.augment(
            prd_analysis=_make_prd_analysis(),
            tasks=input_tasks,
        )

        assert [t.id for t in input_tasks] == snapshot_ids


# ---------------------------------------------------------------------------
# Synthesized ID detection
# ---------------------------------------------------------------------------


class TestSynthesizedIds:
    """``AugmentationResult.synthesized_ids`` must list the IDs of
    tasks the augmenter added (subset of ``augmented_tasks``)."""

    @pytest.mark.asyncio
    async def test_no_gap_fill_synthesized_ids_empty(self) -> None:
        """When no synthesis ran, synthesized_ids is empty list."""
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        parser = _make_mock_parser()
        input_tasks = [_make_task("t1"), _make_task("t2")]
        parser._apply_outcome_coverage_to_graph.return_value = (
            _make_parser_outcome_coverage(
                augmented_tasks=input_tasks,
                intent_fidelity_score=1.0,
            )
        )
        augmenter = OutcomeCoverageAugmenter(parser=parser)

        result = await augmenter.augment(
            prd_analysis=_make_prd_analysis(), tasks=input_tasks
        )
        assert result.synthesized_ids == []

    @pytest.mark.asyncio
    async def test_gap_fill_ids_listed_in_synthesized_ids(self) -> None:
        """When the helper appended gap-fill tasks, their IDs appear
        in synthesized_ids (and only those — not the original tasks)."""
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        parser = _make_mock_parser()
        input_tasks = [_make_task("t1"), _make_task("t2")]
        gap_fill = _gap_fill_task("gap_fill_abc123")
        parser._apply_outcome_coverage_to_graph.return_value = (
            _make_parser_outcome_coverage(
                augmented_tasks=input_tasks + [gap_fill],
                intent_fidelity_score=1.0,
            )
        )
        augmenter = OutcomeCoverageAugmenter(parser=parser)

        result = await augmenter.augment(
            prd_analysis=_make_prd_analysis(), tasks=input_tasks
        )
        assert result.synthesized_ids == ["gap_fill_abc123"]


# ---------------------------------------------------------------------------
# v32 behavior preservation snapshot (Kaia regression-canary)
# ---------------------------------------------------------------------------


class TestV32BehaviorPreservation:
    """Snapshot the wrapper's output for the v32-shaped scenario.

    v32 narrative: outcome ``snake_visible`` initially uncovered →
    gap-fill synthesizes a rendering task → recoverage shows
    ``snake_visible`` covered by the synthesized task.  Score 1.0
    after fill.

    These tests assert the wrapper's ``AugmentationResult`` carries
    the same data the existing event-emission code reads off
    ``ParserOutcomeCoverage`` directly.  If Stage 3 swaps the call
    site to use the wrapper, the ``PLANNING_INTENT_FIDELITY`` event
    payload must be byte-identical.
    """

    @pytest.mark.asyncio
    async def test_v32_scenario_telemetry_matches_event_payload(self) -> None:
        """v32-shape input → wrapper telemetry matches the
        keys/values the existing emission helper reads from
        ``ParserOutcomeCoverage``."""
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        parser = _make_mock_parser()

        # v32 fixture: 2 input tasks, 1 synthesized gap-fill, 1 outcome
        input_tasks = [
            _make_task("t_state", "Snake state machine"),
            _make_task("t_input", "Input handler"),
        ]
        gap_fill = _gap_fill_task("gap_fill_abc123", "Render snake to canvas")

        parser._apply_outcome_coverage_to_graph.return_value = (
            _make_parser_outcome_coverage(
                augmented_tasks=input_tasks + [gap_fill],
                intent_fidelity_score=1.0,
                coverage_before_fill={"snake_visible": []},
                coverage_after_fill={"snake_visible": ["_synth_for_coverage_0"]},
                gap_outcome_ids=["snake_visible"],
            )
        )
        augmenter = OutcomeCoverageAugmenter(parser=parser)

        result = await augmenter.augment(
            prd_analysis=_make_prd_analysis(),
            tasks=input_tasks,
        )

        # Pin the exact event-payload-shaped values
        assert result.telemetry == {
            "intent_fidelity_score": 1.0,
            "coverage_before_fill": {"snake_visible": []},
            "coverage_after_fill": {"snake_visible": ["_synth_for_coverage_0"]},
            "gap_filled_outcomes": ["snake_visible"],
        }
        # Augmented graph contains 3 tasks: 2 input + 1 synth
        assert len(result.augmented_tasks) == 3
        assert result.synthesized_ids == ["gap_fill_abc123"]


# ---------------------------------------------------------------------------
# Stage 2 contract: helpers still callable directly
# ---------------------------------------------------------------------------


class TestStage2NoBehaviorChange:
    """Stage 2 only adds a wrapper.  The existing helpers on
    ``AdvancedPRDParser`` must remain callable directly so Stage 3 can
    switch the decomposer call sites in a separate commit.
    """

    def test_outcome_coverage_helpers_still_exist(self) -> None:
        """``_apply_outcome_coverage_to_graph`` and
        ``_apply_outcome_coverage_to_contract_graph`` are still
        methods on AdvancedPRDParser at Stage 2.  Stage 3-5 will
        eventually remove them once all callers migrate.
        """
        from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser

        assert hasattr(AdvancedPRDParser, "_apply_outcome_coverage_to_graph")
        assert hasattr(AdvancedPRDParser, "_apply_outcome_coverage_to_contract_graph")
