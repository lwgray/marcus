# 35. Assignment Lease System

## Executive Summary

The Assignment Lease System is a sophisticated task ownership management framework that prevents duplicate work, ensures clean handoffs, and maintains task assignment integrity in Marcus's multi-agent environment. It implements a time-based lease mechanism similar to distributed lock systems, ensuring that only one agent can work on a task at any given time while providing automatic recovery for abandoned tasks.

## System Architecture

### Core Components

The Assignment Lease System consists of three primary modules:

```
Assignment Lease System Architecture
├── lease_manager.py (Core Lease Management)
│   ├── LeaseManager (Central lease coordinator)
│   ├── TaskLease (Lease data structure)
│   ├── LeaseStatus (Enumeration of states)
│   └── LeaseConfiguration (System parameters)
├── lease_monitor.py (Health and Recovery)
│   ├── LeaseMonitor (Background monitoring)
│   ├── ExpirationHandler (Automatic lease recovery)
│   ├── HeartbeatTracker (Agent liveness detection)
│   └── LeaseAnalytics (Performance metrics)
└── lease_integration.py (System Integration)
    ├── KanbanLeaseAdapter (Board synchronization)
    ├── AgentLeaseInterface (Agent-side API)
    ├── EventLeasePublisher (Event system integration)
    └── PersistenceLeaseStore (Durable storage)
```

### Lease Lifecycle

```
Task Available
     │
     ▼
Agent Requests Task
     │
     ▼
Lease Acquisition ──────► Lease Created (30 min default)
     │                         │
     ▼                         ▼
Agent Works            Heartbeat Updates (every 5 min)
     │                         │
     ├─────────────────────────┤
     │                         │
     ▼                         ▼
Task Complete           Lease Expired
     │                         │
     ▼                         ▼
Lease Released          Task Re-available
```

## Core Components

### 1. Lease Manager

The central coordinator for all lease operations:

```python
class LeaseManager:
    def __init__(self, config: LeaseConfiguration):
        self.config = config
        self.active_leases: Dict[str, TaskLease] = {}
        self.lease_history: List[LeaseEvent] = []
        self.lock = asyncio.Lock()

    async def acquire_lease(
        self,
        task_id: str,
        agent_id: str,
        duration_minutes: int = 30
    ) -> Optional[TaskLease]:
        """Attempt to acquire exclusive lease on task"""
        async with self.lock:
            if task_id in self.active_leases:
                existing = self.active_leases[task_id]
                if not existing.is_expired():
                    return None  # Already leased

            lease = TaskLease(
                task_id=task_id,
                agent_id=agent_id,
                acquired_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=duration_minutes),
                status=LeaseStatus.ACTIVE
            )

            self.active_leases[task_id] = lease
            await self._persist_lease(lease)
            await self._publish_lease_event("acquired", lease)

            return lease
```

### 2. Lease Data Structure

```python
@dataclass
class TaskLease:
    task_id: str
    agent_id: str
    acquired_at: datetime
    expires_at: datetime
    last_heartbeat: datetime
    status: LeaseStatus
    renewal_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def time_remaining(self) -> timedelta:
        return self.expires_at - datetime.utcnow()

    def is_healthy(self) -> bool:
        # Lease is healthy if heartbeat received within threshold
        heartbeat_threshold = timedelta(minutes=10)
        return datetime.utcnow() - self.last_heartbeat < heartbeat_threshold
```

### 3. Lease Monitoring

Background monitoring for lease health and automatic recovery:

```python
class LeaseMonitor:
    def __init__(self, lease_manager: LeaseManager):
        self.lease_manager = lease_manager
        self.monitoring_interval = 60  # seconds
        self._running = False

    async def start_monitoring(self):
        self._running = True
        while self._running:
            try:
                await self._check_expired_leases()
                await self._check_unhealthy_leases()
                await self._collect_metrics()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Lease monitoring error: {e}")

    async def _check_expired_leases(self):
        """Automatically release expired leases"""
        expired = []
        for task_id, lease in self.lease_manager.active_leases.items():
            if lease.is_expired():
                expired.append(task_id)

        for task_id in expired:
            await self.lease_manager.force_release(
                task_id,
                reason="Lease expired"
            )
```

## Integration with Marcus Ecosystem

### Workflow Integration Points

The Assignment Lease System integrates at critical workflow stages:

1. **request_next_task**: Acquires lease before task assignment
2. **report_progress**: Updates lease heartbeat
3. **report_blocker**: May extend lease duration
4. **finish_task**: Releases lease on completion
5. **agent_disconnect**: Handles lease cleanup for disconnected agents

