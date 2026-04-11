"""
Unit tests for ``AdvancedPRDParser.decompose_by_contract`` (GH-320 PR 2).

Tests the contract-first decomposition path that produces tasks where
each task owns one side of a contract interface. Experiment 1
(2026-04-10) validated the mechanism on a hand-crafted TypeScript
contract; these tests pin the productionized path.

Test strategy
-------------
- Mock ``AIAnalysisEngine.generate_structured_response`` to return
  controlled task lists. Never call real LLMs from unit tests.
- Exercise the happy path, the empty-contracts fallback, the
  LLM-failure path, and the Task.responsibility plumbing.
"""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

# AdvancedPRDParser.__init__ instantiates LLMAbstraction which validates
# Marcus config on first construction. Provide a dummy API key so the
# validation passes — we never actually make LLM calls in unit tests.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

from src.ai.advanced.prd.advanced_parser import (  # noqa: E402
    AdvancedPRDParser,
    PRDAnalysis,
    ProjectConstraints,
)
from src.core.models import TaskStatus  # noqa: E402

pytestmark = pytest.mark.unit


def _make_prd_analysis() -> PRDAnalysis:
    """Build a minimal PRDAnalysis for tests."""
    return PRDAnalysis(
        functional_requirements=[
            {
                "id": "game_engine",
                "name": "Game Engine",
                "description": "Core game loop and state management",
                "complexity": "coordinated",
            },
            {
                "id": "game_ui",
                "name": "Game UI",
                "description": "Render and handle user input",
                "complexity": "simple",
            },
        ],
        non_functional_requirements=[],
        technical_constraints=[],
        business_objectives=[],
        user_personas=[],
        success_metrics=[],
        implementation_approach="iterative",
        complexity_assessment={"level": "medium"},
        risk_factors=[],
        confidence=0.85,
        original_description="Build a snake game with React and TypeScript",
    )


def _make_contract_artifacts():
    """Build contract artifacts matching _generate_contracts_by_domain output."""
    return {
        "Game Engine": {
            "artifacts": [
                {
                    "filename": "types.ts",
                    "artifact_type": "api",
                    "content": (
                        "export interface GameEngine {\n"
                        "  tick(): GameState;\n"
                        "  reset(): void;\n"
                        "}\n"
                        "export interface GameState {\n"
                        "  snake: Coord[];\n"
                        "  food: Coord;\n"
                        "  score: number;\n"
                        "}\n"
                    ),
                    "description": "Shared interface contract",
                    "relative_path": "docs/api/types.ts",
                },
            ],
            "decisions": [],
        },
        "Game UI": {
            "artifacts": [
                {
                    "filename": "ui-contract.md",
                    "artifact_type": "specification",
                    "content": "# UI contract\n\nConsumes GameState from types.ts\n",
                    "description": "UI consumer contract",
                    "relative_path": "docs/specifications/ui-contract.md",
                },
            ],
            "decisions": [],
        },
    }


