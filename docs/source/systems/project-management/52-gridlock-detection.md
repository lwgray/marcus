# Gridlock Detection System

## Overview

The Gridlock Detection System identifies when a Marcus project has entered a deadlock state where forward progress is impossible. It detects the specific situation where agents are actively requesting tasks but all available tasks are blocked by dependencies, creating a gridlock that requires human intervention.

**Core Principle**: Detect project stalls BEFORE they waste hours of agent time and user frustration.

## Problem Solved

### The Gridlock Scenario

**Symptoms**:
1. Multiple agents requesting tasks ("I'm ready to work!")
2. Tasks exist on the Kanban board in TODO state
3. ALL TODO tasks are blocked by dependencies
4. No (or very few) tasks actively IN_PROGRESS
5. Agents keep retrying, getting "no task available"

**Result**: Project appears active but is actually stalled. No forward progress possible.

**Before Gridlock Detection:**
```
Agent 1: Request task → No task available
Agent 2: Request task → No task available
Agent 3: Request task → No task available
[Repeats for hours until user notices something is wrong]
```

**After Gridlock Detection:**
```
Agent 1: Request task → No task available
Agent 2: Request task → No task available
Agent 3: Request task → No task available
Marcus: 🚨 PROJECT GRIDLOCK DETECTED!
        3 agents requested tasks but none available
        10 tasks exist in TODO state
        ALL 10 TODO tasks are blocked by dependencies
        Only 0 task(s) in progress

        IMMEDIATE ACTIONS REQUIRED:
        1. Run diagnostics: diagnose_project()
        2. Check for circular dependencies
        3. Verify in-progress tasks haven't stalled
        4. Consider manually unblocking a task
```

## Architecture

### Component Diagram

```
request_next_task()
    ↓
No task available for agent
    ↓
GridlockDetector.record_no_task_response(agent_id)
    ↓
GridlockDetector.check_for_gridlock(all_tasks)
    ↓
Analyze:
- Recent failed requests (in 5-min window)
- TODO task count
- Blocked task count
- IN_PROGRESS task count
    ↓
Is gridlock? (requests ≥ 3 AND all TODO blocked AND few in-progress)
    ↓
YES → Log critical alert + diagnosis + recommended actions
NO  → Continue normally
```

### Detection Algorithm

**Gridlock Conditions (ALL must be true)**:
1. **Active demand**: ≥ 3 failed task requests in 5-minute window
2. **Tasks exist**: TODO tasks > 0
3. **All blocked**: blocked_tasks == todo_tasks (100% blocked)
4. **Few active**: in_progress_tasks ≤ 1

```python
is_gridlock = (
    recent_requests >= 3
    and len(todo_tasks) > 0
    and len(blocked_tasks) == len(todo_tasks)
    and len(in_progress_tasks) <= 1
)
```

## Implementation

### GridlockDetector Class

**File**: `src/core/gridlock_detector.py`

```python
class GridlockDetector:
    """
    Detects project gridlock situations.

    Gridlock occurs when:
    1. Agents are actively requesting tasks (N requests in M minutes)
    2. Tasks exist in TODO state
    3. All TODO tasks are blocked by dependencies
    4. No tasks are actively IN_PROGRESS or being worked on
    """

    def __init__(
        self,
        request_threshold: int = 3,
        time_window_minutes: int = 5,
        alert_cooldown_minutes: int = 10,
    ):
        """Initialize gridlock detector with configurable thresholds."""
        self.request_threshold = request_threshold
        self.time_window = timedelta(minutes=time_window_minutes)
        self.alert_cooldown = timedelta(minutes=alert_cooldown_minutes)
        self.recent_no_task_requests: deque = deque(maxlen=20)
        self.last_alert_time: Optional[datetime] = None
```

### Key Methods

#### 1. Record Failed Request

```python
def record_no_task_response(self, agent_id: str) -> None:
    """
    Record that an agent requested a task but none were available.

    Tracks timestamp and agent ID for gridlock analysis.
    """
    self.recent_no_task_requests.append({
        "agent_id": agent_id,
        "timestamp": datetime.now(),
    })
```

#### 2. Check for Gridlock

```python
def check_for_gridlock(
    self,
    tasks: List[Task],
    agent_requests_count: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Check if project is in gridlock state.

    Returns
    -------
    Dict[str, Any]
        {
            "is_gridlock": bool,
            "should_alert": bool,  # Respects cooldown
            "severity": "critical" | "normal",
            "metrics": {...},
            "diagnosis": str  # Human-readable analysis
        }
    """
```

#### 3. Generate Diagnosis

