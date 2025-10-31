# Smart Retry Strategy

## Overview

Marcus uses an intelligent retry calculation system that prevents agents from sleeping through available work while minimizing unnecessary polling. The system prioritizes tasks that unlock parallel work and detects early task completions.

## Problem Statement

In multi-agent systems, idle agents need to know when to check back for new work. Traditional approaches have two failure modes:

1. **Sleeping through tasks**: Agent waits for full estimated completion time, but task finishes early and another agent takes the newly available work
2. **Excessive polling**: Agent checks too frequently, wasting resources and API calls

Additionally, agents may wake up for sequential work that current workers could easily handle, missing opportunities to wait for tasks that unlock parallel work better suited for multiple idle agents.

## Solution: Smart Retry with Parallel Work Prioritization

Marcus implements a two-part strategy:

### 1. Parallel Work Prioritization

The system analyzes the dependency graph to determine which in-progress tasks will unlock the most parallel work:

```python
# Count idle agents waiting for work
idle_agents = total_agents - busy_agents

# Prioritize tasks that unlock enough parallel work for idle agents
high_value_tasks = [
    task for task in in_progress_tasks
    if task.unlocks_count >= idle_agents
]
```

**Benefits:**
- Agents wake up when parallel work becomes available
- Prevents waking for sequential work current workers can handle
- Maximizes utilization of idle agent capacity

### 2. Early Completion Detection

Instead of waiting for the full estimated completion time, agents check back at **60% of the ETA** with a **5-minute maximum**:

```python
retry_after = int(target_task["eta_seconds"] * 0.6)
retry_after = max(30, retry_after)  # Minimum 30 seconds
retry_after = min(retry_after, 300)  # Maximum 5 minutes
```

**Benefits:**
- Catches tasks that finish faster than estimated
- Regular re-polling for long-running tasks
- Avoids excessive polling with minimum 30-second interval

## How It Works

### Step 1: Calculate ETAs for In-Progress Tasks

For each in-progress task, Marcus calculates estimated time to completion based on progress:

```python
if progress > 0 and progress < 100:
    # Use actual progress to estimate
    estimated_total_seconds = (elapsed_seconds / progress) * 100
    remaining_seconds = estimated_total_seconds - elapsed_seconds
else:
    # Fall back to historical median
    remaining_seconds = global_median_hours * 3600
```

**Example:**
- Task at 25% progress after 100 seconds
- Estimated total: (100 / 25) × 100 = 400 seconds
- Remaining: 400 - 100 = **300 seconds ETA**

### Step 2: Analyze Dependency Graph

For each task, count how many tasks it will unlock:

```python
dependent_task_ids = [
    t.id for t in project_tasks
    if task.id in (t.dependencies or [])
]
unlocks_count = len(dependent_task_ids)
```

### Step 3: Prioritize High-Value Tasks

Select tasks that unlock enough parallel work for idle agents:

```python
# If we have tasks that unlock parallel work, prioritize those
# Otherwise fall back to any task completion
candidate_tasks = high_value_tasks if high_value_tasks else all_tasks
```

### Step 4: Calculate Retry Time

Apply the 60% rule with bounds:

```python
retry_after = int(target_task["eta_seconds"] * 0.6)
retry_after = max(30, retry_after)    # Min 30s
retry_after = min(retry_after, 300)   # Max 5min
```

## Example Scenarios

### Scenario 1: Prioritizing Parallel Work

**Setup:**
- 2 agents total
- 1 agent busy
- 1 agent idle

**In-Progress Tasks:**
- Task A: ETA 300s, unlocks 1 task (sequential)
- Task B: ETA 400s, unlocks 2 tasks (parallel)

**Decision:**
- Old logic: Wait for Task A (~330s with buffer)
- **New logic: Wait for Task B at 240s (60% of 400s)**
- Rationale: Task B unlocks enough work for the idle agent

### Scenario 2: Early Completion Detection

**Setup:**
- Task ETA: 500 seconds (8.3 minutes)
- Actual completion: 350 seconds (5.8 minutes)

