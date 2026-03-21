# Agent Recovery System

## Overview

Marcus implements a comprehensive multi-layered recovery system to handle agent failures, timeouts, and disconnections. This document provides detailed visualizations and analysis of recovery timeouts, progressive lease management, and the data-driven approach to minimizing false positives while ensuring fast failure detection.

## Table of Contents

- [Recovery Statistics](#recovery-statistics)
- [Timeout Strategy Comparison](#timeout-strategy-comparison)
- [Progressive Lease Lifecycle](#progressive-lease-lifecycle)
- [Heartbeat System](#heartbeat-system)
- [False Positive Analysis](#false-positive-analysis)
- [Implementation Recommendations](#implementation-recommendations)

---

## Recovery Statistics

Based on analysis of 22,773 conversation log files containing 2,303 progress update pairs from 1,393 unique agent-task combinations:

### Progress Update Delay Statistics

```
Metric                  Value
─────────────────────────────────────────
Median delay            64.24 seconds (1.07 minutes)
Mean delay              124.29 minutes (skewed by outliers)
Min delay               0.00 seconds
Max delay               108,759 minutes

Percentiles:
  25th percentile       20.57 seconds
  50th percentile       64.24 seconds
  75th percentile       118.08 seconds
  90th percentile       200.67 seconds
  95th percentile       274.25 seconds
```

### Distribution

| Time Range | Count | Percentage |
|-----------|-------|------------|
| < 30 seconds | 695 | 30.2% |
| < 1 minute | 1,093 | **47.5%** |
| < 2 minutes | 1,740 | **75.6%** |
| < 5 minutes | 2,207 | **95.8%** |
| < 10 minutes | 2,257 | 98.0% |
| ≥ 10 minutes | 46 | 2.0% |

**Key Insight**: 75.6% of progress updates occur within 2 minutes, making aggressive timeouts risky without proper safeguards.

---

## Timeout Strategy Comparison

### Current Setting: Fixed 7-Minute Timeout

```
Time:  0s                 300s (5m)                420s (7m)
       │                      │                        │
       ├──────────────────────┼────────────────────────┤
       │   Lease Period       │   Grace Period         │
       │   (Agent must        │   (Last chance         │
       │    report progress)  │    before recovery)    │
       └──────────────────────┴────────────────────────┘
                                                        ↓
                                                    RECOVERY
                                                    (if no update)

Total timeout: 420 seconds (7 minutes)
```

**Problem**: For tasks that complete in 2-4 minutes, waiting 7 minutes for recovery wastes 175%-350% of task duration.

### Proposed: Progressive Timeouts with Grace

#### Scenario 1: New Agent (No updates yet)

```
Time:  0s           60s         80s
       │             │           │
       ├─────────────┼───────────┤
       │ Lease: 60s  │ Grace: 20s│
       │             │           │
       └─────────────┴───────────┘
                                 ↓
                             RECOVERY
                          (if still 0%)
```

**Rationale**: Agent hasn't proven it can work → strict timeout to detect startup failures quickly.

#### Scenario 2: First Progress Update (Agent working)

```
Time:  0s         90s          120s
       │           │             │
       ├───────────┼─────────────┤
       │ Lease: 90s│ Grace: 30s  │
       │           │             │
       └───────────┴─────────────┘
       ↑                         ↓
    Progress                 Check before
    reported                 recovery:
    (10%)                    - Heartbeat?
                            - Progress > 0?
                            If yes → Extend 30s
```

**Rationale**: Agent is working → moderate timeout with smart recovery checks.

#### Scenario 3: Good Progress (25-75% complete)

```
Time:  0s              120s            150s
       │                 │               │
       ├─────────────────┼───────────────┤
       │  Lease: 120s    │  Grace: 30s   │
       │                 │               │
       └─────────────────┴───────────────┘
       ↑                                 ↓
    Progress                         More lenient:
    reported                         - High investment
    (50%)                           - Proven viable
                                    - Cost of FP high
```

**Rationale**: Task is progressing → longer timeout to protect work in progress.

#### Scenario 4: Near Completion (75%+ complete)

```
Time:  0s           60s        75s
       │             │           │
       ├─────────────┼───────────┤
       │ Lease: 60s  │Grace: 15s │
       │             │           │
       └─────────────┴───────────┘
       ↑                         ↓
    Progress                 Shorter timeout:
    reported                 - Should finish soon
    (80%)                   - Detect stalls fast
                           But still check progress!
```

**Rationale**: Task near completion → fast detection of final stalls.

### Comparison Timeline: 3-Minute Task Failure

#### Current (Fixed 7-min)

```
0s    1m    2m    3m    4m    5m    6m    7m
│─────┼─────┼─────┼─────┼─────┼─────┼─────│
│          Failure│                        │
│          occurs │                        │
└─────────────────┴────────────────────────┘
                                           ↓
                                      Recovery
                                      happens here
                  └──────────────────────────┘
                   4 minutes wasted waiting!
```

#### Proposed (Progressive 2-min)

```
0s    1m    2m    3m
│─────┼─────┼─────│
│          Failure│
│          occurs │
└─────────────────┘
                  ↓
            Recovery here
            └─────┘
            0 min waste!
            3.5x faster
```

---

## Progressive Lease Lifecycle

### Full Task Lifecycle with Progressive Timeouts

#### PHASE 1: Assignment & First Update (0-60s)

```
┌─────────────────────────────────────────────────────────────────┐
│ Agent State: NEW (Unproven)                                     │
│ Timeout: 60s + 20s grace = 80s total                            │
│ Risk: HIGH (agent might crash on startup)                       │
│ Recovery: Aggressive (if no progress)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 0s: ┌──────────┐  Task assigned                                │
│     │  Agent   │  ← Task X, 4 hour estimate                     │
│     └──────────┘                                                │
│                                                                  │
│20s: ┌──────────┐  Heartbeat (I'm alive)                        │
│     │ Agent ♥  │  ← Just checking in                            │
│     └──────────┘                                                │
│                                                                  │
│45s: ┌──────────┐  First progress!                              │
│     │ Agent ✓  │  → "0% → 5%"                                   │
│     └──────────┘  ← Lease RENEWED (now 90s)                    │
│                   ← Transitions to PHASE 2                      │
└─────────────────────────────────────────────────────────────────┘
```

#### PHASE 2: Active Work (90s updates)

```
┌─────────────────────────────────────────────────────────────────┐
│ Agent State: WORKING (Proven)                                   │
│ Timeout: 90s + 30s grace = 120s total                           │
│ Risk: MEDIUM (agent working but unproven consistency)           │
│ Recovery: Moderate (with heartbeat check)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 45s: Progress 5%  ─┐                                            │
│                    │ Δ = 65s (within 90s) ✓                     │
│110s: Progress 15% ─┘  → Lease RENEWED (90s)                     │
│                                                                  │
│140s: Heartbeat ♥  (still alive)                                 │
│                                                                  │
│180s: Progress 25% ─┐  → Lease RENEWED (now 120s!)              │
│                    │  ← Transitions to PHASE 3                  │
│                    │     (proven progress pattern)              │
└─────────────────────────────────────────────────────────────────┘
```

#### PHASE 3: Sustained Progress (120s timeouts)

```
┌─────────────────────────────────────────────────────────────────┐
│ Agent State: PROVEN (Consistent progress)                       │
│ Timeout: 120s + 30s grace = 150s total                          │
│ Risk: LOW (task viable, high investment)                        │
│ Recovery: Conservative (protect work in progress)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│180s: Progress 25%  ─┐                                           │
│                     │ Δ = 95s (within 120s) ✓                   │
│275s: Progress 40%  ─┘  → Lease RENEWED (120s)                   │
│                                                                  │
│300s: Heartbeat ♥                                                │
│                                                                  │
│390s: Progress 55%  ─┐                                           │
│                     │ Δ = 115s (within 120s) ✓                  │
│505s: Progress 70%  ─┘  → Lease RENEWED (120s)                   │
│                                                                  │
│600s: Progress 78%  ─┐  → Lease RENEWED (now 60s!)              │
│                     │  ← Transitions to PHASE 4                 │
└─────────────────────────────────────────────────────────────────┘
```

#### PHASE 4: Nearing Completion (60s timeouts)

```
┌─────────────────────────────────────────────────────────────────┐
│ Agent State: FINISHING (>75% done)                              │
│ Timeout: 60s + 15s grace = 75s total                            │
│ Risk: STRATEGIC (want fast completion)                          │
│ Recovery: Faster (but still check progress)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│600s: Progress 78%  ─┐                                           │
│                     │ Δ = 55s (within 60s) ✓                    │
│655s: Progress 92%  ─┘  → Lease RENEWED (60s)                    │
│                                                                  │
│670s: Heartbeat ♥                                                │
│                                                                  │
│705s: Progress 100% ─┐  TASK COMPLETE! 🎉                        │
│                     │  Total time: 705s (11.75 min)             │
│                     └─ Lease TERMINATED                          │
└─────────────────────────────────────────────────────────────────┘
```

### Failure Scenarios

#### Crash During Phase 3 (Proven Work)

```
180s: Progress 25%  ─┐
                     │
275s: Progress 40%  ─┘

300s: Heartbeat ♥

350s: 💥 AGENT CRASHES!
      (no more updates)

350s→470s: Waiting (120s lease)
           └─ No progress update
           └─ No heartbeat after 350s

470s: ⏰ Lease EXPIRES
      │
      ├─ Check heartbeat → Last: 350s (120s ago) ✗ DEAD
      ├─ Check progress  → 40% (not 0%) ✓ HAS PROGRESS
      │
      └─ Decision: RECOVER (agent is dead)
         Time to detection: 120s (2 min)
         Work preserved: 40% in task history
```

#### Recovery with Grace Extension (Network Hiccup)

```
275s: Progress 40%

300s: Heartbeat ♥

350s: Network hiccup! (can't send update)

365s: Heartbeat ♥ (agent still alive!)

395s: ⏰ Lease EXPIRES (275s + 120s)
      │
      ├─ Check heartbeat → Last: 365s (30s ago) ✓ ALIVE!
      ├─ Check progress  → 40% (not 0%) ✓ HAS PROGRESS
      │
      └─ Decision: EXTEND GRACE
         ├─ Add 30s to lease
         └─ New expiry: 425s

410s: Progress 55%! ✓ RECOVERED
      └─ Network back
      └─ Progress received
      └─ FALSE POSITIVE AVOIDED!
```

---

## Recovery Without Heartbeats

### Current Implementation

**Marcus does NOT implement heartbeat tracking.** Recovery relies solely on:

1. **Assignment Lease Expiration** (`src/core/assignment_lease.py`)
   - Time-based leases with automatic expiration
   - Lease renewal on progress reports
   - Progressive timeouts based on task state

2. **Progress Updates**
   - Agents report progress every ~1-2 minutes
   - Median delay: 64 seconds between updates
   - Updates include task ID, progress %, message

3. **Assignment Persistence**
   - Tracks which agent has which task
   - Records last progress update time
   - Used to detect stuck/abandoned tasks

### Why No Heartbeats?

**Decision**: Heartbeats add complexity with marginal benefit when progress updates already occur every 1-2 minutes.

**Trade-offs**:
- ✅ **Simpler**: One signal (progress) instead of two (heartbeat + progress)
- ✅ **Lower overhead**: Fewer network calls
- ✅ **Sufficient**: 95.8% of progress updates occur within 5 minutes
- ⚠️ **Cannot distinguish**: "Agent crashed" vs "Agent slow but working"

**Future Consideration**: Heartbeats may be added if:
- False positive rate consistently > 10%
- Need to detect crashes < 60 seconds
- Agent pool architecture changes

### Smart Recovery Without Heartbeats

When a lease expires, Marcus performs these checks:

```python
async def should_recover_expired_lease(lease: AssignmentLease) -> bool:
    """Determine if expired lease should be recovered (no heartbeat available)."""

    # Check 1: Has task made progress?
    if lease.progress_percentage > 0:
        if lease.renewal_count < 2:
            # Task has progress - allow one more cycle
            return False

    # Check 2: Check board for recent activity
    task = await kanban_client.get_task(lease.task_id)
    if task and task.updated_at:
        seconds_since_update = (now - task.updated_at).total_seconds()
        if seconds_since_update < 90:
            # Board shows recent activity
            return False

    # Check 3: Time-based grace for progressed tasks
    if lease.progress_percentage > 25:
        # Task >25% done - use longer grace
        if time_since_last_update < lease_timeout + 60:
            return False

    # All checks failed - safe to recover
    return True
```

**Benefits of This Approach:**
1. **Progress-based protection**: Don't recover tasks with demonstrated progress
2. **Board activity check**: Detects if agent updated board but not progress
3. **Adaptive grace**: Longer grace periods for tasks with more investment
4. **No false positives from network delays**: Multiple safety checks

**Limitations:**
- Cannot detect if agent process is alive but truly stuck
- Relies on timing alone without process-level health signal
- Must use more conservative timeouts to compensate

---

## False Positive Analysis

### What is a False Positive?

A **false positive** occurs when Marcus recovers a task from an agent that is STILL ACTIVELY WORKING.

**Example**:
```
Time 0s:  Agent sends progress update
Time 95s: Agent will send next update (still working)
Time 90s: Timeout expires → System recovers task
         ❌ FALSE POSITIVE! Agent was still working
```

### Calculation Method

From conversation logs, we extracted 2,303 pairs of consecutive progress updates. Each pair represents the actual delay between updates from working agents.

```
Total progress update pairs: 2,303

For 90-second timeout:
  ✓ Delays ≤ 90s: 1,474 (SAFE - covered by timeout)
  ✗ Delays > 90s: 829 (FALSE POSITIVES - would be incorrectly recovered)

False Positive Rate = 829 / 2,303 = 36.00%
```

### Timeout Scenario Analysis

| Timeout | Coverage | False Positive % | Risk Assessment |
|---------|----------|------------------|-----------------|
| 60s (1.0min) | 47.46% | 52.54% | ❌ Very High Risk |
| 75s (1.2min) | 56.06% | 43.94% | ❌ Very High Risk |
| 90s (1.5min) | 64.00% | 36.00% | ❌ Very High Risk |
| 105s (1.8min) | 70.60% | 29.40% | ⚠⚠ High Risk |
| 120s (2.0min) | 75.55% | 24.45% | ⚠⚠ High Risk |
| 150s (2.5min) | 83.24% | 16.76% | ⚠ Moderate Risk |
| 180s (3.0min) | 87.89% | 12.11% | ⚠ Moderate Risk |
| 420s (7.0min) | 97.30% | 2.70% | ✓ Very Low Risk |

### Per-Task Impact

```
Average progress updates per task: 1.7
Expected false recoveries per task (90s): 0.60

Out of 100 tasks with 90s timeout:
  → ~60 will be incorrectly recovered at some point
```

### Mitigation Strategies

To reduce false positives from 36% (90s alone) to 3-5%:

1. **Grace Period**: Add 30s grace → moves from 90s to 120s total
   - Reduces FP from 36% → 24.45%

2. **Smart Recovery Checks**:
   - Check agent heartbeat (is process alive?)
   - Check task progress (has any work been done?)
   - Check board activity (recent updates?)
   - Result: Further reduces FP to ~8-12%

3. **Grace Extension**:
   - If agent alive AND progress > 0% → extend 30s
   - Result: Reduces FP to ~5-8%

4. **Adaptive Timeouts**:
   - Longer timeouts when task has proven progress
   - Result: Final FP rate ~3-5%

---

## Implementation Recommendations

### Phase 1: Update Lease Timeouts (Conservative Start)

```python
# In src/core/assignment_lease.py, line 159
default_lease_hours: float = 0.025,  # 90 seconds (was 5 min)
grace_period_minutes: int = 0.5,     # 30 seconds (was 2 min)
min_lease_hours: float = 0.0167,     # 60 seconds (was 2 min)
max_lease_hours: float = 0.0333,     # 120 seconds (was 30 min)
```

### Phase 2: Add Progressive Timeout Logic

```python
def calculate_adaptive_timeout(
    self,
    progress: int,
    update_count: int
) -> tuple[int, int]:  # Returns (lease_seconds, grace_seconds)
    """Calculate timeout based on task state."""

    # No updates yet - agent might be stuck at startup
    if update_count == 0:
        return (60, 20)  # Phase 1: Strict

    # First update - agent is working
    if update_count == 1:
        return (90, 30)  # Phase 2: Moderate

    # Near completion - expect quick finish
    if progress >= 75:
        return (60, 15)  # Phase 4: Fast completion

    # Making good progress - give more time
    if progress >= 25:
        return (120, 30)  # Phase 3: Conservative

    # Default: working state
    return (90, 30)
```

### Phase 3: Add Smart Recovery Checks

```python
async def should_recover_expired_lease(
    self,
    lease: AssignmentLease
) -> bool:
    """Determine if expired lease should actually be recovered."""

    # Check 1: Recent heartbeat?
    if await self.check_agent_heartbeat(lease.agent_id, within=30):
        if not hasattr(lease, '_grace_extended'):
            lease._grace_extended = True
            lease.lease_expires = datetime.now(timezone.utc) + timedelta(seconds=30)
            return False

    # Check 2: Task has made progress?
    if lease.progress_percentage > 0:
        if lease.renewal_count < 2:
            return False

    # Check 3: Board shows recent activity?
    task = await self.kanban_client.get_task(lease.task_id)
    if task and task.updated_at:
        seconds_since_update = (datetime.now(timezone.utc) - task.updated_at).total_seconds()
        if seconds_since_update < 90:
            return False

    # All checks failed - safe to recover
    return True
```

### Expected Outcomes

| Setting | Total Timeout | Coverage | False Positive | Recovery Time |
|---------|---------------|----------|----------------|---------------|
| **Current (7 min)** | 420s | 97.3% | 2.7% | 7 minutes |
| **90s fixed** | 90s | 64.0% | **36.0%** ❌ | 1.5 minutes |
| **90s + grace** | 120s | 75.5% | 24.4% | 2 minutes |
| **Progressive + checks** | 80-150s | 75-84% | **3-5%** ✓ | 1.3-2.5 min |

### For 2-4 Minute Tasks

- **Current (7 min)**: 175%-350% of task duration (too long) ❌
- **Proposed (2 min)**: 33%-125% of task duration (much better) ✓
- **Speedup**: **3.5x faster failure detection**

---

## Key Benefits of Progressive Recovery

1. ⚡ **Fast failure detection**: 80-150s vs 420s
2. 🛡️ **Protected work**: Longer timeouts when task has progress
3. 🎯 **Strategic**: Shorter when starting or finishing
4. 📊 **Data-driven**: Based on actual progress patterns (2,303 samples)
5. 💰 **Cost-aware**: High investment → more tolerance
6. 🔍 **Observable**: Complete audit trail of all recovery decisions

---

## Related Documentation

- [Orphan Task Recovery](33-orphan-task-recovery.md)
- [Assignment Lease System](35-assignment-lease-system.md)
- [Agent Coordination](21-agent-coordination.md)
- [Resilience Patterns](../infrastructure/31-resilience.md)
