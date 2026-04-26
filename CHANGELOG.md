# Changelog

All notable changes to Marcus will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-04-26

**Minor release — parallel experiment platform (Part 1), board integrity guards, agent auto-termination, and experiment reliability fixes.**

### Added
- **Parallel experiment isolation** — `run_comparison_experiment.py --parallel` now
  gives each Marcus instance its own SQLite kanban DB (`db_path`) and MCP URL baked
  into the spawned shell scripts at generation time. Previously all parallel runs
  shared one MCP endpoint and one board, contaminating each other's task assignments.
- **Agent auto-termination (GH-389)** — Marcus sends a termination signal when the
  experiment completes; agents that have been idle for the grace period exit cleanly
  instead of polling indefinitely across sequential runs.
- **`cpm_override` flag** — `config.yaml` now accepts `cpm_override: false` (default).
  When off, Marcus spawns exactly the configured agent count, preserving the
  experimental independent variable. Set `true` to restore CPM auto-sizing.
- **Stub debt scanner** — integration task acceptance criteria now reports unresolved
  stub debt (placeholder functions, hardcoded returns) as warnings in task completion.
- **`output_paths` on Task/Subtask** — integration-wiring tasks track which files
  each task is expected to produce; orphan scan traces reachability from the entry
  point against this manifest.
- **Platform architecture diagrams** — `docs/` now includes architecture and
  experiment flow diagrams.
- **Code of Conduct** — based on the scikit-learn contributor covenant.

### Fixed
- **`~/.claude.json` pretrust race** — parallel experiments calling `_pretrust_directory`
  simultaneously caused last-writer-wins overwrites; fixed with `fcntl.flock(LOCK_EX)`.
- **tmux env inheritance** — `tmux new-session` does not inherit subprocess env; the
  `${MARCUS_URL:-...}` fallback always fired. Fix: bake the concrete URL into scripts
  at `AgentSpawner` init time.
- **DONE-task reversion (stale agent blocker)** — `report_blocker` and
  `report_task_progress(status="blocked")` had no guard against reverting a DONE task.
  Stale agents (lease expired, task completed by new holder) could call `report_blocker`
  and corrupt the board. Both functions now reject calls on DONE tasks and from agents
  that no longer hold the active lease.
- **Validation worktree path on recovery** — `_validate_task_completion` was reading
  `task.assigned_to` (the recovering agent) to locate the worktree, finding the wrong
  directory. The caller `agent_id` is now threaded through explicitly.
- **Phase 4 lease timeout** — raised from 180 s to 360 s (450 s total with 90 s
  grace) based on empirical evidence that tail-phase activities (tests, build, commit,
  push, conflict resolution) routinely produce 161–215 s gaps between progress reports.
- **Validation gate lease expiry** — `touch_lease` is now called before each
  validation LLM attempt so the lease clock doesn't expire during silent 60–120 s
  validator runs.
- **JSON fence stripping** — `_call_claude()` in `ai_analysis_engine.py` now strips
  markdown fences and surrounding prose before returning, preventing `json.loads()`
  failures when the LLM wraps its response in a code block.
- **Spec-coverage ordering** — `check_spec_coverage` now runs before
  `enhance_project_with_integration`; gap tasks are in the integration task's
  dependency list instead of racing it.
- **Lease/assignment release decoupled from correctness** — `report_blocker` and
  task completion now release the agent's assignment slot and active lease
  independently of validation or merge-conflict outcomes.
- **Lease recreation on DONE tasks** — guard added to prevent re-opening a lease
  on a task that has already reached DONE state.
- **Recovery retry counter** — retry counter is now cleared on lease recovery so
  the new agent starts fresh without inheriting the previous agent's retry budget.
- **`board_id` KeyError in dry-run** — `run_all_projects()` was printing
  `inst['board_id']` unconditionally; fixed to fall back to `db_path`.
- **SQLite `db_path` anchored to repo root** — previously relative to the caller's
  cwd; now resolved via `Path(__file__)` so parallel DBs always land in `data/`.
