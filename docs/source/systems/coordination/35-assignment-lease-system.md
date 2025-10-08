# 35. Assignment Lease System

## Executive Summary

The Assignment Lease System is a time-based task assignment management framework that ensures tasks are completed within reasonable timeframes and provides automatic recovery for abandoned or stuck tasks. It implements adaptive lease durations based on task complexity, priority, and agent performance history, with automatic renewal capabilities and configurable grace periods for handling transient issues.

## System Architecture

### Core Components

The Assignment Lease System consists of two primary modules:

```
Assignment Lease System Architecture
├── assignment_lease.py (Core Lease Management)
│   ├── AssignmentLease (Lease data model)
│   ├── AssignmentLeaseManager (Lease lifecycle management)
│   ├── LeaseMonitor (Expiration monitoring)
│   └── Adaptive Duration Calculation
└── Integration Points
    ├── Task Assignment (request_next_task)
    ├── Progress Reporting (report_progress)
    ├── Kanban Synchronization (update_task)
    └── Persistence Layer (lease storage)
```

### Lease Lifecycle

```
Task Available
     │
     ▼
Agent Requests Task
     │
     ▼
Lease Created ──────► Adaptive Duration (1-24 hrs)
     │                         │
     ▼                         ▼
Agent Works              Auto-Renewal on Progress
     │                         │
     ├─────────────────────────┤
     │                         │
     ▼                         ▼
Task Complete           Warning Threshold (30 min before expiry)
     │                         │
     ▼                         ▼
Lease Released          Grace Period (30 min)
                               │
                               ▼
                        Task Recovery
```

## Core Components

### 1. Lease Manager

The central coordinator with adaptive duration calculation:

```python
class AssignmentLeaseManager:
    def __init__(
        self,
        kanban_client: KanbanInterface,
        persistence: AssignmentPersistence,
        default_lease_hours: float = 2.0,
        max_renewals: int = 10,
        warning_threshold_hours: float = 0.5,
        priority_multipliers: Optional[Dict[str, float]] = None,
        complexity_multipliers: Optional[Dict[str, float]] = None,
        grace_period_minutes: int = 30,
        renewal_decay_factor: float = 0.9
    ):
        self.active_leases: Dict[str, AssignmentLease] = {}
        self._lock = asyncio.Lock()

    def calculate_adaptive_duration(self, task: Task) -> float:
        """Calculate lease duration based on task characteristics"""
        base_hours = self.default_lease_hours

        # Apply priority multiplier
        if hasattr(task, 'priority'):
            priority_mult = self.priority_multipliers.get(
                task.priority.value.lower(), 1.0
            )
            base_hours *= priority_mult

        # Apply complexity multiplier
        if hasattr(task, 'labels'):
            for label in task.labels:
                if label in self.complexity_multipliers:
                    base_hours *= self.complexity_multipliers[label]
                    break

        # Ensure within bounds
        return max(self.min_lease_hours,
                  min(base_hours, self.max_lease_hours))
```

### 2. Lease Data Structure

```python
@dataclass
class AssignmentLease:
    """Represents a time-bound assignment of a task to an agent"""
    task_id: str
    agent_id: str
    created_at: datetime
    expires_at: datetime
    duration_hours: float
    renewal_count: int = 0
    last_renewed_at: Optional[datetime] = None
    is_stuck: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if lease has expired"""
        return datetime.now() > self.expires_at

    def is_expiring_soon(self, threshold_hours: float = 0.5) -> bool:
        """Check if lease is close to expiration"""
        time_until_expiry = self.expires_at - datetime.now()
        return time_until_expiry.total_seconds() < threshold_hours * 3600

    def time_remaining(self) -> timedelta:
        """Get time remaining on lease"""
        return max(self.expires_at - datetime.now(), timedelta(0))
```

### 3. Lease Monitoring

Background monitoring with grace period support:

```python
class LeaseMonitor:
    """Monitors active leases and handles expirations"""

    def __init__(self, lease_manager: AssignmentLeaseManager):
        self.lease_manager = lease_manager
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self.check_interval = 60  # seconds

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._check_expiring_leases()
                await self._check_expired_leases()
                await self._detect_stuck_leases()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Lease monitor error: {e}")

    async def _check_expiring_leases(self):
        """Warn about leases approaching expiration"""
        async with self.lease_manager._lock:
            for task_id, lease in list(self.lease_manager.active_leases.items()):
                if lease.is_expiring_soon(self.lease_manager.warning_threshold_hours):
                    logger.warning(
                        f"Lease for task {task_id} expiring in "
                        f"{lease.time_remaining()}, assigned to {lease.agent_id}"
                    )
```

## Integration with Marcus Ecosystem

### Workflow Integration Points

The Assignment Lease System integrates at critical workflow stages:

1. **request_next_task**: Creates lease with adaptive duration on task assignment
2. **report_progress**: Automatically renews lease with decay factor
3. **task completion**: Releases lease when task status changes to DONE
4. **lease expiration**: Triggers task recovery after grace period
5. **ping health command**: Reports lease statistics and orphaned assignments

