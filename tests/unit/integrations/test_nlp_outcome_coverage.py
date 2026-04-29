"""Unit tests for the orchestrator-level outcome coverage hook (issue #449).

``NaturalLanguageProjectCreator._apply_outcome_coverage`` is the
production integration point for the intent fidelity pipeline:

1. Reads outcomes from the shared PRD analysis (or extracts late
   if unavailable).
2. Computes coverage via :func:`compute_coverage_with_llm`.
3. Identifies gaps among in-scope outcomes.
4. Synthesizes replacement tasks via :func:`fill_gaps`, each carrying
   ``provides`` / ``requires`` so the existing wiring infrastructure
   integrates them with the rest of the graph.
5. Builds full :class:`Task` objects from the gap-fill dicts.
6. Recomputes coverage on the augmented graph and reports
   ``intent_fidelity_score``.

Behind ``MARCUS_OUTCOME_COVERAGE``: when off, the helper returns the
input task list unchanged with no LLM calls.
"""

from datetime import datetime, timezone
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import PRDAnalysis
from src.ai.advanced.prd.outcome_extractor import UserOutcome
from src.config.outcome_coverage_config import ENV_VAR_NAME
from src.core.models import Priority, Task, TaskStatus

pytestmark = pytest.mark.unit


def _task(
    task_id: str,
    name: str,
    description: str = "",
    estimated_hours: float = 2.0,
) -> Task:
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
        estimated_hours=estimated_hours,
        project_id="proj_1",
        project_name="Snake Game",
    )


def _make_analysis_with_outcomes(outcomes: List[UserOutcome]) -> PRDAnalysis:
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
        user_outcomes=outcomes,
    )


def _make_creator() -> Any:
    """Build a creator instance with mocked dependencies for unit tests."""
    from src.integrations.nlp_tools import NaturalLanguageProjectCreator

    with patch("src.integrations.nlp_tools.AdvancedPRDParser") as mock_parser_class:
        mock_parser = MagicMock()
        mock_parser.llm_client = AsyncMock()
        mock_parser_class.return_value = mock_parser
        creator = NaturalLanguageProjectCreator(
            kanban_client=MagicMock(),
            ai_engine=MagicMock(),
            state=MagicMock(),
        )
        creator.prd_parser = mock_parser
        return creator


class TestApplyOutcomeCoverageFlagOff:
    """Flag off → helper is a pure pass-through."""

    @pytest.mark.asyncio
    async def test_returns_tasks_unchanged_when_flag_off(
        self, monkeypatch: Any
    ) -> None:
        monkeypatch.delenv(ENV_VAR_NAME, raising=False)
        creator = _make_creator()
        tasks = [_task("t1", "Task 1"), _task("t2", "Task 2")]

        result = await creator._apply_outcome_coverage(
            tasks=tasks,
            description="anything",
            prd_analysis=_make_analysis_with_outcomes([]),
        )

        assert result == tasks
        creator.prd_parser.llm_client.analyze.assert_not_called()


class TestApplyOutcomeCoverageFlagOnNoGaps:
    """Flag on, full coverage → no gap-fill, no graph change."""

    @pytest.mark.asyncio
    async def test_full_coverage_returns_input_unchanged(
        self, monkeypatch: Any
    ) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        creator = _make_creator()
        tasks = [
            _task("t_render", "Render snake to canvas", "draw snake"),
        ]
        outcomes = [
            UserOutcome(
                id="outcome_play_game",
                action="user can play snake",
                success_signal="snake visibly moves",
                scope="in_scope",
            )
        ]

        creator.prd_parser.llm_client.analyze = AsyncMock(
            return_value=('{"coverage": {"outcome_play_game": ["t_render"]}}')
        )

        result = await creator._apply_outcome_coverage(
            tasks=tasks,
            description="build snake",
            prd_analysis=_make_analysis_with_outcomes(outcomes),
        )

        # Same task list, no synthesized additions
        assert result == tasks
        # One LLM call total: the coverage check (no fill, no recompute)
        assert creator.prd_parser.llm_client.analyze.await_count == 1


