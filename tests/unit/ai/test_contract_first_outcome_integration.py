"""Tests for #449 outcome coverage wiring in decompose_by_contract.

Verifies the contract-first decomposer integration:

- _apply_outcome_coverage_to_contract_graph passes contract_artifacts
  to fill_gaps so synthesized provides/requires/responsibility quote
  real interface names from the existing contracts
- Synthesized contract-first tasks get responsibility set from the
  gap-fill output (same convention as native contract-first tasks)
- Synthesized tasks get ['gap_fill', 'intent_fidelity', 'contract']
  labels (the 'contract' marker distinguishes contract-aware
  synthesis from feature-based gap-fill in audits)
- decompose_by_contract returns the augmented task list and stashes
  ParserOutcomeCoverage on self._last_contract_decompose_coverage
  for the orchestrator to read in Phase 5
- Side-channel attribute is reset on entry so stale results don't
  leak across calls
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import (
    ParserOutcomeCoverage,
    PRDAnalysis,
)
from src.ai.advanced.prd.outcome_extractor import UserOutcome
from src.config.outcome_coverage_config import ENV_VAR_NAME
from src.core.models import Priority, Task, TaskStatus

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

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
        )

        assert result is None
        parser.llm_client.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_outcomes(self, monkeypatch: Any) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
        )

        assert result is None
        parser.llm_client.analyze.assert_not_called()

    @pytest.mark.asyncio
    async def test_synthesized_task_carries_responsibility(
        self, monkeypatch: Any
    ) -> None:
        """Contract-first gap-fill tasks set Task.responsibility from output.

        That's the difference from the feature-based path:
        Task.responsibility names the contract interface this task owns.
        Native contract-first tasks have it set; synthesized contract-
        first tasks must too, otherwise downstream
        build_tiered_instructions can't surface the contract framing.
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()

        # 3 LLM responses: coverage (gap), fill (with responsibility),
        # post-fill coverage
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                (
                    '{"tasks": [{'
                    '"name": "Render snake to canvas",'
                    '"description": "draw snake on canvas",'
                    '"provides": "RenderingAgent.draw",'
                    '"requires": "GameStateUpdate",'
                    '"responsibility": '
                    '"implements RenderingAgent from src/contracts/Render.ts"'
                    "}]}"
                ),
                '{"coverage": {"outcome_play": ["_synth_for_coverage_0"]}}',
            ]
        )

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
        )

        assert result is not None
        assert isinstance(result, ParserOutcomeCoverage)
        assert len(result.augmented_tasks) == 2
        synthesized = result.augmented_tasks[1]
        assert synthesized.responsibility == (
            "implements RenderingAgent from src/contracts/Render.ts"
        )
        assert synthesized.provides == "RenderingAgent.draw"
        assert synthesized.requires == "GameStateUpdate"

    @pytest.mark.asyncio
    async def test_synthesized_task_labels_include_contract_marker(
        self, monkeypatch: Any
    ) -> None:
        """Contract-aware synthesis is distinguishable in audit labels.

        Distinguishes a contract-first gap-fill (labels include
        ``"contract"``) from a feature-based gap-fill (no
        ``"contract"`` label).  Useful for audits that ask
        "which gap-fill tasks were synthesized in contract-aware mode?"
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                (
                    '{"tasks": [{'
                    '"name": "Render", "description": "draw",'
                    '"responsibility": "implements R from r.ts"'
                    "}]}"
                ),
                '{"coverage": {"outcome_play": ["_synth_for_coverage_0"]}}',
            ]
        )

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
        )

        assert result is not None
        labels = result.augmented_tasks[1].labels
        assert "gap_fill" in labels
        assert "intent_fidelity" in labels
        assert "contract" in labels

    @pytest.mark.asyncio
    async def test_contract_artifacts_passed_to_fill_gaps(
        self, monkeypatch: Any
    ) -> None:
        """The contract artifact content reaches the gap-fill prompt.

        That's the whole point of the contract-aware path — without
        the contracts in the prompt, the LLM can't ground
        provides/requires/responsibility in real interface names.
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                '{"tasks": []}',  # empty fill — sufficient to inspect the call
            ]
        )

        await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
        )

        # The fill_gaps prompt is the second call; assert the contract
        # content appears in it.
        fill_prompt = parser.llm_client.analyze.await_args_list[1][0][0]
        assert "RenderingAgent" in fill_prompt
        assert "Render.ts" in fill_prompt
        assert "responsibility" in fill_prompt

    @pytest.mark.asyncio
    async def test_empty_contract_artifacts_path_still_runs(
        self, monkeypatch: Any
    ) -> None:
        """Even with no usable contracts, coverage still runs (just no responsibility).

        Defensive: contract_artifacts may have all-None payloads on a
        contract-generation failure.  The helper filters to usable
        artifacts and falls back to None (feature-based gap-fill
        prompt) rather than crashing.
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": ["t_engine"]}}',
            ]
        )

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts={"empty_domain": None},
        )

        assert result is not None
        # No gaps, no synthesis
        assert len(result.augmented_tasks) == 1
        assert result.coverage.intent_fidelity_score == 1.0

    @pytest.mark.asyncio
    async def test_contract_label_omitted_when_responsibility_is_none(
        self, monkeypatch: Any
    ) -> None:
        """The 'contract' label is honest — only present when responsibility is set.

        Phase 4 polish (Kaia review): if contract_artifacts gets
        filtered to empty (all-None payloads), the helper passes
        contract_artifacts=None to apply_outcome_coverage, which uses
        the feature-based gap-fill prompt (no responsibility field).
        Synthesized task ends up with responsibility=None — labeling
        it ``"contract"`` would lie about the synthesis context.
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                # Feature-based fill prompt fires (no contract);
                # responsibility omitted from output dict
                ('{"tasks": [{' '"name": "Render", "description": "draw"' "}]}"),
                '{"coverage": {"outcome_play": ["_synth_for_coverage_0"]}}',
            ]
        )

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            # All None → filtered to empty → fallback to None
            contract_artifacts={"d1": None, "d2": None},
        )

        assert result is not None
        synthesized = result.augmented_tasks[1]
        assert synthesized.responsibility is None
        # Honest label set: gap_fill + intent_fidelity, NOT contract
        assert "gap_fill" in synthesized.labels
        assert "intent_fidelity" in synthesized.labels
        assert "contract" not in synthesized.labels

    @pytest.mark.asyncio
    async def test_source_context_carries_contract_file_for_layer_1_3(
        self, monkeypatch: Any
    ) -> None:
        """source_context is populated so Layer 1.3 surfaces the contract file.

        Phase 4 polish (Kaia review): Layer 1.3 of
        ``build_tiered_instructions`` reads
        ``task.source_context["contract_file"]`` to render the
        "Read() the contract file at..." instruction.  Without this,
        gap-fill agents miss the explicit "go read the contract"
        prompt that native contract-first agents get.

        Best-effort regex parse extracts the file path from the
        responsibility string's canonical
        ``"implements <Iface> from <path>"`` shape.
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                (
                    '{"tasks": [{'
                    '"name": "Render", "description": "draw",'
                    '"responsibility": '
                    '"implements RenderingAgent from src/contracts/Render.ts"'
                    "}]}"
                ),
                '{"coverage": {"outcome_play": ["_synth_for_coverage_0"]}}',
            ]
        )

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
        )

        assert result is not None
        synthesized = result.augmented_tasks[1]
        assert synthesized.source_context is not None
        assert synthesized.source_context["contract_file"] == (
            "src/contracts/Render.ts"
        )
        # Belt-and-braces: responsibility also stashed in source_context
        # for kanban providers that don't round-trip the top-level field
        assert synthesized.source_context["responsibility"] == (
            "implements RenderingAgent from src/contracts/Render.ts"
        )
        assert synthesized.source_type == "gap_fill_contract"

    @pytest.mark.asyncio
    async def test_source_context_is_none_when_responsibility_missing(
        self, monkeypatch: Any
    ) -> None:
        """source_context stays None when responsibility absent.

        Symmetric with the label-based path.
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                ('{"tasks": [{' '"name": "Render", "description": "draw"' "}]}"),
                '{"coverage": {"outcome_play": ["_synth_for_coverage_0"]}}',
            ]
        )

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts={"d": None},  # filtered to empty
        )

        assert result is not None
        synthesized = result.augmented_tasks[1]
        assert synthesized.source_context is None

    @pytest.mark.asyncio
    async def test_method_name_in_responsibility_does_not_become_contract_file(
        self, monkeypatch: Any
    ) -> None:
        """LLM drift to method-name 'from' phrase is filtered by path guard.

        Phase 4 polish (Kaia review): the regex captures any
        whitespace-bounded token containing a period.  Without the
        path-separator guard, ``"from RenderingAgent.draw"`` would
        yield ``contract_file = "RenderingAgent.draw"`` — a method
        name, not a path.  Layer 1.3 would then print
        ``Read() the contract file at RenderingAgent.draw`` which is
        gibberish.  The guard requires '/' or '\\' before accepting.
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                (
                    '{"tasks": [{'
                    '"name": "Render", "description": "draw",'
                    # Drift case: "from <method-name>" instead of
                    # "from <path>".  Method name has a period but
                    # no path separator.
                    '"responsibility": '
                    '"implements RenderingAgent from RenderingAgent.draw"'
                    "}]}"
                ),
                '{"coverage": {"outcome_play": ["_synth_for_coverage_0"]}}',
            ]
        )

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
        )

        assert result is not None
        synthesized = result.augmented_tasks[1]
        # Path guard rejected the method-name candidate
        assert synthesized.source_context is not None
        assert "contract_file" not in synthesized.source_context
        # Responsibility itself is still preserved in source_context
        assert synthesized.source_context["responsibility"] == (
            "implements RenderingAgent from RenderingAgent.draw"
        )

    @pytest.mark.asyncio
    async def test_dotted_namespace_in_responsibility_rejected(
        self, monkeypatch: Any
    ) -> None:
        """Python-style dotted namespaces don't pass as contract files.

        Same path-separator guard as above — drift case
        ``"from src.module.thing"`` (Python-style dotted path) has
        a period but no path separator, so it's filtered out.
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                (
                    '{"tasks": [{'
                    '"name": "Module", "description": "build",'
                    '"responsibility": "implements Module from src.module.thing"'
                    "}]}"
                ),
                '{"coverage": {"outcome_play": ["_synth_for_coverage_0"]}}',
            ]
        )

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
        )

        assert result is not None
        synthesized = result.augmented_tasks[1]
        assert synthesized.source_context is not None
        assert "contract_file" not in synthesized.source_context

    @pytest.mark.asyncio
    async def test_windows_style_path_accepted_via_backslash_separator(
        self, monkeypatch: Any
    ) -> None:
        """Windows-style backslash paths also pass the guard."""
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                (
                    '{"tasks": [{'
                    '"name": "X", "description": "y",'
                    '"responsibility": '
                    r'"implements X from src\\contracts\\X.ts"'
                    "}]}"
                ),
                '{"coverage": {"outcome_play": ["_synth_for_coverage_0"]}}',
            ]
        )

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
        )

        assert result is not None
        synthesized = result.augmented_tasks[1]
        assert synthesized.source_context is not None
        assert synthesized.source_context["contract_file"] == ("src\\contracts\\X.ts")

    @pytest.mark.asyncio
    async def test_marcus_contract_first_marker_embedded_in_description(
        self, monkeypatch: Any
    ) -> None:
        """Gap-fill description carries MARCUS_CONTRACT_FIRST marker.

        Codex review on PR #457: providers like Planka don't round-trip
        ``Task.responsibility`` or ``Task.source_context`` — only the
        description survives.  Without the marker, ``_parse_contract_metadata``
        priority-3 fallback can't recover contract ownership for reloaded
        gap-fill tasks, and ``build_tiered_instructions`` silently drops
        the CONTRACT RESPONSIBILITY layer.

        Mirrors the marker shape native contract-first tasks emit at
        ``advanced_parser.py:679``.  Locks: marker present, parseable
        by ``_parse_contract_metadata`` even when the responsibility
        + source_context are stripped (Planka simulation).
        """
        from src.marcus_mcp.tools.task import _parse_contract_metadata

        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                (
                    '{"tasks": [{'
                    '"name": "Render snake to canvas",'
                    '"description": "draw snake on canvas",'
                    '"provides": "RenderingAgent",'
                    '"requires": "GameStateUpdate",'
                    '"responsibility": '
                    '"implements RenderingAgent from src/contracts/Render.ts"'
                    "}]}"
                ),
                '{"coverage": {"outcome_play": ["_synth_for_coverage_0"]}}',
            ]
        )

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
        )

        assert result is not None
        synthesized = result.augmented_tasks[1]
        assert "<!-- MARCUS_CONTRACT_FIRST" in synthesized.description
        assert (
            "responsibility: implements RenderingAgent from src/contracts/Render.ts"
            in synthesized.description
        )
        assert "contract_file: src/contracts/Render.ts" in synthesized.description
        assert "-->" in synthesized.description

        # Planka simulation: provider strips Task.responsibility and
        # source_context on reload.  Description survives — the marker
        # must let _parse_contract_metadata recover the metadata.
        stripped = Task(
            id=synthesized.id,
            name=synthesized.name,
            description=synthesized.description,
            status=synthesized.status,
            priority=synthesized.priority,
            assigned_to=None,
            created_at=synthesized.created_at,
            updated_at=synthesized.updated_at,
            due_date=None,
            estimated_hours=synthesized.estimated_hours,
            # Planka does NOT round-trip these:
            responsibility=None,
            source_context=None,
        )
        meta = _parse_contract_metadata(stripped)
        assert meta["responsibility"] == (
            "implements RenderingAgent from src/contracts/Render.ts"
        )
        assert meta["contract_file"] == "src/contracts/Render.ts"

    @pytest.mark.asyncio
    async def test_marker_omitted_when_responsibility_absent(
        self, monkeypatch: Any
    ) -> None:
        """No marker when gap-fill omits responsibility (feature-based fallback)."""
        monkeypatch.setenv(ENV_VAR_NAME, "true")
        parser = _build_parser()
        parser.llm_client.analyze = AsyncMock(
            side_effect=[
                '{"coverage": {"outcome_play": []}}',
                (
                    '{"tasks": [{'
                    '"name": "Render", "description": "draw",'
                    '"provides": "RenderingAgent",'
                    '"requires": "GameStateUpdate"'
                    "}]}"
                ),
                '{"coverage": {"outcome_play": ["_synth_for_coverage_0"]}}',
            ]
        )

        result = await parser._apply_outcome_coverage_to_contract_graph(
            prd_analysis=_bare_analysis([_outcome()]),
            tasks=[_contract_task()],
            contract_artifacts=_contract_artifacts(),
        )

        assert result is not None
        synthesized = result.augmented_tasks[1]
        # Responsibility absent → marker would lie about contract framing.
        assert "MARCUS_CONTRACT_FIRST" not in synthesized.description
        assert synthesized.description == "draw"


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
        """Flag on, helper returns a result → outcome_coverage telemetry populated."""
        from src.ai.advanced.prd.advanced_parser import ProjectConstraints
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
        )
        from src.marcus_mcp.coordinator.outcome_coverage import (
            OutcomeCoverageResult,
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

            # Stub helper with a populated ParserOutcomeCoverage
            # carrying a real OutcomeCoverageResult so the wrapper can
            # extract telemetry fields by attribute access.
            real_coverage = OutcomeCoverageResult(
                synthesized_tasks=[],
                intent_fidelity_score=0.9,
                coverage_before_fill={"o1": ["t1"]},
                coverage_after_fill={"o1": ["t1"]},
                gaps=[],
            )
            stub_helper_result = ParserOutcomeCoverage(
                augmented_tasks=[_contract_task()],
                coverage=real_coverage,
            )
            parser._apply_outcome_coverage_to_contract_graph = AsyncMock(
                return_value=stub_helper_result
            )

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
        assert result.augmented_tasks == stub_helper_result.augmented_tasks
        parser._apply_outcome_coverage_to_contract_graph.assert_awaited_once()

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
