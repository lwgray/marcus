# PyCon 2026 Sprint Menu — Marcus

**Sprint date:** May 2026 · Long Beach, CA
**Repo:** https://github.com/lwgray/marcus
**Maintainer:** @lwgray

Marcus is a board-mediated multi-agent coordination system. Agents self-select tasks from a shared kanban board. This sprint gives contributors a real production MAS to dig into — across docs, performance, testing, and integrations.

---

## How to pick your dish

1. Fork the repo, create a branch off `develop`.
2. Find your issue below, read the context block and acceptance criteria.
3. Comment on the issue to claim it.
4. Open a PR against `develop` when ready.

All issues are tagged `pycon_2026` on GitHub.

---

## 🥗 Appetizers — 15–45 min

*Docs, type hints, small bug fixes, logging cleanup. Good for first-time contributors.*

---

### #26 · Document MCP Integration for Various Platforms

**Context.** New users frequently ask how to connect Marcus to their AI tool of choice. There are no platform-specific setup guides. Claude Desktop and VS Code + Continue are the two most common entry points — each needs a short, copy-paste-ready configuration snippet.

**Acceptance criteria**
- [ ] `docs/source/guides/mcp_integrations.rst` created with Claude Desktop config block
- [ ] VS Code + Continue setup section with JSON snippet
- [ ] Correct MCP server ports listed (4298 human endpoint, 4299 agent endpoint)
- [ ] Entry wired into Sphinx toctree — page is reachable, not orphaned

**Estimate:** 20–40 min

---

### #66 · Remove hard-coded MCP client paths

**Context.** Three source files hard-code `~/dev/kanban-mcp/dist/index.js` as the kanban MCP client path. This path exists only on the maintainer's machine and silently breaks CI and any contributor who clones the repo.

**Acceptance criteria**
- [ ] `src/marcus_mcp/coordinator/subtask_assignment.py:531` uses env var or config
- [ ] All other hard-coded path sites replaced
- [ ] Unit test: raises `MissingCredentialsError` (or clear `ValueError`) when path not set
- [ ] No regression in existing tests

**Estimate:** 30–45 min

---

### #108 · fix(monitoring): get_project_status reports incorrect task counts

**Context.** `get_project_status` calls `get_available_tasks()` which filters to only TODO/unassigned tasks. IN_PROGRESS, DONE, and BLOCKED tasks are excluded from the count, so monitoring shows misleadingly small numbers and wrong progress percentages.

**Acceptance criteria**
- [ ] `get_project_status` counts tasks across all statuses
- [ ] Progress percentage derived from DONE / total, not available / total
- [ ] Unit test: mock board with mixed statuses → verify correct counts
- [ ] No change to API response shape (additive fix only)

**Estimate:** 30–45 min

---

### #221 · Perf: Remove debug logging on every task in request_next_task hot path

**Context.** `task.py` lines 1903–1938 contain `logger.info()` for every TODO task in the filtering loop, plus a `logger.critical()` block with an expensive list comprehension hard-coded to look for a task named "Display Game Board". This is leftover debug code from a specific experiment running on every single task assignment.

**Acceptance criteria**
- [ ] `logger.info()` per-task loop removed or moved to `logger.debug()`
- [ ] `logger.critical()` block with "Display Game Board" string removed
- [ ] No regressions in `request_next_task` behavior
- [ ] Unit test confirms hot path no longer emits INFO-level logs per task

**Estimate:** 20–30 min

---

### #228 · Bug: Audit log missing duration_ms for request_next_task

**Context.** Every `request_next_task` call in recent audit logs shows `dur=N/A`. `log_access_denied()` in `audit.py` has no `duration_ms` field. This is the most-called tool in Marcus and we have zero performance baseline — no way to detect if it's slowing down over time.

**Acceptance criteria**
- [ ] `log_access_denied()` accepts and records `duration_ms`
- [ ] Call site passes elapsed time
- [ ] Unit test: audit log entry contains numeric `duration_ms` field
- [ ] Existing audit log tests still pass

**Estimate:** 20–35 min

---

### #245 · chore: Add 'Foundation Quality' section to ROADMAP.md *(replaces #198)*

