"""
Tests for create_project's experiment_id wiring (Simon ``b74d5e1c``).

Before this work, direct-MCP create_project produced cost rows with
``experiment_id="unassigned"`` because no caller invoked the
``start_experiment`` MCP tool — only the ``spawn_agents.py`` paths
(``/marcus`` and Posidonius) did. The ``experiments`` table stayed
empty for the most common entry point, leaving the experiments
dimension of the cost data unusable for direct-MCP users.

These tests lock in the fix:

- Every successful ``create_project`` records exactly one row in the
  ``experiments`` table.
- The recorded ``experiment_id`` matches what cost rows recorded
  during the wrapper's PlannerContext push.
- The recorded row references the real (canonical) ``project_id``,
  not the wrapper's placeholder.
- Failure / missing-registry paths do not crash and do not leave
  half-written experiment rows.

See also: GitHub issue #520 for the follow-up that adds an
``entry_point`` column so direct / ``/marcus`` / Posidonius
experiments can be distinguished at the row level.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure CLAUDE_API_KEY is set so config validation passes."""
    monkeypatch.setenv("CLAUDE_API_KEY", "test-key-for-unit-tests")


@pytest.fixture(autouse=True)
def _clear_create_project_dedup_cache() -> Any:
    """Clear the module-level dedup cache between tests."""
    from src.marcus_mcp.tools import nlp as nlp_module

    nlp_module._recent_create_project_calls.clear()
    yield
    nlp_module._recent_create_project_calls.clear()


def _build_state(cost_store: Any) -> Mock:
    """Construct the minimum-viable ``state`` for the create_project wrapper.

    Returns a Mock pre-wired with the kanban_client, ProjectRegistry,
    project_manager, ai_engine, subtask_manager, and (importantly)
    the real CostStore so the wrapper's
    ``state.cost_store.record_experiment`` / ``rebind_project_id``
    calls hit a real database.
    """
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
    """Real tmp CostStore so we can read back token_events + experiments."""
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


