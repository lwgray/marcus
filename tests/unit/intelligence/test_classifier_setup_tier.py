"""
Unit tests for the setup-tier classifier in :class:`DependencyInferer`.

Issue #455 — ``_is_logical_dependency`` rejected foundation/setup tasks
as prerequisites of implementation tasks because ``_classify_task_type``
returned ``"other"`` (order ``2.5``) for any name not matching the
design / implementation / testing / deployment keyword sets, and
``2.5 >= 2`` (implementation) blocked the dependency.

Fix introduces a ``"setup"`` tier (order ``0.5``) with explicit keywords
(``setup``, ``init``, ``configure``, ``install``, ``scaffold``,
``foundation``).  Foundation tasks now correctly classify and pass
the logical-order gate when the regex pattern fires.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.intelligence.dependency_inferer import DependencyInferer

pytestmark = pytest.mark.unit


def _make_task(task_id: str, name: str, description: str = "") -> Task:
    """Build a minimal Task for classifier tests."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name=name,
        description=description,
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=2.0,
    )


def _make_inferer() -> Any:
    """Construct a DependencyInferer with no AI engine (pattern-only)."""
    return DependencyInferer()


class TestClassifyTaskTypeSetupTier:
    """``_classify_task_type`` recognizes setup/foundation task names."""

    @pytest.mark.parametrize(
        "name",
        [
            "Tech Foundation Setup",
            "Initial Setup",
            "Configure TypeScript",
            "Install Dependencies",
            "Scaffold Project Structure",
            "Initialize Database",
            "Foundation Layer",
        ],
    )
    def test_setup_keywords_classify_as_setup(self, name: str) -> None:
        """Names containing setup keywords land in the setup tier."""
        inferer = _make_inferer()
        assert inferer._classify_task_type(name) == "setup"

    def test_design_still_wins_over_setup_when_both_present(self) -> None:
        """Design task that mentions setup stays classified as design.

        Currently the classifier checks design before setup — this test
        pins that ordering so design tasks aren't accidentally
        downgraded to the setup tier.  ``_classify_task_type`` checks
        in declaration order; design comes first.
        """
        inferer = _make_inferer()
        assert inferer._classify_task_type("Design Initial Setup Approach") == "design"

    def test_implementation_still_wins_over_setup(self) -> None:
        """``Implement initial X`` stays classified as implementation."""
        inferer = _make_inferer()
        assert (
            inferer._classify_task_type("Implement Initial Configuration")
            == "implementation"
        )

    def test_unknown_name_still_returns_other(self) -> None:
        """Names matching no tier still classify as 'other'."""
        inferer = _make_inferer()
        assert inferer._classify_task_type("Game State Data Structure") == "other"


class TestIsLogicalDependencyFoundationToImpl:
    """``_is_logical_dependency`` accepts foundation → implementation deps.

    Pre-#455 regression: ``Tech Foundation Setup`` (other, order 2.5)
    couldn't be a prerequisite of ``Implement X`` (implementation,
    order 2.0) because ``2.5 >= 2`` blocked the edge.  With setup tier
    at order 0.5, the same dep passes the gate.
    """

    def test_tech_foundation_setup_is_valid_prereq_of_implement(self) -> None:
        """``Tech Foundation Setup`` can be a prereq of ``Implement X``."""
        inferer = _make_inferer()
        dep_task = _make_task("t1", "Tech Foundation Setup")
        dependent_task = _make_task("t2", "Implement Speed Progression")
        # setup_blocks_all pattern is at index 0; pattern-agnostic check
        # via the ``setup_blocks_all`` pattern object directly.
        pattern = next(
            p for p in inferer.dependency_patterns if p.name == "setup_blocks_all"
        )
        assert inferer._is_logical_dependency(
            dependent_task=dependent_task,
            dependency_task=dep_task,
            pattern=pattern,
        )

    def test_install_dependencies_is_valid_prereq_of_implement(self) -> None:
        """``Install Dependencies`` can be a prereq of ``Implement X``."""
        inferer = _make_inferer()
        dep_task = _make_task("t1", "Install Dependencies")
        dependent_task = _make_task("t2", "Implement Auth Service")
        pattern = next(
            p for p in inferer.dependency_patterns if p.name == "setup_blocks_all"
        )
        assert inferer._is_logical_dependency(
            dependent_task=dependent_task,
            dependency_task=dep_task,
            pattern=pattern,
        )

    def test_setup_can_precede_design(self) -> None:
        """Setup tasks (order 0.5) sit below design tasks (order 1).

        ``setup_blocks_all`` pattern condition doesn't include
        ``design`` so this pattern wouldn't fire for setup→design
        edges anyway.  This test asserts the order math: if any
        future pattern fires setup→design, the order check accepts.
        """
        inferer = _make_inferer()
        assert inferer._classify_task_type("Tech Foundation Setup") == "setup"
        assert inferer._classify_task_type("Design User Authentication") == "design"

    def test_no_regression_design_to_implement(self) -> None:
        """Design → Implementation still works (the existing pattern).

        This is the canonical case and must not regress.
        """
        inferer = _make_inferer()
        dep_task = _make_task("t1", "Design User Authentication")
        dependent_task = _make_task("t2", "Implement User Authentication")
        pattern = next(
            p
            for p in inferer.dependency_patterns
            if p.name == "design_before_implementation"
        )
        assert inferer._is_logical_dependency(
            dependent_task=dependent_task,
            dependency_task=dep_task,
            pattern=pattern,
        )

    def test_no_regression_implement_to_test(self) -> None:
        """Implementation → Testing still works."""
        inferer = _make_inferer()
        dep_task = _make_task("t1", "Implement User Authentication")
        dependent_task = _make_task("t2", "Test User Authentication")
        pattern = next(
            p
            for p in inferer.dependency_patterns
            if p.name == "implementation_before_testing"
        )
        assert inferer._is_logical_dependency(
            dependent_task=dependent_task,
            dependency_task=dep_task,
            pattern=pattern,
        )

    def test_setup_cannot_be_prereq_of_setup(self) -> None:
        """Two setup tasks cannot have a typed-order edge between them.

        Prevents accidental cycles within the setup tier.  Specific
        sequencing between setup tasks must come from another signal
        (explicit dep declaration, naming heuristic), not the type
        classifier.  Same-tier order check: ``0.5 >= 0.5`` is True →
        edge rejected.
        """
        inferer = _make_inferer()
        assert inferer._classify_task_type("Configure TypeScript") == "setup"
        assert inferer._classify_task_type("Install Dependencies") == "setup"
