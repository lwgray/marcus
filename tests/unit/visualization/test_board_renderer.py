"""
Unit tests for the terminal board renderer.

Tests the Rich-based kanban board visualization that reads from
SQLiteKanban and renders a 4-column board in the terminal.
"""

import asyncio
from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from src.core.models import Priority, Task, TaskStatus
from src.visualization.board_renderer import BoardRenderer

# ============================================================
# Helpers
# ============================================================


def _make_task(
    name: str = "Test Task",
    status: TaskStatus = TaskStatus.TODO,
    priority: Priority = Priority.MEDIUM,
    assigned_to: str | None = None,
    progress: int = 0,
    task_id: str = "abc123",
    labels: list[str] | None = None,
    dependencies: list[str] | None = None,
    is_subtask: bool = False,
    parent_task_id: str | None = None,
    estimated_hours: float = 0.0,
    **kwargs: Any,
) -> Task:
    """Create a Task for testing."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name=name,
        description=kwargs.get("description", ""),
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=estimated_hours,
        actual_hours=0.0,
        dependencies=dependencies or [],
        labels=labels or [],
        is_subtask=is_subtask,
        parent_task_id=parent_task_id,
    )


def _capture_output(renderer: BoardRenderer, tasks: List[Task]) -> str:
    """Render to a string buffer and return output."""
    buf = StringIO()
    console = Console(file=buf, width=120, force_terminal=True)
    renderer.render(tasks, console=console)
    return buf.getvalue()


# ============================================================
# Rendering Tests
# ============================================================


class TestBoardRendererColumns:
    """Test that tasks are grouped into correct columns."""

    def test_empty_board_renders_without_error(self) -> None:
        """Test rendering an empty board produces output."""
        renderer = BoardRenderer()
        output = _capture_output(renderer, [])
        assert "Backlog" in output or "BACKLOG" in output or "backlog" in output

    def test_tasks_grouped_by_status(self) -> None:
        """Test tasks appear in their correct status columns."""
        tasks = [
            _make_task(name="Todo Task", status=TaskStatus.TODO, task_id="t1"),
            _make_task(
                name="Active Task",
                status=TaskStatus.IN_PROGRESS,
                assigned_to="agent-1",
                task_id="t2",
            ),
            _make_task(name="Done Task", status=TaskStatus.DONE, task_id="t3"),
            _make_task(
                name="Blocked Task",
                status=TaskStatus.BLOCKED,
                assigned_to="agent-2",
                task_id="t4",
            ),
        ]
        output = _capture_output(BoardRenderer(), tasks)
        assert "Todo Task" in output
        assert "Active Task" in output
        assert "Done Task" in output
        assert "Blocked Task" in output

    def test_column_counts_shown(self) -> None:
        """Test that column headers show task counts."""
        tasks = [
            _make_task(name="T1", status=TaskStatus.TODO, task_id="t1"),
            _make_task(name="T2", status=TaskStatus.TODO, task_id="t2"),
            _make_task(name="T3", status=TaskStatus.IN_PROGRESS, task_id="t3"),
        ]
        output = _capture_output(BoardRenderer(), tasks)
        # Should show count of 2 for backlog
        assert "2" in output


class TestBoardRendererCards:
    """Test card content rendering."""

    def test_card_shows_task_name(self) -> None:
        """Test that task name appears on the card."""
        tasks = [_make_task(name="Build REST API")]
        output = _capture_output(BoardRenderer(), tasks)
        assert "Build REST API" in output

    def test_card_shows_assignee(self) -> None:
        """Test that assigned agent is shown."""
        tasks = [
            _make_task(
                name="My Task",
                status=TaskStatus.IN_PROGRESS,
                assigned_to="agent-1",
            )
        ]
        output = _capture_output(BoardRenderer(), tasks)
        assert "agent-1" in output

    def test_card_shows_priority(self) -> None:
        """Test that priority indicator is shown for high/urgent."""
        tasks = [_make_task(name="Urgent Thing", priority=Priority.URGENT)]
        output = _capture_output(BoardRenderer(), tasks)
        # Should have some priority indicator
        assert "URGENT" in output or "urgent" in output or "!" in output

    def test_card_shows_estimated_hours(self) -> None:
        """Test that estimated hours appear when set."""
        tasks = [_make_task(name="Big Task", estimated_hours=8.0)]
        output = _capture_output(BoardRenderer(), tasks)
        assert "8" in output

    def test_card_shows_labels(self) -> None:
        """Test that labels are displayed."""
        tasks = [_make_task(name="Labeled", labels=["api", "backend"])]
        output = _capture_output(BoardRenderer(), tasks)
        assert "api" in output
        assert "backend" in output

    def test_card_shows_short_id(self) -> None:
        """Test that a shortened task ID is shown."""
        tasks = [_make_task(name="My Task", task_id="abcdef1234567890")]
        output = _capture_output(BoardRenderer(), tasks)
        # Should show first 8 chars of ID
        assert "abcdef12" in output


class TestBoardRendererSummaryBar:
    """Test the summary bar at the bottom."""

    def test_summary_shows_total_tasks(self) -> None:
        """Test summary bar includes total task count."""
        tasks = [
            _make_task(name="T1", task_id="t1"),
            _make_task(name="T2", task_id="t2"),
            _make_task(name="T3", task_id="t3"),
        ]
        output = _capture_output(BoardRenderer(), tasks)
        assert "3" in output

    def test_summary_shows_completion_percentage(self) -> None:
        """Test summary bar includes completion percentage."""
        tasks = [
            _make_task(name="T1", status=TaskStatus.DONE, task_id="t1"),
            _make_task(name="T2", status=TaskStatus.TODO, task_id="t2"),
        ]
        output = _capture_output(BoardRenderer(), tasks)
        assert "50%" in output

    def test_summary_shows_blocker_count(self) -> None:
        """Test summary bar shows blocker count when > 0."""
        tasks = [
            _make_task(name="T1", status=TaskStatus.BLOCKED, task_id="t1"),
            _make_task(name="T2", status=TaskStatus.TODO, task_id="t2"),
        ]
        output = _capture_output(BoardRenderer(), tasks)
        assert "1" in output and "blocker" in output.lower()

    def test_summary_shows_active_agents(self) -> None:
        """Test summary bar counts active agents."""
        tasks = [
            _make_task(
                name="T1",
                status=TaskStatus.IN_PROGRESS,
                assigned_to="agent-1",
                task_id="t1",
            ),
            _make_task(
                name="T2",
                status=TaskStatus.IN_PROGRESS,
                assigned_to="agent-2",
                task_id="t2",
            ),
            _make_task(
                name="T3",
                status=TaskStatus.IN_PROGRESS,
                assigned_to="agent-1",
                task_id="t3",
            ),
        ]
        output = _capture_output(BoardRenderer(), tasks)
        assert "2" in output and "agent" in output.lower()

    def test_empty_board_summary(self) -> None:
        """Test summary bar handles zero tasks."""
        output = _capture_output(BoardRenderer(), [])
        assert "0" in output


class TestBoardRendererProjectName:
    """Test project name display."""

    def test_custom_project_name(self) -> None:
        """Test that custom project name appears in header."""
        renderer = BoardRenderer(project_name="My Awesome Project")
        output = _capture_output(renderer, [])
        assert "My Awesome Project" in output

    def test_default_project_name(self) -> None:
        """Test default project name when none specified."""
        renderer = BoardRenderer()
        output = _capture_output(renderer, [])
        assert "Board" in output or "board" in output


class TestBoardRendererFromDB:
    """Test the from_db class method that loads from SQLite."""

    @pytest.mark.asyncio
    async def test_from_db_renders_tasks(self, tmp_path: Any) -> None:
        """Test end-to-end: create tasks in SQLite, render board."""
        from src.integrations.providers.sqlite_kanban import SQLiteKanban

        db_path = str(tmp_path / "board_test.db")
        kanban = SQLiteKanban(
            {
                "db_path": db_path,
                "project_name": "Test Project",
                "attachments_dir": str(tmp_path / "att"),
            }
        )
        await kanban.connect()

        await kanban.create_task(
            {"name": "Setup DB", "priority": "high", "estimated_hours": 2.0}
        )
        t2 = await kanban.create_task({"name": "Build API", "priority": "medium"})
        await kanban.assign_task(t2.id, "agent-1")
        await kanban.create_task({"name": "Write docs", "status": "done"})

        tasks = await kanban.get_all_tasks()
        renderer = BoardRenderer(project_name="Test Project")

        buf = StringIO()
        console = Console(file=buf, width=120, force_terminal=True)
        renderer.render(tasks, console=console)
        output = buf.getvalue()

        assert "Setup DB" in output
        assert "Build API" in output
        assert "Write docs" in output
        assert "agent-1" in output

        await kanban.disconnect()
