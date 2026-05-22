"""
Unit tests for the get_desired_agent_count MCP tool (issue #595 Fix 3).

This tool exposes the layered-spawning signal: how many agents should be
alive right now, given the live task graph. The runner controller polls
it to spawn/retire agents to match.
"""

from datetime import datetime, timezone
from typing import Any, List, Optional

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.tools.scheduling import get_desired_agent_count

pytestmark = pytest.mark.unit


def _task(
    task_id: str,
    *,
    dependencies: Optional[List[str]] = None,
    status: TaskStatus = TaskStatus.TODO,
) -> Task:
    """Build a Task with the fields the scheduler reads."""
    return Task(
        id=task_id,
        name=f"Task {task_id}",
        description="",
        status=status,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=1.0,
        dependencies=dependencies or [],
    )


class _MockState:
    """Minimal Marcus state stand-in."""

    def __init__(self, tasks: List[Task]) -> None:
        self.project_tasks = tasks


class TestGetDesiredAgentCount:
    """get_desired_agent_count returns the live layered-spawning signal."""

    @pytest.mark.asyncio
    async def test_returns_active_layer_width(self) -> None:
        """Width of the earliest layer with incomplete work."""
        state = _MockState(
            [
                _task("l0", status=TaskStatus.DONE),
                _task("a", dependencies=["l0"]),
                _task("b", dependencies=["l0"]),
                _task("c", dependencies=["l0"]),
            ]
        )

        result = await get_desired_agent_count(max_agents=10, state=state)

        assert result["success"] is True
        assert result["desired_agent_count"] == 3

    @pytest.mark.asyncio
    async def test_no_cap_sizes_to_full_layer_width(self) -> None:
        """With no max_agents (default), desired is the full layer width."""
        state = _MockState([_task(f"t{i}") for i in range(7)])

        result = await get_desired_agent_count(state=state)

        assert result["success"] is True
        assert result["desired_agent_count"] == 7

    @pytest.mark.asyncio
    async def test_response_includes_max_layer_width(self) -> None:
        """The response carries max_layer_width — the graph's parallelism ceiling."""
        state = _MockState([_task(f"t{i}") for i in range(5)])

        result = await get_desired_agent_count(state=state)

        assert result["success"] is True
        assert result["max_layer_width"] == 5

    @pytest.mark.asyncio
    async def test_capped_by_max_agents(self) -> None:
        """The result never exceeds max_agents."""
        state = _MockState([_task(f"t{i}") for i in range(8)])

        result = await get_desired_agent_count(max_agents=3, state=state)

        assert result["desired_agent_count"] == 3

    @pytest.mark.asyncio
    async def test_single_task_layer_wants_one_agent(self) -> None:
        """A one-task active layer wants exactly one agent."""
        state = _MockState([_task("only")])

        result = await get_desired_agent_count(max_agents=5, state=state)

        assert result["desired_agent_count"] == 1

    @pytest.mark.asyncio
    async def test_all_done_returns_zero(self) -> None:
        """When all work is DONE, desired count is 0 — retire the pool."""
        state = _MockState([_task("a", status=TaskStatus.DONE)])

        result = await get_desired_agent_count(max_agents=5, state=state)

        assert result["success"] is True
        assert result["desired_agent_count"] == 0

    @pytest.mark.asyncio
    async def test_no_state_returns_error(self) -> None:
        """Missing server state is a graceful error, not a crash."""
        result = await get_desired_agent_count(max_agents=5, state=None)

        assert result["success"] is False
        assert "state" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_no_tasks_returns_zero(self) -> None:
        """An empty board wants zero agents."""
        state = _MockState([])

        result = await get_desired_agent_count(max_agents=5, state=state)

        assert result["success"] is True
        assert result["desired_agent_count"] == 0

    @pytest.mark.asyncio
    async def test_response_includes_unclaimed_task_count(self) -> None:
        """The response carries `unclaimed_tasks` for the runner spawn formula."""
        state = _MockState(
            [
                _task("l0", status=TaskStatus.DONE),
                _task("a", dependencies=["l0"], status=TaskStatus.TODO),
                _task("b", dependencies=["l0"], status=TaskStatus.IN_PROGRESS),
            ]
        )

        result = await get_desired_agent_count(max_agents=10, state=state)

        assert result["success"] is True
        # active layer has 2 tasks (desired) but only 1 is TODO (unclaimed)
        assert result["desired_agent_count"] == 2
        assert result["unclaimed_tasks"] == 1

    @pytest.mark.asyncio
    async def test_refreshes_board_state_before_sizing(self) -> None:
        """The tool refreshes project_tasks from the board before sizing.

        The runner control loop is the only caller and triggers no
        refresh of its own; without this it reads stale state, never
        sees a layer complete, and deadlocks (issue #595 Fix 3).
        """
        refreshed: List[bool] = []

        class _RefreshingState:
            def __init__(self) -> None:
                self.project_tasks = [_task("a")]

            async def refresh_project_state(self) -> None:
                refreshed.append(True)

        result = await get_desired_agent_count(max_agents=5, state=_RefreshingState())

        assert result["success"] is True
        assert refreshed == [True]

    @pytest.mark.asyncio
    async def test_dependency_cycle_is_graceful_error(self) -> None:
        """A cyclic graph returns an error response, not an exception."""
        state = _MockState(
            [
                _task("a", dependencies=["b"]),
                _task("b", dependencies=["a"]),
            ]
        )

        result = await get_desired_agent_count(max_agents=5, state=state)

        assert result["success"] is False
        assert "cycl" in result["error"].lower()
