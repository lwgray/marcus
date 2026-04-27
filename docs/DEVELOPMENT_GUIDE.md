# Marcus Development Guide

**Last Updated:** 2026-04-27
**Audience:** New contributors who want to start hacking on Marcus
**Current shipped release:** v0.3.6 (v0.4.0 work in progress on `develop`)

> This is a fresh, intentionally short developer-onboarding guide. The
> previous 8-week curriculum-style plan was archived during the 2026-04
> documentation triage and is preserved at
> `docs/archive/DEVELOPMENT_GUIDE_2025_12_8wk_plan.md`. Most of its
> milestones either shipped, were dropped, or were punted to the proposed
> Marcus Studio desktop app (issue #443). See `ROADMAP.md` for the
> current shipped state and `docs/Playbook.md` for the long-term vision.

---

## What Marcus is in one paragraph

Marcus is a multi-agent orchestration server built around the Model
Context Protocol (MCP). It exposes a kanban board as the shared
environment, lets AI coding agents (Claude, Cursor, Codex, etc.) pull
tasks via MCP, and coordinates dependencies, parallel work, and recovery.
Greenfield (new project from scratch) is the supported mode today;
brownfield (existing repos) is on the post-v0.5 roadmap. Marcus is one
piece of a small platform that also includes Cato (visualization) and
Posidonius (experiment runner) as sibling repositories.

---

## Run Marcus locally

```bash
# 1. Clone and install
git clone https://github.com/lwgray/marcus.git
cd marcus
pip install -e .

# 2. (Optional) Make the `marcus` command available globally
./install.sh      # symlinks ./marcus into ~/.local/bin

# 3. Start the MCP server
./marcus start

# 4. View the board
./marcus board

# 5. Stop
./marcus stop
```

For the visual dashboard, install Cato as a sibling repo:

```bash
cd ~/dev
git clone https://github.com/lwgray/cato.git
cd cato && pip install -e . && ./cato start
```

For experiment runs with multiple agents in tmux:

```bash
cd ~/dev
git clone https://github.com/lwgray/posidonius.git
cd posidonius && pip install -e .
```

The `/marcus` skill (Claude Code) drives Posidonius for full
multi-agent experiments. See `README.md` Attach mode for details.

---

## The development loop

Per `CLAUDE.local.md`:

```bash
# After any code change, run all four:
black src/ tests/
isort src/ tests/
mypy src/<module-you-touched>/
pytest -m unit                      # baseline — never run by file path
```

Test marker rules (from project memory):
- **Baseline test run:** `pytest -m unit` (not by file path).
- Unit tests live in `tests/unit/`; integration tests in `tests/integration/`.
- Unmarked tests in `tests/unit/` won't run in CI — every test needs a
  `@pytest.mark.unit` (or `integration`, `asyncio`, `slow`, `kanban`) marker.

For full guidance on test placement, error framework, and TDD workflow,
see `CLAUDE.md` (project root).

---

## What's actively being built

### Sprint in flight: Parallel Experiment Platform (`feat/parallel-experiment-platform`)

All five tracks shipped; tail work being closed out:

- **Track 1 — `asyncio.Lock` in `create_project`** (`src/marcus_mcp/tools/nlp.py`)
  serializes concurrent calls. Code in, tests cover lock + serialization,
  end-to-end validation under real concurrent load still pending.
- **Epictetus reliability** — timeout raised 30 min → 2 hr, and Phase 8.5
  in the `/epictetus` skill now checks `MARCUS_DB` before importing
  `marcus_mcp`. Previously, Posidonius-spawned audits silently skipped
  writing to `marcus.db`.
- **Batch pipeline tests** — 6 new tests in Posidonius covering Epictetus
  fire-after-every-run, `COMPLETED` state, and teardown ordering across
  3-run batches.
- **Rufus** — standalone Telegram bot at `~/dev/rufus/`. Read-only access
  to `marcus.db` + Posidonius REST API. Commands: `/status`, `/projects`,
  `/epictetus`, `/quality`, `/start`, `/pause`, `/resume`, `/events`,
  `/ping`. Fourth sibling repo on the platform.
- **Posidonius Epictetus UI** — phase indicators in experiment cards;
  `/api/experiments/{name}/events` endpoint added.

### Next queue — post-v0.4.0

In order:

1. **#414 — SQLite migration for all data streams** — unifies seven
   file-based JSONL/JSON streams under one queryable store. Unblocks
   Cato multi-path work.
2. **#416 — PostHog telemetry (PyCon 2026 sprint)** — opt-in
   anonymized usage analytics. **Sprinters get first pick** — flag the
   issue before working it solo.
3. **#363 — God-files refactor** — 20 modules over 1000 lines
   (`advanced_parser.py` at 4505); each has a subissue with a split plan.
4. **#442 — Track 2: per-session project isolation** — the real fix
   for parallel experiments. Single Marcus on `:4298` handles N
   experiments via MCP session ID. **Deferred post-PyCon** because
   blast radius is 80+ locations / 15+ files.

### Open architectural debt — high urgency, no milestone

Surfaced from post-mortems and Kaia architectural reviews:

- **Feature-based contract bleed** — `get_task_context` doesn't label
  artifacts `in_scope` vs `reference_only`; two open options (B:
  mode-aware framing, C: explicit `artifact_role` field).
- **Foundation task descriptions missing consumption contracts** —
  design-phase artifacts ship but task descriptions don't tell
  downstream agents *how* to consume them (dashboard-v80 post-mortem).
- **Decomposer removed integration-wiring tasks** —
  `_create_integration_subtask` removal causes hollow products
  (dashboard-v99 audit). Each component passes unit tests; the composed
  result is broken.

### Smaller surviving items from the 2026-04 doc triage

| # | Item | Status | Pointer |
|---|---|---|---|
| 1 | Configuration polish (last 20%) | In progress | `src/config/marcus_config.py`, `src/config/settings.py` |
| 2 | `UserJourneyTracker` — log user-journey milestones | Not started | Will live under `src/telemetry/` |
| 3 | Global tab cross-project metrics endpoint | Not started | Lives in Cato; Marcus may need a small helper |

### Background research workstream

- **Coordination tax experiments** (NeurIPS 2026) — 24-PRD test suite
  infrastructure (commit 2801ea6d).
- **Epictetus coordination-effectiveness audit** (#263) — automated
  grading of agent performance, surfaced in Cato's Quality dashboard.
- **Validation hardening** (#421, #337) — citation-backed validation,
  hallucination elimination, retry ceilings.

For longer-term plans (Build Kits, Brownfield, Marketplace, Federation),
see `docs/Playbook.md`.

---

## Where to find things

| Need | Look at |
|---|---|
| What's shipped + what's planned | `ROADMAP.md` |
| 12-month vision (Build Kits / Marketplace / Federation) | `docs/Playbook.md` |
| Active research / experiment work | Issues with the `experiment` or `research` label |
| The architectural rules every change must follow | `CLAUDE.md` (project root) |
| Personal style + mypy strict mode rules | `CLAUDE.local.md` |
| Error framework + retry/circuit-breaker patterns | `CLAUDE.md` → ERROR_HANDLING_FRAMEWORK |
| Test placement decision tree | `CLAUDE.md` → TEST_WRITING_INSTRUCTIONS |
| Public docs + getting started | https://marcus-ai.dev and `README.md` |
| Architecture deep dive | `docs/CATO/` (some are stale — sanity-check against code) |
| The proposed unified desktop app | Issue [#443](https://github.com/lwgray/marcus/issues/443) and Discussion [#444](https://github.com/lwgray/marcus/discussions/444) |
| The previous 8-week curriculum plan | `docs/archive/DEVELOPMENT_GUIDE_2025_12_8wk_plan.md` |

---

## Companion repos and tools

| Repo | Path | Role | Transport |
|---|---|---|---|
| **Marcus** | `~/dev/marcus` | MCP orchestration server | MCP — stdio + HTTP `:4298` |
| **Cato** | `~/dev/cato` | Real-time visualization dashboard | FastAPI + React `:4301` |
| **Posidonius** | `~/dev/posidonius` | Multi-agent experiment runner with MLflow tracking | FastAPI + xterm.js `:8420` |
| **Rufus** | `~/dev/rufus` | Telegram bot for remote monitoring of long-running batches | Reads `marcus.db` directly + Posidonius REST API |
| `/marcus` skill | `~/.claude/skills/marcus` | Spawns Marcus experiments from Claude Code | n/a |
| `/epictetus` skill | `~/.claude/skills/epictetus` | Audits / grades a finished project | n/a |

A future unified desktop app ("Marcus Studio") that wraps all of these
into a single installable application is proposed in issue
[#443](https://github.com/lwgray/marcus/issues/443).

---

## When you're stuck

1. Search the [issue tracker](https://github.com/lwgray/marcus/issues) — there's a strong chance you're not the first to hit it.
2. Check the [Discussions](https://github.com/lwgray/marcus/discussions) board — strategic conversations live there, code questions in issues.
3. Read `CLAUDE.md` — most "how do I do X in Marcus" questions are answered there.
4. If the doc you're following references a file that doesn't exist or a command that doesn't work, that doc is stale — open a quick PR or issue. Many `docs/CATO/` and `docs/implementation/` files were written against an earlier plan that has since shifted.
