# PM Agent - AI Project Manager for Autonomous Development Teams

<div align="center">

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![MCP](https://img.shields.io/badge/MCP-Protocol-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

An intelligent project management agent that coordinates autonomous development teams using the Model Context Protocol (MCP).

[Quick Start](#-quick-start) • [Documentation](docs/) • [Architecture](docs/architecture.md) • [Contributing](#-contributing)

</div>

## 🎯 Overview

PM Agent acts as an intelligent project manager that:
- 🤖 Coordinates multiple AI worker agents
- 📋 Manages tasks on Kanban boards (Planka)
- 🧠 Uses AI to resolve blockers and optimize workflows
- ⏱️ Tracks time and progress automatically
- 🔄 Adapts task allocation based on agent capabilities

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Docker (for Planka) or existing Planka instance
- [kanban-mcp](https://github.com/bradrisse/mcp-kanban) installed at `../kanban-mcp`
- Anthropic API key (optional, for AI features)

### Installation

1. **Clone and setup**:
   ```bash
   git clone https://github.com/lwgray/pm-agent.git
   cd pm-agent
   pip install -r requirements.txt
   ```

2. **Start Planka** (if not running):
   ```bash
   docker run -d --name planka -p 3333:1337 ghcr.io/plankanban/planka:latest
   ```

3. **Configure** (copy example and edit):
   ```bash
   cp .env.example .env
   # Add your ANTHROPIC_API_KEY to .env
   ```

4. **Verify setup**:
   ```bash
   python scripts/utilities/test_setup.py
   ```

### Running PM Agent

```bash
# Quick test - view board state
python scripts/utilities/quick_board_view.py

# Interactive testing
python scripts/utilities/interactive_test.py

# Start PM Agent as MCP server
python start_pm_agent_task_master.py

# Run full simulation
python scripts/test_pm_agent_end_to_end.py
```

## 📚 Documentation

- 📖 [Quick Start Guide](docs/quick-start.md) - Get running in 5 minutes
- 🏗️ [Architecture Overview](docs/architecture.md) - System design and components  
- 🔧 [Configuration Guide](docs/configuration.md) - All configuration options
- 🤝 [Worker Agents Guide](docs/worker-agents.md) - Building compatible agents
- 🧪 [Testing Guide](docs/testing-guide.md) - Testing approaches and tools
- 🔌 [Kanban MCP Integration](docs/kanban-mcp-integration.md) - Understanding kanban-mcp
- 🚀 [Beyond MVP](docs/beyond-mvp.md) - Roadmap and scaling
- 📋 [API Reference](docs/api-reference.md) - Complete tool documentation
- 🐛 [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## 🛠️ Key Features

### For Worker Agents
- **Register & Join**: Declare capabilities and join the team
- **Request Tasks**: Get assigned work matching your skills
- **Report Progress**: Update task status in real-time
- **Handle Blockers**: Get AI-powered help when stuck

### For Project Management
- **Smart Task Distribution**: Match tasks to agent capabilities
- **Real-time Monitoring**: Track progress across all agents
- **AI-Powered Resolution**: Resolve blockers intelligently
- **Automatic Time Tracking**: Monitor task duration

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Worker Agent   │     │  Worker Agent   │     │  Worker Agent   │
│   (Frontend)    │     │   (Backend)     │     │     (QA)        │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │ MCP                   │ MCP                   │ MCP
         └───────────────┬───────┴───────────────────────┘
                         │
                ┌────────▼────────┐
                │    PM Agent     │
                │  (MCP Server)   │
                └────────┬────────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
    ┌───────▼──────┐ ┌───▼────┐ ┌────▼─────┐
    │ Kanban MCP   │ │   AI   │ │ Monitor  │
    │   Client     │ │ Engine │ │          │
    └───────┬──────┘ └───┬────┘ └──────────┘
            │            │
    ┌───────▼──────┐ ┌───▼────┐
    │   Planka     │ │ Claude │
    │   (Kanban)   │ │  API   │
    └──────────────┘ └────────┘
```

## 📁 Project Structure

```
pm-agent/
├── src/                    # Core source code
│   ├── core/              # Models and business logic
│   ├── integrations/      # MCP & Kanban clients
│   ├── monitoring/        # Project monitoring
│   ├── config/            # Configuration management
│   └── communication/     # Agent communication hub
├── scripts/               
│   ├── examples/          # Example usage scripts
│   ├── setup/             # Setup and configuration
│   ├── testing/           # Test utilities
│   └── utilities/         # Helper tools
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── docs/                  # Documentation
├── config/               # Configuration files
└── archive/              # Archived/old code
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Interactive testing
python scripts/utilities/interactive_test.py

# Full simulation
python scripts/test_pm_agent_end_to_end.py
```

## 🔧 Configuration

### Environment Variables (.env)
```env
ANTHROPIC_API_KEY=your-api-key
PLANKA_BASE_URL=http://localhost:3333
PLANKA_AGENT_EMAIL=demo@demo.demo
PLANKA_AGENT_PASSWORD=demo
```

### Project Configuration (config_pm_agent.json)
```json
{
  "project_id": "your-project-id",
  "board_id": "your-board-id",
  "project_name": "Your Project",
  "auto_find_board": false
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- Kanban board integration via [Planka](https://planka.app/)
- MCP Kanban server by [kanban-mcp](https://github.com/bradrisse/mcp-kanban)

## 🚧 Status

Currently in MVP stage. The system is functional and includes:
- ✅ Complete PM Agent MCP server implementation
- ✅ Full kanban board integration
- ✅ AI-powered task management
- ✅ Worker agent communication
- ✅ Comprehensive test suite
- ✅ Documentation

See [Beyond MVP](docs/beyond-mvp.md) for the roadmap to production.

---

<div align="center">
Built with ❤️ for autonomous development teams
</div>