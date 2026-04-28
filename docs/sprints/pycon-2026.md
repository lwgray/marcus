# PyCon 2026 Sprint Menu — Marcus

**Sprint date:** May 2026 · Long Beach, CA
**Repo:** https://github.com/lwgray/marcus
**Maintainer:** @lwgray

Marcus is a board-mediated multi-agent coordination system. Agents self-select tasks from a shared kanban board. This sprint gives contributors a real production MAS to dig into — across docs, performance, testing, and integrations.

---

## How to pick your dish

1. Browse the **Tier Browser** below to find an issue that fits your time and skill level.
2. Read the issue's context block and acceptance criteria further down the page.
3. Comment on the issue to claim it.
4. Fork the repo, branch off `develop`, open a PR back to `develop` when ready.

All issues are tagged `pycon_2026` on GitHub.
Sprint menu issues also carry the `sprint-menu` label and one of `appetizer` / `main-course` / `dessert` / `nightcap`.

---

## 🍽️ Tier Browser

A single-glance map of every dish on the menu. Click an issue number to jump to its detail block.

### 🥗 Appetizers — 15–45 min · *first-time-friendly*

| # | Title | Est. | Flavor |
|---|---|---|---|
| [#26](#26--document-mcp-integration-for-various-platforms) | Document MCP integration for various platforms | 20–40 min | 📘 docs |
| [#66](#66--remove-hard-coded-mcp-client-paths) | Remove hard-coded MCP client paths | 30–45 min | 🔥 critical bug |
| [#115](#115--fix-plankakanban-usage-in-get_all_board_tasks) | Fix `PlankaKanban` usage in `get_all_board_tasks()` | 15–25 min | 🧹 refactor |
| [#198](#198--handle-empty-planka-response-during-project-discovery) | Handle empty Planka response during project discovery | 15–25 min | 🐛 bug |
| [#221](#221--remove-debug-logging-on-every-task-in-request_next_task-hot-path) | Remove debug logging in `request_next_task` hot path | 20–30 min | ⚡ perf |
| [#228](#228--audit-log-missing-duration_ms-for-request_next_task) | Audit log missing `duration_ms` for `request_next_task` | 20–35 min | 🐛 bug |
| [#274](#274--fix-broken-sphinx-index-files-and-wire-64-orphaned-pages) | Fix broken Sphinx index files (64 orphaned pages) | 30–45 min | 📘 docs |
| [#278](#278--write-documentation-for-marcus-claude-code-skill) | Write documentation for `/marcus` Claude Code skill | 30–45 min | 📘 docs |
| [#283](#283--fix-docstring-style-violations-and-remove--future-suffix-files) | Fix docstring style violations + remove `-FUTURE` files | 30–45 min | 🧹 cleanup |

### 🍝 Main Courses — 1–2.5 hr · *comfortable reading Python*

| # | Title | Est. | Flavor |
|---|---|---|---|
| [#219](#219--perf-onmp-nested-loop-in-phase-filtering) | Perf: O(N·M·P) nested loop in phase filtering | 1.5–2.5 hr | ⚡ perf |
| [#229](#229--skill-add-robust-error-handling-for-marcus-repo-path-discovery) | Skill: robust error handling for repo path discovery | 1–2 hr | 🐛 bug |
| [#231](#231--skill-add---dry-run-mode-to-preview-experiment-setup) | Skill: add `--dry-run` mode | 1.5–2.5 hr | ✨ feature |
| [#236](#236--openai-provider-end-to-end-smoke-test) | OpenAI provider end-to-end smoke test | 1.5–2.5 hr | 🧪 test |
| [#237](#237--add-undocumented-mcp-tool-groups-to-api-reference) | Add 5 undocumented MCP tool groups to API reference | 45–75 min | 📘 docs |
| [#240](#240--write-how-to-add-a-new-kanban-provider-developer-guide) | Write "How to add a new kanban provider" guide | 90–120 min | 📘 docs |
| [#241](#241--scaffold-jira-kanban-provider-with-kanbaninterface-stub) | Scaffold Jira kanban provider stub | 2–3 hr | ✨ integration |
| [#244](#244--write-how-to-add-a-new-mcp-tool-developer-guide) | Write "How to add a new MCP tool" guide | 60–90 min | 📘 docs |
| [#264](#264--persist-ai-config-at-startup-for-accurate-status-reporting) | Persist AI config at startup for `marcus status` | 1.5–2.5 hr | 🐛 bug |
| [#284](#284--fix-cato-board-view-doesnt-match-marcus-kanban-board) | Fix Cato board view doesn't match Marcus | 1.5–2.5 hr | 🐛 bug |
| [#324](#324--gate-full-test-suite-ci-job-on-push-to-main--nightly) | Gate `full-test-suite` CI on push to main + nightly | 1–1.5 hr | 🚦 CI |
| [#382](#382--auto-select-decomposer-strategy) | Auto-select decomposer strategy | 2–3 hr | ✨ feature |
| [#383](#383--synthetic-agent-for-ci-and-runner-validation) | Synthetic agent for CI and runner validation | 2.5–3 hr | 🧪 test |

### 🍮 Desserts — 3+ hr · *experienced contributors*

| # | Title | Est. | Flavor |
|---|---|---|---|
| [#72](#72--create-task-graph-algorithms-module) | Create task graph algorithms module | 3–5 hr | 🏗️ refactor |
| [#120](#120--benchmark-1-agent-vs-3-agents-speedup-measurement) | Benchmark: 1 agent vs 3 agents speedup | 3–5 hr | 📊 research |
| [#255](#255--backpropagation-style-blame-attribution) | Backpropagation-style blame attribution | 4–6 hr | 🧠 research |
| [#312](#312--make-pip-install-marcus-ai-a-complete-install-path) | Make `pip install marcus-ai` a complete install path | 4–6 hr | 📦 packaging |
| [#338](#338--generative-validator-llm-produces-verification-code) | Generative validator (LLM writes verification code) | 5–8 hr | 🧠 research |
| [#378](#378--catos-living-architecture-diagram-with-gif-export) | Cato Living Architecture Diagram with GIF export | 5–8 hr | 🎨 build |

### 🌙 Night Cap — open-ended bonus issues

| # | Title | Vibe |
|---|---|---|
| [#403](https://github.com/lwgray/marcus/issues/403) | CLI Agent Runners for all major harness vehicles | 🛠️ Build |
| [#404](https://github.com/lwgray/marcus/issues/404) | Harness engineering with Ollama — local model vehicles | 📘 Docs + Prototype |
| [#405](https://github.com/lwgray/marcus/issues/405) | Frontend harness — visual/design skills for agents | 🎨 Design + Build |
| [#406](https://github.com/lwgray/marcus/issues/406) | How Marcus selects agents by skill — audit + improve | 🔍 Investigation |
| [#407](https://github.com/lwgray/marcus/issues/407) | How Marcus learns patterns over time — memory audit | 🔍 Investigation |
| [#408](https://github.com/lwgray/marcus/issues/408) | How Marcus estimates task duration — time model audit | 🔍 Investigation |
| [#409](https://github.com/lwgray/marcus/issues/409) | Full-page token usage and cost dashboard | 🛠️ Build |

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

**Context.** Four source files hard-code `~/dev/kanban-mcp/dist/index.js` as the kanban MCP client path. This path exists only on the maintainer's machine and silently breaks any contributor who clones the repo. `kanban_client.py` already has a correct `_get_kanban_mcp_path()` resolver — the fix is to make the other sites use it (or extract it to a shared utility).

**Where to look**
- `src/marcus_mcp/coordinator/subtask_assignment.py:531` — hardcoded path
- `src/integrations/nlp_base.py:728` — hardcoded path
- `src/integrations/providers/planka_kanban.py:67` — hardcoded path
- `src/config/marcus_config.py:42` — hardcoded default
- `src/integrations/kanban_client.py:227–293` — **the correct resolver to reuse**

**Acceptance criteria**
- [ ] No `~/dev/kanban-mcp` literal in `src/` (`grep -rn "~/dev/kanban-mcp" src/` returns zero)
- [ ] Path can be configured via env var or config file
- [ ] Unit test: env var override is respected
- [ ] Unit test: clear error raised when path can't be resolved
- [ ] No regression in existing tests

**Estimate:** 30–45 min

---

### #115 · Fix `PlankaKanban` usage in `get_all_board_tasks()`

**Context.** `get_all_board_tasks()` in `src/marcus_mcp/tools/task.py:3819–3821` instantiates a fresh `PlankaKanban(config={})` instead of using the kanban client already on `state`. Every other tool in the file goes through `state.kanban_client`, which is configured by the factory and respects the active provider. This one tool bypasses that and hard-codes Planka — meaning it silently breaks for SQLite, GitHub, and Linear users.

**Where to look**
- `src/marcus_mcp/tools/task.py:3792–3830` — `get_all_board_tasks()` function
- `src/marcus_mcp/state.py` — `state.kanban_client` is already populated at startup

**Fix pattern**
```python
# Replace:
from src.integrations.providers.planka_kanban import PlankaKanban
provider = PlankaKanban(config={})
await provider.connect()
tasks = await provider.get_all_tasks()

# With:
tasks = await state.kanban_client.get_all_tasks()
```

**Acceptance criteria**
- [ ] No `PlankaKanban(config={})` literal remains in `task.py`
- [ ] `get_all_board_tasks()` uses `state.kanban_client`
- [ ] Unit test mocks `state.kanban_client.get_all_tasks` and verifies it's called
- [ ] Function returns the same shape as before for a populated board

**Estimate:** 15–25 min

---

### #198 · Handle empty Planka response during project discovery

**Context.** `discover_planka_projects` in `kanban_client.py:1375` calls `json.loads(first_content.text)` on the kanban-mcp response. When Planka has no projects yet (fresh install), the response body is empty and parsing crashes with `JSONDecodeError: Expecting value: line 1 column 1`. The fix is a two-line guard before the parse.

**Where to look**
- `src/integrations/kanban_client.py:1373–1383` — the unguarded `json.loads`

**Fix pattern**
```python
if result and hasattr(result, "content"):
    first_content = cast(TextContent, result.content[0])
    if not first_content.text or not first_content.text.strip():
        return []  # No projects found — empty board
    projects_data = json.loads(first_content.text)
    ...
```

**Acceptance criteria**
- [ ] `discover_planka_projects` returns `[]` when response body is empty
- [ ] No `JSONDecodeError` raised for an empty Planka instance
- [ ] Unit test: empty string → returns `[]`
- [ ] Unit test: valid JSON → returns project list

**Estimate:** 15–25 min

---

### #221 · Perf: Remove debug logging on every task in `request_next_task` hot path

**Context.** `task.py:3390–3407` contains a `logger.critical()` block that fires for every task with `"Display Game Board"` in its name — leftover debug code from a one-off experiment. The block runs inside the per-task filtering loop in the most-called tool in Marcus.

**Where to look**
- `src/marcus_mcp/tools/task.py:3390–3407` — the `"Display Game Board"` block
- `src/marcus_mcp/tools/task.py:1903–1938` — additional `logger.info()` per-task spam

**Acceptance criteria**
- [ ] `grep -n "Display Game Board" src/marcus_mcp/tools/task.py` returns zero results
- [ ] Per-task `logger.info()` removed or downgraded to `logger.debug()`
- [ ] No regression in `request_next_task` behavior
- [ ] Unit test confirms the hot path no longer emits INFO-level logs per task

**Estimate:** 20–30 min

---

### #228 · Audit log missing `duration_ms` for `request_next_task`

**Context.** Every recent `request_next_task` audit entry shows `dur=N/A`. `log_access_denied()` in `audit.py` has no `duration_ms` field, and the call sites in `task.py` aren't capturing start time. The most-called tool in Marcus has zero performance baseline — there's no way to detect if it's getting slower as projects grow.

**Where to look**
- `src/core/audit.py` — `log_access_denied()` signature missing `duration_ms`
- `src/marcus_mcp/tools/task.py` — `request_next_task` call sites

**Acceptance criteria**
- [ ] `log_access_denied()` accepts and records `duration_ms`
- [ ] Both success and denied paths capture and pass elapsed time
- [ ] Audit entries also include task count at time of call
- [ ] Unit test: audit entry contains numeric `duration_ms` field
- [ ] Existing audit tests still pass

**Estimate:** 20–35 min

---

### #274 · Fix broken Sphinx index files and wire 64 orphaned pages

**Context.** 64+ documentation pages exist on disk but are unreachable — Sphinx prints a "document isn't included in any toctree" warning for each. The root cause is a filename numbering mismatch: index files reference old prefixes (e.g. `37-optimal-agent-scheduling`) but the actual files have different numbers (e.g. `45-optimal-agent-scheduling`).

**Where to look**
- `docs/source/systems/coordination/index.rst`
- `docs/source/systems/project-management/index.rst`
- `docs/source/systems/intelligence/index.rst`
- `docs/source/systems/` — actual `.md` files

**Acceptance criteria**
- [ ] `cd docs && make html` produces zero "document isn't included in any toctree" warnings
- [ ] No documentation pages deleted — only index references corrected
- [ ] No new pages listed in toctrees that don't exist on disk
- [ ] Existing navigation structure preserved

**Estimate:** 30–45 min

---

### #278 · Write documentation for `/marcus` Claude Code skill

**Context.** The `/marcus` Claude Code skill is the recommended entry point for running multi-agent experiments but has no standalone documentation. The README mentions it briefly alongside the harder MCP-direct path. Sprint contributors need this on day one.

**Where to look**
- `~/.claude/skills/marcus/SKILL.md` — the skill source contributors should read
- `docs/source/guides/` — where the new guide should live
- `README.md` — where the skill is currently buried in "Step 7"

**Acceptance criteria**
- [ ] `docs/source/guides/marcus_skill.rst` (or `.md`) created
- [ ] Covers: prerequisites, install, basic usage, agent count selection, common failure modes
- [ ] Code blocks copy-paste correct
- [ ] Wired into Sphinx toctree

**Estimate:** 30–45 min

---

### #283 · Fix docstring style violations and remove `-FUTURE` suffix files

**Context.** `CLAUDE.md` mandates numpy-style docstrings throughout Marcus. Several known files still use Google-style (`Args:` / `Returns:` inline). Two documentation files violate the no-version-suffix rule by carrying `-FUTURE` in their names. Both problems are mechanical — AI-assisted batch conversion is fast here.

**Where to look**
- `src/marcus_mcp/handlers.py` — Google-style docstrings
- `src/integrations/enhanced_task_classifier.py` — Google-style docstrings
- `src/orchestration/mode_registry.py` — Google-style docstrings
- `docs/source/systems/intelligence/07-ai-intelligence-engine-FUTURE.md` — delete
- `docs/source/systems/intelligence/44-enhanced-task-classifier-FUTURE.md` — delete

**Acceptance criteria**
- [ ] Both `-FUTURE` files deleted; index references updated/removed
- [ ] All Google-style docstrings in the three known files converted to numpy-style
- [ ] `mypy` passes on changed files
- [ ] Existing tests still pass

**Estimate:** 30–45 min

---

## 🍝 Main Courses — 1–2.5 hours

*Bug fixes, new flags, small features, CI improvements. Requires reading 1–2 source files.*

---

### #219 · Perf: O(N·M·P) nested loop in phase filtering

**Context.** Phase dependency enforcement in `task.py:3540–3640` has nested loops: for each available task, it scans every in-progress task AND every project task, calling `classifier.classify()` (an expensive regex-scoring operation) on each. On a 50-task project with 5 agents, that's thousands of classifications per `request_next_task` call.

**Where to look**
- `src/marcus_mcp/tools/task.py:3540–3640` — the nested loop
- `src/integrations/enhanced_task_classifier.py` — `classifier.classify()` cost
- `src/core/phase_dependency_enforcer.py` — phase order rules

**Acceptance criteria**
- [ ] Phase filtering rewritten to O(N+M) using set-based lookups + memoized classification
- [ ] `classifier.classify()` not called inside the inner loop
- [ ] Benchmark: `request_next_task` on 50-task project ≥ 2× faster
- [ ] All existing phase enforcement tests pass

**Estimate:** 1.5–2.5 hr

---

### #229 · Skill: add robust error handling for Marcus repo path discovery

**Context.** The `/marcus` skill discovers the repo root via `python3 -c "from pathlib import Path; import marcus_mcp; ..."`. If `marcus_mcp` isn't installed (wrong conda env, fresh clone without `pip install -e .`), this silently fails or produces an obscure import error with no actionable guidance — the most common day-one setup failure at sprints.

**Where to look**
- `~/.claude/skills/marcus/SKILL.md:35` — the brittle import discovery line
- `~/.claude/skills/marcus/SKILL.md:154` — same pattern in a second location

**Acceptance criteria**
- [ ] Skill detects import failure and prints a clear diagnostic with the fix command
- [ ] Fallback path resolution tried (e.g., walk up from `$PWD` looking for `pyproject.toml`)
- [ ] Test: simulated missing package → correct error message
- [ ] Works in both editable install and non-install scenarios

**Estimate:** 1–2 hr

---

### #231 · Skill: add `--dry-run` mode to preview experiment setup

**Context.** The `/marcus` skill generates config files and immediately launches `run_experiment.py`, spawning agents in tmux. There's no way to preview what will be created before committing. A typo in the project name means: wait for agents to spawn → kill tmux → re-run. Dry-run shows the config diff without executing.

**Where to look**
- `~/.claude/skills/marcus/SKILL.md` — skill bash blocks
- `dev-tools/experiments/runners/run_experiment.py` — what gets launched today

**Acceptance criteria**
- [ ] `--dry-run` flag supported in skill invocation
- [ ] Dry-run prints: generated config, agent count, tmux pane layout — then exits
- [ ] No files written, no tmux sessions created in dry-run
- [ ] Test: dry-run with sample params produces expected preview output

**Estimate:** 1.5–2.5 hr

---

### #236 · OpenAI provider end-to-end smoke test

**Context.** Marcus supports OpenAI as an LLM provider but has no smoke test verifying the full pipeline. OpenAI and Anthropic differ on prompt formats, token limits, and response parsing. OpenAI-specific bugs can ship undetected. `tests/integration/external/` is empty today.

**Where to look**
- `tests/integration/external/` — currently empty (`__init__.py` only)
- `src/ai/providers/openai_provider.py` — provider under test
- `config_marcus.example.json` — OpenAI config example

**Acceptance criteria**
- [ ] Smoke test in `tests/integration/external/test_openai_smoke.py`
- [ ] Covers: project creation → decomposition call → first task assignment
- [ ] Test skips gracefully if `OPENAI_API_KEY` not set
- [ ] Marked `@pytest.mark.integration` and `@pytest.mark.slow`

**Estimate:** 1.5–2.5 hr

---

### #237 · Add undocumented MCP tool groups to API reference

**Context.** The curated API reference at `docs/source/api/mcp_tools.rst` (196 lines) documents 9 tool groups. Five additional groups exist in the codebase with auto-generated stubs in `docs/source/api/auto/` but are NOT in the curated reference: **attachment, audit_tools, auth, board_health, code_metrics**. Contributors don't know these tools exist unless they dig through auto-generated docs.

**Where to look**
- `docs/source/api/mcp_tools.rst` — file to edit
- `docs/source/api/auto/src.marcus_mcp.tools.{attachment,audit_tools,auth,board_health,code_metrics}.rst` — auto-stubs to reference
- `src/marcus_mcp/tools/` — actual code with signatures and docstrings
- `src/marcus_mcp/tool_groups.py` — group registration

**Acceptance criteria**
- [ ] All 5 tool groups added to `mcp_tools.rst` following the existing format
- [ ] Each tool documented with: name, description, parameters, return value
- [ ] `make html -C docs` builds without errors and without new warnings
- [ ] Section headings consistent with the existing 9 groups

**Estimate:** 45–75 min

---

### #240 · Write "How to add a new kanban provider" developer guide

**Context.** The roadmap lists Jira, Linear, and Trello as v0.3.x kanban providers. There's no developer guide explaining how to implement one — a contributor would have to reverse-engineer the Planka implementation. This guide unblocks #241 (Jira scaffold) and any future provider work.

**Where to look**
- `src/integrations/kanban_interface.py` (479 lines) — the contract to document
- `src/integrations/providers/planka_kanban.py` (995 lines) — reference implementation
- `src/integrations/kanban_factory.py` — registration
- `docs/source/developer/` — existing developer guides for style reference

**Acceptance criteria**
- [ ] `docs/source/developer/adding-kanban-provider.md` (or `.rst`) created
- [ ] Walks through full lifecycle: implement interface → register in factory → add config → write tests
- [ ] Method-by-method reference for each `KanbanInterface` method
- [ ] Includes a config example snippet
- [ ] Wired into Sphinx toctree

**Estimate:** 90–120 min

---

### #241 · Scaffold Jira kanban provider with `KanbanInterface` stub

**Context.** Marcus supports Planka, Linear, and GitHub kanban backends. The v0.3.x roadmap adds Jira — the most-requested enterprise integration. This issue creates the stub: a class implementing `KanbanInterface` with `connect()` / `disconnect()` working and the rest raising `NotImplementedError` so individual methods can be filled in incrementally.

**Where to look**
- `src/integrations/kanban_interface.py` — interface to implement
- `src/integrations/providers/github_kanban.py` — best non-Planka reference
- `src/integrations/kanban_factory.py:20–126` — add `"jira"` case
- `src/integrations/providers/jira_kanban.py` — **new file**

**Acceptance criteria**
- [ ] `src/integrations/providers/jira_kanban.py` exists, implements `KanbanInterface`
- [ ] All interface methods present (most may raise `NotImplementedError` with helpful message)
- [ ] `connect()` / `disconnect()` use a real `httpx` session against Jira REST v3
- [ ] Factory wires `"jira"` → `JiraKanban`
- [ ] `config_marcus.example.json` gains a `jira` section
- [ ] Unit tests cover the implemented methods; `mypy` passes

**Estimate:** 2–3 hr

---

### #244 · Write "How to add a new MCP tool" developer guide

**Context.** Marcus's MCP tools are the primary interface between AI agents and the coordination engine. Adding a new tool requires touching specific files in a specific order, but there's no guide explaining the process. Contributors have to reverse-engineer existing tools.

**Where to look**
- `src/marcus_mcp/tool_groups.py` (181 lines) — tool registration
- `src/marcus_mcp/handlers.py` — handler dispatch
- `docs/source/api/mcp_tools.rst` — where new tools are documented
- `tests/unit/mcp/` — existing tool tests for the test pattern

**Acceptance criteria**
- [ ] `docs/source/developer/adding-mcp-tool.md` (or `.rst`) created
- [ ] Covers: define → register in `tool_groups.py` → implement handler → add docs → write test
- [ ] Includes an annotated walkthrough of an existing simple tool
- [ ] Includes a copy-paste PR checklist
- [ ] Wired into Sphinx toctree

**Estimate:** 60–90 min

---

### #264 · Persist AI config at startup for accurate `marcus status` reporting

**Context.** `./marcus status` reads AI config from `config_marcus.json` on disk via `get_config()` — not from what the running server actually loaded. If you started Marcus with `MARCUS_AI_MODEL=...` and then cleared the env var, `status` reports the wrong model. Runtime truth ≠ file truth.

**Where to look**
- `marcus:380–420` (the CLI script) — `status()` function
- `src/marcus_mcp/server.py` — server startup; needs to write a runtime state file
- `~/.marcus/` — natural home for the runtime state file

**Acceptance criteria**
- [ ] Effective AI config written to a runtime state file at server startup
- [ ] `./marcus status` reads from the runtime state file, not raw config
- [ ] Test: env-var override at startup → status shows overridden model
- [ ] Runtime state file cleaned up on server stop

**Estimate:** 1.5–2.5 hr

---

### #284 · Fix Cato board view doesn't match Marcus kanban board

**Context.** The board view in Cato (the Marcus dashboard) doesn't visually match the Marcus kanban board: column names, task card fields, and status labels differ between the two views. During demos, audiences see two different representations of the same project — damaging trust.

Marcus's canonical column names and order: `TODO → IN_PROGRESS → DONE` (plus `BLOCKED`).

**Where to look**
- `~/dev/cato/` — Cato dashboard repo
- `src/core/models.py` — canonical `TaskStatus` enum

**Acceptance criteria**
- [ ] Cato board columns use the same names + order as Marcus
- [ ] Task card fields match (title, assignee, status, labels)
- [ ] A status change in Marcus appears correctly in Cato on next refresh
- [ ] No browser console errors when the board view loads

**Estimate:** 1.5–2.5 hr

---

### #324 · Gate `full-test-suite` CI job on push to main + nightly

**Context.** The `full-test-suite` job in `.github/workflows/tests.yml:211–217` only triggers on `schedule` (nightly) or `workflow_dispatch`. Every other CI job uses `pytest -m unit` which runs only marker-tagged tests; unmarked tests in `tests/unit/` slip through silently. PRs can merge with a green check while the full suite is red — and historically have, for 100+ consecutive days.

**Where to look**
- `.github/workflows/tests.yml:211–217` — the `if:` condition

**Acceptance criteria**
- [ ] `full-test-suite` triggers on `push: branches: [main]` in addition to nightly
- [ ] Nightly schedule preserved — both paths active
- [ ] Existing PR fast-check (`pytest -m unit`) unchanged
- [ ] Workflow YAML valid; CI run confirmed passing with new trigger

**Estimate:** 1–1.5 hr

---

### #382 · Auto-select decomposer strategy

**Context.** `MARCUS_DECOMPOSER` is a user-set env var choosing between `contract_first` and `feature_based` task decomposition strategies. Most users have no basis for this choice — it's an implementation detail leaking into the user interface. v0.3.4 made `contract_first` the default but didn't add auto-selection. The system has enough information (project description, coupling indicators) to choose automatically.

**Where to look**
- `src/integrations/nlp_tools.py` — decomposer dispatch
- `src/config/settings.py` — current env var read
- `src/intelligence/prd_parser.py` — signals for coupling analysis

**Acceptance criteria**
- [ ] Auto-selection logic implemented (e.g., coupling analysis or task-count heuristic)
- [ ] `MARCUS_DECOMPOSER` still accepted as override for power users
- [ ] Default behavior: env var absent → auto-select
- [ ] Decision logged to audit trail
- [ ] Unit tests cover both auto-select paths

**Estimate:** 2–3 hr

---

### #383 · Synthetic agent for CI and runner validation

**Context.** Running a full end-to-end Marcus experiment in CI today requires real LLM agents — costs API money, takes minutes, and produces non-deterministic results. A synthetic agent that speaks the Marcus MCP protocol without making LLM calls makes the full coordination loop testable in seconds at zero cost. It registers, requests tasks, simulates work, reports completion, and loops.

**Where to look**
- `src/worker/client.py` — existing agent client to model from
- `src/marcus_mcp/tools/agent.py` — registration & request_next_task entry points
- `src/agents/synthetic_agent.py` — **new file**

**Acceptance criteria**
- [ ] `src/agents/synthetic_agent.py` implements full Marcus MCP protocol
- [ ] No LLM calls — behavior driven by deterministic config + seed
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

### #255 · Backpropagation-style blame attribution

**Context.** After a Marcus experiment, Epictetus audits identify *what* went wrong but not *who is responsible* — Marcus (bad decomposition or instructions), the agent (bad execution), or `CLAUDE.md` (conflicting directives). Without this distinction, we tune the wrong knob. The fix is structured attribution propagating backward through the task graph from failure points.

**Acceptance criteria**
- [ ] Blame attribution implemented as post-experiment analysis pass
- [ ] Attribution assigns probability mass to: task spec, agent execution, system config
- [ ] Output integrated into Epictetus audit report
- [ ] Test: synthetic failure scenario → correct blame distribution
- [ ] Paper-compatible output format (structured JSON)

**Estimate:** 4–6 hr

---

### #312 · Make `pip install marcus-ai` a complete install path

**Context.** `pip install marcus-ai` gives users an MCP server and CLI entry point, but cannot run projects. The `/marcus` skill, experiment runner, and templates all assume a git clone. Users who install via pip get a broken `marcus` command with no useful error.

**Acceptance criteria**
- [ ] `marcus start` works after pip install (no git clone required)
- [ ] Required templates bundled as package data
- [ ] `marcus run-experiment` works or produces a clear "requires git clone" message
- [ ] Integration test: fresh venv + pip install → `marcus start` succeeds
- [ ] PyPI metadata accurate

**Estimate:** 4–6 hr

---

### #338 · Generative validator: LLM produces verification code

**Context.** The current `WorkAnalyzer` asks an LLM "does this code satisfy the criterion?" — speculative static review that regularly hallucinates correctness. The alternative: ask the LLM to *write* a verification script, execute it, and use the exit code as ground truth. Generative verification > speculative review.

**Acceptance criteria**
- [ ] `WorkAnalyzer` mode flag: `generative` vs `review`
- [ ] Generative mode: LLM outputs runnable Python, sandboxed execution, exit code captured
- [ ] Sandboxing: no network, no filesystem writes outside temp dir
- [ ] Benchmark on 20 prior tasks: compare hallucination rate between modes
- [ ] `mypy` passes; no `subprocess` without timeout

**Estimate:** 5–8 hr

---

### #378 · Cato's Living Architecture Diagram with GIF export

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
|---|---|---|
| [#403](https://github.com/lwgray/marcus/issues/403) | CLI Agent Runners for all major harness vehicles | 🛠️ Build |
| [#404](https://github.com/lwgray/marcus/issues/404) | Harness engineering with Ollama — local model vehicles | 📘 Docs + Prototype |
| [#405](https://github.com/lwgray/marcus/issues/405) | Frontend harness — visual/design skills for agents | 🎨 Design + Build |
| [#406](https://github.com/lwgray/marcus/issues/406) | How Marcus selects agents by skill — audit + improve | 🔍 Investigation |
| [#407](https://github.com/lwgray/marcus/issues/407) | How Marcus learns patterns over time — memory audit | 🔍 Investigation |
| [#408](https://github.com/lwgray/marcus/issues/408) | How Marcus estimates task duration — time model audit | 🔍 Investigation |
| [#409](https://github.com/lwgray/marcus/issues/409) | Full-page token usage and cost dashboard | 🛠️ Build |

---

## Quick reference

| Tier | Count | Time | Good for |
|---|---|---|---|
| 🥗 Appetizer | 9 | 15–45 min | First-time contributors, docs writers |
| 🍝 Main Course | 13 | 1–2.5 hr | Developers comfortable reading Python |
| 🍮 Dessert | 6 | 3+ hr | Experienced contributors |
| 🌙 Night Cap | 7 | Open-ended | "I want to go deep" |

**All sprint issues:** [`pycon_2026` label](https://github.com/lwgray/marcus/issues?q=is%3Aopen+label%3Apycon_2026)
**Curated menu:** [`sprint-menu` label](https://github.com/lwgray/marcus/issues?q=is%3Aopen+label%3Asprint-menu)
**Browse by tier:**
[appetizer](https://github.com/lwgray/marcus/issues?q=is%3Aopen+label%3Aappetizer) ·
[main-course](https://github.com/lwgray/marcus/issues?q=is%3Aopen+label%3Amain-course) ·
[dessert](https://github.com/lwgray/marcus/issues?q=is%3Aopen+label%3Adessert)

---

## Changelog

- **2026-04-27** — Removed obsolete/solved appetizers: #108 (effectively fixed by kanban metrics path), #261 (closed/shipped), #282 (CHANGELOG caught up through 0.3.6), #245 (poor first-contributor fit — assumes ROADMAP knowledge). Added new appetizers #115 and #198. Added new main-courses #237, #240, #244. Added the Tier Browser table.