**Context.** ROADMAP.md has detailed version milestones for features (v0.1.x–v0.3.x) but 33 of 35 sprint-ready issues are bug fixes, test coverage, refactoring, and documentation improvements that don't map to any roadmap item. Contributors see stability work as invisible. A "Foundation Quality" section aligns these issues with the roadmap so contributors understand the work is planned and valued. *(Issue #198 — empty Planka response bug — was claimed before the sprint; this is its replacement.)*

**Acceptance criteria**
- [ ] `ROADMAP.md` gains a `## Foundation Quality (v0.2.x)` section
- [ ] Section lists the 33 affected issue types with brief descriptions
- [ ] Prose explains why stability work precedes v0.3.x features
- [ ] No other roadmap sections modified

**Estimate:** 20–30 min

---

### #261 · feat: add AI model info to ping MCP tool response

**Context.** The `ping` MCP tool is the first call any agent or user makes to verify Marcus is running. It returns the kanban `provider` but nothing about the AI model configuration. When debugging model deprecation errors (404s) or verifying which model loaded after an env var override, there's no fast way to check.

**Acceptance criteria**
- [ ] `ping` response includes `ai_model`, `ai_provider` fields
- [ ] Fields populated from loaded config (not re-read from file at call time)
- [ ] Unit test: mock config → verify fields in ping response
- [ ] No breaking change to existing ping response keys

**Estimate:** 25–40 min

---

### #274 · docs: Fix broken Sphinx index files and wire 64 orphaned pages

**Context.** Five Sphinx index files in `docs/source/systems/` reference wrong filenames due to a numbering mismatch. 64+ documentation pages build successfully as HTML but have no navigation path — they exist but are unreachable from the docs site.

**Acceptance criteria**
- [ ] All five broken index files corrected
- [ ] `sphinx-build -b linkcheck` reports no orphan warnings for `systems/`
- [ ] No pages listed in toctrees that don't exist
- [ ] Existing navigation structure preserved

**Estimate:** 30–45 min

---

### #278 · docs: Write documentation for /marcus Claude Code skill

**Context.** The `/marcus` Claude Code skill is the recommended entry point for running multi-agent experiments but has no documentation in `docs/source/`. The README mentions it buried in "Step 7" alongside the harder MCP-direct path. Sprint contributors need this on day one.

**Acceptance criteria**
- [ ] `docs/source/guides/marcus_skill.rst` created
- [ ] Covers: prerequisites, install, basic usage, agent count selection, dry-run
- [ ] Code blocks copy-paste correct
- [ ] Wired into Sphinx toctree

**Estimate:** 30–45 min

---

### #282 · docs: Update CHANGELOG.md — missing v0.2.1 entries and unreleased features

**Context.** CHANGELOG.md is missing entries for three major features that shipped in v0.2.1, and the `[Unreleased]` section is empty despite 65+ commits since that release. New contributors rely on the changelog to understand project velocity and history.

**Acceptance criteria**
- [ ] v0.2.1 section complete (identify entries from `git log`)
- [ ] `[Unreleased]` section populated with changes since v0.2.1
- [ ] Keep-a-Changelog format maintained
- [ ] No invented entries — every item traceable to a commit or PR

**Estimate:** 25–40 min

---

### #283 · docs: Fix docstring style violations and remove -FUTURE suffix files

**Context.** `CLAUDE.md` mandates numpy-style docstrings throughout Marcus. Several files still use Google-style (`Args:` / `Returns:` inline). Two files violate the no-version-suffix rule with `-FUTURE` in their names. Both problems are mechanical — AI-assisted batch conversion is fast here.

**Acceptance criteria**
- [ ] All Google-style docstrings in scope converted to numpy-style
- [ ] `-FUTURE` suffix files renamed or removed per maintainer guidance
- [ ] `mypy` passes after changes
- [ ] Existing tests still pass

**Estimate:** 30–45 min

---

## 🍝 Main Courses — 1–3 hours

*Bug fixes, new flags, small features, CI improvements. Requires reading 1–2 source files.*

---

### #219 · Perf: O(N·M·P) nested loop in phase filtering

**Context.** Phase dependency enforcement in `task.py:2074–2160` has a triple nested loop: for each available task, it linearly searches all in-progress tasks AND all project tasks, calling `classifier.classify()` (expensive regex scoring) on each. On a 50-task project with 5 agents, this is ~12,500 classifications per `request_next_task` call.

