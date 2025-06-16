# PM Agent - AI Project Manager for Autonomous Development Teams

PM Agent is an AI-powered Project Manager that coordinates autonomous software development teams through kanban board integration. It acts as a central hub, intelligently assigning tasks to AI worker agents based on their skills and managing the entire development workflow.

## 🌟 Key Features

- **Dual MCP Architecture**: Serves as both MCP Server (for worker agents) and MCP Client (for kanban integration)
- **Intelligent Task Assignment**: Matches tasks to workers based on skills, priority, and availability
- **AI-Enhanced Coordination**: Generates detailed task instructions and blocker resolutions using Claude
- **Real-time Progress Tracking**: Updates kanban boards as workers progress through tasks
- **Autonomous Workflow Support**: Enables continuous REQUEST → WORK → REPORT → REQUEST cycles

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Planka instance running (default: http://localhost:3333)
- Anthropic API key

### Installation

1. **Clone and setup**:
   ```bash
   git clone https://github.com/your-repo/pm-agent.git
   cd pm-agent
   ./scripts/setup/setup_environment.sh
   ```

2. **Configure environment**:
   ```bash
   # Edit .env file with your API key
   ANTHROPIC_API_KEY=your-api-key-here
   ```

3. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

### Running PM Agent

1. **Select your project board**:
   ```bash
   python scripts/examples/select_task_master_board.py
   ```

2. **Create test tasks** (optional):
   ```bash
   python scripts/examples/create_todo_app_tasks.py
   ```

3. **Start PM Agent**:
   ```bash
   python start_pm_agent_task_master.py
   ```

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Overview](docs/overview.md) - System overview and concepts
- [Getting Started](docs/getting-started.md) - Detailed setup guide
- [Architecture](docs/architecture.md) - Technical architecture
- [Configuration](docs/configuration.md) - Configuration options
- [API Reference](docs/api-reference.md) - MCP tools documentation
- [Worker Agents](docs/worker-agents.md) - Building compatible agents
- [Troubleshooting](docs/troubleshooting.md) - Common issues

## 🤖 Example Worker Agent

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def worker_loop():
    # Connect to PM Agent
    server_params = StdioServerParameters(
        command="python",
        args=["pm_agent_mvp_fixed.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Register
            await session.call_tool("register_agent", {
                "agent_id": "backend_dev_1",
                "name": "Backend Developer",
                "role": "Backend Developer",
                "skills": ["python", "fastapi", "postgresql"]
            })
            
            # Work loop
            while True:
                # Request task
                task = await session.call_tool("request_next_task", {
                    "agent_id": "backend_dev_1"
                })
                
                if task["has_task"]:
                    # Work on task...
                    # Report progress...
                    # Complete task...
                    pass
                
                await asyncio.sleep(30)
```

## 🏗️ Project Structure

```
pm-agent/
├── src/                    # Core source code
│   ├── core/              # Core models and logic
│   ├── integrations/      # External integrations
│   ├── config/            # Configuration
│   └── enhancements/      # Additional features
├── scripts/               # Utility scripts
│   ├── setup/            # Setup and installation
│   ├── examples/         # Example scripts
│   └── testing/          # Test scripts
├── tests/                 # Test suite
├── docs/                  # Documentation
└── config_pm_agent.json   # Project configuration
```

## 🧪 Testing

Run the test suite:
```bash
# All tests
python run_tests.py

# Unit tests only
python run_tests.py --type unit

# With coverage
python run_tests.py --coverage
```

## 🔧 Configuration

PM Agent can be configured via:
1. `config_pm_agent.json` - Project and board settings
2. Environment variables - Credentials and API keys
3. Command line arguments - Runtime options

See [Configuration Guide](docs/configuration.md) for details.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- Built with [MCP (Model Context Protocol)](https://modelcontextprotocol.io)
- Powered by [Claude](https://anthropic.com)
- Kanban integration via [Planka](https://planka.app)