class TestDecomposeByContract:
    """Test suite for AdvancedPRDParser.decompose_by_contract."""

    @pytest.mark.asyncio
    async def test_happy_path_produces_tasks_with_responsibility(self):
        """
        LLM returns structured tasks → Task objects with responsibility.

        The decomposer builds Task objects whose ``responsibility``
        field names the contract interface each task owns. This is the
        core productionization of experiment 1.
        """
        parser = AdvancedPRDParser()
        prd_analysis = _make_prd_analysis()
        contracts = _make_contract_artifacts()

        llm_response = {
            "tasks": [
                {
                    "name": "Implement GameEngine",
                    "description": "Build the game loop and state transitions",
                    "responsibility": "implements GameEngine interface from types.ts",
                    "contract_file": "docs/api/types.ts",
                    "provides": "GameState transitions, tick() implementation",
                    "requires": "None",
                    "estimated_minutes": 10,
                },
                {
                    "name": "Implement Game UI",
                    "description": "Render the board and handle keyboard input",
                    "responsibility": "consumes GameState, implements UI layer",
                    "contract_file": "docs/specifications/ui-contract.md",
                    "provides": "Rendered board, input dispatch",
                    "requires": "GameEngine tick() output",
                    "estimated_minutes": 8,
                },
            ]
        }

        with patch(
            "src.integrations.ai_analysis_engine.AIAnalysisEngine."
            "generate_structured_response",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            tasks = await parser.decompose_by_contract(
                prd_analysis=prd_analysis,
                contract_artifacts=contracts,
                agent_count=2,
                constraints=ProjectConstraints(complexity_mode="standard"),
            )

        assert len(tasks) == 2

        engine_task = tasks[0]
        assert engine_task.name == "Implement GameEngine"
        assert engine_task.responsibility == (
            "implements GameEngine interface from types.ts"
        )
        assert engine_task.status == TaskStatus.TODO
        assert engine_task.source_type == "contract_first"
        assert engine_task.source_context is not None
        assert engine_task.source_context.get("contract_file") == "docs/api/types.ts"
        assert engine_task.provides == "GameState transitions, tick() implementation"
        # "None" maps to Python None for requires
        assert engine_task.requires is None
        # 10 minutes -> hours
        assert abs(engine_task.estimated_hours - (10 / 60)) < 1e-6
        # Description embeds the contract reference
        assert "docs/api/types.ts" in engine_task.description

        ui_task = tasks[1]
        assert ui_task.responsibility == "consumes GameState, implements UI layer"
        assert ui_task.requires == "GameEngine tick() output"

    @pytest.mark.asyncio
    async def test_empty_contracts_raises_value_error(self):
        """
        All-None contracts → ValueError so caller can fall back.

        When every domain's contract generation produced no artifacts
        (payload=None), the decomposer cannot proceed. The caller in
        NaturalLanguageProjectCreator catches ValueError and falls back
        to feature_based with a visible warning.
        """
        parser = AdvancedPRDParser()
        prd_analysis = _make_prd_analysis()

        empty_contracts = {"Game Engine": None, "Game UI": None}

        with pytest.raises(ValueError, match="no usable domains"):
            await parser.decompose_by_contract(
                prd_analysis=prd_analysis,
                contract_artifacts=empty_contracts,
                agent_count=2,
            )

    @pytest.mark.asyncio
    async def test_contracts_with_empty_artifacts_raises_value_error(self):
        """
        Domains with empty artifact lists are treated as unusable.

        A payload with ``{"artifacts": []}`` is as useless as None —
        the LLM would see no contract content to decompose against.
        """
        parser = AdvancedPRDParser()
        prd_analysis = _make_prd_analysis()

        empty_contracts = {
            "Game Engine": {"artifacts": [], "decisions": []},
        }

        with pytest.raises(ValueError, match="no usable domains"):
            await parser.decompose_by_contract(
                prd_analysis=prd_analysis,
                contract_artifacts=empty_contracts,
                agent_count=2,
            )

    @pytest.mark.asyncio
    async def test_llm_failure_raises_runtime_error(self):
        """LLM exception → RuntimeError so caller can fall back."""
        parser = AdvancedPRDParser()
        prd_analysis = _make_prd_analysis()
        contracts = _make_contract_artifacts()

        with patch(
            "src.integrations.ai_analysis_engine.AIAnalysisEngine."
            "generate_structured_response",
            new_callable=AsyncMock,
            side_effect=TimeoutError("LLM call timed out"),
        ):
            with pytest.raises(RuntimeError, match="Contract decomposition LLM"):
                await parser.decompose_by_contract(
                    prd_analysis=prd_analysis,
                    contract_artifacts=contracts,
                    agent_count=2,
                )

    @pytest.mark.asyncio
    async def test_empty_task_list_in_response_raises(self):
        """LLM returns ``{"tasks": []}`` → RuntimeError (unusable)."""
        parser = AdvancedPRDParser()
        prd_analysis = _make_prd_analysis()
        contracts = _make_contract_artifacts()

        with patch(
            "src.integrations.ai_analysis_engine.AIAnalysisEngine."
            "generate_structured_response",
            new_callable=AsyncMock,
            return_value={"tasks": []},
        ):
            with pytest.raises(RuntimeError, match="contained no tasks"):
                await parser.decompose_by_contract(
                    prd_analysis=prd_analysis,
                    contract_artifacts=contracts,
                    agent_count=2,
                )

    @pytest.mark.asyncio
    async def test_labels_include_contract_first(self):
        """Contract-first tasks carry a 'contract_first' label for filtering."""
        parser = AdvancedPRDParser()
        prd_analysis = _make_prd_analysis()
        contracts = _make_contract_artifacts()

        llm_response = {
            "tasks": [
                {
                    "name": "Implement thing",
                    "description": "Do the thing",
                    "responsibility": "implements Thing from contract",
                    "contract_file": "docs/api/types.ts",
                    "provides": "thing",
                    "requires": "None",
                    "estimated_minutes": 5,
                },
            ]
        }

        with patch(
            "src.integrations.ai_analysis_engine.AIAnalysisEngine."
            "generate_structured_response",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            tasks = await parser.decompose_by_contract(
                prd_analysis=prd_analysis,
                contract_artifacts=contracts,
                agent_count=1,
            )

        assert "contract_first" in tasks[0].labels
        assert "implementation" in tasks[0].labels

    @pytest.mark.asyncio
    async def test_contract_file_embedded_in_description(self):
        """Task description includes the contract file path for agent discovery."""
        parser = AdvancedPRDParser()
        prd_analysis = _make_prd_analysis()
        contracts = _make_contract_artifacts()

        llm_response = {
            "tasks": [
                {
                    "name": "Implement thing",
                    "description": "Build the thing (no contract ref in LLM output)",
                    "responsibility": "implements Thing interface",
                    "contract_file": "docs/api/types.ts",
                    "provides": "thing",
                    "requires": "None",
                    "estimated_minutes": 5,
                },
            ]
        }

        with patch(
            "src.integrations.ai_analysis_engine.AIAnalysisEngine."
            "generate_structured_response",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            tasks = await parser.decompose_by_contract(
                prd_analysis=prd_analysis,
                contract_artifacts=contracts,
                agent_count=1,
            )

        # Even if the LLM didn't embed the contract_file in its own
        # description text, the decomposer augments it so agents can
        # read the contract without hunting through source_context.
        assert "docs/api/types.ts" in tasks[0].description
        assert "implements Thing interface" in tasks[0].description

    @pytest.mark.asyncio
    async def test_mixed_none_and_usable_contracts(self):
        """Partial contract generation → decomposer uses only usable ones."""
        parser = AdvancedPRDParser()
        prd_analysis = _make_prd_analysis()
        # One domain succeeded, one failed (None)
        contracts = {
            "Game Engine": {
                "artifacts": [
                    {
                        "filename": "types.ts",
                        "artifact_type": "api",
                        "content": "export interface GameEngine {}",
                        "description": "contract",
                        "relative_path": "docs/api/types.ts",
                    }
                ],
                "decisions": [],
            },
            "Game UI": None,  # contract generation failed for this domain
        }

        llm_response = {
            "tasks": [
                {
                    "name": "Implement GameEngine",
                    "description": "Build the engine",
                    "responsibility": "implements GameEngine",
                    "contract_file": "docs/api/types.ts",
                    "provides": "engine",
                    "requires": "None",
                    "estimated_minutes": 8,
                }
            ]
        }

        with patch(
            "src.integrations.ai_analysis_engine.AIAnalysisEngine."
            "generate_structured_response",
            new_callable=AsyncMock,
            return_value=llm_response,
        ) as mock_llm:
            tasks = await parser.decompose_by_contract(
                prd_analysis=prd_analysis,
                contract_artifacts=contracts,
                agent_count=1,
            )

        # Decomposition proceeded with 1 usable contract
        assert len(tasks) == 1
        # Verify the prompt sent to the LLM only included the Game Engine
        # section (the None domain was filtered out).
        call_args = mock_llm.call_args
        prompt = call_args.kwargs["prompt"]
        assert "Game Engine" in prompt
        assert "Game UI" not in prompt