**Acceptance criteria**
- [ ] Phase filtering rewritten to O(N+M) using set-based lookups
- [ ] `classifier.classify()` not called inside the inner loop
- [ ] Benchmark: `request_next_task` on 50-task project ≥ 2× faster
- [ ] All existing phase enforcement tests pass

**Estimate:** 1.5–2.5 hr

---

### #229 · Skill: add robust error handling for Marcus repo path discovery

**Context.** The `/marcus` skill discovers the repo root via `python3 -c "from pathlib import Path; import marcus_mcp; ..."`. If `marcus_mcp` isn't installed (wrong conda env, fresh clone without `pip install -e .`), this silently fails or produces an obscure import error with no actionable guidance.

**Acceptance criteria**
- [ ] Skill detects import failure and prints a clear diagnostic with fix command
- [ ] Fallback path resolution tried (e.g., walk up from `$PWD`)
- [ ] Test: simulated missing package → correct error message shown
- [ ] Works in both editable install and non-install scenarios

**Estimate:** 1–2 hr

---

### #231 · Skill: add --dry-run mode to preview experiment setup

**Context.** The `/marcus` skill generates config files and immediately launches `run_experiment.py`, spawning agents in tmux. There's no way to preview what will be created before committing. A typo in the project name means: wait for agents to spawn → kill tmux → re-run. Dry-run shows the config diff without executing.

**Acceptance criteria**
- [ ] `--dry-run` flag supported in skill invocation
- [ ] Dry-run prints: generated config, agent count, tmux pane layout — then exits
- [ ] No files written, no tmux sessions created in dry-run
- [ ] Test: dry-run with sample params produces expected preview output

**Estimate:** 1.5–2.5 hr

---

### #236 · test: OpenAI provider end-to-end smoke test

**Context.** Marcus supports OpenAI as an LLM provider but has no smoke test verifying the full pipeline: project creation → task decomposition → task assignment. OpenAI-specific bugs (prompt format differences, token limit behaviors, response parsing) could ship undetected.

**Acceptance criteria**
- [ ] Smoke test in `tests/integration/external/test_openai_smoke.py`
- [ ] Covers: project creation, decomposition call, first task assignment
- [ ] Test skips gracefully if `OPENAI_API_KEY` not set
- [ ] Marked `@pytest.mark.integration` and `@pytest.mark.slow`

**Estimate:** 1.5–2.5 hr

---

### #241 · feat: Scaffold Jira kanban provider with KanbanInterface stub

**Context.** Marcus supports Planka, Linear, and GitHub as kanban backends. The v0.3.x roadmap adds Jira. This issue creates the scaffold — a properly stubbed class implementing `KanbanInterface` with one working method (e.g., `get_projects`) as proof of concept. Everyone at PyCon uses Jira; this is high-excitement.

**Acceptance criteria**
- [ ] `src/integrations/jira_kanban.py` created, implements `KanbanInterface`
- [ ] All interface methods present (may raise `NotImplementedError`)
- [ ] At least `get_projects()` makes a real Jira REST API call (mocked in tests)
- [ ] Unit tests cover the implemented method
- [ ] `mypy` passes

**Estimate:** 2–3 hr

---

### #264 · feat: persist AI config at startup for accurate status reporting

**Context.** `./marcus status` reads AI config from the current `config_marcus.json` — not from what the running server actually loaded at startup. If you start Marcus with `MARCUS_AI_MODEL=claude-haiku-4-5-20251001` and then clear the env var, `status` reports the wrong model. There's a runtime truth / file truth mismatch.

**Acceptance criteria**
- [ ] Effective AI config written to a runtime state file at server startup
- [ ] `./marcus status` reads runtime state file, not raw config
- [ ] Test: env-var override at startup → status shows overridden model
- [ ] Runtime state file cleaned up on server stop

**Estimate:** 1.5–2.5 hr

---

### #284 · fix: Cato board view doesn't match Marcus kanban board

**Context.** The board view in Cato doesn't visually match the Marcus kanban board. Column names, task card fields, or status labels differ between the two views. When switching between Cato and Marcus during a demo, users see inconsistent representations of the same project — damaging trust in the tool.

**Acceptance criteria**
- [ ] Column names identical between Cato and Marcus board views
- [ ] Task card status labels match
- [ ] Visual regression test or screenshot comparison added
- [ ] Demo walkthrough confirmed: no visible inconsistency across views

