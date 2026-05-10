"""
Unit tests for the ``get_cost_summary`` MCP tool.

Validates the tool's argument handling, dispatch to ``CostAggregator``,
and the shape of the returned payload. Uses a fake state object that
exposes the real :class:`CostStore` from ``src.cost_tracking`` populated
with deterministic test data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.cost_tracking.cost_store import (
    CostStore,
    Experiment,
    ModelPrice,
    TokenEvent,
)
from src.marcus_mcp.tools.cost_tracking import (
    COST_SUMMARY_TOOL,
    get_cost_summary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def populated_store(tmp_path: Path) -> CostStore:
    """Store with one experiment + a planner event + a worker turn."""
    s = CostStore(db_path=tmp_path / "costs.db")
    s.record_price(
        ModelPrice(
            model="claude-sonnet-4-6",
            provider="anthropic",
            effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
            input_per_million=3.0,
            cache_creation_per_million=3.75,
            cache_read_per_million=0.30,
            output_per_million=15.0,
            source="default",
        )
    )
    s.record_experiment(
        Experiment(
            experiment_id="exp_1",
            project_id="proj_1",
            project_name="hangman",
            started_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
            num_agents=1,
            total_tasks=4,
            completed_tasks=2,
        )
    )
    base = dict(
        experiment_id="exp_1",
        project_id="proj_1",
        provider="anthropic",
        model="claude-sonnet-4-6",
    )
    s.record_event(
        TokenEvent(
            agent_id="planner",
            agent_role="planner",
            operation="parse_prd",
            input_tokens=1000,
            output_tokens=500,
            **base,
        )
    )
    s.record_event(
        TokenEvent(
            agent_id="agent_1",
            agent_role="worker",
            operation="turn",
            task_id="t_1",
            session_id="s_1",
            turn_index=1,
            input_tokens=2000,
            cache_read_tokens=500,
            output_tokens=100,
            **base,
        )
    )
    return s


@pytest.fixture
def state(populated_store: CostStore) -> Any:
    """Minimal state stub exposing ``cost_store`` like MarcusServer does."""

    class _State:
        pass

    s = _State()
    s.cost_store = populated_store
    return s


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------


class TestToolDefinition:
    """Static checks on the MCP Tool descriptor."""

    def test_tool_name(self) -> None:
        """Tool registers under the documented name."""
        assert COST_SUMMARY_TOOL.name == "get_cost_summary"

    def test_tool_accepts_either_id(self) -> None:
        """Schema exposes both experiment_id and project_id parameters."""
        props = COST_SUMMARY_TOOL.inputSchema["properties"]
        assert "experiment_id" in props
        assert "project_id" in props


# ---------------------------------------------------------------------------
# get_cost_summary by experiment_id
# ---------------------------------------------------------------------------


class TestGetCostSummaryByExperiment:
    """Happy path: pass ``experiment_id``."""

    @pytest.mark.asyncio
    async def test_returns_full_breakdown(self, state: Any) -> None:
        """Response carries summary + by_role + by_agent + by_task etc."""
        result = await get_cost_summary(experiment_id="exp_1", state=state)
        assert result["experiment_id"] == "exp_1"
        assert result["project_id"] == "proj_1"
        assert "summary" in result
        assert {"by_role", "by_agent", "by_task", "by_operation", "by_model"} <= set(
            result.keys()
        )

    @pytest.mark.asyncio
    async def test_summary_totals_are_correct(self, state: Any) -> None:
        """summary.total_tokens sums across both events."""
        result = await get_cost_summary(experiment_id="exp_1", state=state)
        # planner: 1000 + 500 = 1500. worker: 2000 + 500 + 100 = 2600. total: 4100.
        assert result["summary"]["total_tokens"] == 4100

    @pytest.mark.asyncio
    async def test_unknown_experiment_returns_error(self, state: Any) -> None:
        """A missing experiment_id surfaces a friendly error."""
        result = await get_cost_summary(experiment_id="nope", state=state)
        assert result.get("success") is False
        assert "not found" in result.get("error", "").lower()


# ---------------------------------------------------------------------------
# get_cost_summary by project_id
# ---------------------------------------------------------------------------


class TestGetCostSummaryByProject:
    """Happy path: pass ``project_id``."""

    @pytest.mark.asyncio
    async def test_returns_project_totals_and_experiments(self, state: Any) -> None:
        """Response carries totals + per-experiment list."""
        result = await get_cost_summary(project_id="proj_1", state=state)
        assert result["project_id"] == "proj_1"
        assert result["totals"]["events"] == 2
        assert result["totals"]["total_tokens"] == 4100
        assert len(result["experiments"]) == 1
        assert result["experiments"][0]["experiment_id"] == "exp_1"


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


class TestArgumentValidation:
    """Caller errors are returned, never raised."""

    @pytest.mark.asyncio
    async def test_missing_both_ids_returns_error(self, state: Any) -> None:
        """At least one of experiment_id / project_id is required."""
        result = await get_cost_summary(state=state)
        assert result.get("success") is False
        assert "experiment_id" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_missing_cost_store_returns_error(self) -> None:
        """If state has no cost_store, surface a clear error."""
        result = await get_cost_summary(experiment_id="exp_1", state=object())
        assert result.get("success") is False
        assert "cost store" in result.get("error", "").lower()
