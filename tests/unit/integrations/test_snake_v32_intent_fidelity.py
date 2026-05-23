"""
End-to-end integration test for the v31→v32 intent-fidelity narrative.

Issue #449 — Phase 6 (the headline test).

Snake-v31 reproduction: a feature-based PRD that describes a playable
snake game decomposes into a state machine + input handler but no
rendering task.  The graph compiles, agents implement clean code, and
the resulting product is invisible — the snake "moves" in unreachable
state with nothing on screen.

Snake-v32 expectation: the outcome-coverage pipeline catches the
missing rendering task at planning time and synthesizes a gap-fill
task.  The orchestrator emits a ``PLANNING_INTENT_FIDELITY`` event so
Cato can surface intent fidelity alongside its other planning swim
lanes.

This test exercises the full chain through
``NaturalLanguageProjectCreator.process_natural_language``:

- ``AdvancedPRDParser.parse_prd_to_tasks`` runs end-to-end
- ``apply_outcome_coverage_to_feature_graph`` runs the real coverage pipeline
- The augmented task list has the synthesized rendering task
- ``_emit_intent_fidelity_event`` publishes the expected payload

Per Kaia's Phase 6 design: assert on the *event payload*, not just
the augmented task list — that's what locks the wire from the typed
``TaskGenerationResult`` fields all the way to the Cato-bound event.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import PRDAnalysis
from src.ai.advanced.prd.outcome_extractor import UserOutcome
from src.config.outcome_coverage_config import ENV_VAR_NAME
from src.core.events import EventTypes
from src.core.models import Priority, Task, TaskStatus
from src.detection.context_detector import MarcusMode

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_SNAKE_OUTCOME_ID = "snake_visible"


def _snake_outcome() -> UserOutcome:
    """The outcome that v31 silently dropped — 'user can see the snake'."""
    return UserOutcome(
        id=_SNAKE_OUTCOME_ID,
        action="user can play the snake game",
        success_signal="snake visibly moves on a 2D board",
        scope="in_scope",
    )


def _snake_prd_analysis() -> PRDAnalysis:
    """Minimal PRDAnalysis carrying the snake outcome.

    The coverage pipeline reads ``user_outcomes`` and
    ``original_description``; everything else is unused here so the
    other fields stay empty.
    """
    return PRDAnalysis(
        functional_requirements=[],
        non_functional_requirements=[],
        technical_constraints=[],
        business_objectives=[],
        user_personas=[],
        success_metrics=[],
        implementation_approach="agile",
        complexity_assessment={},
        risk_factors=[],
        confidence=0.9,
        original_description=(
            "Build a snake game where the user can play. The snake "
            "must visibly move on a 2D board."
        ),
        user_outcomes=[_snake_outcome()],
    )


def _make_task(task_id: str, name: str, description: str) -> Task:
    """Build a Task that ``parse_prd_to_tasks`` could plausibly emit."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name=name,
        description=description,
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=2.0,
        dependencies=[],
        labels=[],
    )


def _v31_decomposer_output() -> list[Task]:
    """Mimic the v31 decomposer output: state + input, no rendering.

    This is the engineered gap.  An LLM-driven coverage check on this
    list against the snake outcome must say 'uncovered'.
    """
    return [
        _make_task(
            "t_state",
            "Snake state machine",
            "Track snake body coordinates and growth.",
        ),
        _make_task(
            "t_input",
            "Input handler",
            "Map keyboard arrows to direction changes.",
        ),
    ]


