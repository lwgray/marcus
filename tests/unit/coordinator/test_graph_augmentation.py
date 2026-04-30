"""
Unit tests for the ``GraphAugmenter`` protocol + ``AugmentationResult``
dataclass (issue #456 — Stage 1).

This stage defines the abstract surface only.  No behavior change
yet.  Tests pin the Protocol shape, dataclass fields, and runtime-
checkability so subsequent stages (OutcomeCoverageAugmenter,
SpecCoverageAugmenter) can wrap existing implementations against a
stable interface.

Why a Protocol (structural) rather than ABC (nominal): Marcus's
existing pipeline conventions favor duck typing; structural typing
keeps the interface non-invasive to existing classes.  ``@runtime_checkable``
lets the orchestrator validate registered augmenters with
``isinstance`` when registration happens, without requiring those
classes to inherit from a base.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from src.core.models import Priority, Task, TaskStatus

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# AugmentationResult dataclass
# ---------------------------------------------------------------------------


class TestAugmentationResultDataclass:
    """``AugmentationResult`` carries the canonical augmenter output shape."""

    def test_module_exports_augmentation_result(self) -> None:
        """``AugmentationResult`` is importable from the canonical module."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
        )

        assert AugmentationResult is not None

    def test_required_field_augmented_tasks(self) -> None:
        """``augmented_tasks`` is a required field carrying the
        post-augmentation graph (original tasks + any synthesized).
        """
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
        )

        result = AugmentationResult(augmented_tasks=[])
        assert result.augmented_tasks == []

    def test_synthesized_ids_defaults_to_empty_list(self) -> None:
        """``synthesized_ids`` carries IDs of newly added tasks.

        Subset of ``augmented_tasks``.  Empty when no synthesis ran.
        Default factory so each instance gets its own list (no
        mutable-default shared state).
        """
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
        )

        a = AugmentationResult(augmented_tasks=[])
        b = AugmentationResult(augmented_tasks=[])
        assert a.synthesized_ids == []
        assert b.synthesized_ids == []
        # Mutation on one must not affect the other (default-factory check)
        a.synthesized_ids.append("x")
        assert b.synthesized_ids == []

    def test_telemetry_defaults_to_empty_dict(self) -> None:
        """``telemetry`` is augmenter-specific metrics for event emission.

        Generic ``Dict[str, Any]`` keeps the Protocol simple — typed
        Union would force every augmenter to declare a typed payload
        upfront, premature when the augmenter shapes are still
        evolving.  Default factory so each instance gets its own dict.
        """
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
        )

        a = AugmentationResult(augmented_tasks=[])
        b = AugmentationResult(augmented_tasks=[])
        assert a.telemetry == {}
        assert b.telemetry == {}
        a.telemetry["score"] = 1.0
        assert b.telemetry == {}

    def test_can_construct_with_all_fields(self) -> None:
        """Smoke test: dataclass accepts all three fields explicitly."""
        from datetime import datetime, timezone

        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
        )

        now = datetime.now(timezone.utc)
        task = Task(
            id="t1",
            name="Test",
            description="...",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=1.0,
        )
        result = AugmentationResult(
            augmented_tasks=[task],
            synthesized_ids=["t1"],
            telemetry={"score": 0.5, "extra": "data"},
        )
        assert len(result.augmented_tasks) == 1
        assert result.synthesized_ids == ["t1"]
        assert result.telemetry == {"score": 0.5, "extra": "data"}


# ---------------------------------------------------------------------------
# GraphAugmenter Protocol
# ---------------------------------------------------------------------------