class TestCreateProjectRecordsExperiment:
    """Direct-MCP ``create_project`` must record an experiments row."""

    @pytest.mark.asyncio
    async def test_records_exactly_one_experiment_per_successful_call(
        self, cost_store: Any, recorder: Any
    ) -> None:
        """One successful create_project → exactly one experiments row."""
        from src.marcus_mcp.tools.nlp import create_project

        state = _build_state(cost_store)
        marcus_project_id = "abc-123-def-456"
        canonical_pid = marcus_project_id.replace("-", "")

        mock_creator_result: Dict[str, Any] = {
            "success": True,
            "project_name": "Flight Simulator",
            "tasks_created": 29,
            "task_ids": ["task-1"],
            "board": {
                "project_name": "Flight Simulator",
                "board_name": "Main Board",
            },
        }

        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            mock_creator = MockCreator.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value=mock_creator_result
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
                "SELECT experiment_id, project_id, project_name FROM experiments"
            )
        )
        assert len(rows) == 1, f"expected one experiments row, got {rows}"
        exp_id, pid, name = rows[0]
        # experiment_id is a 32-char hex (uuid4().hex)
        assert len(exp_id) == 32 and all(c in "0123456789abcdef" for c in exp_id)
        assert pid == canonical_pid
        assert name == "Flight Simulator"

    @pytest.mark.asyncio
    async def test_no_experiment_row_on_failure(
        self, cost_store: Any, recorder: Any
    ) -> None:
        """Failed creator → no experiments row written.

        The wrapper's recording is gated on ``result.get("success")``,
        so a failure path leaves the experiments table clean. This
        prevents a flood of orphaned experiment rows when the
        decomposer is misbehaving.
        """
        from src.marcus_mcp.tools.nlp import create_project

        state = _build_state(cost_store)
        mock_creator_result: Dict[str, Any] = {
            "success": False,
            "error": "decomposer blew up",
        }
        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            mock_creator = MockCreator.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value=mock_creator_result
            )
            result = await create_project(
                description="Build something",
                project_name="Will Fail",
                options={"provider": "planka"},
                state=state,
            )

        assert result["success"] is False
        rows = list(cost_store.conn.execute("SELECT * FROM experiments"))
        assert rows == [], f"expected zero experiments rows, got {rows}"

    @pytest.mark.asyncio
    async def test_handles_missing_cost_store_gracefully(self) -> None:
        """If ``state`` has no ``cost_store``, the wrapper still returns success.

        Older tests / minimal deployments may construct a state Mock
        without a cost_store attribute. The wrapper must skip the
        experiment-record / rebind path without crashing.
        """
        from src.integrations.kanban_interface import KanbanProvider
        from src.marcus_mcp.tools.nlp import create_project

        # state without cost_store (spec excludes the attribute)
        state = Mock(
            spec=[
                "log_event",
                "kanban_client",
                "ai_engine",
                "subtask_manager",
                "project_registry",
                "project_manager",
                "_subtasks_migrated",
            ]
        )
        state.log_event = Mock()
        state.kanban_client = Mock()
        state.kanban_client.provider = KanbanProvider.PLANKA
        state.kanban_client.project_id = "1670692878487127607"
        state.kanban_client.board_id = "1670692878621345337"
        state.ai_engine = Mock()
        state.subtask_manager = Mock()
        state.project_registry = Mock()
        state.project_manager = Mock()
        state.project_registry.add_project = AsyncMock(return_value="abc-123")
        state.project_registry.get_active_project = AsyncMock(return_value=None)
        state.project_manager.switch_project = AsyncMock()
        state.project_manager.get_kanban_client = AsyncMock(
            return_value=state.kanban_client
        )
        state._subtasks_migrated = False

        mock_creator_result: Dict[str, Any] = {
            "success": True,
            "project_name": "Tiny Project",
            "tasks_created": 1,
        }
        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            mock_creator = MockCreator.return_value
            mock_creator.create_project_from_description = AsyncMock(
                return_value=mock_creator_result
            )
            result = await create_project(
                description="Tiny",
                project_name="Tiny Project",
                options={"provider": "planka"},
                state=state,
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_experiment_id_matches_token_event_rows(
        self, cost_store: Any, recorder: Any
    ) -> None:
        """Cost rows emitted during the wrapper carry the experiment_id we recorded.

        This is the property that lets the dashboard's experiment view
        actually display anything for direct-MCP projects. If the
        token_events.experiment_id and experiments.experiment_id don't
        match, the dashboard's join returns empty and the fix is
        useless even though the experiments row exists.
        """
        from src.cost_tracking.cost_recorder import get_recorder
        from src.marcus_mcp.tools.nlp import create_project

        state = _build_state(cost_store)

        # Simulate a planner LLM call landing during the wrapper's
        # scope by having the mocked creator's
        # ``create_project_from_description`` emit a cost row before
        # returning. This mirrors how the real decomposer's LLM calls
        # land inside the wrapper.
        async def _creator_emits_cost(*_args: Any, **_kwargs: Any) -> Dict[str, Any]:
            get_recorder().record_planner_call(
                operation="decompose_prd",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=100,
                output_tokens=50,
            )
            return {
                "success": True,
                "project_name": "Flight Sim",
                "tasks_created": 3,
            }

        with patch(
            "src.integrations.nlp_tools.NaturalLanguageProjectCreator"
        ) as MockCreator:
            mock_creator = MockCreator.return_value
            mock_creator.create_project_from_description = AsyncMock(
                side_effect=_creator_emits_cost
            )
            await create_project(
                description="Build a flight simulator",
                project_name="Flight Sim",
                options={"provider": "planka"},
                state=state,
            )

        # Both tables must reference the same experiment_id
        exp_row = cost_store.conn.execute(
            "SELECT experiment_id FROM experiments"
        ).fetchone()
        te_row = cost_store.conn.execute(
            "SELECT DISTINCT experiment_id FROM token_events "
            "WHERE operation = 'decompose_prd'"
        ).fetchone()
        assert exp_row is not None
        assert te_row is not None
        assert exp_row[0] == te_row[0], (
            f"experiment_id mismatch — experiments has {exp_row[0]!r} but "
            f"token_events has {te_row[0]!r}. The dashboard's join "
            f"would return empty."
        )
        # And critically — neither side recorded the legacy 'unassigned'
        # sentinel that the pre-fix wrapper used.
        assert exp_row[0] != "unassigned"
        assert te_row[0] != "unassigned"
