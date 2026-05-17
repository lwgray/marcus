"""
Unit tests for subtask-aware task resolution in the validation gate.

Regression coverage for issue #557. The validation gate in
``report_task_progress`` resolves the completed task by id before
deciding whether to validate it. It used to look only at
``kanban_client.get_all_tasks()`` — which returns parent tasks only.
Subtasks (``is_subtask=True``) live in ``state.project_tasks``, so a
subtask completion resolved to ``None`` and the whole validation block
was skipped, letting stub/placeholder code reach DONE unvalidated.

These tests cover the two helpers extracted for the fix:
``_resolve_completed_task`` and ``_validation_filter_task``.
"""

from datetime import datetime, timezone

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.tools.task import (
    _resolve_completed_task,
    _should_validate_completion,
)

pytestmark = pytest.mark.unit


def _task(
    task_id: str,
    *,
    name: str = "Task",
    labels: list[str] | None = None,
    is_subtask: bool = False,
    parent_task_id: str | None = None,
) -> Task:
    """Build a minimal Task for resolution tests."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name=name,
        description="",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=1.0,
        labels=labels or [],
        is_subtask=is_subtask,
        parent_task_id=parent_task_id,
    )


class TestResolveCompletedTask:
    """``_resolve_completed_task`` must find board tasks AND subtasks."""

    def test_resolves_parent_task_from_board(self) -> None:
        """A parent task id resolves from the kanban board list."""
        board = [_task("parent-1"), _task("parent-2")]
        result = _resolve_completed_task("parent-2", board, project_tasks=[])
        assert result is not None
        assert result.id == "parent-2"

    def test_resolves_subtask_from_project_tasks_on_board_miss(self) -> None:
        """
        REGRESSION #557: a subtask id is absent from the board but present
        in project_tasks — it must still resolve, not return None.
        """
        board = [_task("parent-1")]
        subtask = _task("parent-1_sub_3", is_subtask=True, parent_task_id="parent-1")
        project_tasks = [_task("parent-1"), subtask]

        result = _resolve_completed_task("parent-1_sub_3", board, project_tasks)

        assert result is not None
        assert result.id == "parent-1_sub_3"
        assert result.is_subtask is True

    def test_board_takes_precedence_over_project_tasks(self) -> None:
        """A board hit is used even when project_tasks also has the id."""
        board = [_task("t-1", name="fresh")]
        project_tasks = [_task("t-1", name="stale")]
        result = _resolve_completed_task("t-1", board, project_tasks)
        assert result is not None and result.name == "fresh"

    def test_returns_none_when_id_matches_neither_store(self) -> None:
        """An unknown id resolves to None (no crash)."""
        assert _resolve_completed_task("ghost", [_task("a")], [_task("b")]) is None


class TestShouldValidateCompletion:
    """``_should_validate_completion`` decides validate-vs-skip (#557)."""

    def test_non_subtask_implementation_task_validates(self) -> None:
        """A normal implementation task is validated."""
        t = _task("t-1", labels=["implement"])
        assert _should_validate_completion(t, board_tasks=[]) is True

    def test_non_subtask_design_task_skips(self) -> None:
        """A non-implementation task (design) is not validated."""
        t = _task("t-1", labels=["design"])
        assert _should_validate_completion(t, board_tasks=[]) is False

    def test_subtask_uses_parent_labels(self) -> None:
        """
        REGRESSION #557: a subtask may carry no implementation labels.
        The decision uses the parent's labels — a subtask of an
        implementation parent is validated.
        """
        parent = _task("parent-1", labels=["implement", "backend"])
        subtask = _task(
            "parent-1_sub_1",
            labels=[],
            is_subtask=True,
            parent_task_id="parent-1",
        )
        assert _should_validate_completion(subtask, board_tasks=[parent]) is True

    def test_subtask_skips_when_parent_is_design(self) -> None:
        """A subtask of a design parent is not validated."""
        parent = _task("parent-1", labels=["design"])
        subtask = _task(
            "parent-1_sub_1", labels=[], is_subtask=True, parent_task_id="parent-1"
        )
        assert _should_validate_completion(subtask, board_tasks=[parent]) is False

    def test_subtask_validates_when_parent_missing(self) -> None:
        """
        Fail toward validating: a subtask whose parent cannot be resolved
        is validated anyway — skipping it would silently reopen the #557
        gap. A subtask only exists because its parent was decomposable
        implementation work.
        """
        subtask = _task(
            "orphan_sub_1", is_subtask=True, parent_task_id="missing-parent"
        )
        assert _should_validate_completion(subtask, board_tasks=[]) is True
