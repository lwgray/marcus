"""
Unit tests for the kanban board simulator.

BoardSimulator (``src/visualization/board_simulator.py``) seeds a fake
project and drives fake agents that move tasks across a SQLite-backed
kanban board. These tests run against a real on-disk SQLite database
created under pytest's ``tmp_path``, with the virtual clock set very
fast so each test finishes quickly.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.core.models import TaskStatus
from src.integrations.providers.sqlite_kanban import SQLiteKanban
from src.visualization.board_simulator import DEMO_TASK_SPECS, BoardSimulator

pytestmark = pytest.mark.unit


# ============================================================
# Fixtures / helpers
# ============================================================


@pytest.fixture
def kanban(tmp_path: Path) -> SQLiteKanban:
    """Provide an unconnected SQLiteKanban on a temp database."""
    return SQLiteKanban({"db_path": str(tmp_path / "demo.db"), "project_name": "Test"})


def _sim(kanban: SQLiteKanban, **kwargs: Any) -> BoardSimulator:
    """Build a BoardSimulator tuned for fast, deterministic tests."""
    kwargs.setdefault("speed", 10_000.0)
    kwargs.setdefault("blocker_rate", 0.0)
    kwargs.setdefault("seed", 42)
    sim = BoardSimulator(kanban, **kwargs)
    # Shrink the simulated waits so the test suite stays fast.
    sim._POLL_SECONDS = 0.01
    sim._MIN_STEP_SECONDS = 0.001
    return sim


# ============================================================
# Seeding
# ============================================================


class TestSeed:
    """Tests for BoardSimulator.seed."""

    async def test_seed_creates_all_tasks_in_backlog(
        self, kanban: SQLiteKanban
    ) -> None:
        """Every spec becomes a TODO task on the board."""
        sim = _sim(kanban)

        created = await sim.seed()

        assert len(created) == len(DEMO_TASK_SPECS)
        tasks = await kanban.get_all_tasks()
        assert len(tasks) == len(DEMO_TASK_SPECS)
        assert all(t.status == TaskStatus.TODO for t in tasks)

    async def test_seed_scopes_provider_to_new_project(
        self, kanban: SQLiteKanban
    ) -> None:
        """Seeding assigns the provider a project id to scope reads."""
        sim = _sim(kanban)

        await sim.seed()

        assert kanban.project_id is not None

    async def test_seed_translates_dependency_keys_to_ids(
        self, kanban: SQLiteKanban
    ) -> None:
        """depends_on keys are rewritten to real generated task ids."""
        sim = _sim(kanban)

        await sim.seed()

        by_name = {t.name: t for t in await kanban.get_all_tasks()}
        deploy = by_name["Deploy to staging"]
        all_ids = {t.id for t in by_name.values()}
        # The deploy spec depends on four other specs.
        assert len(deploy.dependencies) == 4
        assert all(dep in all_ids for dep in deploy.dependencies)

    async def test_seed_rejects_unsorted_specs(self, kanban: SQLiteKanban) -> None:
        """A forward dependency reference raises ValueError."""
        bad_specs: List[Dict[str, Any]] = [
            {"key": "b", "name": "B", "depends_on": ["a"]},
            {"key": "a", "name": "A", "depends_on": []},
        ]
        sim = BoardSimulator(kanban, task_specs=bad_specs)

        with pytest.raises(ValueError, match="topologically sorted"):
            await sim.seed()

    async def test_seed_rejects_duplicate_keys(self, kanban: SQLiteKanban) -> None:
        """Two specs sharing a key raise ValueError."""
        bad_specs: List[Dict[str, Any]] = [
            {"key": "a", "name": "A", "depends_on": []},
            {"key": "a", "name": "A again", "depends_on": []},
        ]
        sim = BoardSimulator(kanban, task_specs=bad_specs)

        with pytest.raises(ValueError, match="Duplicate"):
            await sim.seed()


# ============================================================
# Running
# ============================================================


class TestRun:
    """Tests for BoardSimulator.run."""

    async def test_run_completes_all_tasks(self, kanban: SQLiteKanban) -> None:
        """Every task reaches DONE; none are left active."""
        sim = _sim(kanban)

        metrics = await sim.run()

        assert metrics["total_tasks"] == len(DEMO_TASK_SPECS)
        assert metrics["completed_tasks"] == len(DEMO_TASK_SPECS)
        assert metrics["in_progress_tasks"] == 0
        assert metrics["backlog_tasks"] == 0
        assert metrics["blocked_tasks"] == 0

    async def test_run_completes_even_when_every_task_blocks(
        self, kanban: SQLiteKanban
    ) -> None:
        """With blocker_rate=1.0 the recovery path still finishes."""
        sim = _sim(kanban, blocker_rate=1.0)

        metrics = await sim.run()

        assert metrics["completed_tasks"] == metrics["total_tasks"]

    async def test_run_with_single_agent(self, kanban: SQLiteKanban) -> None:
        """A one-agent run still completes the whole graph."""
        sim = _sim(kanban, agents=1)

        metrics = await sim.run()

        assert metrics["completed_tasks"] == len(DEMO_TASK_SPECS)

    async def test_run_with_many_agents(self, kanban: SQLiteKanban) -> None:
        """More agents than tasks does not break completion."""
        sim = _sim(kanban, agents=20)

        metrics = await sim.run()

        assert metrics["completed_tasks"] == len(DEMO_TASK_SPECS)

    async def test_run_seeds_implicitly(self, kanban: SQLiteKanban) -> None:
        """Calling run without a prior seed still seeds the board."""
        sim = _sim(kanban)

        metrics = await sim.run()

        assert metrics["total_tasks"] == len(DEMO_TASK_SPECS)

    async def test_run_with_custom_task_specs(self, kanban: SQLiteKanban) -> None:
        """A caller-supplied task graph runs to completion."""
        specs: List[Dict[str, Any]] = [
            {"key": "a", "name": "Task A", "estimated_hours": 1.0, "depends_on": []},
            {"key": "b", "name": "Task B", "estimated_hours": 1.0, "depends_on": ["a"]},
        ]
        sim = _sim(kanban, task_specs=specs)

        metrics = await sim.run()

        assert metrics["total_tasks"] == 2
        assert metrics["completed_tasks"] == 2


# ============================================================
# Dependency gating
# ============================================================


class TestEligibility:
    """Tests for BoardSimulator._eligible dependency gating."""

    async def test_only_root_tasks_eligible_initially(
        self, kanban: SQLiteKanban
    ) -> None:
        """Only dependency-free tasks are claimable at the start."""
        sim = _sim(kanban)
        await sim.seed()

        eligible = sim._eligible(await kanban.get_all_tasks())

        names = {t.name for t in eligible}
        assert names == {"Design database schema", "Scaffold frontend app"}

    async def test_dependency_unlocks_after_prerequisite_done(
        self, kanban: SQLiteKanban
    ) -> None:
        """A gated task becomes eligible once its dependency is DONE."""
        sim = _sim(kanban)
        await sim.seed()

        schema = next(
            t
            for t in await kanban.get_all_tasks()
            if t.name == "Design database schema"
        )
        await kanban.move_task_to_column(schema.id, "done")

        eligible = sim._eligible(await kanban.get_all_tasks())

        names = {t.name for t in eligible}
        assert "Write database migrations" in names

    async def test_claimed_tasks_are_not_re_offered(self, kanban: SQLiteKanban) -> None:
        """A task an agent has reserved is excluded from _eligible."""
        sim = _sim(kanban)
        await sim.seed()

        tasks = await kanban.get_all_tasks()
        first = sim._eligible(tasks)[0]
        sim._claimed.add(first.id)

        still_eligible = {t.id for t in sim._eligible(tasks)}
        assert first.id not in still_eligible


# ============================================================
# Constructor argument handling
# ============================================================


class TestConstructor:
    """Tests for BoardSimulator argument normalization."""

    def test_agents_clamped_to_minimum_one(self, kanban: SQLiteKanban) -> None:
        """A non-positive agent count is clamped up to 1."""
        assert BoardSimulator(kanban, agents=0).agents == 1
        assert BoardSimulator(kanban, agents=-5).agents == 1

    def test_blocker_rate_clamped_to_unit_interval(self, kanban: SQLiteKanban) -> None:
        """blocker_rate is clamped into the range [0, 1]."""
        assert BoardSimulator(kanban, blocker_rate=5.0).blocker_rate == 1.0
        assert BoardSimulator(kanban, blocker_rate=-1.0).blocker_rate == 0.0

    def test_non_positive_speed_falls_back_to_one(self, kanban: SQLiteKanban) -> None:
        """A zero or negative speed defaults to 1.0."""
        assert BoardSimulator(kanban, speed=0.0).speed == 1.0
        assert BoardSimulator(kanban, speed=-3.0).speed == 1.0


# ============================================================
# Robustness — empty board + provider failures
# ============================================================


class TestRobustness:
    """Tests for the deadlock-avoidance paths in _agent_loop."""

    async def test_run_with_empty_task_specs_exits_cleanly(
        self, kanban: SQLiteKanban
    ) -> None:
        """An empty task graph returns immediately rather than hanging.

        Regression test for the case where ``run()`` is called with no
        task specs: ``_agent_loop`` previously gated its exit on
        ``tasks and self._all_done(tasks)``, so an empty board polled
        forever.
        """
        sim = _sim(kanban, task_specs=[])

        metrics = await asyncio.wait_for(sim.run(), timeout=2.0)

        assert metrics["total_tasks"] == 0
        assert metrics["completed_tasks"] == 0

    async def test_failed_provider_write_releases_claim(
        self, kanban: SQLiteKanban
    ) -> None:
        """A failed assign_task releases the claim so a retry can occur.

        Without the release, the task would stay TODO but permanently
        in ``_claimed``, deadlocking the run.
        """
        sim = _sim(kanban)
        await sim.seed()
        tasks = await kanban.get_all_tasks()
        target = sim._eligible(tasks)[0]

        original = kanban.assign_task
        calls = {"n": 0}

        async def flaky_assign(task_id: str, assignee_id: str) -> bool:
            calls["n"] += 1
            if task_id == target.id and calls["n"] == 1:
                return False  # Simulate a transient provider failure.
            return await original(task_id, assignee_id)

        kanban.assign_task = flaky_assign  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="assign_task"):
            await sim._agent_loop("sim-agent-1")

        # The claim must have been released on failure.
        assert target.id not in sim._claimed
