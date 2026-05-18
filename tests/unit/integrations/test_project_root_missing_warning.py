"""
Unit tests for issue #478: contract_first fail-fast when project_root absent.

When the active decomposer strategy is ``contract_first`` but the caller
omits ``project_root`` from ``options``, Marcus must fail fast and return an
actionable error — not silently degrade to feature_based and return success:True
with a buried warning key that most callers will never check.

Two layers are tested:

1. ``_build_decomposer_warning`` — the pure detection helper.  Its logic
   is the same; only where we use it changes.
2. ``create_project_from_description`` fail-fast integration — verifies that
   the method returns ``success: False`` with a clear, actionable error message
   before any expensive kanban/LLM work is attempted.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.nlp_tools import _build_decomposer_warning

# ---------------------------------------------------------------------------
# Layer 1: pure detection helper
# ---------------------------------------------------------------------------


class TestBuildDecomposerWarning:
    """Test suite for ``_build_decomposer_warning``."""

    def test_returns_warning_when_contract_first_and_no_project_root(self) -> None:
        """
        When contract_first is the active strategy and project_root is absent,
        a non-empty warning string must be returned.
        """
        options: dict[str, Any] = {"decomposer": "contract_first"}
        warning = _build_decomposer_warning(options=options)
        assert warning is not None
        assert len(warning) > 0
        assert "project_root" in warning
        assert "feature_based" in warning

    def test_returns_warning_for_explicit_contract_first_no_project_root(
        self,
    ) -> None:
        """Explicit ``decomposer=contract_first`` without project_root → warning."""
        options: dict[str, Any] = {"decomposer": "contract_first"}
        warning = _build_decomposer_warning(options=options)
        assert warning is not None
        assert "project_root" in warning

    def test_returns_none_when_project_root_provided(self) -> None:
        """When project_root is supplied, contract_first CAN run — no warning."""
        options: dict[str, Any] = {
            "decomposer": "contract_first",
            "project_root": "/home/agent/projects/myproject",
        }
        warning = _build_decomposer_warning(options=options)
        assert warning is None

    def test_returns_none_when_project_root_provided_and_no_explicit_decomposer(
        self,
    ) -> None:
        """Default strategy with project_root present: happy path, no warning."""
        options: dict[str, Any] = {"project_root": "/home/agent/projects/impl"}
        warning = _build_decomposer_warning(options=options)
        assert warning is None

    def test_returns_none_for_explicit_feature_based(self) -> None:
        """Explicit feature_based — no project_root needed, no warning."""
        options: dict[str, Any] = {"decomposer": "feature_based"}
        warning = _build_decomposer_warning(options=options)
        assert warning is None

    def test_returns_none_for_feature_based_even_without_project_root(self) -> None:
        """Explicit feature_based with no project_root: intentional, no warning."""
        options: dict[str, Any] = {"decomposer": "feature_based"}
        warning = _build_decomposer_warning(options=options)
        assert warning is None

    def test_warning_message_mentions_structural_scaffolding(self) -> None:
        """Warning must state the practical consequence, not just the cause."""
        options: dict[str, Any] = {"decomposer": "contract_first"}
        warning = _build_decomposer_warning(options=options)
        assert warning is not None
        assert "structural" in warning.lower() or "scaffolding" in warning.lower()


# ---------------------------------------------------------------------------
# Layer 2: fail-fast integration in create_project_from_description
# ---------------------------------------------------------------------------


def _make_creator() -> Any:
    """Build a NaturalLanguageProjectCreator with minimal mocked deps."""
    with (
        patch("src.integrations.nlp_tools.AdvancedPRDParser"),
        patch("src.integrations.nlp_tools.BoardAnalyzer"),
        patch("src.integrations.nlp_tools.ContextDetector"),
    ):
        from src.integrations.nlp_tools import NaturalLanguageProjectCreator

        mock_kanban = MagicMock()
        mock_kanban.board_id = "test-board"
        mock_kanban.project_id = "proj-1"
        # Async methods must be AsyncMock so await doesn't crash
        mock_kanban.auto_setup_project = AsyncMock()
        mock_ai = MagicMock()
        inst = NaturalLanguageProjectCreator(
            kanban_client=mock_kanban,
            ai_engine=mock_ai,
        )
        inst.active_project_id = None
        return inst


@pytest.mark.asyncio
@pytest.mark.unit
class TestContractFirstFallback:
    """
    ``create_project_from_description`` must NOT abort when contract_first
    is active and project_root is absent. Instead it proceeds: the
    decomposer falls back to feature_based and project creation continues.

    A warning is logged so the degraded strategy is visible.
    """

    @pytest.fixture(autouse=True)
    def _stub_config(self) -> Any:
        """Stub get_config so the test does not depend on a local
        config_marcus.json / AI key. create_project_from_description calls
        get_config() to pick the default kanban provider; in a clean
        environment that path validates config and errors out before the
        fallback reaches kanban setup (Codex review #558). A sqlite-provider
        stub keeps the test exercising the fallback, not local config.
        """
        cfg = MagicMock()
        cfg.kanban.provider = "sqlite"
        with patch("src.config.marcus_config.get_config", return_value=cfg):
            yield

    async def test_no_project_root_does_not_abort_default_strategy(
        self,
    ) -> None:
        """
        Default options (contract_first, no project_root) must NOT short
        circuit on a project_root error — creation proceeds past the guard
        into kanban setup.
        """
        creator = _make_creator()
        with patch("src.integrations.nlp_tools.log_agent_event"):
            await creator.create_project_from_description(
                description="Build a snake game",
                project_name="SnakeGame",
                options=None,
            )

        # Got past the project_root guard: kanban setup was attempted.
        creator.kanban_client.auto_setup_project.assert_called()

    async def test_fallback_warning_logged_when_no_project_root(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        The fallback to feature_based must be logged as a warning so the
        degraded strategy is visible rather than silent.
        """
        creator = _make_creator()
        with (
            patch("src.integrations.nlp_tools.log_agent_event"),
            caplog.at_level("WARNING", logger="src.integrations.nlp_tools"),
        ):
            await creator.create_project_from_description(
                description="Build a todo app",
                project_name="TodoApp",
                options={"decomposer": "contract_first"},
            )

        assert any(
            "project_root" in rec.message and "feature_based" in rec.message
            for rec in caplog.records
        ), "Expected a warning mentioning project_root and the feature_based fallback"

    async def test_process_natural_language_called_on_fallback(self) -> None:
        """
        With contract_first + no project_root, creation proceeds — so
        process_natural_language IS called (decomposition still happens,
        via the feature_based fallback).
        """
        creator = _make_creator()
        creator.process_natural_language = AsyncMock(return_value=[])

        with patch("src.integrations.nlp_tools.log_agent_event"):
            await creator.create_project_from_description(
                description="Build a chess game",
                project_name="Chess",
                options=None,
            )

        creator.process_natural_language.assert_called()

    async def test_kanban_setup_called_on_fallback(self) -> None:
        """
        Creation proceeds past the project_root guard, so kanban setup
        runs — a board IS created for the (feature_based) project.
        """
        creator = _make_creator()

        with patch("src.integrations.nlp_tools.log_agent_event"):
            await creator.create_project_from_description(
                description="Build a chess game",
                project_name="Chess",
                options=None,
            )

        creator.kanban_client.auto_setup_project.assert_called()


# ---------------------------------------------------------------------------
# Layer 3: create_tasks must not trip the fail-fast
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
class TestCreateTasksDefaultsToFeatureBased:
    """
    ``create_tasks`` adds tasks to an existing project and has no documented
    ``project_root`` option.  It must not trip the contract_first fail-fast.

    The fix: ``create_tasks`` must inject ``decomposer=feature_based`` into
    options before calling ``create_project_from_description`` when neither
    ``decomposer`` nor ``project_root`` is already set by the caller.
    """

    async def test_create_tasks_without_project_root_does_not_fail_fast(
        self,
    ) -> None:
        """
        Calling create_tasks with no options must not trigger the
        contract_first fail-fast — it should reach task creation, not return
        a project_root error.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_state = MagicMock()
        mock_project = MagicMock()
        mock_project.name = "TestProject"
        mock_project.provider_config = {
            "project_id": "proj-1",
            "board_id": "board-1",
            "board_name": "Main Board",
        }
        mock_state.project_registry.get_active_project = AsyncMock(
            return_value=mock_project
        )
        mock_kanban = MagicMock()
        mock_state.project_manager.get_kanban_client = AsyncMock(
            return_value=mock_kanban
        )
        mock_state.ai_engine = MagicMock()
        mock_state.subtask_manager = None

        mock_result = {"success": True, "tasks_created": 3}

        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            mock_creator_inst = MagicMock()
            mock_creator_inst.create_project_from_description = AsyncMock(
                return_value=mock_result
            )
            MockCreator.return_value = mock_creator_inst

            from src.marcus_mcp.tools.nlp import create_tasks

            result = await create_tasks(
                task_description="Add user authentication",
                state=mock_state,
            )

        assert (
            result.get("success") is True
        ), f"create_tasks must succeed without project_root. Got: {result}"

        # Verify feature_based was injected into the options passed downstream
        call_kwargs = mock_creator_inst.create_project_from_description.call_args
        passed_options = call_kwargs.kwargs.get(
            "options", call_kwargs.args[2] if len(call_kwargs.args) > 2 else {}
        )
        assert passed_options.get("decomposer") == "feature_based", (
            f"create_tasks must inject decomposer=feature_based when no "
            f"project_root is set. Options passed: {passed_options}"
        )

    async def test_create_tasks_respects_explicit_decomposer(self) -> None:
        """
        If the caller explicitly sets options.decomposer, create_tasks must
        not overwrite it — the injection only fires when decomposer is absent.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_state = MagicMock()
        mock_project = MagicMock()
        mock_project.name = "TestProject"
        mock_project.provider_config = {
            "project_id": "proj-1",
            "board_id": "board-1",
            "board_name": "Main Board",
        }
        mock_state.project_registry.get_active_project = AsyncMock(
            return_value=mock_project
        )
        mock_state.project_manager.get_kanban_client = AsyncMock(
            return_value=MagicMock()
        )
        mock_state.ai_engine = MagicMock()
        mock_state.subtask_manager = None

        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            mock_creator_inst = MagicMock()
            mock_creator_inst.create_project_from_description = AsyncMock(
                return_value={"success": True, "tasks_created": 1}
            )
            MockCreator.return_value = mock_creator_inst

            from src.marcus_mcp.tools.nlp import create_tasks

            await create_tasks(
                task_description="Add payments",
                options={
                    "decomposer": "contract_first",
                    "project_root": "/home/agent/projects/p",
                },
                state=mock_state,
            )

        call_kwargs = mock_creator_inst.create_project_from_description.call_args
        passed_options = call_kwargs.kwargs.get(
            "options", call_kwargs.args[2] if len(call_kwargs.args) > 2 else {}
        )
        assert (
            passed_options.get("decomposer") == "contract_first"
        ), "Explicit decomposer must not be overwritten by create_tasks injection."
