---
name: marcus
description: >
  Launch Marcus multi-agent experiments with independent CLI agents in tmux panes.
  Use when the user says "build X with Marcus", "run a Marcus experiment",
  "spawn N agents with Marcus", "/marcus", or references the Marcus multi-agent
  framework. This skill handles experiment setup, config generation, and spawning
  independent agent CLI processes that coordinate via the Marcus MCP server. Each
  agent runs in its own tmux pane with full autonomy. NOT for ClawTeam — this is
  specifically for the Marcus MCP-based multi-agent system.
  NOTE: "Marcus" is also the name of the MCP server that agents use for coordination.
  The /marcus skill launches experiments that USE the Marcus MCP server — they are
  complementary, not competing. The MCP server must be running before invoking this skill.
  The Marcus MCP server is agent-agnostic; this skill supports both Anthropic's
  claude CLI and OpenAI's codex CLI as agent harnesses (selected via --harness).
user-invocable: true
argument-hint: "<project description> [--name \"Project Name\"] [--agents N] [--complexity prototype|standard|enterprise] [--decomposer contract_first|feature_based] [--epictetus] [--model <model>] [--harness claude|codex]"
---

# Marcus Multi-Agent Experiment Launcher (Codex)

You are helping the user launch a Marcus multi-agent experiment. Marcus uses an MCP
server to coordinate independent agent CLI processes, each running in its own tmux pane.

This skill is invoked from within the Codex CLI. When the user runs `/marcus` from
inside Codex, the typical (but not required) intent is to spawn **codex** agents —
pass `--harness codex` to make that explicit. The skill also accepts `--harness
claude` to spawn Anthropic CLI agents from a Codex driver session if that's what
the user wants.

## What You Do

1. Parse the user's request to extract: project description, agent count, harness, model
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
- **Decomposer**: Look for "--decomposer contract_first|feature_based". Default: "contract_first" (as of v0.3.4). This controls Marcus's task decomposition strategy (GH-320):
  - `contract_first` — default. Generates interface contracts before decomposition. Board is fully populated before any agent starts (no Phase A race). Each agent owns one side of a contract. Best for tightly-coupled projects (games, dashboards, state machines).
  - `feature_based` — legacy path, splits tasks by functional requirement. Fine for loosely-coupled projects where features don't share files.
- **Epictetus mode**: Look for `--epictetus` flag. Default: not set (false). When present, the monitor agent does NOT kill the tmux session after the experiment completes — it stays alive for Epictetus post-experiment interrogation.
- **Agent model**: Look for `--model <value>`. Default: not set — Marcus reads `ai.model` from `config_marcus.json` and uses that same value for the spawned Agent CLI processes (so by default Planners and Agents share one model). When `--model X` is provided, X overrides for THIS run only and applies to all spawned panes (project creator + workers + monitor). The same string is passed verbatim to whichever harness is active — accepts `claude --model` values (e.g. `sonnet`, `opus`, `haiku`, `claude-haiku-4-5-20251001`) or `codex --model` values (e.g. `gpt-5-codex`, `o3`). No client-side validation against per-harness namespaces — invalid model names surface as CLI errors inside the agent panes. Affects ONLY the spawned Agents — Marcus's Planner model continues to read from `config_marcus.json`.
- **Agent harness**: Look for `--harness claude|codex`. Default: `claude` (matches `run_experiment.py` default). When invoked from inside Codex CLI, you typically want `--harness codex` — but the runner does not auto-detect the caller. `codex` spawns `codex exec --dangerously-bypass-approvals-and-sandbox` (the documented form of "YOLO mode" — sets `approval: never, sandbox: danger-full-access`). All agents in a single experiment use the same harness; mixed-harness teams are out of scope for v1. The runner pre-flights `which <cli>` and fails fast if the binary is missing.

Examples:
- `/marcus Build a snake game with 3 agents` -> description="Build a snake game", name="snake_game", agents=3, complexity="prototype", decomposer="contract_first", harness="claude"
- `/marcus Build a TODO CLI with 2 agents --harness codex` -> description="Build a TODO CLI", name="todo_cli", agents=2, complexity="prototype", decomposer="contract_first", harness="codex"
- `/marcus Build a TODO CLI --harness codex --model gpt-5-codex` -> description="Build a TODO CLI", name="todo_cli", agents=2, complexity="prototype", decomposer="contract_first", model="gpt-5-codex", harness="codex"
- `/marcus Build a snake game with 4 agents --harness codex --model o3` -> description="Build a snake game", name="snake_game", agents=4, complexity="prototype", decomposer="contract_first", model="o3", harness="codex"

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

