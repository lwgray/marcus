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

    def test_protocol_supports_isinstance(self) -> None:
        """``@runtime_checkable`` enables ``isinstance`` against the Protocol.

        Pre-#456 Marcus had no augmenter registry.  Stage-3 adds one;
        registration-time validation calls ``isinstance(thing, GraphAugmenter)``
        to fail loud on misregistered classes.  Without
        ``@runtime_checkable``, that call raises
        ``TypeError: Protocols with non-method members don't support
        issubclass()`` rather than returning a boolean.

        Behavior test (Kaia review of Stage 1): assert
        ``isinstance(stub, GraphAugmenter)`` returns a boolean rather
        than raising.  Pre-#456 versions of this test inspected
        Python's private ``_is_runtime_protocol`` marker, which
        could rename across CPython versions and silently miss the
        decorator's removal.  Behavior test fails loud regardless of
        Python version.
        """
        from src.marcus_mcp.coordinator.graph_augmentation import (
            AugmentationResult,
            GraphAugmenter,
        )

        class StubAugmenter:
            name: str = "behavior-test-stub"

            async def augment(
                self,
                *,
                prd_analysis: Any,
                tasks: List[Task],
                contract_artifacts: Optional[Dict[str, Any]] = None,
            ) -> AugmentationResult:
                return AugmentationResult(augmented_tasks=tasks)

        try:
            result = isinstance(StubAugmenter(), GraphAugmenter)
        except TypeError as exc:
            pytest.fail(
                f"GraphAugmenter must be decorated with @runtime_checkable "
                f"so isinstance() returns a boolean.  Got TypeError: {exc}"
            )

        assert result is True

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
# Stage-5 anti-regression: legacy helpers are gone
# ---------------------------------------------------------------------------


class TestStage5LegacyHelpersRemoved:
    """Stage 5 cleanup deletes the legacy parser-side helpers.

    The Stage-1 contract was "helpers still exist" as a temporary
    invariant during the refactor.  Stage 5 inverts it: the helpers
    must NOT exist anymore — the lifted module functions in
    ``outcome_coverage.py`` are the only path.

    Anti-regression: catches a future commit that re-adds the
    underscored helpers to ``AdvancedPRDParser``, which would
    silently re-introduce the parallel-pipeline smell that #456
    eliminated.
    """

    def test_legacy_outcome_coverage_helpers_deleted(self) -> None:
        """``_apply_outcome_coverage_to_*`` methods are removed from
        AdvancedPRDParser.  The lifted module functions in
        ``src.marcus_mcp.coordinator.outcome_coverage`` replace them.
        """
        from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser

        assert not hasattr(AdvancedPRDParser, "_apply_outcome_coverage_to_graph")
        assert not hasattr(
            AdvancedPRDParser, "_apply_outcome_coverage_to_contract_graph"
        )

    def test_lifted_outcome_coverage_functions_exist(self) -> None:
        """The lifted module functions are the canonical entry points."""
        from src.marcus_mcp.coordinator.outcome_coverage import (
            apply_outcome_coverage_to_contract_graph,
            apply_outcome_coverage_to_feature_graph,
        )

        assert callable(apply_outcome_coverage_to_feature_graph)
        assert callable(apply_outcome_coverage_to_contract_graph)

    def test_parser_outcome_coverage_dataclass_deleted(self) -> None:
        """``ParserOutcomeCoverage`` dataclass is removed.

        The lifted functions return :class:`AugmentationResult`
        directly — no parser-side wrapper type remains.
        """
        import src.ai.advanced.prd.advanced_parser as parser_module

        assert not hasattr(parser_module, "ParserOutcomeCoverage")

    def test_check_spec_coverage_only_called_via_augmenter(self) -> None:
        """``check_spec_coverage`` is reachable only through the augmenter.

        The function still exists in ``spec_coverage.py`` because the
        :class:`SpecCoverageAugmenter` delegates to it.  But there must
        be no other production caller — the post-safety-check call
        site at the old ``nlp_tools.py:1336`` is gone.
        """
        from pathlib import Path

        from src.integrations.spec_coverage import check_spec_coverage

        assert callable(check_spec_coverage)

        # nlp_tools.py is the previous post-safety-check call site —
        # confirm it no longer imports the function.
        nlp_tools_path = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "integrations"
            / "nlp_tools.py"
        )
        content = nlp_tools_path.read_text()
        assert (
            "from src.integrations.spec_coverage import check_spec_coverage"
            not in content
        )
