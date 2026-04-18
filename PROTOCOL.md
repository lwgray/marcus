# Marcus Agent Protocol

This document describes the protocol any agent must follow to participate in a
Marcus-coordinated project. It is the developer-facing complement to
[`prompts/Agent_prompt.md`](prompts/Agent_prompt.md), which is the agent-facing
version of the same specification.

**If you are building a runner** (a system that spawns agents and connects them
to Marcus), this document tells you what your agents must do.

**If you are an agent author** (writing the prompt your agent will follow),
use [`prompts/Agent_prompt.md`](prompts/Agent_prompt.md) directly — it is written
to be copied verbatim into your agent's system prompt.

---

## Overview

Marcus is an MCP server. Any agent that can call MCP tools can participate in a
Marcus project. The agent does not need to be Claude — it needs to speak
[Model Context Protocol](https://modelcontextprotocol.io/).

Marcus exposes its interface at `http://localhost:4298/mcp` by default.

---

## Required MCP Tools

An agent must be capable of calling these tools:

| Tool | Purpose |
|---|---|
| `create_project` | Bootstrap the project: decompose a description into tasks on the board |
| `register_agent` | Announce agent identity to Marcus at startup |
| `request_next_task` | Pull the next available task from the board |
| `get_task_context` | Fetch dependency artifacts before starting work |
| `report_task_progress` | Report progress at milestones (25/50/75/100%) |
| `report_blocker` | Report a blocking problem and receive AI suggestions |
| `log_decision` | Record an architectural decision to the board |
| `log_artifact` | Store a file reference (spec, design doc, schema) |
| `get_experiment_status` | Check whether the experiment is still running |

---

## Two Agent Roles

Every run has two distinct roles. One agent plays **project creator**; the rest
are **workers**. A single agent can play both roles (create, then immediately
enter the work loop).

### Project Creator

The creator calls `create_project` once to bootstrap the board:

```
create_project(
    description:  str,   # natural language description of what to build
    project_name: str,   # name for the project board
    options:      dict   # optional — e.g. {"num_agents": 3}
)
```

Returns `recommended_agents`, `project_id`, and the full task graph. When
`create_project` returns, tasks are on the board and immediately available.

### Workers

Workers call `register_agent` and enter the work loop. They never call
`create_project`.

---

## Agent Lifecycle

Every agent follows this sequence:

### 1. Register (once at startup)

```
register_agent(
    agent_id:  str,   # unique within this experiment
    name:      str,   # display name
    role:      str,   # e.g. "full-stack", "backend", "synthetic"
    skills:    list[str]
)
```

Call this exactly once. Do not re-register during a run.

### 2. Work Loop

Repeat until `get_experiment_status` returns `is_running = false`:

```
a. request_next_task()
   → returns: task | retry_after_seconds

b. If no task: sleep retry_after_seconds, then goto (a)
   (Leases are being recovered. Do not exit.)

c. If task received:
   i.  If task has dependencies: call get_task_context(task_id)
   ii. Do the work
   iii. Call report_task_progress at 25%, 50%, 75%, 100%
   iv. Immediately call request_next_task (do not wait)
```

### 3. Exit

When `get_experiment_status` returns:
- `experiment_started = false` → startup window, sleep 10s and re-poll
- `experiment_started = true, is_running = true` → active, keep working
- `experiment_started = true, is_running = false` → done, exit

---

## Experiment Completion

Marcus computes completion from board state:

```
in_progress_tasks == 0
AND (completed_tasks + blocked_tasks) == total_tasks
```

When this condition is met, Marcus flips `is_running` to false. Agents do not
compute this themselves — they poll `get_experiment_status` and trust the signal.

Blocked tasks count as terminal. The board will not stall waiting for them.

---

## The Three Agent Invariants

These are non-negotiable. Violating them breaks the coordination model:

1. **Agents self-select work.** Agents pull tasks via `request_next_task`.
   Marcus never pushes. No runner should pre-assign tasks to specific agents.

2. **Agents make all implementation decisions.** Marcus communicates WHAT to
   build and WHY. It never specifies HOW — no library choices, no file structure,
   no internal architecture. Two agents given the same task must be free to
   produce legitimately different implementations.

3. **Agents communicate exclusively through the board.** No agent-to-agent
   messages. No direct coordination. The board is the only channel.

---

## What Marcus Guarantees

- **Task isolation.** Only one agent holds a lease on any task at a time.
- **Dependency ordering.** `request_next_task` only returns tasks whose
  dependencies are complete. Agents never need to check this themselves.
- **Lease recovery.** If an agent dies mid-task, Marcus detects the expired
  lease and returns the task to the pool.
- **Artifact routing.** `get_task_context` returns artifacts from dependency
  tasks. Agents do not need to know which task produced an artifact — Marcus
  walks the DAG.
- **Scope annotation.** Dependency artifacts carry a `scope_annotation` field:
  `in_scope` (implement fully) or `reference_only` (do not implement, read for
  context only).

---

## Minimal Conforming Runner

A runner is any system that:

1. Starts one agent as **project creator** — it calls `create_project` via Marcus
   and writes `project_info.json` when complete.
2. Starts N agents as **workers** — they wait for `project_info.json`, then
   enter the work loop above.
3. Optionally starts a **monitor** — polls `get_experiment_status` and calls
   `end_experiment` when `is_running` flips to false.

The reference runner is
[`dev-tools/experiments/runners/spawn_agents.py`](dev-tools/experiments/runners/spawn_agents.py),
which implements this pattern using Claude CLI agents in tmux panes.

---

## Implementing a New Runner

To add support for a different agent runtime (LangGraph, AutoGen, Codex, etc.):

1. Connect your agent to the Marcus MCP server at `http://localhost:4298/mcp`.
2. Copy [`prompts/Agent_prompt.md`](prompts/Agent_prompt.md) into your agent's
   system prompt (or translate it to your runtime's prompt format).
3. Ensure your runner implements the project creator / worker / monitor split
   described above.
4. Validate against the synthetic agent test harness (see issue
   [#383](https://github.com/lwgray/marcus/issues/383)) — if a synthetic agent
   can complete an experiment end-to-end with your runner, your integration is
   conforming.

---

## Quick Reference

```
Creator:   create_project(description, project_name) → board populated, tasks ready
Startup:   register_agent
Work loop: request_next_task → [get_task_context] → work → report_task_progress(100%) → repeat
Exit:      get_experiment_status → is_running=false → exit
```

See [`prompts/Agent_prompt.md`](prompts/Agent_prompt.md) for the complete
agent-facing specification including artifact management, blocker workflow,
git conventions, and progress reporting format.
