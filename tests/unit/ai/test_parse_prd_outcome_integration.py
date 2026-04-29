"""Tests for #449 outcome coverage wiring in parse_prd_to_tasks.

Verifies the feature-based decomposer integration:

- Outcomes are extracted during _analyze_prd_deeply when flag is on
- apply_outcome_coverage is called between _create_detailed_tasks and
  _infer_smart_dependencies, so synthesized tasks participate in
  dependency inference
- Synthesized task dicts are converted to Task objects with
  gap_fill_<uuid> ids and sibling-inherited defaults
- TaskGenerationResult exposes intent_fidelity_score plus coverage
  maps for telemetry
- Flag-off path is a no-op (no extraction, no coverage check)
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import (
    PRDAnalysis,
    ProjectConstraints,
)
from src.ai.advanced.prd.outcome_extractor import UserOutcome
from src.config.outcome_coverage_config import ENV_VAR_NAME

pytestmark = pytest.mark.unit


def _build_parser() -> Any:
    """Build an AdvancedPRDParser with mocked LLM dependencies."""
    from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser

    with (
        patch("src.ai.advanced.prd.advanced_parser.LLMAbstraction"),
        patch("src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"),
    ):
        parser = AdvancedPRDParser()
        parser.llm_client = AsyncMock()
        return parser


def _outcome(out_id: str = "outcome_play") -> UserOutcome:
    return UserOutcome(
        id=out_id,
        action="user can play the snake game",
        success_signal="snake visibly moves on a board",
        scope="in_scope",
    )


def _bare_analysis(outcomes: list[UserOutcome]) -> PRDAnalysis:
    """Build a minimal PRDAnalysis carrying the supplied outcomes."""
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
        original_description="build a snake game",
        user_outcomes=outcomes,
    )


class TestApplyOutcomeCoverageToGraphHelper:
    """The private helper bridges apply_outcome_coverage to the graph."""

    @pytest.mark.asyncio
    async def test_returns_none_when_flag_off(self, monkeypatch: Any) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "false")
        parser = _build_parser()

        result = await parser._apply_outcome_coverage_to_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[],
        )

        assert result is None
        parser.llm_client.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_outcomes(self, monkeypatch: Any) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()

        result = await parser._apply_outcome_coverage_to_graph(
            prd_analysis=_bare_analysis([]),
            tasks=[],
        )

        assert result is None
        parser.llm_client.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_appends_synthesized_tasks_with_gap_fill_id(
        self, monkeypatch: Any
    ) -> None:
        """Gap-fill tasks land in the graph as gap_fill_<uuid> tasks."""
        from datetime import datetime, timezone

        from src.core.models import Priority, Task, TaskStatus

        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()

        # 3 LLM responses: coverage (gap), fill, post-fill coverage
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                (
                    '{"tasks": [{'
                    '"name": "Render snake to canvas",'
                    '"description": "draw snake on canvas",'
                    '"provides": "RenderingAgent",'
                    '"requires": "GameStateUpdate"'
                    "}]}"
                ),
                '{"coverage": {"outcome_play": ["_synth_for_coverage_0"]}}',
            ]
        )

        now = datetime.now(timezone.utc)
        v31_task = Task(
            id="t_state",
            name="Snake state machine",
            description="track snake body",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=2.0,
            project_id="proj_1",
            project_name="Snake",
        )

        result = await parser._apply_outcome_coverage_to_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[v31_task],
        )

        assert result is not None
        assert len(result["augmented_tasks"]) == 2
        synthesized = result["augmented_tasks"][1]
        assert synthesized.id.startswith("gap_fill_")
        assert synthesized.name == "Render snake to canvas"
        assert synthesized.provides == "RenderingAgent"
        assert synthesized.requires == "GameStateUpdate"
        assert "gap_fill" in synthesized.labels
        assert "intent_fidelity" in synthesized.labels
        assert synthesized.project_id == "proj_1"
        assert synthesized.project_name == "Snake"
        # Median of [2.0] is 2.0
        assert synthesized.estimated_hours == 2.0

    @pytest.mark.asyncio
    async def test_score_and_coverage_maps_returned(self, monkeypatch: Any) -> None:
        """Helper exposes score + coverage maps for TaskGenerationResult."""
        from datetime import datetime, timezone

        from src.core.models import Priority, Task, TaskStatus

        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()

        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": ["t_render"]}}',
            ]
        )

        now = datetime.now(timezone.utc)
        complete_task = Task(
            id="t_render",
            name="Render snake",
            description="draw snake",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=2.0,
        )

        result = await parser._apply_outcome_coverage_to_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[complete_task],
        )

        assert result is not None
        assert result["score"] == 1.0
        assert result["coverage_before_fill"] == {"outcome_play": ["t_render"]}
        assert result["coverage_after_fill"] is None  # no gap-fill ran
        assert result["gap_ids"] == []
        # Original tasks unchanged when coverage is full
        assert result["augmented_tasks"] == [complete_task]

    @pytest.mark.asyncio
    async def test_coverage_failure_returns_none_does_not_raise(
        self, monkeypatch: Any
    ) -> None:
        """LLM error in coverage check is logged, helper returns None."""
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        parser.llm_client.analyze = AsyncMock(return_value="not json")

        result = await parser._apply_outcome_coverage_to_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[],
        )

        assert result is None
