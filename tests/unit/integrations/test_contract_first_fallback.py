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

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import PRDAnalysis
from src.integrations.nlp_tools import NaturalLanguageProjectCreator

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
    """
    Build a creator with ``LLMAbstraction`` stubbed.

    ``NaturalLanguageProjectCreator.__init__`` instantiates
    ``AdvancedPRDParser`` which in turn instantiates
    ``LLMAbstraction``, and that calls ``get_config()`` which
    requires a valid Marcus config. In CI there is no
    ``config_marcus.json`` and no ``ANTHROPIC_API_KEY``, so
    construction fails at ``LLMAbstraction.__init__``.

    Matches the project convention from
    ``tests/unit/ai/test_advanced_prd_parser.py``: stub
    ``LLMAbstraction`` at the import site before constructing the
    parser. Every test in this file patches the parser's methods
    individually so the stubbed LLM client is never actually
    invoked.
    """
    with patch("src.ai.advanced.prd.advanced_parser.LLMAbstraction") as mock_llm_class:
        mock_llm_class.return_value = MagicMock()
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
    async def test_happy_path_returns_design_ghosts_plus_impl_tasks(self):
        """
        All stages succeed → returns design ghost(s) + impl task(s).

        After GH-320 PR 3 (Cato retrofit), the contract-first path
        prepends one synthetic design ghost task per usable domain to
        the impl tasks returned by ``decompose_by_contract``. The
        ghosts make Cato's structural-task classifier fire so contract
        generation work shows up in the dashboard the same way the
        feature-based design phase does.
        """
        creator = _make_creator()
        constraints = MagicMock()

        # Build a real impl task so we can assert dependency wiring.
        from datetime import datetime, timezone

        from src.core.models import Priority, Task, TaskStatus

        impl_task = Task(
            id="contract_task_1",
            name="Implement Auth Module",
            description="Implement auth module from contract",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.2,
            labels=["contract_first", "implementation"],
            source_type="contract_first",
            source_context={
                "contract_file": "docs/api/main-interface-contracts.md",
                "responsibility": "implements Auth interface",
            },
            responsibility="implements Auth interface",
        )

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
                                "filename": "main-interface-contracts.md",
                                "artifact_type": "specification",
                                "content": "# Interface Contracts",
                                "description": "interfaces",
                                "relative_path": (
                                    "docs/api/main-interface-contracts.md"
                                ),
                            },
                            {
                                "filename": "main-architecture.md",
                                "artifact_type": "architecture",
                                "content": "# Arch",
                                "description": "arch",
                                "relative_path": "docs/api/main-architecture.md",
                            },
                        ],
                        "decisions": [
                            {
                                "what": "Use REST",
                                "why": "Simplicity",
                                "impact": "All endpoints HTTP",
                            }
                        ],
                    }
                },
            ),
            patch.object(
                creator.prd_parser,
                "decompose_by_contract",
                new_callable=AsyncMock,
                return_value=[impl_task],
            ),
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a thing",
                project_name="Thing",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first", "agent_count": 3},
            )

        # Result is design ghost(s) + impl task(s)
        assert result is not None
        assert len(result) == 2, (
            f"Expected 1 design ghost + 1 impl task, got {len(result)}: "
            f"{[(t.name, t.labels) for t in result]}"
        )

        # First task is the design ghost; second is the original impl task
        ghost = result[0]
        impl = result[1]

        assert ghost.name == "Design Main"
        assert "design" in ghost.labels
        # Codex P2 on PR #334: ghost MUST NOT carry "contract_first"
        # label — that label is also on impl tasks and would cause
        # SafetyChecker to over-link every impl to every ghost.
        # Provenance lives on source_type instead.
        assert "contract_first" not in ghost.labels
        assert ghost.status == TaskStatus.DONE
        assert ghost.assigned_to == "Marcus"
        assert ghost.source_type == "contract_first_design"
        assert (
            ghost.source_context.get("contract_file")
            == "docs/api/main-interface-contracts.md"
        )

        # Impl task is the same object the decomposer returned, with
        # its dependencies updated to include the matching design ghost
        assert impl is impl_task
        assert ghost.id in impl.dependencies, (
            f"Impl task should depend on its domain's design ghost. "
            f"Ghost id: {ghost.id}, impl deps: {impl.dependencies}"
        )

        # The contract_artifacts dict was stashed on the creator instance
        # so the background _run_design_phase can pick it up and route
        # through the existing _register_design_via_mcp Phase B path.
        stashed = getattr(creator, "_contract_first_design_content", None)
        assert stashed is not None, (
            "Contract-first design content must be stashed on the "
            "creator instance for the background design phase to use."
        )
        assert "Design Main" in stashed, (
            f"Stashed design content must be rekeyed by 'Design {{domain}}' "
            f"to match Phase B's name-based join. Got keys: {list(stashed.keys())}"
        )
        # The artifacts and decisions are forwarded verbatim
        assert len(stashed["Design Main"]["artifacts"]) == 2
        assert len(stashed["Design Main"]["decisions"]) == 1


