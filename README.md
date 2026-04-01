<h1 align="center">Marcus</h1>

<p align="center">
  <strong>Agents should coordinate through shared state, not conversation.</strong>
</p>

<p align="center">
  <a href="#get-started"><img src="https://img.shields.io/badge/Get_Started-5_min-blue?style=for-the-badge" alt="Get Started"></a>
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
| **2026-04-03** | v0.3.0 — SQLite default provider, Epictetus evaluation, `/marcus` skill, PyPI publish (`pip install marcus-ai`) |
| **2026-03-21** | v0.2.1 — lease recovery, progressive timeouts, structured agent handoffs |
| **2026-03-16** | v0.2.0 — AI-powered validation, centralized config, 115 commits since v0.1.3.1 |
| **2025-10-20** | v0.1.3.1 — sweep-line parallelism algorithm, tmux multi-agent support |
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

Marcus introduces a named pattern: **board-mediated coordination**.

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

**You describe once. Agents build with context.**

```
You: "Create a project for a todo app with Marcus and start working"
```

What happens:

1. Agent registers with Marcus
2. Marcus breaks your description into tasks with dependencies
3. Tasks appear on the Planka board: Backlog -> In Progress -> Done
4. Agent pulls the first available task, gets full context
5. Agent builds, reports progress (25%, 50%, 75%, 100%)
6. Artifacts from completed tasks flow as context to dependent tasks
7. Next agent picks up the next task — with context from what was already built
8. Repeat until done

**You walk away. You come back to working software.**

Track everything in real-time with [Cato](https://github.com/lwgray/cato),
the companion visualization dashboard.

<!-- TODO: Add screenshot/gif of Cato showing agents working -->

---

## Get Started

**Prerequisites:**
- Python 3.11+
- [Claude Code](https://claude.ai/code) (or any MCP-compatible agent)
- An LLM provider:
  - **Free:** Local model with [Ollama](https://ollama.ai) (zero cost)
  - **Paid:** Anthropic or OpenAI API key

### Step 1: Install

```bash
pip install marcus-ai
```

Or install from source:

```bash
git clone https://github.com/lwgray/marcus.git
cd marcus
pip install -e .
```

### Step 2: Configure Your LLM Provider

Marcus uses an LLM to decompose projects into tasks and validate work.

```bash
cp .env.example .env
```

Edit `.env` and set your API key:

```bash
# For Anthropic (recommended):
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# For OpenAI (alternative — uncomment and fill in):
# OPENAI_API_KEY=sk-your-key-here
```

| Provider | Cost | Setup |
|----------|------|-------|
| Anthropic | Paid | Set `ANTHROPIC_API_KEY` in `.env` |
| OpenAI | Paid | Set `OPENAI_API_KEY` in `.env`, change provider in config |
| Ollama | Free | Install [Ollama](https://ollama.ai), pull a model, set provider to `"local"` in config |

> **Note:** This is the LLM that Marcus itself uses for task decomposition.
> Your AI coding agents (Claude Code, Codex, etc.) use their own API keys separately.

### Step 3: Start Marcus

```bash
./marcus start
```

> **No Docker required.** Marcus uses SQLite by default — everything runs locally.
> For a visual kanban board UI, see [Advanced Setup with Planka](#advanced-setup-planka-board-ui) below.

### Step 4: Connect Your Agent

Marcus exposes an MCP server at `http://localhost:4298/mcp`. Connect your
AI coding agent to it:

```bash
# Claude Code:
claude mcp add --transport http marcus http://localhost:4298/mcp

# Other MCP-compatible agents (Codex, Gemini CLI, Kimi, etc.):
# Add http://localhost:4298/mcp as an MCP server in your agent's config
```

Copy the [Agent System Prompt](prompts/Agent_prompt.md) to your agent's
configuration (e.g., as a CLAUDE.md file for Claude Code, or the equivalent
system prompt for your agent).

### Step 5: Start Cato Dashboard (Optional)

```bash
# In a sibling directory
git clone https://github.com/lwgray/cato.git
cd cato && pip install -e . && ./cato start
# Open http://localhost:5173
```

### Step 6: Your First Project

There are three ways to use Marcus — pick the one that fits your agent:

#### Option A: `/marcus` Skill (Claude Code only)

> **This option requires [Claude Code](https://claude.ai/code).** For other
> agents (Codex, Gemini CLI, Kimi, etc.), use Option B or C below.

Marcus ships with a Claude Code skill in [`skills/marcus/`](skills/marcus/).

Install the skill into `~/.claude/skills/marcus`:

```bash
cp -r skills/marcus ~/.claude/skills/marcus
```

> **Note:** Run Claude Code from the same environment where you installed Marcus
> (`pip install marcus-ai` or `pip install -e .`), so the `/marcus` skill can discover the repo path.

Then prompt:

```
/marcus Build a todo app with authentication using 3 agents
```

The skill generates the experiment config, spawns independent Claude agents in
tmux panes, and wires up a project creator + workers + monitor — all autonomous.

#### Option B: MCP Direct (Any MCP-compatible agent)

This works with **any** agent that supports MCP — Claude Code, Codex, Gemini CLI,
Kimi, or any other MCP client. Each agent connects to Marcus at
`http://localhost:4298/mcp` and uses MCP tools directly.

1. Open your agent with the Marcus MCP server connected
2. Tell it to create a project with Marcus at your chosen complexity
3. Tell it to register as an agent and follow the Marcus agent workflow
4. Open another terminal with a second agent, register it too
5. Repeat for as many agents as you want

```
"Create a project for a todo app with Marcus and start working"
```

#### Option C: Posidonius (Experiment Dashboard)

[Posidonius](https://github.com/lwgray/posidonius) is the experiment dashboard
for launching and managing multi-agent runs across any CLI agent. It handles
agent spawning, experiment tracking, and provides a web UI for monitoring.

```bash
git clone https://github.com/lwgray/posidonius.git
cd posidonius && pip install -e .
```

See the [Posidonius README](https://github.com/lwgray/posidonius) for setup.

#### Comparing the Three

| | `/marcus` Skill | MCP Direct | Posidonius |
|---|---|---|---|
| **Agent** | Claude Code only | Any MCP agent | Any CLI agent |
| **Setup** | One command | Manual per-agent | Web dashboard |
| **Multi-agent** | Auto tmux panes | Manual terminals | Auto-managed |
| **Tracking** | MLflow automatic | Manual | Built-in |
| **Control** | Hands-off | Full control | Configurable |

*Either way: walk away, come back to working software.*

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

> **Why not Docker for Marcus itself?** Agents write to the local filesystem.
> Marcus needs `project_root` to point to where agents write. Running Marcus
> in Docker creates a path mismatch. Docker is only for infrastructure (Planka + Postgres).

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
| **v0.3.0** | 2026-04-03 | 59 | SQLite default provider (`pip install marcus-ai`), Epictetus evaluation, `/marcus` one-command experiments, agent resilience overhaul, tmux reliability |
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
