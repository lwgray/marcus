"""
Unit tests for issue #478: contract_first fail-fast when project_root absent.

When the active decomposer strategy is ``contract_first`` (default) but the caller
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
        warning = _build_decomposer_warning(options=None)
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
        warning = _build_decomposer_warning(options=None)
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
class TestContractFirstFailFast:
    """
    ``create_project_from_description`` must fail fast — returning
    ``success: False`` with a clear, actionable error — when contract_first
    is active and project_root is absent.

    The fail-fast must fire BEFORE any kanban setup or LLM calls.
    """

    async def test_returns_failure_when_no_project_root_default_strategy(
        self,
    ) -> None:
        """
        Default options (contract_first, no project_root) must return
        ``success: False`` with a project_root error before any I/O.
        """
        creator = _make_creator()
        with patch("src.integrations.nlp_tools.log_agent_event"):
            result = await creator.create_project_from_description(
                description="Build a snake game",
                project_name="SnakeGame",
                options=None,
            )

        assert result.get("success") is False
        error_payload = result.get("error", {})
        error_text = (
            error_payload.get("message", "")
            if isinstance(error_payload, dict)
            else str(error_payload)
        )
        assert "project_root" in error_text, (
            f"Error must mention 'project_root' so caller knows what to add. "
            f"Got: {error_text!r}"
        )

    async def test_error_message_mentions_feature_based_alternative(self) -> None:
        """
        The error must offer the caller an escape hatch: set
        ``decomposer=feature_based`` to proceed without project_root.
        """
        creator = _make_creator()
        with patch("src.integrations.nlp_tools.log_agent_event"):
            result = await creator.create_project_from_description(
                description="Build a todo app",
                project_name="TodoApp",
                options={"decomposer": "contract_first"},
            )

        assert result.get("success") is False
        error_payload = result.get("error", {})
        error_text = (
            error_payload.get("message", "")
            if isinstance(error_payload, dict)
            else str(error_payload)
        )
        assert "feature_based" in error_text, (
            f"Error must mention 'feature_based' as the alternative. "
            f"Got: {error_text!r}"
        )

    async def test_process_natural_language_not_called_on_fail_fast(self) -> None:
        """
        When the fail-fast fires, process_natural_language must NOT be called.
        No LLM spend on a project that was misconfigured from the start.
        """
        creator = _make_creator()
        creator.process_natural_language = AsyncMock(return_value=[])

        with patch("src.integrations.nlp_tools.log_agent_event"):
            result = await creator.create_project_from_description(
                description="Build a chess game",
                project_name="Chess",
                options=None,
            )

        assert result.get("success") is False
        creator.process_natural_language.assert_not_called()

    async def test_kanban_setup_not_called_on_fail_fast(self) -> None:
        """
        The fail-fast must fire before kanban setup — no board created for a
        project that will never produce contract-first tasks.
        """
        creator = _make_creator()

        with patch("src.integrations.nlp_tools.log_agent_event"):
            result = await creator.create_project_from_description(
                description="Build a chess game",
                project_name="Chess",
                options=None,
            )

        assert result.get("success") is False
        creator.kanban_client.auto_setup_project.assert_not_called()