**Estimate:** 1.5–2.5 hr

---

### #324 · urgent: gate full-test-suite CI job on push to main + nightly

**Context.** The `full-test-suite` CI job is the only job running `pytest tests/unit` without a marker filter. Every other job uses `pytest -m unit` which covers only 391 of 2562 unit tests (15%). The full-suite job is gated on `if: github.event_name == 'schedule'` — it never runs on PRs or pushes to main.

**Acceptance criteria**
- [ ] `full-test-suite` job triggers on `push: branches: [main]` in addition to nightly
- [ ] PR check suite references the job (required status check)
- [ ] CI run confirmed passing with updated trigger
- [ ] No other CI workflow logic changed

**Estimate:** 1–1.5 hr

---

### #382 · feat: auto-select decomposer strategy

**Context.** `MARCUS_DECOMPOSER` is a user-set env var choosing between `contract_first` and `feature_based` task decomposition strategies. Users have no meaningful basis for this choice — it's an implementation detail leaking into the user interface. The system has enough information to choose automatically based on project structure.

**Acceptance criteria**
- [ ] Auto-selection logic implemented (e.g., coupling analysis, task count heuristic)
- [ ] `MARCUS_DECOMPOSER` still accepted as override for power users
- [ ] Default behavior: env var absent → auto-select
- [ ] Unit tests cover both auto-select paths
- [ ] Decision logged to audit trail

**Estimate:** 2–3 hr

---

### #383 · feat: synthetic agent for CI and runner validation

**Context.** There's no way to run a full end-to-end Marcus experiment in CI without real LLM agents (cost, latency, non-determinism). A synthetic agent that speaks the Marcus MCP protocol without making LLM calls makes the full coordination loop testable in seconds at zero API cost — it requests tasks, reports progress, and completes them on a deterministic schedule.

**Acceptance criteria**
- [ ] `src/agents/synthetic_agent.py` implements full Marcus MCP protocol
- [ ] No LLM calls — behavior driven by deterministic config
- [ ] Can run a 3-agent × 5-task experiment end-to-end in < 10 seconds
- [ ] Integrated into at least one CI smoke test
- [ ] `mypy` passes

**Estimate:** 2.5–3 hr

---

## 🍮 Desserts — 3+ hours

*New integrations, architectural refactors, experimental features. For experienced contributors.*

---

### #72 · Create task graph algorithms module

**Context.** Cycle detection is duplicated across 9 separate locations in the codebase. `get_critical_path()` has two separate implementations. No unified `TaskGraph` data structure exists. Every graph bug requires fixes in multiple places; advanced features (parallel scheduling, bottleneck detection) can't be built cleanly without a shared foundation.

**Acceptance criteria**
- [ ] `src/core/task_graph.py` with `TaskGraph` dataclass
- [ ] `detect_cycles()`, `get_critical_path()`, `get_topological_order()` implemented once
- [ ] All 9 duplicated call sites migrated to use new module
- [ ] Test coverage ≥ 90% for new module
- [ ] `mypy` strict passes

**Estimate:** 3–5 hr

---

### #120 · Benchmark: 1 Agent vs 3 Agents Speedup Measurement

**Context.** Marcus claims "2-3× faster with multiple agents." There is no empirical measurement backing this claim. `benchmark_scaling.py` in `tests/performance/` tests connection throughput — not task completion speedup, which is the actual claim. This issue produces the real data.

**Acceptance criteria**
- [ ] Benchmark script runs 1-agent and 3-agent experiments on identical task sets
- [ ] Measures wall-clock task completion time (not throughput)
- [ ] Results saved as structured data (JSON/CSV) for reproducibility
- [ ] README updated with actual measured speedup (whatever it is)
- [ ] Script parameterized for different task counts

**Estimate:** 3–5 hr

---

### #255 · feat: Backpropagation-style blame attribution for post-experiment audits

**Context.** After a Marcus experiment, Epictetus audits identify *what* went wrong but not *who is responsible* — Marcus (bad decomposition or instructions), the agent (bad execution), or `CLAUDE.md` (conflicting directives). Without this distinction, we tune the wrong knob. The fix is structured attribution propagating backward through the task graph from failure points.

**Acceptance criteria**
- [ ] Blame attribution implemented as post-experiment analysis pass
- [ ] Attribution assigns probability mass to: task spec, agent execution, system config
- [ ] Output integrated into Epictetus audit report
- [ ] Test: synthetic failure scenario → correct blame distribution
- [ ] Paper-compatible output format (structured JSON)

