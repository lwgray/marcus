"""
Unit tests for helpers in ``src.integrations.nlp_tools``.

These tests cover small, pure helpers that can be exercised without
spinning up a kanban client or AI engine. Integration behavior of
``NaturalLanguageProjectCreator`` is covered in the integration test
suite.
"""

from datetime import datetime

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.enhanced_task_classifier import EnhancedTaskClassifier
from src.integrations.nlp_tools import _task_type_breakdown


def _make_task(
    *,
    task_id: str,
    name: str,
    labels: list[str],
    description: str = "",
) -> Task:
    """
    Build a minimal Task instance for classifier tests.

    Parameters
    ----------
    task_id : str
        Unique task identifier.
    name : str
        Task name — strong classifier signal.
    labels : list[str]
        Task labels — strongest classifier signal.
    description : str, optional
        Task description — weak classifier signal.

    Returns
    -------
    Task
        Populated Task dataclass ready for classification.
    """
    return Task(
        id=task_id,
        name=name,
        description=description,
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        due_date=None,
        estimated_hours=1.0,
        labels=labels,
    )


class TestTaskTypeBreakdown:
    """Test suite for ``_task_type_breakdown``."""

    @pytest.fixture
    def classifier(self) -> EnhancedTaskClassifier:
        """Return a real classifier — fast, no external deps."""
        return EnhancedTaskClassifier()

    def test_contract_first_tasks_classify_as_implementation(
        self, classifier: EnhancedTaskClassifier
    ) -> None:
        """
        Regression test: contract-first tasks must not be labeled
        'unknown' in the task-type breakdown.

        Before this fix, the breakdown loop used
        ``getattr(task, "task_type", "unknown")`` which always fell
        back to ``"unknown"`` because Task has no ``task_type``
        attribute. The fix routes through the EnhancedTaskClassifier,
        which correctly recognizes the ``implementation`` label on
        contract-first tasks.
        """
        tasks = [
            _make_task(
                task_id="t1",
                name="Implement WeatherWidget",
                labels=["contract_first", "implementation"],
                description=(
                    "implements WeatherWidget module from "
                    "weather-information-system-interface-contracts.md"
                ),
            ),
            _make_task(
                task_id="t2",
                name="Implement TimeWidget",
                labels=["contract_first", "implementation"],
                description=(
                    "implements TimeWidget module from "
                    "time-display-system-interface-contracts.md"
                ),
            ),
            _make_task(
                task_id="t3",
                name="Implement Dashboard Container",
                labels=["contract_first", "implementation"],
                description=(
                    "implements Dashboard Container from "
                    "dashboard-presentation-layer-interface-contracts.md"
                ),
            ),
        ]

        breakdown = _task_type_breakdown(tasks, classifier)

        assert "unknown" not in breakdown, (
            f"Contract-first tasks must not classify as 'unknown': " f"{breakdown}"
        )
        assert (
            breakdown.get("implementation", 0) == 3
        ), f"Expected 3 implementation tasks, got: {breakdown}"

    def test_mixed_task_types_produce_accurate_histogram(
        self, classifier: EnhancedTaskClassifier
    ) -> None:
        """
        Breakdown counts by TaskType enum value, not by string
        attribute. A mix of design/implement/test tasks produces a
        histogram with three non-zero buckets.
        """
        tasks = [
            _make_task(
                task_id="d1",
                name="Design the API schema",
                labels=["design"],
            ),
            _make_task(
                task_id="i1",
                name="Implement user authentication",
                labels=["implementation"],
            ),
            _make_task(
                task_id="i2",
                name="Build the dashboard component",
                labels=["implementation"],
            ),
            _make_task(
                task_id="t1",
                name="Write integration tests for auth",
                labels=["testing"],
            ),
        ]

        breakdown = _task_type_breakdown(tasks, classifier)

        assert breakdown.get("design", 0) == 1, breakdown
        assert breakdown.get("implementation", 0) == 2, breakdown
        assert breakdown.get("testing", 0) == 1, breakdown
        assert "unknown" not in breakdown, breakdown

    def test_empty_task_list_returns_empty_breakdown(
        self, classifier: EnhancedTaskClassifier
    ) -> None:
        """No tasks → empty histogram, not an error."""
        assert _task_type_breakdown([], classifier) == {}