# Harness selection: omit the field (defaults to 'claude') or set explicitly.
# CLI flag --harness on run_experiment.py overrides this value.
harness: "<parsed harness>"  # "claude" (default) or "codex"

project_options:
  complexity: "<parsed complexity>"
  provider: "sqlite"
  mode: "new_project"
  decomposer: "<parsed decomposer>"

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

**Decomposer rule:** Default is `contract_first` as of v0.3.4. Only override to
`feature_based` when the user passes `--decomposer feature_based` explicitly.

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

Append `--epictetus`, `--model <value>`, and/or `--harness <value>` to the command
based on what the user passed. All flags combine.

```bash
# Codex harness, codex's default model:
cd "${MARCUS_ROOT}/dev-tools/experiments" && python runners/run_experiment.py <cwd> --harness codex

# Codex harness with explicit model:
cd "${MARCUS_ROOT}/dev-tools/experiments" && python runners/run_experiment.py <cwd> --harness codex --model gpt-5-codex

# Claude harness from inside Codex (rare but supported):
cd "${MARCUS_ROOT}/dev-tools/experiments" && python runners/run_experiment.py <cwd> --harness claude
```

This will:
- Create `prompts/`, `logs/`, `implementation/` directories
- Initialize a git repo in `implementation/`
- Copy CLAUDE.md to `implementation/`
- Pre-flight `which claude` or `which codex` depending on `--harness`
- Create a tmux session: `marcus_<project_name_lowercase>`
- Spawn: 1 project creator + N workers + 1 monitor in tmux panes
- For codex harness, each pane runs `codex exec --dangerously-bypass-approvals-and-sandbox` with the Marcus MCP server registered via `codex mcp add marcus --url http://localhost:4298/mcp/`

### Step 5: Report to User

After launching, tell the user:
- The tmux session name: `marcus_<project_name_lowercase_underscored>`
- The harness being used (claude or codex)
- How to attach: `tmux attach -t <session_name>`
- How to navigate: Click panes (mouse enabled), Ctrl+b arrow keys, Ctrl+b n/p for windows
- How to kill: `tmux kill-session -t <session_name>`
- The experiment directory location
- Agent count: 1 creator + N workers + 1 monitor = N+2 total panes

## Important Notes

- The Marcus MCP server must be running at `http://localhost:4298/mcp` before launching
- Each agent is a fully independent harness CLI process. For codex: `codex exec --dangerously-bypass-approvals-and-sandbox` (approval=never, sandbox=danger-full-access). For claude: `claude --dangerously-skip-permissions`.
- Agents coordinate via MCP tools (register_agent, request_next_task, report_task_progress, etc.)
- All agents work on isolated git worktrees in `implementation/`; Marcus prevents task conflicts
- MLflow tracks experiment metrics in `<experiment_dir>/mlruns/`
- The project creator agent calls `mcp__marcus__create_project` which uses AI to decompose the spec into tasks — this takes 30-60 seconds
- Workers wait for `project_info.json` before starting (written by project creator)
- The monitor polls every 2 minutes and calls `end_experiment` when all tasks complete

## Pre-flight Checks

Before running, verify:
1. Marcus MCP is registered for the active harness:
   - claude: `claude mcp list` shows "marcus"
   - codex: `codex mcp list` shows "marcus"
2. tmux is installed: `which tmux`
3. Harness CLI is on PATH: `which claude` or `which codex`

If Marcus MCP is not running, tell the user:
```
Marcus MCP server is not running. Start it first:
  cd <MARCUS_ROOT> && ./marcus start
```

If `--harness codex` and Marcus MCP is not yet registered with codex, tell the user:
```
codex mcp add marcus --url http://localhost:4298/mcp/
```

If `--harness claude` and Marcus MCP is not yet registered with claude, tell the user:
```
claude mcp add marcus -t http http://localhost:4298/mcp
```
