"""Unit tests for blocked-task retry in ``report_blocker`` (issue #595).

A reported blocker is one agent giving up on a task — not proof the task
is impossible. ``report_blocker`` re-opens the task (status ``TODO``) for
a fresh agent up to ``_BLOCKER_RETRY_LIMIT`` times; only when retries are
exhausted is the task terminally ``BLOCKED``. This stops a single
blocker from stalling a layered run.

Coordination-state release (Simon decision 011b3fad) still happens on
both the retry path and the exhausted path.
"""

from datetime import datetime, timezone
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.tools.task import (
    _BLOCKER_RETRY_LIMIT,
    _blocker_retry_count,
    _labels_with_retry_count,
    report_blocker,
)

pytestmark = pytest.mark.unit


def _make_task(task_id: str = "task-1", labels: Optional[List[str]] = None) -> Task:
    """Build a minimal IN_PROGRESS task fixture with the given labels."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name="Test task",
        description="...",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assigned_to="agent-1",
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=2.0,
        dependencies=[],
        labels=labels if labels is not None else [],
    )


def _make_state(task: Task) -> Any:
    """Build a fully-mocked Marcus state holding one assigned task + lease."""
    state = MagicMock()
    state.kanban_client = AsyncMock()
    state.kanban_client.update_task = AsyncMock()
    state.kanban_client.add_comment = AsyncMock()
    state.kanban_client.get_task_by_id = AsyncMock(return_value=task)
    state.project_tasks = [task]
    state.initialize_kanban = AsyncMock()

    agent = MagicMock()
    agent.current_tasks = [task]
    state.agent_status = {"agent-1": agent}

    assignment = MagicMock()
    assignment.task_id = task.id
    state.agent_tasks = {"agent-1": assignment}

    state.assignment_persistence = AsyncMock()
    state.assignment_persistence.remove_assignment = AsyncMock()

    lease = MagicMock()
    lease.agent_id = "agent-1"
    state.lease_manager = MagicMock()
    state.lease_manager.active_leases = {task.id: lease}

    state.ai_engine = AsyncMock()
    state.ai_engine.analyze_blocker = AsyncMock(return_value="Try X")

    state.project_registry = None
    state.code_analyzer = None
    state.provider = "sqlite"
    return state


async def _report(state: Any, task: Task) -> Any:
    """Call report_blocker with the active experiment monitor patched out."""
    with patch(
        "src.experiments.live_experiment_monitor.get_active_monitor",
        return_value=None,
    ):
        return await report_blocker(
            agent_id="agent-1",
            task_id=task.id,
            blocker_description="Stuck on dep",
            severity="medium",
            state=state,
        )


def _update_payload(state: Any) -> Any:
    """The dict passed to the last kanban ``update_task`` call."""
    return state.kanban_client.update_task.call_args[0][1]


class TestBlockerRetryHelpers:
    """The pure retry-count label helpers."""

    def test_count_is_zero_with_no_retry_label(self) -> None:
        """A task with no retry label has retry count 0."""
        assert _blocker_retry_count(_make_task(labels=["other"])) == 0

    def test_count_is_zero_for_none(self) -> None:
        """A missing task is treated as retry count 0."""
        assert _blocker_retry_count(None) == 0

    def test_count_reads_retry_label(self) -> None:
        """The count is parsed from the ``retry:N`` label."""
        assert _blocker_retry_count(_make_task(labels=["x", "retry:2"])) == 2

    def test_count_is_zero_for_malformed_label(self) -> None:
        """A non-numeric retry label degrades to 0, not a crash."""
        assert _blocker_retry_count(_make_task(labels=["retry:oops"])) == 0

    def test_labels_with_retry_count_adds_label(self) -> None:
        """A retry label is added and other labels are preserved."""
        labels = _labels_with_retry_count(_make_task(labels=["keep"]), 1)
        assert "keep" in labels
        assert "retry:1" in labels

    def test_labels_with_retry_count_replaces_old(self) -> None:
        """An existing retry label is replaced, not duplicated."""
        labels = _labels_with_retry_count(_make_task(labels=["retry:1"]), 2)
        assert labels.count("retry:2") == 1
        assert "retry:1" not in labels


class TestReportBlockerRetry:
    """report_blocker re-opens a blocked task until the retry cap."""

    @pytest.mark.asyncio
    async def test_fresh_blocker_reopens_task_to_todo(self) -> None:
        """A first blocker re-opens the task to TODO for another attempt."""
        task = _make_task(labels=[])
        state = _make_state(task)

        result = await _report(state, task)

        payload = _update_payload(state)
        assert payload["status"] == TaskStatus.TODO
        assert payload["assigned_to"] is None
        assert result["retry_scheduled"] is True

    @pytest.mark.asyncio
    async def test_fresh_blocker_records_first_retry(self) -> None:
        """The first re-open stamps a ``retry:1`` label on the task."""
        task = _make_task(labels=[])
        state = _make_state(task)

        await _report(state, task)

        assert "retry:1" in _update_payload(state)["labels"]

    @pytest.mark.asyncio
    async def test_second_blocker_bumps_retry_count(self) -> None:
        """A task already retried once is re-opened again as ``retry:2``."""
        task = _make_task(labels=["retry:1"])
        state = _make_state(task)

        result = await _report(state, task)

        payload = _update_payload(state)
        assert payload["status"] == TaskStatus.TODO
        assert "retry:2" in payload["labels"]
        assert result["retry_scheduled"] is True

    @pytest.mark.asyncio
    async def test_blocker_at_retry_limit_marks_blocked(self) -> None:
        """Once the retry limit is reached, the task is terminally BLOCKED."""
        task = _make_task(labels=[f"retry:{_BLOCKER_RETRY_LIMIT}"])
        state = _make_state(task)

        result = await _report(state, task)

        assert _update_payload(state)["status"] == TaskStatus.BLOCKED
        assert result["retry_scheduled"] is False

    @pytest.mark.asyncio
    async def test_exhausted_blocker_still_releases_coordination(self) -> None:
        """The terminal BLOCKED path still releases lease + assignment.

        Simon decision 011b3fad: a terminal status flip releases
        coordination state regardless of the retry outcome.
        """
        task = _make_task(labels=[f"retry:{_BLOCKER_RETRY_LIMIT}"])
        state = _make_state(task)

        await _report(state, task)

        assert "agent-1" not in state.agent_tasks
        assert task.id not in state.lease_manager.active_leases