- **`ANTHROPIC_API_KEY` → `CLAUDE_API_KEY`** — renamed to preserve Claude Code
  subscription credentials alongside API key usage.

## [0.3.5] - 2026-04-22

**Patch release — project-scoped registration, CPM-optimal agent count, integration orphan scan.**

### Added
- **CPM-optimal agent count** — Critical Path Method query is now authoritative
  for how many agents to spawn; config entries are templates (not a cap).
  `max_agents` config key (default 12) is the safety valve. Overflow agents get
  unique IDs (`agent_unicorn_{i+1}`) and `subagents=0`.
- **Integration orphan scan** — integration task acceptance criteria now requires
  tracing reachability from the entry point; every source file must be reachable
  or explicitly documented as intentionally standalone. Validated: v89 → v90
  reduced orphaned lines from 681 to 0.

### Fixed
- **Cross-experiment task theft (GH-388)** — `register_agent` now requires
  `project_id`; agents without one are rejected. `agent_project_map: Dict[str,
  str]` added to server state; `request_next_task` filters candidates to the
  agent's registered project. Legacy tasks with `project_id=None` pass through
  unchanged.
- **Atomic registration (GH-388 P2)** — `project_id` validation now runs before
  any state mutation; failed registrations leave no ghost `WorkerStatus` entries.
- **stdio handler wiring (GH-388 P1)** — `handlers.py` dispatch now extracts
  `project_id` from MCP tool arguments and declares it in the tool schema
  `required[]` list.
- **Overflow agent ID collision** — all overflow agents previously got the same
  ID (`agent_unicorn_1`); now uniquely numbered.
- **Overflow agents inheriting template subagents** — overflow agents now always
  set `subagents=0` regardless of the template they were copied from.
- **CPM failure log** — exception type and message now logged on CPM query failure
  before falling back to template count.

## [0.3.4.post3] - 2026-04-18

**Hotfix release — SQLite startup fix; PROTOCOL.md and README corrections.**

### Fixed
- **SQLite startup blocked by missing kanban-mcp (GH-386)** — `KanbanClient.__init__`
  eagerly called `_get_kanban_mcp_path()` which raised `FileNotFoundError` even for
  SQLite, GitHub, and Linear providers that never use kanban-mcp. Path detection is
  now deferred to first use via a lazy property — non-Planka providers construct
  cleanly; Planka users get the same descriptive error at call time.
- **`ProjectMonitor` instantiated for all providers** — `MarcusServer` now skips
  `ProjectMonitor()` for non-Planka providers since it unconditionally constructs a
  `KanbanClient`. Fixes the README claim "No Docker required" for SQLite.

### Docs
- **PROTOCOL.md** — added `create_project` to Required MCP Tools table; added Two
  Agent Roles section (creator vs worker); removed runner-specific exit logic
  (`get_experiment_status`, Experiment Completion section) from the agent protocol;
  added `log_decision` and `log_artifact` to work loop steps.
- **README.md** — named `config_marcus.json` in provider setup table; fixed agent
  directory guidance (agents run from the project directory, not the Marcus directory);
  clarified `CLAUDE.md` placement.

## [0.3.4.post2] - 2026-04-17

**Patch release — Codex P2 guardrail scope fixes.**

### Fixed
- **`log_artifact` guard too broad (P2-1)** — the git-tracked-file guard
  introduced in `0.3.4.post1` blocked *all* tracked files, including legitimate
  artifact outputs under `docs/` and `tmp/` that were committed in a previous
  run. Iterative artifact refreshes must be allowed. Guard is now scoped to
  paths whose first component is NOT in `{"docs", "tmp"}` — files under those
  artifact output roots skip the check entirely. Source roots (`src/`, `lib/`,
  etc.) are still protected.
- **Smoke gate fail-open on missing workspace state (P2-2)** — `_run_product_smoke_gate`
  previously returned `None` (the "verification passed" sentinel) in three
  infrastructure-failure paths: workspace state load error, `project_root` absent
  from state, and `project_root` not a directory on disk. Integration tasks could
  therefore slip through unverified on misconfigured environments. All three paths
  now return a `smoke_gate_unavailable` rejection dict so the gate is always a
  hard stop when it cannot initialise.