```python
def _generate_diagnosis(
    self,
    is_gridlock: bool,
    recent_requests: int,
    todo_tasks: List[Task],
    blocked_tasks: List[Task],
    in_progress_tasks: List[Task],
) -> str:
    """
    Generate human-readable diagnosis with:
    - Symptoms (what's happening)
    - Root cause (why it's gridlocked)
    - Immediate actions (what to do)
    - Blocked task list (first 5 + count)
    """
```

## Integration Points

### 1. Server Initialization

**File**: `src/marcus_mcp/server.py` (lines 142-148)

```python
# Gridlock detection
from src.core.gridlock_detector import GridlockDetector

self.gridlock_detector = GridlockDetector(
    request_threshold=3,        # 3 failed requests
    time_window_minutes=5,      # in 5 minutes
    alert_cooldown_minutes=10,  # Don't spam alerts
)
```

### 2. Task Assignment

**File**: `src/marcus_mcp/tools/task.py` (lines 657-681)

```python
# No task available - record for gridlock detection
if hasattr(state, "gridlock_detector") and state.gridlock_detector:
    state.gridlock_detector.record_no_task_response(agent_id)

    # Check for gridlock
    gridlock_result = state.gridlock_detector.check_for_gridlock(
        state.project_tasks
    )

    if gridlock_result["is_gridlock"] and gridlock_result["should_alert"]:
        # CRITICAL: Project is gridlocked!
        logger.critical("🚨 PROJECT GRIDLOCK DETECTED!")
        logger.critical(gridlock_result["diagnosis"])

        # Log to conversation for visibility
        conversation_logger.log_pm_thinking(
            "🚨 PROJECT GRIDLOCK DETECTED",
            {
                "severity": "critical",
                "metrics": gridlock_result["metrics"],
                "diagnosis": gridlock_result["diagnosis"],
            },
        )
```

## Diagnosis Output

### Example Diagnosis

```
🚨 PROJECT GRIDLOCK DETECTED

SYMPTOMS:
  • 5 agents requested tasks but none available
  • 12 tasks exist in TODO state
  • ALL 12 TODO tasks are blocked by dependencies
  • Only 1 task(s) in progress

ROOT CAUSE:
  Likely circular dependencies or missing tasks that unlock work.

IMMEDIATE ACTIONS REQUIRED:
  1. Run diagnostics: diagnose_project() or capture_stall_snapshot()
  2. Check for circular dependencies in task graph
  3. Verify in-progress tasks haven't stalled (check lease status)
  4. Consider manually unblocking a task to break the deadlock

BLOCKED TASKS (12):
  • Implement User Registration (ID: task_abc123)
    Waiting for: setup_database, create_auth_middleware
  • Create Login Endpoint (ID: task_def456)
    Waiting for: user_registration, setup_sessions
  • Setup Database Schema (ID: task_ghi789)
    Waiting for: user_registration
  ... and 9 more
```

### Metrics in Diagnosis

```python
"metrics": {
    "recent_failed_requests": 5,
    "total_tasks": 15,
    "todo_tasks": 12,
    "blocked_tasks": 12,
    "in_progress_tasks": 1,
    "done_tasks": 2,
    "time_window_minutes": 5.0,
}
```

## Configuration

### Thresholds

**Configurable at initialization**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `request_threshold` | 3 | Failed requests to trigger detection |
| `time_window_minutes` | 5 | Time window for counting requests |
| `alert_cooldown_minutes` | 10 | Minutes between alerts |

**Tuning Recommendations**:

```python
# Conservative (fewer false positives)
detector = GridlockDetector(
    request_threshold=5,        # 5 requests
    time_window_minutes=10,     # in 10 minutes
    alert_cooldown_minutes=15,  # 15 min between alerts
)

# Aggressive (catch gridlock faster)
detector = GridlockDetector(
    request_threshold=2,        # 2 requests
    time_window_minutes=3,      # in 3 minutes
    alert_cooldown_minutes=5,   # 5 min between alerts
)

# Default (balanced)
detector = GridlockDetector(
    request_threshold=3,
    time_window_minutes=5,
    alert_cooldown_minutes=10,
)
```

### Alert Cooldown

Prevents alert spam when gridlock persists:

```python
# First detection
[12:00:00] 🚨 PROJECT GRIDLOCK DETECTED! [Full diagnosis]

# Subsequent detections (within 10 minutes)
[12:02:00] Gridlock still detected (alert suppressed - cooldown)
[12:05:00] Gridlock still detected (alert suppressed - cooldown)

# Cooldown expires
[12:11:00] 🚨 PROJECT GRIDLOCK DETECTED! [Full diagnosis again]
```

**Reset cooldown manually** (for testing):

```python
detector.reset_alert_cooldown()
```