**Timeline:**
- Old logic: Wait 550s, miss the completion at 350s
- **New logic: Check at 300s (60%), catch completion at 350s**
- Benefit: Agent discovers work 200+ seconds earlier

### Scenario 3: Long-Running Tasks

**Setup:**
- Task ETA: 1200 seconds (20 minutes)
- Progress updates every few minutes

**Behavior:**
- Calculated retry: 1200 × 0.6 = 720 seconds
- **Actual retry: 300 seconds (5-minute cap)**
- Result: Agent re-polls every 5 minutes to catch early completion or updated progress

### Scenario 4: Fast Sequential Work

**Setup:**
- 3 agents: 2 busy, 1 idle
- Task A: ETA 60s, unlocks 1 task
- Task B: ETA 90s, unlocks 1 task

**Behavior:**
- No tasks unlock >= 1 parallel work slots
- Falls back to soonest completion (Task A)
- Retry: 60 × 0.6 = 36 seconds
- **Actual: 36 seconds** (above 30s minimum)

## Configuration

The retry strategy uses these constants (in `src/marcus_mcp/tools/task.py`):

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `retry_percentage` | 0.6 (60%) | Check at 60% of ETA for early completion |
| `min_retry_seconds` | 30 | Prevent excessive polling |
| `max_retry_seconds` | 300 (5 min) | Regular re-polling for long tasks |
| `no_work_retry` | 300 (5 min) | Default when no tasks in progress |

## Benefits

1. **Reduced Idle Time**: Agents wake up at optimal times for available work
2. **Better Resource Utilization**: Prioritizes parallel work over sequential work
3. **Early Detection**: Catches tasks completing faster than estimated
4. **Scalability**: Adapts to varying numbers of agents and task patterns
5. **Cost Efficiency**: Avoids unnecessary polling while staying responsive

## Implementation Details

### Location

The smart retry logic is implemented in:
- **File**: `src/marcus_mcp/tools/task.py`
- **Function**: `calculate_retry_after_seconds(state: Any) -> Dict[str, Any]`
- **Lines**: ~318-455

### Return Value

```python
{
    "retry_after_seconds": 180,  # Time to wait
    "reason": "Waiting for 'Setup Database' to complete (~6 min, 40% done) (unlocks 2 tasks)",
    "blocking_task": {
        "id": "task-123",
        "name": "Setup Database",
        "progress": 40,
        "eta_seconds": 300
    }
}
```

### Integration Points

The retry calculation is called by:
1. `request_next_task` MCP tool when no suitable tasks are available
2. Task assignment logic when all agents are busy

## Monitoring

### Logs

Watch for retry decisions in Marcus logs:

```
[INFO] Agent agent-2 requesting next task
[INFO] No suitable tasks - retry in 120 seconds
[INFO] Reason: Waiting for 'API Implementation' to complete (~8 min, 30% done) (unlocks 3 tasks)
```

### Metrics

Track these metrics to evaluate retry effectiveness:

- **Average idle time**: Time agents spend waiting for work
- **Missed opportunities**: Tasks completed while agents slept
- **Polling frequency**: How often agents check for work
- **Parallel utilization**: Percentage of time multiple agents work simultaneously

## Future Enhancements

Potential improvements to the retry strategy:

1. **Machine learning**: Learn actual completion time patterns per task type
2. **Agent skill matching**: Factor in which agents can handle unlocked tasks
3. **Priority weighting**: Consider task priority in addition to parallelism
4. **Dynamic percentage**: Adjust retry percentage based on historical accuracy
5. **Network awareness**: Account for distributed agents with varying latency

## References

- **Task Assignment**: See [Assignment Lease System](35-assignment-lease-system.md)
- **Dependency Management**: See [Task Dependency System](36-task-dependency-system.md)
- **Agent Coordination**: See [Agent Coordination](21-agent-coordination.md)
- **Optimal Agent Scheduling**: See [Optimal Agent Scheduling System](37-optimal-agent-scheduling.md)
