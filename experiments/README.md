# PM Agent Experiments

This directory contains the experimental framework for validating PM Agent's performance against industry benchmarks.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Initialize experiment environment:**
   ```bash
   python scripts/setup_experiments.py
   ```

4. **Run an experiment:**
   ```bash
   python scripts/run_experiment.py --experiment baseline
   ```

## Benchmark Information

### SWE-bench
- **Official Leaderboard**: https://www.swebench.com/
- **Documentation**: https://www.swebench.com/SWE-bench/
- **Dataset Access**: Via Hugging Face `princeton-nlp/SWE-bench_Lite`
- **Current SOTA**: ~25% task completion rate

### Task Completion Rate Definition
Task Completion Rate (TCR) = (Successfully Completed Tasks / Total Attempted Tasks) × 100

A task is considered complete when:
1. Code changes implemented correctly
2. All existing tests pass
3. New tests added (if applicable)
4. Linting and type checking pass
5. Solution matches expected behavior

## Available Experiments

1. **Baseline Performance** (`baseline`)
   - Tests on SWE-bench Lite (300 real-world Python issues)
   - Compares 1, 3, 5, and 10 agent configurations
   - Target: >40% completion rate

2. **Failure Recovery** (`failure_recovery`)
   - Tests recovery from 6 common failure scenarios
   - Validates blocker reporting mechanism
   - Target: >70% recovery rate

3. **Scalability Stress** (`scalability`)
   - Tests with 1-50 concurrent agents
   - Monitors resource usage and throughput
   - Finds optimal configurations

4. **Real-World Project** (`real_world`)
   - Builds complete todo application
   - Tests end-to-end development workflow
   - Target: >80% feature completion

5. **Coordination Efficiency** (`coordination`)
   - Compares team sizes on same project
   - Measures coordination overhead
   - Target: <20% overhead

6. **Human-AI Collaboration** (`collaboration`)
   - Tests different autonomy levels
   - Optimizes human intervention points
   - Target: <20% intervention rate

7. **Cost-Benefit Analysis** (`cost_benefit`)
   - Tracks all operational costs
   - Measures value delivered
   - Target: ROI positive in 3 months

8. **Integration Complexity** (`integration`)
   - Tests on existing codebases (Django, Express, React)
   - Bug fixes and feature additions
   - Target: >60% success on bug fixes

## Running Experiments

### Run Single Experiment
```bash
python scripts/run_experiment.py --experiment baseline --agents 5 --tasks 100
```

### Run All Experiments
```bash
python scripts/run_all_experiments.py --parallel
```

### Dry Run (Preview)
```bash
python scripts/run_experiment.py --experiment baseline --dry-run
```

## Monitoring

Start monitoring stack:
```bash
docker-compose up -d prometheus grafana
```

View metrics at: http://localhost:3000 (Grafana)

## Results

Results are saved to `./results/{experiment_name}/` with timestamps.

Generate comprehensive report:
```bash
python scripts/generate_report.py --format pdf
```

## Project Structure
```
experiments/
├── config/
│   └── experiment_config.yaml    # Main configuration
├── experiments/
│   ├── baseline.py              # Baseline experiment
│   ├── failure_recovery.py      # Failure recovery experiment
│   └── ...                      # Other experiments
├── scripts/
│   ├── setup_experiments.py     # Environment setup
│   ├── run_experiment.py        # Single experiment runner
│   └── run_all_experiments.py   # Batch runner
├── data/                        # Test data and tasks
├── cache/                       # Downloaded datasets
├── results/                     # Experiment results
└── monitoring/                  # Prometheus/Grafana configs
```

## Extending Experiments

To add a new experiment:

1. Create new file in `experiments/` extending `BaseExperiment`
2. Add configuration to `config/experiment_config.yaml`
3. Register in `run_experiment.py` EXPERIMENT_CLASSES
4. Implement the `run()` method

Example:
```python
from .base import BaseExperiment

class CustomExperiment(BaseExperiment):
    async def run(self, progress_callback=None):
        # Your experiment logic
        return results
```

## Troubleshooting

1. **PM Agent not running**: Ensure PM Agent API is running on configured URL
2. **Dataset download fails**: Check internet connection and Hugging Face access
3. **Out of memory**: Reduce agent count or task batch size
4. **API rate limits**: Configure delays in experiment config

## Contact

For questions about experiments or benchmarks, see the main PM Agent documentation.