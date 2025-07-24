# 41. Assignment Monitor System

## Executive Summary

The Assignment Monitor System is a real-time task assignment consistency checker that prevents workers from being stuck with reverted or reassigned tasks. It continuously monitors the state of task assignments between Marcus's internal persistence layer and the Kanban board, detecting and resolving discrepancies to ensure agents always work on valid, properly assigned tasks.

## System Architecture

### Core Components

The Assignment Monitor consists of three primary components:

```
Assignment Monitor Architecture
├── assignment_monitor.py (Core Monitoring)
│   ├── AssignmentMonitor (Main monitor class)
│   ├── Reversion Detection (State change detection)
│   ├── Monitoring Loop (Continuous checking)
│   └── Statistics Tracking (Monitor health)
├── assignment_health_checker.py (Health Analysis)
│   ├── AssignmentHealthChecker (Health assessment)
│   ├── Orphan Detection (Persistence vs Kanban)
│   ├── Issue Reporting (Health issues)
│   └── Metrics Collection (System metrics)
└── assignment_reconciliation.py (Conflict Resolution)
    ├── AssignmentReconciler (Sync resolution)
    ├── State Synchronization (Board alignment)
    └── Cleanup Operations (Orphan removal)
```

### Monitoring Flow

```
Start Monitor
     │
     ▼
Load Assignments ◄─────┐
     │                 │
     ▼                 │
Get Board State        │ (Every 30 seconds)
     │                 │
     ▼                 │
Compare States         │
     │                 │
     ├── Match ────────┘
     │
     └── Mismatch
         │
         ▼
     Detect Type
         │
         ├── Task Reverted → Remove Assignment
         ├── Task Reassigned → Update Records
         ├── Task Missing → Clean Up
         └── Task Blocked → Handle Appropriately
```

## Core Functionality

### 1. Reversion Detection

The monitor detects several types of task state reversions:

```python
async def _detect_reversion(self, task: Task, worker_id: str) -> bool:
    """
    Detect if a task has been reverted from its expected state.

    Detection Cases:
    1. Task reverted to TODO status
    2. Task reassigned to different worker
    3. Task completed by someone else
    4. Task blocked and unassigned
    """
    task_id = task.id

    # Case 1: Task went back to TODO
    if task.status == TaskStatus.TODO:
        logger.info(f"Task {task_id} reverted to TODO status")
        return True

    # Case 2: Task is IN_PROGRESS but assigned to different worker
    if task.status == TaskStatus.IN_PROGRESS and task.assigned_to != worker_id:
        logger.info(
            f"Task {task_id} reassigned from {worker_id} to {task.assigned_to}"
        )
        return True

    # Case 3: Task completed by someone else
    if task.status == TaskStatus.DONE and task.assigned_to != worker_id:
        logger.info(
            f"Task {task_id} completed by {task.assigned_to} instead of {worker_id}"
        )
        return True

    # Case 4: Task blocked but no longer assigned
    if task.status == TaskStatus.BLOCKED and not task.assigned_to:
        logger.info(f"Task {task_id} blocked and unassigned")
        return True

    return False
```

### 2. Monitoring Loop

Continuous background monitoring with configurable intervals:

```python
async def _monitor_loop(self):
    """Main monitoring loop."""
    while self._running:
        try:
            await self._check_for_reversions()
            await asyncio.sleep(self.check_interval)  # Default: 30 seconds
        except Exception as e:
            logger.error(f"Error in assignment monitor: {e}")
            await asyncio.sleep(self.check_interval)
```

### 3. Health Checking

Comprehensive health assessment of the assignment system:

```python
class AssignmentHealthChecker:
    async def check_assignment_health(self) -> Dict:
        """
        Performs comprehensive health check comparing:
        - Persisted assignments vs Kanban board state
        - Monitor operational status
        - Reversion frequency tracking
        - Orphaned assignments detection
        """
        health = {
            "healthy": True,
            "issues": [],
            "metrics": {},
            "timestamp": datetime.now().isoformat()
        }

        # Check for orphaned assignments
        persisted_task_ids = {a["task_id"] for a in persisted.values()}
        kanban_assigned_ids = {t.id for t in in_progress if t.assigned_to}

        # Tasks only in persistence (orphaned)
        orphaned_persisted = persisted_task_ids - kanban_assigned_ids
        if orphaned_persisted:
            health["healthy"] = False
            health["issues"].append({
                "type": "orphaned_assignments",
                "description": f"{len(orphaned_persisted)} tasks in persistence but not assigned in kanban",
                "task_ids": list(orphaned_persisted)
            })
```

## Key Features