### Event System Integration

The system publishes lease lifecycle events:

```python
LEASE_EVENTS = {
    "LEASE_ACQUIRED": "Agent acquired task lease",
    "LEASE_RENEWED": "Lease duration extended",
    "LEASE_RELEASED": "Lease released normally",
    "LEASE_EXPIRED": "Lease expired without renewal",
    "LEASE_FORCED_RELEASE": "Lease forcibly released",
    "LEASE_HEARTBEAT": "Lease heartbeat received"
}
```

### Kanban Board Synchronization

Lease status is reflected on the Kanban board:

```python
class KanbanLeaseAdapter:
    async def sync_lease_to_board(self, lease: TaskLease):
        """Update task card with lease information"""
        metadata = {
            "assigned_to": lease.agent_id,
            "lease_expires": lease.expires_at.isoformat(),
            "lease_healthy": lease.is_healthy(),
            "assignment_locked": True
        }

        await self.kanban_client.update_task_metadata(
            lease.task_id,
            metadata
        )
```

## Key Features

### 1. Automatic Lease Extension

Agents can request lease extensions when needed:

```python
async def extend_lease(
    self,
    task_id: str,
    agent_id: str,
    additional_minutes: int = 30
) -> bool:
    """Extend existing lease duration"""
    lease = self.active_leases.get(task_id)

    if not lease or lease.agent_id != agent_id:
        return False

    if lease.renewal_count >= self.config.max_renewals:
        logger.warning(f"Max renewals reached for task {task_id}")
        return False

    lease.expires_at += timedelta(minutes=additional_minutes)
    lease.renewal_count += 1

    await self._publish_lease_event("renewed", lease)
    return True
```

### 2. Forced Release Mechanism

Administrators can force-release stuck leases:

```python
async def force_release(
    self,
    task_id: str,
    reason: str,
    admin_id: Optional[str] = None
) -> bool:
    """Forcibly release a lease"""
    if task_id not in self.active_leases:
        return False

    lease = self.active_leases[task_id]
    lease.status = LeaseStatus.FORCE_RELEASED

    # Notify the agent
    await self._notify_agent_lease_revoked(
        lease.agent_id,
        task_id,
        reason
    )

    # Clean up
    del self.active_leases[task_id]

    # Audit trail
    await self._record_force_release(lease, reason, admin_id)

    return True
```

### 3. Lease Analytics

Track lease performance and patterns:

```python
class LeaseAnalytics:
    def calculate_metrics(self, lease_history: List[LeaseEvent]) -> Dict:
        return {
            "average_lease_duration": self._avg_duration(lease_history),
            "renewal_rate": self._renewal_percentage(lease_history),
            "expiration_rate": self._expiration_percentage(lease_history),
            "agent_lease_distribution": self._agent_distribution(lease_history),
            "peak_lease_hours": self._peak_usage_hours(lease_history),
            "stuck_lease_count": self._count_stuck_leases(lease_history)
        }
```

### 4. Heartbeat System

Keep-alive mechanism for active leases:

```python
class HeartbeatTracker:
    async def send_heartbeat(self, task_id: str, agent_id: str) -> bool:
        """Update lease heartbeat timestamp"""
        lease = self.lease_manager.get_active_lease(task_id)

        if not lease or lease.agent_id != agent_id:
            return False

        lease.last_heartbeat = datetime.utcnow()

        # Check if lease needs automatic extension
        if lease.time_remaining() < timedelta(minutes=10):
            await self.lease_manager.extend_lease(
                task_id,
                agent_id,
                additional_minutes=30
            )

        return True
```

## Configuration Options

### Lease Configuration Parameters

```python
@dataclass
class LeaseConfiguration:
    # Timing
    default_lease_duration_minutes: int = 30
    max_lease_duration_minutes: int = 240  # 4 hours
    heartbeat_interval_minutes: int = 5
    heartbeat_timeout_minutes: int = 10

    # Renewal
    max_renewals: int = 5
    auto_renew_threshold_minutes: int = 10

    # Monitoring
    monitor_interval_seconds: int = 60
    cleanup_expired_after_hours: int = 24

    # Recovery
    enable_auto_recovery: bool = True
    recovery_delay_minutes: int = 5

    # Persistence
    persist_lease_history: bool = True
    lease_history_retention_days: int = 30
```

## Pros and Cons

### Advantages