class TestApplyOutcomeCoverageFlagOnWithGaps:
    """Flag on, gaps exist → fill_gaps synthesizes Task objects with contracts."""

    @pytest.mark.asyncio
    async def test_gap_fill_appends_task_with_provides_requires(
        self, monkeypatch: Any
    ) -> None:
        """Snake-v31 scenario: missing rendering task is detected and filled.

        End-to-end through the helper: extract -> coverage finds gap ->
        fill produces task with provides/requires -> Task object built
        with those contracts -> appended to graph -> recompute coverage.
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        creator = _make_creator()
        v31_tasks = [
            _task("t_state", "Snake state machine", "track snake body"),
            _task("t_movement", "Movement engine", "advance snake"),
            _task("t_food", "Food generator", "place food"),
        ]
        outcomes = [
            UserOutcome(
                id="outcome_play_game",
                action="user can play snake",
                success_signal="snake visibly moves on a board",
                scope="in_scope",
            )
        ]

        # Three sequential LLM calls: coverage (gap found),
        # fill_gaps (returns rendering task with provides/requires),
        # post-fill coverage recomputation (gap closed).
        creator.prd_parser.llm_client.analyze = AsyncMock(
            side_effect=[
                # 1. Coverage: no v31 task addresses the play outcome
                '{"coverage": {"outcome_play_game": []}}',
                # 2. Gap-fill: produces a rendering task with contracts
                (
                    '{"tasks": [{'
                    '"name": "Render snake to canvas",'
                    '"description": "Subscribe to game-state events and '
                    'draw snake/food/score on canvas",'
                    '"provides": "RenderingAgent.draw",'
                    '"requires": "GameStateUpdate"'
                    "}]}"
                ),
                # 3. Post-fill coverage: the new task IS covering
                '{"coverage": {"outcome_play_game": ["GAP_FILL_ID"]}}',
            ]
        )

        result = await creator._apply_outcome_coverage(
            tasks=v31_tasks,
            description="build a snake game",
            prd_analysis=_make_analysis_with_outcomes(outcomes),
        )

        assert len(result) == 4, "Expected v31 tasks + 1 synthesized task"
        gap_fill_task = result[-1]
        assert gap_fill_task.name == "Render snake to canvas"
        rendering_words = ("render", "draw", "canvas", "display")
        haystack = (gap_fill_task.name + " " + gap_fill_task.description).lower()
        assert any(
            word in haystack for word in rendering_words
        ), f"Gap-fill task does not address rendering: {gap_fill_task}"
        assert gap_fill_task.provides == "RenderingAgent.draw"
        assert gap_fill_task.requires == "GameStateUpdate"
        assert "gap_fill" in gap_fill_task.labels
        assert "intent_fidelity" in gap_fill_task.labels
        assert gap_fill_task.id.startswith("gap_fill_")
        assert gap_fill_task.status == TaskStatus.TODO
        # Inherits project context from siblings
        assert gap_fill_task.project_id == "proj_1"
        assert gap_fill_task.project_name == "Snake Game"

    @pytest.mark.asyncio
    async def test_gap_fill_task_inherits_median_estimated_hours(
        self, monkeypatch: Any
    ) -> None:
        """Synthesized tasks get a sensible hour estimate from siblings."""
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        creator = _make_creator()
        siblings = [
            _task("t1", "Task 1", "", estimated_hours=2.0),
            _task("t2", "Task 2", "", estimated_hours=4.0),
            _task("t3", "Task 3", "", estimated_hours=6.0),
        ]
        outcomes = [
            UserOutcome(
                id="o1",
                action="user can do X",
                success_signal="X visible",
                scope="in_scope",
            )
        ]
        creator.prd_parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"o1": []}}',
                (
                    '{"tasks": [{'
                    '"name": "Filled task", "description": "fill the gap"'
                    "}]}"
                ),
                '{"coverage": {"o1": ["filled"]}}',
            ]
        )

        result = await creator._apply_outcome_coverage(
            tasks=siblings,
            description="x",
            prd_analysis=_make_analysis_with_outcomes(outcomes),
        )

        # Median of [2, 4, 6] is 4.0
        assert result[-1].estimated_hours == 4.0

    @pytest.mark.asyncio
    async def test_gap_fill_task_provides_requires_default_to_none(
        self, monkeypatch: Any
    ) -> None:
        """Tasks without contract metadata get None — wiring leaves them alone."""
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        creator = _make_creator()
        outcomes = [
            UserOutcome(
                id="o1",
                action="user can do X",
                success_signal="X visible",
                scope="in_scope",
            )
        ]
        creator.prd_parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"o1": []}}',
                (
                    '{"tasks": [{"name": "Standalone", '
                    '"description": "no contracts"}]}'
                ),
                '{"coverage": {"o1": ["x"]}}',
            ]
        )

        result = await creator._apply_outcome_coverage(
            tasks=[_task("t1", "T1")],
            description="x",
            prd_analysis=_make_analysis_with_outcomes(outcomes),
        )

        assert result[-1].provides is None
        assert result[-1].requires is None


class TestApplyOutcomeCoverageRobustness:
    """Failures in any LLM step degrade gracefully — never block creation."""

    @pytest.mark.asyncio
    async def test_late_extraction_when_prd_analysis_lacks_outcomes(
        self, monkeypatch: Any
    ) -> None:
        """When prd_analysis is None, helper extracts outcomes inline."""
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        creator = _make_creator()
        tasks = [_task("t1", "Task 1")]

        with patch(
            "src.integrations.nlp_tools.extract_user_outcomes",
            new=AsyncMock(
                return_value=[
                    UserOutcome(
                        id="o1",
                        action="user can do X",
                        success_signal="X visible",
                        scope="in_scope",
                    )
                ]
            ),
        ) as mock_extract:
            creator.prd_parser.llm_client.analyze = AsyncMock(
                return_value='{"coverage": {"o1": ["t1"]}}'
            )
            result = await creator._apply_outcome_coverage(
                tasks=tasks, description="x", prd_analysis=None
            )

        mock_extract.assert_awaited_once()
        assert result == tasks

    @pytest.mark.asyncio
    async def test_late_extraction_failure_returns_tasks_unchanged(
        self, monkeypatch: Any
    ) -> None:
        """Extraction failure logs a warning, returns original tasks."""
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        creator = _make_creator()
        tasks = [_task("t1", "Task 1")]

        with patch(
            "src.integrations.nlp_tools.extract_user_outcomes",
            new=AsyncMock(side_effect=ValueError("LLM exploded")),
        ):
            result = await creator._apply_outcome_coverage(
                tasks=tasks, description="x", prd_analysis=None
            )

        assert result == tasks
        creator.prd_parser.llm_client.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_outcomes_skips_coverage_check(self, monkeypatch: Any) -> None:
        """When outcomes list is empty, no coverage call fires."""
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        creator = _make_creator()
        tasks = [_task("t1", "Task 1")]

        result = await creator._apply_outcome_coverage(
            tasks=tasks,
            description="x",
            prd_analysis=_make_analysis_with_outcomes([]),
        )

        # When prd_analysis exists but carries no outcomes, helper
        # falls through to late extraction.  Provide a mock for that.
        with patch(
            "src.integrations.nlp_tools.extract_user_outcomes",
            new=AsyncMock(return_value=[]),
        ):
            result = await creator._apply_outcome_coverage(
                tasks=tasks,
                description="x",
                prd_analysis=_make_analysis_with_outcomes([]),
            )

        assert result == tasks

    @pytest.mark.asyncio
    async def test_coverage_failure_returns_tasks_unchanged(
        self, monkeypatch: Any
    ) -> None:
        """LLM coverage failure logs a warning, returns original tasks."""
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        creator = _make_creator()
        tasks = [_task("t1", "Task 1")]
        outcomes = [
            UserOutcome(
                id="o1",
                action="user can do X",
                success_signal="X",
                scope="in_scope",
            )
        ]

        creator.prd_parser.llm_client.analyze = AsyncMock(return_value="not json")

        result = await creator._apply_outcome_coverage(
            tasks=tasks,
            description="x",
            prd_analysis=_make_analysis_with_outcomes(outcomes),
        )

        assert result == tasks

    @pytest.mark.asyncio
    async def test_fill_failure_returns_original_when_gap_present(
        self, monkeypatch: Any
    ) -> None:
        """Gap-fill failure leaves gaps unaddressed but does not block."""
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        creator = _make_creator()
        tasks = [_task("t1", "Task 1")]
        outcomes = [
            UserOutcome(
                id="o1",
                action="user can do X",
                success_signal="X",
                scope="in_scope",
            )
        ]
        creator.prd_parser.llm_client.analyze = AsyncMock(
            side_effect=[
                # Coverage finds gap
                '{"coverage": {"o1": []}}',
                # Gap-fill returns malformed JSON
                "not json",
            ]
        )

        result = await creator._apply_outcome_coverage(
            tasks=tasks,
            description="x",
            prd_analysis=_make_analysis_with_outcomes(outcomes),
        )

        # Original tasks unchanged — fill failure logged, no synthesis
        assert result == tasks
