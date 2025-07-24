# Task Recovery and Board Health System

## Overview

Marcus now includes advanced systems for automatic task recovery and board health monitoring. These features ensure that tasks don't get stuck when agents disconnect and that the overall project board remains healthy and productive.

## Assignment Lease System

The assignment lease system ensures tasks are automatically recovered when agents fail to complete them within expected timeframes.

### How It Works

1. **Task Assignment**: When a task is assigned, it receives a time-limited lease (default: 4 hours)
2. **Progress Renewal**: Each progress report automatically renews the lease
3. **Automatic Recovery**: Expired leases trigger task recovery (status → TODO)
4. **Smart Duration**: Renewal duration adapts based on progress and task complexity

### Lease Duration Logic

```python
# Initial lease duration based on task estimation
initial_lease = max(task.estimated_hours, 4.0) hours

# Renewal duration based on progress
- 75%+ complete: 2 hours (near completion)
- 50-75% complete: 3 hours
- <25% with many renewals: 2 hours (possibly stuck)
- Complex tasks (>8h estimate): 1.5x duration
- After 5+ renewals: capped at 2 hours
```

### Example Workflow

```
1. Agent requests task → 4-hour lease created
2. Agent reports 25% progress → lease renewed for 4 hours
3. Agent reports 50% progress → lease renewed for 3 hours
4. Agent reports 75% progress → lease renewed for 2 hours
5. Agent completes task → lease removed
```

### Monitoring Leases

Use the ping tool to check lease status:

```python
# Check system health including leases
result = await session.call_tool("ping", arguments={"echo": "health"})

# Response includes:
{
    "lease_statistics": {
        "total_active": 5,
        "expired": 1,
        "expiring_soon": 2,
        "average_renewal_count": 2.3
    }
}
```

## Board Health Analyzer

The board health analyzer detects project-level issues that might prevent progress.

### Detection Capabilities

1. **Skill Mismatches**
   - Tasks that no available agent can handle
   - Missing skills in the team
   - Recommendations for hiring/training

2. **Circular Dependencies**
   - Task A → B → C → A cycles
   - Automatic detection using graph analysis
   - Critical severity issues

3. **Bottlenecks**
   - Tasks blocking 3+ other tasks
   - Prioritization recommendations
   - Impact analysis

4. **Chain Blocks**
   - Long sequential dependency chains
   - Tasks with 4+ levels of dependencies
   - Parallelization opportunities

5. **Stale Tasks**
   - In-progress tasks not updated in 7+ days
   - Agent workload analysis
   - Reassignment recommendations

6. **Agent Workload**
   - Overloaded agents (>3 tasks)
   - Idle agents with no tasks
   - Load balancing suggestions

### Using Board Health Tools

#### Check Overall Health

```python
result = await session.call_tool("check_board_health")

# Response:
{
    "health_score": 75.0,  # 0-100
    "status": "good",      # excellent/good/fair/poor/critical
    "issues": [
        {
            "type": "skill_mismatch",
            "severity": "high",
            "description": "3 tasks cannot be assigned due to skill mismatches",
            "affected_tasks": ["task-123", "task-456", "task-789"],
            "recommendations": [
                "Add agent with skills: kubernetes, terraform",
                "Consider cross-training existing agents"
            ]
        }
    ],
    "recommendations": [
        "🚨 Address critical issues immediately",
        "🔧 Prioritize bottleneck tasks to unblock dependencies"
    ]
}
```

#### Check Task Dependencies

```python
result = await session.call_tool("check_task_dependencies", arguments={
    "task_id": "task-123"
})

# Response:
{
    "task": {"id": "task-123", "name": "Implement API"},
    "depends_on": [
        {"id": "task-100", "name": "Design Schema", "status": "done"},
        {"id": "task-101", "name": "Setup Database", "status": "in_progress"}
    ],
    "depended_by": [
        {"id": "task-200", "name": "Frontend Integration"},
        {"id": "task-201", "name": "API Tests"}
    ],
    "has_circular_dependency": false,
    "analysis": {
        "is_bottleneck": true,  # Blocks 2+ tasks
        "is_blocked": true,     # Has incomplete dependencies
        "blocking_count": 2,
        "dependency_depth": 3
    }
}
```

