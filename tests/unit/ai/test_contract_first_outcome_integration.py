"""Tests for #449 outcome coverage wiring in decompose_by_contract.

Verifies the contract-first decomposer integration:

- apply_outcome_coverage_to_contract_graph passes contract_artifacts
  to fill_gaps so synthesized provides/requires/responsibility quote
  real interface names from the existing contracts
- Synthesized contract-first tasks get responsibility set from the
  gap-fill output (same convention as native contract-first tasks)
- Synthesized tasks get ['gap_fill', 'intent_fidelity', 'contract']
  labels (the 'contract' marker distinguishes contract-aware
  synthesis from feature-based gap-fill in audits)
- decompose_by_contract returns AugmentationResult with the augmented
  task list and namespaced telemetry (issue #456 Stage 5 — formerly
  ParserOutcomeCoverage on a side-channel attribute).
"""

from datetime import datetime, timezone
from typing import Any, List
from unittest.mock import AsyncMock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import PRDAnalysis
from src.ai.advanced.prd.outcome_extractor import UserOutcome
from src.config.outcome_coverage_config import ENV_VAR_NAME
from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.outcome_coverage import (
    apply_outcome_coverage_to_contract_graph,
)

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


def _contract_artifacts() -> dict[str, Any]:
    """Sample contract artifacts in the shape _generate_contracts_by_domain emits."""
    return {
        "rendering": {
            "artifacts": [
                {
                    "filename": "Render.ts",
                    "relative_path": "src/contracts/Render.ts",
                    "content": "interface RenderingAgent { draw(state) }",
                }
            ]
        }
    }


