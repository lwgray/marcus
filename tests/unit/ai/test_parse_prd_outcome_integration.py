"""Tests for #449 outcome coverage wiring in parse_prd_to_tasks.

Verifies the feature-based decomposer integration:

- Outcomes are extracted during _analyze_prd_deeply when flag is on
- ``apply_outcome_coverage_to_feature_graph`` runs between
  ``_create_detailed_tasks`` and ``_infer_smart_dependencies`` so
  synthesized tasks participate in dependency inference
- Synthesized task dicts are converted to Task objects with
  ``gap_fill_<uuid>`` ids and sibling-inherited defaults
- TaskGenerationResult exposes intent_fidelity_score plus coverage
  maps for telemetry
- Flag-off path is a no-op (no extraction, no coverage check)

Issue #456 Stage 5: the lifted module function
``apply_outcome_coverage_to_feature_graph`` replaces the formerly-
private ``AdvancedPRDParser._apply_outcome_coverage_to_graph``.  The
function returns the canonical :class:`AugmentationResult` shape
directly; tests assert on ``result.telemetry`` (the
PLANNING_INTENT_FIDELITY-shaped dict) instead of ``result.coverage``.
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


class TestApplyOutcomeCoverageToFeatureGraph:
    """The lifted module function bridges apply_outcome_coverage to the graph."""

    @pytest.mark.asyncio
    async def test_no_op_when_flag_off(self, monkeypatch: Any) -> None:
        """Flag off → empty-telemetry passthrough, no LLM call."""
        from src.marcus_mcp.coordinator.outcome_coverage import (
            apply_outcome_coverage_to_feature_graph,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "false")
        llm_client = AsyncMock()

        result = await apply_outcome_coverage_to_feature_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[],
            llm_client=llm_client,
        )

        assert result.telemetry == {}
        assert result.synthesized_ids == []
        llm_client.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_op_when_no_outcomes(self, monkeypatch: Any) -> None:
        """No in-scope outcomes → empty-telemetry passthrough."""
        from src.marcus_mcp.coordinator.outcome_coverage import (
            apply_outcome_coverage_to_feature_graph,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "true")
        llm_client = AsyncMock()

        result = await apply_outcome_coverage_to_feature_graph(
            prd_analysis=_bare_analysis([]),
            tasks=[],
            llm_client=llm_client,
        )

        assert result.telemetry == {}
        llm_client.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_appends_synthesized_tasks_with_gap_fill_id(
        self, monkeypatch: Any
    ) -> None:
        """Gap-fill tasks land in the graph as gap_fill_<uuid> tasks."""
        from datetime import datetime, timezone

        from src.core.models import Priority, Task, TaskStatus
        from src.marcus_mcp.coordinator.outcome_coverage import (
            apply_outcome_coverage_to_feature_graph,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "true")
        llm_client = AsyncMock()
        # 3 LLM responses: coverage (gap), fill, post-fill coverage
        llm_client.analyze = AsyncMock(
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

        result = await apply_outcome_coverage_to_feature_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[v31_task],
            llm_client=llm_client,
        )

        assert len(result.augmented_tasks) == 2
        synthesized = result.augmented_tasks[1]
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
        # Synthesized ID surfaces in synthesized_ids
        assert result.synthesized_ids == [synthesized.id]

    @pytest.mark.asyncio
    async def test_score_and_coverage_maps_in_telemetry(self, monkeypatch: Any) -> None:
        """Telemetry exposes the canonical PLANNING_INTENT_FIDELITY keys."""
        from datetime import datetime, timezone

        from src.core.models import Priority, Task, TaskStatus
        from src.marcus_mcp.coordinator.outcome_coverage import (
            apply_outcome_coverage_to_feature_graph,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "true")
        llm_client = AsyncMock()
        llm_client.analyze = AsyncMock(
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

        result = await apply_outcome_coverage_to_feature_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[complete_task],
            llm_client=llm_client,
        )

        assert result.telemetry["intent_fidelity_score"] == 1.0
        assert result.telemetry["coverage_before_fill"] == {
            "outcome_play": ["t_render"]
        }
        assert result.telemetry["coverage_after_fill"] is None
        assert result.telemetry["gap_filled_outcomes"] == []
        # No gap-fill tasks synthesized — task graph cardinality is
        # unchanged.  Task identity may not match (issue #523 Slice A
        # enriches mapped tasks' acceptance_criteria with the
        # success_signal so the WorkAnalyzer static gate has the
        # user-observable signal to validate against), so compare the
        # task id rather than the whole object.
        assert len(result.augmented_tasks) == 1
        assert result.augmented_tasks[0].id == complete_task.id
        # Signal landed on the mapped task's acceptance_criteria.
        from src.marcus_mcp.coordinator.outcome_coverage import (
            SIGNAL_CRITERION_PREFIX,
        )

        assert any(
            c.startswith(SIGNAL_CRITERION_PREFIX)
            and "snake visibly moves on a board" in c
            for c in result.augmented_tasks[0].acceptance_criteria
        )

    @pytest.mark.asyncio
    async def test_coverage_failure_no_op_does_not_raise(
        self, monkeypatch: Any
    ) -> None:
        """LLM error in coverage check is logged; passthrough result."""
        from src.marcus_mcp.coordinator.outcome_coverage import (
            apply_outcome_coverage_to_feature_graph,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "true")
        llm_client = AsyncMock()
        llm_client.analyze = AsyncMock(return_value="not json")

        result = await apply_outcome_coverage_to_feature_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[],
            llm_client=llm_client,
        )

        # Empty telemetry signals coverage didn't successfully complete
        assert result.telemetry == {}
        assert result.augmented_tasks == []

    @pytest.mark.asyncio
    async def test_signal_lands_on_synthesized_gap_fill_task(
        self, monkeypatch: Any
    ) -> None:
        """Issue #523 Slice A: gap-fill tasks gain the success_signal too.

        When the initial graph misses an outcome and a gap-fill task is
        synthesized, ``coverage_after_fill`` maps the outcome to the
        synthesized task.  The enrichment pass must decorate the gap-fill
        task with the signal so WorkAnalyzer validates against it when
        the agent completes it — same gate as for organically-decomposed
        covering tasks.
        """
        from datetime import datetime, timezone

        from src.core.models import Priority, Task, TaskStatus
        from src.marcus_mcp.coordinator.outcome_coverage import (
            SIGNAL_CRITERION_PREFIX,
            apply_outcome_coverage_to_feature_graph,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "true")
        llm_client = AsyncMock()
        # 3 LLM responses: initial coverage (gap), gap-fill synthesis,
        # post-fill coverage (now covered by the synthesized task).
        llm_client.analyze = AsyncMock(
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
        seed_task = Task(
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
        )

        result = await apply_outcome_coverage_to_feature_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[seed_task],
            llm_client=llm_client,
        )

        # Original seed task is not in the coverage mapping → not
        # enriched.  Pre-existing identity check confirms passthrough.
        assert result.augmented_tasks[0] is seed_task

        # The synthesized gap-fill task IS in coverage_after_fill →
        # enriched with the success_signal.
        synthesized = result.augmented_tasks[1]
        assert synthesized.id.startswith("gap_fill_")
        signal_criteria = [
            c
            for c in (synthesized.acceptance_criteria or [])
            if c.startswith(SIGNAL_CRITERION_PREFIX)
        ]
        assert len(signal_criteria) == 1
        assert "snake visibly moves on a board" in signal_criteria[0]


class TestParsePrdToTasksCallsAugmenterChain:
    """Lock in the integration: parse_prd_to_tasks awaits the chain.

    The augmenter chain runs between Step 3 (``_create_detailed_tasks``)
    and Step 4 (``_infer_smart_dependencies``).  This test fixates that
    the lifted feature-graph function gets called via the chain.
    """

    @pytest.mark.asyncio
    async def test_lifted_function_called_during_parse_prd_to_tasks(
        self, monkeypatch: Any
    ) -> None:
        """parse_prd_to_tasks awaits apply_outcome_coverage_to_feature_graph.

        Mocks the entire downstream pipeline so the test focuses on
        whether the lifted function is reached via the augmenter chain.
        """
        from datetime import datetime, timezone

        from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser
        from src.core.models import Priority, Task, TaskStatus
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "true")

        with (
            patch("src.ai.advanced.prd.advanced_parser.LLMAbstraction"),
            patch("src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"),
        ):
            parser = AdvancedPRDParser()
            parser.llm_client = AsyncMock()

            # PRD analysis returns minimal valid analysis with one outcome.
            stub_analysis = _bare_analysis([_outcome()])
            parser._analyze_prd_deeply = AsyncMock(return_value=stub_analysis)

            # Stub task hierarchy / detailed tasks / dep inference.
            parser._generate_task_hierarchy = AsyncMock(return_value={"e1": ["t1"]})
            now = datetime.now(timezone.utc)
            stub_task = Task(
                id="t1",
                name="task one",
                description="desc",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=2.0,
            )
            parser._create_detailed_tasks = AsyncMock(return_value=[stub_task])
            parser._infer_smart_dependencies = AsyncMock(return_value=[])
            parser._assess_implementation_risks = AsyncMock(return_value={})
            parser._predict_timeline = AsyncMock(return_value={})
            parser._analyze_resource_requirements = AsyncMock(return_value={})
            parser._generate_success_criteria = AsyncMock(return_value=[])

            # Spy on the lifted function — return a populated
            # AugmentationResult so the orchestration completes.
            stub_chain_result = AugmentationResult(
                augmented_tasks=[stub_task],
                synthesized_ids=[],
                telemetry={
                    "intent_fidelity_score": 1.0,
                    "coverage_before_fill": {"outcome_play": ["t1"]},
                    "coverage_after_fill": None,
                    "gap_filled_outcomes": [],
                },
            )

            with (
                patch(
                    "src.marcus_mcp.coordinator.outcome_coverage_augmenter."
                    "apply_outcome_coverage_to_feature_graph",
                    new_callable=AsyncMock,
                    return_value=stub_chain_result,
                ) as mock_apply,
                patch(
                    "src.ai.advanced.prd.advanced_parser.SpecCoverageAugmenter"
                ) as mock_spec_class,
            ):
                # Stub spec_coverage augmenter so it doesn't make
                # network calls; we're testing the outcome-coverage
                # integration here.
                mock_spec_aug = AsyncMock()
                mock_spec_aug.name = "spec_coverage"
                mock_spec_aug.augment = AsyncMock(
                    return_value=AugmentationResult(augmented_tasks=[stub_task])
                )
                mock_spec_class.return_value = mock_spec_aug

                constraints = ProjectConstraints()
                result = await parser.parse_prd_to_tasks(
                    "build a snake game", constraints
                )

        # The lifted function was reached via the augmenter chain
        mock_apply.assert_awaited_once()

        # And its telemetry flowed into TaskGenerationResult
        assert result.intent_fidelity_score == 1.0
        assert result.coverage_before_fill == {"outcome_play": ["t1"]}
