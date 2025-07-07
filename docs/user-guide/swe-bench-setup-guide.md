# Marcus SWE-Bench Setup Guide

## Overview

This guide helps you configure Marcus to tackle the SWE-Bench benchmark and achieve the target 14% resolution rate. SWE-Bench is Princeton's benchmark for evaluating AI systems on real-world software engineering tasks using GitHub issues from popular Python repositories.

## SWE-Bench Background

- **Dataset**: 2,294 real GitHub issues from 12 Python repositories
- **Task**: Generate patches that resolve described problems
- **Success**: FAIL_TO_PASS tests pass, PASS_TO_PASS tests don't break
- **Current SOTA**: 20% on full benchmark, 43% on SWE-Bench Lite
- **Target**: 14% resolution rate (318 issues resolved)

## Prerequisites

### System Requirements
- **OS**: Linux/macOS (x86_64 recommended)
- **Storage**: 120GB+ free space
- **RAM**: 16GB+ recommended
- **CPU**: 8+ cores
- **Docker**: Required for SWE-Bench evaluation harness

### Marcus Requirements
- Marcus properly installed and configured
- Valid OpenAI/Anthropic API keys
- Kanban board configured (Planka recommended for local testing)

## Setup Instructions

### Step 1: Install SWE-Bench

```bash
# Clone SWE-Bench repository
git clone https://github.com/SWE-bench/SWE-bench.git
cd SWE-bench

# Install dependencies
pip install -e .

# Test installation
python -m swebench.harness.run_evaluation --help
```

### Step 2: Configure Marcus for SWE-Bench

Create a specialized configuration file:

```bash
# In your Marcus root directory
cp config_marcus.json config_swe_bench.json
```

Edit `config_swe_bench.json`:

```json
{
  "project_name": "SWE-Bench Challenge",
  "kanban": {
    "provider": "planka",
    "board_name": "SWE-Bench Tasks"
  },
  "features": {
    "events": {
      "enabled": true,
      "store_history": true
    },
    "context": {
      "enabled": true,
      "use_hybrid_inference": true,
      "infer_dependencies": true,
      "code_analysis_depth": "deep"
    },
    "memory": {
      "enabled": true,
      "use_v2_predictions": true,
      "learning_rate": 0.1,
      "pattern_recognition": true
    },
    "visibility": {
      "enabled": true,
      "real_time_updates": true
    }
  },
  "swe_bench": {
    "dataset": "princeton-nlp/SWE-bench_Lite",
    "workspace_dir": "./swe_bench_workspaces",
    "max_attempts_per_issue": 3,
    "timeout_minutes": 30,
    "enable_learning": true,
    "batch_size": 10
  },
  "agents": {
    "max_concurrent": 4,
    "specialization": {
      "issue_analyst": 1,
      "code_explorer": 1, 
      "patch_creator": 1,
      "test_validator": 1
    }
  }
}
```

### Step 3: Add SWE-Bench Extensions to Marcus

#### 3.1 Create SWE-Bench Tools

```bash
# Create SWE-Bench specific tools
mkdir -p src/marcus_mcp/tools/swe_bench
```

Create `src/marcus_mcp/tools/swe_bench/__init__.py`:

```python
"""SWE-Bench integration tools for Marcus"""

from .swe_bench_adapter import SWEBenchAdapter
from .issue_analyzer import IssueAnalyzer
from .patch_generator import PatchGenerator
from .test_runner import TestRunner
from .repo_navigator import RepoNavigator

__all__ = [
    'SWEBenchAdapter',
    'IssueAnalyzer', 
    'PatchGenerator',
    'TestRunner',
    'RepoNavigator'
]
```

#### 3.2 Create Core SWE-Bench Tools

Create the core tool files:

```bash
# Create tool stubs - these will need full implementation
touch src/marcus_mcp/tools/swe_bench/swe_bench_adapter.py
touch src/marcus_mcp/tools/swe_bench/issue_analyzer.py
touch src/marcus_mcp/tools/swe_bench/patch_generator.py
touch src/marcus_mcp/tools/swe_bench/test_runner.py
touch src/marcus_mcp/tools/swe_bench/repo_navigator.py
```

#### 3.3 Register SWE-Bench Tools in MCP

Add to `src/marcus_mcp/tools/__init__.py`:

```python
# Add to existing imports
from .swe_bench import (
    SWEBenchAdapter,
    IssueAnalyzer,
    PatchGenerator, 
    TestRunner,
    RepoNavigator
)

# Add to tool registration in get_tool_definitions()
```

### Step 4: Set Up SWE-Bench Workspace

```bash
# Create workspace directory
mkdir -p ./swe_bench_workspaces

# Set up Docker for evaluation
docker --version  # Ensure Docker is installed

# Download SWE-Bench Lite dataset
python -c "
from datasets import load_dataset
dataset = load_dataset('princeton-nlp/SWE-bench_Lite')
print(f'Loaded {len(dataset[\"test\"])} test instances')
"
```

### Step 5: Configure Kanban Board

Set up a dedicated board for SWE-Bench tasks:

