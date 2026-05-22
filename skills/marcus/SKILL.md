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
argument-hint: "<project description> [--name \"Project Name\"] [--agents N] [--complexity prototype|standard|enterprise] [--stall-timeout N] [--decomposer contract_first|feature_based] [--epictetus] [--model <model>] [--harness claude|codex|gemini]"
---

# Marcus Multi-Agent Experiment Launcher

You are helping the user launch a Marcus multi-agent experiment. Marcus uses an MCP
server to coordinate independent Claude CLI agents, each running in its own tmux pane.

## EXECUTION RULES — READ FIRST, THESE OVERRIDE EVERYTHING BELOW

This skill runs **fully autonomously**. When `/marcus` is invoked you perform
**every step, Step 1 through Step 6, in one continuous pass** and end by launching
the experiment.

1. **NEVER stop to ask the user for confirmation.** Do not ask "Continue?",
   "Should I proceed?", "Ready to launch?", or anything similar. There is no
   approval checkpoint. There is no pause. Run all six steps and launch.
2. **The ONLY thing that stops you is a hard failure in Step 1 (Pre-flight).**
   If a pre-flight check fails, print the exact fix message for that failure and
   stop. That is the only permitted stopping point in this entire skill.
3. **Do the steps strictly in numbered order: 1, 2, 3, 4, 5, 6.** Do not skip a
   step. Do not reorder. Do not do "part of" a step and move on. Finish each step
   completely before starting the next.
4. **Do not narrate intentions and then wait.** Saying "I'll write the files now"
   followed by stopping is a failure. If you say you will do something, do it in
   the same turn.
