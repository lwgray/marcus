# How to Benchmark Marcus: Practical Testing Guide

## Quick Start

Want to benchmark Marcus against other orchestration systems? Here's exactly how to do it.

## Prerequisites

1. Marcus instance running (see main README for setup)
2. Planka board configured
3. Python 3.8+ with dependencies installed
4. Docker for monitoring stack (optional but recommended)

## Test Scenario 1: Basic Performance Testing

### What This Tests
- Task assignment speed
- System responsiveness under load
- Agent coordination efficiency

### How to Run
```bash
# 1. Start Marcus
cd /path/to/marcus
python src/main.py

# 2. Run the scaling benchmark
python tests/performance/benchmark_scaling.py --agents 10 --duration 300

# 3. Check results
cat results/benchmark_results.json
```

### Expected Output
```json
{
  "avg_assignment_time_ms": 87,
  "tasks_per_minute": 45,
  "successful_completions": 98.5,
  "agent_utilization": 0.82
}
```

### What Good Looks Like
- Assignment time < 100ms
- Task completion rate > 95%
- Agent utilization > 75%

## Test Scenario 2: Head-to-Head Comparison

### Setting Up the Comparison

#### Option A: Marcus vs Human PM
```python
# comparison_test.py
from marcus.testing import ComparisonTest

test = ComparisonTest()

# Create two identical projects
marcus_project = test.create_project("Marcus-Managed", coordinator="marcus")
human_project = test.create_project("Human-Managed", coordinator="human")

# Add same 50 tasks to both
test.populate_tasks(marcus_project, "tasks_template.json")
test.populate_tasks(human_project, "tasks_template.json")

# Run for 1 week
results = test.run_comparison(days=7)
print(results.summary())
```

#### Option B: Marcus vs AutoGPT/CrewAI
```bash
# 1. Set up both systems with identical tasks
python experiments/setup_comparison.py --systems marcus,autogpt

# 2. Run parallel execution
python experiments/run_comparison.py --duration 24h

# 3. Analyze results
python experiments/analyze_results.py --metric all
```

### Metrics to Compare
1. **Task Completion Rate**: How many tasks finished successfully
2. **Time to Completion**: Average time per task
3. **Resource Usage**: CPU/memory consumption
4. **Quality Metrics**: Bug density, test coverage
5. **Cost**: API calls, compute resources

## Test Scenario 3: SWE-bench Evaluation

### What This Tests
Real-world software engineering task performance using standardized benchmarks.

### Setup
```bash
# 1. Download SWE-bench dataset
cd experiments
python download_swe_bench.py

# 2. Configure Marcus for SWE-bench
cp config/swe_bench_config.json marcus.config.json

# 3. Run evaluation
python run_swe_bench_test.py --instances 100 --agents 5
```

### Interpreting Results
```
Marcus SWE-bench Results:
- Instances Attempted: 100
- Successfully Resolved: 67
- Partially Resolved: 18  
- Failed: 15
- Success Rate: 67% (vs baseline 13%)
```

## Test Scenario 4: Stress Testing

### Find Breaking Points
```bash
# Gradually increase load
for agents in 10 50 100 200 500; do
    echo "Testing with $agents agents..."
    python tests/performance/stress_test.py --agents $agents
    sleep 30
done
```

### What to Look For
- When does latency exceed 1 second?
- When do tasks start failing?
- What's the maximum sustainable load?

## Test Scenario 5: Real Project Testing

### Most Realistic Test
1. Take an actual software project
2. Create task breakdown (or use existing backlog)
3. Run with Marcus coordination
4. Compare to historical velocity

```python
# real_project_test.py
from marcus import MarcusClient

client = MarcusClient()

# Import your Jira/GitHub issues
tasks = client.import_from_jira("PROJ-123")

# Start Marcus coordination
project = client.create_project("Real Project Test")
client.add_tasks(project.id, tasks)
client.start_coordination(project.id)

# Monitor progress
while not project.is_complete():
    stats = client.get_project_stats(project.id)
    print(f"Progress: {stats.completion_percentage}%")
    print(f"Velocity: {stats.tasks_per_day} tasks/day")
    print(f"Blocked: {stats.blocked_count}")
    time.sleep(3600)  # Check hourly
```

## Monitoring During Tests

### 1. Enable Prometheus/Grafana
```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. Key Dashboards to Watch
- **System Performance**: CPU, memory, network
- **Marcus Metrics**: Task throughput, decision latency
- **Project Health**: Velocity trends, blocker rates
- **AI Performance**: LLM call latency, token usage

### 3. Export Results
```bash
# Export Prometheus data
curl http://localhost:9090/api/v1/query_range \
  -d 'query=marcus_tasks_completed_total' \
  -d 'start=2024-01-01T00:00:00Z' \
  -d 'end=2024-01-02T00:00:00Z' \
  -d 'step=300' > metrics.json
```

## Common Benchmarking Pitfalls

### 1. Unfair Task Distribution
❌ Don't: Give Marcus harder tasks than comparison
✅ Do: Use identical task sets or randomize distribution

### 2. Ignoring Warmup
❌ Don't: Measure from system start
✅ Do: Allow 5-10 minute warmup period

### 3. Small Sample Sizes
❌ Don't: Test with 5 tasks and call it done
✅ Do: Use at least 50-100 tasks for statistical significance

### 4. Single Metric Focus
❌ Don't: Only measure speed
✅ Do: Balance speed, quality, and resource usage

## Analyzing Results

### Statistical Significance
```python
from scipy import stats

# Compare Marcus vs baseline
marcus_times = [/* task completion times */]
baseline_times = [/* baseline completion times */]

t_stat, p_value = stats.ttest_ind(marcus_times, baseline_times)
print(f"Improvement is {'significant' if p_value < 0.05 else 'not significant'}")
```

### Generate Report
```bash
python scripts/generate_benchmark_report.py \
  --input results/ \
  --output benchmark_report.pdf \
  --format detailed
```

## Specific Competitive Benchmarks

### vs Traditional PM Tools (Jira/Asana)
Focus on:
- Time from task creation to assignment
- Assignment accuracy (right person for the job)
- Blocker detection speed

### vs AI Orchestration (AutoGPT/CrewAI)
Focus on:
- Multi-agent coordination effectiveness
- Task completion quality
- Resource efficiency

### vs Human-Only Teams
Focus on:
- Overall project delivery time
- Code quality metrics
- Team satisfaction (surveys)

## Publishing Results

When you have meaningful results:

1. **Document Methodology**: Exactly how you ran tests
2. **Share Raw Data**: Make results reproducible
3. **Highlight Strengths**: Where Marcus excels
4. **Acknowledge Limitations**: Where it needs improvement
5. **Suggest Use Cases**: When to use Marcus vs alternatives

## Getting Help

- Join Marcus Discord: [link]
- Benchmarking channel: #benchmarks
- Share results: benchmarks@marcus.ai

## Next Steps

1. Start with Test Scenario 1 (basic performance)
2. Graduate to Scenario 2 (comparison testing)
3. Run Scenario 5 with a real project
4. Share your results with the community

Remember: The goal isn't to prove Marcus is perfect, but to understand where it adds value and guide improvements.