## Common Gridlock Causes

### 1. Circular Dependencies

**Scenario**: Task A depends on B, B depends on C, C depends on A

**Detection**: All three tasks blocked waiting for each other

**Fix**: Use Task Graph Auto-Fix system to break cycle

### 2. Stuck IN_PROGRESS Task

**Scenario**: Agent abandoned task without completing/reporting blocker

**Detection**: Task IN_PROGRESS for > 2 hours with no progress reports

**Fix**: Use Assignment Lease system to recover stalled tasks

### 3. Missing Implementation Task

**Scenario**: All tasks depend on "Setup Database" but that task doesn't exist

**Detection**: All tasks reference same missing dependency

**Fix**: Manually create the missing task or remove bad dependency

### 4. All Tasks Depend on Failed Task

**Scenario**: Critical task failed, all downstream tasks blocked

**Detection**: One DONE task, all others depend on it but can't proceed

**Fix**: Re-open failed task or update dependencies

## Responding to Gridlock

### Immediate Actions

**1. Run Diagnostics**:
```bash
# Capture current state
python scripts/analyze_stall.py capture

# Or use MCP tool
diagnose_project()
```

**2. Analyze Blocked Tasks**:
```python
# Check what tasks are blocked
for task in blocked_tasks:
    print(f"{task.name} waiting for:")
    for dep_id in task.dependencies:
        dep = get_task(dep_id)
        print(f"  - {dep.name} ({dep.status})")
```

**3. Check for Circular Dependencies**:
```python
from src.core.task_graph_validator import TaskGraphValidator

# Will show circular dependency if exists
try:
    TaskGraphValidator.validate_strictly(tasks)
except ValueError as e:
    print(f"Found issue: {e}")
```

**4. Check Stalled Tasks**:
```python
# Find tasks IN_PROGRESS for > 2 hours
from src.core.assignment_lease import AssignmentLeaseManager

stalled = lease_manager.find_stalled_assignments()
for assignment in stalled:
    print(f"Stalled: {assignment.task_name} by {assignment.assigned_to}")
```

### Resolution Strategies

#### Strategy 1: Manual Task Unblocking

```python
# Identify blocking task
blocking_task = tasks[0].dependencies[0]

# Complete it manually (if trivial) or assign to agent
mark_task_complete(blocking_task)
```

#### Strategy 2: Remove Invalid Dependencies

```python
# If dependency is invalid, remove it
task.dependencies.remove(invalid_dep_id)
update_task(task)
```

#### Strategy 3: Recover Stalled Task

```python
# If task stuck IN_PROGRESS, recover it
lease_manager.recover_lease(stalled_assignment)
# Now task is available again
```

#### Strategy 4: Recreate Project

If gridlock is severe and unfixable:

```python
# 1. Save current progress
snapshot = capture_stall_snapshot()

# 2. Extract completed work
completed = [t for t in tasks if t.status == DONE]

# 3. Recreate project with fixes
new_project = create_project_from_description(
    original_description,
    mode="new_project"
)

# 4. Mark completed tasks as done in new project
for task in completed:
    mark_done_in_new_project(task)
```

## Monitoring and Alerting

### Log Levels

**CRITICAL**: Gridlock detected (requires human intervention)
```
2025-10-07 12:34:56 CRITICAL 🚨 PROJECT GRIDLOCK DETECTED!
2025-10-07 12:34:56 CRITICAL [Full diagnosis with symptoms, root cause, actions]
```

**WARNING**: Failed task requests accumulating
```
2025-10-07 12:30:00 WARNING Agent agent_001 requested task - none available (2/3 threshold)
```

**INFO**: Normal operation
```
2025-10-07 12:25:00 INFO Agent agent_001 requested task - none available (1/3 threshold)
```

### Metrics to Track

| Metric | Formula | Healthy Range |
|--------|---------|---------------|
| Gridlock frequency | Gridlocks per day | < 1 per day |
| Time to gridlock | Minutes until first gridlock | > 30 minutes |
| Resolution time | Minutes from detection to fix | < 15 minutes |
| False positive rate | False alarms / total alerts | < 10% |
| Repeat gridlock rate | Same project gridlocked 2+ times | < 5% |

### Alerting

**Slack/Email Integration**:

```python
if gridlock_result["is_gridlock"] and gridlock_result["should_alert"]:
    send_alert(
        channel="#marcus-alerts",
        title="🚨 Project Gridlock Detected",
        message=gridlock_result["diagnosis"],
        severity="critical",
        project_id=state.project_id,
    )
```

## Testing

### Unit Tests

**File**: `tests/unit/core/test_gridlock_detector.py` (to be created)

