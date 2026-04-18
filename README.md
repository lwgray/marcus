<h1 align="center">Marcus</h1>

<p align="center">
  <strong>Agents should coordinate through shared state, not conversation.</strong>
</p>

<p align="center">
  <a href="#get-started"><img src="https://img.shields.io/badge/Get_Started-Setup-blue?style=for-the-badge" alt="Get Started"></a>
  <a href="#see-it-work"><img src="https://img.shields.io/badge/See_It_Work-Demo-green?style=for-the-badge" alt="See It Work"></a>
  <a href="#how-it-compares"><img src="https://img.shields.io/badge/Compare-Frameworks-purple?style=for-the-badge" alt="Compare"></a>
  <a href="ROADMAP.md"><img src="https://img.shields.io/badge/Roadmap-View-orange?style=for-the-badge" alt="Roadmap"></a>
</p>

<p align="center">
  <a href="https://github.com/lwgray/marcus"><img src="https://img.shields.io/github/stars/lwgray/marcus?style=social" alt="GitHub Stars"></a>
  <a href="https://discord.com/channels/1409498120739487859/1409498121456848907"><img src="https://img.shields.io/discord/1409498120739487859?color=7289da&label=Discord&logo=discord&logoColor=white" alt="Discord"></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python 3.11+">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-Compatible-green" alt="MCP Compatible"></a>
</p>

---

## News

| Date | Update |
|------|--------|
| **2026-04-17** | v0.3.4 — `contract_first` default decomposer, `recommended_agents` in API response, `PROTOCOL.md` |
| **2026-04-16** | Presented Marcus and Cato at Machine Learning Ambassador Conference in Des Moines, Iowa at John Deere Financial
| **2026-04-03** | v0.3.0 — SQLite default provider, Epictetus evaluation, `/marcus` skill |
| **2026-03-21** | v0.2.1 — lease recovery, progressive timeouts, structured agent handoffs |
| **2026-03-16** | v0.2.0 — AI-powered validation, centralized config, 115 commits since v0.1.3.1 |
| **2025-10-20** | v0.1.3.1 — sweep-line parallelism algorithm, tmux multi-agent support |
| **2025-10-19** | Presented Marcus to "AI Assistants" Biweekly Group at Blue River Technology in Santa Clara, California
| **2025-10-18** | v0.1.3 — subtask assignment fix, optimized project creation |
| **2025-10-16** | v0.1.2 — CPM scheduling, dependency graphs, parallelization improvements |
| **2025-10-13** | v0.1.1 — initial release as "PM Agent", MCP protocol, Planka integration |
| **2025-06-15** | Project started — first commit as PM Agent |

---

## The Problem Nobody Talks About

Multi-agent AI is broken at scale.

Every framework today coordinates agents through **conversation** — group chats,
message passing, chain-of-thought relays. This works with 2-3 agents. At scale,
it collapses:

- **Context degrades.** Each agent gets a growing wall of chat history. Signal drowns in noise.
- **Work duplicates.** Without shared state, agents don't know what others have done.
- **Failures cascade.** One agent crashes and the conversation context is gone. No recovery.
- **Adding agents adds chaos.** More agents = more messages = slower, less reliable coordination.

The fundamental mistake: treating coordination as a conversation problem.
It's a **state management** problem.

---

## A Different Approach: Board-Mediated Coordination

Marcus uses a simple idea: **give agents a shared task board** instead of making them talk to each other. We call this **board-mediated coordination**.

Agents never talk to each other. They talk to the board.

```
You: "Build a todo app with authentication"
         |
         v
   +-----------+
   |   Marcus   |  Breaks work into tasks on a shared board
   +-----------+
         |
   +-----+-----+-----+
   |     |     |     |
 Agent  Agent Agent Agent   Each pulls tasks independently
   |     |     |     |
   +-----+-----+-----+
         |
   +-----------+
   |   Board    |  Shared state: tasks, context, artifacts, decisions
   +-----------+
```

**The board is memory, coordinator, and audit trail.**

Each task carries its own context — requirements, dependencies, artifacts from
prior tasks. When an agent picks up a task, it gets exactly the context it needs.
No chat history. No lost threads. No duplicate work.