### Persistence Integration

Leases are stored in the persistence layer for recovery:

```python
# Lease persistence structure
{
    "task_id": "task-123",
    "agent_id": "agent-001",
    "lease": {
        "created_at": "2024-01-20T10:00:00",
        "expires_at": "2024-01-20T12:00:00",
        "duration_hours": 2.0,
        "renewal_count": 1,
        "last_renewed_at": "2024-01-20T11:30:00"
    }
}
```

### Kanban Board Recovery

Expired leases trigger task status updates:

```python
async def recover_task(self, task_id: str, lease: AssignmentLease):
    """Recover task when lease expires"""
    try:
        # Update task status back to TODO
        await self.kanban_client.update_task(
            task_id,
            {"status": "TODO", "assigned_to": None}
        )

        # Clean up persistence
        assignments = await self.persistence.load_assignments()
        for agent_id, assignment in assignments.items():
            if assignment["task_id"] == task_id:
                await self.persistence.remove_assignment(agent_id)
                break

        logger.info(f"Recovered task {task_id} from expired lease")

    except Exception as e:
        logger.error(f"Failed to recover task {task_id}: {e}")
```

## Key Features

### 1. Automatic Lease Renewal

Leases are automatically renewed on progress reports with decay:

```python
async def renew_lease(self, task_id: str, agent_id: str) -> bool:
    """Renew lease with decay factor"""
    lease = self.active_leases.get(task_id)
    if not lease or lease.agent_id != agent_id:
        return False

    if lease.renewal_count >= self.max_renewals:
        lease.is_stuck = True
        logger.warning(
            f"Task {task_id} reached max renewals ({self.max_renewals}), "
            f"marking as stuck"
        )
        return False

    # Calculate new duration with decay
    decay_factor = self.renewal_decay_factor ** lease.renewal_count
    new_duration_hours = lease.duration_hours * decay_factor
    new_duration_hours = max(self.min_lease_hours, new_duration_hours)

    # Extend expiration
    lease.expires_at = datetime.now() + timedelta(hours=new_duration_hours)
    lease.renewal_count += 1
    lease.last_renewed_at = datetime.now()

    # Persist renewal
    await self._persist_lease(task_id, lease)

    logger.info(
        f"Renewed lease for task {task_id}, agent {agent_id}: "
        f"{new_duration_hours:.1f} hours (renewal #{lease.renewal_count})"
    )
    return True
```

### 2. Grace Period Handling

Tasks get a grace period before recovery:

```python
async def handle_expired_lease(self, task_id: str, lease: AssignmentLease):
    """Handle expired lease with grace period"""
    grace_period_end = lease.expires_at + timedelta(
        minutes=self.grace_period_minutes
    )

    if datetime.now() < grace_period_end:
        # Still in grace period
        logger.info(
            f"Task {task_id} in grace period, expires at {grace_period_end}"
        )
        return

    # Grace period exceeded - recover task
    logger.warning(
        f"Task {task_id} lease expired and grace period exceeded, "
        f"recovering task from agent {lease.agent_id}"
    )

    await self.recover_task(task_id, lease)

    # Remove lease
    async with self._lock:
        del self.active_leases[task_id]
        await self._remove_persisted_lease(task_id)
```

### 3. Stuck Task Detection

Identify tasks that aren't progressing:

```python
async def _detect_stuck_leases(self):
    """Detect leases with too many renewals"""
    async with self.lease_manager._lock:
        stuck_count = 0
        for task_id, lease in self.lease_manager.active_leases.items():
            if lease.renewal_count >= self.lease_manager.stuck_task_threshold_renewals:
                if not lease.is_stuck:
                    lease.is_stuck = True
                    stuck_count += 1
                    logger.warning(
                        f"Task {task_id} marked as stuck after "
                        f"{lease.renewal_count} renewals"
                    )

        if stuck_count > 0:
            logger.info(f"Detected {stuck_count} new stuck tasks")
```

### 4. Lease Statistics

Track lease system health:

```python
def get_statistics(self) -> Dict[str, Any]:
    """Get current lease statistics"""
    active_leases = list(self.active_leases.values())

    stats = {
        "total_active_leases": len(active_leases),
        "expiring_soon": sum(
            1 for lease in active_leases
            if lease.is_expiring_soon(self.warning_threshold_hours)
        ),
        "expired": sum(1 for lease in active_leases if lease.is_expired()),
        "stuck_tasks": sum(1 for lease in active_leases if lease.is_stuck),
        "average_renewal_count": (
            sum(lease.renewal_count for lease in active_leases) /
            len(active_leases) if active_leases else 0
        ),
        "max_renewal_count": (
            max(lease.renewal_count for lease in active_leases)
            if active_leases else 0
        )
    }

    return stats
```

## Configuration Options

### Project-Specific Configuration

Leases can be configured per project in `config_marcus.json`:

