"""Unit tests for the user-outcome coverage check (issue #449).

Verifies that:

* :func:`compute_coverage` maps outcomes to the tasks that address them
* :func:`find_gaps` returns only in-scope outcomes with no covering task
* :func:`compute_intent_fidelity_score` reports the right ratio
* :func:`fill_gaps` issues a single LLM call to generate replacement tasks

These tests do not exercise the decomposer end-to-end; integration of the
coverage layer with :mod:`src.marcus_mcp.coordinator.decomposer` is covered
by tests in ``tests/unit/coordinator/test_decomposer_outcome_integration.py``
(future).
"""

from datetime import datetime, timezone
from typing import Any, List
from unittest.mock import AsyncMock

import pytest

from src.ai.advanced.prd.outcome_extractor import UserOutcome
from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.outcome_coverage import (
    compute_coverage,
    compute_coverage_with_llm,
    compute_intent_fidelity_score,
    fill_gaps,
    find_gaps,
    keyword_overlap_mapper,
)

pytestmark = pytest.mark.unit


def _task(task_id: str, name: str, description: str = "") -> Task:
    """Build a minimally-populated :class:`Task` for coverage tests."""
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


def _outcome(
    out_id: str,
    action: str,
    signal: str,
    scope: str = "in_scope",
) -> UserOutcome:
    return UserOutcome(id=out_id, action=action, success_signal=signal, scope=scope)


class TestComputeCoverage:
    """Coverage maps every outcome (by id) to the task ids that address it.

    All tests pass an explicit mapper.  ``compute_coverage`` deliberately
    has no default mapper — the only sync mapper available
    (:func:`keyword_overlap_mapper`) produces false positives on the
    snake_game-v31 case this whole module exists to catch.  Production
    code should use :func:`compute_coverage_with_llm`.
    """

    def test_keyword_overlap_marks_task_as_covering(self) -> None:
        """keyword_overlap_mapper covers outcome via overlapping nouns."""
        outcomes = [
            _outcome(
                "outcome_play",
                "user can play the snake game",
                "snake moves on a board, food appears, score updates",
            )
        ]
        tasks = [
            _task(
                "t1",
                "Render snake game to canvas",
                "Draw the snake, food, and score on a canvas element.",
            ),
        ]
        coverage = compute_coverage(outcomes, tasks, mapper=keyword_overlap_mapper)
        assert coverage["outcome_play"] == ["t1"]

    def test_no_overlap_yields_empty_coverage(self) -> None:
        """When no task addresses an outcome, the list is empty."""
        outcomes = [
            _outcome(
                "outcome_play",
                "user can play the snake game",
                "snake moves on a board, food appears",
            )
        ]
        tasks = [
            _task(
                "t1", "Build authentication service", "JWT tokens and password hashing"
            ),
        ]
        coverage = compute_coverage(outcomes, tasks, mapper=keyword_overlap_mapper)
        assert coverage["outcome_play"] == []

    def test_multiple_tasks_can_cover_one_outcome(self) -> None:
        """An outcome with broad scope may map to several tasks."""
        outcomes = [
            _outcome(
                "outcome_play", "user can play the snake game", "snake moves on a board"
            )
        ]
        tasks = [
            _task("t1", "Render snake on canvas", "draw snake body"),
            _task("t2", "Snake state machine", "moves snake each tick"),
        ]
        coverage = compute_coverage(outcomes, tasks, mapper=keyword_overlap_mapper)
        assert set(coverage["outcome_play"]) == {"t1", "t2"}

    def test_explicit_mapper_overrides_keyword_default(self) -> None:
        """Tests can inject custom mappers besides keyword_overlap_mapper."""
        outcomes = [_outcome("outcome_x", "user can do X", "X is observable")]
        tasks = [_task("t1", "totally unrelated", "nothing matches")]

        def always_match(_outcome: UserOutcome, _task: Task) -> bool:
            return True

        coverage = compute_coverage(outcomes, tasks, mapper=always_match)
        assert coverage["outcome_x"] == ["t1"]

    def test_every_outcome_appears_in_coverage_even_with_zero_tasks(self) -> None:
        """An empty task list produces a coverage dict with empty lists."""
        outcomes = [
            _outcome("o1", "user can do X", "X observable"),
            _outcome("o2", "user can do Y", "Y observable"),
        ]
        coverage = compute_coverage(outcomes, [], mapper=keyword_overlap_mapper)
        assert coverage == {"o1": [], "o2": []}

    def test_mapper_argument_is_required(self) -> None:
        """compute_coverage refuses to run without an explicit mapper.

        This is the footgun guard: the only sync mapper available is
        keyword_overlap_mapper, which produces false positives on the
        snake_game-v31 case.  A contributor importing compute_coverage
        without thinking about which mapper to use would silently
        re-introduce the v31 regression.  Force the choice.
        """
        outcomes = [_outcome("o1", "user can do X", "X observable")]
        tasks = [_task("t1", "task one", "")]
        with pytest.raises(TypeError):
            compute_coverage(outcomes, tasks)  # type: ignore[call-arg]


