"""
Regression test: ``create_tasks_on_board`` snapshots task names for ALL flows.

Codex P2 review on PR #536: the original Phase 3 wiring (Marcus #530)
put the ``record_task_name`` call inside
``NaturalLanguageProjectCreator.create_project_from_description`` only.
The feature-adder flow (``NaturalLanguageFeatureAdder.add_feature_from_description``)
also creates kanban tasks through the same
``NaturalLanguageTaskCreator.create_tasks_on_board`` shared method, but
never executed the snapshot block — so agents working on feature-added
tasks would render as opaque hex IDs in the dashboard's "Tokens by task"
panel.

The fix moves the snapshot into the shared ``create_tasks_on_board``
method in ``nlp_base.py``. This test exercises that method directly with
a mock kanban client and confirms ``record_task_name`` is called once
per created task, with the correct ``(task_id, name)`` pair.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from src.core.models import Priority, Task, TaskStatus
from src.cost_tracking.cost_store import CostStore


@pytest.fixture
def cost_store(tmp_path: Path) -> CostStore:
    """Tmp cost store so we can read back ``task_names`` rows after the call."""
    return CostStore(db_path=tmp_path / "costs.db")


def _make_task(name: str, task_id: str = "") -> Task:
    """Build a minimal Task. ``id`` is empty pre-board, set post-creation."""
    now = datetime.now(timezone.utc)
    return Task(
        id=task_id,
        name=name,
        description=f"description for {name}",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=2.0,
        dependencies=[],
        labels=[],
    )


class TestTaskNameSnapshotInSharedMethod:
    """``create_tasks_on_board`` must snapshot names for every created task."""

    @pytest.mark.asyncio
    async def test_record_task_name_called_for_each_created_task(
        self, cost_store: CostStore
    ) -> None:
        """Every task produced by the kanban client gets its name snapshotted."""
        # Build the shared task creator with a mock kanban client. The
        # mock returns a kanban_task whose ``id`` is the input name's
        # hash — gives us a stable test fixture without touching SQLite.
        from src.integrations.nlp_base import NaturalLanguageTaskCreator

        class _Concrete(NaturalLanguageTaskCreator):
            async def process_natural_language(self, *args: Any, **kwargs: Any) -> Any:
                """Abstract method satisfied with a no-op."""
                return None

        kanban_client = MagicMock()

        async def _create_task_returning_id(task_data: dict) -> Task:
            # Echo back a Task whose id is derived from the name so the
            # test can correlate input task.name → kanban_task.id.
            return _make_task(
                name=task_data["name"],
                task_id=f"kanban_{task_data['name'].replace(' ', '_')}",
            )

        kanban_client.create_task = AsyncMock(side_effect=_create_task_returning_id)

        creator = _Concrete(kanban_client=kanban_client, ai_engine=MagicMock())

        tasks = [
            _make_task("Implement scoring logic"),
            _make_task("Set up build pipeline"),
            _make_task("Write README"),
        ]

        # Patch the cost recorder global so it points at our tmp store.
        # The snapshot block uses get_recorder().store; redirecting the
        # recorder gives the test full control over what gets written.
        with patch("src.cost_tracking.cost_recorder.get_recorder") as mock_get_recorder:
            mock_recorder = MagicMock()
            mock_recorder.store = cost_store
            mock_get_recorder.return_value = mock_recorder

            await creator.create_tasks_on_board(tasks, skip_validation=True)

        # Every task should now have a name entry in task_names.
        rows = dict(
            cost_store.conn.execute(
                "SELECT task_id, name FROM task_names ORDER BY name"
            )
        )
        assert rows == {
            "kanban_Implement_scoring_logic": "Implement scoring logic",
            "kanban_Set_up_build_pipeline": "Set up build pipeline",
            "kanban_Write_README": "Write README",
        }

    @pytest.mark.asyncio
    async def test_snapshot_failure_does_not_break_task_creation(
        self, cost_store: CostStore
    ) -> None:
        """A broken recorder must not block kanban task creation."""
        from src.integrations.nlp_base import NaturalLanguageTaskCreator

        class _Concrete(NaturalLanguageTaskCreator):
            async def process_natural_language(self, *args: Any, **kwargs: Any) -> Any:
                """Abstract method satisfied with a no-op."""
                return None

        kanban_client = MagicMock()

        async def _create_task(task_data: dict) -> Task:
            return _make_task(name=task_data["name"], task_id="some_id")

        kanban_client.create_task = AsyncMock(side_effect=_create_task)
        creator = _Concrete(kanban_client=kanban_client, ai_engine=MagicMock())

        tasks = [_make_task("Task that creates fine")]

        # Recorder raises on access — simulates a broken cost-tracking
        # subsystem. Task creation must still succeed.
        with patch(
            "src.cost_tracking.cost_recorder.get_recorder",
            side_effect=RuntimeError("recorder unavailable"),
        ):
            created = await creator.create_tasks_on_board(tasks, skip_validation=True)

        assert len(created) == 1
        # No task_names rows were written (recorder broken) but the
        # kanban task creation went through cleanly.
        rows = list(cost_store.conn.execute("SELECT COUNT(*) FROM task_names"))
        assert rows[0][0] == 0