### 1. Automatic Reversion Handling

When a reversion is detected, the monitor automatically:
- Removes the invalid assignment from persistence
- Logs the reversion for tracking
- Increments reversion counters for pattern detection

### 2. Reversion Tracking

The system tracks how many times each task has reverted:

```python
# Track reversion count
self._reversion_count[task_id] = self._reversion_count.get(task_id, 0) + 1

# Flag problematic tasks
if self._reversion_count[task_id] >= 3:
    logger.error(
        f"Task {task_id} has reverted {self._reversion_count[task_id]} times! "
        "This task may have issues."
    )
```

### 3. Fallback Handling

The monitor gracefully handles different Kanban client implementations:

```python
try:
    all_tasks = await self.kanban_client.get_all_tasks()
except AttributeError as e:
    # Fallback for clients without get_all_tasks
    logger.warning(
        f"get_all_tasks not available on {type(self.kanban_client)}: {e}"
    )
    logger.warning(
        "Using get_available_tasks as fallback - health check will be limited"
    )
    all_tasks = await self.kanban_client.get_available_tasks()
```

## Integration with Marcus Ecosystem

### Assignment Persistence Integration

The monitor works closely with the AssignmentPersistence layer:

```python
class AssignmentMonitor:
    def __init__(
        self,
        persistence: AssignmentPersistence,
        kanban_client: KanbanInterface,
        check_interval: int = 30
    ):
        self.persistence = persistence
        self.kanban_client = kanban_client
        self.reconciler = AssignmentReconciler(persistence, kanban_client)
```

### Kanban Board Integration

Monitors all task state changes on the Kanban board:
- Fetches current board state every check interval
- Compares with persisted assignments
- Detects any discrepancies or state changes

### Monitoring System Integration

Provides statistics for the broader monitoring infrastructure:

```python
def get_monitoring_stats(self) -> Dict:
    """Get current monitoring statistics."""
    return {
        "monitoring": self._running,
        "check_interval": self.check_interval,
        "tracked_tasks": len(self._last_known_states),
        "reversion_counts": dict(self._reversion_count),
        "last_check": datetime.now().isoformat()
    }
```

## Why This System is Necessary

### Problem Scenarios

1. **Manual Board Changes**: Project managers might manually move tasks back to TODO
2. **Reassignments**: Tasks get reassigned to different agents through the UI
3. **System Glitches**: Network issues or race conditions cause state inconsistencies
4. **Abandoned Tasks**: Agents disconnect without properly releasing tasks

### Solution Benefits

1. **Consistency**: Ensures Marcus's view matches the actual board state
2. **Recovery**: Automatically recovers from state reversions
3. **Visibility**: Tracks patterns of problematic tasks
4. **Reliability**: Prevents agents from working on invalid assignments

## Configuration

The Assignment Monitor supports configurable parameters:

```python
AssignmentMonitor(
    persistence=persistence,
    kanban_client=kanban_client,
    check_interval=30  # Check every 30 seconds
)
```

### Tuning Guidelines

- **check_interval**: Balance between responsiveness and system load
  - Faster (10-20s): Quick reversion detection, higher load
  - Standard (30s): Good balance for most use cases
  - Slower (60s+): Lower load, delayed detection

## Monitoring and Alerts

### Key Metrics Tracked

1. **Reversion Frequency**: How often tasks revert state
2. **Orphaned Assignments**: Assignments without board tasks
3. **Untracked Assignments**: Board tasks without persistence
4. **Monitor Health**: Is the monitor running properly

### Alert Conditions

- Task reverted 3+ times (indicates systemic issue)
- Monitor stopped running
- High number of orphaned assignments
- Reconciliation failures

## Future Enhancements

### Short-term Improvements

1. **Predictive Reversion Detection**: Use patterns to predict likely reversions
2. **Adaptive Check Intervals**: Increase frequency during high activity
3. **Enhanced Notifications**: Direct agent notifications on reversions
4. **Reversion Analytics**: Detailed reporting on reversion patterns

### Long-term Vision

1. **Machine Learning Integration**: Learn reversion patterns per project type
2. **Preventive Actions**: Automatically prevent problematic assignments
3. **Cross-Board Monitoring**: Monitor multiple boards simultaneously
4. **Integration with Lease System**: Coordinate with assignment leases

## Conclusion

The Assignment Monitor System provides critical consistency checking between Marcus's internal state and the actual Kanban board state. By continuously monitoring for reversions and automatically handling discrepancies, it ensures that agents always work on valid, properly assigned tasks. This real-time monitoring and automatic recovery mechanism is essential for maintaining system reliability in the face of manual interventions and system glitches.
