# PM Agent Experiment Setup Guide

## Overview

The experiments test PM Agent by having autonomous agents work through real coding tasks from SWE-bench. Here's exactly how to set up and run them.

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Experiment    │────▶│   PM Agent   │────▶│ Autonomous      │
│   Controller    │     │   Server     │     │ Agents (Claude) │
└─────────────────┘     └──────────────┘     └─────────────────┘
        │                       │                      │
        │                       ▼                      │
        │               ┌──────────────┐               │
        │               │   Kanban     │               │
        │               │   Board      │◀──────────────┘
        │               └──────────────┘
        │
        ▼
┌─────────────────┐
│    Results      │
│   Collection    │
└─────────────────┘
```

## Step-by-Step Setup

### 1. Start PM Agent Server

First, ensure PM Agent is running with the MCP server:

```bash
# In the PM Agent directory
cd /Users/lwgray/dev/pm-agent

# Start the PM Agent server
python -m pm_agent.server --port 8000
```

### 2. Start the Kanban MCP Server

PM Agent needs the Kanban board running:

```bash
# In another terminal
cd /Users/lwgray/dev/pm-agent
npm run start:kanban
```

### 3. Configure Experiment Environment

```bash
cd experiments
cp .env.example .env
```

Edit `.env`:
```env
# PM Agent Configuration
PM_AGENT_API_URL=http://localhost:8000
PM_AGENT_API_KEY=your_pm_agent_key

# Claude API for agents
ANTHROPIC_API_KEY=your_anthropic_key

# Experiment settings
MAX_CONCURRENT_AGENTS=5
DEFAULT_AGENT_COUNT=3
```

### 4. Initialize Experiment Infrastructure

```bash
python scripts/setup_experiments.py
```

This will:
- Download SWE-bench datasets
- Create necessary directories
- Initialize the experiment database
- Verify PM Agent connection

## How Experiments Work

### 1. Experiment Controller Creates a Project

The experiment controller uses PM Agent's API to:
```python
# Create a new project for the experiment
project = pm_agent.create_project(
    name="SWE-bench Baseline Test",
    description="Testing task completion rate"
)
```

### 2. Load Tasks from SWE-bench

```python
# Load real-world coding tasks
tasks = load_dataset('princeton-nlp/SWE-bench_Lite')

# Convert to PM Agent tasks
for task in tasks:
    pm_agent.create_task(
        title=f"Fix: {task['problem_statement'][:50]}...",
        description=task['problem_statement'],
        labels=['swe-bench', task['repo']],
        metadata={
            'instance_id': task['instance_id'],
            'base_commit': task['base_commit'],
            'test_files': task['FAIL_TO_PASS']
        }
    )
```

### 3. Launch Autonomous Agents

For each agent in the experiment:

```bash
# The experiment controller launches agents with specific prompts
python scripts/launch_agent.py \
  --agent-id agent_001 \
  --branch agent_001_work \
  --prompt-template swebench_agent
```

### 4. Agent Prompt Template

The agents receive this prompt (see `prompts/swebench_agent.md`):

```markdown
You are an autonomous software engineer working through PM Agent.

YOUR TASK:
1. Register with PM Agent using the register_agent tool
2. Continuously request tasks using request_next_task
3. For each task:
   - Analyze the problem description
   - Checkout the specified base commit
   - Make necessary code changes
   - Run the failing tests to verify they now pass
   - Report progress at 25%, 50%, 75%, 100%
   - Commit your changes to your branch

IMPORTANT:
- You work on branch: {BRANCH_NAME}
- If blocked, use report_blocker for help
- Complete tasks before requesting new ones
- Focus on making the specified tests pass

AVAILABLE TOOLS:
- PM Agent tools: register_agent, request_next_task, report_progress, report_blocker
- Git tools: checkout, commit, push
- File tools: read, write, edit
- Test tools: run pytest
```

### 5. Experiment Monitoring

While agents work, the experiment controller:
- Monitors task completion rates
- Tracks time per task
- Measures resource usage
- Collects error rates
- Records agent interactions

## Running Different Experiments

### Baseline Performance Test
Tests basic task completion rate:
```bash
python scripts/run_experiment.py --experiment baseline \
  --agents 5 \
  --tasks 100
```

### Failure Recovery Test
Introduces intentional failures:
```bash
python scripts/run_experiment.py --experiment failure_recovery \
  --inject-failures
```

### Scalability Test
Gradually increases agent count:
```bash
python scripts/run_experiment.py --experiment scalability \
  --max-agents 50
```

## Agent Management

### Launching Agents Manually
```bash
# Launch a single agent
claude-code --pm-agent-mode \
  --agent-id test_agent_001 \
  --pm-agent-url http://localhost:8000 \
  --system-prompt prompts/swebench_agent.md
```

### Launching Multiple Agents
```bash
# Use the batch launcher
python scripts/launch_agents.py --count 5 --experiment baseline
```

## Experiment Workflow

1. **Setup Phase**
   - Start PM Agent server
   - Initialize experiment
   - Create project and tasks

2. **Execution Phase**
   - Launch autonomous agents
   - Agents register and start working
   - Monitor progress in real-time

3. **Collection Phase**
   - Wait for all tasks to complete/timeout
   - Collect metrics from PM Agent
   - Generate reports

## Monitoring During Experiments

### PM Agent Dashboard
Open http://localhost:8000/dashboard to see:
- Active agents
- Task progress
- Completion rates
- Error logs

### Experiment Metrics
```bash
# Real-time metrics
python scripts/monitor_experiment.py --experiment-id baseline_001

# Grafana dashboard
open http://localhost:3000
```

## Troubleshooting

### Agent Not Registering
- Check PM Agent server is running
- Verify API URL in agent prompt
- Check network connectivity

### Tasks Not Being Assigned
- Verify tasks were created in PM Agent
- Check agent capabilities match task requirements
- Look for errors in PM Agent logs

### Low Completion Rates
- Review agent prompts
- Check task difficulty
- Analyze blocker reports
- Increase agent timeout

## Example: Running Complete Baseline Test

```bash
# Terminal 1: Start PM Agent
cd /Users/lwgray/dev/pm-agent
python -m pm_agent.server

# Terminal 2: Start Kanban MCP
cd /Users/lwgray/dev/pm-agent
npm run start:kanban

# Terminal 3: Run experiment
cd experiments
python scripts/setup_experiments.py
python scripts/run_full_baseline.py --agents 5 --tasks 50

# This script will:
# 1. Create PM Agent project
# 2. Load 50 SWE-bench tasks
# 3. Launch 5 Claude agents
# 4. Monitor until completion
# 5. Generate report
```

## Results

After experiments complete, find results in:
- `./results/baseline/` - Raw data
- `./results/reports/` - Formatted reports
- `./results/artifacts/` - Agent code changes

The key metric is Task Completion Rate:
- Industry average: ~25%
- PM Agent target: >40%
- Measured as: (Completed Tasks / Total Tasks) × 100