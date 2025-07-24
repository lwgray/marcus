# Task Lease and Board Health Configuration Reference

This document describes all available configuration options for the task lease system and board health analyzer in Marcus. These can be configured globally in `config_marcus.json` or per-project.

## Task Lease Configuration

Task leases ensure that tasks are automatically recovered when agents fail to complete them. Configure under the `"task_lease"` key.

### Basic Options

```json
{
  "task_lease": {
    "default_hours": 2.0,
    "max_renewals": 10,
    "warning_hours": 0.5
  }
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `default_hours` | float | 2.0 | Default lease duration in hours for new task assignments |
| `max_renewals` | int | 10 | Maximum number of times a lease can be renewed before escalation |
| `warning_hours` | float | 0.5 | Hours before lease expiry to start warning (appears in health checks) |

### Advanced Options

```json
{
  "task_lease": {
    "priority_multipliers": {
      "critical": 0.5,
      "high": 0.75,
      "medium": 1.0,
      "low": 1.5
    },
    "complexity_multipliers": {
      "simple": 0.5,
      "complex": 1.5,
      "research": 2.0,
      "epic": 3.0
    },
    "grace_period_minutes": 30,
    "renewal_decay_factor": 0.9,
    "min_lease_hours": 1.0,
    "max_lease_hours": 24.0,
    "stuck_threshold_renewals": 5,
    "enable_adaptive": true
  }
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `priority_multipliers` | object | See below | Lease duration multipliers based on task priority |
| `complexity_multipliers` | object | See below | Lease duration multipliers based on task labels |
| `grace_period_minutes` | int | 30 | Minutes after expiry before task is recovered |
| `renewal_decay_factor` | float | 0.9 | Factor to reduce renewal duration each time (0.9 = 10% reduction) |
| `min_lease_hours` | float | 1.0 | Minimum allowed lease duration |
| `max_lease_hours` | float | 24.0 | Maximum allowed lease duration |
| `stuck_threshold_renewals` | int | 5 | Renewals before considering a task "stuck" |
| `enable_adaptive` | bool | true | Enable smart lease adjustments based on task properties |

#### Priority Multipliers

Adjust lease duration based on task priority:
- `critical`: 0.5 (half the time - urgent tasks)
- `high`: 0.75 (75% of normal time)
- `medium`: 1.0 (normal duration)
- `low`: 1.5 (150% of normal - can take longer)

#### Complexity Multipliers

Adjust lease duration based on task labels:
- `simple`: 0.5 (quick tasks)
- `complex`: 1.5 (needs more time)
- `research`: 2.0 (exploratory work)
- `epic`: 3.0 (very large tasks)

### Lease Duration Calculation

The final lease duration is calculated as:

```
duration = base_hours
         × priority_multiplier
         × complexity_multiplier
         × (decay_factor ^ renewal_count)

bounded by [min_lease_hours, max_lease_hours]
```

### Example Configurations

#### Fast-Paced Startup Project
```json
{
  "task_lease": {
    "default_hours": 1.0,
    "max_renewals": 5,
    "grace_period_minutes": 15,
    "priority_multipliers": {
      "critical": 0.25,
      "high": 0.5,
      "medium": 1.0,
      "low": 2.0
    }
  }
}
```

#### Research Project
```json
{
  "task_lease": {
    "default_hours": 8.0,
    "max_renewals": 20,
    "grace_period_minutes": 120,
    "renewal_decay_factor": 0.95,
    "complexity_multipliers": {
      "experiment": 2.0,
      "analysis": 1.5,
      "documentation": 1.0
    }
  }
}
```

#### Enterprise Project
```json
{
  "task_lease": {
    "default_hours": 4.0,
    "max_renewals": 15,
    "min_lease_hours": 2.0,
    "max_lease_hours": 40.0,
    "stuck_threshold_renewals": 8,
    "enable_adaptive": true
  }
}
```

## Board Health Configuration

Configure the board health analyzer under the `"board_health"` key.

```json
{
  "board_health": {
    "stale_task_days": 7,
    "max_tasks_per_agent": 3,
    "bottleneck_threshold": 3,
    "chain_length_warning": 4,
    "skill_match_threshold": 0.7
  }
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `stale_task_days` | int | 7 | Days before an in-progress task is considered stale |
| `max_tasks_per_agent` | int | 3 | Maximum tasks per agent before considered overloaded |
| `bottleneck_threshold` | int | 3 | Number of dependent tasks to be considered a bottleneck |
| `chain_length_warning` | int | 4 | Dependency chain length that triggers a warning |
| `skill_match_threshold` | float | 0.7 | Minimum skill match score for task assignment |

## Project-Specific Configuration

You can override these settings per project in your projects configuration:

```json
{
  "projects": {
    "urgent-project": {
      "name": "Urgent Customer Project",
      "provider": "github",
      "task_lease": {
        "default_hours": 1.0,
        "max_renewals": 3,
        "grace_period_minutes": 10
      },
      "board_health": {
        "stale_task_days": 2,
        "max_tasks_per_agent": 2
      }
    },
    "research-project": {
      "name": "Long Term Research",
      "provider": "linear",
      "task_lease": {
        "default_hours": 12.0,
        "max_renewals": 30,
        "enable_adaptive": false
      },
      "board_health": {
        "stale_task_days": 14,
        "max_tasks_per_agent": 5
      }
    }
  }
}
```

## Global vs Project Configuration

The configuration hierarchy works as follows:

1. **Project-specific settings** (highest priority)
2. **Global settings** in `config_marcus.json`
3. **System defaults** (lowest priority)

## Monitoring Configuration Effects

After changing configuration, you can monitor the effects using:

```python
# Check current lease statistics
result = await session.call_tool("ping", arguments={"echo": "health"})

# Check board health with new settings
result = await session.call_tool("check_board_health")
```

## Best Practices

### Choosing Lease Durations

1. **Short leases (1-2 hours)**: Good for:
   - Urgent projects with tight deadlines
   - Simple, well-defined tasks
   - Teams with frequent check-ins

2. **Medium leases (2-4 hours)**: Good for:
   - Standard development tasks
   - Balanced urgency and flexibility
   - Most projects

3. **Long leases (4-8+ hours)**: Good for:
   - Research and exploration tasks
   - Complex implementations
   - Tasks with uncertain scope

### Tuning Renewal Decay

- **High decay (0.7-0.8)**: Tasks get shorter leases quickly, good for preventing stuck tasks
- **Medium decay (0.85-0.95)**: Balanced approach
- **Low/No decay (0.95-1.0)**: Tasks maintain similar lease duration, good for consistent work

### Grace Period Considerations

- **Short grace (5-15 min)**: Aggressive recovery, good for critical projects
- **Medium grace (30-60 min)**: Allows for short breaks/interruptions
- **Long grace (60-120 min)**: Accommodates meetings, long breaks

### Board Health Thresholds

- **Stale task days**: Set based on your sprint/iteration length
- **Max tasks per agent**: Consider task complexity and agent experience
- **Bottleneck threshold**: Lower = more sensitive to dependencies

## Troubleshooting

### Tasks Being Recovered Too Quickly

**Solution**: Increase one or more of:
- `default_hours`
- `grace_period_minutes`
- Priority/complexity multipliers

### Tasks Getting Stuck

**Solution**: Decrease one or more of:
- `default_hours`
- `max_renewals`
- `renewal_decay_factor` (more aggressive decay)

### Too Many False Positive Health Issues

**Solution**: Adjust thresholds:
- Increase `stale_task_days`
- Increase `bottleneck_threshold`
- Increase `max_tasks_per_agent`

### Lease Durations Not Adapting

**Solution**: Check that:
- `enable_adaptive` is true
- Tasks have proper priority set
- Tasks have complexity labels
- Multipliers are configured

## Monitoring and Metrics

The lease system provides metrics via the health check:

```json
{
  "lease_statistics": {
    "total_active": 5,
    "expired": 1,
    "expiring_soon": 2,
    "high_renewal_count": 1,
    "average_renewal_count": 3.2,
    "by_status": {
      "active": 3,
      "expiring_soon": 2,
      "expired": 1
    }
  }
}
```

Use these metrics to tune your configuration over time.