## [0.3.4.post1] - 2026-04-17

**Patch release — dashboard-v82 post-mortem fixes.**

### Fixed
- **`log_artifact` must not overwrite git-tracked source files** — the tool
  now calls `git ls-files --error-unmatch` before writing and rejects the write
  with a descriptive error if the target path is tracked. Fail-open: when git
  is unavailable the guard is skipped so non-git projects are unaffected.
  dashboard-v82 post-mortem: Agent 1 accidentally overwrote `theme.css` and
  `design-tokens.json` via `log_artifact` and had to restore from git
  (commit d44dd5a).
- **Documentation task instructions: read source before documenting** —
  `build_tiered_instructions` Layer 6 now injects a "read the actual source
  file" checklist for any task whose labels include `documentation`, `docs`,
  or `readme`, or whose name contains those keywords. Detection fires on label
  OR name so it works even when labels are absent. The AI prompt template
  (`task_instructions`) gains a matching DOCUMENTATION section so LLM-generated
  base instructions reinforce the same requirement. dashboard-v82 post-mortem:
  Agent 1 documented `WeatherWidget` props from the design spec
  (`location: {lat, lon, name}`) instead of the implementation
  (`defaultLocation: string`), causing silent README/code drift.
- **`build_tiered_instructions` Layer 6 defensive guards** — label list and
  task name now use `or []` / `or ""` fallbacks so the guidance block is safe
  when `task.labels` or `task.name` is `None`.

## [0.3.4] - 2026-04-17

**The Contract-First & Agent-Agnostic release.** Contract-first decomposition
graduates from opt-in flag to default. Pre-fork synthesis, planning observability,
and integration verification close the observability gap. PROTOCOL.md documents
Marcus as an agent-agnostic coordination layer. Lease race conditions patched.