**Test Coverage**:
- ✓ Normal operation (no gridlock)
- ✓ Gridlock detection with exact thresholds
- ✓ Alert cooldown prevents spam
- ✓ Time window cleanup (old requests removed)
- ✓ Metrics accuracy
- ✓ Diagnosis formatting
- ✓ Edge cases (no tasks, all tasks done, etc.)

### Integration Tests

**Scenario Testing**:

```python
# Test 1: Circular dependency causes gridlock
def test_circular_dependency_gridlock():
    # Create tasks with circular deps
    # Have 3 agents request tasks
    # Verify gridlock detected
    # Verify diagnosis mentions circular deps

# Test 2: Stuck task causes gridlock
def test_stuck_task_gridlock():
    # Create tasks with one IN_PROGRESS for 2+ hours
    # All other tasks depend on it
    # Have agents request tasks
    # Verify gridlock detected
    # Verify diagnosis mentions stalled task
```

## Performance

**Complexity**:
- `record_no_task_response()`: O(1)
- `check_for_gridlock()`: O(n × m) where n=tasks, m=avg dependencies
- **Overall**: O(n × m) per check

**Typical Performance**:
- 10 tasks: < 1ms
- 100 tasks: < 5ms
- 1000 tasks: < 50ms

**Memory**:
- Stores max 20 recent requests
- Each request: ~100 bytes
- Total memory: ~2 KB

## Edge Cases

### 1. Agents Stop Requesting Tasks

**Scenario**: Gridlock exists but agents gave up requesting

**Detection**: Won't detect (requires active requests)

**Prevention**: Agents should retry indefinitely with backoff

### 2. One Task Slowly In Progress

**Scenario**: 1 task IN_PROGRESS, all others blocked, making slow progress

**Detection**: Gridlock NOT detected (in_progress_tasks > 0)

**Monitoring**: Use lease system to detect stalled tasks

### 3. Task Becomes Available During Check

**Scenario**: Task completed between recording request and checking gridlock

**Detection**: Gridlock detected but immediately resolved

**Result**: Alert may not fire (cooldown or threshold not met)

### 4. All Tasks Done

**Scenario**: All tasks complete, agents still requesting

**Detection**: No gridlock (todo_tasks == 0)

**Result**: Agents get "no task available" without alert (expected)

## Troubleshooting

### Issue: False Positives (Gridlock when not gridlocked)

**Symptoms**: Alert fires but manual inspection shows available tasks

**Causes**:
1. Agent skill mismatch (tasks available but not for requesting agents)
2. Task just became available (timing issue)
3. Threshold too sensitive

**Solutions**:
```python
# Increase thresholds
detector = GridlockDetector(
    request_threshold=5,  # More requests needed
    time_window_minutes=10,  # Longer window
)

# Add skill-aware detection
def check_for_gridlock_with_skills(self, tasks, requesting_agents):
    # Check if tasks exist that ANY requesting agent can do
    available_for_any = any(
        agent.can_do(task)
        for agent in requesting_agents
        for task in todo_tasks
    )
    if available_for_any:
        return {"is_gridlock": False}
```

### Issue: False Negatives (Missed gridlock)

**Symptoms**: Project stalled but no alert

**Causes**:
1. Agents not requesting frequently enough
2. Threshold too high
3. Alert cooldown suppressing repeat alerts

**Solutions**:
```python
# Decrease thresholds
detector = GridlockDetector(
    request_threshold=2,  # Fewer requests needed
    time_window_minutes=3,  # Shorter window
)

# Check cooldown status
stats = detector.get_statistics()
if stats["last_alert"]:
    print(f"Last alert: {stats['last_alert']}")
    print(f"Cooldown: {stats['alert_cooldown_minutes']} min")
```

### Issue: Alert Spam

**Symptoms**: Same gridlock alert every 11 minutes

**Cause**: Gridlock persists, cooldown expires, alert fires again

**Solutions**:
```python
# Longer cooldown
detector = GridlockDetector(
    alert_cooldown_minutes=30,  # 30 min between alerts
)

# Or fix the underlying gridlock!
```

## Related Systems

- **Task Graph Auto-Fix System**: Prevents circular dependencies that cause gridlock
- **Assignment Lease System**: Recovers stuck IN_PROGRESS tasks
- **Task Dependency System**: Core dependency tracking and validation
- **Project Diagnostics**: Tools to analyze and visualize gridlock situations

## References

- **Implementation**: `src/core/gridlock_detector.py`
- **Integration**: `src/marcus_mcp/server.py`, `src/marcus_mcp/tools/task.py`
- **Commit**: 20f56fc - feat(critical-fixes): add gridlock detection
- **Related**: Task Graph Auto-Fix System, Assignment Lease System
