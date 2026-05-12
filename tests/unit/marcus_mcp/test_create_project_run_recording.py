"""
Tests for ``create_project``'s run + path wiring (Simon ``7ed3074d``).

These tests exercise the two-phase attribution + ``path`` discriminator
the wrapper in ``src/marcus_mcp/tools/nlp.py`` is responsible for:

- Every successful ``create_project`` records exactly one row in the
  ``runs`` table.
- ``runs.run_id`` matches the value cost rows recorded during the
  wrapper's PlannerContext push.
- ``runs.path`` reflects the entry point: ``"direct"`` by default,
  ``"marcus"`` / ``"posidonius"`` when supplied in ``options``.
- Failure leaves the runs table clean (no half-written rows).
- Missing ``cost_store`` attribute degrades gracefully.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config validation needs CLAUDE_API_KEY set."""
    monkeypatch.setenv("CLAUDE_API_KEY", "test-key-for-unit-tests")


@pytest.fixture(autouse=True)
def _clear_create_project_dedup_cache() -> Any:
    """Hermetic tests: clear the module-level dedup cache around each test."""
    from src.marcus_mcp.tools import nlp as nlp_module

    nlp_module._recent_create_project_calls.clear()
    yield
    nlp_module._recent_create_project_calls.clear()


def _build_state(cost_store: Any) -> Mock:
    """Mock state pre-wired with a real CostStore so the wrapper writes to disk."""
    from src.integrations.kanban_interface import KanbanProvider

    state = Mock()
    state.log_event = Mock()
    state.kanban_client = Mock()
    state.kanban_client.provider = KanbanProvider.PLANKA
    state.kanban_client.project_id = "1670692878487127607"
    state.kanban_client.board_id = "1670692878621345337"
    state.ai_engine = Mock()
    state.subtask_manager = Mock()
    state.project_registry = Mock()
    state.project_manager = Mock()
    state.cost_store = cost_store
    state.project_registry.add_project = AsyncMock(return_value="abc-123-def-456")
    state.project_registry.get_active_project = AsyncMock(return_value=None)
    state.project_manager.switch_project = AsyncMock()
    state.project_manager.get_kanban_client = AsyncMock(
        return_value=state.kanban_client
    )
    state._subtasks_migrated = False
    return state


@pytest.fixture
def cost_store(tmp_path: Path) -> Any:
    """Real tmp CostStore so we can inspect token_events + runs."""
    from src.cost_tracking.cost_store import CostStore

    return CostStore(db_path=tmp_path / "costs.db")


@pytest.fixture
def recorder(cost_store: Any) -> Any:
    """Enabled cost recorder wired to the tmp store."""
    from src.cost_tracking.cost_recorder import CostRecorder, set_recorder

    rec = CostRecorder(store=cost_store, enabled=True)
    set_recorder(rec)
    yield rec
    set_recorder(None)


def _ok_creator_result() -> Dict[str, Any]:
    """A canned success payload from the underlying creator."""
    return {
        "success": True,
        "project_name": "Flight Simulator",
        "tasks_created": 29,
        "task_ids": ["task-1"],
        "board": {
            "project_name": "Flight Simulator",
            "board_name": "Main Board",
        },
    }


