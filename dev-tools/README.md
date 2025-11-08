# Marcus Development Tools

This directory contains all development, testing, and debugging utilities for the Marcus multi-agent orchestration system.

## Directory Structure

```
dev-tools/
├── experiments/          # Multi-agent experiment framework
├── diagnostics/          # Debugging and analysis tools
├── utilities/            # Maintenance and setup utilities
├── conversation-debugger/ # Web-based debugging UI
└── examples/             # Working code examples
```

## Quick Start

### Running Experiments
Compare single vs multi-agent performance:
```bash
cd dev-tools/experiments
python run_experiment.py --init ~/my-experiment
# Edit config.yaml and project_spec.md
python run_experiment.py ~/my-experiment
```

### Debugging Issues
Analyze project stalls or task issues:
```bash
cd dev-tools/diagnostics
python analyze_stall.py capture          # Capture current state
python diagnose_task_descriptions.py     # Validate task descriptions
python show_ai_input.py                  # View AI context
```

### Monitoring Conversations
Launch the web-based conversation viewer:
```bash
cd dev-tools/conversation-debugger
pip install -r requirements.txt
python app.py
# Open http://localhost:5002
```

### Maintenance Operations
Clean boards or manage projects:
```bash
cd dev-tools/utilities
python clear_board.py                    # Clear Kanban board
python delete_all_projects.py            # Remove all projects
python create_fresh_project.py           # Create test project
```

## Documentation

Each subdirectory contains detailed documentation:

- **[experiments/README.md](experiments/README.md)** - Experiment framework guide
- **[diagnostics/README.md](diagnostics/README.md)** - Diagnostic tools reference
- **[utilities/README.md](utilities/README.md)** - Utility scripts guide
- **[conversation-debugger/README.md](conversation-debugger/README.md)** - Web UI documentation
- **[examples/README.md](examples/README.md)** - Example usage patterns

## Tool Categories

### 🧪 Experiments
**Purpose**: Scientific comparison of agent configurations

**Use when**:
- Testing single vs multi-agent performance
- Optimizing agent count for project complexity
- Generating quality metrics (coverage, type safety)
- Running hypothesis tests

**Key tools**:
- `run_experiment.py` - Main experiment launcher
- `test_optimal_agents.py` - Find optimal agent count
- `score_project.py` - Evaluate code quality
- `compare_scores.py` - Compare experiment results

### 🔍 Diagnostics
**Purpose**: Debug issues and understand system behavior

**Use when**:
- Projects stall or agents stop making progress
- Task descriptions seem problematic
- Need to understand AI reasoning
- Investigating task dependencies

**Key tools**:
- `analyze_stall.py` - Capture and replay stalls
- `diagnose_task_descriptions.py` - Validate tasks
- `show_ai_input.py` - View AI context
- `preview_project_plan.py` - Preview structure

### 🛠️ Utilities
**Purpose**: Maintenance and project management

**Use when**:
- Need to reset board state
- Creating test projects
- Cleaning up after experiments
- Running setup scripts

**Key tools**:
- `clear_board.py` - Clean Kanban boards
- `delete_all_projects.py` - Remove projects
- `create_fresh_project.py` - Generate test projects
- `setup_marcus_project.sh` - Initial setup

### 🖥️ Conversation Debugger
**Purpose**: Real-time conversation monitoring

**Use when**:
- Need to see agent communications live
- Debugging multi-agent coordination
- Analyzing decision-making patterns
- Filtering by project/worker/time

**Features**:
- Auto-refresh every 5 seconds
- Smart filtering (project, worker, type, time)
- Expandable conversation details
- Live statistics dashboard

### 📚 Examples
**Purpose**: Reference implementations

**Use when**:
- Learning Marcus API patterns
- Understanding agent workflows
- Testing connection methods
- Implementing new features

**Available examples**:
- `autonomous_agent_workflow.py` - Full agent lifecycle
- `agent_select_project.py` - Project selection pattern
- `task_decomposition_demo.py` - Task breakdown
- `inspector_demo.py` - Inspector tool usage
- `demo_http_connection.py` - HTTP transport
- `demo_stdio_connection.py` - Stdio transport

## Common Workflows

