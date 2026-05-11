"""
Unit tests for src.cost_tracking.cost_aggregator.

Aggregator is read-only: takes a CostStore, returns dicts shaped like the
Cato ``/api/cost/*`` response payloads documented in #409. Tests seed the
store with deterministic events and assert the aggregations are correct.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.cost_tracking.cost_aggregator import CostAggregator
from src.cost_tracking.cost_store import (
    CostStore,
    Experiment,
    ModelPrice,
    TokenEvent,
)


@pytest.fixture
def store(tmp_path: Path) -> CostStore:
    """Tmp store seeded with one default Anthropic price."""
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
    return s


@pytest.fixture
def populated_store(store: CostStore) -> CostStore:
    """Store with one experiment + 3 events covering planner + 2 workers."""
    store.record_experiment(
        Experiment(
            experiment_id="exp_1",
            project_id="proj_1",
            project_name="hangman",
            started_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
            num_agents=2,
            total_tasks=10,
            completed_tasks=4,
        )
    )
    base_kwargs = dict(
        experiment_id="exp_1",
        project_id="proj_1",
        provider="anthropic",
        model="claude-sonnet-4-6",
    )
    # Planner: parse_prd
    store.record_event(
        TokenEvent(
            agent_id="planner",
            agent_role="planner",
            operation="parse_prd",
            input_tokens=1000,
            output_tokens=500,
            **base_kwargs,
        )
    )
    # Worker 1: turn 1
    store.record_event(
        TokenEvent(
            agent_id="agent_unicorn_1",
            agent_role="worker",
            operation="turn",
            task_id="t_1",
            session_id="s_1",
            turn_index=1,
            input_tokens=2000,
            cache_creation_tokens=1000,
            cache_read_tokens=500,
            output_tokens=300,
            **base_kwargs,
        )
    )
    # Worker 2: turn 1
    store.record_event(
        TokenEvent(
            agent_id="agent_unicorn_2",
            agent_role="worker",
            operation="turn",
            task_id="t_2",
            session_id="s_2",
            turn_index=1,
            input_tokens=3000,
            cache_creation_tokens=0,
            cache_read_tokens=2000,
            output_tokens=400,
            **base_kwargs,
        )
    )
    return store


@pytest.fixture
def agg(populated_store: CostStore) -> CostAggregator:
    """Aggregator over the populated store."""
    return CostAggregator(store=populated_store)


class TestExperimentSummary:
    """Top-level summary used by /api/cost/experiments/{id}."""

    def test_returns_metadata(self, agg: CostAggregator) -> None:
        """Summary includes project_id, name, totals from experiments table."""
        s = agg.experiment_summary("exp_1")
        assert s["experiment_id"] == "exp_1"
        assert s["project_id"] == "proj_1"
        assert s["project_name"] == "hangman"
        assert s["total_tasks"] == 10
        assert s["completed_tasks"] == 4

    def test_summary_aggregates_token_totals(self, agg: CostAggregator) -> None:
        """summary.total_tokens sums across all event types."""
        s = agg.experiment_summary("exp_1")
        # 1500 (planner) + 3800 (w1) + 5400 (w2) = 10700
        assert s["summary"]["total_tokens"] == 10700
        assert s["summary"]["total_events"] == 3

    def test_summary_breaks_down_by_role(self, agg: CostAggregator) -> None:
        """by_role groups planner vs worker."""
        s = agg.experiment_summary("exp_1")
        roles = {r["role"]: r for r in s["by_role"]}
        assert roles["planner"]["events"] == 1
        assert roles["worker"]["events"] == 2

    def test_summary_breaks_down_by_agent(self, agg: CostAggregator) -> None:
        """by_agent has one row per distinct agent_id."""
        s = agg.experiment_summary("exp_1")
        agents = {a["agent_id"]: a for a in s["by_agent"]}
        assert set(agents.keys()) == {"planner", "agent_unicorn_1", "agent_unicorn_2"}
        assert agents["agent_unicorn_2"]["turns"] == 1

    def test_summary_breaks_down_by_task(self, agg: CostAggregator) -> None:
        """by_task ignores rows with NULL task_id."""
        s = agg.experiment_summary("exp_1")
        task_ids = {t["task_id"] for t in s["by_task"]}
        assert task_ids == {"t_1", "t_2"}  # planner row excluded

    def test_summary_includes_cache_hit_rate(self, agg: CostAggregator) -> None:
        """cache_hit_rate = cache_read / (input + cache_creation + cache_read)."""
        s = agg.experiment_summary("exp_1")
        # totals: input=6000, cache_creation=1000, cache_read=2500
        # hit_rate = 2500 / 9500 ≈ 0.2632
        assert s["summary"]["cache_hit_rate"] == pytest.approx(2500 / 9500, rel=1e-3)

    def test_summary_returns_none_for_unknown_experiment(
        self, agg: CostAggregator
    ) -> None:
        """Querying a non-existent experiment returns None."""
        assert agg.experiment_summary("nonexistent") is None


class TestSessionTurns:
    """Per-session turn trajectory used by drill-down."""

    def test_returns_turns_in_order(self, populated_store: CostStore) -> None:
        """session_turns sorts ascending by turn_index."""
        # Add a 2nd turn for s_1
        populated_store.record_event(
            TokenEvent(
                experiment_id="exp_1",
                project_id="proj_1",
                agent_id="agent_unicorn_1",
                agent_role="worker",
                operation="turn",
                session_id="s_1",
                turn_index=2,
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=500,
                output_tokens=100,
            )
        )
        agg = CostAggregator(store=populated_store)
        turns = agg.session_turns("s_1")
        assert [t["turn_index"] for t in turns] == [1, 2]
        assert turns[0]["total_tokens"] == 2000 + 1000 + 500 + 300


class TestExperimentList:
    """List view used by /api/cost/experiments."""

    def test_lists_experiments_with_summary(self, populated_store: CostStore) -> None:
        """Each row has totals attached."""
        agg = CostAggregator(store=populated_store)
        rows = agg.list_experiments()
        assert len(rows) == 1
        assert rows[0]["experiment_id"] == "exp_1"
        assert rows[0]["total_tokens"] == 10700

    def test_filter_by_project(self, populated_store: CostStore) -> None:
        """project_id filter narrows the set."""
        populated_store.record_experiment(
            Experiment(
                experiment_id="exp_2",
                project_id="other",
                started_at=datetime(2026, 5, 11, tzinfo=timezone.utc),
            )
        )
        agg = CostAggregator(store=populated_store)
        rows = agg.list_experiments(project_id="proj_1")
        assert {r["experiment_id"] for r in rows} == {"exp_1"}


class TestListProjects:
    """list_projects derives project rollups from token_events.project_id.

    Project axis is Marcus's actual identity (per CLAUDE.md GH-388 +
    spawn_agents.py); experiment_id is an MLflow tracking handle and is
    intentionally not the join key here.
    """

    def test_lists_projects_with_totals(self, agg: CostAggregator) -> None:
        """One row per distinct project_id with token + cost rollups."""
        rows = agg.list_projects()
        assert len(rows) == 1
        assert rows[0]["project_id"] == "proj_1"
        assert rows[0]["events"] == 3
        assert rows[0]["total_tokens"] == 10700

    def test_excludes_unassigned_bucket(self, populated_store: CostStore) -> None:
        """Events tagged 'unassigned' do not appear in the project list."""
        populated_store.record_event(
            TokenEvent(
                experiment_id="unassigned",
                project_id="unassigned",
                agent_id="planner",
                agent_role="planner",
                operation="parse_prd",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=10,
                output_tokens=10,
            )
        )
        agg = CostAggregator(store=populated_store)
        rows = agg.list_projects()
        assert all(r["project_id"] != "unassigned" for r in rows)

    def test_orders_by_cost_desc(self, populated_store: CostStore) -> None:
        """A cheaper project sorts below an expensive one."""
        populated_store.record_event(
            TokenEvent(
                experiment_id="exp_2",
                project_id="proj_cheap",
                agent_id="planner",
                agent_role="planner",
                operation="parse_prd",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=1,
                output_tokens=1,
            )
        )
        rows = CostAggregator(store=populated_store).list_projects()
        assert rows[0]["project_id"] == "proj_1"
        assert rows[1]["project_id"] == "proj_cheap"


class TestUnassignedTotals:
    """unassigned_totals surfaces the 'no PlannerContext' gap."""

    def test_returns_zeros_when_no_unassigned_events(self, agg: CostAggregator) -> None:
        """Clean state: nothing to report."""
        totals = agg.unassigned_totals()
        assert totals["events"] == 0
        assert totals["total_cost_usd"] == 0.0

    def test_sums_unassigned_events(self, populated_store: CostStore) -> None:
        """Once we add an unassigned event, totals reflect it."""
        populated_store.record_event(
            TokenEvent(
                experiment_id="unassigned",
                project_id="unassigned",
                agent_id="planner",
                agent_role="planner",
                operation="parse_prd",
                provider="anthropic",
                model="claude-sonnet-4-6",
                input_tokens=1_000_000,
                output_tokens=0,
            )
        )
        totals = CostAggregator(store=populated_store).unassigned_totals()
        assert totals["events"] == 1
        # 1M input * $3/M = $3
        assert totals["total_cost_usd"] == pytest.approx(3.0, rel=1e-6)


class TestCacheHitRate:
    """Cache hit rate per agent for a given experiment."""

    def test_per_agent_hit_rate(self, agg: CostAggregator) -> None:
        """cache_hit_rate is computed per agent independently."""
        rates = agg.cache_hit_rate_by_agent("exp_1")
        agent_2 = next(r for r in rates if r["agent_id"] == "agent_unicorn_2")
        # agent_2: input=3000, cache_creation=0, cache_read=2000
        # hit_rate = 2000 / 5000 = 0.40
        assert agent_2["cache_hit_rate"] == pytest.approx(0.40, rel=1e-6)