def _make_creator(state: Any) -> Any:
    """Construct ``NaturalLanguageProjectCreator`` with stubbed I/O.

    AdvancedPRDParser is **not** patched out — the test exercises the
    real ``parse_prd_to_tasks`` orchestration including the coverage
    step.  The parser's LLM client gets stubbed via the parser's
    ``llm_client`` attribute (set after construction).
    """
    from src.integrations.nlp_tools import NaturalLanguageProjectCreator

    mock_kanban = MagicMock()
    mock_ai_engine = MagicMock()

    with (
        patch("src.integrations.nlp_tools.BoardAnalyzer"),
        patch("src.integrations.nlp_tools.ContextDetector"),
        patch("src.ai.advanced.prd.advanced_parser.LLMAbstraction"),
        patch("src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"),
    ):
        creator = NaturalLanguageProjectCreator(
            kanban_client=mock_kanban,
            ai_engine=mock_ai_engine,
            state=state,
        )

    # Stub the parser pipeline steps so only the coverage stage is
    # real.  parse_prd_to_tasks itself is NOT mocked — that's the
    # integration we're locking.
    creator.prd_parser.llm_client = AsyncMock()
    creator.prd_parser._analyze_prd_deeply = AsyncMock(
        return_value=_snake_prd_analysis()
    )
    creator.prd_parser._generate_task_hierarchy = AsyncMock(
        return_value={"snake_epic": ["t_state", "t_input"]}
    )
    creator.prd_parser._create_detailed_tasks = AsyncMock(
        return_value=_v31_decomposer_output()
    )
    creator.prd_parser._infer_smart_dependencies = AsyncMock(return_value=[])
    creator.prd_parser._assess_implementation_risks = AsyncMock(return_value={})
    creator.prd_parser._predict_timeline = AsyncMock(return_value={})
    creator.prd_parser._analyze_resource_requirements = AsyncMock(return_value={})
    creator.prd_parser._generate_success_criteria = AsyncMock(return_value=[])

    # Orchestrator-side stubs (board / context / foundation).
    creator.board_analyzer.analyze_board = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.recommended_mode = MarcusMode.CREATOR
    creator.context_detector.detect_optimal_mode = AsyncMock(return_value=mock_ctx)

    async def _no_foundation(*_args: Any, **_kwargs: Any) -> list[Task]:
        return []

    # type: ignore[method-assign] — stubbing for test isolation
    creator._synthesize_shared_foundation = _no_foundation  # type: ignore

    return creator


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSnakeV32IntentFidelity:
    """Lock the v31→v32 narrative: gap detection, fill, telemetry."""

    @pytest.fixture(autouse=True)
    def _no_spec_coverage(self) -> Any:
        """Stub SpecCoverageAugmenter for these outcome-coverage-only tests.

        Issue #456 Stage 4 wires ``SpecCoverageAugmenter`` alongside
        ``OutcomeCoverageAugmenter`` in the decomposer chain.  These
        v32 tests assert specific task counts and lock outcome-coverage
        behavior, so spec_coverage running concurrently would (a)
        trigger a real LLM call for ``extract_spec_features`` and (b)
        synthesize extra spec_gap tasks that change the assertion math.
        Stub spec_coverage to a no-op for every test in this class.
        """
        with patch(
            "src.marcus_mcp.coordinator.spec_coverage_augmenter." "check_spec_coverage",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_missing_rendering_outcome_rolls_up_to_existing_task(
        self, monkeypatch: Any
    ) -> None:
        """Coverage pipeline catches the missing rendering outcome end-to-end.

        v31 reproduction: decomposer returns state-machine + input
        tasks but no rendering.  Coverage check on these tasks
        against the 'snake_visible' outcome reports gap.  Gap-fill
        produces a rendering behavior, and under #607 step 4 that
        behavior rolls up as a ``completion_criteria`` entry on an
        existing task (last-resort fallback when no integration-
        verification task exists). No new ``gap_fill_<uuid>`` task is
        added to the board.
        """
        from src.marcus_mcp.coordinator.outcome_coverage import (
            OUTCOME_GAP_CRITERION_PREFIX,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "true")

        events = MagicMock()
        events.publish_nowait = AsyncMock()
        state = MagicMock()
        state.events = events
        creator = _make_creator(state=state)

        # Three LLM responses for the coverage pipeline:
        # 1. coverage check on v31 tasks      → uncovered
        # 2. gap-fill                         → 1 rendering behavior
        # 3. coverage check on augmented      → covered by stub only
        creator.prd_parser.llm_client.analyze = AsyncMock(
            side_effect=[
                f'{{"coverage": {{"{_SNAKE_OUTCOME_ID}": []}}}}',
                (
                    '{"tasks": [{'
                    '"name": "Render snake to canvas",'
                    '"description": "Draw the snake body on a 2D canvas '
                    'each tick so the player can see it move.",'
                    '"provides": "RenderingAgent",'
                    '"requires": "GameState"'
                    "}]}"
                ),
                (
                    f'{{"coverage": {{"{_SNAKE_OUTCOME_ID}": '
                    '["_synth_for_coverage_0"]}}'
                ),
            ]
        )

        tasks = await creator.process_natural_language(
            description="Build a snake game",
            project_name="snake-v32",
        )

        # Step 4: no new task; same v31 task list with a criterion
        # appended to one of them.
        assert len(tasks) == 2
        assert tasks[0].id == "t_state"
        assert tasks[1].id == "t_input"
        # At least one of the two tasks carries the rolled-up criterion
        # (precedence: cross-cutting → first task in degraded fallback).
        rollup_criteria = [
            c
            for t in tasks
            for c in (t.completion_criteria or [])
            if c.startswith(OUTCOME_GAP_CRITERION_PREFIX)
        ]
        assert len(rollup_criteria) == 1
        assert "Render snake to canvas" in rollup_criteria[0]

    @pytest.mark.asyncio
    async def test_planning_intent_fidelity_event_emitted_with_payload(
        self, monkeypatch: Any
    ) -> None:
        """The full wire from coverage pipeline to Cato-bound event.

        Phase 5 emission verified end-to-end (not just at the helper
        seam).  This pins the event payload shape so a future refactor
        renaming a ``TaskGenerationResult`` field would fail this test
        rather than silently breaking Cato telemetry.
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")

        events = MagicMock()
        events.publish_nowait = AsyncMock()
        state = MagicMock()
        state.events = events
        creator = _make_creator(state=state)

        creator.prd_parser.llm_client.analyze = AsyncMock(
            side_effect=[
                f'{{"coverage": {{"{_SNAKE_OUTCOME_ID}": []}}}}',
                (
                    '{"tasks": [{'
                    '"name": "Render snake to canvas",'
                    '"description": "Draw the snake on a canvas.",'
                    '"provides": "RenderingAgent",'
                    '"requires": "GameState"'
                    "}]}"
                ),
                (
                    f'{{"coverage": {{"{_SNAKE_OUTCOME_ID}": '
                    '["_synth_for_coverage_0"]}}'
                ),
            ]
        )

        await creator.process_natural_language(
            description="Build a snake game",
            project_name="snake-v32",
        )

        events.publish_nowait.assert_awaited_once()
        args, _kwargs = events.publish_nowait.call_args
        assert args[0] == EventTypes.PLANNING_INTENT_FIDELITY
        assert args[1] == "nlp_orchestrator"
        payload = args[2]
        assert payload["project_name"] == "snake-v32"
        assert payload["decomposer"] == "feature_based"
        # Score on the augmented graph: 1 covered / 1 in-scope = 1.0
        assert payload["intent_fidelity_score"] == 1.0
        # Before-fill map shows the gap; after-fill shows it closed.
        assert payload["coverage_before_fill"] == {_SNAKE_OUTCOME_ID: []}
        assert payload["coverage_after_fill"] == {
            _SNAKE_OUTCOME_ID: ["_synth_for_coverage_0"]
        }
        assert payload["gap_filled_outcomes"] == [_SNAKE_OUTCOME_ID]

    @pytest.mark.asyncio
    async def test_complete_graph_skips_gap_fill_and_scores_full(
        self, monkeypatch: Any
    ) -> None:
        """Negative case: when v31 already covered the outcome, no fill runs.

        If the v31 decomposer had produced a rendering task, the
        coverage check would report full coverage on its first call
        and the pipeline would short-circuit — no gap-fill, no
        recoverage, no synthesized tasks.  Score = 1.0 and event
        still fires (Cato wants the always-1.0 datapoints too).
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")

        events = MagicMock()
        events.publish_nowait = AsyncMock()
        state = MagicMock()
        state.events = events
        creator = _make_creator(state=state)

        # Override the v31 output to include a rendering task.
        complete_tasks = _v31_decomposer_output() + [
            _make_task(
                "t_render",
                "Render snake to canvas",
                "Draw the snake body so the player can see it.",
            )
        ]
        creator.prd_parser._create_detailed_tasks = AsyncMock(
            return_value=complete_tasks
        )

        # Only one LLM call — the initial coverage check.
        creator.prd_parser.llm_client.analyze = AsyncMock(
            side_effect=[
                f'{{"coverage": {{"{_SNAKE_OUTCOME_ID}": ["t_render"]}}}}',
            ]
        )

        tasks = await creator.process_natural_language(
            description="Build a snake game",
            project_name="snake-v32",
        )

        # No gap-fill synthesized — original 3 tasks unchanged.
        assert len(tasks) == 3
        assert {t.id for t in tasks} == {"t_state", "t_input", "t_render"}

        events.publish_nowait.assert_awaited_once()
        payload = events.publish_nowait.call_args.args[2]
        assert payload["intent_fidelity_score"] == 1.0
        assert payload["coverage_before_fill"] == {_SNAKE_OUTCOME_ID: ["t_render"]}
        # No gap-fill ran, so coverage_after_fill is None.
        assert payload["coverage_after_fill"] is None
        assert payload["gap_filled_outcomes"] == []

    @pytest.mark.asyncio
    async def test_flag_off_skips_coverage_pipeline_entirely(
        self, monkeypatch: Any
    ) -> None:
        """When MARCUS_OUTCOME_COVERAGE is off, coverage doesn't run.

        Backward compatibility: existing projects that haven't
        opted in (or have explicitly opted out) get the legacy
        decomposer behavior.  No LLM calls for coverage, no
        synthesized tasks, and the helper no-ops on the emission
        side because intent_fidelity_score is None.
        """
        monkeypatch.setenv(ENV_VAR_NAME, "false")

        events = MagicMock()
        events.publish_nowait = AsyncMock()
        state = MagicMock()
        state.events = events
        creator = _make_creator(state=state)

        # No LLM calls expected — set up a tripwire.
        creator.prd_parser.llm_client.analyze = AsyncMock(
            side_effect=AssertionError(
                "coverage pipeline must not invoke the LLM when flag is off"
            )
        )

        tasks = await creator.process_natural_language(
            description="Build a snake game",
            project_name="snake-v32",
        )

        # v31-style output — no synthesis.
        assert len(tasks) == 2
        assert {t.id for t in tasks} == {"t_state", "t_input"}

        # Helper no-ops because intent_fidelity_score is None when
        # the coverage stage didn't run.
        events.publish_nowait.assert_not_called()

    @pytest.mark.asyncio
    async def test_production_default_is_on_no_env_override(
        self, monkeypatch: Any
    ) -> None:
        """Production default (no env var set) must be ON as of 0.3.6.post1.

        Closes the gap between "tests pass" and "production behavior
        validated".  This test overrides the conftest autouse via
        ``delenv`` so the surrounding env is truly unset, then asserts
        the pipeline runs.  Was previously the OFF-default check; flipped
        when 0.3.6.post1 turned the flag ON by default.
        """
        # Override the conftest autouse: actually delete the var so
        # is_outcome_coverage_enabled() reads its real default.
        monkeypatch.delenv(ENV_VAR_NAME, raising=False)

        events = MagicMock()
        events.publish_nowait = AsyncMock()
        state = MagicMock()
        state.events = events
        creator = _make_creator(state=state)

        # Three LLM responses: coverage check, gap-fill, recoverage.
        # Default-ON means the pipeline runs end-to-end.
        creator.prd_parser.llm_client.analyze = AsyncMock(
            side_effect=[
                f'{{"coverage": {{"{_SNAKE_OUTCOME_ID}": []}}}}',
                (
                    '{"tasks": [{'
                    '"name": "Render snake to canvas",'
                    '"description": "Draw snake on canvas.",'
                    '"provides": "RenderingAgent",'
                    '"requires": "GameState"'
                    "}]}"
                ),
                (
                    f'{{"coverage": {{"{_SNAKE_OUTCOME_ID}": '
                    '["_synth_for_coverage_0"]}}'
                ),
            ]
        )

        tasks = await creator.process_natural_language(
            description="Build a snake game",
            project_name="snake-v32",
        )

        # Pipeline ran end-to-end. Under #607 step 4 the rollup adds
        # NO new task to the board; instead the v31 task list gains a
        # rolled-up criterion on an existing task. Confirm the
        # pipeline ran (criterion appended) and event was emitted.
        from src.marcus_mcp.coordinator.outcome_coverage import (
            OUTCOME_GAP_CRITERION_PREFIX,
        )

        assert len(tasks) == 2  # original v31 graph length unchanged
        rollup_criteria = [
            c
            for t in tasks
            for c in (t.completion_criteria or [])
            if c.startswith(OUTCOME_GAP_CRITERION_PREFIX)
        ]
        assert len(rollup_criteria) == 1
        assert "Render snake to canvas" in rollup_criteria[0]
        # Event emitted with full payload.
        events.publish_nowait.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_coverage_failure_does_not_block_project_creation(
        self, monkeypatch: Any
    ) -> None:
        """Transient LLM errors during coverage must not crash creation.

        Kaia review concern #1 — narrow ``except ValueError`` would
        let a real-world ``asyncio.TimeoutError`` (or any non-
        ValueError raised by the LLM client) bubble up and crash
        project creation.  The contract is "coverage failures must
        never block project creation"; this test pins it.
        """
        import asyncio

        monkeypatch.setenv(ENV_VAR_NAME, "true")

        events = MagicMock()
        events.publish_nowait = AsyncMock()
        state = MagicMock()
        state.events = events
        creator = _make_creator(state=state)

        # Real-world failure mode: LLM call times out.  TimeoutError
        # is NOT a ValueError, so a narrow except would let this
        # bubble up to the outer ``except Exception`` in
        # ``_analyze_prd_deeply`` and fail PRD analysis entirely.
        creator.prd_parser.llm_client.analyze = AsyncMock(
            side_effect=asyncio.TimeoutError("LLM timed out")
        )

        tasks = await creator.process_natural_language(
            description="Build a snake game",
            project_name="snake-v32",
        )

        # Project creation succeeded with the original v31 task list
        # (no synthesis, since coverage degraded gracefully).
        assert len(tasks) == 2
        assert {t.id for t in tasks} == {"t_state", "t_input"}

        # No event emitted — score is None when coverage didn't run.
        events.publish_nowait.assert_not_called()
