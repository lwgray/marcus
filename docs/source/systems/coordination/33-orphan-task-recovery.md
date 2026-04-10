# 33. Orphan Task Recovery (Safety Net)

> **Primary recovery mechanism:** The main path for detecting dead agents
> and recovering their tasks is the lease system. See
> [Resilience and Task Recovery System](34-agent-recovery-system.md) and
> [Assignment Lease System](35-assignment-lease-system.md).
>
> This document describes the **out-of-band safety net** that runs
> alongside the lease system: startup reconciliation and the assignment
> monitor. These mechanisms exist to catch assignments that slip past the
> lease-based path — mismatches between in-memory state, persistence, and
> the kanban board — which can happen during server restarts or when code
> paths update the board without touching the lease manager.

## Where It Fits

Marcus has three layers of protection against orphaned tasks:

1. **Primary — Assignment Lease System.** Every in-progress task has a
   short lease (seconds to minutes). Dead agents are detected within one
   to two monitor cycles via cadence-based recovery. This is the path
   that runs while the server is live and handles the common case of
   "agent tmux pane was killed." See
   [Resilience and Task Recovery System](34-agent-recovery-system.md).
2. **Safety net — Assignment Monitor.** A separate 30-second polling
   loop that watches for state **reversions** on the board (a task that
   was `IN_PROGRESS` drops back to `TODO` without going through the lease
   manager) and cleans stale persistence entries. This catches edge cases
   where the board is updated outside of Marcus or where a code path
   forgets to notify the lease manager.
3. **Startup — Assignment Reconciler.** A one-shot pass at server boot
   that validates every persisted assignment against the live kanban
   state, removes stale entries, and restores orphaned `IN_PROGRESS`
   tasks that exist on the board but are missing from persistence.

Taken together, the lease system handles **live liveness detection**,
while the components in this document handle **state consistency** across
restarts and between Marcus's three stores of truth (in-memory,
persistence, kanban board).

## Components

### 1. Assignment Monitor (`AssignmentMonitor`)

**File:** `src/monitoring/assignment_monitor.py`

A background task that polls every `check_interval` seconds (default 30)
looking for task state reversions. It does **not** perform liveness
detection — that is the lease manager's job. It specifically catches
cases where:

- The board shows a task flipped back to `TODO` but persistence still
  thinks it is assigned.
- The board shows a task was reassigned to a different agent than the
  one persistence has recorded.
- The board shows a task as `DONE` but persistence still has it
  assigned.
- The board shows a task `BLOCKED` with no assignee, but persistence
  still has it assigned.

```python
async def _detect_reversion(self, task: Task, worker_id: str) -> bool:
    # Case 1: Task went back to TODO (could be lease recovery from a
    # previous server instance, or a manual board edit).
    if task.status == TaskStatus.TODO:
        return True

    # Case 2: Task is IN_PROGRESS but assigned to a different worker.
    if task.status == TaskStatus.IN_PROGRESS and task.assigned_to != worker_id:
        return True

    # Case 3: Task completed by someone else.
    if task.status == TaskStatus.DONE and task.assigned_to != worker_id:
        return True

    # Case 4: Task blocked with no assignee.
    if task.status == TaskStatus.BLOCKED and not task.assigned_to:
        return True

    return False
```

When a reversion is detected, the monitor removes the stale persistence
entry. It does **not** generate `RecoveryInfo` or handoff instructions —
that is the lease system's responsibility on the primary path. The
monitor is strictly a bookkeeping cleanup layer.

#### Monitoring Loop

```python
async def _monitor_loop(self) -> None:
    while self._running:
        try:
            await self._check_for_reversions()
            await asyncio.sleep(self.check_interval)  # default: 30 seconds
        except Exception as exc:
            logger.error(f"Error in assignment monitor: {exc}")
            await asyncio.sleep(self.check_interval)
```

### 2. Assignment Reconciler (`AssignmentReconciler`)

**File:** `src/core/assignment_reconciliation.py`

Runs at server startup (and on demand) to reconcile persistence with the
live board. It walks every persisted assignment and every
`IN_PROGRESS` task on the board, then decides what to do for each pair:

| Persistence | Board Status | Board `assigned_to` | Action |
|---|---|---|---|
| Present | TODO | None | Remove assignment (task was reverted). |
| Present | DONE | Different agent | Remove assignment (finished by someone else). |
| Present | IN_PROGRESS | Same agent | Keep — valid assignment. |
| Present | IN_PROGRESS | Different agent | Remove assignment (reassigned). |
| Missing | IN_PROGRESS | Any agent | **Restore** — orphaned in-progress task. |
| Present | Task missing | N/A | Remove assignment (task deleted). |

