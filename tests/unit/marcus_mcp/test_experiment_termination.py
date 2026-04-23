"""
Unit tests for GH-389: agent auto-termination when experiment completes.

Two sub-systems are tested:

1. LiveExperimentMonitor.was_started flag — distinguishes the startup
   window (monitor exists but has not started yet) from the finished state
   (monitor started and is now done).  Without this flag, request_next_task
   cannot tell the difference and would incorrectly fire EXPERIMENT_COMPLETE
   during the startup window.

2. request_next_task EXPERIMENT_COMPLETE signal — when the monitor has been
   started and then stopped, the no-task path returns a terminal response
   (status="EXPERIMENT_COMPLETE", should_exit=True) instead of the normal
   "DO NOT terminate — keep retrying" instructions.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(*, agent_project_id: str = "project-alpha") -> Mock:
    """Minimal Marcus server state mock sufficient to reach the no-task path."""
    state = Mock()
    state.ensure_lease_monitor_running = AsyncMock()
    state.log_event = Mock()
    state.initialize_kanban = AsyncMock()
    state.refresh_project_state = AsyncMock()
    state.agent_status = {}  # unregistered agent → skip one-task check
    state.project_tasks = []
    state.agent_tasks = {}
    state.gridlock_detector = None  # skip gridlock detection
    # Agent is registered to agent_project_id (used for stale-monitor guard)
    state.agent_project_map = {"agent-1": agent_project_id}
    state.kanban_client = Mock()
    state.tasks_being_assigned = set()
    state.project_state = None
    state.ai_engine = None
    state.provider = "sqlite"  # skip GitHub code_analyzer path
    state.code_analyzer = None
    state.context = None
    state.assignment_lock = asyncio.Lock()
    return state


def _make_monitor(
    *,
    was_started: bool,
    is_running: bool,
    project_id: str = "project-alpha",
) -> Mock:
    """Build a mock LiveExperimentMonitor with explicit lifecycle flags."""
    monitor = Mock()
    monitor.was_started = was_started
    monitor.is_running = is_running
    monitor.project_id = project_id
    return monitor


# ---------------------------------------------------------------------------
# LiveExperimentMonitor.was_started flag
# ---------------------------------------------------------------------------


class TestWasStartedFlag:
    """was_started is False on init, True after start()."""

    def test_was_started_false_on_init(self) -> None:
        """Monitor starts with was_started=False before start() is called."""
        from src.experiments.live_experiment_monitor import LiveExperimentMonitor

        monitor = LiveExperimentMonitor(
            experiment_name="test-exp",
            board_id="board-1",
            project_id="project-1",
        )

        assert monitor.was_started is False
        assert monitor.is_running is False

    @pytest.mark.asyncio
    async def test_was_started_true_after_start(self) -> None:
        """start() flips both was_started and is_running to True."""
        from src.experiments.live_experiment_monitor import LiveExperimentMonitor

        monitor = LiveExperimentMonitor(
            experiment_name="test-exp",
            board_id="board-1",
            project_id="project-1",
        )

        with (
            patch.object(monitor.mlflow_experiment, "start_run"),
            patch("asyncio.create_task"),
        ):
            await monitor.start(run_name="run-001")

        assert monitor.was_started is True
        assert monitor.is_running is True

    @pytest.mark.asyncio
    async def test_was_started_stays_true_after_stop(self) -> None:
        """was_started remains True after the monitor is stopped."""
        from src.experiments.live_experiment_monitor import LiveExperimentMonitor

        monitor = LiveExperimentMonitor(
            experiment_name="test-exp",
            board_id="board-1",
            project_id="project-1",
        )

        with (
            patch.object(monitor.mlflow_experiment, "start_run"),
            patch("asyncio.create_task"),
        ):
            await monitor.start(run_name="run-001")

        # Simulate stop by flipping flags directly (avoids MLflow/task complexity)
        monitor.is_running = False
        monitor.monitor_task = None

        assert monitor.was_started is True
        assert monitor.is_running is False


# ---------------------------------------------------------------------------
# request_next_task EXPERIMENT_COMPLETE signal
# ---------------------------------------------------------------------------


class TestExperimentCompleteSignal:
    """request_next_task returns EXPERIMENT_COMPLETE when experiment has ended."""

    @pytest.mark.asyncio
    async def test_returns_experiment_complete_when_experiment_ended(self) -> None:
        """
        EXPERIMENT_COMPLETE is returned when monitor.was_started=True
        and monitor.is_running=False (experiment has ended).
        """
        from src.marcus_mcp.tools.task import request_next_task

        state = _make_state()
        finished_monitor = _make_monitor(was_started=True, is_running=False)

        with (
            patch(
                "src.marcus_mcp.tools.task.find_optimal_task_for_agent",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.experiments.live_experiment_monitor.get_active_monitor",
                return_value=finished_monitor,
            ),
            patch("src.marcus_mcp.tools.task.conversation_logger"),
            patch("src.marcus_mcp.tools.task.log_agent_event"),
            patch("src.marcus_mcp.tools.task.log_thinking"),
        ):
            result = await request_next_task(agent_id="agent-1", state=state)

        assert result["status"] == "EXPERIMENT_COMPLETE"
        assert result["should_exit"] is True
        assert "exit" in result["message"].lower()
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_returns_retry_when_no_experiment_running(self) -> None:
        """
        Normal "no tasks" retry response is returned when no monitor is active
        (no experiment running — standalone Marcus usage).
        """
        from src.marcus_mcp.tools.task import request_next_task

        state = _make_state()

        with (
            patch(
                "src.marcus_mcp.tools.task.find_optimal_task_for_agent",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.experiments.live_experiment_monitor.get_active_monitor",
                return_value=None,
            ),
            patch("src.marcus_mcp.tools.task.conversation_logger"),
            patch("src.marcus_mcp.tools.task.log_agent_event"),
            patch("src.marcus_mcp.tools.task.log_thinking"),
            patch(
                "src.marcus_mcp.tools.task.calculate_retry_after_seconds",
                new=AsyncMock(
                    return_value={"retry_after_seconds": 30, "reason": "no_tasks"}
                ),
            ),
        ):
            result = await request_next_task(agent_id="agent-1", state=state)

        # Should be a retry response, not EXPERIMENT_COMPLETE
        assert result.get("status") != "EXPERIMENT_COMPLETE"
        assert result.get("should_exit") is not True
        assert "retry_after_seconds" in result

    @pytest.mark.asyncio
    async def test_returns_retry_during_startup_window(self) -> None:
        """
        Normal "no tasks" retry is returned when monitor exists but has not
        been started yet (startup window: create_project done, start_experiment
        not yet called).  was_started=False distinguishes this from "ended".
        """
        from src.marcus_mcp.tools.task import request_next_task

        state = _make_state()
        startup_monitor = _make_monitor(was_started=False, is_running=False)

        with (
            patch(
                "src.marcus_mcp.tools.task.find_optimal_task_for_agent",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.experiments.live_experiment_monitor.get_active_monitor",
                return_value=startup_monitor,
            ),
            patch("src.marcus_mcp.tools.task.conversation_logger"),
            patch("src.marcus_mcp.tools.task.log_agent_event"),
            patch("src.marcus_mcp.tools.task.log_thinking"),
            patch(
                "src.marcus_mcp.tools.task.calculate_retry_after_seconds",
                new=AsyncMock(
                    return_value={"retry_after_seconds": 30, "reason": "no_tasks"}
                ),
            ),
        ):
            result = await request_next_task(agent_id="agent-1", state=state)

        # Must NOT be EXPERIMENT_COMPLETE — experiment hasn't started yet
        assert result.get("status") != "EXPERIMENT_COMPLETE"
        assert result.get("should_exit") is not True

    @pytest.mark.asyncio
    async def test_returns_retry_while_experiment_active(self) -> None:
        """
        Normal "no tasks" retry is returned when the experiment is still
        running (was_started=True, is_running=True) — agent should keep polling.
        """
        from src.marcus_mcp.tools.task import request_next_task

        state = _make_state()
        active_monitor = _make_monitor(was_started=True, is_running=True)

        with (
            patch(
                "src.marcus_mcp.tools.task.find_optimal_task_for_agent",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.experiments.live_experiment_monitor.get_active_monitor",
                return_value=active_monitor,
            ),
            patch("src.marcus_mcp.tools.task.conversation_logger"),
            patch("src.marcus_mcp.tools.task.log_agent_event"),
            patch("src.marcus_mcp.tools.task.log_thinking"),
            patch(
                "src.marcus_mcp.tools.task.calculate_retry_after_seconds",
                new=AsyncMock(
                    return_value={"retry_after_seconds": 30, "reason": "no_tasks"}
                ),
            ),
        ):
            result = await request_next_task(agent_id="agent-1", state=state)

        # Must NOT be EXPERIMENT_COMPLETE — experiment is still active
        assert result.get("status") != "EXPERIMENT_COMPLETE"
        assert result.get("should_exit") is not True
        assert "retry_after_seconds" in result

    @pytest.mark.asyncio
    async def test_experiment_complete_message_instructs_exit(self) -> None:
        """EXPERIMENT_COMPLETE message explicitly tells the agent to exit."""
        from src.marcus_mcp.tools.task import request_next_task

        state = _make_state()
        finished_monitor = _make_monitor(was_started=True, is_running=False)

        with (
            patch(
                "src.marcus_mcp.tools.task.find_optimal_task_for_agent",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.experiments.live_experiment_monitor.get_active_monitor",
                return_value=finished_monitor,
            ),
            patch("src.marcus_mcp.tools.task.conversation_logger"),
            patch("src.marcus_mcp.tools.task.log_agent_event"),
            patch("src.marcus_mcp.tools.task.log_thinking"),
        ):
            result = await request_next_task(agent_id="agent-1", state=state)

        msg = result["message"]
        # Message must NOT contain "STAY ALIVE" or "DO NOT terminate"
        assert "STAY ALIVE" not in msg
        assert "DO NOT terminate" not in msg
        # Message must instruct exit
        assert "exit" in msg.lower() or "Exit" in msg

    @pytest.mark.asyncio
    async def test_stale_monitor_different_project_does_not_fire(self) -> None:
        """
        A stale monitor from a PREVIOUS experiment (different project_id)
        must NOT trigger EXPERIMENT_COMPLETE for agents of a new experiment.

        Root cause of the regression: when an experiment auto-stops via
        _monitor_loop, set_active_monitor(None) is not called.  The stale
        monitor lingers with was_started=True, is_running=False.  When the
        next experiment's workers call request_next_task before
        start_experiment replaces the monitor, they get EXPERIMENT_COMPLETE
        and exit immediately — so no tasks are ever done.

        Fix: gate the check on monitor.project_id == agent's project_id.
        """
        from src.marcus_mcp.tools.task import request_next_task

        # Agent is registered to the NEW project
        state = _make_state(agent_project_id="project-beta-new")
        # Stale monitor from the OLD project
        stale_monitor = _make_monitor(
            was_started=True,
            is_running=False,
            project_id="project-alpha-old",  # different project!
        )

        with (
            patch(
                "src.marcus_mcp.tools.task.find_optimal_task_for_agent",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.experiments.live_experiment_monitor.get_active_monitor",
                return_value=stale_monitor,
            ),
            patch("src.marcus_mcp.tools.task.conversation_logger"),
            patch("src.marcus_mcp.tools.task.log_agent_event"),
            patch("src.marcus_mcp.tools.task.log_thinking"),
            patch(
                "src.marcus_mcp.tools.task.calculate_retry_after_seconds",
                new=AsyncMock(
                    return_value={"retry_after_seconds": 30, "reason": "no_tasks"}
                ),
            ),
        ):
            result = await request_next_task(agent_id="agent-1", state=state)

        # Must NOT fire EXPERIMENT_COMPLETE for a different project's stale monitor
        assert result.get("status") != "EXPERIMENT_COMPLETE"
        assert result.get("should_exit") is not True
        assert "retry_after_seconds" in result

    @pytest.mark.asyncio
    async def test_unregistered_agent_does_not_fire(self) -> None:
        """
        An agent that has NOT yet registered (agent_project_map has no entry)
        must NOT get EXPERIMENT_COMPLETE from a finished monitor.

        Root cause of the bug: the original guard used ``not _agent_project_id``
        which evaluated to True for an empty string, making the empty-project
        case match every monitor.  The fix requires a truthy project_id before
        comparing.
        """
        from src.marcus_mcp.tools.task import request_next_task

        # Agent "agent-99" is NOT in the project map → _agent_project_id = ""
        state = _make_state(agent_project_id="project-alpha")
        finished_monitor = _make_monitor(
            was_started=True,
            is_running=False,
            project_id="project-alpha",
        )

        with (
            patch(
                "src.marcus_mcp.tools.task.find_optimal_task_for_agent",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.experiments.live_experiment_monitor.get_active_monitor",
                return_value=finished_monitor,
            ),
            patch("src.marcus_mcp.tools.task.conversation_logger"),
            patch("src.marcus_mcp.tools.task.log_agent_event"),
            patch("src.marcus_mcp.tools.task.log_thinking"),
            patch(
                "src.marcus_mcp.tools.task.calculate_retry_after_seconds",
                new=AsyncMock(
                    return_value={"retry_after_seconds": 30, "reason": "no_tasks"}
                ),
            ),
        ):
            # Use "agent-99" which is not in state.agent_project_map
            result = await request_next_task(agent_id="agent-99", state=state)

        # Must NOT fire — unregistered agent has no project to match against
        assert result.get("status") != "EXPERIMENT_COMPLETE"
        assert result.get("should_exit") is not True

    @pytest.mark.asyncio
    async def test_same_project_finished_monitor_fires(self) -> None:
        """
        EXPERIMENT_COMPLETE fires correctly when the monitor's project_id
        matches the agent's registered project_id (normal happy path).
        """
        from src.marcus_mcp.tools.task import request_next_task

        state = _make_state(agent_project_id="project-alpha")
        finished_monitor = _make_monitor(
            was_started=True,
            is_running=False,
            project_id="project-alpha",  # same project
        )

        with (
            patch(
                "src.marcus_mcp.tools.task.find_optimal_task_for_agent",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.experiments.live_experiment_monitor.get_active_monitor",
                return_value=finished_monitor,
            ),
            patch("src.marcus_mcp.tools.task.conversation_logger"),
            patch("src.marcus_mcp.tools.task.log_agent_event"),
            patch("src.marcus_mcp.tools.task.log_thinking"),
        ):
            result = await request_next_task(agent_id="agent-1", state=state)

        assert result["status"] == "EXPERIMENT_COMPLETE"
        assert result["should_exit"] is True
