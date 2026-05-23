"""Tests for the Task → kanban task_data conversion of completion_criteria.

This file pins a bug found by inspection of post-#608/#611 kanban data:
``TaskBuilder.build_task_data`` at ``src/integrations/nlp_task_utils.py``
copied ``acceptance_criteria`` from the in-memory ``Task`` object but
never copied ``completion_criteria``. Steps 3 and 4 of #607 populated
``Task.completion_criteria`` correctly, but the field was silently
dropped at the conversion to ``task_data`` before kanban persistence.

The unit tests for #608 + #611 passed because they asserted on the
in-memory ``Task`` object — they never went through the persistence
chain.

Tests:

1. ``build_task_data`` carries ``completion_criteria`` from the Task
   into the result dict (the missing-line bug).
2. The list-of-strings shape matches what the SQLite persistence
   layer expects.
3. Empty / None ``completion_criteria`` is handled gracefully
   (matches the pre-fix behavior for tasks without criteria).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.nlp_task_utils import TaskBuilder

pytestmark = pytest.mark.unit


def _make_task(
    *,
    completion_criteria: Optional[List[str]] = None,
    acceptance_criteria: Optional[List[str]] = None,
) -> Task:
    """Minimal Task with optional completion / acceptance criteria."""
    now = datetime.now(timezone.utc)
    return Task(
        id="t_test",
        name="Implement User Login",
        description="Login flow.",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=2.0,
        labels=["implement"],
        completion_criteria=completion_criteria,
        acceptance_criteria=acceptance_criteria or [],
    )


class TestBuildTaskDataCompletionCriteria:
    """Bug pin: build_task_data must carry completion_criteria into
    the persisted task_data dict.

    Without this, every gap-fill criterion (#607 step 4) and test-
    coverage criterion (#607 step 3) was silently dropped before
    kanban persistence — making both PRs functionally inert in
    production despite passing unit tests.
    """

    def test_populated_completion_criteria_appears_in_result_dict(self) -> None:
        """The bug: build_task_data dropped completion_criteria silently.

        After the fix, a Task with non-empty completion_criteria must
        produce a task_data dict that carries the same list.
        """
        criteria = [
            "Implementation must cover: User Login — email + password",
            "Tests cover the happy path for User Login with valid input.",
        ]
        task = _make_task(completion_criteria=criteria)

        result = TaskBuilder.build_task_data(task)

        assert "completion_criteria" in result, (
            "build_task_data must include 'completion_criteria' in the "
            "result dict — without it the sqlite_kanban persistence "
            "layer at line ~470 silently drops every gap-fill and test-"
            "coverage criterion produced by #607 step 3 + step 4."
        )
        assert result["completion_criteria"] == criteria

    def test_none_completion_criteria_passes_through_as_none(self) -> None:
        """Tasks without criteria (design, infra, NFR) carry None.

        ``Task.completion_criteria`` is ``Optional[List[str]]`` so non-
        feature tasks have ``None``. The conversion must preserve that
        rather than coercing to an empty list — the SQLite write path
        uses ``if task_data.get("completion_criteria")`` to decide
        whether to write the field, and None matches that gate.
        """
        task = _make_task(completion_criteria=None)
        result = TaskBuilder.build_task_data(task)
        assert "completion_criteria" in result
        assert result["completion_criteria"] is None

    def test_empty_list_completion_criteria_passes_through(self) -> None:
        """Empty list is distinct from None and must survive."""
        task = _make_task(completion_criteria=[])
        result = TaskBuilder.build_task_data(task)
        assert "completion_criteria" in result
        assert result["completion_criteria"] == []

    def test_acceptance_criteria_still_carried_unchanged(self) -> None:
        """Regression guard: the existing acceptance_criteria copy must
        still work alongside the new completion_criteria copy."""
        task = _make_task(
            completion_criteria=["criterion-1"],
            acceptance_criteria=["acc-1", "acc-2"],
        )
        result = TaskBuilder.build_task_data(task)
        assert result["acceptance_criteria"] == ["acc-1", "acc-2"]
        assert result["completion_criteria"] == ["criterion-1"]