```bash
# Using Planka (recommended for local testing)
# Create columns:
# - TODO: GitHub issues to be processed
# - ANALYZING: Issue analysis in progress  
# - EXPLORING: Codebase exploration
# - IMPLEMENTING: Patch creation
# - TESTING: Validation and testing
# - DONE: Successfully resolved
# - FAILED: Could not resolve
```

## Running SWE-Bench with Marcus

### Phase 1: Basic Setup Test (Manual)

```bash
# Test Marcus SWE-Bench integration
python -c "
from src.marcus_mcp.tools.swe_bench import SWEBenchAdapter
adapter = SWEBenchAdapter()
# Test with a simple instance
"
```

### Phase 2: Automated Processing

```bash
# Start Marcus MCP server with SWE-Bench config
export MARCUS_CONFIG=config_swe_bench.json
python -m src.marcus_mcp.server

# In another terminal, run the SWE-Bench processor
python scripts/run_swe_bench.py \
    --dataset princeton-nlp/SWE-bench_Lite \
    --start_idx 0 \
    --end_idx 42 \
    --target_resolution_rate 0.14
```

### Phase 3: Full Evaluation

```bash
# Run official SWE-Bench evaluation
python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path marcus_predictions.jsonl \
    --max_workers 4 \
    --run_id marcus_run_1
```

## Implementation Strategy

### Immediate Implementation Priority

1. **SWE-Bench Adapter** (Week 1)
   - Load SWE-Bench instances
   - Set up repository workspaces
   - Convert issues to Marcus tasks

2. **Issue Analyzer** (Week 1)
   - Parse GitHub issue descriptions
   - Extract requirements and context
   - Identify affected components

3. **Patch Generator** (Week 2)
   - Create structured patches
   - Handle file modifications
   - Generate git-compatible diffs

4. **Test Runner** (Week 2)
   - Execute FAIL_TO_PASS tests
   - Validate PASS_TO_PASS tests
   - Report validation results

### Advanced Features (Weeks 3-4)

5. **Repository Navigator**
   - Smart codebase exploration
   - Dependency mapping
   - Component relationship understanding

6. **Learning System Integration**
   - Pattern recognition from successful solutions
   - Failed attempt analysis
   - Success rate optimization

## Expected Performance Trajectory

### Phase 1: Basic Implementation (Weeks 1-2)
- **Target**: 5-8% resolution rate
- **Focus**: Core workflow working end-to-end
- **Success**: Able to process issues and generate patches

### Phase 2: Marcus Optimization (Weeks 3-4)  
- **Target**: 10-12% resolution rate
- **Focus**: Leverage Marcus's context and memory systems
- **Success**: Learning from attempts, better code understanding

### Phase 3: Advanced Techniques (Weeks 5-6)
- **Target**: 14%+ resolution rate
- **Focus**: Multi-agent collaboration, advanced reasoning
- **Success**: Achieve target performance

## Key Success Factors

### Leverage Marcus Strengths
1. **Context System**: Use rich context to understand issue relationships
2. **Memory System**: Learn from successful and failed attempts
3. **Hybrid AI**: Combine rules (e.g., "run tests before submitting") with AI intelligence
4. **Error Handling**: Graceful recovery from failed patch attempts

### SWE-Bench Specific Optimizations
1. **Issue Understanding**: Deep analysis of GitHub issue descriptions
2. **Code Navigation**: Smart exploration of large codebases
3. **Test Integration**: Continuous validation during development
4. **Patch Quality**: Generate clean, focused patches

## Monitoring and Debugging

### Real-Time Monitoring
- Marcus's event system provides real-time visibility
- Monitor agent progress through Kanban board
- Track success/failure patterns in memory system

### Performance Metrics
- Resolution rate per repository
- Average time per issue
- Success patterns by issue type
- Agent collaboration efficiency

### Debugging Failed Attempts
- Rich error context from Marcus's error framework
- Step-by-step trace through event history
- Learning from failures through memory system

## Troubleshooting

### Common Issues

**Docker Problems**
```bash
# Increase Docker resources
# macOS: Docker Desktop → Preferences → Resources
# Linux: Check Docker daemon configuration
```

**Memory Issues**
```bash
# Monitor Marcus memory usage
# Adjust batch_size in config if needed
# Increase system RAM allocation
```

**API Rate Limits**
```bash
# Implement rate limiting in AI calls
# Use multiple API keys if available
# Add retry logic with exponential backoff
```

## Next Steps

1. **Implement core SWE-Bench tools** (High Priority)
2. **Set up development environment** with SWE-Bench Lite
3. **Test with 10-20 issues** to validate workflow
4. **Iterate on performance** using Marcus's learning capabilities
5. **Scale to full evaluation** once 14% target achieved

## Resources

- [SWE-Bench Repository](https://github.com/SWE-bench/SWE-bench)
- [SWE-Bench Leaderboard](https://www.swebench.com/)
- [Marcus Documentation](../developer-guide/)
- [SWE-Bench Paper](https://arxiv.org/abs/2310.06770)

---

**Target Milestone**: Achieve 14% resolution rate (42 out of 300 SWE-Bench Lite instances) within 6 weeks using Marcus's autonomous agent architecture.