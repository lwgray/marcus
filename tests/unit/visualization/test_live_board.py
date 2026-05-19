"""
Unit tests for the live kanban board watcher.

Tests LiveBoardWatcher (src/visualization/live_board.py) — the
component that polls a kanban provider and renders a continuously
updating terminal board using Rich's Live display.

All external dependencies (kanban provider, Rich Live) are mocked so
these tests run offline, without a database, in < 100 ms each.
"""

import asyncio
from datetime import datetime, timezone
from io import StringIO
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from rich.console import Console

from src.core.models import Priority, Task, TaskStatus
from src.visualization.live_board import LiveBoardWatcher

# ============================================================
# Helpers
# ============================================================


def _make_task(
    name: str = "Test Task",
    status: TaskStatus = TaskStatus.TODO,
    task_id: str = "abc12345",
    assigned_to: str | None = None,
    project_id: str | None = None,
    project_name: str | None = None,
) -> Task:
    """Create a minimal Task for testing."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name=name,
        description="",
        status=status,
        priority=Priority.MEDIUM,
        assigned_to=assigned_to,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=0.0,
        actual_hours=0.0,
        dependencies=[],
        labels=[],
        is_subtask=False,
        parent_task_id=None,
        project_id=project_id,
        project_name=project_name,
    )


def _make_kanban(tasks: list[Task] | None = None) -> AsyncMock:
    """Build a mock kanban provider that returns the given tasks."""
    mock = AsyncMock()
    mock.connect = AsyncMock(return_value=True)
    mock.disconnect = AsyncMock(return_value=None)
    mock.get_all_tasks = AsyncMock(return_value=tasks or [])
    return mock


# ============================================================
# Constructor Tests
# ============================================================


class TestLiveBoardWatcherInit:
    """Test LiveBoardWatcher construction and defaults."""

    def test_default_interval_is_two_seconds(self) -> None:
        """Test that the default poll interval is 2.0 seconds."""
        watcher = LiveBoardWatcher(_make_kanban())
        assert watcher.interval == 2.0

    def test_custom_interval_is_stored(self) -> None:
        """Test that a custom interval is stored on the instance."""
        watcher = LiveBoardWatcher(_make_kanban(), interval=5.0)
        assert watcher.interval == 5.0

    def test_default_project_name(self) -> None:
        """Test that the default project name is used when none given."""
        watcher = LiveBoardWatcher(_make_kanban())
        assert watcher.project_name == "Marcus Board"

    def test_custom_project_name_stored(self) -> None:
        """Test that a custom project name is stored."""
        watcher = LiveBoardWatcher(_make_kanban(), project_name="My Project")
        assert watcher.project_name == "My Project"

    def test_project_filter_defaults_to_none(self) -> None:
        """Test that the project filter is None by default."""
        watcher = LiveBoardWatcher(_make_kanban())
        assert watcher.project_filter is None


# ============================================================
# _fetch_tasks Tests
# ============================================================


class TestFetchTasks:
    """Test the internal _fetch_tasks helper."""

    @pytest.mark.asyncio
    async def test_returns_all_tasks_when_no_filter(self) -> None:
        """Test that all tasks are returned when project_filter is None."""
        tasks = [_make_task("T1", task_id="t1"), _make_task("T2", task_id="t2")]
        kanban = _make_kanban(tasks)
        watcher = LiveBoardWatcher(kanban)
        result = await watcher._fetch_tasks()
        assert result == tasks

    @pytest.mark.asyncio
    async def test_filters_by_project_id_prefix(self) -> None:
        """Test that tasks are filtered to those matching the project ID prefix."""
        t1 = _make_task("Match", task_id="m1", project_id="proj-abc-123")
        t2 = _make_task("No match", task_id="m2", project_id="other-xyz")
        kanban = _make_kanban([t1, t2])
        watcher = LiveBoardWatcher(kanban, project_filter="proj-abc")
        result = await watcher._fetch_tasks()
        assert result == [t1]

    @pytest.mark.asyncio
    async def test_falls_back_to_name_match_when_no_id_match(self) -> None:
        """Test name-based fallback when project_id filter finds nothing."""
        t1 = _make_task("In project", task_id="i1", project_name="My Project")
        t2 = _make_task("Other project", task_id="i2", project_name="Other")
        kanban = _make_kanban([t1, t2])
        watcher = LiveBoardWatcher(
            kanban, project_filter="nomatch", project_name="My Project"
        )
        result = await watcher._fetch_tasks()
        assert result == [t1]

    @pytest.mark.asyncio
    async def test_returns_all_tasks_when_neither_filter_matches(self) -> None:
        """Test that all tasks are returned when filter finds nothing at all."""
        tasks = [_make_task("T1", task_id="t1")]
        kanban = _make_kanban(tasks)
        watcher = LiveBoardWatcher(
            kanban, project_filter="missing", project_name="Missing Project"
        )
        result = await watcher._fetch_tasks()
        assert result == tasks

    @pytest.mark.asyncio
    async def test_name_filter_is_case_insensitive(self) -> None:
        """Test that the name fallback filter ignores case."""
        t = _make_task("Task", task_id="t1", project_name="MY PROJECT")
        kanban = _make_kanban([t])
        watcher = LiveBoardWatcher(
            kanban, project_filter="nomatch", project_name="my project"
        )
        result = await watcher._fetch_tasks()
        assert result == [t]


# ============================================================
# _build_live_renderable Tests
# ============================================================


class TestBuildLiveRenderable:
    """Test the renderable produced by _build_live_renderable."""

    def _render_to_string(self, watcher: LiveBoardWatcher, tasks: list) -> str:
        """Render the live renderable to a string for assertion."""
        buf = StringIO()
        console = Console(file=buf, width=120, force_terminal=True)
        renderable = watcher._build_live_renderable(tasks)
        console.print(renderable)
        return buf.getvalue()

    def test_board_contains_task_name(self) -> None:
        """Test that task names appear in the live renderable output."""
        watcher = LiveBoardWatcher(_make_kanban())
        tasks = [_make_task("Build the API", task_id="b1")]
        output = self._render_to_string(watcher, tasks)
        assert "Build the API" in output

    def test_footer_contains_updated_label(self) -> None:
        """Test that the live footer includes the 'Updated:' timestamp label."""
        watcher = LiveBoardWatcher(_make_kanban())
        output = self._render_to_string(watcher, [])
        assert "Updated:" in output

    def test_footer_contains_ctrl_c_hint(self) -> None:
        """Test that the footer tells the user how to stop the live view."""
        watcher = LiveBoardWatcher(_make_kanban())
        output = self._render_to_string(watcher, [])
        assert "Ctrl+C" in output

    def test_footer_shows_configured_interval(self) -> None:
        """Test that the footer displays the configured refresh interval."""
        watcher = LiveBoardWatcher(_make_kanban(), interval=5.0)
        output = self._render_to_string(watcher, [])
        assert "5s" in output

    def test_project_name_shown_in_header(self) -> None:
        """Test that the project name appears in the board header."""
        watcher = LiveBoardWatcher(_make_kanban(), project_name="Alpha Project")
        output = self._render_to_string(watcher, [])
        assert "Alpha Project" in output

    def test_multiple_status_columns_present(self) -> None:
        """Test that all four kanban columns appear in the output."""
        watcher = LiveBoardWatcher(_make_kanban())
        output = self._render_to_string(watcher, [])
        for col in ("Backlog", "In Progress", "Blocked", "Done"):
            assert col in output, f"Column '{col}' not found in live renderable"


# ============================================================
# watch() Integration Tests (mocked I/O)
# ============================================================


class TestWatchLifecycle:
    """Test that watch() connects, polls, and disconnects correctly."""

    @pytest.mark.asyncio
    async def test_watch_connects_to_kanban(self) -> None:
        """Test that watch() calls kanban.connect() before polling."""
        kanban = _make_kanban()
        watcher = LiveBoardWatcher(kanban, interval=0.01)

        async def _cancel_after_first_poll(*_: Any) -> None:
            raise asyncio.CancelledError()

        with (
            patch("src.visualization.live_board.Live") as mock_live_cls,
            patch("asyncio.sleep", side_effect=_cancel_after_first_poll),
        ):
            mock_live_obj = MagicMock()
            mock_live_obj.__enter__ = Mock(return_value=mock_live_obj)
            mock_live_obj.__exit__ = Mock(return_value=False)
            mock_live_cls.return_value = mock_live_obj

            await watcher.watch(console=Console(file=StringIO()))

        kanban.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_watch_disconnects_after_cancellation(self) -> None:
        """Test that disconnect() is always called, even when interrupted."""
        kanban = _make_kanban()
        watcher = LiveBoardWatcher(kanban, interval=0.01)

        async def _cancel(*_: Any) -> None:
            raise asyncio.CancelledError()

        with (
            patch("src.visualization.live_board.Live") as mock_live_cls,
            patch("asyncio.sleep", side_effect=_cancel),
        ):
            mock_live_obj = MagicMock()
            mock_live_obj.__enter__ = Mock(return_value=mock_live_obj)
            mock_live_obj.__exit__ = Mock(return_value=False)
            mock_live_cls.return_value = mock_live_obj

            await watcher.watch(console=Console(file=StringIO()))

        kanban.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_watch_polls_tasks_at_least_once(self) -> None:
        """Test that get_all_tasks() is called at least once per watch run."""
        kanban = _make_kanban([_make_task("Poll me", task_id="p1")])
        watcher = LiveBoardWatcher(kanban, interval=0.01)

        call_count = 0

        async def _cancel_after_one(*_: Any) -> None:
            nonlocal call_count
            call_count += 1
            raise asyncio.CancelledError()

        with (
            patch("src.visualization.live_board.Live") as mock_live_cls,
            patch("asyncio.sleep", side_effect=_cancel_after_one),
        ):
            mock_live_obj = MagicMock()
            mock_live_obj.__enter__ = Mock(return_value=mock_live_obj)
            mock_live_obj.__exit__ = Mock(return_value=False)
            mock_live_cls.return_value = mock_live_obj

            await watcher.watch(console=Console(file=StringIO()))

        kanban.get_all_tasks.assert_called()
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_watch_uses_configured_sleep_interval(self) -> None:
        """Test that asyncio.sleep is called with the configured interval."""
        kanban = _make_kanban()
        watcher = LiveBoardWatcher(kanban, interval=3.7)

        sleep_arg = None

        async def _capture_then_cancel(seconds: float) -> None:
            nonlocal sleep_arg
            sleep_arg = seconds
            raise asyncio.CancelledError()

        with (
            patch("src.visualization.live_board.Live") as mock_live_cls,
            patch("asyncio.sleep", side_effect=_capture_then_cancel),
        ):
            mock_live_obj = MagicMock()
            mock_live_obj.__enter__ = Mock(return_value=mock_live_obj)
            mock_live_obj.__exit__ = Mock(return_value=False)
            mock_live_cls.return_value = mock_live_obj

            await watcher.watch(console=Console(file=StringIO()))

        assert sleep_arg == pytest.approx(3.7)


# ============================================================
# _run_is_complete Tests
# ============================================================


class TestRunIsComplete:
    """Test the _run_is_complete static method."""

    def test_returns_false_for_empty_task_list(self) -> None:
        """Empty board is not considered complete (run may not have started)."""
        assert LiveBoardWatcher._run_is_complete([]) is False

    def test_returns_false_when_todo_tasks_remain(self) -> None:
        """Board with TODO tasks is not complete."""
        tasks = [_make_task(status=TaskStatus.TODO)]
        assert LiveBoardWatcher._run_is_complete(tasks) is False

    def test_returns_false_when_in_progress_tasks_remain(self) -> None:
        """Board with IN_PROGRESS tasks is not complete."""
        tasks = [_make_task(status=TaskStatus.IN_PROGRESS)]
        assert LiveBoardWatcher._run_is_complete(tasks) is False

    def test_returns_true_when_all_done(self) -> None:
        """Board where every task is DONE is complete."""
        tasks = [
            _make_task(status=TaskStatus.DONE, task_id="d1"),
            _make_task(status=TaskStatus.DONE, task_id="d2"),
        ]
        assert LiveBoardWatcher._run_is_complete(tasks) is True

    def test_returns_true_when_all_blocked_no_active(self) -> None:
        """Board with only BLOCKED tasks (no TODO/IN_PROGRESS) is complete."""
        tasks = [_make_task(status=TaskStatus.BLOCKED)]
        assert LiveBoardWatcher._run_is_complete(tasks) is True

    def test_returns_true_when_done_and_blocked_mixed(self) -> None:
        """Mix of DONE and BLOCKED with no active tasks is complete."""
        tasks = [
            _make_task(status=TaskStatus.DONE, task_id="d1"),
            _make_task(status=TaskStatus.BLOCKED, task_id="b1"),
        ]
        assert LiveBoardWatcher._run_is_complete(tasks) is True

    def test_returns_false_when_one_in_progress_among_done(self) -> None:
        """A single IN_PROGRESS task keeps the board active."""
        tasks = [
            _make_task(status=TaskStatus.DONE, task_id="d1"),
            _make_task(status=TaskStatus.IN_PROGRESS, task_id="p1"),
        ]
        assert LiveBoardWatcher._run_is_complete(tasks) is False


class TestWatchAutoExit:
    """Test that watch() exits automatically when the run finishes."""

    @pytest.mark.asyncio
    async def test_watch_exits_when_all_tasks_done(self) -> None:
        """watch() stops polling once all tasks reach DONE status."""
        done_task = _make_task(status=TaskStatus.DONE, task_id="d1")
        kanban = _make_kanban([done_task])
        watcher = LiveBoardWatcher(kanban, interval=0.01)

        sleep_call_count = 0

        async def _count_sleeps(seconds: float) -> None:
            nonlocal sleep_call_count
            sleep_call_count += 1

        with (
            patch("src.visualization.live_board.Live") as mock_live_cls,
            patch("asyncio.sleep", side_effect=_count_sleeps),
        ):
            mock_live_obj = MagicMock()
            mock_live_obj.__enter__ = Mock(return_value=mock_live_obj)
            mock_live_obj.__exit__ = Mock(return_value=False)
            mock_live_cls.return_value = mock_live_obj

            await watcher.watch(console=Console(file=StringIO()))

        # sleep should never be reached because _run_is_complete() exits first
        assert sleep_call_count == 0
        kanban.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_watch_does_not_exit_while_tasks_in_progress(self) -> None:
        """watch() keeps polling while tasks are still IN_PROGRESS."""
        active_task = _make_task(status=TaskStatus.IN_PROGRESS, task_id="p1")
        kanban = _make_kanban([active_task])
        watcher = LiveBoardWatcher(kanban, interval=0.01)

        async def _cancel_after_first(*_: Any) -> None:
            raise asyncio.CancelledError()

        with (
            patch("src.visualization.live_board.Live") as mock_live_cls,
            patch("asyncio.sleep", side_effect=_cancel_after_first),
        ):
            mock_live_obj = MagicMock()
            mock_live_obj.__enter__ = Mock(return_value=mock_live_obj)
            mock_live_obj.__exit__ = Mock(return_value=False)
            mock_live_cls.return_value = mock_live_obj

            await watcher.watch(console=Console(file=StringIO()))

        # sleep WAS reached, meaning the loop did not auto-exit
        kanban.get_all_tasks.assert_called()