class TestComputeCoverageWithLLM:
    """LLM-backed coverage: one call maps all outcomes to all tasks."""

    @pytest.fixture
    def llm_returning(self) -> Any:
        def _build(payload: str) -> AsyncMock:
            mock = AsyncMock()
            mock.analyze = AsyncMock(return_value=payload)
            return mock

        return _build

    @pytest.mark.asyncio
    async def test_returns_coverage_dict_from_llm_response(
        self, llm_returning: Any
    ) -> None:
        outcomes = [
            _outcome("o_play", "user can play snake", "snake visibly moves"),
            _outcome("o_score", "user can see score", "score visible"),
        ]
        tasks = [
            _task("t_state", "Snake state machine", "track snake body"),
            _task("t_render", "Render snake to canvas", "draw snake"),
            _task("t_score", "Score display", "render score in DOM"),
        ]
        llm = llm_returning(
            '{"coverage": {' '"o_play": ["t_render"],' '"o_score": ["t_score"]' "}}"
        )

        coverage = await compute_coverage_with_llm(outcomes, tasks, llm)

        assert coverage == {"o_play": ["t_render"], "o_score": ["t_score"]}

    @pytest.mark.asyncio
    async def test_unknown_task_ids_in_response_are_dropped(
        self, llm_returning: Any
    ) -> None:
        """LLM hallucinations don't corrupt the coverage map."""
        outcomes = [_outcome("o1", "user can play", "snake moves")]
        tasks = [_task("t1", "real task", "real desc")]
        llm = llm_returning('{"coverage": {"o1": ["t1", "t_does_not_exist"]}}')

        coverage = await compute_coverage_with_llm(outcomes, tasks, llm)
        assert coverage == {"o1": ["t1"]}

    @pytest.mark.asyncio
    async def test_unknown_outcome_ids_in_response_are_dropped(
        self, llm_returning: Any
    ) -> None:
        outcomes = [_outcome("o1", "user can play", "moves")]
        tasks = [_task("t1", "render", "draw")]
        llm = llm_returning('{"coverage": {"o1": ["t1"], "o_phantom": ["t1"]}}')

        coverage = await compute_coverage_with_llm(outcomes, tasks, llm)
        assert "o_phantom" not in coverage
        assert coverage == {"o1": ["t1"]}

    @pytest.mark.asyncio
    async def test_missing_outcome_in_response_filled_empty(
        self, llm_returning: Any
    ) -> None:
        """LLM that forgets an outcome gets the empty-list default.

        This mirrors find_gaps' contract — every outcome must have an
        entry, even if the LLM skipped it.  Treating "skipped" as
        "uncovered" surfaces the gap; treating it as "covered" would
        hide it.
        """
        outcomes = [
            _outcome("o1", "user can play", "moves"),
            _outcome("o2", "user can score", "visible"),
        ]
        tasks = [_task("t1", "render", "draw")]
        llm = llm_returning('{"coverage": {"o1": ["t1"]}}')

        coverage = await compute_coverage_with_llm(outcomes, tasks, llm)
        assert coverage == {"o1": ["t1"], "o2": []}

    @pytest.mark.asyncio
    async def test_malformed_json_raises(self, llm_returning: Any) -> None:
        outcomes = [_outcome("o1", "user can play", "moves")]
        tasks = [_task("t1", "render", "draw")]
        llm = llm_returning("not json")
        with pytest.raises(ValueError, match="malformed JSON"):
            await compute_coverage_with_llm(outcomes, tasks, llm)

    @pytest.mark.asyncio
    async def test_missing_coverage_key_raises(self, llm_returning: Any) -> None:
        outcomes = [_outcome("o1", "user can play", "moves")]
        tasks = [_task("t1", "render", "draw")]
        llm = llm_returning('{"wrong_key": {}}')
        with pytest.raises(ValueError, match="coverage"):
            await compute_coverage_with_llm(outcomes, tasks, llm)

    @pytest.mark.asyncio
    async def test_no_tasks_returns_empty_lists_without_llm_call(
        self, llm_returning: Any
    ) -> None:
        """When the task graph is empty, no LLM call fires."""
        outcomes = [_outcome("o1", "user can play", "moves")]
        llm = llm_returning('{"coverage": {}}')
        coverage = await compute_coverage_with_llm(outcomes, [], llm)
        assert coverage == {"o1": []}
        llm.analyze.assert_not_called()


