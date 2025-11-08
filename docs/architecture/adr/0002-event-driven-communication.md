# ADR 0002: Event-Driven Communication Between Components

**Status:** Accepted

**Date:** 2024-11 (Initial Implementation)

**Deciders:** Marcus Core Team

---

## Context

Marcus coordinates multiple agents working on tasks across different projects. Components need to communicate about:
- Task state changes (created, assigned, completed, failed)
- Agent activity (registered, task started, progress updates)
- Project state changes (new project, state snapshot)
- System events (errors, warnings, health checks)

### Requirements

1. **Loose Coupling:** Components should not directly depend on each other
2. **Audit Trail:** All significant events must be tracked for debugging and analysis
3. **Extensibility:** New event consumers should be easy to add
4. **Asynchronous:** Event processing should not block critical operations
5. **Reliability:** Events should not be lost, especially for critical operations
6. **History:** Need to query past events for post-project analysis

### Problems with Direct Coupling

```python
# ❌ Tight coupling - bad
class TaskManager:
    def complete_task(self, task_id):
        task.status = "completed"
        self.kanban_sync.update_card(task_id)  # Direct dependency
        self.metrics.record_completion(task_id)  # Direct dependency
        self.notification.send(task_id)  # Direct dependency
```

This approach:
- Creates tight coupling between components
- Makes testing difficult (must mock all dependencies)
- Makes adding new features require changes to existing code
- Violates Open/Closed Principle

---

## Decision

We will implement an **Event-Driven Architecture** using a publish/subscribe pattern with the following characteristics:

### Event System Design

1. **Central Event Bus** (`src/core/events.py`)
   - In-memory event distribution
   - Async event handlers
   - Optional event persistence for audit trail

2. **Domain Events** (defined in domain layer)
   - Immutable event objects
   - Rich event data (timestamp, context, metadata)
   - Type-safe with Python dataclasses

3. **Event Subscribers** (any layer)
   - Register handlers for specific event types
   - Multiple subscribers per event type
   - Async event processing

4. **Event History** (optional persistence)
   - SQLite storage for queryable history
   - JSON file backup for portability
   - Used for post-project analysis

### Event Pattern

```python
# ✅ Event-driven - good
class TaskManager:
    def complete_task(self, task_id):
        task.status = "completed"
        await self.event_bus.publish(
            TaskCompleted(
                task_id=task_id,
                timestamp=datetime.now(),
                agent_id=task.assigned_agent,
                project_id=task.project_id
            )
        )
        # That's it! Subscribers handle the rest

# Separate subscribers
class KanbanSync:
    async def on_task_completed(self, event: TaskCompleted):
        await self.update_card(event.task_id)

class MetricsCollector:
    async def on_task_completed(self, event: TaskCompleted):
        await self.record_completion(event)
```

### Event Types

```python
# Domain Events
@dataclass
class TaskCreated(Event):
    task_id: str
    title: str
    project_id: str
    priority: int
    dependencies: list[str]

@dataclass
class TaskAssigned(Event):
    task_id: str
    agent_id: str
    lease_expiry: datetime

@dataclass
class TaskCompleted(Event):
    task_id: str
    agent_id: str
    duration_seconds: float

@dataclass
class ProjectStateChanged(Event):
    project_id: str
    state_snapshot: ProjectState
    trigger: str  # "manual", "schedule", "completion"
```

---

## Consequences

### Positive

✅ **Loose Coupling**
- Components don't know about each other
- Easy to add/remove event subscribers
- Better testability

✅ **Audit Trail**
- All events automatically logged
- Complete history of system behavior
- Invaluable for debugging and analysis

✅ **Extensibility**
- New features subscribe to existing events
- No changes to event publishers
- Open/Closed Principle

✅ **Async Processing**
- Event handlers run asynchronously
- Non-blocking event distribution
- Better performance

✅ **Post-Project Analysis**
- Event history enables powerful analysis
- Can reconstruct project timeline
- Identify bottlenecks and patterns

✅ **Multiple Consumers**
- One event, many handlers
- Metrics, logging, Kanban sync all independent
- Easy to add new consumers

### Negative

⚠️ **Debugging Complexity**
- Event flow less obvious than direct calls
- Need good tooling to trace event chains
- Mitigation: Event logging with correlation IDs

⚠️ **Potential Performance Overhead**
- Event serialization and distribution
- Multiple handlers per event
- Mitigation: Async processing, batching

⚠️ **Event Ordering**
- No guaranteed order across event types
- Can cause race conditions
- Mitigation: Use timestamps, idempotent handlers

⚠️ **Error Handling**
- One handler failure shouldn't affect others
- Need isolated error handling per subscriber
- Mitigation: Try/except in event bus

⚠️ **Storage Growth**
- Event history grows over time
- Need retention policies
- Mitigation: Configurable retention, archiving

