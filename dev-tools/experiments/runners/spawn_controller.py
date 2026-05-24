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
    in_flight_tasks: int,
    unclaimed_tasks: int,
) -> int:
    """
    Decide how many ephemeral agents to spawn this control cycle.

    The formula is ``max(0, min(desired_agent_count - in_flight_tasks,
    unclaimed_tasks))``:

    - ``desired_agent_count - in_flight_tasks`` is the staffing gap:
      how many MORE active claimers the active layer needs.
    - The ``unclaimed_tasks`` cap prevents spawning an agent for which no
      claimable task exists — such an agent would receive "no task" and
      idle, the cost Fix 3 removes.
    - The ``max(0, ...)`` clamp handles a layer boundary: ``desired``
      drops as the graph narrows while a just-finished assignment is
      still being reaped, so the gap can be momentarily negative.

    Why ``in_flight_tasks`` instead of ``live_agents`` (issue #632)
    --------------------------------------------------------------
    Pre-#632 this formula used a runner-side count of alive tmux panes
    as the staffing variable. That count answers the question "how many
    processes exist?" which is the same as "how many agents will claim
    the next unclaimed task?" only under the old long-lived agent model.
    Under the ephemeral lifecycle (PR #600) an agent does EXACTLY ONE
    task and exits — so a pane that's still alive after the agent
    finished its task will never claim more work. Counting it as
    "staffing" stalls the run for any hangover task.

    The right question is "how many tasks have an agent actively working
    on them?" — which Marcus answers directly via the IN_PROGRESS count
    in the active layer. The runner reads it from
    ``get_desired_agent_count``'s response.

    Parameters
    ----------
    desired_agent_count : int
        Active-layer width capped at ``max_agents`` (from Marcus's
        ``get_desired_agent_count``).
    in_flight_tasks : int
        IN_PROGRESS tasks in the active layer (from
        ``get_desired_agent_count``). Replaces the pre-#632 ``live_agents``
        pane count.
    unclaimed_tasks : int
        TODO tasks in the active layer (from ``get_desired_agent_count``).

    Returns
    -------
    int
        Number of ephemeral agents to spawn now; never negative.
    """
    gap = desired_agent_count - in_flight_tasks
    return max(0, min(gap, unclaimed_tasks))


def experiment_lifecycle_state(
    experiment_started: bool, is_running: bool, seen_running: bool
) -> str:
    """
    Map Marcus's experiment-status fields to a lifecycle state.

    The runner reads ``experiment_started`` and ``is_running`` from
    ``get_experiment_status`` each poll and branches on the result.

    Marcus's startup has a gap: the project creator calls
    ``start_experiment`` (which sets ``experiment_started=True``) and
    only *then* does the LiveExperimentMonitor spin up and flip
    ``is_running=True``. A poll landing in that gap sees
    ``experiment_started=True, is_running=False`` — which, from those
    two fields alone, is indistinguishable from a genuinely finished
    run. ``seen_running`` resolves it: a not-running poll counts as
    "finished" only once the runner has actually observed
    ``is_running=True`` at least once; before that it is still
    "waiting" for the monitor to come up.

    Parameters
    ----------
    experiment_started : bool
        Whether the project creator has called ``start_experiment``.
    is_running : bool
        Whether Marcus currently considers the project active.
    seen_running : bool
        Whether the runner has observed ``is_running=True`` on any
        prior poll this run (a latch the caller maintains).

    Returns
    -------
    str
        ``"waiting"`` (not started, or monitor not up yet),
        ``"running"`` (active), or ``"finished"`` (was running and has
        now stopped).
    """
    if not experiment_started:
        return "waiting"
    if is_running:
        return "running"
    return "finished" if seen_running else "waiting"


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