**Estimate:** 4–6 hr

---

### #312 · feat: make pip install marcus-ai a complete install path

**Context.** `pip install marcus-ai` gives users an MCP server and CLI entry point, but cannot run projects. The `/marcus` skill, experiment runner, and templates all assume a git clone. Users who install via pip get a broken `marcus` command with no useful error.

**Acceptance criteria**
- [ ] `marcus start` works after pip install (no git clone required)
- [ ] Required templates bundled as package data
- [ ] `marcus run-experiment` works or produces a clear "requires git clone" message
- [ ] Integration test: fresh venv + pip install → `marcus start` succeeds
- [ ] PyPI metadata accurate

**Estimate:** 4–6 hr

---

### #338 · Generative validator: LLM produces verification code instead of reviewing it

**Context.** The current `WorkAnalyzer` asks an LLM "does this code satisfy the criterion?" — speculative static review that regularly hallucinates correctness. The alternative: ask the LLM to *write* a verification script, execute it, and use the exit code as ground truth. Generative verification > speculative review.

**Acceptance criteria**
- [ ] `WorkAnalyzer` mode flag: `generative` vs `review`
- [ ] Generative mode: LLM outputs runnable Python, sandboxed execution, exit code captured
- [ ] Sandboxing: no network, no filesystem writes outside temp dir
- [ ] Benchmark on 20 prior tasks: compare hallucination rate between modes
- [ ] `mypy` passes; no `subprocess` without timeout

**Estimate:** 5–8 hr

---

### #378 · feat(cato): Living Architecture Diagram — real-time IDEA flow with GIF export

**Context.** Add an "Architecture" view to Cato showing Marcus as a living 8-layer system diagram with animated particles flowing between layers as real MCP events fire. Not a static poster — the data is live. GIF export captures a real working session as shareable social proof.

**Acceptance criteria**
- [ ] Architecture view added to Cato navigation
- [ ] 8-layer diagram rendered with layer labels matching Marcus docs
- [ ] Particles animate on live MCP event stream (SSE or WebSocket)
- [ ] GIF export: captures 10-second session clip
- [ ] Works without active experiment (static fallback)

**Estimate:** 5–8 hr

---

## 🌙 Night Cap — Late-night bonus issues

*Ambitious explorations. Bring coffee. No pressure to finish at the sprint.*

| # | Title | Vibe |
|---|-------|------|
| [#403](https://github.com/lwgray/marcus/issues/403) | CLI Agent Runners for all major harness vehicles | Build |
| [#404](https://github.com/lwgray/marcus/issues/404) | Harness engineering with Ollama — local model vehicles | Docs + Prototype |
| [#405](https://github.com/lwgray/marcus/issues/405) | Frontend harness — giving agents visual/design skills | Design + Build |
| [#406](https://github.com/lwgray/marcus/issues/406) | How Marcus selects agents by skill — audit and improve | Investigation |
| [#407](https://github.com/lwgray/marcus/issues/407) | How Marcus learns patterns over time — memory audit | Investigation |
| [#408](https://github.com/lwgray/marcus/issues/408) | How Marcus estimates task duration — time model audit | Investigation |
| [#409](https://github.com/lwgray/marcus/issues/409) | Full-page token usage and cost dashboard | Build |

---

## Quick reference

| Tier | Count | Time | Good for |
|------|-------|------|----------|
| 🥗 Appetizer | 10 | 15–45 min | First-time contributors, docs writers |
| 🍝 Main Course | 10 | 1–3 hr | Developers comfortable reading Python |
| 🍮 Dessert | 6 | 3+ hr | Experienced contributors |
| 🌙 Night Cap | 7 | Open-ended | "I want to go deep" |

All issues: [`pycon_2026` label](https://github.com/lwgray/marcus/issues?q=is%3Aopen+label%3Apycon_2026)
Sprint menu: [`sprint-menu` label](https://github.com/lwgray/marcus/issues?q=is%3Aopen+label%3Asprint-menu)

---

*Note: Issue #198 (handle empty Planka response) was claimed before the sprint — a contribution is in review at PR #402. Issue #245 (Foundation Quality section in ROADMAP.md) is its appetizer replacement.*
