"""End-to-end pipeline test for intent fidelity coverage (issue #449).

Exercises the extractor → coverage → gap-fill chain with mocked LLMs.
The snake-game regression case is the headline scenario: a spec of
``"build a snake game"`` previously produced a task graph with no
rendering task because the decomposer treated rendering as implicit.
This test proves that with the outcome layer in place, the missing
rendering task is detected as a gap and filled.
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.ai.advanced.prd.outcome_extractor import UserOutcome, extract_user_outcomes
from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.outcome_coverage import (
    compute_coverage,
    compute_intent_fidelity_score,
    fill_gaps,
    find_gaps,
)

# Visual-action verbs that signal a task produces something user-visible.
# This is the kind of mapper an LLM would produce on the snake-v31 case;
# we encode it explicitly here so the integration test is deterministic
# and does not require a live LLM.  Production usage of compute_coverage
# in the decomposer should pass an LLM-backed mapper.
_VISUAL_ACTION_VERBS = ("render", "draw", "canvas", "display", "show", "paint")


def _visual_play_mapper(outcome: UserOutcome, task: Task) -> bool:
    """Coverage mapper for the play-the-game outcome.

    Returns ``True`` only when a task's name or description contains a
    visual-action verb.  This mirrors what an LLM evaluator would
    conclude on the snake-v31 task graph: only rendering tasks
    actually contribute to the user being able to play.
    """
    if outcome.id != "outcome_play_game":
        # Out of scope for this mapper — defer to default behavior.
        return False
    haystack = (task.name + " " + (task.description or "")).lower()
    return any(verb in haystack for verb in _VISUAL_ACTION_VERBS)


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


class TestSnakeGameRegression:
    """The snake_game-v31 audit scenario: rendering missing from task graph.

    Reproduces the conditions that caused the production failure:

    1. Spec is open-ended ("build a snake game") — no explicit mention
       of rendering, the LLM in the snake-v31 run dropped it as
       "non-essential" under prototype capacity filtering
    2. Decomposer produces logic-only tasks (state, movement, food,
       collision, score) — exactly what the v31 board contained
    3. Outcome extractor sees the spec and returns ``user can play
       the snake game`` (this is the kind of outcome an LLM correctly
       produces from "snake game"; we mock it for determinism)
    4. Coverage check finds no task addresses the play outcome
    5. Gap-fill produces a rendering task
    6. Final intent_fidelity_score after gap-fill is 1.0
    """

    @pytest.fixture
    def extractor_llm(self) -> Any:
        """Mocked extractor LLM produces the play-game outcome."""
        mock = AsyncMock()
        mock.analyze = AsyncMock(
            return_value=(
                '{"outcomes": ['
                '{"id": "outcome_play_game",'
                ' "action": "user can play the snake game in their browser",'
                ' "success_signal": "snake visibly moves on a board, food '
                'appears, score updates after each food eaten",'
                ' "scope": "in_scope"}'
                "]}"
            )
        )
        return mock

    @pytest.fixture
    def gap_fill_llm(self) -> Any:
        """Mocked gap-fill LLM produces a rendering task for the missing outcome."""
        mock = AsyncMock()
        mock.analyze = AsyncMock(
            return_value=(
                '{"tasks": ['
                '{"name": "Render snake to canvas",'
                ' "description": "Subscribe to game-state-update events and '
                "draw the snake body, food, and score on a canvas element "
                "inside the existing game-mount container.  Consumers: "
                'browser DOM."}'
                "]}"
            )
        )
        return mock

    @pytest.mark.asyncio
    async def test_missing_render_task_is_detected_and_filled(
        self, extractor_llm: Any, gap_fill_llm: Any
    ) -> None:
        """Full pipeline detects the snake-v31 failure and recovers."""
        # 1. Extract outcomes from spec
        spec = "build a snake game"
        outcomes = await extract_user_outcomes(spec, llm_client=extractor_llm)
        assert any(o.id == "outcome_play_game" for o in outcomes)

        # 2. Decomposer produces logic-only tasks (matches v31 reality:
        # game state, movement, food, collision, score — but no rendering)
        v31_tasks = [
            _task("t_state", "Snake state machine", "track snake body and direction"),
            _task("t_movement", "Movement engine", "advance snake one cell per tick"),
            _task("t_food", "Food generator", "place food at random empty cell"),
            _task(
                "t_collision", "Collision detection", "detect wall and self collisions"
            ),
            _task("t_score", "Score tracker", "increment score on food eaten"),
        ]

        # 3. Coverage check identifies the gap.  We use the
        # _visual_play_mapper because the default keyword heuristic is
        # too permissive for this case (it would match on the shared
        # "snake"/"food"/"score" domain nouns); production decomposer
        # integration will use an LLM-backed mapper that reaches the
        # same conclusion as our explicit visual-action-verb mapper.
        coverage = compute_coverage(outcomes, v31_tasks, mapper=_visual_play_mapper)
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
        # The new task description must mention rendering or canvas —
        # otherwise the gap-fill LLM produced something unrelated
        rendering_keywords = ("render", "canvas", "draw", "display")
        assert any(
            kw in new_task_dicts[0]["description"].lower() for kw in rendering_keywords
        ), f"Gap-fill task does not address rendering: {new_task_dicts[0]}"

        # 5. After appending the new task to the graph, fidelity is 1.0.
        # Same mapper used as before for consistency.
        new_tasks = list(v31_tasks) + [
            _task(f"t_filled_{i}", d["name"], d["description"])
            for i, d in enumerate(new_task_dicts)
        ]
        coverage_after = compute_coverage(
            outcomes, new_tasks, mapper=_visual_play_mapper
        )
        score_after = compute_intent_fidelity_score(outcomes, coverage_after)
        assert score_after == 1.0, (
            f"After gap-fill, intent fidelity must be 1.0 — got {score_after}. "
            "Gap-fill produced tasks that don't actually cover the outcome."
        )

    @pytest.mark.asyncio
    async def test_full_coverage_skips_gap_fill_call(
        self, extractor_llm: Any, gap_fill_llm: Any
    ) -> None:
        """When the task graph already covers all outcomes, no LLM call fires.

        This is the cost-control invariant: gap-fill is paid only when
        the decomposer actually missed something.
        """
        outcomes = await extract_user_outcomes(
            "build a snake game", llm_client=extractor_llm
        )

        # Task graph that DOES include rendering — same five logic
        # tasks plus a render task whose description shares keywords
        # ("snake", "play", "score", "food") with the outcome
        complete_tasks = [
            _task("t_state", "Snake state machine", "track snake body"),
            _task(
                "t_render",
                "Render snake to canvas",
                "draw snake, food, and score so the user can play "
                "the snake game in the browser",
            ),
        ]

        coverage = compute_coverage(
            outcomes, complete_tasks, mapper=_visual_play_mapper
        )
        gaps = find_gaps(outcomes, coverage)
        new_task_dicts = await fill_gaps(
            spec="build a snake game", gaps=gaps, llm_client=gap_fill_llm
        )

        assert gaps == []
        assert new_task_dicts == []
        gap_fill_llm.analyze.assert_not_called()