5. **If the user gave a separate instruction in their message** (e.g. "don't do
   anything", "just answer this", "explain only"), that instruction wins — obey it
   and do NOT run the steps. The autonomy rule applies only to a plain `/marcus`
   invocation with no overriding instruction.

Definition of done: a tmux session is spawned and you have reported its name to
the user (Step 6). Anything short of that is an incomplete run.

## Overview of the Six Steps

1. **Pre-flight checks** — verify MCP server, tmux, harness CLI. (Only stopping point.)
2. **Parse arguments** — extract description, name, agent count, flags.
3. **Write `project_spec.md`** into the current working directory.
4. **Write `config.yaml`** into the current working directory.
5. **Run `run_experiment.py`** — launches the long-lived control loop (background).
6. **Report** the tmux session name and attach instructions to the user.

## Discovering Paths

Find the Marcus repo root via the installed package:

```bash
MARCUS_ROOT=$(python3 -c "from pathlib import Path; import marcus_mcp; print(Path(marcus_mcp.__file__).parent.parent.parent)")
```

From there:
- **Run script**: `${MARCUS_ROOT}/dev-tools/experiments/runners/run_experiment.py`
- **Templates**: `${MARCUS_ROOT}/dev-tools/experiments/templates/`

If the import fails, Marcus isn't installed. Tell the user this and stop:
```
Marcus is not installed. Follow the setup instructions:
  git clone https://github.com/lwgray/marcus.git
  cd marcus && pip install -e .
```

---

## Step 1: Pre-flight Checks (the ONLY stopping point)

Run all three checks before anything else. If any check fails, print its exact
fix message and STOP. If all three pass, continue immediately to Step 2 — do not
ask the user anything.

**Check 1 — Marcus MCP server is running.** Run `claude mcp list` (claude
harness), `codex mcp list` (codex harness), or `gemini mcp list` (gemini
harness) and confirm "marcus" shows "Connected".
If not running, print and stop:
```
Marcus MCP server is not running. Start it first:
  cd <MARCUS_ROOT> && ./marcus start
```

**Check 2 — tmux is installed.** Run `which tmux`. If missing, tell the user to
install tmux and stop.

**Check 3 — harness CLI is available.** Run `which claude` (default),
`which codex` (when `--harness codex`), or `which gemini` (when
`--harness gemini`). If missing, tell the user to install the
CLI and stop.

If `--harness codex` and Marcus MCP is not yet registered with codex, print and stop:
```
codex mcp add marcus --url http://localhost:4298/mcp/
```

```
codex mcp add marcus --url http://localhost:4298/mcp/
```

If `--harness gemini` and Marcus MCP is not yet registered with gemini, print and stop:
```
gemini mcp add --transport http --scope user marcus http://localhost:4298/mcp
```

**All three passed → go straight to Step 2. Do not pause. Do not ask.**

---

## Step 2: Parse Arguments

The user's input comes in as `$ARGUMENTS`. Extract:
- **Project description**: Everything that describes what to build
- **Project name**: Look for `--name "Some Name"` or `--name some_name`. If not provided, derive a short name from the description.
- **Agent ceiling**: Look for "N agents", "--agents N", "with N workers". **Default: unset.** When the user does NOT pass `--agents`, omit `max_agents` from config.yaml entirely — Marcus then sizes the agent pool to each DAG layer's full width (peaks at the widest layer; full parallelism). Only when `--agents N` is explicitly given, write `max_agents: N` — a hard cap the pool never exceeds. Use `--agents N` to cap on a machine that cannot handle many concurrent agents.
- **Complexity**: Look for "--complexity prototype|standard|enterprise". Default: "prototype"
- **Stall timeout**: Look for "--stall-timeout N" (minutes). Default: 20. Sets `stall_timeout_minutes` in config.yaml — the runner's control loop tears down the tmux session if task counts don't change for that long, so a stalled run does not hang. Pass `--stall-timeout 0` to disable the watchdog.
- **Decomposer**: Look for "--decomposer contract_first|feature_based". Default: "contract_first" (as of v0.3.4). This controls Marcus's task decomposition strategy (GH-320):
  - `contract_first` — default. Generates interface contracts before decomposition. Board is fully populated before any agent starts (no Phase A race). Each agent owns one side of a contract. Best for tightly-coupled projects (games, dashboards, state machines).
  - `feature_based` — legacy path, splits tasks by functional requirement. Fine for loosely-coupled projects where features don't share files.
- **Epictetus mode**: Look for `--epictetus` flag. Default: not set (false). When present, the runner does NOT tear down the tmux session after the experiment completes — it stays alive for Epictetus post-experiment interrogation.
- **Agent model**: Look for `--model <value>`. Default: not set — Marcus reads `ai.model` from `config_marcus.json` and uses that same value for the spawned Agent CLI processes (so by default Planners and Agents share one model). When `--model X` is provided, X overrides for THIS run only and applies to all spawned panes (project creator + workers). The same string is passed verbatim to whichever harness is active — accepts `claude --model` values (e.g. `sonnet`, `opus`, `haiku`, `claude-haiku-4-5-20251001`) or `codex --model` values (e.g. `gpt-5-codex`, `o3`). No client-side validation against per-harness namespaces — invalid model names surface as CLI errors inside the agent panes. Affects ONLY the spawned Agents — Marcus's Planner model continues to read from `config_marcus.json`.
- **Agent harness**: Look for `--harness claude|codex|gemini`. Default: `claude`. `claude` spawns Anthropic's claude CLI with `--dangerously-skip-permissions`. `codex` spawns OpenAI's codex CLI with `exec --dangerously-bypass-approvals-and-sandbox` (the documented form of "YOLO mode" — sets `approval: never, sandbox: danger-full-access`). `gemini` spawns Google's gemini CLI with `--skip-trust --yolo` (bypass the trusted-directory dialog and auto-approve all tool calls). All agents in a single experiment use the same harness; mixed-harness teams are out of scope for v1. The runner pre-flights `which <cli>` and fails fast if the binary is missing.

After extracting all values, print one line summarizing the parse (description,
name, agents, complexity, decomposer, model, harness) so the user can see it —
then **continue immediately to Step 3. Printing the parse is NOT a checkpoint.
Do not wait for a reply.**

Examples:
- `/marcus Build a snake game with 3 agents` -> description="Build a snake game", name="snake_game", agents=3, complexity="prototype", decomposer="contract_first"
- `/marcus Build a REST API for task management` -> description="Build a REST API for task management", name="task_management_api", agents=2, complexity="prototype", decomposer="contract_first"
- `/marcus Build a chat app --name "ChatBuddy" with 4 agents` -> description="Build a chat app", name="ChatBuddy", agents=4, complexity="prototype", decomposer="contract_first"
- `/marcus Use 2 agents to build a pomodoro timer --complexity standard --name "FocusTimer"` -> description="build a pomodoro timer", name="FocusTimer", agents=2, complexity="standard", decomposer="contract_first"
- `/marcus Build a snake game with 2 agents --decomposer feature_based` -> description="Build a snake game", name="snake_game", agents=2, complexity="prototype", decomposer="feature_based"
- `/marcus --decomposer feature_based Build a weather dashboard with 3 agents` -> description="Build a weather dashboard", name="weather_dashboard", agents=3, complexity="prototype", decomposer="feature_based"
- `/marcus Build a snake game --model haiku` -> description="Build a snake game", name="snake_game", agents=2, complexity="prototype", decomposer="contract_first", model="haiku", harness="claude"
- `/marcus Build a chat app with 3 agents --model claude-haiku-4-5-20251001` -> description="Build a chat app", name="chat_app", agents=3, complexity="prototype", decomposer="contract_first", model="claude-haiku-4-5-20251001", harness="claude"
- `/marcus Build a TODO CLI with 2 agents --harness codex --model gpt-5-codex` -> description="Build a TODO CLI", name="todo_cli", agents=2, complexity="prototype", decomposer="contract_first", model="gpt-5-codex", harness="codex"
- `/marcus Build a snake game --harness codex` -> description="Build a snake game", name="snake_game", agents=2, complexity="prototype", decomposer="contract_first", harness="codex" (model left unset; codex uses its global default)
- `/marcus build a ping pong html game --harness gemini` -> description="build a ping pong html game", name="ping_pong_html_game", agents=2, complexity="prototype", decomposer="contract_first", harness="gemini" (model left unset; gemini uses its global default)
- `/marcus Build a TODO CLI --harness gemini --model gemini-2.5-pro` -> description="Build a TODO CLI", name="todo_cli", agents=2, complexity="prototype", decomposer="contract_first", model="gemini-2.5-pro", harness="gemini"

---

## Step 3: Write project_spec.md

Write all files into the **current working directory**. Do NOT create or mkdir a
new directory. `run_experiment.py` will create the subdirectories it needs
(`prompts/`, `logs/`, `implementation/`).

```
<cwd>/
├── config.yaml       (you create this — Step 4)
├── project_spec.md   (you create this — Step 3)
├── prompts/          (created by run_experiment.py)
├── logs/             (created by run_experiment.py)
└── implementation/   (created by run_experiment.py, git repo where agents write code)
```

Write the user's project description **as-is** to `project_spec.md`. Do NOT rewrite,
expand, restructure, or add sections to it. Marcus handles task decomposition — the
spec is just the raw input from the user.

Then continue immediately to Step 4.

---

## Step 4: Write config.yaml

**CRITICAL: Always write a fresh config.yaml from the template below. Do NOT read or
preserve values from any existing config.yaml in the directory. Overwrite it completely.**

Use this exact format — field names are case-sensitive:

```yaml
project_name: "<--name value if provided, otherwise derived from description>"
project_spec_file: "project_spec.md"

# max_agents: ONLY include this line if the user passed --agents N.
# When --agents N was given, write:  max_agents: N
# When --agents was NOT given, omit the line entirely — Marcus sizes the
# agent pool to each DAG layer's full width (full parallelism).

stall_timeout_minutes: 20   # Runner tears down the tmux session if task counts don't change for this many minutes. 0 disables the watchdog.

project_options:
  complexity: "<parsed complexity>"  # "prototype" (default), "standard" for medium, "enterprise" for large
  provider: "sqlite"        # Uses local SQLite DB. Also supports: "planka", "github", "linear"
  mode: "new_project"       # Always new_project
  decomposer: "<parsed decomposer>"  # "contract_first" (default) or "feature_based" (GH-320)

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

**Decomposer rule:** Default is `contract_first` as of v0.3.4. Only
override to `feature_based` when the user passes `--decomposer feature_based`
explicitly. Do NOT infer the decomposer from phrases in the project
description — "don't use contract first" and "use contract first" both
contain the same substring, and a substring match would pick the wrong
strategy half the time. If the flag is absent, always set
`decomposer: "contract_first"`.

**Agent blocks:** Write **two** agent blocks — they are only the *template
pool* the runner cycles through for agent names and skills. The pool's length
does NOT set or cap the agent count: the runner sizes the pool to each DAG
layer's width, bounded only by `max_agents` if `--agents N` was passed. Use
IDs `agent_unicorn_1`, `agent_unicorn_2`.

Then continue immediately to Step 5.

---

## Step 5: Run the Experiment

Discover the Marcus repo root:
```bash
MARCUS_ROOT=$(python3 -c "from pathlib import Path; import marcus_mcp; print(Path(marcus_mcp.__file__).parent.parent.parent)")
```

`run_experiment.py` is a **long-lived control loop**. It spawns the project
creator, then polls Marcus and spawns ephemeral one-task worker agents layer by
layer until the project finishes, then tears down the tmux session. It runs for
the **entire experiment** — many minutes — so it MUST be launched as a
**background process**: pass `run_in_background: true` to the Bash tool. Do NOT
run it with a foreground timeout — a timeout would kill the runner mid-experiment.

Use the current working directory as the experiment directory. If `--epictetus`,
`--model <value>`, or `--harness <value>` were passed, append them; flags combine.

```bash
# Default (claude harness):
cd "${MARCUS_ROOT}/dev-tools/experiments" && python runners/run_experiment.py <cwd>

# With Epictetus mode (tmux session kept alive for interrogation):
cd "${MARCUS_ROOT}/dev-tools/experiments" && python runners/run_experiment.py <cwd> --epictetus

# With agent model override (spawned panes run on this model):
cd "${MARCUS_ROOT}/dev-tools/experiments" && python runners/run_experiment.py <cwd> --model claude-haiku-4-5-20251001

# With codex harness:
cd "${MARCUS_ROOT}/dev-tools/experiments" && python runners/run_experiment.py <cwd> --harness codex --model gpt-5-codex
```

This will:
- Create `prompts/`, `logs/`, `implementation/` directories
- Initialize a git repo in `implementation/`
- Create a tmux session: `marcus_<project_name_lowercase>`
- Spawn the project creator, then run the control loop: poll Marcus and spawn
  ephemeral one-task agents to match the active task layer (agent count is
  dynamic, capped by `max_agents`), then tear down the tmux session when the
  project completes or stalls
- Mirror live progress to `<cwd>/logs/runner.log`

Then continue immediately to Step 6.

---

## Step 6: Report to User

The experiment is now running as a background process. Tell the user:
- The tmux session name: `marcus_<project_name_lowercase_underscored>`
- Watch the control loop live: `tail -f <cwd>/logs/runner.log`
- Watch the agents: `tmux attach -t <session_name>` (click panes, Ctrl+b arrows, Ctrl+b n/p for windows)
- How to kill: `tmux kill-session -t <session_name>`
- The experiment directory location
- The runner spawns worker agents dynamically as the task graph opens up, and
  tears down the tmux session itself when the project completes.

This completes the run.

## Important Notes

- The Marcus MCP server must be running at `http://localhost:4298/mcp` before launching
- Each agent is a fully independent harness CLI process: `claude --dangerously-skip-permissions` (default), `codex exec --dangerously-bypass-approvals-and-sandbox` when `--harness codex`, or `gemini --skip-trust --yolo` when `--harness gemini`
- Agents coordinate via MCP tools (register_agent, request_next_task, report_task_progress, etc.)
- All agents work on the `main` branch in `implementation/`; Marcus prevents task conflicts
- MLflow tracks experiment metrics in `<experiment_dir>/mlruns/`
- The project creator agent calls `mcp__marcus__create_project` which uses AI to decompose the
  spec into tasks — this takes 30-60 seconds
- Workers wait for `project_info.json` before starting (written by project creator)
- Each worker is ephemeral — it does exactly one task, then its process exits
- The runner's control loop detects completion (Marcus flips `is_running`) and tears down the tmux session; there is no separate monitor agent