1. **Prevents Duplicate Work**: Ensures only one agent works on a task
2. **Automatic Recovery**: Handles agent failures gracefully
3. **Flexible Duration**: Supports extensions for long-running tasks
4. **Audit Trail**: Complete history of task assignments
5. **Performance Visibility**: Analytics on assignment patterns
6. **Clean Handoffs**: Explicit lease transfer mechanism
7. **Scalable**: Lock-free design for most operations

### Disadvantages

1. **Complexity**: Adds another layer to task management
2. **Overhead**: Heartbeat traffic and monitoring costs
3. **Time Pressure**: Agents must complete within lease window
4. **Recovery Delay**: Gap between expiration and reassignment
5. **Storage Requirements**: Lease history accumulation
6. **Clock Synchronization**: Requires accurate time across agents

## Why This Approach

The lease-based system was chosen for several key reasons:

1. **Distributed Systems Best Practice**: Proven pattern in distributed computing
2. **Failure Resilience**: Automatic handling of agent crashes
3. **Clear Ownership**: Unambiguous task assignment
4. **Flexibility**: Configurable timeouts and extensions
5. **Observability**: Rich metrics for optimization
6. **Integration-Friendly**: Works with existing Marcus components

## Complex Task Handling

### Long-Running Tasks

For tasks exceeding standard lease duration:

```python
class LongTaskLeaseStrategy:
    async def handle_long_task(self, task: Task, agent_id: str):
        # 1. Acquire initial lease with max duration
        lease = await acquire_lease(
            task.id,
            agent_id,
            duration_minutes=240  # 4 hours
        )

        # 2. Set up automatic renewal
        renewal_task = asyncio.create_task(
            self._auto_renew_lease(lease)
        )

        # 3. Monitor task progress
        progress_monitor = asyncio.create_task(
            self._monitor_progress(task, lease)
        )

        return lease, [renewal_task, progress_monitor]
```

### Multi-Agent Coordination

For tasks requiring multiple agents:

```python
class MultiAgentLeaseCoordinator:
    async def coordinate_multi_agent_task(
        self,
        task: Task,
        required_agents: List[str]
    ):
        # Parent lease for coordination
        parent_lease = await acquire_lease(
            f"{task.id}_coordinator",
            "system",
            duration_minutes=60
        )

        # Sub-leases for each agent
        sub_leases = []
        for agent_id in required_agents:
            sub_lease = await acquire_lease(
                f"{task.id}_{agent_id}",
                agent_id,
                duration_minutes=30
            )
            sub_leases.append(sub_lease)

        return parent_lease, sub_leases
```

## Future Evolution

### Short-term Enhancements

1. **Smart Lease Duration**: ML-based duration prediction
2. **Priority Leases**: High-priority tasks get extended leases
3. **Lease Trading**: Agents can transfer leases
4. **Batch Operations**: Acquire multiple leases atomically

### Long-term Vision

1. **Distributed Lease Storage**: Multi-region lease management
2. **Predictive Recovery**: Anticipate failures before expiration
3. **Dynamic Heartbeat**: Adjust frequency based on task criticality
4. **Lease Marketplace**: Agents bid for high-value task leases

## Monitoring and Alerts

### Key Metrics

1. **Lease Utilization**: Percentage of time tasks are leased
2. **Expiration Rate**: Leases expiring vs completing
3. **Renewal Frequency**: How often leases need extension
4. **Agent Efficiency**: Lease duration vs actual work time
5. **Recovery Time**: Duration from expiration to re-lease

### Alert Conditions

```python
LEASE_ALERTS = {
    "high_expiration_rate": "More than 20% of leases expiring",
    "stuck_leases": "Leases active but no heartbeat for 15+ minutes",
    "excessive_renewals": "Task renewed more than 5 times",
    "lease_starvation": "Agent unable to acquire leases for 30+ minutes",
    "system_overload": "More than 1000 active leases"
}
```

## Conclusion

The Assignment Lease System provides Marcus with a robust, distributed task ownership mechanism that prevents conflicts while ensuring work continuity. By implementing time-based leases with automatic monitoring and recovery, the system maintains task assignment integrity even in the face of agent failures or network issues.

The lease system's integration with Marcus's event system, Kanban boards, and monitoring infrastructure creates a comprehensive assignment management solution that scales with the number of agents and complexity of projects. As Marcus evolves toward more sophisticated multi-agent coordination, the Assignment Lease System provides the foundational ownership primitives necessary for reliable distributed task execution.
