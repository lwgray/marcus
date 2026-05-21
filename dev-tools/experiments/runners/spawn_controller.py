"""
Pure decision logic for the runner spawn-controller (issue #595 Fix 3).

The runner is a long-lived, spawn-only controller: it polls Marcus for
the layered-spawning signal and spawns ephemeral agents to match. The
functions here are the controller's *decisions*, with no I/O — the tmux
and HTTP glue that calls them lives in ``spawn_agents.py``. Keeping the
decisions pure makes them unit-testable in isolation.
"""

from __future__ import annotations

from typing import Optional, Tuple


def compute_spawn_count(
    desired_agent_count: int,
    live_agents: int,
    unclaimed_tasks: int,
) -> int:
    """
    Decide how many ephemeral agents to spawn this control cycle.

    The formula is ``max(0, min(desired_agent_count - live_agents,
    unclaimed_tasks))``:

    - ``desired_agent_count - live_agents`` is the staffing gap.
    - The ``unclaimed_tasks`` cap prevents spawning an agent for which no
      claimable task exists — such an agent would receive "no task" and
      idle, the cost Fix 3 removes.
    - The ``max(0, ...)`` clamp handles a layer boundary: ``desired``
      drops as the graph narrows while a just-finished agent is still
      being reaped, so the gap can be momentarily negative.

    Parameters
    ----------
    desired_agent_count : int
        Active-layer width capped at ``max_agents`` (from Marcus's
        ``get_desired_agent_count``).
    live_agents : int
        Agents the runner currently has alive.
    unclaimed_tasks : int
        TODO tasks in the active layer (from ``get_desired_agent_count``).

    Returns
    -------
    int
        Number of ephemeral agents to spawn now; never negative.
    """
    gap = desired_agent_count - live_agents
    return max(0, min(gap, unclaimed_tasks))


def experiment_lifecycle_state(experiment_started: bool, is_running: bool) -> str:
    """
    Map Marcus's experiment-status fields to a lifecycle state.

    The runner reads ``experiment_started`` and ``is_running`` from
    ``get_experiment_status`` and branches on the result.

    Parameters
    ----------
    experiment_started : bool
        Whether the project creator has called ``start_experiment``.
    is_running : bool
        Whether Marcus still considers the project active.

    Returns
    -------
    str
        ``"waiting"`` (not started yet), ``"running"`` (active), or
        ``"finished"`` (started and complete).
    """
    if not experiment_started:
        return "waiting"
    return "running" if is_running else "finished"


class StallWatchdog:
    """
    Detect a stalled run: task counts unchanged for N consecutive polls.

    Each control cycle the runner feeds the current
    ``(completed, in_progress, blocked)`` task-count tuple to
    :meth:`update`. When that tuple is identical for ``stall_polls``
    polls in a row, the run has made no progress and is considered
    stalled. Any change resets the counter.

    Parameters
    ----------
    stall_polls : int
        Consecutive unchanged polls that constitute a stall. ``0``
        disables the watchdog entirely (it never reports a stall).
    """

    def __init__(self, stall_polls: int) -> None:
        self._stall_polls = stall_polls
        self._last: Optional[Tuple[int, int, int]] = None
        self._unchanged = 0

    def update(self, completed: int, in_progress: int, blocked: int) -> bool:
        """
        Record one poll's task counts and report whether the run stalled.

        Parameters
        ----------
        completed, in_progress, blocked : int
            Task counts from the current poll.

        Returns
        -------
        bool
            True once the counts have been unchanged for ``stall_polls``
            consecutive polls; always False when the watchdog is disabled.
        """
        if self._stall_polls <= 0:
            return False

        current = (completed, in_progress, blocked)
        if current == self._last:
            self._unchanged += 1
        else:
            self._last = current
            self._unchanged = 0
        return self._unchanged >= self._stall_polls