def _contract_task(task_id: str = "t_engine") -> Task:
    """Native contract-first Task with responsibility set."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name="Game Engine",
        description="produces GameStateUpdate",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=4.0,
        provides="GameStateUpdate",
        responsibility="implements GameEngine from src/contracts/GameState.ts",
        project_id="proj_1",
        project_name="Snake",
    )


class TestContractCoverageHelper:
    """The contract-first coverage helper surfaces responsibility on output."""

    @pytest.mark.asyncio
    async def test_returns_none_when_flag_off(self, monkeypatch: Any) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "false")
        parser = _build_parser()

        result = await apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
            llm_client=parser.llm_client,
        )

        assert result.telemetry == {}
        parser.llm_client.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_outcomes(self, monkeypatch: Any) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()

        result = await apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
            llm_client=parser.llm_client,
        )

        assert result.telemetry == {}
        parser.llm_client.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_gap_fill_rolls_up_to_existing_contract_task_criteria(
        self, monkeypatch: Any
    ) -> None:
        """#607 step 4 (contract-first): gap-fill output rolls up onto
        an existing contract task's completion_criteria.

        Replaces the pre-step-4 ``TestContractCoverageHelper`` tests
        that asserted the structure of ``_build_contract_gap_fill_task``
        — that builder is removed in step 4. Routing precedence and
        criterion text are covered in
        ``tests/unit/coordinator/test_gap_fill_criteria_rollup.py``;
        this test only locks in that the contract-first applier wires
        through the rollup, not the synthesis path.
        """
        from src.marcus_mcp.coordinator.outcome_coverage import (
            OUTCOME_GAP_CRITERION_PREFIX,
            SIGNAL_CRITERION_PREFIX,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        # Post-fill includes the native contract task as co-anchor so
        # the criterion routes to it via precedence 1.
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                (
                    '{"tasks": [{'
                    '"name": "Render snake to canvas",'
                    '"description": "draw snake on canvas",'
                    '"responsibility": "implements R from r.ts"'
                    "}]}"
                ),
                (
                    '{"coverage": {"outcome_play": ['
                    '"_synth_for_coverage_0", "t_contract"]}}'
                ),
            ]
        )

        result = await apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
            llm_client=parser.llm_client,
        )

        # Step 4: same-length graph; native contract task carries the
        # rollup criterion AND the success_signal.
        assert len(result.augmented_tasks) == 1
        assert result.synthesized_ids == []
        anchor = result.augmented_tasks[0]
        rollup_criteria = [
            c
            for c in (anchor.completion_criteria or [])
            if c.startswith(OUTCOME_GAP_CRITERION_PREFIX)
        ]
        assert len(rollup_criteria) == 1
        assert "Render snake to canvas" in rollup_criteria[0]
        signal_criteria = [
            c
            for c in (anchor.acceptance_criteria or [])
            if c.startswith(SIGNAL_CRITERION_PREFIX)
        ]
        assert len(signal_criteria) == 1


class TestDecomposeByContractReturnShape:
    """decompose_by_contract returns AugmentationResult uniformly.

    Issue #456 Stage 3 routes the contract-first decomposer through
    the augmenter chain.  These tests lock in the post-Stage-3 shape:

    - ``result.augmented_tasks`` is always populated with the contract
      task list (plus any synthesized gap-fill tasks)
    - ``result.telemetry`` is empty when the outcome-coverage pipeline
      didn't run (flag off / no outcomes / LLM error)
    - ``result.telemetry["outcome_coverage"]`` carries
      ``intent_fidelity_score`` + sibling keys when coverage ran
    """

    @pytest.fixture(autouse=True)
    def _no_spec_coverage(self) -> Any:
        """Stub SpecCoverageAugmenter — these tests assert shape only.

        Issue #456 Stage 4 wires SpecCoverageAugmenter into the
        decomposer chain alongside OutcomeCoverageAugmenter.  Without
        stubbing, ``check_spec_coverage`` would make a real LLM call
        and synthesize spec_gap tasks that contaminate the
        return-shape assertions in this class.  Tests that need real
        spec_coverage behavior live in
        ``test_spec_coverage_augmenter.py``.
        """
        with patch(
            "src.marcus_mcp.coordinator.spec_coverage_augmenter." "check_spec_coverage",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock:
            yield mock

    @staticmethod
    def _stub_engine_output() -> dict[str, Any]:
        """Canonical contract-first LLM response with one task."""
        return {
            "tasks": [
                {
                    "name": "Engine",
                    "description": "build engine",
                    "estimated_minutes": 240,
                    "provides": "GameStateUpdate",
                    "requires": "None",
                    "responsibility": (
                        "implements GameEngine from src/contracts/GameState.ts"
                    ),
                    "contract_file": "src/contracts/GameState.ts",
                    "acceptance_criteria": [],
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_returns_augmentation_result_with_empty_telemetry(
        self, monkeypatch: Any
    ) -> None:
        """Flag off → result.telemetry is empty, augmented_tasks populated."""
        from src.ai.advanced.prd.advanced_parser import ProjectConstraints
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "false")
        parser = _build_parser()

        with patch(
            "src.ai.advanced.prd.advanced_parser.AIAnalysisEngine"
        ) as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine.generate_structured_response = AsyncMock(
                return_value=self._stub_engine_output()
            )
            mock_engine_class.return_value = mock_engine

            result = await parser.decompose_by_contract(
                prd_analysis=_bare_analysis([_outcome()]),
                contract_artifacts=_contract_artifacts(),
                constraints=ProjectConstraints(),
            )

        assert isinstance(result, AugmentationResult)
        # Coverage didn't run (flag off) → no telemetry slice
        assert "outcome_coverage" not in result.telemetry
        # augmented_tasks still has the one contract task
        assert len(result.augmented_tasks) == 1
        assert result.augmented_tasks[0].name == "Engine"

    @pytest.mark.asyncio
    async def test_returns_augmentation_result_with_outcome_coverage_telemetry(
        self, monkeypatch: Any
    ) -> None:
        """Flag on, lifted function returns telemetry → result carries it.

        Issue #456 Stage 5: the chain calls
        ``apply_outcome_coverage_to_contract_graph`` (lifted module
        function) directly.  We patch that to control the
        AugmentationResult that flows into the chain output.
        """
        from src.ai.advanced.prd.advanced_parser import ProjectConstraints
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()

        with patch(
            "src.ai.advanced.prd.advanced_parser.AIAnalysisEngine"
        ) as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine.generate_structured_response = AsyncMock(
                return_value=self._stub_engine_output()
            )
            mock_engine_class.return_value = mock_engine

            # Stub the lifted function directly with a populated
            # AugmentationResult carrying outcome-coverage telemetry.
            stub_task = _contract_task()
            stub_chain_result = AugmentationResult(
                augmented_tasks=[stub_task],
                synthesized_ids=[],
                telemetry={
                    "intent_fidelity_score": 0.9,
                    "coverage_before_fill": {"o1": ["t1"]},
                    "coverage_after_fill": {"o1": ["t1"]},
                    "gap_filled_outcomes": [],
                },
            )

            with patch(
                "src.marcus_mcp.coordinator.outcome_coverage_augmenter."
                "apply_outcome_coverage_to_contract_graph",
                new_callable=AsyncMock,
                return_value=stub_chain_result,
            ) as mock_apply:
                result = await parser.decompose_by_contract(
                    prd_analysis=_bare_analysis([_outcome()]),
                    contract_artifacts=_contract_artifacts(),
                    constraints=ProjectConstraints(),
                )

        assert isinstance(result, AugmentationResult)
        # Telemetry namespaced by augmenter name with canonical keys
        assert result.telemetry["outcome_coverage"]["intent_fidelity_score"] == 0.9
        assert result.telemetry["outcome_coverage"]["coverage_before_fill"] == {
            "o1": ["t1"]
        }
        assert result.augmented_tasks == [stub_task]
        mock_apply.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_side_channel_attribute_remains(self, monkeypatch: Any) -> None:
        """Phase 4 tech-debt fix removed self._last_contract_decompose_coverage.

        Locks in: parser instances no longer expose the side-channel
        attribute.  Anyone who was reading
        ``parser._last_contract_decompose_coverage`` needs to switch
        to reading ``result.coverage`` from the return value.
        """
        parser = _build_parser()
        # The old side-channel attribute should no longer exist.
        assert not hasattr(parser, "_last_contract_decompose_coverage")


class TestPreExistingTasksThreading:
    """``pre_existing_tasks`` parameter threads foundation tasks through
    the augmenter chain (Codex P2 on PR #473).

    Regression: pre-fix, ``SpecCoverageAugmenter`` saw only contract
    tasks during decompose_by_contract.  Foundation tasks synthesized
    pre-fork by ``_synthesize_shared_foundation`` were appended later
    by the orchestrator, so spec_coverage's keyword scan could
    falsely flag features as "uncovered" and synthesize duplicate
    spec_gap tasks for foundation work that already covered them.

    The fix threads foundation tasks into ``decompose_by_contract``
    via ``pre_existing_tasks`` so the chain sees the full pre-fork
    graph during scanning.
    """

    @pytest.fixture(autouse=True)
    def _no_spec_coverage(self) -> Any:
        """Stub spec_coverage; tests focus on threading."""
        with patch(
            "src.marcus_mcp.coordinator.spec_coverage_augmenter." "check_spec_coverage",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_pre_existing_tasks_visible_to_chain(self, monkeypatch: Any) -> None:
        """Foundation tasks appear in the chain's input task list."""
        from datetime import datetime, timezone

        from src.ai.advanced.prd.advanced_parser import ProjectConstraints
        from src.core.models import Priority, Task, TaskStatus
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "false")
        parser = _build_parser()

        now = datetime.now(timezone.utc)
        foundation = Task(
            id="foundation_auth",
            name="Set up Auth foundation",
            description="Bootstrap auth module",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=2.0,
        )

        with patch(
            "src.ai.advanced.prd.advanced_parser.AIAnalysisEngine"
        ) as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine.generate_structured_response = AsyncMock(
                return_value={
                    "tasks": [
                        {
                            "name": "Engine",
                            "description": "build engine",
                            "estimated_minutes": 240,
                            "provides": "GameStateUpdate",
                            "requires": "None",
                            "responsibility": (
                                "implements GameEngine from "
                                "src/contracts/GameState.ts"
                            ),
                            "contract_file": "src/contracts/GameState.ts",
                            "acceptance_criteria": [],
                        }
                    ]
                }
            )
            mock_engine_class.return_value = mock_engine

            # Spy on the chain's outcome-coverage helper so we can see
            # what tasks list it received.
            captured_chain_input: List[Task] = []

            async def _spy(
                *,
                prd_analysis: Any,
                tasks: List[Task],
                contract_artifacts: Any,
                llm_client: Any,
            ) -> AugmentationResult:
                captured_chain_input.extend(tasks)
                return AugmentationResult(augmented_tasks=list(tasks))

            with patch(
                "src.marcus_mcp.coordinator.outcome_coverage_augmenter."
                "apply_outcome_coverage_to_contract_graph",
                new=_spy,
            ):
                result = await parser.decompose_by_contract(
                    prd_analysis=_bare_analysis([_outcome()]),
                    contract_artifacts=_contract_artifacts(),
                    constraints=ProjectConstraints(),
                    pre_existing_tasks=[foundation],
                )

        # The chain saw the foundation task during scanning
        captured_ids = [t.id for t in captured_chain_input]
        assert "foundation_auth" in captured_ids

        # And the augmented result includes both foundation and contract task
        result_ids = [t.id for t in result.augmented_tasks]
        assert "foundation_auth" in result_ids
        assert any("Engine" in t.name for t in result.augmented_tasks)

    @pytest.mark.asyncio
    async def test_pre_existing_tasks_default_none_backward_compat(
        self, monkeypatch: Any
    ) -> None:
        """Calls without ``pre_existing_tasks`` still work — back-compat."""
        from src.ai.advanced.prd.advanced_parser import ProjectConstraints
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
        )

        monkeypatch.setenv(ENV_VAR_NAME, "false")
        parser = _build_parser()

        with patch(
            "src.ai.advanced.prd.advanced_parser.AIAnalysisEngine"
        ) as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine.generate_structured_response = AsyncMock(
                return_value={
                    "tasks": [
                        {
                            "name": "Engine",
                            "description": "build",
                            "estimated_minutes": 240,
                            "provides": "X",
                            "requires": "None",
                            "responsibility": "implements X from a/b.ts",
                            "contract_file": "a/b.ts",
                            "acceptance_criteria": [],
                        }
                    ]
                }
            )
            mock_engine_class.return_value = mock_engine

            # Call with default (no pre_existing_tasks); must not raise
            result = await parser.decompose_by_contract(
                prd_analysis=_bare_analysis([_outcome()]),
                contract_artifacts=_contract_artifacts(),
                constraints=ProjectConstraints(),
            )

        assert isinstance(result, AugmentationResult)
        assert len(result.augmented_tasks) == 1
        assert result.augmented_tasks[0].name == "Engine"
