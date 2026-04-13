"""
Unit tests for the stale-completion guard in report_task_progress.

Regression coverage for Issue #343 (simultaneous completion guard
for recovered tasks). When a task's lease expires and is recovered
to another agent, the original agent's in-memory assignment is
cleared. If that original agent keeps working locally and later
reports completion — unaware their assignment was revoked — Marcus
must reject the stale completion. Otherwise we accept a second
completion on a task another agent is actively working on, and the
two implementations collide at merge time.

Dashboard-v70 Epictetus audit: 341 lines of ghost source + 506
lines of ghost tests were produced by exactly this race.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.models import Priority, TaskAssignment
from src.marcus_mcp.tools.task import report_task_progress

pytestmark = pytest.mark.unit


def _make_assignment(task_id: str, agent_id: str = "agent-001") -> TaskAssignment:
    """Build a minimal TaskAssignment for state.agent_tasks."""
    return TaskAssignment(
        task_id=task_id,
        task_name="Test Task",
        description="desc",
        instructions="do it",
        estimated_hours=0.1,
        priority=Priority.HIGH,
        dependencies=[],
        assigned_to=agent_id,
        assigned_at=datetime.now(timezone.utc),
        due_date=None,
    )


def _make_state_with_assignment(agent_id: str, task_id: str | None) -> Mock:
    """
    Build a Mock state with agent_tasks populated appropriately.
    ``task_id=None`` simulates the post-recovery state where the
    agent's assignment was cleared by on_recovery_callback.
    """
    state = Mock()
    state.initialize_kanban = AsyncMock()
    state.kanban_client = Mock()
    state.kanban_client.get_all_tasks = AsyncMock(return_value=[])
    state.kanban_client.update_task = AsyncMock()
    state.kanban_client.update_task_progress = AsyncMock()
    # _load_workspace_state is consulted by _merge_agent_branch_to_main
    # via ``if ws_state and "project_root" in ws_state``. Returning None
    # short-circuits the merge path so the test stays focused on the
    # guard rather than git worktree behavior.
    state.kanban_client._load_workspace_state = Mock(return_value=None)
    state.agent_tasks = {}
    if task_id is not None:
        state.agent_tasks[agent_id] = _make_assignment(task_id, agent_id)
    state.project_tasks = []
    state.lease_manager = None
    state.agent_status = {}
    state.assignment_persistence = Mock()
    state.assignment_persistence.remove_assignment = AsyncMock()
    state.memory = None
    state.provider = "sqlite"
    state.code_analyzer = None
    state.subtask_manager = None
    return state


class TestStaleCompletionGuard:
    """
    ``report_task_progress`` must reject stale completions from
    agents whose assignments were cleared by recovery callback.
    """

    @pytest.mark.asyncio
    async def test_rejects_completion_when_assignment_cleared(self) -> None:
        """
        Original agent had task X, recovery cleared agent_tasks,
        agent still tries to complete X → rejected with
        stale_completion status.
        """
        state = _make_state_with_assignment("agent-001", task_id=None)

        result = await report_task_progress(
            agent_id="agent-001",
            task_id="task-343",
            status="completed",
            progress=100,
            message="finished",
            state=state,
        )

        assert result["success"] is False
        assert result["status"] == "stale_completion"
        assert result["error"] == "task_recovered"
        assert "task-343" in result["message"]
        assert "marcus/agent-001" in result["message"]
        # Kanban must NOT have been written — the whole point of
        # the guard is to prevent the double-completion side
        # effects. The completion path never runs.
        state.kanban_client.update_task.assert_not_called()
        state.kanban_client.update_task_progress.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_completion_when_agent_reassigned_to_different_task(
        self,
    ) -> None:
        """
        Original agent was recovered off task X, then picked up
        task Y. They still try to complete X from their local
        work → rejected. The agent IS in agent_tasks but their
        assignment points to a different task.
        """
        state = _make_state_with_assignment("agent-001", task_id="task-Y")

        result = await report_task_progress(
            agent_id="agent-001",
            task_id="task-X",
            status="completed",
            progress=100,
            message="finished",
            state=state,
        )

        assert result["success"] is False
        assert result["status"] == "stale_completion"
        assert "task-X" in result["message"]
        state.kanban_client.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_allows_completion_when_assignment_matches(self) -> None:
        """
        Legitimate completion: agent is assigned to task X and
        reports completion on X → guard passes, completion flows
        through the normal pipeline.
        """
        state = _make_state_with_assignment("agent-001", task_id="task-343")
        # Skip the validation gate by returning no matching task
        # from get_all_tasks (task_filter sees no task, skips).
        # This isolates the guard test from validator logic.

        result = await report_task_progress(
            agent_id="agent-001",
            task_id="task-343",
            status="completed",
            progress=100,
            message="finished",
            state=state,
        )

        # Kanban WAS written — guard did not block the path
        state.kanban_client.update_task.assert_called_once()
        # Final response surfaces success
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_allows_progress_update_even_when_assignment_cleared(
        self,
    ) -> None:
        """
        The guard fires only on status=completed. Intermediate
        progress updates (25%, 50%, etc.) from an agent whose
        assignment was cleared still flow through — the "No
        active lease" fallback in the lease path recreates the
        lease, so the agent can continue working. Only
        completions are blocked, because completions have
        irreversible kanban side effects (DONE status + branch
        merge).
        """
        state = _make_state_with_assignment("agent-001", task_id=None)

        result = await report_task_progress(
            agent_id="agent-001",
            task_id="task-343",
            status="in_progress",
            progress=50,
            message="halfway",
            state=state,
        )

        # Progress update goes through
        assert result["success"] is True
        state.kanban_client.update_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_rejects_completion_when_no_assignment_for_agent(
        self,
    ) -> None:
        """
        Agent is completely unknown to state.agent_tasks (never
        registered or was removed entirely) → reject with the
        stale-completion response. This covers the "recovery
        callback cleared our entry" path where ``agent_tasks[agent_id]``
        is missing rather than pointing to a different task.
        """
        state = _make_state_with_assignment("other-agent", task_id="task-X")

        result = await report_task_progress(
            agent_id="agent-001",
            task_id="task-343",
            status="completed",
            progress=100,
            message="finished",
            state=state,
        )

        assert result["success"] is False
        assert result["status"] == "stale_completion"
        assert result["error"] == "task_recovered"
        state.kanban_client.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_cold_cache_completion_allowed_via_lease_manager(
        self,
    ) -> None:
        """
        Codex P1 regression on PR #345.

        ``state.agent_tasks`` is in-memory only and starts EMPTY on
        Marcus restart. ``MarcusServer.__init__`` never rehydrates
        it from ``assignment_persistence``. The lease manager, on
        the other hand, IS rebuilt from persistence on startup.

        Without a fallback path, every legitimate post-restart
        completion gets rejected as stale because the in-memory
        cache is empty. The fix: when ``agent_tasks`` misses, also
        consult ``state.lease_manager.active_leases`` — if a lease
        for this task exists AND is held by this agent, allow the
        completion. The lease manager is the authoritative
        cross-restart source of truth for "who holds this task."

        This test simulates a restart by giving the state an EMPTY
        ``agent_tasks`` but a lease manager with a matching lease.
        Pre-fix this would reject; post-fix it must allow.
        """
        state = _make_state_with_assignment("agent-001", task_id=None)
        # Cold cache: no in-memory entry for this agent
        assert state.agent_tasks == {}

        # But the lease manager has a lease (rebuilt from
        # persistence on restart in the real system)
        fake_lease = Mock()
        fake_lease.agent_id = "agent-001"
        fake_lease.task_id = "task-343"
        state.lease_manager = Mock()
        state.lease_manager.active_leases = {"task-343": fake_lease}

        result = await report_task_progress(
            agent_id="agent-001",
            task_id="task-343",
            status="completed",
            progress=100,
            message="finished",
            state=state,
        )

        # Completion proceeds — the cold-cache fallback recognized
        # this agent as the legitimate lease holder.
        assert result["success"] is True
        # Kanban DONE write happened (completion path ran).
        state.kanban_client.update_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_cold_cache_rejects_when_lease_held_by_different_agent(
        self,
    ) -> None:
        """
        Cold cache fallback must NOT allow a completion when the
        lease manager says a DIFFERENT agent holds the task. This
        is the actual stale-completion case post-recovery: lease
        manager has been updated to the new holder, in-memory
        cache may or may not have been cleared, original agent
        tries to complete — both checks correctly reject.
        """
        state = _make_state_with_assignment("agent-001", task_id=None)

        fake_lease = Mock()
        fake_lease.agent_id = "different-agent"  # NOT the requester
        fake_lease.task_id = "task-343"
        state.lease_manager = Mock()
        state.lease_manager.active_leases = {"task-343": fake_lease}

        result = await report_task_progress(
            agent_id="agent-001",
            task_id="task-343",
            status="completed",
            progress=100,
            message="finished",
            state=state,
        )

        assert result["success"] is False
        assert result["status"] == "stale_completion"
        state.kanban_client.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_cold_cache_lease_lookup_error_falls_through_to_reject(
        self,
    ) -> None:
        """
        If the lease manager lookup raises (e.g. corrupt state,
        race during reload), don't crash the completion path —
        fall through to the default rejection. The agent will
        retry, the cache will eventually rebuild, and the next
        attempt will succeed.
        """
        state = _make_state_with_assignment("agent-001", task_id=None)

        broken_lease_manager = Mock()
        # Make .active_leases.get raise
        broken_active_leases = Mock()
        broken_active_leases.get = Mock(side_effect=RuntimeError("corrupt"))
        broken_lease_manager.active_leases = broken_active_leases
        state.lease_manager = broken_lease_manager

        result = await report_task_progress(
            agent_id="agent-001",
            task_id="task-343",
            status="completed",
            progress=100,
            message="finished",
            state=state,
        )

        # Falls through to rejection — defensive, not a crash.
        assert result["success"] is False
        assert result["status"] == "stale_completion"
