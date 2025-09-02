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
- GitHub account with a [personal access token](https://github.com/settings/tokens) (needs `project` scope)
- Claude Code or another MCP-compatible AI agent
- API key for your AI model (Anthropic, OpenAI, or local with Ollama)

### **1. Run Marcus with Docker**
```bash
# Quick start (config via environment variables)
docker run -p 4298:4298 \
  -e GITHUB_TOKEN=your_github_token \
  -e ANTHROPIC_API_KEY=your_api_key \
  marcus/marcus:latest

# Or with a config file
docker run -p 4298:4298 \
  -v $(pwd)/config_marcus.json:/app/config_marcus.json \
  marcus/marcus:latest

# Build from source
git clone https://github.com/lwgray/marcus.git
cd marcus
cp config_marcus.example.json config_marcus.json
# Edit config_marcus.json with your settings
docker build -t marcus .
docker run -p 4298:4298 -v $(pwd)/config_marcus.json:/app/config_marcus.json marcus
```

### **2. Connect Your AI Agent**
```bash
# For Claude Code:
claude mcp add http://localhost:4298/marcus

# Marcus provides MCP-compatible endpoints for any agent
```

### **3. Configure Your Agent**
```bash
# Use this system prompt to establish the Marcus workflow:
# Copy the contents of prompts/Agent_prompt.md as your agent's system prompt

# This gives your agent the complete workflow including:
# - Autonomous work loop (register → request → work → report → repeat)
# - Context sharing through artifacts and decisions
# - Progress reporting and error recovery
# - Dependency handling

# Want to build your own workflow? See docs/agent-workflow.md for all components
```

### **4. Start Building**
```bash
# Tell your configured agent:
"Create a project for a todo app with Marcus and start working"

# The agent will automatically:
# 1. Register with Marcus
# 2. Create a GitHub project board from your description
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

---

## 🤝 **Contributing**

Marcus is open source and we need your help! Priority areas:

### **Most Needed**
1. **Kanban Provider Integrations** - Add support for Jira, Trello, Linear, etc.
2. **Documentation** - Tutorials, use cases, and examples
3. **Use Case Definitions** - Show what Marcus can build

### **Getting Started**
```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/marcus.git
cd marcus

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Submit PR with your contribution
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## ⚙️ **Configuration**

Marcus needs a few settings to work. You can provide them via:

1. **Environment variables** (easiest for Docker):
   - `GITHUB_TOKEN` - Your GitHub personal access token
   - `ANTHROPIC_API_KEY` - For Claude models
   - `OPENAI_API_KEY` - For GPT models

2. **Config file** (`config_marcus.json`):
   ```json
   {
     "github_token": "ghp_...",
     "anthropic_api_key": "sk-ant-...",
     "kanban_provider": "github"
   }
   ```

See [config_marcus.example.json](config_marcus.example.json) for all options.

---

## 📚 **Documentation**

- **[Agent Prompt](prompts/Agent_prompt.md)** - The complete agent workflow and system prompt
- **[Configuration Guide](docs/configuration.md)** - All config options explained
- **[API Reference](docs/api/)** - All MCP tools documented
- **[Agent Workflow](docs/agent-workflow.md)** - How agents interact with Marcus
- **[Architecture Overview](docs/architecture.md)** - How Marcus works internally

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