### Health Score Calculation

The board health score (0-100) considers:

- **Issue Severity Penalties**:
  - Critical: -20 points
  - High: -10 points
  - Medium: -5 points
  - Low: -2 points

- **Completion Rate**: <10% = -10 points, <30% = -5 points
- **Blocked Rate**: >30% = -10 points, >15% = -5 points

### Common Issues and Solutions

#### Skill Mismatch Deadlock

**Symptom**: Tasks sitting in TODO because no agent has required skills

**Solution**:
1. Check board health to identify missing skills
2. Either:
   - Add agents with required skills
   - Train existing agents
   - Modify task requirements
   - Outsource specialized tasks

#### Circular Dependencies

**Symptom**: Tasks that depend on each other in a cycle

**Solution**:
1. Use `check_task_dependencies` to identify cycles
2. Break the cycle by:
   - Removing one dependency link
   - Merging related tasks
   - Restructuring task breakdown

#### Bottleneck Tasks

**Symptom**: One task blocking many others

**Solution**:
1. Identify bottlenecks via board health check
2. Prioritize bottleneck completion
3. Assign best available agent
4. Consider breaking down the task

## Integration with Existing Systems

### Assignment Monitor

The lease system works alongside the assignment monitor:
- Monitor tracks state reversions
- Lease manager handles timeouts
- Both update assignment persistence

### Progress Reporting

Progress reports automatically renew leases:
```python
# This renews the lease
await report_task_progress(
    agent_id="agent-001",
    task_id="task-123",
    status="in_progress",
    progress=50,
    message="Halfway complete"
)
```

### Graceful Shutdown

On interruption:
1. Active leases are persisted
2. Lease monitor stops cleanly
3. State is preserved for restart

## Best Practices

### For Project Managers

1. **Regular Health Checks**: Run board health analysis daily
2. **Address Critical Issues**: Fix circular dependencies immediately
3. **Balance Workload**: Keep agents at 1-3 tasks each
4. **Monitor Bottlenecks**: Prioritize tasks blocking others

### For Agents

1. **Report Progress**: Regular updates renew your lease
2. **Complete or Release**: Don't hold tasks you can't complete
3. **Request Appropriate Tasks**: Match your skills to task requirements

### For System Administrators

1. **Configure Lease Durations**: Adjust based on project complexity
2. **Set Stale Thresholds**: Default 7 days, adjust as needed
3. **Monitor Lease Statistics**: Watch for high renewal counts
4. **Review Recovery History**: Identify problematic task patterns

## Configuration

```python
# Lease system configuration
lease_manager = AssignmentLeaseManager(
    kanban_client,
    assignment_persistence,
    default_lease_hours=4.0,      # Initial lease duration
    max_renewals=10,              # Max renewals before escalation
    warning_threshold_hours=1.0   # Warning before expiry
)

# Board health configuration
health_analyzer = BoardHealthAnalyzer(
    kanban_client,
    stale_task_days=7,           # Days before task is stale
    max_tasks_per_agent=3        # Overload threshold
)
```

## Troubleshooting

### Tasks Keep Getting Recovered

**Causes**:
- Agent not reporting progress
- Lease duration too short
- Task genuinely stuck

**Solutions**:
- Check agent connectivity
- Increase lease duration for complex tasks
- Review task with agent

### False Positive Bottlenecks

**Causes**:
- Natural task hierarchies
- Misidentified dependencies

**Solutions**:
- Review dependency structure
- Adjust bottleneck threshold
- Use task labels to indicate critical path

### Skill Mismatch False Positives

**Causes**:
- Incorrect skill extraction
- Tasks don't need specialized skills

**Solutions**:
- Update task descriptions/labels
- Configure skill extraction keywords
- Manual skill override in task metadata
