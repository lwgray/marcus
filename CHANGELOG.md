# Changelog

All notable changes to Marcus will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