class TestFindGaps:
    """Gaps are in-scope outcomes that have no covering tasks."""

    def test_in_scope_uncovered_outcomes_are_gaps(self) -> None:
        outcomes = [
            _outcome("o1", "user can play snake", "snake moves"),
            _outcome("o2", "user can see score", "score visible"),
        ]
        coverage = {"o1": ["t1"], "o2": []}
        gaps = find_gaps(outcomes, coverage)
        assert [g.id for g in gaps] == ["o2"]

    def test_out_of_scope_outcomes_never_count_as_gaps(self) -> None:
        """Out-of-scope outcomes are tracked for audit but excluded from gaps."""
        outcomes = [
            _outcome("o1", "user can log in", "session set", scope="out_of_scope"),
        ]
        coverage = {"o1": []}
        gaps = find_gaps(outcomes, coverage)
        assert gaps == []

    def test_no_gaps_when_all_covered(self) -> None:
        outcomes = [_outcome("o1", "user can play", "moves")]
        coverage = {"o1": ["t1"]}
        assert find_gaps(outcomes, coverage) == []


class TestIntentFidelityScore:
    """Score is covered_in_scope / total_in_scope, in [0.0, 1.0]."""

    def test_full_coverage_scores_one(self) -> None:
        outcomes = [
            _outcome("o1", "user can play", "moves"),
            _outcome("o2", "user can score", "score visible"),
        ]
        coverage = {"o1": ["t1"], "o2": ["t2"]}
        assert compute_intent_fidelity_score(outcomes, coverage) == 1.0

    def test_partial_coverage(self) -> None:
        outcomes = [
            _outcome("o1", "user can play", "moves"),
            _outcome("o2", "user can score", "score visible"),
            _outcome("o3", "user can pause", "pause works"),
            _outcome("o4", "user can restart", "restart works"),
        ]
        coverage = {"o1": ["t1"], "o2": [], "o3": ["t3"], "o4": []}
        assert compute_intent_fidelity_score(outcomes, coverage) == 0.5

    def test_out_of_scope_excluded_from_denominator(self) -> None:
        """Out-of-scope outcomes do not count toward score."""
        outcomes = [
            _outcome("o1", "user can play", "moves"),
            _outcome("o2", "user can log in", "auth", scope="out_of_scope"),
        ]
        coverage = {"o1": ["t1"], "o2": []}
        # 1 in-scope outcome, 1 covered → 1.0
        assert compute_intent_fidelity_score(outcomes, coverage) == 1.0

    def test_no_in_scope_outcomes_yields_one(self) -> None:
        """Empty denominator → vacuously satisfied (score = 1.0).

        The alternative (NaN, 0.0, raise) all surprise consumers.  Since
        there are no in-scope outcomes to fail, treat it as full fidelity.
        """
        outcomes = [
            _outcome("o1", "user can x", "x", scope="out_of_scope"),
        ]
        coverage = {"o1": []}
        assert compute_intent_fidelity_score(outcomes, coverage) == 1.0


