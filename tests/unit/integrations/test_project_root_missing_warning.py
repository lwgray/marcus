"""
Unit tests for issue #478: contract_first silent fallback when project_root absent.

When the active decomposer strategy is ``contract_first`` (default) but the caller
omits ``project_root`` from ``options``, Marcus silently falls back to
``feature_based`` and emits only a logger.warning.  The result dict returned by
``create_project_from_description`` — and thus the MCP response — contains no
indication that the caller is getting a degraded decomposition path with no
structural scaffolding.

This module tests the helper ``_build_decomposer_warning`` and its integration
into the result dict.  The helper is the single source of truth for the check;
the integration verifies it is wired into the final result.
"""

from typing import Any, Optional

import pytest

from src.integrations.nlp_tools import _build_decomposer_warning


class TestBuildDecomposerWarning:
    """Test suite for ``_build_decomposer_warning``."""

    def test_returns_warning_when_contract_first_and_no_project_root(self) -> None:
        """
        When contract_first is the active strategy and project_root is absent,
        a non-empty warning string must be returned.

        This is the primary bug path: caller uses default options (or explicit
        ``decomposer=contract_first``) without ``project_root``.  Marcus
        falls back silently; the warning surfaces that to the caller.
        """
        warning = _build_decomposer_warning(options=None)
        assert warning is not None
        assert len(warning) > 0
        assert "project_root" in warning
        assert "feature_based" in warning

    def test_returns_warning_for_explicit_contract_first_no_project_root(
        self,
    ) -> None:
        """
        Explicit ``decomposer=contract_first`` in options without project_root
        must also produce a warning.
        """
        options: dict[str, Any] = {"decomposer": "contract_first"}
        warning = _build_decomposer_warning(options=options)
        assert warning is not None
        assert "project_root" in warning

    def test_returns_none_when_project_root_provided(self) -> None:
        """
        When project_root is supplied, contract_first CAN run — no warning.
        """
        options: dict[str, Any] = {
            "decomposer": "contract_first",
            "project_root": "/home/agent/projects/myproject",
        }
        warning = _build_decomposer_warning(options=options)
        assert warning is None

    def test_returns_none_when_project_root_provided_and_no_explicit_decomposer(
        self,
    ) -> None:
        """
        Default strategy (contract_first) with project_root present: no warning.

        This is the happy path for skill-based callers that correctly pass
        project_root.
        """
        options: dict[str, Any] = {"project_root": "/home/agent/projects/impl"}
        warning = _build_decomposer_warning(options=options)
        assert warning is None

    def test_returns_none_for_explicit_feature_based(self) -> None:
        """
        When the caller explicitly requests feature_based, no project_root is
        needed — no warning should be emitted.
        """
        options: dict[str, Any] = {"decomposer": "feature_based"}
        warning = _build_decomposer_warning(options=options)
        assert warning is None

    def test_returns_none_for_feature_based_even_without_project_root(self) -> None:
        """
        Explicit feature_based with no project_root: caller chose the fallback
        intentionally, no warning needed.
        """
        options: dict[str, Any] = {"decomposer": "feature_based"}
        warning = _build_decomposer_warning(options=options)
        assert warning is None

    def test_warning_message_mentions_structural_scaffolding(self) -> None:
        """
        The warning must mention the practical consequence (no structural
        scaffolding) so callers understand the impact, not just the cause.
        """
        warning = _build_decomposer_warning(options=None)
        assert warning is not None
        assert "structural" in warning.lower() or "scaffolding" in warning.lower()
