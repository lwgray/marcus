"""
Unit tests for lease-recovery state sync — issue #485.

When a lease is recovered, three in-memory state buckets must stay in
sync with the lease manager:

1. ``state.agent_tasks[agent_id]`` — TaskAssignment cache
2. ``state.agent_status[agent_id].current_tasks`` — Agent's current task list
3. ``state.tasks_being_assigned`` — set of task_ids being assigned

Before the fix, only (1) and (3) were cleared on recovery; (2) was
left stale.  That caused ``request_next_task`` (which reads
``current_tasks``) to disagree with ``report_task_progress`` (which
reads ``agent_tasks`` and the lease manager) about ownership.

Reproducer: ``test4-snake-game-skill-haiku`` integration verification
task — agent finished the work locally but completion was rejected as
``stale_completion`` while ``request_next_task`` insisted the agent
still owned it.  The work got stranded in ``blocked`` status.
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.models import Priority, Task, TaskAssignment, TaskStatus, WorkerStatus

pytestmark = pytest.mark.unit


def _make_task(task_id: str, name: str = "T") -> Task:
    """Build a minimal Task for current_tasks lists."""
    return Task(
        id=task_id,
        name=name,
        description="",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assigned_to="agent-001",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=1.0,
        labels=[],
        dependencies=[],
    )


def _make_assignment(task_id: str, agent_id: str = "agent-001") -> TaskAssignment:
    """Build a minimal TaskAssignment for state.agent_tasks."""
    return TaskAssignment(
        task_id=task_id,
        task_name="T",
        description="",
        instructions="",
        estimated_hours=1.0,
        priority=Priority.MEDIUM,
        dependencies=[],
        assigned_to=agent_id,
        assigned_at=datetime.now(timezone.utc),
        due_date=None,
    )


def _make_server_double(agent_id: str, task_id: str) -> Any:
    """Build a stand-in for MarcusServer with the three state buckets populated."""
    server = MagicMock()
    server.agent_tasks = {agent_id: _make_assignment(task_id, agent_id)}
    server.tasks_being_assigned = {task_id}

    agent = WorkerStatus(
        worker_id=agent_id,
        name="Agent",
        role="dev",
        email=None,
        current_tasks=[_make_task(task_id)],
        completed_tasks_count=0,
        capacity=1,
        skills=[],
        availability={},
        performance_score=1.0,
    )
    server.agent_status = {agent_id: agent}
    return server


class TestHandleLeaseRecovery:
    """``MarcusServer._handle_lease_recovery`` must clear all three buckets."""

    def test_clears_agent_tasks_bucket(self) -> None:
        """``state.agent_tasks[agent_id]`` must be deleted on recovery."""
        from src.marcus_mcp.server import MarcusServer

        server = _make_server_double("agent-001", "task-485")
        MarcusServer._handle_lease_recovery(server, "agent-001", "task-485")

        assert "agent-001" not in server.agent_tasks

    def test_clears_current_tasks_on_agent_status(self) -> None:
        """
        Issue #485: ``agent_status[agent_id].current_tasks`` must have the
        recovered task removed.  Before this fix, the task was left in
        the list — causing ``request_next_task`` to refuse new assignments
        because the agent appeared to already own one.
        """
        from src.marcus_mcp.server import MarcusServer

        server = _make_server_double("agent-001", "task-485")
        MarcusServer._handle_lease_recovery(server, "agent-001", "task-485")

        agent = server.agent_status["agent-001"]
        assert task_id_in_list("task-485", agent.current_tasks) is False, (
            f"Recovered task must be removed from current_tasks. "
            f"Got: {[t.id for t in agent.current_tasks]}"
        )

    def test_discards_tasks_being_assigned(self) -> None:
        """``tasks_being_assigned`` must drop the recovered task_id."""
        from src.marcus_mcp.server import MarcusServer

        server = _make_server_double("agent-001", "task-485")
        MarcusServer._handle_lease_recovery(server, "agent-001", "task-485")

        assert "task-485" not in server.tasks_being_assigned

    def test_only_removes_recovered_task_from_current_tasks(self) -> None:
        """
        If the agent has multiple current tasks (rare, but possible), only
        the recovered one is removed — the others remain.
        """
        from src.marcus_mcp.server import MarcusServer

        server = _make_server_double("agent-001", "task-485")
        # Add a second task that should NOT be touched
        server.agent_status["agent-001"].current_tasks.append(_make_task("task-other"))

        MarcusServer._handle_lease_recovery(server, "agent-001", "task-485")

        remaining_ids = [t.id for t in server.agent_status["agent-001"].current_tasks]
        assert "task-485" not in remaining_ids
        assert "task-other" in remaining_ids

    def test_no_crash_when_agent_status_missing(self) -> None:
        """
        If the agent isn't in ``agent_status`` (e.g. cold cache after
        restart), the recovery callback must not crash — the other
        cleanup steps still need to run.
        """
        from src.marcus_mcp.server import MarcusServer

        server = _make_server_double("agent-001", "task-485")
        del server.agent_status["agent-001"]

        # Must not raise
        MarcusServer._handle_lease_recovery(server, "agent-001", "task-485")

        # Other buckets still cleaned
        assert "agent-001" not in server.agent_tasks
        assert "task-485" not in server.tasks_being_assigned


def task_id_in_list(task_id: str, tasks: list[Task]) -> bool:
    """Return True iff any task in the list has the given id."""
    return any(t.id == task_id for t in tasks)
