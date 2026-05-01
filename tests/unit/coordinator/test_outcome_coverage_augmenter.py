"""Unit tests for ``OutcomeCoverageAugmenter`` (issue #456 Stage 5).

Stage 5 simplified the augmenter to a thin Protocol-satisfying
dispatcher: it picks between the two lifted module functions in
:mod:`src.marcus_mcp.coordinator.outcome_coverage` based on whether
``contract_artifacts`` is provided.

Behavior tests for the lifted functions themselves
(``apply_outcome_coverage_to_feature_graph`` and
``apply_outcome_coverage_to_contract_graph``) live in
``tests/unit/ai/test_parse_prd_outcome_integration.py`` and
``tests/unit/ai/test_contract_first_outcome_integration.py``
respectively.

This file pins:

* Protocol satisfaction (``isinstance(augmenter, GraphAugmenter)``)
* Path dispatch (correct lifted function called by ``contract_artifacts``)
* The augmenter forwards ``llm_client`` so the lifted function has
  what it needs to call the LLM
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(task_id: str, name: str = "Implement Foo") -> Task:
    """Minimal Task for dispatcher tests."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name=name,
        description="...",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=2.0,
    )


def _make_prd_analysis() -> Any:
    """Minimal PRDAnalysis for dispatcher input."""
    from src.ai.advanced.prd.advanced_parser import PRDAnalysis

    return PRDAnalysis(
        functional_requirements=[],
        non_functional_requirements=[],
        technical_constraints=[],
        business_objectives=[],
        user_personas=[],
        success_metrics=[],
        implementation_approach="iterative",
        complexity_assessment={},
        risk_factors=[],
        confidence=0.9,
        original_description="build a snake game",
    )


def _stub_augmentation_result(tasks: list[Task]) -> Any:
    """Build a passthrough AugmentationResult (no synthesis)."""
    from src.marcus_mcp.coordinator.graph_augmentation import (
        AugmentationResult,
    )

    return AugmentationResult(augmented_tasks=tasks)


# ---------------------------------------------------------------------------
# Protocol satisfaction
# ---------------------------------------------------------------------------


class TestProtocolSatisfaction:
    """Augmenter satisfies the GraphAugmenter Protocol."""

    def test_module_exports_augmenter(self) -> None:
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        assert OutcomeCoverageAugmenter is not None

    def test_augmenter_is_graph_augmenter(self) -> None:
        """``isinstance(augmenter, GraphAugmenter)`` returns True."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            GraphAugmenter,
        )
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        augmenter = OutcomeCoverageAugmenter(llm_client=AsyncMock())
        assert isinstance(augmenter, GraphAugmenter)

    def test_name_is_outcome_coverage(self) -> None:
        """Canonical name keys telemetry / log lines / event filters."""
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        augmenter = OutcomeCoverageAugmenter(llm_client=AsyncMock())
        assert augmenter.name == "outcome_coverage"


# ---------------------------------------------------------------------------
# Path dispatch
# ---------------------------------------------------------------------------


class TestPathDispatch:
    """Augmenter picks the right lifted function based on
    ``contract_artifacts``."""

    @pytest.mark.asyncio
    async def test_feature_path_when_no_contract_artifacts(self) -> None:
        """``contract_artifacts=None`` → feature-based lifted function."""
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        with (
            patch(
                "src.marcus_mcp.coordinator.outcome_coverage_augmenter."
                "apply_outcome_coverage_to_feature_graph",
                new_callable=AsyncMock,
                return_value=_stub_augmentation_result([_make_task("t1")]),
            ) as mock_feature,
            patch(
                "src.marcus_mcp.coordinator.outcome_coverage_augmenter."
                "apply_outcome_coverage_to_contract_graph",
                new_callable=AsyncMock,
            ) as mock_contract,
        ):
            augmenter = OutcomeCoverageAugmenter(llm_client=AsyncMock())
            await augmenter.augment(
                prd_analysis=_make_prd_analysis(),
                tasks=[_make_task("t1")],
                contract_artifacts=None,
            )

        mock_feature.assert_awaited_once()
        mock_contract.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_contract_path_when_contract_artifacts_provided(
        self,
    ) -> None:
        """``contract_artifacts`` non-None → contract-first lifted function."""
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        with (
            patch(
                "src.marcus_mcp.coordinator.outcome_coverage_augmenter."
                "apply_outcome_coverage_to_feature_graph",
                new_callable=AsyncMock,
            ) as mock_feature,
            patch(
                "src.marcus_mcp.coordinator.outcome_coverage_augmenter."
                "apply_outcome_coverage_to_contract_graph",
                new_callable=AsyncMock,
                return_value=_stub_augmentation_result([_make_task("t1")]),
            ) as mock_contract,
        ):
            augmenter = OutcomeCoverageAugmenter(llm_client=AsyncMock())
            await augmenter.augment(
                prd_analysis=_make_prd_analysis(),
                tasks=[_make_task("t1")],
                contract_artifacts={"Auth": {"artifacts": [{"content": "..."}]}},
            )

        mock_contract.assert_awaited_once()
        mock_feature.assert_not_awaited()


# ---------------------------------------------------------------------------
# LLM client forwarding
# ---------------------------------------------------------------------------


class TestLlmClientForwarding:
    """Augmenter forwards its constructor ``llm_client`` to lifted functions.

    The lifted functions need an LLM client to call the coverage and
    fill-gaps prompts.  Without forwarding, the lifted function would
    raise TypeError on missing kwarg, or worse, bind a None client and
    crash inside the LLM call.  These tests pin the forwarding contract.
    """

    @pytest.mark.asyncio
    async def test_feature_path_forwards_llm_client(self) -> None:
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        my_llm = AsyncMock()
        with patch(
            "src.marcus_mcp.coordinator.outcome_coverage_augmenter."
            "apply_outcome_coverage_to_feature_graph",
            new_callable=AsyncMock,
            return_value=_stub_augmentation_result([_make_task("t1")]),
        ) as mock_feature:
            augmenter = OutcomeCoverageAugmenter(llm_client=my_llm)
            await augmenter.augment(
                prd_analysis=_make_prd_analysis(),
                tasks=[_make_task("t1")],
            )

        assert mock_feature.call_args.kwargs["llm_client"] is my_llm

    @pytest.mark.asyncio
    async def test_contract_path_forwards_llm_client(self) -> None:
        from src.marcus_mcp.coordinator.outcome_coverage_augmenter import (
            OutcomeCoverageAugmenter,
        )

        my_llm = AsyncMock()
        with patch(
            "src.marcus_mcp.coordinator.outcome_coverage_augmenter."
            "apply_outcome_coverage_to_contract_graph",
            new_callable=AsyncMock,
            return_value=_stub_augmentation_result([_make_task("t1")]),
        ) as mock_contract:
            augmenter = OutcomeCoverageAugmenter(llm_client=my_llm)
            await augmenter.augment(
                prd_analysis=_make_prd_analysis(),
                tasks=[_make_task("t1")],
                contract_artifacts={"X": {"artifacts": []}},
            )

        assert mock_contract.call_args.kwargs["llm_client"] is my_llm