class TestRunRecording:
    """Direct-MCP ``create_project`` records a ``runs`` row on success."""

    @pytest.mark.asyncio
    async def test_one_run_row_per_successful_call(
        self, cost_store: Any, recorder: Any
    ) -> None:
        """Exactly one row in ``runs``; path defaults to 'direct'."""
        from src.marcus_mcp.tools.nlp import create_project

        state = _build_state(cost_store)
        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            MockCreator.return_value.create_project_from_description = AsyncMock(
                return_value=_ok_creator_result()
            )
            result = await create_project(
                description="Build a flight simulator",
                project_name="Flight Simulator",
                options={"provider": "planka"},
                state=state,
            )

        assert result["success"] is True
        rows = list(
            cost_store.conn.execute(
                "SELECT run_id, project_id, project_name, path FROM runs"
            )
        )
        assert len(rows) == 1, f"expected one runs row, got {rows}"
        run_id, pid, name, path = rows[0]
        assert len(run_id) == 32 and all(c in "0123456789abcdef" for c in run_id)
        assert pid == "abc123def456"  # canonical (dashless)
        assert name == "Flight Simulator"
        assert path == "direct", "default path for unmarked options must be 'direct'"

    @pytest.mark.asyncio
    async def test_no_row_on_failure(self, cost_store: Any, recorder: Any) -> None:
        """A failed creator leaves the runs table clean."""
        from src.marcus_mcp.tools.nlp import create_project

        state = _build_state(cost_store)
        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            MockCreator.return_value.create_project_from_description = AsyncMock(
                return_value={"success": False, "error": "decomposer blew up"}
            )
            result = await create_project(
                description="x",
                project_name="Will Fail",
                options={"provider": "planka"},
                state=state,
            )

        assert result["success"] is False
        rows = list(cost_store.conn.execute("SELECT * FROM runs"))
        assert rows == []

    @pytest.mark.asyncio
    async def test_run_id_matches_token_events(
        self, cost_store: Any, recorder: Any
    ) -> None:
        """The runs.run_id matches what cost rows recorded during the wrapper.

        This is the join the dashboard depends on — if the two don't
        match, the experiment view returns empty and the fix is dead.
        """
        from src.cost_tracking.cost_recorder import get_recorder
        from src.marcus_mcp.tools.nlp import create_project

        state = _build_state(cost_store)

        async def _emits_cost(*_args: Any, **_kwargs: Any) -> Dict[str, Any]:
            get_recorder().record_planner_call(
                operation="decompose_prd",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=100,
                output_tokens=50,
            )
            return _ok_creator_result()

        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            MockCreator.return_value.create_project_from_description = AsyncMock(
                side_effect=_emits_cost
            )
            await create_project(
                description="x",
                project_name="Flight Sim",
                options={"provider": "planka"},
                state=state,
            )

        run_row = cost_store.conn.execute("SELECT run_id FROM runs").fetchone()
        te_row = cost_store.conn.execute(
            "SELECT DISTINCT run_id FROM token_events "
            "WHERE operation = 'decompose_prd'"
        ).fetchone()
        assert run_row is not None and te_row is not None
        assert run_row[0] == te_row[0]
        assert run_row[0] != "unassigned"


class TestPathDiscriminator:
    """``options['path']`` flows into ``runs.path``."""

    @pytest.mark.asyncio
    async def test_default_path_is_direct(self, cost_store: Any, recorder: Any) -> None:
        """When options lack a 'path' key, the wrapper stamps 'direct'."""
        from src.marcus_mcp.tools.nlp import create_project

        state = _build_state(cost_store)
        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            MockCreator.return_value.create_project_from_description = AsyncMock(
                return_value=_ok_creator_result()
            )
            await create_project(
                description="x",
                project_name="P",
                # No 'path' in options — must default to 'direct'.
                options={"provider": "planka"},
                state=state,
            )
        path = cost_store.conn.execute("SELECT path FROM runs").fetchone()[0]
        assert path == "direct"

    @pytest.mark.asyncio
    async def test_explicit_marcus_path_flows_through(
        self, cost_store: Any, recorder: Any
    ) -> None:
        """spawn_agents.py's path='marcus' lands in the runs row."""
        from src.marcus_mcp.tools.nlp import create_project

        state = _build_state(cost_store)
        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            MockCreator.return_value.create_project_from_description = AsyncMock(
                return_value=_ok_creator_result()
            )
            await create_project(
                description="x",
                project_name="P",
                options={"provider": "planka", "path": "marcus"},
                state=state,
            )
        path = cost_store.conn.execute("SELECT path FROM runs").fetchone()[0]
        assert path == "marcus"

    @pytest.mark.asyncio
    async def test_explicit_posidonius_path_flows_through(
        self, cost_store: Any, recorder: Any
    ) -> None:
        """Posidonius's path='posidonius' lands in the runs row."""
        from src.marcus_mcp.tools.nlp import create_project

        state = _build_state(cost_store)
        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            MockCreator.return_value.create_project_from_description = AsyncMock(
                return_value=_ok_creator_result()
            )
            await create_project(
                description="x",
                project_name="P",
                options={"provider": "planka", "path": "posidonius"},
                state=state,
            )
        path = cost_store.conn.execute("SELECT path FROM runs").fetchone()[0]
        assert path == "posidonius"