class TestContractFirstDesignGhosts:
    """
    Test design ghost task creation in contract-first decomposition.

    Synthetic design tasks are the Cato retrofit (GH-320 PR after #333):
    contract-first generates contract artifacts and decisions in Phase A
    via ``_generate_contracts_by_domain`` but, before this fix, those
    were discarded after being passed to ``decompose_by_contract``. No
    log_artifact, no log_decision, no structural task in marcus.db, no
    ghost node in Cato.

    The fix synthesizes one DONE design task per usable domain so the
    existing feature-based Phase B infrastructure
    (``_register_design_via_mcp``) and the marcus.db design-task
    persistence block both fire naturally — zero Cato changes.
    """

    @pytest.mark.asyncio
    async def test_design_ghost_satisfies_is_design_task_helper(self):
        """
        Synthesized ghosts must trip ``_is_design_task`` so the
        background design phase fires and the marcus.db persistence
        block at nlp_tools.py:820-873 picks them up. ``_is_design_task``
        requires both ``"design"`` in labels AND name starting with
        ``"design"``.
        """
        from datetime import datetime, timezone

        from src.core.models import Priority, Task, TaskStatus
        from src.integrations.nlp_tools import _is_design_task

        creator = _make_creator()
        constraints = MagicMock()

        # Minimal impl task — the existing guard rejects empty task
        # lists from decompose_by_contract as "no tasks generated".
        stub_impl = Task(
            id="contract_task_stub",
            name="Implement Stub",
            description="stub",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.1,
            labels=["contract_first", "implementation"],
            source_context={
                "contract_file": (
                    "docs/api/weather-information-system-" "interface-contracts.md"
                ),
            },
        )

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
                return_value={
                    "Weather Information System": ["f1"],
                    "Time Display System": ["f2"],
                },
            ),
            patch(
                "src.integrations.nlp_tools._generate_contracts_by_domain",
                new_callable=AsyncMock,
                return_value={
                    "Weather Information System": {
                        "artifacts": [
                            {
                                "filename": (
                                    "weather-information-system-"
                                    "interface-contracts.md"
                                ),
                                "artifact_type": "specification",
                                "content": "# Weather",
                                "description": "weather",
                                "relative_path": (
                                    "docs/api/weather-information-system-"
                                    "interface-contracts.md"
                                ),
                            }
                        ],
                        "decisions": [],
                    },
                    "Time Display System": {
                        "artifacts": [
                            {
                                "filename": (
                                    "time-display-system-" "interface-contracts.md"
                                ),
                                "artifact_type": "specification",
                                "content": "# Time",
                                "description": "time",
                                "relative_path": (
                                    "docs/api/time-display-system-"
                                    "interface-contracts.md"
                                ),
                            }
                        ],
                        "decisions": [],
                    },
                },
            ),
            patch.object(
                creator.prd_parser,
                "decompose_by_contract",
                new_callable=AsyncMock,
                return_value=[stub_impl],
            ),
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a dashboard",
                project_name="Dashboard",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        assert result is not None
        ghosts = [t for t in result if t.name.lower().startswith("design")]
        assert len(ghosts) == 2, (
            f"Expected one ghost per domain (2), got {len(ghosts)}: "
            f"{[t.name for t in ghosts]}"
        )
        for ghost in ghosts:
            assert _is_design_task(ghost), (
                f"Ghost task {ghost.name!r} with labels {ghost.labels} "
                f"does not satisfy _is_design_task — Cato/marcus.db "
                f"persistence path will not fire for this task."
            )

    @pytest.mark.asyncio
    async def test_impl_tasks_wired_to_matching_ghost_by_contract_file(
        self,
    ):
        """
        Each impl task must have its corresponding design ghost in
        ``dependencies``, matched by ``source_context["contract_file"]``.
        Restores the diamond DAG topology so the integration task ends
        up depending on impl tasks transitively through the design
        layer, same shape as feature-based.
        """
        from datetime import datetime, timezone

        from src.core.models import Priority, Task, TaskStatus

        creator = _make_creator()
        constraints = MagicMock()

        weather_impl = Task(
            id="contract_task_weather",
            name="Implement WeatherWidget",
            description="weather impl",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.2,
            labels=["contract_first", "implementation"],
            source_context={
                "contract_file": (
                    "docs/api/weather-information-system-" "interface-contracts.md"
                ),
            },
        )
        time_impl = Task(
            id="contract_task_time",
            name="Implement TimeWidget",
            description="time impl",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.2,
            labels=["contract_first", "implementation"],
            source_context={
                "contract_file": (
                    "docs/api/time-display-system-interface-contracts.md"
                ),
            },
        )

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
                return_value={
                    "Weather Information System": ["f1"],
                    "Time Display System": ["f2"],
                },
            ),
            patch(
                "src.integrations.nlp_tools._generate_contracts_by_domain",
                new_callable=AsyncMock,
                return_value={
                    "Weather Information System": {
                        "artifacts": [
                            {
                                "filename": (
                                    "weather-information-system-"
                                    "interface-contracts.md"
                                ),
                                "artifact_type": "specification",
                                "content": "# Weather",
                                "description": "weather",
                                "relative_path": (
                                    "docs/api/weather-information-system-"
                                    "interface-contracts.md"
                                ),
                            }
                        ],
                        "decisions": [],
                    },
                    "Time Display System": {
                        "artifacts": [
                            {
                                "filename": (
                                    "time-display-system-" "interface-contracts.md"
                                ),
                                "artifact_type": "specification",
                                "content": "# Time",
                                "description": "time",
                                "relative_path": (
                                    "docs/api/time-display-system-"
                                    "interface-contracts.md"
                                ),
                            }
                        ],
                        "decisions": [],
                    },
                },
            ),
            patch.object(
                creator.prd_parser,
                "decompose_by_contract",
                new_callable=AsyncMock,
                return_value=[weather_impl, time_impl],
            ),
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a dashboard",
                project_name="Dashboard",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        assert result is not None

        # Find the two ghosts by name
        weather_ghost = next(
            t for t in result if t.name == "Design Weather Information System"
        )
        time_ghost = next(t for t in result if t.name == "Design Time Display System")

        # Each impl task depends on its matching ghost only — not the
        # other ghost. This is the load-bearing assertion: a wrong
        # match would still produce a green Cato but break the
        # integration task's dependency closure.
        assert weather_ghost.id in weather_impl.dependencies
        assert time_ghost.id not in weather_impl.dependencies
        assert time_ghost.id in time_impl.dependencies
        assert weather_ghost.id not in time_impl.dependencies

    @pytest.mark.asyncio
    async def test_no_ghost_when_domain_produced_no_artifacts(self):
        """
        Domains where contract generation produced an empty/None
        payload must NOT get a ghost task. The Phase B handoff joins
        on name; a ghost without backing content would just dangle.
        """
        from datetime import datetime, timezone

        from src.core.models import Priority, Task, TaskStatus

        creator = _make_creator()
        constraints = MagicMock()

        impl_task = Task(
            id="contract_task_1",
            name="Implement Main",
            description="impl",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.2,
            labels=["contract_first", "implementation"],
            source_context={
                "contract_file": "docs/api/good-interface-contracts.md",
            },
        )

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
                return_value={"Good": ["f1"], "Empty": ["f2"]},
            ),
            patch(
                "src.integrations.nlp_tools._generate_contracts_by_domain",
                new_callable=AsyncMock,
                return_value={
                    "Good": {
                        "artifacts": [
                            {
                                "filename": "good-interface-contracts.md",
                                "artifact_type": "specification",
                                "content": "# Good",
                                "description": "good",
                                "relative_path": (
                                    "docs/api/good-interface-contracts.md"
                                ),
                            }
                        ],
                        "decisions": [],
                    },
                    "Empty": None,  # contract generation failed for this domain
                },
            ),
            patch.object(
                creator.prd_parser,
                "decompose_by_contract",
                new_callable=AsyncMock,
                return_value=[impl_task],
            ),
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a thing",
                project_name="Thing",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        assert result is not None
        ghost_names = [t.name for t in result if t.name.lower().startswith("design")]
        assert ghost_names == ["Design Good"], (
            f"Expected only 'Design Good' ghost (Empty domain failed), "
            f"got {ghost_names}"
        )

    @pytest.mark.asyncio
    async def test_returns_none_on_cross_contract_type_collision(self):
        """
        Decomposition gate, check 1: ``_try_contract_first_decomposition``
        must fall back to feature-based when two contracts define
        the same field name with different types.

        Regression test for the WidgetPosition collision found in
        Experiment 4 v2 — the contract-first path produced a Python
        contract with ``positionX (number)`` and a TypeScript
        contract with ``positionX (string)``. Both passed isolated
        validation but agents shipped incompatible code.
        """
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
                return_value={
                    "Python Layout": ["f1"],
                    "TS Layout": ["f2"],
                },
            ),
            patch(
                "src.integrations.nlp_tools._generate_contracts_by_domain",
                new_callable=AsyncMock,
                return_value={
                    "Python Layout": {
                        "artifacts": [
                            {
                                "filename": ("python-layout-interface-contracts.md"),
                                "artifact_type": "specification",
                                "content": (
                                    "## WidgetPosition\n"
                                    "- positionX (number) — px coord\n"
                                ),
                                "description": "py layout",
                                "relative_path": (
                                    "docs/specifications/"
                                    "python-layout-interface-contracts.md"
                                ),
                            }
                        ],
                        "decisions": [],
                    },
                    "TS Layout": {
                        "artifacts": [
                            {
                                "filename": ("ts-layout-interface-contracts.md"),
                                "artifact_type": "specification",
                                "content": (
                                    "## WidgetPosition\n"
                                    "- positionX (string) — CSS grid prop\n"
                                ),
                                "description": "ts layout",
                                "relative_path": (
                                    "docs/specifications/"
                                    "ts-layout-interface-contracts.md"
                                ),
                            }
                        ],
                        "decisions": [],
                    },
                },
            ),
            patch.object(
                creator.prd_parser,
                "decompose_by_contract",
                new_callable=AsyncMock,
            ) as mock_decompose,
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a thing",
                project_name="Thing",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        assert result is None, (
            "Contract-first must fall back when contracts disagree "
            "on the same field's type."
        )
        mock_decompose.assert_not_called(), (
            "decompose_by_contract should not even be called when "
            "the consistency gate trips — the contracts are broken "
            "and burning an LLM call on them is wasteful."
        )

    @pytest.mark.asyncio
    async def test_safety_checker_does_not_over_link_ghosts_to_impl_tasks(
        self,
    ):
        """
        Regression test for Codex P2 on PR #334.

        ``SafetyChecker.apply_implementation_dependencies`` calls
        ``_find_related_tasks`` which treats any non-prefixed shared
        label as a relation. If contract-first design ghosts and impl
        tasks share the ``"contract_first"`` label, the safety check
        would link every impl task to every ghost, undoing the
        per-domain ``contract_file`` wiring done in
        ``_try_contract_first_decomposition``.

        This test runs the full pipeline (decomposition + safety
        check) on a multi-domain project and asserts each impl task's
        final dependency set contains only its matched domain ghost,
        not all ghosts.
        """
        from datetime import datetime, timezone

        from src.core.models import Priority, Task, TaskStatus
        from src.integrations.nlp_task_utils import SafetyChecker

        creator = _make_creator()
        constraints = MagicMock()

        weather_impl = Task(
            id="contract_task_weather",
            name="Implement WeatherWidget",
            description="weather impl",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.2,
            labels=["contract_first", "implementation"],
            source_context={
                "contract_file": (
                    "docs/api/weather-information-system-" "interface-contracts.md"
                ),
            },
        )
        time_impl = Task(
            id="contract_task_time",
            name="Implement TimeWidget",
            description="time impl",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.2,
            labels=["contract_first", "implementation"],
            source_context={
                "contract_file": (
                    "docs/api/time-display-system-interface-contracts.md"
                ),
            },
        )

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
                return_value={
                    "Weather Information System": ["f1"],
                    "Time Display System": ["f2"],
                },
            ),
            patch(
                "src.integrations.nlp_tools._generate_contracts_by_domain",
                new_callable=AsyncMock,
                return_value={
                    "Weather Information System": {
                        "artifacts": [
                            {
                                "filename": (
                                    "weather-information-system-"
                                    "interface-contracts.md"
                                ),
                                "artifact_type": "specification",
                                "content": "# Weather",
                                "description": "weather",
                                "relative_path": (
                                    "docs/api/weather-information-system-"
                                    "interface-contracts.md"
                                ),
                            }
                        ],
                        "decisions": [],
                    },
                    "Time Display System": {
                        "artifacts": [
                            {
                                "filename": (
                                    "time-display-system-" "interface-contracts.md"
                                ),
                                "artifact_type": "specification",
                                "content": "# Time",
                                "description": "time",
                                "relative_path": (
                                    "docs/api/time-display-system-"
                                    "interface-contracts.md"
                                ),
                            }
                        ],
                        "decisions": [],
                    },
                },
            ),
            patch.object(
                creator.prd_parser,
                "decompose_by_contract",
                new_callable=AsyncMock,
                return_value=[weather_impl, time_impl],
            ),
        ):
            result = await creator._try_contract_first_decomposition(
                description="Build a dashboard",
                project_name="Dashboard",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        assert result is not None

        # Now run the safety check that would normally fire in
        # ``create_tasks_from_description``. This is the path that
        # over-linked everything before the fix.
        SafetyChecker().apply_implementation_dependencies(result)

        weather_ghost = next(
            t for t in result if t.name == "Design Weather Information System"
        )
        time_ghost = next(t for t in result if t.name == "Design Time Display System")

        # After the safety check, each impl task must depend on its
        # matched ghost ONLY, not the cross-domain ghost. The original
        # bug: shared "contract_first" label caused
        # _find_related_tasks to return all ghosts as related to all
        # impl tasks, so weather_impl ended up depending on the time
        # ghost and vice versa.
        assert weather_ghost.id in weather_impl.dependencies, (
            f"Weather impl should depend on weather ghost. "
            f"Deps: {weather_impl.dependencies}"
        )
        assert time_ghost.id not in weather_impl.dependencies, (
            f"Weather impl should NOT depend on time ghost (cross-domain). "
            f"Deps: {weather_impl.dependencies}. "
            f"This is the Codex P2 over-linking regression."
        )
        assert time_ghost.id in time_impl.dependencies, (
            f"Time impl should depend on time ghost. " f"Deps: {time_impl.dependencies}"
        )
        assert weather_ghost.id not in time_impl.dependencies, (
            f"Time impl should NOT depend on weather ghost (cross-domain). "
            f"Deps: {time_impl.dependencies}. "
            f"This is the Codex P2 over-linking regression."
        )

    @pytest.mark.asyncio
    async def test_domain_descriptions_include_user_facing_requirements(
        self,
    ):
        """
        Upstream intent preservation (GH-320 task #64).

        The domain descriptions passed to ``_generate_contracts_by_domain``
        must include the user-facing requirements for that domain, not
        just the feature names. This makes the LLM see "this domain must
        support: Display weather temperature" alongside the domain's
        technical description, so the generated contracts include
        interfaces for user-visible behaviors (not just API shapes).

        The test captures the ``domains`` argument passed to
        ``_generate_contracts_by_domain`` and verifies it contains
        the requirement names from the PRD analysis.
        """
        creator = _make_creator()
        constraints = MagicMock()

        prd_with_display = PRDAnalysis(
            functional_requirements=[
                {
                    "id": "f1",
                    "name": "Display current weather temperature",
                    "description": "User sees temp on dashboard",
                    "complexity": "simple",
                },
            ],
            non_functional_requirements=[],
            technical_constraints=[],
            business_objectives=[],
            user_personas=[],
            success_metrics=[],
            implementation_approach="iterative",
            complexity_assessment={"level": "low"},
            risk_factors=[],
            confidence=0.8,
            original_description="Build a dashboard with weather",
        )

        captured_domains: dict = {}

        async def capture_domains(**kwargs: Any) -> dict:
            captured_domains.update(kwargs.get("domains", {}))
            return {
                "Weather": {
                    "artifacts": [
                        {
                            "filename": ("weather-interface-contracts.md"),
                            "artifact_type": "specification",
                            "content": "# Weather",
                            "description": "weather",
                            "relative_path": (
                                "docs/specifications/" "weather-interface-contracts.md"
                            ),
                        }
                    ],
                    "decisions": [],
                },
            }

        from datetime import datetime, timezone

        from src.core.models import Priority, Task, TaskStatus

        impl_task = Task(
            id="contract_task_1",
            name="Implement WeatherWidget",
            description="weather impl",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.2,
            labels=["contract_first", "implementation"],
            source_context={
                "contract_file": (
                    "docs/specifications/" "weather-interface-contracts.md"
                ),
            },
        )

        with (
            patch.object(
                creator.prd_parser,
                "_analyze_prd_deeply",
                new_callable=AsyncMock,
                return_value=prd_with_display,
            ),
            patch.object(
                creator.prd_parser,
                "_discover_domains",
                new_callable=AsyncMock,
                return_value={"Weather": ["f1"]},
            ),
            patch(
                "src.integrations.nlp_tools._generate_contracts_by_domain",
                new_callable=AsyncMock,
                side_effect=capture_domains,
            ),
            patch.object(
                creator.prd_parser,
                "decompose_by_contract",
                new_callable=AsyncMock,
                return_value=[impl_task],
            ),
        ):
            await creator._try_contract_first_decomposition(
                description="Build a dashboard with weather",
                project_name="Dashboard",
                project_root="/tmp/test",  # nosec B108
                constraints=constraints,
                options={"decomposer": "contract_first"},
            )

        # The domain description must contain the requirement name
        # so the LLM sees the user-facing intent when generating
        # the interface contracts.
        assert "Weather" in captured_domains, (
            f"Expected Weather domain in captured domains, "
            f"got: {list(captured_domains.keys())}"
        )
        weather_desc = captured_domains["Weather"]
        assert "Display current weather temperature" in weather_desc, (
            f"Domain description must include the functional "
            f"requirement name so the LLM preserves user-facing "
            f"intent in the generated contracts. Got:\n{weather_desc}"
        )
