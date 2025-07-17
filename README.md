# 🏛️ Marcus - AI Agent Coordination Platform

## What is Marcus?

Marcus is an AI-powered project coordinator that breaks down requirements into tasks and assigns them to your AI
agents. It's designed around a simple philosophy: give agents clear context and let them work autonomously.
[Learn more about our approach →](docs/philosophy.md)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Ultimately, Marcus coordinates AI agents (Claude, GPT, etc.) to work together on projects with **context sharing**, **dependency resolution**, and **continuous learning**. Unlike traditional project management, Marcus is built specifically for autonomous AI agents.

---

## 🚀 **5-Minute Demo Setup**

### **Prerequisites**
- Python 3.11+
- Docker
- Claude Code
- AI Model (choose one):
  - Anthropic API key (for Claude) - [Get one here](https://console.anthropic.com/)
  - OR local model with Ollama - [Setup guide](docs/user-guide/how-to/setup-local-llm.md)

### **1. Setup Planka Board (1 minute)** Marcus maintains context with a Kanban Board
#### Bring Your Own Board (BYOB)
```bash
# Clone and start the kanban-mcp server
git clone https://github.com/bradrisse/kanban-mcp.git ~/dev/kanban-mcp
cd ~/dev/kanban-mcp
docker-compose up -d

# Planka will be available at http://localhost:3333
# Default login: demo@demo.demo / demo
```

### **2. Install Marcus (30 seconds)**
```bash
git clone https://github.com/lwgray/marcus.git
cd marcus
pip install -r requirements.txt
```

### **3. One-Command Demo Setup (2.5 minutes)**
```bash
# Automated setup: creates Planka project, updates config, creates tasks
python setup_marcus_demo.py

# This script will:
# - Guide you through Planka setup if needed
# - Create "Marcus Todo Demo" project automatically
# - Update config_marcus.json with correct IDs
# - Create 17 todo app tasks ready for AI agents
# - Give you final setup instructions
```

### **4. Starting Marcus (30 seconds)**
```bash
# Start Marcus from the root directory
cd /path/to/marcus
python -m src.marcus_mcp.server

# Marcus will start and be ready to accept connections
```

### **5. Connect Claude Code (30 seconds)**
```bash
# In a DIFFERENT directory (not marcus root), configure Claude Code:
cd ~/my-project  # or any directory outside marcus
claude mcp add python /path/to/marcus/src/marcus_mcp/server.py
```

### **6. Run Demo & Watch Magic (30 seconds)**
```bash
# In Claude Code:
# 1. Copy content from prompts/Agent_prompt.md as your system prompt
# 2. Add your Anthropic API key to config_marcus.json
#    Or use a local model - see docs/user-guide/how-to/setup-local-llm.md
# 3. Say: "Register with Marcus and start working"
# 4. Watch agent automatically complete tasks in Planka!
```

### **✅ You Should See:**
- Tasks moving through board columns in Planka
- Agent reporting progress and getting new assignments
- Rich context passed between tasks
- Automatic error recovery when agents get stuck

---

## 🎯 **What Makes Marcus Special**

### **🧠 Context Intelligence**
When Agent A completes "Create User API", Agent B automatically knows:
- What endpoints were created
- What data models exist
- Architectural decisions made
- How to integrate with existing code

### **🔄 Continuous Work Loop**
Agents never stop working:
```
Register → Request Task → Work → Report Progress → Request Next Task → ...
```

### **📚 Learning & Adaptation**
Marcus learns from every project:
- Successful patterns get recommended
- Common errors get predicted and prevented
- Task assignment improves over time

### **🛡️ Error Recovery**
When agents get stuck, Marcus provides:
- AI-powered suggestions based on context
- Alternative approaches
- Escalation to human when needed

---

## 🚨 **Quick Troubleshooting**

| Problem | Solution |
|---------|----------|
| **"No tasks available"** | Run `python setup_marcus_demo.py` to create demo tasks |
| **"Connection failed"** | Check Planka running at localhost:3333 and API keys in config_marcus.json |
| **"Agent not found"** | Verify agent used `register_agent` tool first |
| **Setup script fails** | Ensure Planka is running: `cd ~/dev/kanban-mcp && docker-compose up -d` |

---

## 📚 **What's Next?**

### **Learn More**
- **[API Documentation](docs/api/)** - Complete MCP tool reference
- **[System Architecture](docs/systems/)** - Deep dive into all 32 systems
- **[Agent Prompt Guide](prompts/Agent_prompt.md)** - Understanding the work loop

### **Real Projects**
- Try the full todo app: `python projects/todo_app/create_all_todo_app_cards.py`
- Create your own project: Use `create_project` MCP tool
- Build with multiple agents: Register different agent types

### **Extend Marcus**
- Add new AI providers ([OpenAI](docs/systems/07-ai-intelligence-engine.md), [local models with Ollama](docs/user-guide/how-to/setup-local-llm.md))
- Connect to GitHub Projects or Linear
- Build custom MCP tools

---

## 💡 **Pro Tips**

### **Project Location**
⚠️ **Always build projects outside Marcus root** - Create in `~/projects/` or similar to avoid git conflicts

### **Multi-Agent Strategies**
- **Option 1**: Git worktrees - Each agent on separate branch, merge when done
  ```bash
  git worktree add ../project-agent1 agent1-branch
  ```
- **Option 2**: Single agent with subagents - No merging needed, sequential work

### **Enable Context Awareness**
Set `"context_dependency": true` in `config_marcus.json` - Agents see previous implementations, API endpoints, and decisions

---

## 🤝 **Get Help**

- 💬 **Questions**: [GitHub Discussions](https://github.com/lwgray/marcus/discussions)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/lwgray/marcus/issues)
- 📖 **Documentation**: [Full Docs](docs/)

---

**⭐ Star us on GitHub • 🍴 Fork and contribute • 💬 Join our community**

*Built with ❤️ for the AI development community*
