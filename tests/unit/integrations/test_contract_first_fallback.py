"""
Unit tests for contract-first fallback path (GH-320 PR 2).

Tests that ``NaturalLanguageProjectCreator._try_contract_first_decomposition``
returns None (triggering feature-based fallback) when any stage fails:

- project_root missing (cannot write contracts)
- PRD analysis fails
- No functional requirements
- Domain discovery fails
- Contract generation fails or produces no usable artifacts
- Decomposer raises ValueError or RuntimeError

The caller in ``process_natural_language`` then falls back to
feature-based decomposition with a visible warning — never a silent
fallback.
"""

import os

# Provide dummy API key so parser/creator instantiation succeeds in unit tests
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

import pytest  # noqa: E402

from src.ai.advanced.prd.advanced_parser import PRDAnalysis  # noqa: E402
from src.integrations.nlp_tools import NaturalLanguageProjectCreator  # noqa: E402

pytestmark = pytest.mark.unit


def _make_prd_analysis(with_requirements: bool = True) -> PRDAnalysis:
    """Build a minimal PRDAnalysis for tests."""
    return PRDAnalysis(
        functional_requirements=(
            [
                {
                    "id": "f1",
                    "name": "Feature 1",
                    "description": "Do the thing",
                    "complexity": "simple",
                }
            ]
            if with_requirements
            else []
        ),
        non_functional_requirements=[],
        technical_constraints=[],
        business_objectives=[],
        user_personas=[],
        success_metrics=[],
        implementation_approach="iterative",
        complexity_assessment={"level": "low"},
        risk_factors=[],
        confidence=0.8,
        original_description="Build a thing",
    )


def _make_creator() -> NaturalLanguageProjectCreator:
    """Build a creator with mocked AI engine."""
    return NaturalLanguageProjectCreator(
        kanban_client=MagicMock(),
        ai_engine=MagicMock(),
        state=MagicMock(),
    )


