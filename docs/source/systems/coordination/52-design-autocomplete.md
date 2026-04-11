# Design Autocomplete

## Status

| Field | Value |
|-------|-------|
| Status | Implemented |
| Version | 2.0 |
| Date | 2026-04-11 |

## Problem

When a worker agent completes a Design task and then receives an Implementation task, it over-executes. The design knowledge is still hot in the agent's context window, so the agent builds far more than its assigned scope.

**Evidence:** In the dashboard-v16 experiment, `agent_unicorn_2` completed "Design Dashboard" and was then assigned "Implement Time Widget." Instead of building only the time widget, it built BOTH widgets — 1,130 lines in a single commit. This is **Finding 2 from GH-301**: context contamination.

The root cause is that the agent has the full system design in its context when it starts the implementation task. It cannot help but act on that knowledge.

## Solution

Marcus auto-completes design tasks during `create_project` without letting any agent touch them. Design artifacts are produced by Marcus itself using targeted LLM calls. The implementation runs in two phases that together live inside a single background task, `_run_design_phase`:

- **Phase A** generates design artifacts to disk via parallel LLM calls.
- **Phase B** registers those artifacts into the MCP `state.task_artifacts` so downstream implementation tasks discover them via `get_task_context`.

Both phases must run in lockstep. They used to be wired independently and that split broke silently when one was refactored — see [Regression History](#regression-history) below.

## Race Mitigation: `assigned_to="Marcus"`

Design tasks are born with `assigned_to="Marcus"` rather than born DONE. Marcus's task assignment filter treats any task whose `assigned_to` is `"Marcus"` as off-limits to agents regardless of status. This prevents agents from grabbing design tasks during the window between `create_tasks_on_board()` and the kanban DONE update that marks Phase A complete.

This is the mechanism that replaced the original "born DONE" invariant when Phase A moved to a background task in GH-314. The race still exists at the board level (tasks are TODO for a few seconds), but the assignment filter closes it at the allocation layer.

## Background Execution Model

`_run_design_phase` runs as an `asyncio.ensure_future` background task, scheduled after `create_tasks_on_board()` returns and BEFORE `create_project_from_description()` returns to its caller. The MCP tool response is not blocked on Phase A's LLM calls (1–3 min wall-clock after the GH-304 parallelization). Implementation tasks remain blocked on hard dependencies until the kanban DONE update inside the closure fires.

```
create_project_from_description():
  ├── parse_prd_to_tasks() [synchronous]
  ├── create_tasks_on_board() [synchronous]
  │     design tasks born with assigned_to="Marcus", status=TODO
  ├── asyncio.ensure_future(_run_design_phase(...))  [fire-and-forget]
  └── return result  [MCP tool responds immediately]

_run_design_phase() [background]:
  ├── Phase A: _generate_design_content()
  │     └── parallel LLM calls, write files to disk
  ├── Phase B: _register_design_via_mcp()         ← MUST be before kanban DONE
  │     └── log_artifact() populates state.task_artifacts[design_task_id]
  ├── Kanban DONE update                           ← unblocks impl tasks
  │     └── kanban_client.update_task(id, "done")
  └── _generate_project_scaffold()
        └── writes initial project scaffolding
```

## Phase A: Generate Content

For each design task, Marcus makes **separate LLM calls** for each artifact document:

1. Architecture document
2. API contracts
3. Data models
4. Interface contracts
5. One call for decisions

Each call writes its artifact file to disk at the standard `ARTIFACT_PATHS` location.

### Why separate LLM calls per artifact

A single LLM call producing all artifacts as one JSON response truncated at 7,714 characters. This caused JSON parse failures and triggered graceful degradation (the task stayed TODO and an agent grabbed it — which is exactly the context contamination problem).

Separate calls per document mirror how agents actually work. Each document is a focused, bounded response that fits comfortably within output limits.

### Parallelism (GH-304)

The five LLM calls per task run concurrently (Level 2), and all design tasks run concurrently with each other (Level 1). A per-invocation `asyncio.Semaphore(10)` caps total in-flight LLM calls to respect provider rate limits. Wall-clock: 25–33 min sequential → 1–3 min parallel on a typical 10-task enterprise project.

### Fail-fast semantics

Each LLM call is wrapped with `@with_retry(max_attempts=3, base_delay=2.0, jitter=True)`. If retries exhaust on any single call, the exception propagates through the inner `gather`, aborts the outer `gather`, and `_generate_design_content` raises. `_run_design_phase` catches this, logs it, and short-circuits: no Phase B, no kanban updates, no scaffold, no partial state. Fail-fast was chosen over warn-and-continue because partial design outputs silently corrupt downstream agent work.

## Phase B: Register Metadata

Phase B registers artifacts and decisions through MCP tools:

- `log_artifact()` for each file produced in Phase A — populates `state.task_artifacts[design_task_id]`
- `log_decision()` for each architectural decision — populates `state.context.decisions`

Phase B does **NOT** call `report_task_progress`. The task's kanban DONE update happens in the next step.

Workers discover design artifacts and decisions through `get_task_context` when they start dependent tasks. The retrieval path is `_collect_task_artifacts` (context.py) which walks `task.dependencies`, pulls `state.task_artifacts[dep_id]` for each, and returns the merged list to the agent.

## Ordering Invariant

**Phase B registration MUST run before the kanban DONE update.** This is a load-bearing ordering constraint pinned by `_run_design_phase` and tested by `TestRunDesignPhaseHandoff`.

The kanban DONE update is what unblocks implementation tasks from hard dependencies. If Phase B runs after, there is a window where:

1. Design task marked DONE on kanban
2. Implementation task unblocked
3. Agent requests implementation task
4. `_collect_task_artifacts` walks dependencies, finds empty `state.task_artifacts[design_task_id]`
5. Agent receives no contracts, proceeds without them

The window is sub-second but races don't care about narrow windows. Phase B before kanban update closes it entirely.

## Regression History

This section exists because the Phase A → Phase B handoff was broken for 5 days (2026-04-06 to 2026-04-11) and the regression hid behind stale documentation.

**2026-04-02 (GH-297, commit 4daccb7):** Two-phase design autocomplete landed. Phase A ran synchronously inside `create_project_from_description` and stored output in `result["design_content"]`. Phase B ran in `src/marcus_mcp/tools/nlp.py` after `state.refresh_project_state()`, reading the key from the result dict.

**2026-04-06 (GH-314, commit 1c5c7f7):** Phase A moved to a background closure via `asyncio.ensure_future` to prevent Claude Code from timing out on long LLM calls. The line `result["design_content"] = design_content` was deleted as part of the refactor. Phase B in nlp.py continued to read `result.get("design_content", {})` but the key was never populated again. Phase B became dead code. No test caught it — the `TestRegisterDesignViaMcp` unit tests mocked `design_content` directly, bypassing the handoff.

**2026-04-06 to 2026-04-11:** Marcus generated design artifacts to disk on every project creation but never registered them in `state.task_artifacts`. Agents calling `get_task_context` on implementation tasks walked the dependency graph and found empty artifact lists for every design task dependency. Contract-first decomposition was silently non-functional.

**2026-04-11 (GH-320):** Regression discovered while planning the contract-first decomposer. Phase A and Phase B consolidated into a single `_run_design_phase` function that cannot break again without touching both phases. The dead Phase B block in nlp.py was removed. The ordering invariant (Phase B before kanban DONE) was pinned by `TestRunDesignPhaseHandoff`. This document was rewritten to match current code.

**Lesson:** Cross-cutting handoffs between code owned by the same closure are fragile when the closure is refactored. If you ever split Phase A and Phase B again — or move Phase A to a different lifecycle hook — preserve the ordering invariant and add a chain-level test that exercises the full handoff with both phases mocked.

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

- `src/integrations/nlp_tools.py`
  - `_generate_design_content()` — Phase A: parallel LLM calls, writes files to disk
  - `_register_design_via_mcp()` — Phase B: calls `log_artifact` / `log_decision` to populate MCP state
  - `_run_design_phase()` — Background orchestrator: Phase A + Phase B + kanban DONE + scaffold, with load-bearing ordering
  - `_ARTIFACT_PROMPT`, `_DECISIONS_PROMPT`, `_INTERFACE_CONTRACTS_PROMPT` — LLM prompt templates
- `src/integrations/nlp_tools.py::NaturalLanguageProjectCreator.create_project_from_description()` — schedules `_run_design_phase` as a background task via `asyncio.ensure_future`
- `tests/unit/integrations/test_design_autocomplete.py::TestRunDesignPhaseHandoff` — regression guard for the Phase A → Phase B handoff and ordering invariant
- `cato_src/core/aggregator.py` — `_filter_tasks_by_view()` filters `auto_completed` label

## Pipeline Context

Design autocomplete runs as a single background task within the project creation pipeline:

```
create_project (MCP tool)
  ├── parse PRD synchronously
  ├── create tasks on kanban board (design tasks born with assigned_to="Marcus")
  ├── schedule _run_design_phase via ensure_future [fire-and-forget]
  └── return to caller immediately

_run_design_phase [background]:
  ├── Phase A: LLM artifact generation + disk writes
  ├── Phase B: log_artifact + log_decision via MCP tools
  ├── Kanban DONE update (unblocks implementation tasks)
  └── Phase A.5: Project scaffold generation
```

Phase A.5 (project scaffolding) reads the architecture document produced
by Phase A and generates the shared project infrastructure. This prevents
agents from duplicating scaffolding work in parallel worktrees.

## See Also

- [Project Scaffolding](../infrastructure/16-project-scaffolding.md) — Phase A.5, shared project infrastructure
- [Git Worktree Isolation](../infrastructure/15-git-worktree-isolation.md) — how agents are isolated during experiments
- GitHub Issues:
  - [#301](https://github.com/marcus/marcus/issues/301) — Four findings from dashboard-v16, including Finding 2 (context contamination)
  - [#297](https://github.com/marcus/marcus/issues/297) — Original design autocomplete implementation
  - [#300](https://github.com/marcus/marcus/issues/300) — Reverted attempt
  - [#267](https://github.com/marcus/marcus/issues/267) — Topology-aware decomposition
