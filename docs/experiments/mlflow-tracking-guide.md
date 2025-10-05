# MLflow Experiment Tracking for Marcus

Complete guide to using MLflow for systematic Marcus experiments and performance analysis.

## Overview

Marcus now includes comprehensive MLflow integration for tracking experiments with different configurations and conditions. This allows you to:

- 📊 Track metrics across multiple runs
- 🔬 Compare different experimental conditions
- 📈 Analyze agent performance over time
- 🎯 Optimize Marcus configurations

## Installation

```bash
pip install mlflow
```

## Quick Start

### Basic Usage

```python
from src.experiments import MarcusExperiment

# Initialize experiment
experiment = MarcusExperiment(
    experiment_name="my-test",
    tracking_uri="./mlruns"
)

# Start a run
with experiment.start_run(
    run_name="test-1",
    params={
        "num_agents": 50,
        "complexity": "enterprise"
    }
):
    # Your experiment code
    experiment.log_metric("velocity", 12.5)
    experiment.log_blocker("agent-1", "task-123", "API timeout")
```

### Running Twitter Swarm with MLflow

```bash
# Run with all conditions enabled
python examples/twitter_clone_with_mlflow.py \\
    --enable-all \\
    --num-agents 50 \\
    --complexity enterprise \\
    --experiment-name "twitter-50-agents"

# Run specific conditions
python examples/twitter_clone_with_mlflow.py \\
    --enable-blockers \\
    --enable-artifacts \\
    --num-agents 25 \\
    --complexity standard
```

## Tracked Metrics

### Project-Level Metrics
- `velocity` - Tasks completed per time period
- `total_tasks` - Total tasks in project
- `completed_tasks` - Number completed
- `in_progress_tasks` - Currently active
- `blocked_tasks` - Blocked count
- `progress_percent` - Overall progress

### Task-Level Metrics
- `task_duration_{task_id}` - Individual task duration
- `avg_task_duration` - Average across all tasks
- `total_tasks_completed` - Running total
- `estimation_accuracy_{task_id}` - Actual vs estimated

### Agent-Level Metrics
- `agent_{id}_tasks_completed` - Per-agent task count
- `agent_{id}_avg_duration` - Per-agent average duration
- `agent_{id}_success_rate` - Per-agent success rate

### Condition Metrics
- `total_blockers` - Number of blockers reported
- `blocker_{severity}` - Blockers by severity level
- `total_artifacts` - Artifacts created
- `artifacts_{type}` - Artifacts by type
- `total_decisions` - Decisions logged
- `total_context_requests` - Context requests made

## Experimental Conditions

### Enable Blockers
Simulates agents encountering and reporting blockers:
```bash
--enable-blockers
```
Logs: Blocker description, severity, agent, task

### Enable Artifacts
Simulates agents creating artifacts:
```bash
--enable-artifacts
```
Logs: Artifact type, filename, task context

### Enable Decisions
Simulates agents logging architectural decisions:
```bash
--enable-decisions
```
Logs: Decision description, agent, task context

### Enable Context Requests
Simulates agents requesting task context:
```bash
--enable-context-requests
```
Logs: Context type, requester, task

## Viewing Results

### MLflow UI

```bash
# Start MLflow UI
mlflow ui

# Open in browser
http://localhost:5000
```

### Compare Runs

```python
from src.experiments import MarcusExperiment

experiment = MarcusExperiment("my-test")

# Compare all runs
comparison = experiment.compare_runs()

# Compare specific runs
comparison = experiment.compare_runs(
    run_ids=["run1", "run2"],
    metric_names=["velocity", "total_blockers"]
)

# Generate report
experiment.generate_report("report.json")
```

## Example Experiments

### 1. Agent Scaling Test

Test how performance changes with different agent counts:

```bash
# 10 agents
python examples/twitter_clone_with_mlflow.py \\
    --num-agents 10 \\
    --experiment-name "scaling-test" \\
    --run-name "10-agents"

# 25 agents
python examples/twitter_clone_with_mlflow.py \\
    --num-agents 25 \\
    --experiment-name "scaling-test" \\
    --run-name "25-agents"

# 50 agents
python examples/twitter_clone_with_mlflow.py \\
    --num-agents 50 \\
    --experiment-name "scaling-test" \\
    --run-name "50-agents"
```

### 2. Complexity Comparison

Test how complexity affects outcomes:

```bash
# Prototype
python examples/twitter_clone_with_mlflow.py \\
    --complexity prototype \\
    --experiment-name "complexity-test" \\
    --run-name "prototype"

# Enterprise
python examples/twitter_clone_with_mlflow.py \\
    --complexity enterprise \\
    --experiment-name "complexity-test" \\
    --run-name "enterprise"
```

### 3. Condition Impact Analysis

Test impact of different conditions:

```bash
# No conditions
python examples/twitter_clone_with_mlflow.py \\
    --experiment-name "condition-test" \\
    --run-name "baseline"

# With blockers
python examples/twitter_clone_with_mlflow.py \\
    --enable-blockers \\
    --experiment-name "condition-test" \\
    --run-name "with-blockers"

# All conditions
python examples/twitter_clone_with_mlflow.py \\
    --enable-all \\
    --experiment-name "condition-test" \\
    --run-name "all-conditions"
```

## Advanced Usage

### Custom Metrics

```python
from src.experiments import MarcusExperiment

experiment = MarcusExperiment("custom-test")

with experiment.start_run():
    # Log custom metrics
    experiment.log_metric("custom_metric", 42.0)

    # Log metrics over time
    for step in range(100):
        velocity = calculate_velocity(step)
        experiment.log_velocity(velocity, step=step)

    # Log project state over time
    for step in range(100):
        state = get_project_state()
        experiment.log_project_state(
            total_tasks=state.total,
            completed_tasks=state.completed,
            in_progress_tasks=state.in_progress,
            blocked_tasks=state.blocked,
            progress_percent=state.progress,
            velocity=state.velocity,
            step=step
        )
```

### Batch Experiments

```python
import asyncio
from src.experiments import MarcusExperiment

async def run_batch_experiments():
    """Run multiple experiments in sequence."""
    configs = [
        {"agents": 10, "complexity": "prototype"},
        {"agents": 25, "complexity": "standard"},
        {"agents": 50, "complexity": "enterprise"},
    ]

    for config in configs:
        await twitter_mlflow_workflow(
            num_agents=config["agents"],
            complexity=config["complexity"],
            experiment_name="batch-test",
            run_name=f"{config['agents']}-{config['complexity']}"
        )

asyncio.run(run_batch_experiments())
```

## Best Practices

1. **Consistent Naming**: Use clear, descriptive experiment and run names
2. **Parameter Tracking**: Always log all configuration parameters
3. **Multiple Runs**: Run each configuration multiple times for statistical significance
4. **Baseline**: Always include a baseline run with default settings
5. **Documentation**: Add notes/tags to runs for context

## Troubleshooting

### MLflow UI Not Loading
```bash
# Check if port 5000 is in use
lsof -i :5000

# Use different port
mlflow ui --port 5001
```

### Metrics Not Appearing
- Ensure `mlflow.log_metric()` is called within an active run
- Check that tracking URI is set correctly
- Verify experiment name exists

### Comparison Errors
- Ensure run IDs are valid
- Check that runs belong to the same experiment
- Verify metrics exist in all compared runs

## See Also

- [MLflow Documentation](https://www.mlflow.org/docs/latest/index.html)
- [Marcus Monitoring Systems](../systems/quality/11-monitoring-systems.md)
- [Performance Benchmarking](../../tests/performance/benchmark_scaling.py)
