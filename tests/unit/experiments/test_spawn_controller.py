"""
Unit tests for the runner spawn-controller core (issue #595 Fix 3, chunk 3a).

These are the pure decision functions the runner daemon is built on:
- compute_spawn_count: how many ephemeral agents to spawn this cycle.
- StallWatchdog: detect a run whose task counts stop changing.
- experiment_lifecycle_state: map raw status fields to a lifecycle state.

They contain no I/O so they are unit-testable in isolation; the tmux /
HTTP glue that drives them lives in spawn_agents.py.
"""

import pytest

# conftest.py puts dev-tools/experiments/ on sys.path so `runners` imports.
from runners.spawn_controller import (
    StallWatchdog,
    compute_spawn_count,
    experiment_lifecycle_state,
)

pytestmark = pytest.mark.unit


class TestComputeSpawnCount:
    """compute_spawn_count = max(0, min(desired - live, unclaimed))."""

    def test_spawns_to_fill_the_gap(self) -> None:
        """desired 5, live 2, plenty unclaimed -> spawn 3."""
        assert (
            compute_spawn_count(desired_agent_count=5, live_agents=2, unclaimed_tasks=5)
            == 3
        )

    def test_gated_by_unclaimed_tasks(self) -> None:
        """Never spawn more agents than there are claimable tasks."""
        assert (
            compute_spawn_count(desired_agent_count=5, live_agents=0, unclaimed_tasks=1)
            == 1
        )

    def test_clamped_at_zero_when_live_exceeds_desired(self) -> None:
        """At a layer boundary live can transiently exceed desired -> 0."""
        assert (
            compute_spawn_count(desired_agent_count=2, live_agents=3, unclaimed_tasks=5)
            == 0
        )

    def test_zero_when_no_unclaimed_work(self) -> None:
        """A vacancy with no claimable task spawns nothing (no idle agent)."""
        assert (
            compute_spawn_count(desired_agent_count=5, live_agents=2, unclaimed_tasks=0)
            == 0
        )

    def test_zero_when_fully_staffed(self) -> None:
        """live == desired -> spawn nothing."""
        assert (
            compute_spawn_count(desired_agent_count=4, live_agents=4, unclaimed_tasks=4)
            == 0
        )


class TestStallWatchdog:
    """StallWatchdog flags a run whose task counts stop changing."""

    def test_flags_stall_after_n_unchanged_polls(self) -> None:
        """The same tuple for `stall_polls` polls in a row is a stall."""
        wd = StallWatchdog(stall_polls=3)
        assert wd.update(2, 1, 0) is False  # first poll — baseline
        assert wd.update(2, 1, 0) is False  # unchanged x1
        assert wd.update(2, 1, 0) is False  # unchanged x2
        assert wd.update(2, 1, 0) is True  # unchanged x3 -> stalled

    def test_progress_resets_the_counter(self) -> None:
        """Any change to the task-count tuple resets the stall counter."""
        wd = StallWatchdog(stall_polls=2)
        wd.update(1, 2, 0)
        wd.update(1, 2, 0)  # unchanged x1
        assert wd.update(2, 1, 0) is False  # progress — reset
        assert wd.update(2, 1, 0) is False  # unchanged x1 again
        assert wd.update(2, 1, 0) is True  # unchanged x2 -> stalled

    def test_zero_stall_polls_disables_the_watchdog(self) -> None:
        """stall_polls=0 means the watchdog never fires."""
        wd = StallWatchdog(stall_polls=0)
        for _ in range(20):
            assert wd.update(0, 0, 0) is False


class TestExperimentLifecycleState:
    """experiment_lifecycle_state maps status fields to a lifecycle state."""

    def test_waiting_before_start(self) -> None:
        """experiment_started False -> waiting, regardless of is_running."""
        assert (
            experiment_lifecycle_state(
                experiment_started=False, is_running=False, seen_running=False
            )
            == "waiting"
        )

    def test_running_when_started_and_running(self) -> None:
        """started + running -> running."""
        assert (
            experiment_lifecycle_state(
                experiment_started=True, is_running=True, seen_running=False
            )
            == "running"
        )

    def test_startup_gap_is_waiting_not_finished(self) -> None:
        """started + not-running + never-seen-running -> waiting.

        Regression (#595): Marcus sets experiment_started=True before
        the monitor flips is_running=True. A poll in that gap must not
        read as 'finished' — that tore the session down with 0 agents
        spawned.
        """
        assert (
            experiment_lifecycle_state(
                experiment_started=True, is_running=False, seen_running=False
            )
            == "waiting"
        )

    def test_finished_when_was_running_then_stopped(self) -> None:
        """started + not-running, but is_running seen earlier -> finished."""
        assert (
            experiment_lifecycle_state(
                experiment_started=True, is_running=False, seen_running=True
            )
            == "finished"
        )
