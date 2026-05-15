"""
Unit tests for ``_emit_intent_fidelity_event`` (issue #449, Phase 5).

The helper bridges decomposer-side coverage telemetry to Cato by
publishing a ``PLANNING_INTENT_FIDELITY`` event after each decomposer
path returns.  These tests cover:

- Both decomposer paths emit with the expected payload shape.
- No-op when ``intent_fidelity_score`` is ``None`` (coverage didn't
  run, e.g. flag off or no outcomes extracted).
- No-op when ``self.state`` has no ``events`` attribute or events is
  falsy (CLI / test paths without a wired event bus).

The helper itself is implementation-agnostic of which decomposer
called it — these tests pin the payload shape directly rather than
going through the full orchestration pipeline.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.events import EventTypes

pytestmark = pytest.mark.unit


def _make_creator(state: Any = None) -> Any:
    """Build a ``NaturalLanguageProjectCreator`` with mocked I/O."""
    from src.integrations.nlp_tools import NaturalLanguageProjectCreator

    mock_kanban = MagicMock()
    mock_ai_engine = MagicMock()

    with (
        patch("src.integrations.nlp_tools.AdvancedPRDParser"),
        patch("src.integrations.nlp_tools.BoardAnalyzer"),
        patch("src.integrations.nlp_tools.ContextDetector"),
    ):
        creator = NaturalLanguageProjectCreator(
            kanban_client=mock_kanban,
            ai_engine=mock_ai_engine,
            state=state,
        )
    return creator


class TestEmitIntentFidelityEvent:
    """Unit tests for the planning-intent-fidelity event helper."""

    @pytest.mark.asyncio
    async def test_feature_based_payload_shape(self) -> None:
        """Feature-based caller produces the expected event payload."""
        events = MagicMock()
        events.publish_nowait = AsyncMock()
        state = MagicMock()
        state.events = events
        creator = _make_creator(state=state)

        await creator._emit_intent_fidelity_event(
            project_name="snake-v32",
            decomposer="feature_based",
            intent_fidelity_score=0.5,
            coverage_before_fill={"play": []},
            coverage_after_fill={"play": ["gap_fill_abc"]},
            gap_filled_outcomes=["play"],
        )

        events.publish_nowait.assert_awaited_once()
        args, _kwargs = events.publish_nowait.call_args
        assert args[0] == EventTypes.PLANNING_INTENT_FIDELITY
        assert args[1] == "nlp_orchestrator"
        payload = args[2]
        assert payload == {
            "project_name": "snake-v32",
            "decomposer": "feature_based",
            "intent_fidelity_score": 0.5,
            "coverage_before_fill": {"play": []},
            "coverage_after_fill": {"play": ["gap_fill_abc"]},
            "gap_filled_outcomes": ["play"],
        }

    @pytest.mark.asyncio
    async def test_telemetry_forwarder_converts_maps_to_ratios(self) -> None:
        """The PostHog forwarder ships scalar ratios, not coverage maps.

        The internal event carries coverage as maps
        (outcome.id -> covering task ids).  docs/telemetry.md promises
        ``planning_intent_fidelity`` ships float coverage *ratios* and
        an int gap-fill *count*.  This test pins the conversion.

        Falsification recipe: delete the ``_coverage_ratio`` block in
        ``_emit_intent_fidelity_event`` and pass the raw maps/list
        straight to ``fire_planning_intent_fidelity``.  Confirm this
        test fails because the forwarder receives dicts.
        """
        events = MagicMock()
        events.publish_nowait = AsyncMock()
        state = MagicMock()
        state.events = events
        creator = _make_creator(state=state)

        with patch("src.telemetry.events.fire_planning_intent_fidelity") as mock_fire:
            await creator._emit_intent_fidelity_event(
                project_name="snake-v32",
                decomposer="feature_based",
                intent_fidelity_score=0.5,
                # 1 of 2 outcomes covered before -> 0.5
                coverage_before_fill={"play": [], "score": ["t_score"]},
                # 2 of 2 covered after -> 1.0
                coverage_after_fill={
                    "play": ["gap_fill_abc"],
                    "score": ["t_score"],
                },
                gap_filled_outcomes=["play"],
            )

        mock_fire.assert_called_once()
        kwargs = mock_fire.call_args.kwargs
        assert kwargs["coverage_before_fill"] == 0.5
        assert kwargs["coverage_after_fill"] == 1.0
        assert kwargs["gap_filled_outcomes"] == 1
        # Never a map or list.
        assert isinstance(kwargs["coverage_before_fill"], float)
        assert isinstance(kwargs["gap_filled_outcomes"], int)

    @pytest.mark.asyncio
    async def test_telemetry_forwarder_after_defaults_to_before(self) -> None:
        """When no gap-fill ran, ``coverage_after_fill`` equals before.

        ``coverage_after_fill`` is None in the internal event when no
        gap-fill happened.  The forwarder must still ship a float —
        the before-ratio is the honest value.
        """
        events = MagicMock()
        events.publish_nowait = AsyncMock()
        state = MagicMock()
        state.events = events
        creator = _make_creator(state=state)

        with patch("src.telemetry.events.fire_planning_intent_fidelity") as mock_fire:
            await creator._emit_intent_fidelity_event(
                project_name="snake-v32",
                decomposer="contract_first",
                intent_fidelity_score=1.0,
                coverage_before_fill={"play": ["t_render"]},
                coverage_after_fill=None,
                gap_filled_outcomes=[],
            )

        kwargs = mock_fire.call_args.kwargs
        assert kwargs["coverage_before_fill"] == 1.0
        assert kwargs["coverage_after_fill"] == 1.0
        assert kwargs["gap_filled_outcomes"] == 0

    @pytest.mark.asyncio
    async def test_contract_first_payload_shape(self) -> None:
        """Contract-first caller produces the same event shape."""
        events = MagicMock()
        events.publish_nowait = AsyncMock()
        state = MagicMock()
        state.events = events
        creator = _make_creator(state=state)

        await creator._emit_intent_fidelity_event(
            project_name="snake-v32",
            decomposer="contract_first",
            intent_fidelity_score=1.0,
            coverage_before_fill={"play": ["t_render"]},
            coverage_after_fill=None,
            gap_filled_outcomes=[],
        )

        events.publish_nowait.assert_awaited_once()
        args, _kwargs = events.publish_nowait.call_args
        payload = args[2]
        assert payload["decomposer"] == "contract_first"
        assert payload["intent_fidelity_score"] == 1.0
        assert payload["coverage_after_fill"] is None
        assert payload["gap_filled_outcomes"] == []

    @pytest.mark.asyncio
    async def test_noop_when_score_is_none(self) -> None:
        """Coverage-didn't-run case must not publish an event.

        ``intent_fidelity_score is None`` signals that the outcome
        coverage pipeline did not run (flag off, no outcomes
        extracted, or LLM error during coverage check).  The helper
        must stay silent rather than emit a half-populated event.
        """
        events = MagicMock()
        events.publish_nowait = AsyncMock()
        state = MagicMock()
        state.events = events
        creator = _make_creator(state=state)

        await creator._emit_intent_fidelity_event(
            project_name="snake-v32",
            decomposer="feature_based",
            intent_fidelity_score=None,
            coverage_before_fill={},
            coverage_after_fill=None,
            gap_filled_outcomes=[],
        )

        events.publish_nowait.assert_not_called()

    @pytest.mark.asyncio
    async def test_noop_when_state_missing(self) -> None:
        """No state object means no event bus — silent no-op."""
        creator = _make_creator(state=None)

        # Must not raise even though state is None.
        await creator._emit_intent_fidelity_event(
            project_name="snake-v32",
            decomposer="feature_based",
            intent_fidelity_score=0.5,
            coverage_before_fill={"play": []},
            coverage_after_fill=None,
            gap_filled_outcomes=["play"],
        )

    @pytest.mark.asyncio
    async def test_noop_when_state_has_no_events_attr(self) -> None:
        """State without an ``events`` attribute is treated as no-bus.

        Some test harnesses pass a stripped-down state object that
        omits the event system entirely.  The helper must not raise
        ``AttributeError`` — it should silently no-op.
        """

        class StrippedState:
            """State stand-in with no events attribute."""

        creator = _make_creator(state=StrippedState())

        await creator._emit_intent_fidelity_event(
            project_name="snake-v32",
            decomposer="contract_first",
            intent_fidelity_score=0.8,
            coverage_before_fill={"play": ["t1"]},
            coverage_after_fill=None,
            gap_filled_outcomes=[],
        )

    @pytest.mark.asyncio
    async def test_noop_when_events_is_falsy(self) -> None:
        """state.events is None — also a silent no-op."""
        state = MagicMock()
        state.events = None
        creator = _make_creator(state=state)

        await creator._emit_intent_fidelity_event(
            project_name="snake-v32",
            decomposer="feature_based",
            intent_fidelity_score=0.5,
            coverage_before_fill={},
            coverage_after_fill=None,
            gap_filled_outcomes=[],
        )

        # No raise — and nothing to assert on a None.
