# 35. Assignment Lease System

> **Primary spec:** This document focuses on the lease data model, adaptive
> duration math, and renewal mechanics. For the end-to-end liveness
> detection, cadence-based recovery, touch-on-any-tool behavior, and the
> recovery handoff flow, see
> [Resilience and Task Recovery System](34-agent-recovery-system.md).

## Executive Summary

The Assignment Lease System tracks a short-lived **lease** for every
in-progress task assignment. A lease is Marcus's proof-of-life record for an
agent: while the lease is fresh, Marcus trusts that the agent is working;
once the lease expires past its grace period, the lease is evaluated for
recovery.

Marcus runs in an **aggressive** lease mode — lease durations are measured
in **seconds to minutes**, not hours. The defaults are tuned to detect dead
tmux panes, killed processes, and dropped network connections within one
to two monitor cycles. Adaptive duration math, priority and complexity
multipliers, and renewal decay still exist, but they operate within a
much tighter timing envelope than older versions of the system.

## Source Files

| Component | Path |
|-----------|------|
| Lease data model + manager + monitor | `src/core/assignment_lease.py` |
| Default configuration | `src/config/marcus_config.py` — `TaskLeaseSettings` |
| Server wiring + recovery callback | `src/marcus_mcp/server.py` |
| Lease creation + progress renewal + recreation | `src/marcus_mcp/tools/task.py` |
| Touch-on-any-tool-call | `src/marcus_mcp/handlers.py` |

## Lease Data Model

```python
@dataclass
class AssignmentLease:
    task_id: str
    agent_id: str
    assigned_at: datetime
    lease_expires: datetime
    last_renewed: datetime
    renewal_count: int = 0
    estimated_hours: float = 4.0
    progress_percentage: int = 0
    last_progress_message: str = ""
    grace_period_seconds: Optional[float] = None
    update_timestamps: list[datetime] = field(default_factory=list)
```

Key properties:

- `update_timestamps` — every progress update appends a timestamp. The
  lease exposes `median_update_interval`, the median seconds between
  updates, which powers cadence-based recovery (see
  [Resilience and Task Recovery System](34-agent-recovery-system.md)).
- `grace_period_seconds` — per-lease adaptive grace, set by the current
  progressive timeout phase.
- `renewal_count` — used by renewal decay and by the stuck-task detector.

## Aggressive Defaults

All tuning lives in `TaskLeaseSettings` in `src/config/marcus_config.py`.
The current defaults are:

| Setting | Default | Meaning |
|---------|---------|---------|
| `default_hours` | `0.025` | ~90 seconds base lease. |
| `grace_period_minutes` | `0.5` | 30 seconds of grace after expiry. |
| `min_lease_hours` | `0.0167` | 60 seconds — the floor. |
| `max_lease_hours` | `0.0833` | 5 minutes — the ceiling. |
| `warning_hours` | `0.01` | ~36 seconds before expiry, emit a warning. |
| `max_renewals` | `10` | Safety cap on renewal count. |
| `stuck_threshold_renewals` | `5` | Flag for stuck-task detection. |
| `silence_multiplier` | `1.5` | Cadence threshold multiplier. |
| `enable_adaptive` | `true` | Enable progressive phases. |
| `renewal_decay_factor` | `0.9` | Decay applied on each renewal. |

The dict-path fallback in `server.py` mirrors these values so config-less
startup still matches the dataclass defaults.

## Progressive Timeout Phases

When `default_hours < 1.0` (the aggressive mode path), `create_lease` and
`renew_lease` call `calculate_adaptive_timeout` to pick a phase-specific
lease + grace based on where the task is in its lifecycle:

| Phase | Trigger | Lease | Grace | Total | Rationale |
|-------|---------|-------|-------|-------|-----------|
| 1. Unproven | 0 updates | 60s | 20s | 80s | Detect startup failures fast. |
| 2. Working | 1 update | 90s | 30s | 120s | Agent is alive, be moderate. |
| 3. Proven | 25–75% progress | 120s | 30s | 150s | Protect in-flight work. |
| 4. Finishing | >75% progress | 60s | 15s | 75s | Detect final stalls quickly. |

A new task starts in Phase 1. As soon as the first
`report_task_progress` arrives, the lease transitions to Phase 2 and
subsequent phases follow the progress percentage.

## Lease Lifecycle

```
Task Assigned
     │
     ▼
create_lease() ──────────► Phase 1 lease (60s + 20s grace)
     │
     │ ◄─── touch_lease(agent_id)    (any MCP tool call extends lease)
     │
     ▼
Agent reports progress
     │
     ▼
renew_lease(task_id, progress) ──► Phase 2–4 based on progress
     │
     ├──── on each renewal: update_timestamps append
     │     renewal_count += 1
     │     renewal_decay applied
     │
     ▼
Task completes → lease removed from active_leases
```

### `touch_lease(agent_id)`

A cheap extension triggered by the MCP dispatch loop in
`handlers.py`. **Any** tool call from an agent (including
`log_decision`, `log_artifact`, `report_blocker`, `get_task_context`, etc.)
counts as a touch — the agent proves it is alive by working. No explicit
heartbeat is ever required.

```python
# src/marcus_mcp/handlers.py
agent_id = arguments.get("agent_id") if arguments else None
if agent_id and hasattr(state, "lease_manager") and state.lease_manager:
    await state.lease_manager.touch_lease(agent_id)
```

### `renew_lease(task_id, progress, message)`

The full renewal path used by `report_task_progress`. It appends a new
`update_timestamps` entry, recomputes the phase, applies decay, and pushes
out `lease_expires`.