When an agent fails, the task stays on the board with its progress. Another agent
picks it up and continues. The board is the system of record.

> *The board is the system.*

---

## See It Work

**One command. Multiple agents. Working software.**

**1. You describe what to build:**

<video src="docs/assets/build_command.mp4" autoplay loop muted playsinline></video>

**2. Agents work in parallel:**

<video src="docs/assets/tmux.mp4" autoplay loop muted playsinline></video>

**3. Coordinating through the board, not conversation:**

<video src="docs/assets/swim_lanes.mp4" autoplay loop muted playsinline></video>

**4. You come back to this:**

<video src="docs/assets/product.mp4" autoplay loop muted playsinline></video>

Track everything in real-time with [Cato](https://github.com/lwgray/cato),
the companion visualization dashboard.

---

## Get Started

**Prerequisites:**
- Python 3.11+
- [Claude Code](https://claude.ai/code) (or any agent that supports [MCP](https://modelcontextprotocol.io/))
- An LLM provider:
  - **Free:** Local model with [Ollama](https://ollama.ai) (zero cost)
  - **Paid:** Anthropic or OpenAI API key
- `tmux` — required for **Runner mode** (`/marcus` skill spawns agents in panes). Not needed for Attach mode.

### Step 1: Install

```bash
git clone https://github.com/lwgray/marcus.git
cd marcus
pip install -e .
```

### Step 2: Configure Your LLM Provider

Marcus uses an LLM to decompose projects into tasks and validate work.

```bash
cp .env.example .env
cp config_marcus.example.json config_marcus.json
```

Edit `.env` for your API key and `config_marcus.json` for provider, model, and kanban backend:

```bash
# .env — API keys
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
# OPENAI_API_KEY=sk-your-key-here
```

| Provider | Cost | Setup |
|----------|------|-------|
| Anthropic | Paid | Set `ANTHROPIC_API_KEY` in `.env` — works out of the box |
| OpenAI | Paid | Set `OPENAI_API_KEY` in `.env`, set `ai.provider` to `"openai"` in `config_marcus.json` |
| Ollama | Free | Install [Ollama](https://ollama.ai), pull a model, set `ai.provider` to `"local"` in `config_marcus.json` |

> **Note:** This is the LLM Marcus uses for task decomposition.
> Your AI coding agents (Claude Code, Codex, etc.) use their own API keys separately.

### Step 3: Start Marcus

```bash
./marcus start
```

> **No Docker required.** Marcus uses SQLite by default — everything runs locally.
> For a visual kanban board UI, see [Advanced Setup with Planka](#advanced-setup-planka-board-ui) below.

### Step 4: Choose Your Mode

There are two ways to use Marcus:

| | **Attach mode** | **Runner mode** |
|---|---|---|
| **You start** | One agent manually | Fleet of agents via `/marcus` skill |
| **Prompt wiring** | You drop `CLAUDE.md` in your project dir | Skill injects system prompt automatically |
| **Requires** | Any MCP agent | Claude Code + tmux |
| **Best for** | Custom runtimes, single agents, experimentation | Hands-off multi-agent runs |

#### Attach mode — wire it yourself

Register Marcus as an MCP server **from your project directory** (registration is project-scoped):

```bash
cd ~/projects/my-todo-app
claude mcp add --transport http marcus http://localhost:4298/mcp
```

Copy [prompts/Agent_prompt.md](prompts/Agent_prompt.md) into your project as `CLAUDE.md`:

```bash
cp /path/to/marcus/prompts/Agent_prompt.md ~/projects/my-todo-app/CLAUDE.md
```

Then launch your agent from the project directory and call `create_project` directly.

#### Runner mode — `/marcus` skill handles everything

Install the skill once:

```bash
cp -r /path/to/marcus/skills/marcus ~/.claude/skills/marcus
```

The skill registers MCP, injects the agent prompt, and spawns agents in tmux panes automatically. See Step 6.

> **Building a runner for a different runtime?** See [PROTOCOL.md](PROTOCOL.md) for the developer-facing spec.

### Step 5: Start Cato Dashboard (Optional)

```bash
# In a sibling directory
git clone https://github.com/lwgray/cato.git
cd cato && pip install -e . && ./cato start
# Open http://localhost:5173
```

### Step 6: Your First Project (Runner mode)

Create a project directory and launch your agent from there:

```bash
mkdir ~/projects/my-todo-app
cd ~/projects/my-todo-app
claude --dangerously-skip-permissions
```

Then prompt:

```
/marcus Build a todo app with authentication using 3 agents
```

The skill registers Marcus MCP, injects the agent prompt, decomposes the project into tasks,
and spawns agents in tmux panes. You walk away, you come back to working software.

<details>
<summary><strong>Using Attach mode instead?</strong> (Codex, Gemini CLI, Kimi, AutoGen, or any MCP agent)</summary>

1. Register `http://localhost:4298/mcp` as an MCP server **from your project directory**
2. Put [prompts/Agent_prompt.md](prompts/Agent_prompt.md) in the agent's system prompt (or as `CLAUDE.md` in the project dir for Claude Code)
3. Launch your agent from the project directory
4. Have one agent call `create_project`, then all agents call `register_agent` and enter the work loop

Each agent registers independently and pulls tasks from the shared board. No tmux required.

</details>

<details>
<summary><strong>Running experiments at scale?</strong> Use Posidonius (web dashboard for multi-run management)</summary>

[Posidonius](https://github.com/lwgray/posidonius) is the experiment dashboard
for launching and managing multi-agent runs across any CLI agent. It handles
agent spawning, experiment tracking, and provides a web UI for monitoring.

```bash
git clone https://github.com/lwgray/posidonius.git
cd posidonius && pip install -e .
```

See the [Posidonius README](https://github.com/lwgray/posidonius) for setup.
By default Posidonius writes projects to `~/experiments/`.

</details>

---

### Advanced Setup: Planka Board UI

For a visual kanban board with drag-and-drop, Marcus supports
[Planka](https://planka.app/) as a backend. Requires Docker.

```bash
docker compose up -d          # Starts Planka + Postgres
cp config_marcus.example.json config_marcus.json
# Edit config_marcus.json: set kanban.provider to "planka"
./marcus start
```

Open http://localhost:3333 to see the board (login: `demo@demo.demo` / `demo`).

---

## What You'll See

- Tasks flowing through the board: **Backlog -> In Progress -> Done**
- Agents pulling work independently, no conflicts
- Context passing between tasks (API specs -> implementation -> tests)
- Progress updates: 25%, 50%, 75%, 100%
- Real-time visualization in Cato
- Full audit trail of every decision and artifact

> *The moment it clicks: I didn't have to manage any of this.*

---

## How It Compares

| | Group Chat Coordination | Board-Mediated Coordination |
|---|---|---|
| **Used by** | AutoGen, CrewAI, LangGraph | **Marcus** |
| **Coordination** | Conversation between agents | Shared board state |
| **Context at scale** | Degrades (growing chat history) | Preserved per-task |
| **Agent failure** | Lost context, no recovery | Resume from board state |
| **Visibility** | Chat logs | Full audit trail + Cato dashboard |
| **Add more agents** | More chaos, more messages | More throughput |
| **Enterprise ready** | Limited governance | Audit trails, accountability |

Marcus doesn't compete on raw speed. It competes on **coordination quality,
observability, and enterprise readiness**. When you need to know *what happened,
who did it, and why* — the board gives you that for free.

---

## Architecture

```
+-------------------+     +------------------+     +------------------+
|   Your AI Agent   |     |   Your AI Agent  |     |   Your AI Agent  |
| (Claude, Cursor)  |     |  (Claude Code)   |     |   (Any MCP)      |
+--------+----------+     +--------+---------+     +--------+---------+
         |                         |                         |
         +------------+------------+------------+------------+
                      |         MCP Protocol         |
                      v                              v
              +-------+--------+
              |     Marcus      |  Orchestrator: task creation,
              |   (runs local)  |  assignment, context, validation
              +-------+--------+
                      |
              +-------+--------+
              |  Shared Board   |  Shared state: tasks, context,
              | (SQLite/Planka) |  artifacts, decisions
              +----------------+
```

**Key design decisions:**
- **Agents are stateless.** All state lives on the board.
- **Tasks are the unit of coordination.** Each task has context, dependencies, and artifacts.
- **MCP is the interface.** Any MCP-compatible agent works with Marcus.
- **Observability is built in.** Every action is traceable through the board and Cato.

See [Architecture Docs](docs/source/architecture/) for deep dives.

---

## Milestones

| Version | Date | Commits | Highlights |
|---------|------|---------|------------|
| **v0.3.4** | 2026-04-17 | — | `contract_first` default decomposer (board complete before agents spawn), `recommended_agents` in `create_project` response, `PROTOCOL.md` agent protocol spec, pre-fork synthesis (#355), scope annotation (#356) |
| **v0.3.0** | 2026-04-03 | 59 | SQLite default provider, Epictetus evaluation, `/marcus` one-command experiments, agent resilience overhaul, tmux reliability |
| **v0.2.1** | 2026-03-21 | 1 | Lease recovery with progressive timeouts, structured RecoveryInfo for agent handoffs, configurable LLM temperature |
| **v0.2.0** | 2026-03-16 | 115 | AI-powered task validation, centralized config system, composition-aware PRD extraction, enterprise mode task decomposition, constraint propagation, soft/hard dependencies, post-project analysis (Phase 1+2), MLflow experiment tracking, intelligent task pattern selection, bundled domain design tasks |
| **v0.1.3.1** | 2025-10-20 | 4 | Sweep-line algorithm for correct parallelism calculation, tmux multi-agent experiment support, phase enforcer cross-feature dependency fix |
| **v0.1.3** | 2025-10-18 | 2 | Optimized project creation (eliminated duplicate dependency wiring), subtask assignment fix |
| **v0.1.2** | 2025-10-16 | ~50 | CPM scheduling algorithm, unified dependency graphs, optimal agent count calculation, cross-parent dependency wiring, race condition fixes, MLflow trace integration |
| **v0.1.1** | 2025-10-13 | ~80 | Initial release. Rebranded from PM Agent to Marcus. MCP protocol, Planka kanban integration, workspace isolation, hybrid intelligent coordination, NLP tools, AI-powered feature analysis, board quality validator |

**Project started:** 2025-06-15 as "PM Agent" — rebranded to Marcus in October 2025.

See [CHANGELOG.md](CHANGELOG.md) for full release notes and [ROADMAP.md](ROADMAP.md) for what's next.

---

## Join the Movement

Marcus isn't just a tool. It's a thesis: **board-mediated coordination is the
right pattern for the agent era.**

We're building the coordination layer that lets agents work together at scale
with governance, accountability, and full visibility. Open source. MIT licensed.
Community-driven.

### Priority Contributions

1. **Kanban Provider Integrations** — Jira, Trello, Linear support
2. **Documentation** — tutorials, use cases, examples
3. **Use Case Definitions** — show what Marcus can build beyond software

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/marcus.git
cd marcus
pip install -r requirements-dev.txt
pytest tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [Local Development Setup](docs/source/developer/local-development.md).

### Community

- [Discord](https://discord.com/channels/1409498120739487859/1409498121456848907) — real-time help and discussions
- [GitHub Discussions](https://github.com/lwgray/marcus/discussions) — ideas and questions
- [GitHub Issues](https://github.com/lwgray/marcus/issues) — bugs and feature requests

---

## For Researchers and Educators

**Board-mediated coordination** is a named, citable pattern for multi-agent systems.

If you're teaching or researching multi-agent coordination:
- The pattern is documented in [Architecture Docs](docs/source/architecture/)
- Example projects demonstrate the pattern in action
- Marcus is MIT licensed — use it in courses, papers, and experiments

Named after Marcus Aurelius. The Stoic philosophy runs deep: discipline,
transparency, and letting the system — not any single agent — hold the truth.

---

## Going Deeper

- [Configuration Reference](docs/source/developer/configuration.md) — all options
- [Agent Workflow Guide](docs/source/guides/agent-workflows/agent-workflow.md) — how agents interact
- [Development Workflow](docs/source/developer/development-workflow.md) — daily dev workflows
- [Local Development Setup](docs/source/developer/local-development.md) — first-time setup
- [Roadmap](ROADMAP.md) — where we're headed

---

## License

MIT License — see [LICENSE](LICENSE) for details.

**Star us on GitHub if Marcus helps you build something awesome.**
