# Marcus Event-Driven Architecture System

## Overview

The Event-Driven Architecture system provides the foundational communication backbone for the Marcus project management platform. It implements a robust publish-subscribe pattern that enables loose coupling between system components while maintaining reliable message delivery and persistence.

## System Architecture

### Core Components

#### Event Data Structure
```python
@dataclass
class Event:
    event_id: str           # Unique identifier with timestamp
    timestamp: datetime     # When the event occurred
    event_type: str        # Categorized event type
    source: str            # Origin of the event
    data: Dict[str, Any]   # Event payload
    metadata: Optional[Dict[str, Any]]  # Additional context
```

#### Events System Class
The `Events` class provides:
- **Publisher/Subscriber Management**: Dynamic subscription and unsubscription
- **Async Event Handling**: Non-blocking event processing
- **Error Isolation**: Subscriber failures don't affect other subscribers
- **Optional Persistence**: Events can be stored to disk for replay/analysis
- **History Management**: In-memory event history with configurable limits
- **Performance Optimization**: Fire-and-forget vs wait-for-completion options

### Technical Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Event Source  │────▶│   Events System  │────▶│   Subscribers   │
│                 │     │                  │     │                 │
│ - Marcus Core   │     │ - Pub/Sub Router │     │ - Task Manager  │
│ - Agents        │     │ - History Store  │     │ - Context Sys   │
│ - Kanban        │     │ - Persistence    │     │ - Monitoring    │
│ - UI Updates    │     │ - Error Handler  │     │ - Notifications │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Persistence   │
                        │   (Optional)    │
                        └─────────────────┘
```

## Marcus Ecosystem Integration

### Position in Architecture
The Event system serves as the **nervous system** of Marcus, sitting at the core of all major subsystems:

1. **Task Management**: Events coordinate task assignment, progress, and completion
2. **Context System**: Events propagate context updates and dependency changes
3. **Agent Management**: Events handle agent registration, status, and skill updates
4. **Kanban Integration**: Events synchronize with external project boards
5. **Memory System**: Events feed learning and prediction algorithms
6. **UI Updates**: Events drive real-time dashboard updates

### Workflow Integration Points

In the typical Marcus workflow, events are fired at every critical juncture:

```
create_project → PROJECT_CREATED event
     ↓
register_agent → AGENT_REGISTERED event
     ↓
request_next_task → TASK_REQUESTED → TASK_ASSIGNED events
     ↓
agent_work → TASK_STARTED → TASK_PROGRESS events
     ↓
report_progress → TASK_PROGRESS events (multiple)
     ↓
report_blocker → TASK_BLOCKED → BLOCKER_RESOLVED events
     ↓
finish_task → TASK_COMPLETED event
```

## Event Types and Categories

### Task Lifecycle Events
- `TASK_REQUESTED`: Agent requests work
- `TASK_ASSIGNED`: Marcus assigns specific task
- `TASK_STARTED`: Agent begins work
- `TASK_PROGRESS`: Periodic progress updates
- `TASK_COMPLETED`: Task finished successfully
- `TASK_BLOCKED`: Agent encounters blocker
- `BLOCKER_RESOLVED`: Blocker resolved via AI suggestions

### Agent Lifecycle Events
- `AGENT_REGISTERED`: New agent joins system
- `AGENT_STATUS_CHANGED`: Agent availability changes
- `AGENT_SKILL_UPDATED`: Agent capabilities modified

### Context and Intelligence Events
- `CONTEXT_UPDATED`: Context system learns new information
- `DEPENDENCY_DETECTED`: New task dependencies discovered
- `IMPLEMENTATION_FOUND`: Code/API patterns detected
- `DECISION_LOGGED`: Architectural decisions recorded
- `PATTERN_DETECTED`: Code patterns identified
- `PREDICTION_MADE`: AI predictions generated
- `AGENT_LEARNED`: Learning system updates

### System Events
- `SYSTEM_STARTUP`/`SYSTEM_SHUTDOWN`: System lifecycle
- `KANBAN_CONNECTED`/`KANBAN_ERROR`: External integration status
- `PROJECT_CREATED`/`PROJECT_UPDATED`: Project management

## What Makes This System Special

### 1. Graceful Degradation
```python
@with_fallback(lambda self, event: logger.warning(f"Event {event.event_id} not persisted"))
async def _persist_event_safe(self, event: Event):
    """Persist event with graceful degradation"""
    await self.persistence.store_event(event)
```

The system continues operating even if persistence fails, logging warnings but not crashing.

### 2. Error Isolation
```python
async def safe_handler(h, e):
    try:
        await h(e)
    except Exception as err:
        logger.error(f"Error in event handler {h.__name__}: {err}")
```

One subscriber's failure doesn't affect others - critical for system reliability.

### 3. Performance Flexibility
```python
# Synchronous (wait for handlers)
await events.publish("task_completed", "agent_1", data)

