# Running Real Claude Agents with Marcus

This guide explains how to run experiments with real Claude agents (not simulations) working through Marcus MCP.

## Overview

The real agent system allows you to:
- Launch multiple Claude instances
- Each working in their own git worktree
- Coordinated through Marcus MCP
- Solving real SWE-bench tasks

## Prerequisites

1. **Marcus MCP Server** running:
   ```bash
   cd /Users/lwgray/dev/marcus
   python marcus_mcp_server.py
   ```

2. **Claude CLI** installed and configured

3. **A test repository** with tasks loaded into Marcus

## Quick Start

### 1. Simple Test (2 Agents)

```bash
cd /Users/lwgray/dev/marcus/experiments

# Create a test repository
mkdir -p /tmp/test-repo
cd /tmp/test-repo
git init
echo "# Test Project" > README.md
git add .
git commit -m "Initial commit"

# Run experiment
python scripts/run_real_agents.py \
  --source-repo /tmp/test-repo \
  --workspace /tmp/agent-workspace \
  --marcus-server /Users/lwgray/dev/marcus/marcus_mcp_server.py \
  --agents 2
```

### 2. Full SWE-bench Test (5 Agents)

```bash
# Assuming you have a repository with SWE-bench tasks loaded
python scripts/run_real_agents.py \
  --source-repo /path/to/swebench-repo \
  --workspace /tmp/swebench-agents \
  --marcus-server /Users/lwgray/dev/marcus/marcus_mcp_server.py \
  --agents 5
```

## Step-by-Step Process

### 1. Setup Worktrees

The system creates isolated git worktrees for each agent:

```bash
python scripts/setup_worktrees.py \
  --source-repo /path/to/repo \
  --workspace-dir /tmp/agent-workspace \
  --num-agents 5
```

This creates:
```
/tmp/agent-workspace/
├── agent1/  (on branch: agent1-work)
├── agent2/  (on branch: agent2-work)
├── agent3/  (on branch: agent3-work)
├── agent4/  (on branch: agent4-work)
└── agent5/  (on branch: agent5-work)
```

### 2. Launch Agents

Each agent is launched with:
- Access to Marcus MCP
- Their own worktree directory
- A customized prompt

```bash
python scripts/launch_agents.py \
  --workspace-dir /tmp/agent-workspace \
  --marcus-server /path/to/marcus_mcp_server.py \
  --prompt-file prompts/marcus_agent.md \
  --agents 5
```

### 3. Monitor Progress

- **Marcus UI**: http://localhost:8765
- **Terminal**: The launcher shows agent status
- **Git**: Check branches for commits

## Individual Components

### Worktree Manager

```python
from scripts.setup_worktrees import WorktreeManager

manager = WorktreeManager(
    source_repo="/path/to/repo",
    workspace_dir="/tmp/workspace"
)

# Create worktrees
worktrees = manager.setup_agent_worktrees(num_agents=3)

# List worktrees
existing = manager.list_worktrees()

# Clean up
manager.remove_worktree("agent1")
```

### Agent Launcher

```python
from scripts.launch_agents import AgentLauncher

launcher = AgentLauncher(
    workspace_dir="/tmp/workspace",
    marcus_server_path="/path/to/marcus_mcp_server.py"
)

# Launch single agent
pid = launcher.launch_agent(
    agent_id="agent1",
    branch_name="agent1-work",
    worktree_path="/tmp/workspace/agent1",
    prompt_template="prompts/marcus_agent.md"
)

# Check status
status = launcher.get_agent_status("agent1")

# Terminate
launcher.terminate_agent("agent1")
```

## Customizing Agent Prompts

The prompt template (`prompts/marcus_agent.md`) supports these variables:
- `{AGENT_ID}` - Unique agent identifier
- `{BRANCH_NAME}` - Git branch for this agent
- `{WORKTREE_PATH}` - Path to agent's worktree

Example custom prompt:
```markdown
You are {AGENT_ID} working on experimental features.
Your branch is {BRANCH_NAME}.
Focus on performance optimizations.
```

## Troubleshooting

### Agents Not Starting

1. Check Marcus is running:
   ```bash
   curl http://localhost:8765/health
   ```

2. Verify Claude CLI works:
   ```bash
   claude --version
   ```

3. Check worktree creation:
   ```bash
   cd /tmp/agent-workspace/agent1
   git status
   ```

### Agents Terminating Early

1. Check agent logs (if available)
2. Verify Marcus has tasks available
3. Ensure prompt template is valid

### Git Conflicts

Each agent works on their own branch, but if you see conflicts:
1. Agents should never work on the same files
2. Marcus should coordinate to prevent this
3. Check task assignment logic

## Performance Considerations

- Each Claude agent uses significant resources
- Start with 2-3 agents before scaling up
- Monitor system resources during experiments
- Consider API rate limits

## Example Experiments

### 1. Bug Fix Sprint
```bash
# Load bug fix tasks into Marcus
# Launch 3 agents focused on bug fixes
python scripts/run_real_agents.py \
  --source-repo /path/to/project \
  --workspace /tmp/bugfix-agents \
  --marcus-server $MARCUS_PATH \
  --agents 3 \
  --prompt prompts/bugfix_specialist.md
```

### 2. Feature Development
```bash
# Load feature tasks into Marcus
# Launch 5 agents for parallel feature development
python scripts/run_real_agents.py \
  --source-repo /path/to/project \
  --workspace /tmp/feature-agents \
  --marcus-server $MARCUS_PATH \
  --agents 5 \
  --prompt prompts/feature_developer.md
```

### 3. Full SWE-bench Evaluation
```bash
# Load SWE-bench tasks
# Run with 10 agents for maximum throughput
python scripts/run_real_agents.py \
  --source-repo /path/to/swebench \
  --workspace /tmp/swebench-eval \
  --marcus-server $MARCUS_PATH \
  --agents 10
```

## Collecting Results

After experiments:

1. **From Marcus API**:
   - Task completion rates
   - Time per task
   - Agent utilization

2. **From Git**:
   - Commits per agent
   - Code quality
   - Test results

3. **From Logs**:
   - Error rates
   - Blocker frequency
   - Token usage

## Integration with Existing Experiments

To update the baseline experiment to use real agents instead of simulations:

1. Replace `PMAgentClient` with real agent launcher
2. Update metrics collection to query Marcus
3. Extend timeouts for real work
4. Add git analysis for code quality

## Safety Notes

- Always use a test repository first
- Monitor resource usage
- Set up cost limits for API usage
- Use version control for experiment configs
- Keep backups of important code

## Next Steps

1. Start with 2 agents on a simple task
2. Verify the complete workflow works
3. Scale up gradually
4. Run full benchmark experiments
5. Analyze results and optimize