---

## Implementation Details

### Event Bus (`src/core/events.py`)

```python
class EventBus:
    """
    Central event distribution system.

    Supports:
    - Async event handlers
    - Multiple subscribers per event type
    - Optional event persistence
    - Event history queries
    """

    def __init__(self, persist: bool = True):
        self._handlers: dict[type, list[Callable]] = {}
        self._persist = persist
        self._history: list[Event] = []

    async def publish(self, event: Event) -> None:
        """Publish event to all subscribers"""
        # Log event
        logger.debug(f"Publishing {type(event).__name__}: {event}")

        # Persist if enabled
        if self._persist:
            await self._store_event(event)

        # Notify subscribers
        event_type = type(event)
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Event handler failed: {e}")
                    # Don't let one handler failure affect others

    def subscribe(
        self,
        event_type: type[Event],
        handler: Callable[[Event], Awaitable[None]]
    ) -> None:
        """Subscribe to event type"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
```

### Event Subscribers

```python
# Kanban Sync Subscriber
class KanbanSyncSubscriber:
    def __init__(self, event_bus: EventBus, kanban: KanbanProvider):
        self.kanban = kanban
        event_bus.subscribe(TaskCreated, self.on_task_created)
        event_bus.subscribe(TaskCompleted, self.on_task_completed)

    async def on_task_created(self, event: TaskCreated):
        await self.kanban.create_card(
            title=event.title,
            task_id=event.task_id
        )

    async def on_task_completed(self, event: TaskCompleted):
        await self.kanban.move_card(
            task_id=event.task_id,
            list_name="Done"
        )

# Metrics Collector Subscriber
class MetricsSubscriber:
    def __init__(self, event_bus: EventBus):
        event_bus.subscribe(TaskCompleted, self.on_task_completed)
        event_bus.subscribe(TaskAssigned, self.on_task_assigned)

    async def on_task_completed(self, event: TaskCompleted):
        await record_metric(
            "task.completion_time",
            event.duration_seconds,
            tags={"agent": event.agent_id}
        )
```

### Event Persistence

Events are persisted to SQLite for querying:

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    project_id TEXT,
    agent_id TEXT,
    task_id TEXT,
    payload JSON NOT NULL,
    correlation_id TEXT
);

CREATE INDEX idx_events_project_id ON events(project_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_type ON events(event_type);
```

---

## Alternatives Considered

### 1. Message Queue (RabbitMQ, Redis)
**Rejected** because:
- Adds external dependency and operational complexity
- Overkill for current scale (single process)
- In-memory event bus is sufficient
- All agents run in same process

**When to Reconsider:**
- Distributed agent architecture
- Need guaranteed delivery
- Cross-process communication

### 2. Direct Method Calls
**Rejected** because:
- Creates tight coupling
- Hard to test
- Violates Open/Closed Principle
- Makes adding features difficult

### 3. Observer Pattern (Callbacks)
**Partially Adopted:**
- Event system IS observer pattern
- But with richer event objects
- And centralized bus for management

**Why Enhanced:**
- Centralized subscription management
- Better event history/audit trail
- Type-safe event objects

### 4. CQRS (Command Query Responsibility Segregation)
**Not Needed** because:
- Read/write separation not required
- Single database is sufficient
- Would add unnecessary complexity

**When to Reconsider:**
- Performance bottlenecks in reads vs writes
- Need different consistency models
- Separate read/write scaling

---

## Usage Guidelines

### When to Use Events

✅ **Use Events For:**
- State changes (task created, agent registered)
- Cross-boundary communication (domain → integration)
- Audit trail requirements
- Multiple consumers of same information
- Decoupling components

❌ **Don't Use Events For:**
- Synchronous operations requiring immediate response
- Simple getter/setter operations
- Performance-critical tight loops
- Within a single class

### Event Design Principles

1. **Events are Immutable:** Once created, never changed
2. **Events are Past Tense:** TaskCompleted, not CompleteTask
3. **Events are Rich:** Include all relevant context
4. **Events are Versioned:** Plan for schema evolution

---

## Related Decisions

- [ADR-0001: Layered Architecture with DDD](./0001-layered-architecture-with-ddd.md)
- [ADR-0004: Async-First Design](./0004-async-first-design.md)
- [ADR-0009: Post-Project Analysis System](./0009-post-project-analysis.md)

---

## References

- [Event-Driven Architecture](https://martinfowler.com/articles/201701-event-driven.html)
- [Domain Events Pattern](https://docs.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/domain-events-design-implementation)

---

## Notes

The event system has proven invaluable for:
- Post-project analysis (reconstructing project history)
- Debugging (tracing event chains)
- Adding new features without modifying core code
- Maintaining loose coupling as system grows

Event persistence overhead is minimal (~5% performance impact) and provides massive value for analysis and debugging.
