"""
Unit tests for planning phase observability (GH-357).

Verifies that ``create_project_from_description`` on
``NaturalLanguageProjectCreator`` logs ``planning_start`` and
``planning_end`` agent events so Cato's swim lanes can show how long
the Marcus coordination / setup phase takes relative to agent work.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(task_id: str, name: str) -> Task:
    """Build a minimal Task for use in mocked return values."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name=name,
        description="Do the thing",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=2.0,
        dependencies=[],
    )


def _make_creator() -> Any:
    """Build a ``NaturalLanguageProjectCreator`` with all I/O mocked."""
    from src.integrations.nlp_tools import NaturalLanguageProjectCreator

    mock_kanban = MagicMock()
    mock_kanban.auto_setup_project = AsyncMock()
    mock_kanban.project_id = "proj-test-1"
    mock_ai_engine = MagicMock()

    creator = NaturalLanguageProjectCreator(
        kanban_client=mock_kanban,
        ai_engine=mock_ai_engine,
    )
    creator.active_project_id = "proj-test-1"
    return creator


def _make_about_task() -> Task:
    """Minimal About task returned by ``_create_about_task`` mock."""
    now = datetime.now(timezone.utc)
    return Task(
        id="about-1",
        name="About: TestProject",
        description="Project overview",
        status=TaskStatus.DONE,
        priority=Priority.LOW,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=0.0,
        dependencies=[],
        labels=[],
    )


def _mock_kanban_task(task_id: str = "kanban-1") -> MagicMock:
    """Minimal kanban API response for create_task calls."""
    m = MagicMock()
    m.id = task_id
    return m


# ---------------------------------------------------------------------------
# Shared patch context manager
# ---------------------------------------------------------------------------