### Lease Recreation on Progress Report

If `report_task_progress` runs and the lease is **missing** (because the
monitor already recovered the task due to a cadence false-positive), the
progress handler recreates the lease instead of failing:

```python
# src/marcus_mcp/tools/task.py
renewed_lease = await state.lease_manager.renew_lease(task_id, progress, message)
if renewed_lease is None:
    # Lease was recovered — recreate so monitoring resumes.
    task_obj = next((t for t in state.project_tasks if t.id == task_id), None)
    new_lease = await state.lease_manager.create_lease(task_id, agent_id, task_obj)
```

This makes false positives **self-healing**: the next progress update
re-attaches a lease and the monitor resumes watching.

### `recover_expired_lease(lease)`

Resets the task to `TODO`, clears `assigned_to`, builds a `RecoveryInfo`,
dual-writes to the board (field + comment), removes the lease from
`active_leases`, and finally invokes `on_recovery_callback(agent_id,
task_id)`.

See [Resilience and Task Recovery System](34-agent-recovery-system.md) for
the full recovery flow, including `RecoveryInfo`, worktree-aware handoff
instructions, and the cadence check that gates recovery.

## LeaseMonitor

```python
class LeaseMonitor:
    """Background asyncio task that polls every 60 seconds."""

    check_interval = 60  # seconds
```

On each poll it walks `active_leases`, identifies expired leases (past
grace), calls `should_recover_expired_lease` for the cadence-aware check,
and invokes `recover_expired_lease` when the check says to recover.

### Lazy start on the correct event loop

The monitor **must not** be started during server setup. The HTTP
transport spins up its own event loop per request context, and a monitor
task created during setup is bound to a loop that no longer exists by the
time a request arrives. Instead the server exposes
`ensure_lease_monitor_running()` and the first `request_next_task` call
lazily starts the monitor on the live request loop:

```python
# src/marcus_mcp/tools/task.py
if hasattr(state, "ensure_lease_monitor_running"):
    await state.ensure_lease_monitor_running()
```

## Recovery Callback

`AssignmentLeaseManager` does not import server state. The server sets a
callback at initialization so in-memory assignment tracking
(`agent_tasks`, `tasks_being_assigned`) is cleaned whenever a lease is
recovered:

```python
# src/marcus_mcp/server.py
def _on_recovery(agent_id: str, task_id: str) -> None:
    if agent_id in self.agent_tasks:
        del self.agent_tasks[agent_id]
    self.tasks_being_assigned.discard(task_id)

self.lease_manager.on_recovery_callback = _on_recovery
```

Without this, the assignment filter would keep the recovered task marked
as taken and no agent could pick it up.

## Adaptive Duration (Conservative Mode Only)

When `default_hours >= 1.0`, the manager falls back to classic adaptive
duration math using the task's `estimated_hours`, `priority_multipliers`,
and `complexity_multipliers`, bounded by `min_lease_hours` and
`max_lease_hours`. The Marcus production default is aggressive mode, so
this path is primarily a configuration escape hatch for long-running
non-agent workflows.

### Priority Multipliers

```python
"priority_multipliers": {
    "critical": 0.5,
    "high": 0.75,
    "medium": 1.0,
    "low": 1.5,
}
```

### Complexity Multipliers

```python
"complexity_multipliers": {
    "complex": 2.0,
    "large": 1.5,
    "simple": 0.75,
    "tiny": 0.5,
}
```

### Renewal Decay

```python
# With decay factor 0.9:
# Renewal 0: 1.00 * base
# Renewal 1: 0.90 * base
# Renewal 2: 0.81 * base
# ...
# bounded by min_lease_hours
```

Decay discourages tasks from being held indefinitely by agents that keep
renewing without finishing.

## Configuration

```json
{
  "task_lease": {
    "default_hours": 0.025,
    "max_renewals": 10,
    "warning_hours": 0.01,
    "grace_period_minutes": 0.5,
    "renewal_decay_factor": 0.9,
    "min_lease_hours": 0.0167,
    "max_lease_hours": 0.0833,
    "stuck_threshold_renewals": 5,
    "silence_multiplier": 1.5,
    "enable_adaptive": true,
    "priority_multipliers": {
      "critical": 0.5,
      "high": 0.75,
      "medium": 1.0,
      "low": 1.5
    },
    "complexity_multipliers": {
      "complex": 2.0,
      "large": 1.5,
      "simple": 0.75,
      "tiny": 0.5
    }
  }
}
```

Project-specific overrides live under each project in the project
registry; the global fallback lives in `src/config/marcus_config.py`.

## Statistics and Health

`AssignmentLeaseManager.get_statistics()` returns counts for active,
expiring-soon, expired, and stuck leases plus average and max renewal
counts. These are exposed through the `ping` health tool for operational
visibility.

## Related Documentation

- [Resilience and Task Recovery System](34-agent-recovery-system.md) — the
  primary spec describing cadence-based recovery, touch-on-any-tool-call,
  lease recreation, the recovery callback, the lazy monitor start,
  worktree-aware handoff, and the full kill → recover → reassign flow.
- [Orphan Task Recovery](33-orphan-task-recovery.md) — the startup
  reconciler and assignment monitor that act as a safety net for
  assignments left behind by non-lease code paths.
- [Agent Coordination](21-agent-coordination.md) — how task assignment,
  progress reporting, and the assignment filter fit together.
- [Smart Retry Strategy](46-smart-retry-strategy.md) — retry and backoff
  policies used alongside recovery.
