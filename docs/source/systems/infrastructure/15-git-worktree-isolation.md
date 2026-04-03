# Git Worktree Isolation

## Status

| Field | Value |
|-------|-------|
| Status | Implemented |
| Version | 1.0 |
| Date | 2026-03-31 |

## Problem

Marcus runs multiple worker agents in parallel during experiments. All agents produce code that ultimately lives in a single `implementation/` directory on the `main` branch. Without isolation, parallel agents overwrite each other's files — a failure mode we call **Type A failure**.

A naive fix would be to let agents work in isolation and merge everything at the end. But Marcus decomposes projects into a DAG of tasks with fan-in dependencies. For example, "Test Time Widget" depends on "Implement Time Widget" and needs to see its code before it can run. Integration-only-at-the-end does not work because dependent tasks need to see completed work mid-experiment.

The system needs a mechanism that provides:

1. **Isolation** — agents never interfere with each other's in-progress work
2. **Visibility** — when a task completes, its code becomes visible to dependent tasks immediately
3. **Attribution** — every line of code is traceable to the agent that wrote it

## Solution

Three mechanisms work together to solve this:

### 1. Per-agent git worktrees

Each worker agent gets its own git worktree checked out on a dedicated branch named `marcus/{agent_id}`. The worktree is a separate directory with its own working tree but shares the same `.git` object store as the main repository.

### 2. Per-worktree git identity

Each worktree has `git config user.name` set to the agent's ID. This ensures `git blame` and `git log` attribute commits to the correct agent without relying on global git configuration.

### 3. Merge-on-completion

When a task passes validation and is marked DONE, Marcus merges the agent's branch back to `main`. Dependent tasks then start from an updated `main` that contains all completed work. If the merge produces conflicts, Marcus aborts the merge and sends the agent back to resolve them.

## Responsibility Matrix

| Actor | Responsibility |
|-------|---------------|
| `run_experiment.py` | `git init`, create `implementation/` on `main` |
| `spawn_agents.py` | Creates worktrees per worker via `_create_agent_worktree()`. Sets git identity. Sets working directory in agent prompt. |
| Marcus MCP (`task.py`) | `_merge_agent_branch_to_main()` in `report_task_progress()` after validation passes. Sends agent back on conflicts. |
| Worker agent | Works in its worktree, commits to its branch, resolves conflicts if sent back |
| Integration agent | Works on `main` (everything already merged), verifies and fixes |
| Epictetus | Uses `git blame` to attribute code per agent for contribution analysis |

## Directory Structure

```
experiment_dir/
├── implementation/                          <- main branch (project creator, integration, monitor)
│   ├── .git/
│   ├── CLAUDE.md
│   ├── docs/architecture/...               <- design artifacts from create_project
│   └── (merged code accumulates here)
├── implementation-agent_unicorn_1/          <- worktree, branch marcus/agent_unicorn_1
│   ├── .git -> ../implementation/.git
│   └── (agent 1's isolated work)
└── implementation-agent_unicorn_2/          <- worktree, branch marcus/agent_unicorn_2
    ├── .git -> ../implementation/.git
    └── (agent 2's isolated work)
```

Each `implementation-{agent_id}/` directory is a full working copy. The `.git` symlink back to the main repository means all branches share the same object store — merges are local operations with no network overhead.

## Branch Structure

```
main ─────●──────●──────────────────●────●────●────────->
          |      |                  |    |    |
          |  design artifacts   merge1 merge2 |
          |  (Marcus)                         integration
          |
          ├── marcus/agent_unicorn_1
          |   ●──●──●──●
          |
          └── marcus/agent_unicorn_2
              ●──●──●──●
```

The `main` branch accumulates completed work. Each agent branch diverges from `main` at the point the agent started its current task and is merged back when the task passes validation.

## Task Lifecycle with Worktrees

```
┌─────────────────────────────────────────────────────────────────┐
│                        TASK LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Agent gets task                                             │
│     └──> Works in worktree, commits to marcus/{agent_id}        │
│                                                                 │
│  2. Agent reports 100%                                          │
│     └──> Validation gate runs                                   │
│                                                                 │
│  3. Validation fails?                                           │
│     └──> Agent fixes, stays on branch, NO merge                 │
│                                                                 │
│  4. Validation passes?                                          │
│     └──> Marcus merges branch to main                           │
│                                                                 │
│  5. Merge conflicts?                                            │
│     └──> Marcus aborts merge                                    │
│     └──> Sends agent back: "git merge main, fix conflicts,      │
│          commit, report again"                                  │
│                                                                 │
│  6. Merge succeeds?                                             │
│     └──> Task truly DONE, code on main                          │
│     └──> Dependent tasks can now start                          │
│                                                                 │
│  7. Agent gets next task                                        │
│     └──> New worktree from updated main                         │
│     └──> Sees all previously completed work                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Step 7 is critical: the new worktree branches from the current `main`, which contains all merged work from completed tasks. This is how dependent tasks see the code they depend on.

## Interface Comparison

Marcus has three interfaces. Each handles worktree creation differently:

| Interface | Who creates worktrees? | Where? |
|-----------|----------------------|--------|
| `/marcus` skill | `spawn_agents.py` (automatic) | In experiment runner |
| Posidonius | `spawn_agents.py` via `run_experiment.py` (automatic) | Same code path |
| MCP direct | User (manual `git worktree add`) | User's responsibility |

For the `/marcus` skill and Posidonius interfaces, worktree creation is fully automated. When using the MCP server directly (without the experiment runner), the user is responsible for setting up git worktrees manually.

## What's NOT Handled (Deferred)

- **Feature branches** — There is no Feature entity. Tasks branch directly from `main`. A feature branch abstraction may be added later if experiments grow to need it.
- **Worktree cleanup** — Worktrees are not cleaned up after experiments. The entire experiment directory is disposable, so cleanup is unnecessary.
- **Cross-agent worktree reuse** — Each task gets a new worktree from the current `main`. Worktrees are not reused across tasks.

## Implementation Files

- `dev-tools/experiments/runners/spawn_agents.py` — `_create_agent_worktree()`, `spawn_worker()`, `create_worker_prompt()`
- `src/marcus_mcp/tools/task.py` — `_merge_agent_branch_to_main()` in `report_task_progress()`

## See Also

- [Workspace Isolation and Feature Context](workspace-isolation-and-feature-context.md) — earlier design notes on isolation
- GitHub Issues: [#250](https://github.com/marcus/marcus/issues/250), [#249](https://github.com/marcus/marcus/issues/249), [#206](https://github.com/marcus/marcus/issues/206)