### Workflow 1: Run New Experiment
```bash
# 1. Initialize experiment
cd dev-tools/experiments
python run_experiment.py --init ~/experiments/my-project

# 2. Configure (edit files)
cd ~/experiments/my-project
vim config.yaml          # Define agents
vim project_spec.md      # Define requirements

# 3. Test optimal configuration
cd /Users/lwgray/dev/marcus/dev-tools/experiments
python test_optimal_agents.py ~/experiments/my-project

# 4. Run experiment
python run_experiment.py ~/experiments/my-project

# 5. Analyze results
python score_project.py ~/experiments/my-project/implementation
python compare_scores.py --report results.json
```

### Workflow 2: Debug Stalled Project
```bash
# 1. Capture current state
cd dev-tools/diagnostics
python analyze_stall.py capture

# 2. Check task descriptions
python diagnose_task_descriptions.py

# 3. View AI context
python show_ai_input.py

# 4. Monitor conversations
cd ../conversation-debugger
python app.py
# Open http://localhost:5002 and filter by your project

# 5. Replay stall scenario
cd ../diagnostics
python analyze_stall.py replay <snapshot_file>
```

### Workflow 3: Clean Slate Testing
```bash
# 1. Clear everything
cd dev-tools/utilities
python delete_all_projects.py
python clear_board.py

# 2. Create fresh test project
python create_fresh_project.py

# 3. Verify setup
cd ../diagnostics
python preview_project_plan.py
```

## Development Guidelines

### Adding New Tools

**Experiments**: Add to `dev-tools/experiments/`
- Must integrate with MLflow tracking
- Follow existing config.yaml patterns
- Document in experiments/README.md

**Diagnostics**: Add to `dev-tools/diagnostics/`
- Must be read-only (no destructive operations)
- Support snapshot/replay where applicable
- Document in diagnostics/README.md

**Utilities**: Add to `dev-tools/utilities/`
- Provide --dry-run flag for destructive operations
- Include clear confirmation prompts
- Document in utilities/README.md

### Tool Design Principles

1. **Single Responsibility**: Each tool does one thing well
2. **Composability**: Tools can be chained together
3. **Safety**: Destructive operations require confirmation
4. **Documentation**: Self-documenting with --help flags
5. **Consistency**: Follow existing CLI patterns

## Requirements

Most tools require:
- Python 3.8+
- Marcus MCP server running
- Claude Code CLI installed

Specific requirements listed in each subdirectory's README.

## Troubleshooting

### Tools Can't Find Marcus
**Issue**: ImportError or connection errors

**Solution**:
```bash
# Ensure Marcus is in PYTHONPATH
export PYTHONPATH="/Users/lwgray/dev/marcus:$PYTHONPATH"

# Or run from Marcus root
cd /Users/lwgray/dev/marcus
python dev-tools/experiments/run_experiment.py
```

### Experiment Fails to Launch Agents
**Issue**: Agents don't spawn or terminate immediately

**Solution**:
1. Check Marcus MCP server is running
2. Verify Claude Code CLI: `claude --version`
3. Check logs in experiment directory: `logs/*.log`
4. Ensure config.yaml has valid settings

### Conversation Debugger Shows No Data
**Issue**: Web UI loads but no conversations appear

**Solution**:
1. Check logs exist: `ls logs/conversations/`
2. Verify JSONL format: `cat logs/conversations/conversations_*.jsonl | head`
3. Check time filter isn't too restrictive
4. Ensure Marcus is generating conversation logs

### Stall Analyzer Finds Nothing
**Issue**: No stalls detected when project seems stuck

**Solution**:
1. Verify board has tasks: Check Kanban board directly
2. Check agent logs: `ls logs/agents/`
3. Use conversation debugger to see last activity
4. Run diagnose_task_descriptions.py to check task quality

## Contributing

When adding new dev tools:
1. Place in appropriate subdirectory
2. Add executable permissions if needed: `chmod +x script.py`
3. Update subdirectory README.md
4. Add to this master README if it's a major tool
5. Follow existing patterns for CLI arguments
6. Include docstrings and type hints

## Support

For issues with dev tools:
- Check subdirectory READMEs for detailed docs
- Review logs in respective output directories
- Ensure all prerequisites are installed
- Verify Marcus MCP server is operational

For Marcus core issues:
- See main project README.md
- Check Marcus documentation
- Review MCP server logs
