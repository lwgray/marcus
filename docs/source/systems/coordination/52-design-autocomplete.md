# Design Autocomplete

## Status

| Field | Value |
|-------|-------|
| Status | Implemented |
| Version | 1.0 |
| Date | 2026-03-31 |

## Problem

When a worker agent completes a Design task and then receives an Implementation task, it over-executes. The design knowledge is still hot in the agent's context window, so the agent builds far more than its assigned scope.

**Evidence:** In the dashboard-v16 experiment, `agent_unicorn_2` completed "Design Dashboard" and was then assigned "Implement Time Widget." Instead of building only the time widget, it built BOTH widgets — 1,130 lines in a single commit. This is **Finding 2 from GH-301**: context contamination.

The root cause is that the agent has the full system design in its context when it starts the implementation task. It cannot help but act on that knowledge.

## Solution

Marcus auto-completes design tasks during `create_project`, before any agent is spawned. Design artifacts are produced by Marcus itself using targeted LLM calls, and design tasks arrive on the board already marked DONE. No agent ever touches a design task.

This is a two-phase process because it spans two different stages of project creation.

## Phase A: Generate Content (Before Board Creation)

Runs inside `create_project`, before `create_tasks_on_board()` is called.

For each design task, Marcus makes **separate LLM calls** for each artifact document:

1. Architecture document
2. API contracts
3. Data models
4. One call for decisions

Each call writes its artifact file to disk at the standard `ARTIFACT_PATHS` location.

Then Marcus sets on the task object:
- `status = DONE`
- `assigned_to = "Marcus"`
- Label: `"auto_completed"`

When `create_tasks_on_board()` runs, design tasks hit the board already DONE. No agent can grab them.

### Why separate LLM calls per artifact

A single LLM call producing all artifacts as one JSON response truncated at 7,714 characters. This caused JSON parse failures and triggered graceful degradation (the task stayed TODO and an agent grabbed it — which is exactly the context contamination problem).

Separate calls per document mirror how agents actually work. Each document is a focused, bounded response that fits comfortably within output limits.

## Phase B: Register Metadata (After State Refresh)

Runs inside `create_project_from_natural_language()`, after `state.refresh_project_state()` has populated the MCP state object.

Phase B registers the artifacts and decisions through MCP tools:

- `log_artifact()` for each file produced in Phase A — populates `state.task_artifacts`
- `log_decision()` for each architectural decision — populates `state.context.decisions`

Phase B does **NOT** call `report_task_progress`. The task is already DONE from Phase A.

Workers discover design artifacts and decisions through `get_task_context` when they start dependent tasks.

## Why Two Phases

```
create_project flow:

  ┌──────────────────────────┐
  │  Phase A                 │
  │  - LLM calls             │   Needs to run BEFORE create_tasks_on_board()
  │  - Write files to disk   │   so tasks are born DONE (prevents race
  │  - Set status = DONE     │   condition where agents grab design tasks)
  │  - Set auto_completed    │
  └──────────┬───────────────┘
             │
             v
  ┌──────────────────────────┐
  │  create_tasks_on_board() │   Design tasks arrive DONE
  └──────────┬───────────────┘
             │
             v
  ┌──────────────────────────┐
  │  refresh_project_state() │   Populates MCP state object
  └──────────┬───────────────┘
             │
             v
  ┌──────────────────────────┐
  │  Phase B                 │   Needs MCP state object, which is only
  │  - log_artifact()        │   available after refresh_project_state()
  │  - log_decision()        │
  └──────────────────────────┘
```

The two phases serve different purposes and cannot be combined. Phase A needs to complete before board creation to prevent the race condition. Phase B needs the MCP `state` object which only exists after `refresh_project_state()`.

## Why MCP Tools for Registration

The logging functions (`log_artifact`, `log_decision`) require the MCP `state` object because they write to multiple destinations:

- `state.task_artifacts` — discovery for `get_task_context`
- `state.context.decisions` — cross-referencing for architectural decisions
- Experiment monitor — observability
- Conversation logs — debugging
- Project history — persistence

Bypassing MCP tools and writing directly to these stores means broken discovery and missing observability. The MCP tools are the single source of truth for registration.

## Prompt Constraints

Design artifact prompts explicitly say **"describe WHAT and WHY, not HOW."**

Design artifacts describe:
- Behavior and responsibilities
- Data flow between components
- Integration boundaries and contracts

Design artifacts do NOT specify:
- File names or directory structure
- Function signatures or class hierarchies
- Prop interfaces or component APIs
- Implementation details of any kind

The implementing agent decides all of those.

**The design principle:** "No implementation agent should ever be able to reconstruct the full system from what Marcus gave it. If it can, Marcus gave it too much."

## Graceful Degradation

If any LLM call in Phase A fails, the design task stays TODO and a worker agent handles it the old way. The experiment continues — it just loses the context contamination protection for that task.

This is a deliberate choice. The auto-complete feature is an optimization, not a requirement. The system never breaks if it fails.

## Agent Output Contract

Auto-completed design tasks produce the same outputs a worker agent would:

| Output | MCP Tool | Purpose |
|--------|----------|---------|
| Artifacts (files + metadata) | `log_artifact()` | `get_task_context` discovery |
| Decisions (what/why/impact) | `log_decision()` | Architectural decision cross-referencing |
| Task status DONE | Set in Phase A | Never assignable to agents |

From the perspective of a worker agent calling `get_task_context`, there is no difference between a design task completed by Marcus and one completed by another agent.

## Cato Integration

Tasks with the `"auto_completed"` label are filtered from the default board view in `_filter_tasks_by_view()`. Design tasks are hidden from the DAG and swim lane views, but their artifacts and decisions remain visible on dependent task cards.

This keeps the board focused on work that agents are actually doing, while preserving full access to design context where it matters.

## Implementation Files

- `src/integrations/nlp_tools.py` — `_generate_design_content()` (Phase A), `_register_design_via_mcp()` (Phase B), `_ARTIFACT_PROMPT`, `_DECISIONS_PROMPT`
- `src/integrations/nlp_tools.py` — Wiring in `create_project_from_description()` (Phase A) and `create_project_from_natural_language()` (Phase B)
- `cato_src/core/aggregator.py` — `_filter_tasks_by_view()` filters `auto_completed` label

## See Also

- [Git Worktree Isolation](git-worktree-isolation.md) — how agents are isolated during experiments
- GitHub Issues:
  - [#301](https://github.com/marcus/marcus/issues/301) — Four findings from dashboard-v16, including Finding 2 (context contamination)
  - [#297](https://github.com/marcus/marcus/issues/297) — Original design autocomplete implementation
  - [#300](https://github.com/marcus/marcus/issues/300) — Reverted attempt
  - [#267](https://github.com/marcus/marcus/issues/267) — Topology-aware decomposition
