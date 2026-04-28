"""End-to-end pipeline test for intent fidelity coverage (issue #449).

Exercises the extractor -> coverage -> gap-fill chain with three mocked
LLM calls (one per stage):

1. Extractor LLM produces user outcomes from the spec
2. Coverage LLM evaluates the v31 task graph against those outcomes
3. Gap-fill LLM generates replacement tasks for uncovered outcomes

The snake_game-v31 case is the headline scenario: ``"build a snake game"``
previously produced a task graph with no rendering task because the
decomposer treated rendering as implicit.  This test proves that with
the outcome layer in place, an honest LLM coverage call surfaces the
gap, gap-fill produces a rendering task, and a re-run of coverage on
the augmented graph confirms full intent fidelity.

Earlier drafts of this test used a hardcoded sync mapper
(``_visual_play_mapper``) that pre-encoded the "rendering verbs"
answer.  That tested the pipeline plumbing but not what an LLM
evaluator would actually conclude — i.e. it proved
"given a correct mapper, the pipeline detects gaps" rather than
"given a snake-game spec, our system catches missing rendering."
The current version mocks the coverage LLM directly so the test
asserts pipeline behavior given honest coverage signals.
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.ai.advanced.prd.outcome_extractor import extract_user_outcomes
from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.outcome_coverage import (
    compute_coverage_with_llm,
    compute_intent_fidelity_score,
    fill_gaps,
    find_gaps,
)

pytestmark = pytest.mark.unit


def _task(task_id: str, name: str, description: str = "") -> Task:
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
        estimated_hours=1.0,
    )


def _llm_returning(payload: str) -> AsyncMock:
    """Build an AsyncMock LLM client that returns the given JSON string."""
    mock = AsyncMock()
    mock.analyze = AsyncMock(return_value=payload)
    return mock


def _llm_with_responses(*payloads: str) -> AsyncMock:
    """Build an AsyncMock that returns each payload in sequence (one per call).

    extract_user_outcomes makes two LLM calls (extraction + verifiability
    filter), so tests that exercise the full extractor must provide
    both payloads in order.
    """
    mock = AsyncMock()
    mock.analyze = AsyncMock(side_effect=list(payloads))
    return mock


class TestSnakeGameRegression:
    """The snake_game-v31 audit scenario: rendering missing from task graph.

    Reproduces the conditions that caused the production failure:

    1. Spec is open-ended (``"build a snake game"``) — no explicit
       mention of rendering, the LLM in the snake-v31 run dropped it
       as "non-essential" under prototype capacity filtering
    2. Decomposer produces logic-only tasks (state, movement, food,
       collision, score) — exactly what the v31 board contained
    3. Outcome extractor sees the spec and returns ``user can play
       the snake game`` (mocked for determinism)
    4. Coverage LLM evaluates each task against the outcome and
       correctly returns no covering tasks (mocked: this is what an
       honest LLM would conclude on the v31 graph — internal logic
       tasks do not produce user-visible movement)
    5. Gap-fill produces a rendering task (mocked)
    6. A second coverage call on the augmented graph confirms the
       new render task covers the outcome — fidelity is 1.0
    """

    @pytest.fixture
    def extractor_llm(self) -> Any:
        """Mocked extractor LLM produces play-game outcome + filter approves it.

        ``extract_user_outcomes`` makes two LLM calls now: extraction
        plus a verifiability self-check.  Both responses are queued.
        """
        return _llm_with_responses(
            '{"outcomes": ['
            '{"id": "outcome_play_game",'
            ' "action": "user can play the snake game in their browser",'
            ' "success_signal": "snake visibly moves on a board, food '
            'appears, score updates after each food eaten",'
            ' "scope": "in_scope"}'
            "]}",
            '{"verdicts": {"outcome_play_game": '
            '{"verifiable": true, "reason": "concrete user-visible action"}}}',
        )

    @pytest.fixture
    def gap_fill_llm(self) -> Any:
        """Mocked gap-fill LLM produces a rendering task for the missing outcome."""
        return _llm_returning(
            '{"tasks": ['
            '{"name": "Render snake to canvas",'
            ' "description": "Subscribe to game-state-update events and '
            "draw the snake body, food, and score on a canvas element "
            "inside the existing game-mount container.  Consumers: "
            'browser DOM."}'
            "]}"
        )

    @pytest.mark.asyncio
    async def test_missing_render_task_is_detected_and_filled(
        self, extractor_llm: Any, gap_fill_llm: Any
    ) -> None:
        """Full pipeline detects the snake-v31 failure and recovers.

        Three LLM calls are mocked, in the order the pipeline issues
        them:

        1. Extractor: returns the play-game outcome
        2. Coverage: returns ``{outcome_play_game: []}`` because no
           v31 task is user-visible (this is what an honest LLM
           evaluator concludes; the test mocks it directly so we
           assert pipeline behavior, not LLM cleverness)
        3. After gap-fill, a second coverage call returns
           ``{outcome_play_game: [t_filled_0]}`` because the new
           rendering task does address the outcome
        """
        # 1. Extract outcomes from spec
        spec = "build a snake game"
        outcomes = await extract_user_outcomes(spec, llm_client=extractor_llm)
        assert any(o.id == "outcome_play_game" for o in outcomes)

        # 2. Decomposer produces logic-only tasks (matches v31 reality)
        v31_tasks = [
            _task("t_state", "Snake state machine", "track snake body"),
            _task("t_movement", "Movement engine", "advance snake one cell per tick"),
            _task("t_food", "Food generator", "place food at random empty cell"),
            _task("t_collision", "Collision detection", "detect wall collisions"),
            _task("t_score", "Score tracker", "increment score on food eaten"),
        ]

        # 3. Coverage LLM correctly identifies that no v31 task covers
        # the play outcome — the mock returns the result an honest
        # evaluator would produce on this graph
        coverage_llm_v31 = _llm_returning('{"coverage": {"outcome_play_game": []}}')
        coverage = await compute_coverage_with_llm(
            outcomes, v31_tasks, llm_client=coverage_llm_v31
        )
        gaps = find_gaps(outcomes, coverage)
        score_before = compute_intent_fidelity_score(outcomes, coverage)

        assert len(gaps) == 1, (
            f"Expected exactly one gap (missing rendering); got "
            f"{[g.id for g in gaps]}"
        )
        assert gaps[0].id == "outcome_play_game"
        assert score_before == 0.0, (
            "v31 had zero rendering tasks — intent fidelity must be 0.0 "
            "before gap-fill, not silently passing"
        )

        # 4. Gap-fill produces replacement tasks
        new_task_dicts = await fill_gaps(spec=spec, gaps=gaps, llm_client=gap_fill_llm)
        assert len(new_task_dicts) >= 1

        # 5. Append the new task and re-run coverage.  The augmented
        # graph now includes a rendering task; the coverage LLM
        # correctly identifies it.
        new_tasks = list(v31_tasks) + [
            _task(f"t_filled_{i}", d["name"], d["description"])
            for i, d in enumerate(new_task_dicts)
        ]
        coverage_llm_after = _llm_returning(
            '{"coverage": {"outcome_play_game": ["t_filled_0"]}}'
        )
        coverage_after = await compute_coverage_with_llm(
            outcomes, new_tasks, llm_client=coverage_llm_after
        )
        score_after = compute_intent_fidelity_score(outcomes, coverage_after)
        assert score_after == 1.0, (
            f"After gap-fill, intent fidelity must be 1.0 — got "
            f"{score_after}.  Gap-fill produced tasks that don't "
            "actually cover the outcome."
        )

    @pytest.mark.asyncio
    async def test_full_coverage_skips_gap_fill_call(
        self, extractor_llm: Any, gap_fill_llm: Any
    ) -> None:
        """When the task graph already covers all outcomes, no LLM call fires.

        Cost-control invariant: gap-fill is paid only when the
        decomposer actually missed something.
        """
        outcomes = await extract_user_outcomes(
            "build a snake game", llm_client=extractor_llm
        )

        # Task graph that DOES include rendering
        complete_tasks = [
            _task("t_state", "Snake state machine", "track snake body"),
            _task(
                "t_render",
                "Render snake to canvas",
                "draw snake, food, and score so the user can play "
                "the snake game in the browser",
            ),
        ]

        coverage_llm = _llm_returning(
            '{"coverage": {"outcome_play_game": ["t_render"]}}'
        )
        coverage = await compute_coverage_with_llm(
            outcomes, complete_tasks, llm_client=coverage_llm
        )
        gaps = find_gaps(outcomes, coverage)
        new_task_dicts = await fill_gaps(
            spec="build a snake game", gaps=gaps, llm_client=gap_fill_llm
        )

        assert gaps == []
        assert new_task_dicts == []
        gap_fill_llm.analyze.assert_not_called()