### Added
- **Contract-first decomposition — full GH-320 series** — the decomposer now
  generates domain contracts synchronously inside `create_project`, fully
  populating the board before agents spawn. Eliminates the Phase A race where
  agents grabbed tasks before design artifacts were ready. One task per contract
  boundary; boundaries are determined by interface surface, not by agent count.
  Includes: domain-keyed contract generation, Phase A→B artifact registration,
  gate (Invariant 5 + verb-coverage), Cato synthetic design ghosts, scope clamp,
  upstream intent preservation, framing layer, acceptance criteria, and scope
  annotation (`in_scope` vs `reference_only` at retrieval time). (#320, #322,
  #326, #327, #329, #330, #331, #334, #335, #336, #339, #344, #381)
- **Pre-fork synthesis** (#355, #380) — Marcus generates shared foundation
  artifacts (architecture decisions, shared contracts) as a pre-fork task before
  agents spawn, preventing the most common class of cross-agent interface mismatch.
- **Planning observability** (#355, #380) — task graph, dependency DAG, and
  decomposition rationale logged as structured events for Cato and Simon.
- **Systemic integration verification** (#346) — three-layer verification:
  static boundary analysis, cross-agent contract tracing, and doc-code consistency
  check. Catches field-name mismatches, return-type disagreements, and config
  value divergence at agent boundaries.
- **`recommended_agents` in `create_project` JSON response** — CPM-based optimal
  agent count (from `calculate_optimal_agents`) surfaced in the API response after
  decomposition. API consumers get a data-driven recommendation; no change to the
  `/marcus` skill or human-driven workflows.
- **PROTOCOL.md** — developer-facing agent protocol spec. Documents the
  register → work-loop → exit lifecycle, required MCP tools, Marcus guarantees
  (task isolation, dependency ordering, lease recovery, artifact routing, scope
  annotation), and the Three Agent Invariants. Complements `Agent_prompt.md`
  (which is agent-facing). Marcus is agent-agnostic: any MCP-compatible agent
  (Codex, Gemini CLI, AutoGen, LangGraph…) can participate.
- **Merge-conflict-aware lease extension** (#350) — when an agent's lease is
  about to expire and its worktree has unresolved git merge conflicts, Marcus
  grants a one-shot 5-minute extension (max 2 grants = 10 min total). Truth is
  the worktree git state — agents cannot self-declare or lie about conflict status.

### Changed
- **`contract_first` is now the default decomposer** — previously `feature_based`.
  Set `MARCUS_DECOMPOSER=feature_based` or pass `{"decomposer": "feature_based"}`
  to opt out. The `/marcus` skill default updated to match.
- **`agent_count` removed from contract decomposition LLM prompt** — was being
  used to set `min_tasks`/`max_tasks` in the prompt, which is backwards. Task
  count should be determined by contract boundary count (one task per boundary),
  not by user-supplied agent count. Use `recommended_agents` in the response
  instead of driving decomposition with agent count.
- **README** — `<details>` summaries clarify agent-agnostic positioning; v0.3.4
  row added to News and Milestones tables; PROTOCOL.md linked from setup steps.

### Fixed
- **Lease extension race conditions** (Codex P1 + P2 review, PR #384):
  - **P1** — if `renew_lease` wins the race during the git probe, the lease is
    no longer expired but the merge-conflict extension still fired, burning an
    extension slot against the cap of 2. Fix: re-verify `is_expired` inside the
    Phase 3 lock before mutating; re-check in `check_expired_leases` so a
    concurrently-renewed lease is not added to the recovery list.
  - **P2** — `now` timestamp was captured once at scan start; later candidates
    in a batch received shorter-than-intended extensions. Fix: capture `grant_time`
    inside the lock at the moment of grant so each candidate gets the full 300s.
- **Decomposer contract bleed** (#353, #354) — contract-first framing leaked
  into feature-based artifact generation when both decomposers were active in
  the same process. Isolated artifact context per decomposer path.
- **Integration smoke — `start_command` required** (#351) — smoke test runner now
  requires agents to declare a `start_command`; vacuous passes where no build
  pipeline was exercised are rejected.
- **Product smoke — exec → shell runner** (#352) — killed the v73 vacuous-pass
  class where the smoke script exited 0 without actually running tests.
- **Agent completion signal** (#349) — agents now receive the real completion
  signal (`is_running=false`) rather than timing out on the work loop.
- **Task reviewer-selection deadlock** (#348) — Layer 3 reviewer selection
  removed after dashboard-v72 deadlock traced to it.

## [0.3.2] - 2026-04-10

**The Observability & Attribution release.** Substantive improvements to design
autocomplete speed, cross-agent contract verification, worktree agent resilience,
and the code cleanup that clears the path for contract-first decomposition in v0.3.3.

### Added
- **Cross-agent interface contracts for design and integration** (#313) — the
  integration verification agent now explicitly traces identifiers, data shapes,
  and configuration values across agent boundaries. Catches the class of bug
  where two agents' code works in isolation but collides at the boundary: field
  names that don't match, return types that disagree with caller expectations,
  config values that differ between producer and consumer. The verification step
  uses `git log --format="%an %s"` to find boundaries between agent-authored
  files, then traces data across each boundary with raw command output as
  evidence.
- **PyPI publishing workflow** — `publish.yml` triggers on GitHub release
  published, builds via `python -m build`, verifies `pyproject.toml` version
  matches the tag, and uploads to PyPI via trusted publishing. First release
  to exercise this workflow.

### Changed
- **Design autocomplete parallelized** (#304) — the sequential for-loops in
  `_generate_design_content()` are replaced with two levels of `asyncio.gather`:
  Level 1 across design tasks, Level 2 within each task (4 artifact calls + 1
  decisions call run concurrently). Concurrency cap via `asyncio.Semaphore(10)`,
  retries via `@with_retry(max_attempts=3, base_delay=2.0, jitter=True)` from
  `src/core/resilience.py`.

  **Wall-clock impact:** a 10-task enterprise project went from ~25-33 min
  sequential to ~145s parallel (10-14× speedup, 27% of the 10-min project
  creation budget). The smoke test run caught and transparently recovered from
  15 transient Anthropic API timeouts via the retry layer — all 50 LLM calls
  ultimately succeeded despite a ~30% transient failure rate.

  **Failure semantics change:** previously the design phase would warn-and-
  continue on per-task errors. Now any unrecoverable failure aborts the whole
  design phase (fail-fast). Partial design results are worse than no results
  because they silently corrupt downstream agent work.

### Fixed
- **Worktree agent resilience** (#317) — wired up the resilience system and
  fixed recovery for worktree-based agents. Before this, failed worktree agents
  could leave the recovery system in an inconsistent state.

### Removed
- **Dead `create_project_from_natural_language` function** (#303) — 180 lines
  of orphaned code removed from `src/integrations/nlp_tools.py`. The real MCP
  entry point was `src.marcus_mcp.tools.nlp.create_project`; the old function
  had no callers in `src/` and was only referenced by tests that exercised a
  dead code path. 13 files changed, +357 / −1,899. This cleanup unblocks the
  contract-first decomposition work planned for v0.3.3 (#320).

## [0.3.1] - 2026-04-07

### Fixed
- **Duplicate project creation** — Claude's `--print` mode retried `create_project` after timeout during design phase, creating duplicate projects. Fixed with dedup guard on the MCP tool and background design phase that returns immediately. (GH-314)
- **Missing git init in spawn_agents.py** — multi-agent experiment runner now initializes git repo in `implementation/` directory, preventing first-run failures that triggered Claude Code retries. (GH-314)
- **Design task agent assignment** — design tasks now assigned to Marcus before hitting the kanban board, preventing workers from grabbing them during the background design phase.

### Added
- **Background design phase** — `create_project` returns after tasks are on the board (seconds) instead of waiting for design artifact generation (3-5 min). Workers are blocked by hard dependencies until design tasks reach DONE status. Prevents Claude timeout retries.
- **Design task persistence** — design task outcomes persisted to marcus.db with `agent_id: "Marcus"`, enabling Cato to display them in the Swim Lane planning lane.
- **Epictetus Phase 8.5** — audit reports now persist to marcus.db `quality_assessments` collection for Cato Quality dashboard integration. Best-effort; skips silently if marcus.db not found.
- **`project_id` field** in Epictetus report schema for reliable project-to-report linking.
- **Caller stack logging** on `create_project` MCP tool for debugging duplicate invocations.

## [0.3.0] - 2026-04-03

**The Multi-Agency Foundation release.** First release where two independent agents
produce a working, multi-authored product and deliver it to main. Epictetus audit
of dashboard-v48: Multi-Agency Effective: Yes, Delivery: Delivered, Coordination: B.

### Multi-Agency Infrastructure (NEW)
- **Design autocomplete** — Marcus owns all design tasks. Generates architecture docs, API contracts, data models, and architectural decisions via LLM during `create_project`. Design tasks are born DONE — no agent ever carries design authorship context into implementation. Artifacts and decisions registered via MCP tools (`log_artifact`, `log_decision`) for full observability. (GH-297)
- **Git worktree isolation** — each worker agent gets an isolated git worktree on branch `marcus/{agent_id}`. Agents work in parallel without file conflicts. Merge-on-completion after validation passes. If merge conflicts, agent is sent back to resolve — code is never lost. (GH-250)
- **Project scaffolding** — Marcus generates shared project infrastructure (package manifest, build config, entry point, placeholder files) from the architecture document. Committed to main before worktrees branch. Prevents agents from duplicating scaffolding work. Post-processing filter rejects over-generated files. (GH-300)
- **Per-task visibility** — agents run `git merge main` before each task to see all previously completed work. DAG fan-in dependencies work correctly. (GH-302)
- **Commit attribution** — `GIT_AUTHOR_NAME` and `GIT_COMMITTER_NAME` env vars per agent tmux pane. Enables `git blame` attribution and Epictetus contribution analysis. (GH-308)
- **Design principle**: "No implementation agent should ever be able to reconstruct the full system from what Marcus gave it."
- **Five research findings** on why multi-agent parallelism fails documented in GH-301: decomposition mismatch, context contamination, knowledge leakage, precision-autonomy tradeoff, scaffolding duplication.

### Added
- **SQLite Kanban provider** — local-first, zero-config; no Docker needed for basic use (GH-258)
- **Epictetus evaluation skill** — standardized rubric grading for experiments (GH-258)
- **Coordination Effectiveness analysis** in Epictetus reports (GH-263)
- **Integration verification phase** — validates task outputs fit together (GH-271, GH-286)
- **Dr. Kaia Chen AI architect skill** for architectural advice via `/kaia` (GH-287)
- **`/marcus` Claude Code skill** — one-command experiment launcher (GH-227)
- Cadence-based agent recovery using median progress intervals (GH-247)
- Phase-level timing in `request_next_task` for scheduling insights (GH-248)
- Acceptance criteria stored in SQLite DB and wired through pipeline (GH-268, GH-269)
- Agent event logging on `get_task_context` calls (GH-285, GH-288)
- TERM normalization for tmux panes in non-interactive shells (GH-291)
- Pane readiness polling before injecting commands via `send-keys` (GH-291)
- Auto-confirm Claude trust/permission prompts in tmux panes (GH-218)
- AI model info displayed in `marcus status` output (GH-262)
- Project config snapshots saved at creation time (GH-260)
- Project status metrics sourced from kanban DB (GH-266)
- Brief task instruction generation to reduce context bloat (GH-259)
- PyPI publishing as `marcus-ai` (`pip install marcus-ai`)

### Changed
- **Default provider for experiments is now SQLite** — Planka remains fully supported for existing users
- Docker is now optional infrastructure (Planka + Postgres only)
- README redesigned with News, Architecture, and Comparison sections (GH-202, GH-216)

### Fixed
- **Dual project ID mismatch** — kanban and registry generated separate UUIDs, making decisions/artifacts invisible in Cato. Now uses kanban project ID as single source of truth. (GH-306)
- **Validator worktree awareness** — WorkAnalyzer now validates in the agent's worktree, not the main repo. Prevents false validation failures. (GH-305)
- **Phase B routing** — design artifact/decision registration moved to actual MCP tool entry point (`nlp.py`), not dead code path. (GH-303)
- **Stale .git cleanup** — `run_experiment.py` removes leftover `.git` at experiment root to prevent worktrees branching from wrong repo.
- **Agent prompt updates** — removed "push commits" (no remote), removed "NEVER merge" (agents need `git merge main`), added worktree workflow instructions.
- Display estimated time in minutes instead of hours on board
- Agent startup reliability in detached tmux sessions (GH-289)
- `experiment_complete.json` now written in `end_experiment` (GH-265)
- Task instruction generation constrained to be brief (GH-259)

### Documentation
- System docs: `15-git-worktree-isolation.md`, `16-project-scaffolding.md`, `52-design-autocomplete.md`
- Research findings: GH-301 — five empirical findings on multi-agent parallelism failure
- Vision document: `~/Desktop/new_vision_plan_design_implement_flow.md`

### Notes
- `/marcus`, `/kaia`, and `/epictetus` skills require Claude Code CLI — they are not part of the Python API
- Epictetus is the foundation for a larger backpropagation-style self-learning system (see GH-255, GH-257)
- **Known limitations**: lopsided contributions (73/27 split), scaffold may over-generate types/utils (filter mitigates), CSS conflicts between agents (no shared convention yet). See v0.3.1 milestone for planned fixes.

## [0.2.1] - 2026-03-21
### Added
- Progressive timeout system with lease recovery and handoff (GH-191)
- Structured RecoveryInfo field on Task model for agent handoffs (GH-190)
- Per-lease adaptive grace periods for progressive timeouts
- Recovery info preservation across project state refreshes
- Docker improvements: updated compose config, devcontainer (GH-182)
- LLM temperature now configurable via config
- Experiment infrastructure: reorganized folder structure, project_root handling
- False positive monitoring guide and scripts
- Local development documentation (LOCAL_DEVELOPMENT.md)
- Demo materials updated for April 15 conference talk

### Fixed
- Validation loop bug: LLM returning fail with zero issues now auto-passes
- AIAnalysisEngine UnboundLocalError when config validation fails
- get_task_by_id now searches all tasks, not just available/TODO tasks
- Design tasks exempt from deployment keyword filter
- Handle None completion_criteria in validation prompt builder
- docker-compose env vars preventing Marcus from starting
- .env file loading in marcus startup script
- WorkAnalyzer test failures and test suite updates (GH-187)
- All unit test fixtures updated to mock config/LLM dependencies

## [0.2.0] - 2026-03-16
### Added
- Feature completeness validation system with AI-powered analysis (GH-170)
- Centralized configuration system with validation and environment support (GH-162)
- Composition-aware task completeness validation (GH-160)
- Composition-aware PRD extraction with specificity detection (GH-159)
- AI-powered task completeness validation with automatic retry
- Project management utilities and telemetry planning tools (GH-167)
- Demo materials: presentation decks, scripts, and audio transcriptions
- Single-agent trial runner for controlled experiments
- Enhanced task classifier with weighted signal scoring and confidence levels
- Protection for integration requirements from complexity filtering (GH-163)
- WorkAnalyzer for source code validation
- Pre-completion validation checks to agent workflow
- Hybrid test discovery strategy for validation

### Changed
- Simplified validation to single-tier intent system (GH-166)
- Simplified MCP tool logger to activity tracker (GH-164)
- Task completeness validator is now AI provider-agnostic
- Agent retry wait times reduced for better parallelization (GH-177)
- Integrated Marcus error framework and resilience patterns into validation

### Removed
- Integration requirements extraction from PRD analysis (GH-165)
- Duplicate documentation enhancement call in NLP pipeline

### Fixed
- Task classifier misclassification causing phase enforcement failures (GH-180)
- Strong signals (task name + labels) now override weak signals (description keywords)
- Database connection tasks correctly classified as IMPLEMENTATION vs INFRASTRUCTURE
- Code comment tasks correctly classified as DOCUMENTATION vs IMPLEMENTATION
- Config loading and project-local database path with tilde expansion (GH-171)
- MCP tool logging and workflow enforcement (GH-172)
- Validation retry tracking order to prevent premature blocker creation
- Code review issues from validation refactoring
- Security and code quality issues across codebase

## [0.1.3.1] - 2026-03-09
### Fixed
- Validation retry tracking order to prevent premature blocker creation (GH-170)

## [0.1.3] - 2026-03-08
### Fixed
- Security and code quality issues
- Validation system final updates (GH-170)
- Task label fetching from Kanban to use filtered labels

### Added
- Comprehensive resolution summary for Issue #170
- Pre-completion validation checks to agent workflow
- Runtime test execution to catch configuration issues
- Detailed logging to validation gate

## [0.1.2] - 2026-03-07
### Added
- Hybrid test discovery strategy for validation
- WorkAnalyzer for source code validation (GH-170)
- Phase 2 validation gate integration (GH-170)
- Retry tracking with comprehensive tests

### Changed
- Integrated Marcus error framework and resilience patterns into validation

## [0.1.1] - 2026-03-06
### Added
- Initial validation system framework
- Basic task completion verification

### Fixed
- Various bug fixes in agent coordination

## [0.1.0] - 2026-03-01
### Added
- Initial beta release
- Multi-agent coordination platform
- MCP protocol support
- GitHub and Planka Kanban integrations
- Agent registration and task assignment
- Context sharing through artifacts
- Progress reporting system
- Blocker handling workflow

[0.3.0]: https://github.com/lwgray/marcus/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/lwgray/marcus/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/lwgray/marcus/compare/v0.1.3.1...v0.2.0
[0.1.3.1]: https://github.com/lwgray/marcus/compare/v0.1.3...v0.1.3.1
[0.1.3]: https://github.com/lwgray/marcus/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/lwgray/marcus/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/lwgray/marcus/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/lwgray/marcus/releases/tag/v0.1.0
