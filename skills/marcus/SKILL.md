---
name: marcus
description: >
  Launch Marcus multi-agent experiments with independent Claude agents in tmux panes.
  Use when the user says "build X with Marcus", "run a Marcus experiment",
  "spawn N agents with Marcus", "/marcus", or references the Marcus multi-agent
  framework. This skill handles experiment setup, config generation, and spawning
  independent Claude CLI agents that coordinate via the Marcus MCP server. Each
  agent runs in its own tmux pane with full autonomy. NOT for ClawTeam — this is
  specifically for the Marcus MCP-based multi-agent system.
  NOTE: "Marcus" is also the name of the MCP server that agents use for coordination.
  The /marcus skill launches experiments that USE the Marcus MCP server — they are
  complementary, not competing. The MCP server must be running before invoking this skill.
user-invocable: true
argument-hint: "<project description> [--name \"Project Name\"] [--agents N] [--complexity prototype|standard|enterprise]"
---

# Marcus Multi-Agent Experiment Launcher

You are helping the user launch a Marcus multi-agent experiment. Marcus uses an MCP
server to coordinate independent Claude CLI agents, each running in its own tmux pane.

## What You Do

1. Parse the user's request to extract: project description and agent count
2. Create an experiment directory with config.yaml and project_spec.md
3. Run `run_experiment.py` which spawns agents in tmux panes
4. Report the tmux session name so the user can attach

## Discovering Paths

Find the Marcus repo root via the installed package:

```bash
MARCUS_ROOT=$(python3 -c "from pathlib import Path; import marcus_mcp; print(Path(marcus_mcp.__file__).parent.parent.parent)")
```

From there:
- **Run script**: `${MARCUS_ROOT}/dev-tools/experiments/runners/run_experiment.py`
- **Templates**: `${MARCUS_ROOT}/dev-tools/experiments/templates/`

If the import fails, Marcus isn't installed. Tell the user:
```
Marcus is not installed. Follow the setup instructions:
  git clone https://github.com/lwgray/marcus.git
  cd marcus && pip install -e .
```

## How to Parse Arguments

The user's input comes in as `$ARGUMENTS`. Extract:
- **Project description**: Everything that describes what to build
- **Project name**: Look for `--name "Some Name"` or `--name some_name`. If not provided, derive a short name from the description.
- **Agent count**: Look for patterns like "N agents", "--agents N", "with N workers". Default: 2
- **Complexity**: Look for "--complexity prototype|standard|enterprise". Default: "prototype"

Examples:
- `/marcus Build a snake game with 3 agents` -> description="Build a snake game", name="snake_game", agents=3, complexity="prototype"
- `/marcus Build a REST API for task management` -> description="Build a REST API for task management", name="task_management_api", agents=2, complexity="prototype"
- `/marcus Build a chat app --name "ChatBuddy" with 4 agents` -> description="Build a chat app", name="ChatBuddy", agents=4, complexity="prototype"
- `/marcus Use 2 agents to build a pomodoro timer --complexity standard --name "FocusTimer"` -> description="build a pomodoro timer", name="FocusTimer", agents=2, complexity="standard"

## Step-by-Step Execution

### Step 1: Use the Current Working Directory

Write all files into the current working directory. Do NOT create or mkdir a new directory.
`run_experiment.py` will create the subdirectories it needs (`prompts/`, `logs/`, `implementation/`).

```
<cwd>/
├── config.yaml       (you create this)
├── project_spec.md   (you create this)
├── prompts/          (created by run_experiment.py)
├── logs/             (created by run_experiment.py)
└── implementation/   (created by run_experiment.py, git repo where agents write code)
```

### Step 2: Generate project_spec.md

Write the user's project description **as-is** to `project_spec.md`. Do NOT rewrite,
expand, restructure, or add sections to it. Marcus handles task decomposition — the
spec is just the raw input from the user.

### Step 3: Generate config.yaml