Restored assignments do not carry `RecoveryInfo`, because the reconciler
runs before any agent has asked for work and does not know whether the
restored in-progress task actually needs recovery or is simply one that
survived the restart.

### 3. Assignment Health Checker

**File:** `src/monitoring/assignment_monitor.py` (bundled with
`AssignmentMonitor`)

Exposes `check_assignment_health()` for the `ping` health endpoint. It
reports counts of persisted assignments, kanban-assigned tasks, and any
mismatches between the two — a useful operational check because those
mismatches are exactly what the monitor and reconciler exist to fix.

## When the Safety Net Fires

In steady state, the lease system handles everything and the safety net
does almost nothing. These components earn their keep at the seams:

- **Server restart.** While Marcus is down, a lease monitor cannot run.
  On boot, the reconciler checks every persisted assignment against the
  live board and fixes whatever has drifted.
- **External board edits.** A human (or another tool) resets a task to
  `TODO` on the board. The lease manager has no event for this. On the
  next 30-second tick the assignment monitor notices and clears the
  stale persistence entry.
- **Non-lease code paths.** A code path updates the board status without
  touching the lease manager (e.g. a legacy integration or a bulk
  operation). The monitor catches the mismatch and cleans up.
- **Persistence/board split-brain.** Whatever the board says wins. The
  reconciler treats the kanban board as the source of truth and updates
  persistence to match.

## Relationship to the Lease System

| Concern | Primary Path | Safety Net |
|---|---|---|
| Detect dead agents | Lease monitor + cadence check | — |
| Touch-on-any-tool liveness | Lease manager | — |
| Reset task to TODO on board | Lease manager | — |
| Build `RecoveryInfo` + handoff | Lease manager | — |
| Clean in-memory `agent_tasks` | `on_recovery_callback` | — |
| Clean stale persistence | Lease manager on recovery | Assignment monitor (reversions) |
| Reconcile across server restart | — | Assignment reconciler |
| Restore orphaned IN_PROGRESS | — | Assignment reconciler |
| Detect board/persistence drift | — | Assignment health checker |

The lease system owns the **live** path. The safety net owns the
**consistency** path. They do not duplicate work, and the monitor does
not try to generate recovery handoffs — if handoff context is needed,
the task should go through a lease recovery, not a reversion cleanup.

## Configuration

```python
monitor = AssignmentMonitor(
    persistence=assignment_persistence,
    kanban_client=kanban_client,
    check_interval=30,  # seconds
)
await monitor.start()
```

The `force_reconciliation()` method is on `AssignmentMonitor` (in
`src/monitoring/assignment_monitor.py`), not on `AssignmentReconciler`.
`AssignmentReconciler` only exposes `reconcile_assignments()`;
`AssignmentMonitor.force_reconciliation()` calls that internally.

Startup reconciliation is **not** automatic — it only runs when
`force_reconciliation()` is explicitly called. The server initialization
method is `_initialize_monitoring_systems` (not `_initialize_persistence`)
and it sets up the monitor but does not trigger an immediate reconciliation
pass.

## Limitations

1. The assignment monitor relies on kanban board polling. If the board
   provider is temporarily unavailable, the monitor logs the error and
   keeps retrying on the next interval.
2. The monitor performs **cleanup only**, not handoff. A task cleaned up
   by the monitor will be re-offered to agents without the Layer 1.1
   recovery handoff in its instructions. If you need a handoff with
   `git merge` instructions for the next agent, the task should be
   recovered through the lease system while the server is live, not
   picked up by the reconciler after a restart.
3. The reconciler prefers the board as the source of truth. If the board
   state itself is wrong, the reconciler will propagate that wrongness
   into persistence.

## Related Documentation

- [Resilience and Task Recovery System](34-agent-recovery-system.md) — the
  primary spec for agent liveness detection, cadence-based recovery,
  touch-on-any-tool-call, lease recreation, the recovery callback,
  the lazy monitor start, and the worktree-aware handoff flow.
- [Assignment Lease System](35-assignment-lease-system.md) — lease data
  model, progressive timeout phases, and aggressive defaults (90s lease,
  30s grace, 60s min, 5min max).
- [Agent Coordination](21-agent-coordination.md) — task assignment flow
  and the assignment filter.
