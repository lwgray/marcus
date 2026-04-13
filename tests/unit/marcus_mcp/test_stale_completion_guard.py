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