```json
{
  "task_lease": {
    "default_hours": 2.0,
    "max_renewals": 10,
    "warning_hours": 0.5,
    "grace_period_minutes": 30,
    "renewal_decay_factor": 0.9,
    "min_lease_hours": 1.0,
    "max_lease_hours": 24.0,
    "stuck_threshold_renewals": 5,
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

## Pros and Cons

### Advantages

1. **Adaptive Duration**: Lease time adjusts to task complexity and priority
2. **Automatic Recovery**: Tasks recovered after lease expiration + grace period
3. **Progress-Based Renewal**: Automatic extension when agents report progress
4. **Stuck Detection**: Identifies tasks not progressing after many renewals
5. **Configurable**: Per-project configuration for different workflows
6. **Graceful Degradation**: Grace periods handle temporary network issues
7. **Integration**: Works seamlessly with existing Marcus components

### Disadvantages

1. **Time Pressure**: Agents must work within lease windows
2. **Monitoring Overhead**: Continuous lease checking every 60 seconds
3. **Recovery Delay**: Grace period delays task reassignment
4. **Configuration Complexity**: Many parameters to tune correctly
5. **False Positives**: May mark active tasks as stuck
6. **Memory Usage**: All active leases kept in memory

## Why This Approach

The adaptive lease system was chosen to address key challenges:

1. **Agent Timeouts**: When agents disconnect, tasks get stuck in progress
2. **Variable Task Complexity**: Different tasks need different time allocations
3. **Network Reliability**: Grace periods handle transient connection issues
4. **Progress Tracking**: Renewal on progress shows active work
5. **Resource Optimization**: Prevents tasks from being held indefinitely
6. **Operational Visibility**: Clear metrics on task assignment health

## Task-Specific Adaptations

### Priority-Based Leasing

Critical tasks get shorter leases for faster turnover:

```python
# Priority multipliers
"priority_multipliers": {
    "critical": 0.5,   # 1 hour for 2-hour default
    "high": 0.75,      # 1.5 hours
    "medium": 1.0,     # 2 hours (default)
    "low": 1.5         # 3 hours
}
```

### Complexity-Based Leasing

Complex tasks get extended time:

```python
# Complexity multipliers based on labels
"complexity_multipliers": {
    "complex": 2.0,    # 4 hours for 2-hour default
    "large": 1.5,      # 3 hours
    "simple": 0.75,    # 1.5 hours
    "tiny": 0.5        # 1 hour
}
```

### Renewal Decay

Each renewal gets progressively shorter time:

```python
# With decay factor 0.9:
# Initial: 2 hours
# Renewal 1: 1.8 hours
# Renewal 2: 1.62 hours
# Renewal 3: 1.46 hours
# ...
# Renewal 10: 0.78 hours (minimum 1 hour enforced)
```

## Real-World Usage

### Example: Task Assignment with Lease

```python
# In request_next_task tool
if optimal_task and agent_id:
    # Create lease for this assignment
    if hasattr(state, 'lease_manager') and state.lease_manager:
        lease = await state.lease_manager.create_lease(
            optimal_task.id,
            agent_id,
            optimal_task
        )

        if lease:
            logger.info(
                f"Created lease for task {optimal_task.id}: "
                f"{lease.duration_hours:.1f} hours"
            )
```

### Example: Progress Report with Renewal

```python
# In report_progress tool
if hasattr(state, 'lease_manager') and state.lease_manager:
    renewed = await state.lease_manager.renew_lease(task_id, agent_id)
    if renewed:
        lease = state.lease_manager.get_active_lease(task_id)
        logger.info(
            f"Renewed lease for task {task_id}, "
            f"expires at {lease.expires_at}"
        )
```

## Monitoring via Ping Tool

### Health Check Output

```bash
$ ping marcus health

🏥 Marcus Health Status
=======================

📊 Lease Statistics:
• Active leases: 5
• Expiring soon: 1
• Expired: 0
• Stuck tasks: 0
• Average renewals: 2.4
• Max renewals: 4

⚠️  Warnings:
• Task task-123 expiring in 25 minutes
• 1 orphaned assignment detected
```

### Cleanup Command

```bash
$ ping marcus cleanup

🧹 Cleanup Results:
• Cleared 2 stuck assignments
• Removed 1 orphaned lease
• Reset 3 tasks to TODO status
```

## Related Systems

- **Gridlock Detection System**: Detects when projects are stalled due to all tasks being blocked
- **Task Graph Auto-Fix System**: Prevents and resolves circular dependencies
- **Orphan Task Recovery System**: Handles tasks without proper ownership
- **Task Dependency System**: Core dependency tracking and validation

## Conclusion

The Assignment Lease System provides Marcus with adaptive time-based task management that prevents tasks from being stuck indefinitely when agents disconnect or fail. By implementing intelligent lease durations based on task characteristics, automatic renewal with decay, and graceful recovery with configurable grace periods, the system ensures reliable task completion while accommodating varying task complexities and network conditions.

The integration with Marcus's task assignment workflow, progress reporting, and monitoring systems creates a self-managing task ownership solution that requires minimal manual intervention. The system's configurability allows different projects to tune lease parameters to their specific needs, making it suitable for both rapid development cycles and long-running complex tasks.
