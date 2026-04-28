<style>
@page { size: letter landscape; margin: 0.5in 0.25in 0.25in 0.25in; }
@page :first { margin: 0.25in; }
body { font-size: 9.5pt; line-height: 1.25; }
h1 { font-size: 16pt; margin: 0 0 4pt 0; }
h2 { font-size: 11pt; margin: 8pt 0 4pt 0; }
table { font-size: 8.5pt; width: 100%; border-collapse: collapse; }
th, td { padding: 2pt 6pt; }
hr { margin: 4pt 0; }
p { margin: 2pt 0; }
</style>

# Marcus · PyCon 2026 Sprint Menu

**Long Beach, CA · May 2026** · github.com/lwgray/marcus · maintainer **@lwgray**

Pick a dish. Comment on the issue to claim it. Branch off `develop`, PR back to `develop`. Full details: `docs/sprints/pycon-2026.md`

---

## 🥗 Appetizers — 15–45 min · *first-time-friendly*

| # | Title | Time | Flavor |
|---|---|---|---|
| **#26** | Document MCP integration for Claude Desktop + VS Code | 20–40 m | 📘 docs |
| **#66** | Remove hard-coded MCP client paths *(critical — breaks every clone)* | 30–45 m | 🔥 bug |
| **#115** | Fix `PlankaKanban` usage in `get_all_board_tasks()` | 15–25 m | 🧹 refactor |
| **#198** | Handle empty Planka response during project discovery | 15–25 m | 🐛 bug |
| **#221** | Remove debug logging in `request_next_task` hot path | 20–30 m | ⚡ perf |
| **#228** | Audit log missing `duration_ms` for `request_next_task` | 20–35 m | 🐛 bug |
| **#274** | Fix broken Sphinx index files (64 orphaned pages) | 30–45 m | 📘 docs |
| **#278** | Write documentation for `/marcus` Claude Code skill | 30–45 m | 📘 docs |
| **#283** | Fix docstring style violations + remove `-FUTURE` files | 30–45 m | 🧹 cleanup |

## 🍝 Main Courses — 1–2.5 hr · *comfortable reading Python*

| # | Title | Time | Flavor |
|---|---|---|---|
| **#219** | Perf: O(N·M·P) nested loop in phase filtering | 1.5–2.5 h | ⚡ perf |
| **#229** | Skill: robust error handling for repo path discovery | 1–2 h | 🐛 bug |
| **#231** | Skill: add `--dry-run` mode | 1.5–2.5 h | ✨ feature |
| **#236** | OpenAI provider end-to-end smoke test | 1.5–2.5 h | 🧪 test |
| **#237** | Add 5 undocumented MCP tool groups to API reference | 45–75 m | 📘 docs |
| **#240** | Write "How to add a new kanban provider" guide | 90–120 m | 📘 docs |
| **#241** | Scaffold Jira kanban provider stub | 2–3 h | ✨ integration |
| **#244** | Write "How to add a new MCP tool" guide | 60–90 m | 📘 docs |
| **#264** | Persist AI config at startup for `marcus status` | 1.5–2.5 h | 🐛 bug |
| **#284** | Fix Cato board view to match Marcus kanban board | 1.5–2.5 h | 🐛 bug |
| **#324** | Gate `full-test-suite` CI on push to main + nightly | 1–1.5 h | 🚦 CI |
| **#382** | Auto-select decomposer strategy | 2–3 h | ✨ feature |
| **#383** | Synthetic agent for CI and runner validation | 2.5–3 h | 🧪 test |

## 🍮 Desserts — 3+ hr · *experienced contributors*

| # | Title | Time | Flavor |
|---|---|---|---|
| **#72**  | Create unified task graph algorithms module | 3–5 h | 🏗️ refactor |
| **#120** | Benchmark: 1 agent vs 3 agents speedup measurement | 3–5 h | 📊 research |
| **#255** | Backpropagation-style blame attribution | 4–6 h | 🧠 research |
| **#312** | Make `pip install marcus-ai` a complete install path | 4–6 h | 📦 packaging |
| **#338** | Generative validator (LLM writes verification code) | 5–8 h | 🧠 research |
| **#378** | Cato Living Architecture Diagram with GIF export | 5–8 h | 🎨 build |

## 🌙 Night Cap — open-ended bonus issues

| # | Title | Vibe |
|---|---|---|
| **#403** | CLI Agent Runners for all major harness vehicles | 🛠️ Build |
| **#404** | Harness engineering with Ollama — local model vehicles | 📘 Docs + Prototype |
| **#405** | Frontend harness — visual/design skills for agents | 🎨 Design + Build |
| **#406** | How Marcus selects agents by skill — audit + improve | 🔍 Investigation |
| **#407** | How Marcus learns patterns over time — memory audit | 🔍 Investigation |
| **#408** | How Marcus estimates task duration — time model audit | 🔍 Investigation |
| **#409** | Full-page token usage and cost dashboard | 🛠️ Build |

---

## Quick links

| Filter | URL |
|---|---|
| All sprint issues | [github.com/lwgray/marcus/labels/pycon\_2026](https://github.com/lwgray/marcus/labels/pycon_2026) |
| Curated menu | [github.com/lwgray/marcus/labels/sprint-menu](https://github.com/lwgray/marcus/labels/sprint-menu) |
| 🥗 Appetizers | [github.com/lwgray/marcus/labels/appetizer](https://github.com/lwgray/marcus/labels/appetizer) |
| 🍝 Main courses | [github.com/lwgray/marcus/labels/main-course](https://github.com/lwgray/marcus/labels/main-course) |
| 🍮 Desserts | [github.com/lwgray/marcus/labels/dessert](https://github.com/lwgray/marcus/labels/dessert) |

## Tier counts

🥗 9 appetizers  ·  🍝 13 main courses  ·  🍮 6 desserts  ·  🌙 7 night caps  ·  **35 issues total**