# Asynchronous (fire-and-forget)
await events.publish_nowait("monitoring_update", "system", data)
```

Supports both blocking and non-blocking event handling based on criticality.

### 4. Universal Subscription
```python
# Subscribe to specific events
events.subscribe("task_completed", handle_completion)

# Subscribe to ALL events (monitoring/logging)
events.subscribe("*", universal_handler)
```

Enables system-wide monitoring and debugging capabilities.

### 5. Temporal Event Waiting
```python
# Wait for specific event with timeout
event = await events.wait_for_event("task_completed", timeout=30.0)
```

Supports synchronization patterns where components need to wait for specific conditions.

## Technical Implementation Details

### Event ID Generation
```python
event_id = f"evt_{self._event_counter}_{datetime.now().timestamp()}"
```
- Sequential counter prevents collisions
- Timestamp provides ordering and uniqueness
- Human-readable for debugging

### Memory Management
```python
if len(self.history) > 1000:
    self.history = self.history[-1000:]
```
- Automatic history trimming prevents memory leaks
- Configurable limits based on system requirements
- LRU-style eviction of oldest events

### Concurrent Handler Execution
```python
tasks = [safe_handler(handler, event) for handler in handlers]
await asyncio.gather(*tasks)  # Parallel execution
```
- All handlers run concurrently for performance
- Uses asyncio.gather for efficient coordination
- Error isolation prevents cascade failures

### Persistence Integration
The system integrates with any persistence layer that implements:
```python
async def store_event(self, event: Event)
async def get_events(self, event_type=None, source=None, limit=100)
```

## Pros and Cons

### Advantages

**Loose Coupling**
- Components don't need direct references to each other
- Easy to add new features without modifying existing code
- Supports microservice-style architecture within monolith

**Observability**
- Complete audit trail of system behavior
- Easy debugging through event history
- Real-time monitoring capabilities

**Resilience**
- System continues operating despite individual component failures
- Graceful degradation when persistence unavailable
- Error isolation prevents cascade failures

**Performance Options**
- Blocking vs non-blocking event handling
- Configurable persistence for different performance profiles
- Efficient concurrent handler execution

**Extensibility**
- New event types can be added without code changes
- Universal subscription enables cross-cutting concerns
- Event-driven plugins and extensions

### Disadvantages

**Debugging Complexity**
- Async event flow can be harder to trace
- Multiple subscribers make causality chains complex
- Temporal coupling issues in distributed scenarios

**Memory Usage**
- Event history storage in memory
- Multiple async tasks for concurrent handlers
- Potential memory leaks if history not managed

**Performance Overhead**
- Every action generates events and handler calls
- JSON serialization for persistence
- Async context switching overhead

**Eventual Consistency**
- Events may not be processed immediately
- Subscribers may see different ordering
- Race conditions possible in complex workflows

## Why This Approach Was Chosen

### Design Rationale

**Microservice Readiness**
The event system prepares Marcus for potential microservice decomposition. Components communicate through events rather than direct calls, making it easier to extract services later.

**AI System Integration**
AI components need to observe system behavior for learning. The event stream provides a natural data feed for:
- Pattern recognition
- Predictive modeling
- Anomaly detection
- Performance optimization

**Real-time Requirements**
Modern project management requires real-time updates. The event system enables:
- Live dashboard updates
- Instant notifications
- Reactive workflow adjustments
- Dynamic resource allocation

**Audit and Compliance**
Enterprise environments require detailed audit trails. Events provide:
- Complete system history
- Regulatory compliance support
- Security monitoring
- Performance analysis

## Simple vs Complex Task Handling

### Simple Tasks
For straightforward tasks (single agent, no dependencies):
```python
# Minimal event footprint
TASK_REQUESTED → TASK_ASSIGNED → TASK_STARTED → TASK_COMPLETED
```
- Few events generated
- Direct agent-to-task mapping
- Minimal coordination overhead

### Complex Tasks
For multi-agent, dependent tasks:
```python
# Rich event stream
TASK_REQUESTED → DEPENDENCY_DETECTED → CONTEXT_UPDATED →
TASK_ASSIGNED → IMPLEMENTATION_FOUND → TASK_STARTED →
TASK_PROGRESS (multiple) → DECISION_LOGGED →
TASK_BLOCKED → BLOCKER_RESOLVED → TASK_COMPLETED
```
- Comprehensive event trail
- Multiple system interactions
- Complex coordination patterns

The event system scales naturally from simple to complex scenarios without architectural changes.

## Board-Specific Considerations

### Kanban Integration Events
```python
# Board state synchronization
KANBAN_CONNECTED → PROJECT_CREATED → TASK_ASSIGNED
TASK_PROGRESS → KANBAN_UPDATED
KANBAN_ERROR → FALLBACK_MODE
```

### Board-Specific Event Data
Events can carry board-specific metadata:
```python
metadata = {
    "board_id": "proj_123",
    "board_type": "kanban",
    "sync_status": "pending",
    "external_id": "TICKET-456"
}
```

### Multi-Board Scenarios
The event system handles multiple project boards simultaneously:
- Events tagged with board identifiers
- Board-specific subscription patterns
- Cross-board dependency tracking
- Unified monitoring across boards

## Seneca Integration

### Learning Event Stream
The event system feeds Marcus's learning component (Seneca) with rich behavioral data:

```python
# Events of interest to learning system
TASK_COMPLETED + performance_metrics
TASK_BLOCKED + problem_patterns
DECISION_LOGGED + outcome_data
PATTERN_DETECTED + context_info
```

### Prediction Integration
Seneca can publish prediction events:
```python
await events.publish("prediction_made", "seneca", {
    "prediction_type": "task_duration",
    "estimated_hours": 4.5,
    "confidence": 0.85,
    "task_id": "task_123"
})
```

### Feedback Loops
Events enable continuous learning:
1. Seneca makes predictions → `PREDICTION_MADE`
2. Actual outcomes occur → `TASK_COMPLETED`
3. Learning system compares → `AGENT_LEARNED`
4. Improved predictions → Updated models

## Future Evolution

### Planned Enhancements

**Event Sourcing**
- Full event sourcing for complete system replay
- Time-travel debugging capabilities
- State reconstruction from event streams

**Advanced Filtering**
- Pattern-based event subscription
- Complex event processing (CEP)
- Real-time event stream analysis

**Distributed Events**
- Multi-instance event distribution
- External system integration
- Event mesh architecture

**ML-Driven Events**
- AI-generated synthetic events
- Predictive event streams
- Anomaly detection events

### Performance Optimizations

**Event Batching**
```python
# Future: Batch related events
await events.publish_batch([
    ("task_progress", "agent_1", {"progress": 25}),
    ("task_progress", "agent_1", {"progress": 50}),
    ("task_progress", "agent_1", {"progress": 75})
])
```

**Selective Persistence**
- Critical events persist immediately
- Non-critical events batch-persist
- Configurable persistence policies

**Event Compression**
- Similar events get compressed
- Reduced storage requirements
- Faster history queries

## Scenario Integration

In the typical Marcus workflow scenario:

### 1. Project Creation
```python
await events.publish("project_created", "marcus", {
    "project_id": "proj_123",
    "board_type": "kanban",
    "task_count": 15
})
```

### 2. Agent Registration
```python
await events.publish("agent_registered", "marcus", {
    "agent_id": "agent_claude_1",
    "skills": ["python", "documentation"],
    "availability": "active"
})
```

### 3. Task Request Cycle
```python
# Agent requests work
await events.publish("task_requested", "agent_claude_1", {})

