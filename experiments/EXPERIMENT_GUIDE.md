# Marcus Experiments: Single Agent vs Multi-Agent Comparison

This directory contains a comprehensive experimental framework for comparing single-agent vs multi-agent performance using Marcus.

## Overview

This framework enables **well-controlled experiments** to test hypotheses about multi-agent collaboration efficiency. It includes:

- **Test projects** of varying complexity (simple, medium, complex)
- **Experiment configurations** for 1, 2, 4, 8, and 16 agent setups
- **Enhanced MLflow tracking** with 50+ metrics
- **Statistical analysis scripts** for hypothesis testing
- **Visualization tools** for generating comparison charts

## Quick Start

### 1. Install Dependencies

```bash
cd experiments/analysis
pip install -r requirements.txt
```

### 2. Run a Simple Experiment

```bash
# Test with the simple calculator project
cd experiments
python run_comparison_experiment.py --projects 01_simple_calculator --dry-run

# Remove --dry-run to actually run
python run_comparison_experiment.py --projects 01_simple_calculator
```

### 3. Analyze Results

```bash
# Generate comparison report
python analysis/compare_experiments.py --report comparison_report.json

# Create visualizations
python analysis/visualize_results.py --output-dir plots/
```

## Hypotheses Being Tested

### H1: Throughput & Parallelization

**Hypothesis**: Marcus multi-agent systems will complete projects faster than single agents for complex tasks with parallelizable subtasks.

**Predictions**:
- Simple (< 10 tasks): Single ≈ Multi (overhead dominates)
- Medium (10-30 tasks): Multi 2-3x faster
- Complex (> 30 tasks): Multi 3-5x faster (until saturation ~8-10 agents)

**Metrics**: `parallel_speedup_factor`, `throughput_tasks_per_hour`

### H2: Coordination Overhead

**Hypothesis**: Multi-agent systems have higher coordination overhead but this cost is outweighed by parallel execution benefits.

**Predictions**:
- Multi-agent: Higher `total_context_requests`, `total_blockers`
- Break-even point: ~5-8 parallelizable tasks

**Metrics**: `coordination_context_requests`, `coordination_blockers`

### H3: Quality & Consistency

**Hypothesis**: Single agents produce more consistent code style, but multi-agent systems may have better error detection.

**Metrics**: `test_coverage`, `linting_errors`, `type_errors`

### H4: Cost Efficiency

**Hypothesis**: For high-parallelizability projects, multi-agent systems have better cost-per-task despite higher total tokens.

**Metrics**: `api_cost_usd`, `cost_per_task`, `duration_hours`

### H5: Task Complexity Scaling

**Hypothesis**: The multi-agent advantage increases non-linearly with task complexity and dependency graph breadth.

**Metrics**: `parallel_speedup_factor` vs `parallelizable_fraction`, `critical_path_length`

## Metrics Tracked (50+ metrics)

- **Performance**: duration_hours, velocity, throughput, speedup, efficiency
- **Quality**: test_coverage, linting_errors, type_errors, complexity
- **Coordination**: context_requests, blockers, artifacts, decisions, conflicts
- **Resources**: total_tokens, api_cost, tokens_per_task, cost_per_task
- **Dependencies**: critical_path, avg_depth, parallelizable_fraction

See full documentation in experiments/EXPERIMENT_GUIDE.md