**CRITICAL: Always write a fresh config.yaml from the template below. Do NOT read or
preserve values from any existing config.yaml in the directory. Overwrite it completely.**

Use this exact format — field names are case-sensitive:

```yaml
project_name: "<--name value if provided, otherwise derived from description>"
project_spec_file: "project_spec.md"

project_options:
  complexity: "<parsed complexity>"  # "prototype" (default), "standard" for medium, "enterprise" for large
  provider: "sqlite"        # Uses local SQLite DB. Also supports: "planka", "github", "linear"
  mode: "new_project"       # Always new_project

agents:
  - id: "agent_unicorn_1"
    name: "Unicorn Developer 1"
    role: "full-stack"
    skills:
      - "python"
      - "javascript"
      - "typescript"
      - "react"
      - "fastapi"
      - "sqlalchemy"
      - "postgresql"
      - "database-design"
      - "rest-api"
      - "jwt"
      - "security"
      - "pytest"
      - "integration-testing"
    subagents: 0
  # Repeat for each agent...

timeouts:
  project_creation: 600
  agent_startup: 60
```

**Complexity heuristic:**
- "prototype" — Simple single-page apps, scripts, small tools
- "standard" — Most projects (APIs, full-stack apps, moderate features)
- "enterprise" — Large systems with many components, microservices, complex auth

**Agent count:** Generate one agent block per requested agent. Use incrementing IDs:
`agent_unicorn_1`, `agent_unicorn_2`, etc.

### Step 4: Initialize and Run the Experiment

First, discover the Marcus repo root:
```bash
MARCUS_ROOT=$(python3 -c "from pathlib import Path; import marcus_mcp; print(Path(marcus_mcp.__file__).parent.parent.parent)")
```

Then run it directly (using the current working directory as the experiment directory).
**IMPORTANT:** Use a 600000ms (10 minute) timeout on the Bash command. Project creation
includes AI design task generation which takes 4-6 minutes. The default 2-minute
Bash timeout will kill the process prematurely.

```bash
cd "${MARCUS_ROOT}/dev-tools/experiments" && python runners/run_experiment.py <cwd>
```

This will:
- Create `prompts/`, `logs/`, `implementation/` directories
- Initialize a git repo in `implementation/`
- Copy CLAUDE.md to `implementation/`
- Verify Marcus MCP is configured
- Create a tmux session: `marcus_<project_name_lowercase>`
- Spawn: 1 project creator + N workers + 1 monitor in tmux panes

### Step 5: Report to User

After launching, tell the user:
- The tmux session name: `marcus_<project_name_lowercase_underscored>`
- How to attach: `tmux attach -t <session_name>`
- How to navigate: Click panes (mouse enabled), Ctrl+b arrow keys, Ctrl+b n/p for windows
- How to kill: `tmux kill-session -t <session_name>`
- The experiment directory location
- Agent count: 1 creator + N workers + 1 monitor = N+2 total panes

## Important Notes

- The Marcus MCP server must be running at `http://localhost:4298/mcp` before launching
- Each agent is a fully independent `claude` CLI process with `--dangerously-skip-permissions`
- Agents coordinate via MCP tools (register_agent, request_next_task, report_task_progress, etc.)
- All agents work on the `main` branch in `implementation/`; Marcus prevents task conflicts
- MLflow tracks experiment metrics in `<experiment_dir>/mlruns/`
- The project creator agent calls `mcp__marcus__create_project` which uses AI to decompose the
  spec into tasks — this takes 30-60 seconds
- Workers wait for `project_info.json` before starting (written by project creator)
- The monitor polls every 2 minutes and calls `end_experiment` when all tasks complete

## Pre-flight Checks

Before running, verify:
1. Marcus MCP is running: check `claude mcp list` for "marcus" showing "Connected"
2. tmux is installed: `which tmux`
3. Claude CLI is available: `which claude`

If Marcus MCP is not running, tell the user:
```
Marcus MCP server is not running. Start it first:
  cd <MARCUS_ROOT> && ./marcus start
```
