# Marcus Enhanced Features Documentation

## Overview

Marcus has been enhanced with three powerful systems that work together to provide intelligent task coordination:

1. **Events System** - Enables loose coupling between components through publish/subscribe
2. **Context System** - Provides rich context for task assignments including dependency awareness
3. **Memory System** - Learns from past experiences to make predictive task assignments

## Configuration

All enhanced features are controlled via `config_marcus.json`:

```json
{
  ...existing config...
  "features": {
    "events": true,    // Enable event distribution
    "context": true,   // Enable context awareness
    "memory": true,    // Enable learning and prediction
    "visibility": false // Future enhancement
  }
}
```

When any feature is enabled, Marcus automatically creates a persistence layer using SQLite for long-term storage.

## Events System

### Overview

The Events system provides a publish/subscribe mechanism for loose coupling between Marcus components. Any component can publish events, and multiple subscribers can react to them asynchronously.

### Key Features

- Asynchronous event handling
- Error isolation (one subscriber error doesn't affect others)
- Optional event history
- Universal subscribers (subscribe to all events with `*`)
- Persistence for event replay

### Usage Example

```python
from src.core.events import Events, EventTypes

# Create events system
events = Events(store_history=True, persistence=persistence)

# Subscribe to specific events
async def task_handler(event):
    print(f"Task {event.data['task_id']} assigned to {event.data['agent_id']}")
    
events.subscribe(EventTypes.TASK_ASSIGNED, task_handler)

# Subscribe to all events
async def universal_handler(event):
    logger.info(f"Event: {event.event_type} from {event.source}")
    
events.subscribe("*", universal_handler)

# Publish events
await events.publish(
    EventTypes.TASK_ASSIGNED,
    "marcus",  # source
    {
        "task_id": "task_123",
        "agent_id": "agent_1",
        "task_name": "Build API"
    }
)
```

### Standard Event Types

- `task_requested` - Agent requests work
- `task_assigned` - Task assigned to agent
- `task_started` - Agent begins work
- `task_progress` - Progress update
- `task_completed` - Task finished
- `task_blocked` - Task encountered blocker
- `decision_logged` - Architectural decision made
- `context_updated` - Context prepared for task

## Context System

### Overview

The Context system enhances task assignments by providing agents with:
- Previous implementations from dependencies
- Awareness of tasks that depend on their work
- Architectural decisions from related tasks
- Learned patterns from similar work

### Key Features

- **Dependency Awareness**: Agents see what future tasks need from their work
- **Implementation Tracking**: Previous work is available as context
- **Decision Logging**: Architectural decisions are captured and cross-referenced
- **Pattern Recognition**: Common patterns are extracted and reused

### For Agents

Agents receive enhanced task assignments:

```json
{
  "task": {
    "id": "task_123",
    "name": "Build User API",
    "instructions": "...",
    
    // Previous work this task can build on
    "implementation_context": {
      "task_99": {
        "apis": ["GET /users", "POST /users"],
        "models": ["User(id, email, password_hash)"],
        "patterns": ["RESTful", "JWT auth"]
      }
    },
    
    // NEW: What depends on this work
    "dependency_awareness": "2 future tasks depend on your work:\n- Frontend Login (needs: /auth/login endpoint)\n- Admin Dashboard (needs: JWT validation middleware)",
    
    // NEW: Full context object
    "full_context": {
      "previous_implementations": {...},
      "dependent_tasks": [...],
      "architectural_decisions": [...],
      "related_patterns": [...]
    }
  }
}
```

Agents can also log decisions:

```python
# Agent logs an architectural decision
marcus.log_decision(
    agent_id="agent_1",
    task_id="task_123",
    decision="I chose JWT tokens because mobile apps need stateless auth. This affects all API endpoints which must validate tokens."
)
```

### For Project Managers

The Context system automatically:
- Analyzes task dependencies (both explicit and inferred)
- Tracks implementations as tasks complete
- Cross-references decisions to dependent tasks
- Provides rich context without manual intervention

## Memory System

### Overview

The Memory system enables Marcus to learn from past experiences and make predictive task assignments. It uses a cognitive-inspired architecture with four memory tiers.

### Memory Tiers

1. **Working Memory** (minutes to hours)
   - Active task assignments
   - Current system state
   - Recent events

2. **Episodic Memory** (weeks to months)
   - Complete task execution records
   - Success/failure outcomes
   - Actual vs estimated time
   - Blockers encountered

3. **Semantic Memory** (long-term)
   - Agent skill profiles
   - Task type patterns
   - Success factors
   - Common blockers by type

4. **Procedural Memory** (long-term)
   - Successful workflows
   - Optimization strategies
   - Best practices

### Predictions

When assigning tasks, Marcus now provides predictions:

```json
{
  "task": {
    "id": "task_123",
    "name": "Build Payment API",
    
    // NEW: Predictions based on history
    "predictions": {
      "success_probability": 0.85,
      "estimated_duration": 12.5,  // Adjusted from 10 hours
      "blockage_risk": 0.3,
      "risk_factors": ["authentication_setup", "payment_gateway_config"]
    }
  }
}
```

### Learning Process

1. **Task Start**: Memory records assignment in working memory
2. **Task Progress**: Updates and events tracked
3. **Task Completion**: 
   - Outcome recorded in episodic memory
   - Agent profile updated with success/failure
   - Patterns extracted and stored
   - Estimation accuracy calculated
4. **Future Assignments**: Predictions improve based on accumulated data

### Agent Profiles

The system builds profiles for each agent:

```python
AgentProfile(
    agent_id="agent_1",
    total_tasks=50,
    successful_tasks=45,
    success_rate=0.9,
    skill_success_rates={
        "python": 0.95,
        "api": 0.92,
        "database": 0.78
    },
    average_estimation_accuracy=0.85,
    common_blockers=["auth_config", "db_connection"],
    blockage_rate=0.2
)
```

## Integration Example

Here's how all three systems work together:

```python
# 1. Agent requests work
await marcus.request_next_task(agent_id="agent_1")

# 2. Memory predicts outcomes for available tasks
predictions = await memory.predict_task_outcome("agent_1", task)

# 3. Context provides dependency awareness
context = await context.get_context(task.id, task.dependencies)

# 4. Task assigned with full context and predictions
response = {
    "task": {
        ...task details...,
        "implementation_context": previous_work,
        "dependency_awareness": dependent_tasks_info,
        "predictions": predictions
    }
}

# 5. Events published for monitoring
await events.publish(EventTypes.TASK_ASSIGNED, "marcus", assignment_data)

# 6. Agent works and reports progress
await marcus.report_task_progress(
    agent_id="agent_1",
    task_id="task_123",
    status="completed",
    progress=100
)

# 7. Memory learns from outcome
await memory.record_task_completion(
    agent_id="agent_1",
    task_id="task_123",
    success=True,
    actual_hours=11.5
)

# 8. Context updated for future tasks
await context.add_implementation("task_123", implementation_details)
```

## Benefits

### For Agents
- **Reduced Context Discovery**: No need to reverse-engineer existing code
- **Clearer Requirements**: Know what future tasks need from your work
- **Better Estimates**: Predictions based on actual historical data
- **Fewer Blockers**: Common issues predicted and mitigated

### For Project Managers
- **Improved Visibility**: Events provide real-time project status
- **Better Planning**: Predictions help with realistic timelines
- **Knowledge Preservation**: Decisions and patterns captured automatically
- **Continuous Improvement**: System gets smarter with each project

### For Organizations
- **Faster Development**: 30-50% reduction in context discovery time
- **Higher Quality**: Consistent patterns and practices
- **Reduced Risk**: Predictive warnings about potential blockers
- **Institutional Memory**: Knowledge persists beyond individual projects

## Monitoring and Analytics

With persistence enabled, you can query historical data:

```python
# Get recent events
events = await persistence.get_events(
    event_type=EventTypes.TASK_COMPLETED,
    limit=100
)

# Get agent decisions
decisions = await persistence.get_decisions(
    agent_id="agent_1",
    limit=50
)

# Get memory statistics
stats = memory.get_memory_stats()
print(f"Total tasks tracked: {stats['episodic_memory']['total_outcomes']}")
print(f"Agent profiles: {stats['semantic_memory']['agent_profiles']}")
print(f"Task patterns learned: {stats['semantic_memory']['task_patterns']}")
```

## Best Practices

1. **Enable Features Gradually**: Start with Events, add Context, then Memory
2. **Monitor Predictions**: Compare predicted vs actual to tune learning
3. **Clean Old Data**: Use `persistence.cleanup(days=90)` periodically
4. **Log Decisions**: Encourage agents to log architectural decisions
5. **Review Patterns**: Periodically review learned patterns for insights

## Troubleshooting

### Features Not Working
- Check `config_marcus.json` has features enabled
- Verify SQLite database is created in `./data/`
- Check logs for initialization errors

### Predictions Seem Wrong
- Memory needs data to learn - predictions improve over time
- Check if agent profiles have sufficient history
- Verify task labels are consistent

### Performance Issues
- Use `persistence.cleanup()` to remove old data
- Consider switching to PostgreSQL for large deployments
- Monitor event subscriber performance

## Future Enhancements

The architecture supports future additions:
- **Visibility System**: Real-time dashboards and monitoring
- **Advanced Predictions**: ML models for complex predictions
- **Team Learning**: Cross-team pattern sharing
- **Automated Optimization**: Self-tuning task assignments