class TestGraphAugmenterProtocol:
    """``GraphAugmenter`` is a Protocol (structural type) for pre-inference
    task graph augmentation.  Stage-2 will provide the first
    implementation (OutcomeCoverageAugmenter); Stage-4 the second
    (SpecCoverageAugmenter).
    """

    def test_module_exports_graph_augmenter(self) -> None:
        """``GraphAugmenter`` is importable from the canonical module."""
        from src.marcus_mcp.coordinator.graph_augmentation import (
            GraphAugmenter,
        )

        assert GraphAugmenter is not None

    def test_protocol_is_runtime_checkable(self) -> None:
        """``@runtime_checkable`` lets the orchestrator validate
        registered augmenters via ``isinstance``.

        Pre-#456 Marcus had no augmenter registry.  Stage-3 adds one;
        registration-time validation needs ``isinstance(thing, GraphAugmenter)``
        to fail loud on misregistered classes that don't satisfy the
        Protocol.  Without ``@runtime_checkable``, the failure would
        only surface at first .augment() call.
        """
        from typing import _ProtocolMeta  # type: ignore[attr-defined]

        from src.marcus_mcp.coordinator.graph_augmentation import (
            GraphAugmenter,
        )

        # Protocol classes have a magic attribute set by @runtime_checkable
        assert getattr(
            GraphAugmenter, "_is_runtime_protocol", False
        ), "GraphAugmenter must be decorated with @runtime_checkable"

    def test_stub_implementation_satisfies_protocol(self) -> None:
        """A concrete class with the right shape passes ``isinstance``.

        Pins the Protocol surface: any class with ``name: str`` and
        an async ``augment`` method matching the signature should be
        accepted.  This is the contract Stage-2 / Stage-4 augmenters
        must satisfy.
        """
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
            GraphAugmenter,
        )

        class StubAugmenter:
            """Minimal Protocol-satisfying stub for testing."""

            name: str = "stub"

            async def augment(
                self,
                *,
                prd_analysis: Any,
                tasks: List[Task],
                contract_artifacts: Optional[Dict[str, Any]] = None,
            ) -> AugmentationResult:
                return AugmentationResult(augmented_tasks=tasks)

        stub = StubAugmenter()
        assert isinstance(stub, GraphAugmenter)

    def test_class_missing_name_does_not_satisfy_protocol(self) -> None:
        """Anti-regression: classes lacking ``name`` attribute fail
        the Protocol check.

        ``name`` is required for telemetry / event emission keying.
        """
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
            GraphAugmenter,
        )

        class NoNameAugmenter:
            async def augment(
                self,
                *,
                prd_analysis: Any,
                tasks: List[Task],
                contract_artifacts: Optional[Dict[str, Any]] = None,
            ) -> AugmentationResult:
                return AugmentationResult(augmented_tasks=tasks)

        no_name = NoNameAugmenter()
        # runtime_checkable Protocol requires all attributes to exist
        assert not isinstance(no_name, GraphAugmenter)

    def test_class_missing_augment_does_not_satisfy_protocol(self) -> None:
        """Anti-regression: classes lacking ``augment`` method fail.

        The ``augment`` method is the augmenter's only behavioral
        contract.  A class without it can't participate in the chain.
        """
        from src.marcus_mcp.coordinator.graph_augmentation import (
            GraphAugmenter,
        )

        class NoAugmentAugmenter:
            name: str = "broken"

        broken = NoAugmentAugmenter()
        assert not isinstance(broken, GraphAugmenter)


# ---------------------------------------------------------------------------
# Stage-1 contract: NO behavior change
# ---------------------------------------------------------------------------


class TestStage1NoBehaviorChange:
    """Stage 1 only defines the abstract surface — no caller switches
    to the new Protocol yet.  These tests pin that the existing
    outcome_coverage and spec_coverage code paths remain untouched.

    Stage-3 will switch parse_prd_to_tasks to the augmenter chain;
    Stage-4 will join spec_coverage.  At Stage 1, both old call sites
    must still exist as before.
    """

    def test_outcome_coverage_helpers_still_exist(self) -> None:
        """``_apply_outcome_coverage_to_graph`` and
        ``_apply_outcome_coverage_to_contract_graph`` still on
        AdvancedPRDParser at Stage 1.  Stage-3 removes them.
        """
        from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser

        assert hasattr(AdvancedPRDParser, "_apply_outcome_coverage_to_graph")
        assert hasattr(AdvancedPRDParser, "_apply_outcome_coverage_to_contract_graph")

    def test_check_spec_coverage_still_callable(self) -> None:
        """``check_spec_coverage`` public function still exists at Stage 1.
        Stage-4 may remove it when the call site is migrated.
        """
        from src.integrations.spec_coverage import check_spec_coverage

        assert callable(check_spec_coverage)