class TestFillGaps:
    """Gap-fill issues a single LLM call returning task dicts."""

    @pytest.fixture
    def llm_returning(self) -> Any:
        def _build(payload: str) -> AsyncMock:
            mock = AsyncMock()
            mock.analyze = AsyncMock(return_value=payload)
            return mock

        return _build

    @pytest.mark.asyncio
    async def test_returns_task_dicts_for_each_gap(self, llm_returning: Any) -> None:
        """LLM returns a list of task dicts; one per gap (or more)."""
        gaps = [
            _outcome(
                "outcome_render",
                "user can play the snake game",
                "snake visible on canvas",
            )
        ]
        llm = llm_returning(
            '{"tasks": ['
            '{"name": "Render snake to canvas",'
            ' "description": "Subscribe to game-state events and draw '
            'snake/food/score on a canvas element"}'
            "]}"
        )
        new_tasks = await fill_gaps(
            spec="build a snake game", gaps=gaps, llm_client=llm
        )
        assert len(new_tasks) == 1
        assert new_tasks[0]["name"] == "Render snake to canvas"

    @pytest.mark.asyncio
    async def test_empty_gaps_returns_empty_without_llm_call(
        self, llm_returning: Any
    ) -> None:
        """No gaps means no LLM call — saves cost when coverage is full."""
        llm = llm_returning('{"tasks": []}')
        new_tasks = await fill_gaps(spec="anything", gaps=[], llm_client=llm)
        assert new_tasks == []
        llm.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_malformed_response_raises(self, llm_returning: Any) -> None:
        gaps = [_outcome("o1", "user can do X", "X")]
        llm = llm_returning("not json")
        with pytest.raises(ValueError, match="JSON"):
            await fill_gaps(spec="x", gaps=gaps, llm_client=llm)

    @pytest.mark.asyncio
    async def test_each_returned_task_has_name_and_description(
        self, llm_returning: Any
    ) -> None:
        """A task dict missing required fields is rejected, not silently kept."""
        gaps = [_outcome("o1", "user can do X", "X observable")]
        llm = llm_returning('{"tasks": [{"name": "no description"}]}')
        with pytest.raises(ValueError, match="description"):
            await fill_gaps(spec="x", gaps=gaps, llm_client=llm)

    @pytest.mark.asyncio
    async def test_null_name_field_is_rejected(self, llm_returning: Any) -> None:
        """Null name must raise — must not coerce 'None' through validation.

        Codex P1 regression (PR #453): the original ``str(item.get(...))``
        coercion turned ``None`` into the literal string ``"None"`` which
        is non-empty and silently passed the empty-name check, so callers
        thought gaps were filled with usable tasks when they were not.
        """
        gaps = [_outcome("o1", "user can do X", "X observable")]
        llm = llm_returning(
            '{"tasks": [{"name": null, "description": "valid description"}]}'
        )
        with pytest.raises(ValueError, match=r"'name'.*string"):
            await fill_gaps(spec="x", gaps=gaps, llm_client=llm)

    @pytest.mark.asyncio
    async def test_null_description_field_is_rejected(self, llm_returning: Any) -> None:
        """Null description must raise (same Codex P1 bug, other field)."""
        gaps = [_outcome("o1", "user can do X", "X observable")]
        llm = llm_returning('{"tasks": [{"name": "valid name", "description": null}]}')
        with pytest.raises(ValueError, match=r"'description'.*string"):
            await fill_gaps(spec="x", gaps=gaps, llm_client=llm)

    @pytest.mark.asyncio
    async def test_non_string_name_field_is_rejected(self, llm_returning: Any) -> None:
        """An integer where a string is expected raises (no silent coercion)."""
        gaps = [_outcome("o1", "user can do X", "X observable")]
        llm = llm_returning(
            '{"tasks": [{"name": 42, "description": "valid description"}]}'
        )
        with pytest.raises(ValueError, match=r"'name'.*string"):
            await fill_gaps(spec="x", gaps=gaps, llm_client=llm)

    @pytest.mark.asyncio
    async def test_provides_field_is_emitted_when_supplied(
        self, llm_returning: Any
    ) -> None:
        """fill_gaps surfaces ``provides`` so wiring task generation can use it.

        The decomposer's ``_generate_wiring_tasks`` builds integration
        tasks from provides/requires pairs.  Gap-fill tasks must
        participate in that mechanism — otherwise they sit isolated
        in the DAG with no consumer plumbing.
        """
        gaps = [_outcome("o1", "user can play snake", "snake visibly moves")]
        llm = llm_returning(
            '{"tasks": [{'
            '"name": "Render snake to canvas",'
            '"description": "Draw snake/food/score on canvas element",'
            '"provides": "RenderingAgent.draw"'
            "}]}"
        )
        new_tasks = await fill_gaps(spec="build snake", gaps=gaps, llm_client=llm)
        assert new_tasks[0]["provides"] == "RenderingAgent.draw"

    @pytest.mark.asyncio
    async def test_requires_field_is_emitted_when_supplied(
        self, llm_returning: Any
    ) -> None:
        """``requires`` lets gap-fill tasks consume foundation artifacts."""
        gaps = [_outcome("o1", "user can play snake", "snake visibly moves")]
        llm = llm_returning(
            '{"tasks": [{'
            '"name": "Render snake to canvas",'
            '"description": "Draw snake on canvas",'
            '"requires": "GameStateUpdate"'
            "}]}"
        )
        new_tasks = await fill_gaps(spec="build snake", gaps=gaps, llm_client=llm)
        assert new_tasks[0]["requires"] == "GameStateUpdate"

    @pytest.mark.asyncio
    async def test_provides_and_requires_default_to_none(
        self, llm_returning: Any
    ) -> None:
        """Tasks without contracts get ``provides=None``, ``requires=None``.

        Both fields are optional in the Task model; gap-fill tasks that
        are pure leaves (no consumer, no upstream contract) emit ``None``
        for both rather than raising.
        """
        gaps = [_outcome("o1", "user can do X", "X observable")]
        llm = llm_returning(
            '{"tasks": [{"name": "Standalone task", "description": "no contract"}]}'
        )
        new_tasks = await fill_gaps(spec="x", gaps=gaps, llm_client=llm)
        assert new_tasks[0]["provides"] is None
        assert new_tasks[0]["requires"] is None

    @pytest.mark.asyncio
    async def test_non_string_provides_is_rejected(self, llm_returning: Any) -> None:
        """A list or int for ``provides`` is malformed — must be string or null."""
        gaps = [_outcome("o1", "user can do X", "X observable")]
        llm = llm_returning(
            '{"tasks": [{' '"name": "X", "description": "Y", "provides": ["bad"]' "}]}"
        )
        with pytest.raises(ValueError, match=r"'provides'.*string"):
            await fill_gaps(spec="x", gaps=gaps, llm_client=llm)

    @pytest.mark.asyncio
    async def test_non_string_requires_is_rejected(self, llm_returning: Any) -> None:
        """Same shape check for ``requires``."""
        gaps = [_outcome("o1", "user can do X", "X observable")]
        llm = llm_returning(
            '{"tasks": [{' '"name": "X", "description": "Y", "requires": 42' "}]}"
        )
        with pytest.raises(ValueError, match=r"'requires'.*string"):
            await fill_gaps(spec="x", gaps=gaps, llm_client=llm)