class TestContractFirstFallback:
    """Test suite for _try_contract_first_decomposition fallback conditions."""

    @pytest.mark.asyncio
    async def test_returns_none_when_project_root_missing(self):
        """project_root=None → fallback (contracts have nowhere to land)."""
        creator = _make_creator()
        constraints = MagicMock()

        result = await creator._try_contract_first_decomposition(
            description="Build a thing",
            project_name="Thing",
            project_root=None,
            constraints=constraints,
            options={"decomposer": "contract_first"},
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_prd_analysis_fails(self):
        """PRD analysis raises → fallback."""
        creator = _make_creator()
        constraints = MagicMock()

        with patch.object(
            creator.prd_parser,
            "_analyze_prd_deeply",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM timeout"),
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a thing",
                project_name="Thing",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_functional_requirements(self):
        """Empty functional_requirements → fallback."""
        creator = _make_creator()
        constraints = MagicMock()
        empty_analysis = _make_prd_analysis(with_requirements=False)

        with patch.object(
            creator.prd_parser,
            "_analyze_prd_deeply",
            new_callable=AsyncMock,
            return_value=empty_analysis,
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a thing",
                project_name="Thing",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_domain_discovery_fails(self):
        """Domain discovery raises → fallback."""
        creator = _make_creator()
        constraints = MagicMock()

        with (
            patch.object(
                creator.prd_parser,
                "_analyze_prd_deeply",
                new_callable=AsyncMock,
                return_value=_make_prd_analysis(),
            ),
            patch.object(
                creator.prd_parser,
                "_discover_domains",
                new_callable=AsyncMock,
                side_effect=RuntimeError("discovery failed"),
            ),
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a thing",
                project_name="Thing",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_domains_discovered(self):
        """Empty domain groups → fallback."""
        creator = _make_creator()
        constraints = MagicMock()

        with (
            patch.object(
                creator.prd_parser,
                "_analyze_prd_deeply",
                new_callable=AsyncMock,
                return_value=_make_prd_analysis(),
            ),
            patch.object(
                creator.prd_parser,
                "_discover_domains",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a thing",
                project_name="Thing",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_contract_generation_fails(self):
        """_generate_contracts_by_domain raises → fallback."""
        creator = _make_creator()
        constraints = MagicMock()

        with (
            patch.object(
                creator.prd_parser,
                "_analyze_prd_deeply",
                new_callable=AsyncMock,
                return_value=_make_prd_analysis(),
            ),
            patch.object(
                creator.prd_parser,
                "_discover_domains",
                new_callable=AsyncMock,
                return_value={"Main": ["f1"]},
            ),
            patch(
                "src.integrations.nlp_tools._generate_contracts_by_domain",
                new_callable=AsyncMock,
                side_effect=RuntimeError("contract gen failed"),
            ),
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a thing",
                project_name="Thing",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_contracts_all_empty(self):
        """All domains produce None artifacts → fallback."""
        creator = _make_creator()
        constraints = MagicMock()

        with (
            patch.object(
                creator.prd_parser,
                "_analyze_prd_deeply",
                new_callable=AsyncMock,
                return_value=_make_prd_analysis(),
            ),
            patch.object(
                creator.prd_parser,
                "_discover_domains",
                new_callable=AsyncMock,
                return_value={"Main": ["f1"]},
            ),
            patch(
                "src.integrations.nlp_tools._generate_contracts_by_domain",
                new_callable=AsyncMock,
                return_value={"Main": None},
            ),
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a thing",
                project_name="Thing",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_decomposer_fails(self):
        """decompose_by_contract raises RuntimeError → fallback."""
        creator = _make_creator()
        constraints = MagicMock()

        with (
            patch.object(
                creator.prd_parser,
                "_analyze_prd_deeply",
                new_callable=AsyncMock,
                return_value=_make_prd_analysis(),
            ),
            patch.object(
                creator.prd_parser,
                "_discover_domains",
                new_callable=AsyncMock,
                return_value={"Main": ["f1"]},
            ),
            patch(
                "src.integrations.nlp_tools._generate_contracts_by_domain",
                new_callable=AsyncMock,
                return_value={
                    "Main": {
                        "artifacts": [
                            {
                                "filename": "contract.md",
                                "artifact_type": "api",
                                "content": "# Contract",
                                "description": "api",
                                "relative_path": "docs/api/contract.md",
                            }
                        ],
                        "decisions": [],
                    }
                },
            ),
            patch.object(
                creator.prd_parser,
                "decompose_by_contract",
                new_callable=AsyncMock,
                side_effect=RuntimeError("LLM structured output failed"),
            ),
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a thing",
                project_name="Thing",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_happy_path_returns_tasks(self):
        """All stages succeed → returns task list."""
        creator = _make_creator()
        constraints = MagicMock()

        fake_tasks = [MagicMock()]  # decomposer returns at least one task

        with (
            patch.object(
                creator.prd_parser,
                "_analyze_prd_deeply",
                new_callable=AsyncMock,
                return_value=_make_prd_analysis(),
            ),
            patch.object(
                creator.prd_parser,
                "_discover_domains",
                new_callable=AsyncMock,
                return_value={"Main": ["f1"]},
            ),
            patch(
                "src.integrations.nlp_tools._generate_contracts_by_domain",
                new_callable=AsyncMock,
                return_value={
                    "Main": {
                        "artifacts": [
                            {
                                "filename": "contract.md",
                                "artifact_type": "api",
                                "content": "# Contract",
                                "description": "api",
                                "relative_path": "docs/api/contract.md",
                            }
                        ],
                        "decisions": [],
                    }
                },
            ),
            patch.object(
                creator.prd_parser,
                "decompose_by_contract",
                new_callable=AsyncMock,
                return_value=fake_tasks,
            ),
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a thing",
                project_name="Thing",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first", "agent_count": 3},
            )

        assert result == fake_tasks
