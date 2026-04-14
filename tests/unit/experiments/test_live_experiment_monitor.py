"""
Unit tests for LiveExperimentMonitor.get_status.

Covers the v73 fix: get_status must expose ground-truth task counts
from the kanban backend (total_tasks, completed_tasks, etc.) in
addition to the legacy in-monitor running tallies. Consumers
(monitor agent, downstream tooling, future MCP wrappers) rely on
the kanban-truth block to make "is the project done" decisions —
the legacy task_assignments/task_completions counters are running
event tallies that do NOT represent project totals and were the
root of the v73 premature-exit cascade.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.experiments.live_experiment_monitor import LiveExperimentMonitor

pytestmark = pytest.mark.unit


def _make_monitor(kanban_client: Any = None) -> LiveExperimentMonitor:
    """Build a LiveExperimentMonitor with a mock MLflow experiment."""
    monitor = LiveExperimentMonitor.__new__(LiveExperimentMonitor)
    monitor.experiment_name = "test_exp"
    monitor.board_id = "board-1"
    monitor.project_id = "proj-1"
    monitor.tracking_interval = 30
    monitor.kanban_client = kanban_client
    monitor.mlflow_experiment = MagicMock()
    monitor.is_running = True
    monitor.monitor_task = None
    monitor.run_name = "run-1"
    monitor.run_dir = None
    monitor.registered_agents = {}
    monitor.task_assignments = {}
    monitor.task_completions = {}
    monitor.blockers_reported = 0
    monitor.artifacts_created = 0
    monitor.decisions_logged = 0
    monitor.context_requests = 0
    return monitor


class TestGetStatusKanbanTruth:
    """get_status must expose kanban-truth task counts."""

    @pytest.mark.asyncio
    async def test_get_status_includes_kanban_truth_fields(self) -> None:
        """When kanban_client is wired, get_status must include all 5 truth fields."""
        kanban_client = MagicMock()
        kanban_client.get_project_metrics = AsyncMock(
            return_value={
                "total_tasks": 6,
                "completed_tasks": 4,
                "in_progress_tasks": 1,
                "backlog_tasks": 1,
                "blocked_tasks": 0,
            }
        )
        monitor = _make_monitor(kanban_client=kanban_client)

        status = await monitor.get_status()

        # Ground-truth fields — what consumers MUST use for done-checks
        assert status["total_tasks"] == 6
        assert status["completed_tasks"] == 4
        assert status["in_progress_tasks"] == 1
        assert status["backlog_tasks"] == 1
        assert status["blocked_tasks"] == 0

    @pytest.mark.asyncio
    async def test_get_status_preserves_legacy_running_counters(self) -> None:
        """Legacy task_assignments/task_completions must still be present.

        They are misleading as "project totals" but mlflow + summary
        rendering still consume them as running tallies.
        """
        monitor = _make_monitor()
        monitor.task_assignments = {"t1": "agent-1", "t2": "agent-2"}
        monitor.task_completions = {"t1": 100.0}

        status = await monitor.get_status()

        assert status["task_assignments"] == 2
        assert status["task_completions"] == 1
        assert status["is_running"] is True
        assert status["run_name"] == "run-1"

    @pytest.mark.asyncio
    async def test_get_status_omits_kanban_fields_when_no_client(self) -> None:
        """No kanban client → no truth fields, but call still succeeds."""
        monitor = _make_monitor(kanban_client=None)

        status = await monitor.get_status()

        # Legacy fields present
        assert status["is_running"] is True
        assert status["task_assignments"] == 0
        # Truth fields absent
        assert "total_tasks" not in status
        assert "completed_tasks" not in status

    @pytest.mark.asyncio
    async def test_get_status_handles_kanban_failure_gracefully(self) -> None:
        """Kanban fetch failure → log warning, return legacy fields only."""
        kanban_client = MagicMock()
        kanban_client.get_project_metrics = AsyncMock(
            side_effect=RuntimeError("kanban down")
        )
        monitor = _make_monitor(kanban_client=kanban_client)

        status = await monitor.get_status()

        # Must not raise; legacy fields still present
        assert status["is_running"] is True
        # Truth fields absent because fetch failed
        assert "total_tasks" not in status

    @pytest.mark.asyncio
    async def test_get_status_v73_regression_total_tasks_distinct_from_assignments(
        self,
    ) -> None:
        """
        REGRESSION for dashboard-v73.

        v73 had 6 project tasks but only 2 had ever been assigned to
        agents (Build + Integrate; the other 4 were either pre-baked
        DONE, gated on dependencies, or about to be created later).
        The legacy task_assignments counter showed 2; consumers
        misread it as "total tasks = 2" and concluded the project
        was done.

        After the fix, get_status must expose total_tasks=6 from the
        kanban backend so consumers have an unambiguous denominator.
        """
        kanban_client = MagicMock()
        kanban_client.get_project_metrics = AsyncMock(
            return_value={
                "total_tasks": 6,
                "completed_tasks": 2,
                "in_progress_tasks": 0,
                "backlog_tasks": 4,
                "blocked_tasks": 0,
            }
        )
        monitor = _make_monitor(kanban_client=kanban_client)
        # Simulate the v73 state: 2 assignments observed, 2 completions observed
        monitor.task_assignments = {"build-id": "agent-1", "integrate-id": "agent-2"}
        monitor.task_completions = {"build-id": 100.0, "integrate-id": 200.0}

        status = await monitor.get_status()

        # The legacy tallies still report 2/2 — that's NOT a bug, that's
        # what they semantically are. The fix is exposing the kanban
        # truth alongside them.
        assert status["task_assignments"] == 2
        assert status["task_completions"] == 2
        # The truth: 6 total, 2 done, 4 still pending. Consumers
        # making done-checks now have an unambiguous denominator.
        assert status["total_tasks"] == 6
        assert status["completed_tasks"] == 2
        assert status["backlog_tasks"] == 4
        # Therefore: completed_tasks != total_tasks → project NOT done
        assert status["completed_tasks"] != status["total_tasks"]

    @pytest.mark.asyncio
    async def test_get_status_is_awaitable(self) -> None:
        """get_status must be async (was sync before v73 fix)."""
        import inspect

        monitor = _make_monitor()
        assert inspect.iscoroutinefunction(monitor.get_status)


class TestGetExperimentStatusLifecycle:
    """The MCP wrapper distinguishes startup, active, and finished states.

    Codex P1 on PR #349: workers wait on project_info.json which
    the creator writes BEFORE calling start_experiment. There's a
    real window where get_experiment_status returns "no monitor"
    and a worker reading is_running=False would exit. The fix is
    to expose experiment_started so consumers can distinguish
    "not started yet" from "started and ended."
    """

    @pytest.mark.asyncio
    async def test_status_returns_not_started_when_no_monitor(self) -> None:
        """Startup window: monitor is None → experiment_started=False."""
        from src.marcus_mcp.tools import experiments as experiments_module

        # Patch get_active_monitor to return None (startup window)
        original = experiments_module.get_active_monitor
        experiments_module.get_active_monitor = lambda: None  # type: ignore[assignment]
        try:
            status = await experiments_module.get_experiment_status()
        finally:
            experiments_module.get_active_monitor = original  # type: ignore[assignment]

        assert status["experiment_started"] is False
        assert status["is_running"] is False
        # The two-flag combination unambiguously says "not started"
        # (vs "started=True, is_running=False" which means "ended")

    @pytest.mark.asyncio
    async def test_status_returns_started_when_monitor_active(self) -> None:
        """Active state: monitor exists → experiment_started=True."""
        from src.marcus_mcp.tools import experiments as experiments_module

        kanban_client = MagicMock()
        kanban_client.get_project_metrics = AsyncMock(
            return_value={
                "total_tasks": 6,
                "completed_tasks": 2,
                "in_progress_tasks": 2,
                "backlog_tasks": 2,
                "blocked_tasks": 0,
            }
        )
        monitor = _make_monitor(kanban_client=kanban_client)

        original = experiments_module.get_active_monitor
        experiments_module.get_active_monitor = (  # type: ignore[assignment]
            lambda: monitor
        )
        try:
            status = await experiments_module.get_experiment_status()
        finally:
            experiments_module.get_active_monitor = original  # type: ignore[assignment]

        assert status["experiment_started"] is True
        assert status["is_running"] is True
        assert status["total_tasks"] == 6


class TestCompletionFormulaAlignment:
    """The documented completion formula must match _check_completion.

    Codex P2 on PR #349: prior PR docstrings said
    `completed_tasks == total_tasks AND in_progress_tasks == 0`,
    but the runtime check at LiveExperimentMonitor._check_completion
    uses `(completed + blocked) == total AND in_progress == 0`.
    Blocked tasks count toward "done" because the project shouldn't
    stall waiting for them. Consumers following the wrong formula
    would think work is incomplete even after Marcus finishes.
    """

    @pytest.mark.asyncio
    async def test_completion_with_blocked_tasks_matches_runtime(self) -> None:
        """When blocked + completed == total, the project IS done."""
        # Build a state where: total=5, completed=3, blocked=2,
        # in_progress=0. Per the runtime formula, this is "done"
        # because (3+2)==5 and in_progress==0. Consumers using the
        # documented formula must reach the same verdict.
        kanban_client = MagicMock()
        kanban_client.get_project_metrics = AsyncMock(
            return_value={
                "total_tasks": 5,
                "completed_tasks": 3,
                "in_progress_tasks": 0,
                "backlog_tasks": 0,
                "blocked_tasks": 2,
            }
        )
        monitor = _make_monitor(kanban_client=kanban_client)

        status = await monitor.get_status()

        completed = status["completed_tasks"]
        blocked = status["blocked_tasks"]
        total = status["total_tasks"]
        in_progress = status["in_progress_tasks"]

        # The documented formula
        project_done = in_progress == 0 and (completed + blocked) == total
        assert project_done is True, (
            "Documented formula must match runtime: blocked tasks "
            "count toward done. Codex P2 on PR #349."
        )

        # The OLD/wrong formula would say not done
        wrong_formula = completed == total and in_progress == 0
        assert wrong_formula is False, (
            "Sanity check: the OLD formula would (incorrectly) say "
            "not done in this state — that's the bug we're guarding "
            "against."
        )
