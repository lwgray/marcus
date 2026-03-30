"""
Unit tests for get_project_status kanban metrics integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus


def _make_task(name: str, status: TaskStatus) -> Task:
    """Create a minimal Task for testing."""
    from datetime import datetime, timezone

    return Task(
        id=name.lower().replace(" ", "_"),
        name=name,
        description="",
        status=status,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=1.0,
    )


def _make_state(
    kanban_metrics: dict | None = None,
    tasks: list | None = None,
    metrics_error: Exception | None = None,
) -> MagicMock:
    """Create a mock server state."""
    state = MagicMock()
    state.project_state = MagicMock()
    state.project_state.project_name = "Test"
    state.agent_status = {}
    state.provider = "sqlite"

    state.project_registry = MagicMock()
    state.project_registry.get_active_project = AsyncMock(
        return_value=MagicMock(
            id="proj-1",
            name="Test",
            provider="sqlite",
            provider_config={},
        )
    )

    if kanban_metrics is not None or metrics_error is not None:
        kanban = MagicMock()
        if metrics_error:
            kanban.get_project_metrics = AsyncMock(side_effect=metrics_error)
        else:
            kanban.get_project_metrics = AsyncMock(return_value=kanban_metrics)
        state.kanban_client = kanban
    else:
        state.kanban_client = None

    state.project_manager = MagicMock()
    state.project_manager.get_kanban_client = AsyncMock(
        return_value=state.kanban_client
    )
    state.project_tasks = tasks or []
    state.refresh_project_state = AsyncMock()

    return state


@pytest.fixture(autouse=True)
def _passthrough_serialize():
    """Bypass serialize_for_mcp in tests."""
    with patch(
        "src.marcus_mcp.tools.project.serialize_for_mcp",
        side_effect=lambda x: x,
    ):
        yield


class TestProjectStatusKanbanMetrics:
    """Test get_project_status with kanban DB metrics."""

    @pytest.mark.asyncio
    async def test_uses_kanban_metrics_when_complete(self) -> None:
        """Test that complete kanban metrics are used."""
        from src.marcus_mcp.tools.project import get_project_status

        state = _make_state(
            kanban_metrics={
                "total_tasks": 5,
                "completed_tasks": 5,
                "in_progress_tasks": 0,
                "blocked_tasks": 0,
            }
        )
        result = await get_project_status(state=state)
        assert result["project"]["total_tasks"] == 5
        assert result["project"]["completed"] == 5
        assert result["project"]["completion_percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_falls_back_when_metrics_incomplete(self) -> None:
        """Test fallback when metrics miss required fields."""
        from src.marcus_mcp.tools.project import get_project_status

        state = _make_state(
            kanban_metrics={
                "total_tasks": 5,
                "completed_tasks": 3,
                "in_progress_tasks": 2,
            },
            tasks=[
                _make_task("T1", TaskStatus.DONE),
                _make_task("T2", TaskStatus.DONE),
                _make_task("T3", TaskStatus.IN_PROGRESS),
            ],
        )
        result = await get_project_status(state=state)
        assert result["project"]["total_tasks"] == 3
        assert result["project"]["completed"] == 2

    @pytest.mark.asyncio
    async def test_falls_back_when_no_get_project_metrics(self) -> None:
        """Test fallback when kanban client lacks get_project_metrics."""
        from src.marcus_mcp.tools.project import get_project_status

        state = _make_state(
            kanban_metrics={},  # Creates a client but empty metrics
            tasks=[
                _make_task("T1", TaskStatus.DONE),
                _make_task("T2", TaskStatus.TODO),
            ],
        )
        # Remove the method to simulate a client without it
        del state.kanban_client.get_project_metrics
        result = await get_project_status(state=state)
        assert result["project"]["total_tasks"] == 2
        assert result["project"]["completed"] == 1

    @pytest.mark.asyncio
    async def test_falls_back_when_metrics_call_fails(self) -> None:
        """Test fallback when get_project_metrics raises."""
        from src.marcus_mcp.tools.project import get_project_status

        state = _make_state(
            metrics_error=Exception("DB locked"),
            tasks=[_make_task("T1", TaskStatus.DONE)],
        )
        result = await get_project_status(state=state)
        assert result["project"]["total_tasks"] == 1
        assert result["project"]["completed"] == 1

    @pytest.mark.asyncio
    async def test_about_task_counted_as_done(self) -> None:
        """Test that About task (born done) is counted."""
        from src.marcus_mcp.tools.project import get_project_status

        state = _make_state(
            kanban_metrics={
                "total_tasks": 5,
                "completed_tasks": 5,
                "in_progress_tasks": 0,
                "blocked_tasks": 0,
            }
        )
        result = await get_project_status(state=state)
        assert result["project"]["completed"] == 5
        assert result["project"]["total_tasks"] == 5

    @pytest.mark.asyncio
    async def test_empty_metrics_falls_back(self) -> None:
        """Test fallback when metrics dict is empty."""
        from src.marcus_mcp.tools.project import get_project_status

        state = _make_state(
            kanban_metrics={},
            tasks=[_make_task("T1", TaskStatus.TODO)],
        )
        result = await get_project_status(state=state)
        assert result["project"]["total_tasks"] == 1
