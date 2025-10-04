# 🏛️ Marcus - AI Agent Coordination Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/discord/1409498120739487859?color=7289da&label=Discord&logo=discord&logoColor=white)](https://discord.gg/marcus)
[![GitHub Stars](https://img.shields.io/github/stars/lwgray/marcus?style=social)](https://github.com/lwgray/marcus)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://hub.docker.com/r/marcus/marcus)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io/)

## What is Marcus?
Marcus turns your ideas into working software by coordinating AI agents. Tell Marcus what you want to build in plain English, and it creates a project board that multiple AI agents work from autonomously.

### Why I Built This
I was stuck between micromanaging every agent decision or letting agents run wild. I wanted to step away and trust that agents had enough context to build what I wanted. Marcus solves this by being the project manager - you describe once, agents build with proper context and boundaries.

### How It Works
1. **You say:** "Build a todo app with authentication"
2. **Marcus:** Creates tasks on a GitHub project board with dependencies
3. **Agents:** Pull tasks, get context from previous work, build autonomously
4. **You:** Watch progress, intervene only when needed

Each task is locked to one agent until complete, preventing conflicts. Agents share context through the board, seeing what others built without direct communication.

---

## 🚀 **Quick Start**

### **Prerequisites**
- Docker
- Claude Code or another MCP-compatible AI agent
- AI model: Choose one option:
  - **Free:** Local model with Ollama (zero cost, recommended for contributors)
  - **Paid:** Anthropic or OpenAI API key

### **1. Run Marcus with Docker**

```bash
**Using Planka with Docker Compose**

📖 **See the complete guide:** [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)

**Quick overview:**
```bash
# 1. Clone and start Planka
git clone https://github.com/lwgray/marcus.git
cd marcus
docker-compose up -d postgres planka

# 2. Create project and board in Planka (http://localhost:3333)
# Login: demo@demo.demo / demo
1. Create Project (e.g. "My Project")
2. Note project ID: http://localhost:3333/projects/1234567890
                                                   ^project_id
3. Click `+` to create board (e.g. "My Board")
4. Note board ID http://localhost:3333/boards/56789101112
                                              ^board_id

# 3. Set up your board (IMPORTANT - required for task creation):
 - Go to "Marcus Todo Demo" board
 - Click "Add another list" to create these columns in order:
   • Backlog
   • In Progress
   • Blocked
   • Done
 - Without these lists, task creation will fail!

# 4. Configure and start Marcus
# Option A: Use default config
cp config_marcus.example.json config_marcus.json
# Edit config with your board IDs and API key
docker-compose up -d marcus

# Option B: Use a specific config (Anthropic, GitHub, etc.)
MARCUS_CONFIG=config_marcus.json.anthropic docker-compose up -d marcus

# Option C: Create .env file for persistent config selection
echo "MARCUS_CONFIG=config_marcus.json.anthropic" > .env
docker-compose up -d marcus
```

For detailed setup instructions, troubleshooting, and customization options, see [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md).

### **2. Connect Your AI Agent**
```bash
# For Claude Code:
claude mcp add --transport http marcus http://localhost:4298

# Marcus provides MCP-compatible endpoints for any agent
```

### **3. Configure Your Agent**

**Copy the [Agent System Prompt](https://raw.githubusercontent.com/lwgray/marcus/main/prompts/Agent_prompt.md) to your AI agent:**


**For Claude Code users:**
1. Copy the contents from [prompts/Agent_prompt.md](prompts/Agent_prompt.md)
2. Add to your Claude Code configuration as a CLAUDE.md file

**What this enables:**
- ✅ Autonomous work loop (register → request → work → report → repeat)
- ✅ Context sharing through artifacts and decisions
- ✅ Smart dependency handling with `get_task_context`
- ✅ Progress reporting at 25%, 50%, 75%, 100%
- ✅ Architectural decision logging for other agents
- ✅ Continuous task execution without waiting for user input

**Want to understand or customize the workflow?** See the [Agent Workflow Guide](docs/source/guides/agent-workflows/agent-workflow.md) for detailed explanations of each component.

### **4. Start Building**
```bash
# Tell your configured agent:
"Create a project for a todo app with Marcus and start working"

# The agent will automatically:
# 1. Register with Marcus
# 2. Create Tasks onto the Planka board from your description
# 3. Request and work on tasks continuously
# 4. Report progress as it goes
# 5. Keep working until all tasks are done
```

### **✅ What You'll See**
- Agent registers itself with Marcus ("Agent claude-1 registered")
- Project created on GitHub with tasks
- Agent continuously pulling tasks and working
- Progress updates: "25% complete", "50% complete", etc.
- Tasks moving through board columns: TODO → IN PROGRESS → DONE
- Context flowing between tasks (API specs → implementation → tests)

### **5. Add More Agents (Optional)**
```bash
# Want multiple agents working in parallel? Three options:

# Option A: Multiple windows (simplest)
# Open a new terminal/Claude window, connect to Marcus, and start another agent
# Both agents will pull different tasks from the same board

# Option B: Claude subagents
# If using Claude, launch subagents with the Task tool
# Each subagent automatically registers and works independently

# Option C: Git worktrees (prevents code conflicts)
git worktree add ../project-agent2 -b agent2-branch
# Each agent works in its own directory/branch
# Merge when ready
```

---

## 🎯 **What Makes Marcus Different**

### **Open Source & Accessible**
Unlike proprietary AI coding tools, Marcus is completely open source. Anyone can use it, modify it, and contribute to make it better.

### **Zero to Software, Fast**
Marcus empowers anyone - even non-programmers - to build real software. Describe what you want in plain English, and watch it get built.

### **True Autonomous Agents**
- **Other tools:** You copy-paste between chats or manage each agent
- **Marcus:** Agents work independently with shared context through the board
- **Result:** You can actually step away while software gets built

### **Community-Driven**
Built by developers, for developers. We're focused on making software creation accessible to everyone, not maximizing profits.

---

## 🚨 **Troubleshooting**

| Problem | Solution |
|---------|----------|
| **"Connection refused"** | Ensure Marcus Docker container is running on port 4298 |
| **"No tasks available"** | Agent needs to create a project first with `create_project` |
| **"Agent not registered"** | Agent must call `register_agent` before requesting tasks |
| **"GitHub auth failed"** | Check GitHub token has project permissions |
| **"Failed to create any tasks" (Planka)** | Board has no lists! Add lists: Backlog, In Progress, Blocked, Done |
| **"find_target_list failed"** | Open Planka board and create at least one list/column |

---

## 🤝 **Contributing**

> **📖 Developer guides:**
> - [Local Development Setup](docs/source/developer/local-development.md) - First-time setup
> - [Development Workflow](docs/source/developer/development-workflow.md) - Daily workflows

Marcus is open source and we need your help!

### **Priority Areas**
1. **Kanban Provider Integrations** - Add Jira, Trello, Linear support
2. **Documentation** - Tutorials, use cases, examples
3. **Use Case Definitions** - Show what Marcus can build

### **Quick Start**
```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/marcus.git
cd marcus

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [Local Development Setup](docs/source/developer/local-development.md) for detailed guidelines.

---

## ⚙️ **Configuration**

> **📖 Full reference:** [Configuration Guide](docs/CONFIGURATION.md)

Marcus supports multiple configuration methods:

**Quick config via environment variables:**
```bash
MARCUS_KANBAN_PROVIDER=github \
MARCUS_KANBAN_GITHUB_TOKEN=ghp_... \
MARCUS_KANBAN_GITHUB_OWNER=your_username \
MARCUS_KANBAN_GITHUB_REPO=your_repo \
MARCUS_AI_ANTHROPIC_API_KEY=sk-ant-... \
docker-compose up -d
```

**Or use a config file:**
```bash
# Use default config
cp config_marcus.example.json config_marcus.json
# Edit with your settings
docker-compose up -d

# Or select a specific config
MARCUS_CONFIG=config_marcus.json.anthropic docker-compose up -d
```

See the [Configuration Reference](docs/source/developer/configuration.md) for all available options.

---

## 📚 **Documentation**

### **Getting Started**
- **[Quick Start](docs/source/getting-started/quickstart.md)** - Get Marcus running in 5 minutes
- **[Docker Quickstart](DOCKER_QUICKSTART.md)** - Complete Docker setup guide
- **[Agent System Prompt](prompts/Agent_prompt.md)** - Configure your AI agent
- **[Core Concepts](docs/source/getting-started/core-concepts.md)** - Understand Marcus fundamentals

### **Development**
- **[Local Development Setup](docs/source/developer/local-development.md)** - First-time setup and directory structure
- **[Development Workflow](docs/source/developer/development-workflow.md)** - Daily development workflows (restart, rebuild, test)
- **[Configuration Reference](docs/source/developer/configuration.md)** - All environment variables and config options

### **Agent Workflows**
- **[Agent Workflow Guide](docs/source/guides/agent-workflows/agent-workflow.md)** - How agents interact with Marcus
- **[Registration](docs/source/guides/agent-workflows/registration.md)** - How agents register
- **[Requesting Tasks](docs/source/guides/agent-workflows/requesting-tasks.md)** - Task assignment
- **[Getting Context](docs/source/guides/agent-workflows/getting-context.md)** - Task dependencies
- **[Reporting Progress](docs/source/guides/agent-workflows/reporting-progress.md)** - Progress tracking
- **[Handling Blockers](docs/source/guides/agent-workflows/handling-blockers.md)** - Error recovery

### **Full Documentation**
- **[Complete Documentation](https://marcus.readthedocs.io/)** - Full Sphinx docs (when published)
- **[Docker Hub Publishing](DOCKER_HUB_PUBLISHING.md)** - Publishing Marcus images

---

## 🌟 **Community**

- 💬 **Discord**: [Join our Discord](https://discord.gg/marcus) - Real-time help and discussions
- 🗣️ **Discussions**: [GitHub Discussions](https://github.com/lwgray/marcus/discussions)
- 🐛 **Issues**: [GitHub Issues](https://github.com/lwgray/marcus/issues)
- 📖 **Docs**: [Full Documentation](docs/)
- 🤝 **Contributing**: [Contribution Guide](CONTRIBUTING.md)

---

## 📄 **License**

MIT License - see [LICENSE](LICENSE) for details

---

**⭐ Star us on GitHub if Marcus helps you build something awesome!**