# Marcus assigns task
await events.publish("task_assigned", "marcus", {
    "task_id": "task_456",
    "agent_id": "agent_claude_1",
    "priority": "high"
})
```

### 4. Progress Reporting
```python
# Periodic progress
await events.publish("task_progress", "agent_claude_1", {
    "task_id": "task_456",
    "progress": 50,
    "status": "in_progress",
    "message": "Implemented core functionality"
})
```

### 5. Blocker Handling
```python
# Blocker encountered
await events.publish("task_blocked", "agent_claude_1", {
    "task_id": "task_456",
    "blocker_type": "dependency",
    "description": "Need API specification"
})

# AI suggestion provided
await events.publish("blocker_resolved", "marcus", {
    "task_id": "task_456",
    "suggestion": "Use OpenAPI spec from task_123",
    "confidence": 0.9
})
```

### 6. Task Completion
```python
await events.publish("task_completed", "agent_claude_1", {
    "task_id": "task_456",
    "duration_minutes": 120,
    "lines_changed": 450,
    "tests_added": 8
})
```

## Monitoring and Debugging

### Event Stream Analysis
```python
# Monitor high-frequency events
high_freq_events = await events.get_history(limit=1000)
event_types = Counter(e.event_type for e in high_freq_events)

# Detect anomalies
blocked_tasks = await events.get_history(event_type="task_blocked")
```

### Performance Metrics
```python
# Track handler performance
handler_metrics = {
    "avg_execution_time": 0.05,  # 50ms average
    "error_rate": 0.01,          # 1% error rate
    "event_throughput": 1000     # Events per minute
}
```

### Debug Helpers
```python
# Wait for specific conditions
completion_event = await events.wait_for_event(
    "task_completed",
    timeout=300.0
)

# Universal monitoring
events.subscribe("*", debug_all_events)
```

## Conclusion

The Event-Driven Architecture system provides Marcus with a robust, scalable foundation for component communication. Its design prioritizes reliability, observability, and performance while maintaining the flexibility needed for both simple task automation and complex multi-agent workflows. The system's event-centric approach enables natural integration with AI learning systems and provides the audit trails necessary for enterprise project management platforms.

The architecture's emphasis on loose coupling and graceful degradation ensures that Marcus can operate reliably even when individual components experience issues, making it suitable for production environments where uptime and consistency are critical requirements.
