"""Unit tests for #449 PRDAnalysis outcome integration in advanced_parser.

When ``MARCUS_OUTCOME_COVERAGE`` is on, ``_analyze_prd_deeply``
populates ``PRDAnalysis.user_outcomes`` via ``extract_user_outcomes``.
When the flag is off, the field stays empty and no extra LLM call
fires — the existing PRD pipeline runs unchanged.
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import PRDAnalysis
from src.ai.advanced.prd.outcome_extractor import UserOutcome
from src.config.outcome_coverage_config import ENV_VAR_NAME

pytestmark = pytest.mark.unit


class TestPRDAnalysisDataclassUserOutcomesField:
    """The dataclass carries user_outcomes with a sensible default."""

    def test_user_outcomes_defaults_to_empty_list(self) -> None:
        """A PRDAnalysis can be constructed without user_outcomes (legacy)."""
        analysis = PRDAnalysis(
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
        )
        assert analysis.user_outcomes == []

    def test_user_outcomes_can_be_set_directly(self) -> None:
        outcome = UserOutcome(
            id="outcome_play",
            action="user can play snake",
            success_signal="snake visibly moves",
            scope="in_scope",
        )
        analysis = PRDAnalysis(
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
            user_outcomes=[outcome],
        )
        assert analysis.user_outcomes == [outcome]


class TestParserOutcomeExtractionWiring:
    """``_analyze_prd_deeply`` calls ``extract_user_outcomes`` only when flagged."""

    @pytest.fixture
    def sample_outcome(self) -> UserOutcome:
        return UserOutcome(
            id="outcome_play_game",
            action="user can play the snake game",
            success_signal="snake visibly moves on a board",
            scope="in_scope",
        )

    @pytest.mark.asyncio
    async def test_extraction_skipped_when_flag_off(
        self, monkeypatch: Any, sample_outcome: UserOutcome
    ) -> None:
        """Default off — extract_user_outcomes is never called."""
        monkeypatch.delenv(ENV_VAR_NAME, raising=False)

        with patch(
            "src.ai.advanced.prd.advanced_parser.extract_user_outcomes",
            new=AsyncMock(return_value=[sample_outcome]),
        ) as mock_extract:
            from src.ai.advanced.prd.advanced_parser import (
                AdvancedPRDParser,
                ProjectConstraints,
            )

            with (
                patch("src.ai.advanced.prd.advanced_parser.LLMAbstraction"),
                patch("src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"),
            ):
                parser = AdvancedPRDParser()
                mock_llm = AsyncMock()
                parser.llm_client = mock_llm
                mock_llm.analyze = AsyncMock(
                    return_value=(
                        '{"functional_requirements": [{"id": "f1", "name": '
                        '"play game"}], "non_functional_requirements": [], '
                        '"technical_constraints": [], "business_objectives": '
                        '[], "user_personas": [], "success_metrics": [], '
                        '"implementation_approach": "agile", '
                        '"complexity_assessment": {}, "risk_factors": [], '
                        '"confidence": 0.9}'
                    )
                )
                analysis = await parser._analyze_prd_deeply(
                    "build a snake game", ProjectConstraints()
                )

        assert analysis.user_outcomes == []
        mock_extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_extraction_runs_when_flag_on(
        self, monkeypatch: Any, sample_outcome: UserOutcome
    ) -> None:
        """Flag on — extract_user_outcomes is called and result attached."""
        monkeypatch.setenv(ENV_VAR_NAME, "true")

        with patch(
            "src.ai.advanced.prd.advanced_parser.extract_user_outcomes",
            new=AsyncMock(return_value=[sample_outcome]),
        ) as mock_extract:
            from src.ai.advanced.prd.advanced_parser import (
                AdvancedPRDParser,
                ProjectConstraints,
            )

            with (
                patch("src.ai.advanced.prd.advanced_parser.LLMAbstraction"),
                patch("src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"),
            ):
                parser = AdvancedPRDParser()
                mock_llm = AsyncMock()
                parser.llm_client = mock_llm
                mock_llm.analyze = AsyncMock(
                    return_value=(
                        '{"functional_requirements": [{"id": "f1", "name": '
                        '"play game"}], "non_functional_requirements": [], '
                        '"technical_constraints": [], "business_objectives": '
                        '[], "user_personas": [], "success_metrics": [], '
                        '"implementation_approach": "agile", '
                        '"complexity_assessment": {}, "risk_factors": [], '
                        '"confidence": 0.9}'
                    )
                )
                analysis = await parser._analyze_prd_deeply(
                    "build a snake game", ProjectConstraints()
                )

        assert analysis.user_outcomes == [sample_outcome]
        mock_extract.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_extraction_failure_does_not_break_prd_analysis(
        self, monkeypatch: Any
    ) -> None:
        """Outcome extraction failure logs a warning, returns empty list.

        The PRD analysis pipeline must remain robust to filter-LLM
        failures — fidelity becomes unmeasurable for that project, but
        decomposition still proceeds.
        """
        monkeypatch.setenv(ENV_VAR_NAME, "true")

        with patch(
            "src.ai.advanced.prd.advanced_parser.extract_user_outcomes",
            new=AsyncMock(side_effect=ValueError("LLM filter exploded")),
        ):
            from src.ai.advanced.prd.advanced_parser import (
                AdvancedPRDParser,
                ProjectConstraints,
            )

            with (
                patch("src.ai.advanced.prd.advanced_parser.LLMAbstraction"),
                patch("src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"),
            ):
                parser = AdvancedPRDParser()
                mock_llm = AsyncMock()
                parser.llm_client = mock_llm
                mock_llm.analyze = AsyncMock(
                    return_value=(
                        '{"functional_requirements": [{"id": "f1", "name": '
                        '"play"}], "non_functional_requirements": [], '
                        '"technical_constraints": [], "business_objectives": '
                        '[], "user_personas": [], "success_metrics": [], '
                        '"implementation_approach": "agile", '
                        '"complexity_assessment": {}, "risk_factors": [], '
                        '"confidence": 0.9}'
                    )
                )
                analysis = await parser._analyze_prd_deeply(
                    "build a snake game", ProjectConstraints()
                )

        assert analysis.user_outcomes == []
        # PRD analysis itself succeeded
        assert len(analysis.functional_requirements) == 1
