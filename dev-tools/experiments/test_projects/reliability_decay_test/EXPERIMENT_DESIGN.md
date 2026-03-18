# Reliability Decay Experiment: Disproving the Pipeline Failure Model

## Background

A recent article claims multi-agent systems exhibit multiplicative reliability decay:
- **Article's Model**: `P(success) = p₁ × p₂ × ... × pₙ`
- **Example**: With 98% per-agent accuracy, 10 agents = 81.7% system success

**Key Assumption**: Agents pass outputs directly to each other without validation, causing error propagation.

## Hypothesis

**Marcus does NOT exhibit this reliability decay** because:

1. **Board-Mediated Coordination**: No direct agent-to-agent handoffs
2. **Explicit State Validation**: Tasks have clear success/failure states
3. **Retry/Reassignment**: Failed tasks don't poison the system
4. **Observable Failures**: Failures are explicit, not silent propagation

## Experimental Method

### Test Task: 5-Stage Data Pipeline

A sequential pipeline where each stage depends on the previous:
```
Stage 1: Data Ingestion → Stage 2: Validation → Stage 3: Enrichment →
Stage 4: Aggregation → Stage 5: Reporting
```

### Configurations to Test

| Config | Agents | Dependency Depth | Expected Behavior |
|--------|--------|------------------|-------------------|
| Single Agent | 1 | 0 (no handoffs) | Baseline success rate |
| 5 Agents | 5 | 4 (4 handoffs) | **Should NOT decay to p⁵** |
| 10 Agents | 10 | 9 (9 handoffs) | **Should NOT decay to p¹⁰** |

### Key Metrics to Track (via MLflow)

1. **Task Completion Rate**:
   - `completed_tasks / total_tasks` by dependency depth
   - Article predicts: 98%^5 = 90.4% for 5-stage pipeline
   - Marcus hypothesis: >95% even with 5 agents

2. **Retry Count**:
   - How many tasks needed retry?
   - Marcus isolates failures, allows recovery

3. **Blocker Rate**:
   - How many tasks blocked on dependencies?
   - Should be high if coordination works (agents wait properly)
   - Should be low if error propagation (poisoned dependencies cause failures)

4. **Time to Completion**:
   - Single agent: Baseline time
   - Multi-agent: May be slower due to coordination overhead
   - **But should still complete successfully**

5. **Failure Mode Analysis**:
   - **Silent failures** (article's model): Task completes but output is wrong
   - **Explicit failures** (Marcus): Task marked failed, can be retried

## What Would Disprove Marcus?

If we see:
- **Exponential decay**: Success rate drops to 90% with 5 agents, 82% with 10 agents
- **Cascading failures**: One task failure causes all downstream tasks to fail
- **No recovery**: Failed tasks stay failed, no retry mechanism

## What Would Support Marcus?

If we see:
- **Stable success rate**: >95% completion regardless of agent count
- **Contained failures**: Failed tasks don't propagate errors
- **Successful retries**: Tasks that fail initially can be recovered
- **Explicit validation**: Failures detected at boundaries, not downstream

## How to Run This Experiment

```bash
# From marcus/dev-tools/experiments/
python run_comparison_experiment.py \
  --projects reliability_decay_test \
  --results-dir ./results/reliability_study
```

## Expected Results

### Article's Model (Pipeline-Style MAS)
```
Depth 0 (1 agent):  98.0% success
Depth 4 (5 agents): 90.4% success ❌
Depth 9 (10 agents): 81.7% success ❌
```

### Marcus (Board-Mediated MAS)
```
Depth 0 (1 agent):  98.0% success
Depth 4 (5 agents): 96-98% success ✅
Depth 9 (10 agents): 95-98% success ✅
```

**Why the difference?**
- Marcus breaks the product rule by **validating at boundaries**
- Failures are **explicit and recoverable**, not silent and propagating
- Board state acts as **circuit breaker** preventing error propagation

## Analysis Script

After running experiments, analyze with:

```python
import mlflow
import pandas as pd

# Load experiment data
experiments = ["5_stages_1_agent", "5_stages_5_agents", "5_stages_10_agents"]
results = []

for exp_name in experiments:
    runs = mlflow.search_runs(experiment_names=[exp_name])

    # Calculate success rate
    completed = runs["metrics.total_task_completions"].max()
    total = runs["params.task_count"].iloc[0]
    success_rate = completed / total

    results.append({
        "experiment": exp_name,
        "agents": int(runs["params.num_agents"].iloc[0]),
        "success_rate": success_rate,
        "retries": runs["metrics.total_blockers"].max(),
        "avg_time": runs["metrics.duration_seconds"].max()
    })

df = pd.DataFrame(results)

# Compare against article's predictions
df["article_prediction"] = df["agents"].apply(lambda n: 0.98 ** n)
df["beats_prediction"] = df["success_rate"] > df["article_prediction"]

print(df)
```

## Key Insight for Response

**The article's math only applies to unvalidated pipelines.**

Marcus is not a pipeline - it's a **coordination platform** where:
- Work is explicit (Kanban cards)
- State transitions are validated
- Failures are observable and recoverable
- No silent error propagation

This is **architectural**, not just "we have better agents."