def _patch_heavy_deps(creator: Any, domain_tasks: list[Task]) -> Any:
    """
    Return a context manager that stubs out all heavy I/O in
    ``create_project_from_description`` so only planning events are emitted.

    The function uses local imports for several helpers, so we patch them at
    their source modules (which is where Python caches the name after the
    first import).
    """
    from contextlib import ExitStack

    stack = ExitStack()

    # Internal methods
    stack.enter_context(
        patch.object(
            creator,
            "process_natural_language",
            new=AsyncMock(return_value=domain_tasks),
        )
    )
    stack.enter_context(
        patch.object(
            creator,
            "apply_safety_checks",
            new=AsyncMock(return_value=domain_tasks),
        )
    )
    stack.enter_context(
        patch.object(
            creator,
            "create_tasks_on_board",
            new=AsyncMock(return_value=domain_tasks),
        )
    )
    stack.enter_context(
        patch.object(
            creator,
            "_create_about_task",
            return_value=_make_about_task(),
        )
    )
    stack.enter_context(
        patch.object(
            creator,
            "_cleanup_background",
            new=AsyncMock(),
        )
    )

    # About task kanban write
    creator.kanban_client.create_task = AsyncMock(
        return_value=_mock_kanban_task("about-kanban-1")
    )

    # Local imports inside the function — patch at source
    stack.enter_context(
        patch(
            "src.integrations.integration_verification"
            ".enhance_project_with_integration",
            return_value=domain_tasks,
        )
    )
    stack.enter_context(
        patch(
            "src.integrations.documentation_tasks"
            ".enhance_project_with_documentation",
            return_value=domain_tasks,
        )
    )
    # Prevent SQLite writes
    stack.enter_context(
        patch("src.core.persistence.SQLitePersistence", new=MagicMock())
    )
    # Prevent background design phase
    stack.enter_context(patch("asyncio.ensure_future", new=MagicMock()))

    return stack


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestPlanningObservability:
    """``create_project_from_description`` logs planning start/end events."""

    async def test_logs_planning_start_event(self) -> None:
        """A ``planning_start`` event is logged when project creation begins.

        This lets Cato's swim lanes show the coordination / setup phase
        duration that currently appears as dead time before any task bar
        appears on the timeline.
        """
        creator = _make_creator()
        tasks = [_make_task("task-1", "Build Widget")]

        with _patch_heavy_deps(creator, tasks):
            with patch("src.integrations.nlp_tools.log_agent_event") as mock_log:
                await creator.create_project_from_description(
                    "Build a widget", "TestProject"
                )

        event_types = [c.args[0] for c in mock_log.call_args_list]
        assert (
            "planning_start" in event_types
        ), f"expected planning_start in logged events, got: {event_types}"

    async def test_logs_planning_end_event(self) -> None:
        """A ``planning_end`` event is logged when task creation completes.

        The span from ``planning_start`` to ``planning_end`` is the
        coordination overhead visible in Cato swim lanes.
        """
        creator = _make_creator()
        tasks = [_make_task("task-1", "Build Widget")]

        with _patch_heavy_deps(creator, tasks):
            with patch("src.integrations.nlp_tools.log_agent_event") as mock_log:
                await creator.create_project_from_description(
                    "Build a widget", "TestProject"
                )

        event_types = [c.args[0] for c in mock_log.call_args_list]
        assert (
            "planning_end" in event_types
        ), f"expected planning_end in logged events, got: {event_types}"

    async def test_planning_start_logged_before_planning_end(self) -> None:
        """``planning_start`` must be logged before ``planning_end``.

        Order matters: Cato computes duration as end − start.
        """
        creator = _make_creator()
        tasks = [_make_task("task-1", "Build Widget")]
        log_order: list[str] = []

        def _capture(event_type: str, _data: Any) -> None:
            if event_type in ("planning_start", "planning_end"):
                log_order.append(event_type)

        with _patch_heavy_deps(creator, tasks):
            with patch(
                "src.integrations.nlp_tools.log_agent_event",
                side_effect=_capture,
            ):
                await creator.create_project_from_description(
                    "Build a widget", "TestProject"
                )

        assert "planning_start" in log_order, "planning_start not logged"
        assert "planning_end" in log_order, "planning_end not logged"
        assert log_order.index("planning_start") < log_order.index(
            "planning_end"
        ), f"planning_start must precede planning_end, got order: {log_order}"

    async def test_planning_start_event_includes_project_name(self) -> None:
        """``planning_start`` payload contains the project name for Cato filtering."""
        creator = _make_creator()
        tasks = [_make_task("task-1", "Build Widget")]
        captured: list[dict[str, Any]] = []

        def _capture(event_type: str, data: Any) -> None:
            if event_type == "planning_start":
                captured.append(data)

        with _patch_heavy_deps(creator, tasks):
            with patch(
                "src.integrations.nlp_tools.log_agent_event",
                side_effect=_capture,
            ):
                await creator.create_project_from_description(
                    "Build a widget", "TestProject"
                )

        assert len(captured) == 1, "exactly one planning_start event expected"
        assert (
            captured[0].get("project_name") == "TestProject"
        ), f"planning_start payload must include project_name, got: {captured[0]}"

    async def test_planning_end_event_includes_task_count(self) -> None:
        """``planning_end`` payload contains the number of tasks created.

        Cato can use this to display a summary annotation on the planning bar.
        """
        creator = _make_creator()
        tasks = [_make_task(f"task-{i}", f"Task {i}") for i in range(3)]
        # Capture expected count before the call: the list is mutated
        # when the About task is appended to created_tasks.
        expected_min_count = len(tasks)
        captured: list[dict[str, Any]] = []

        def _capture(event_type: str, data: Any) -> None:
            if event_type == "planning_end":
                captured.append(data)

        with _patch_heavy_deps(creator, tasks):
            with patch(
                "src.integrations.nlp_tools.log_agent_event",
                side_effect=_capture,
            ):
                await creator.create_project_from_description(
                    "Build a multi-widget dashboard", "TestProject"
                )

        assert len(captured) == 1, "exactly one planning_end event expected"
        assert (
            "task_count" in captured[0]
        ), f"planning_end payload must include task_count, got: {captured[0]}"
        # planning_end fires right after create_tasks_on_board; task_count
        # reflects work tasks only (About task is added after).
        assert captured[0]["task_count"] >= expected_min_count, (
            f"task_count {captured[0]['task_count']} must be "
            f">= {expected_min_count}"
        )
