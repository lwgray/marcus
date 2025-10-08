# Marcus Multi-Agent Experiments

A portable framework for running multi-agent software development experiments with Marcus task orchestration.

## Overview

This framework allows you to run Marcus multi-agent experiments anywhere on your system. Agents work collaboratively on the `main` branch, coordinated by Marcus to prevent conflicts, with full MLflow experiment tracking support.

### Key Features

- **Portable**: Run experiments anywhere, not tied to the Marcus repo
- **Configurable**: Define custom agents with specific skills and subagent counts
- **Flexible**: Support for any project type and tech stack
- **Tracked**: Full MLflow integration for experiment monitoring
- **Collaborative**: All agents work on main branch with Marcus coordination

## Prerequisites

- Marcus MCP server running
- Claude Code CLI installed (`claude` command)
- Python 3.8+ with PyYAML installed
- macOS (uses Terminal.app for agent windows)

## Quick Start

### 1. Create a New Experiment

```bash
cd /Users/lwgray/dev/marcus/experiments
python run_experiment.py --init ~/my-experiments/podcast-generator
```

This creates:
```
~/my-experiments/podcast-generator/
├── config.yaml          # Agent configuration
├── project_spec.md      # What to build
├── prompts/             # Auto-generated prompts
├── logs/                # Agent logs
└── implementation/      # Code output (git repo)
```

### 2. Configure Your Experiment

Edit `config.yaml` to define your agents:

```yaml
project_name: "Podcast Generator"

project_spec_file: "project_spec.md"

project_options:
  complexity: "standard"
  provider: "planka"

agents:
  - id: "agent_backend"
    name: "Backend Developer"
    role: "backend"
    skills: ["python", "fastapi", "postgresql"]
    subagents: 5

  - id: "agent_frontend"
    name: "Frontend Developer"
    role: "frontend"
    skills: ["react", "typescript", "tailwind"]
    subagents: 3
```

Edit `project_spec.md` to describe what you want built:

```markdown
# Podcast Generator

## Overview
Build a web app that generates podcast scripts using AI...

## Features
- Script generation
- Audio synthesis
- Episode management

## Technical Stack
- Backend: FastAPI
- Frontend: React + TypeScript
- Database: PostgreSQL
```

### 3. Run the Experiment

```bash
python run_experiment.py ~/my-experiments/podcast-generator
```

This will:
1. Open 1 terminal for project creation
2. Open N terminals for your agents (one per agent in config)
3. Each agent registers itself + subagents with Marcus
4. Agents request tasks, complete them, and request more
5. All work committed to `main` branch in `implementation/`

### 4. Monitor Progress

Watch the terminal windows to see:
- Project creation and task breakdown
- Agents registering and requesting tasks
- Code commits and progress reports
- Task completion and handoffs

Results appear in `~/my-experiments/podcast-generator/implementation/`

## Directory Structure

```
marcus/
└── experiments/                    # Framework (in repo)
    ├── run_experiment.py           # Main launcher
    ├── spawn_agents.py             # Agent spawner
    ├── templates/
    │   ├── config.yaml.template    # Config template
    │   └── agent_prompt.md         # Agent behavior
    ├── examples/
    │   └── task_management_api.yaml  # Example config
    └── README.md                   # This file

~/my-experiments/                   # Experiments (outside repo)
├── podcast-generator/
│   ├── config.yaml
│   ├── project_spec.md
│   ├── implementation/             # Git repo on main
│   │   ├── src/
│   │   ├── tests/
│   │   └── ...
│   ├── prompts/                    # Generated
│   └── logs/                       # Agent logs
└── ecommerce-platform/
    └── ...
```

## Configuration Reference

### config.yaml

```yaml
# Project settings
project_name: "Your Project Name"
project_spec_file: "project_spec.md"  # Relative to experiment dir

# Marcus project options
project_options:
  complexity: "standard"    # prototype | standard | enterprise
  provider: "planka"        # planka | github | linear
  mode: "new_project"       # new_project | auto | select_project

# Agent definitions
agents:
  - id: "unique_agent_id"
    name: "Human Readable Name"
    role: "backend"         # backend | frontend | qa | devops | fullstack
    skills:
      - "python"
      - "fastapi"
      - "postgresql"
    subagents: 5            # Number of subagents to spawn

# Optional timeouts
timeouts:
  project_creation: 300     # Seconds (default: 300)
  agent_startup: 60         # Seconds (default: 60)
```

### Agent Skills

Common skill tags by role:

**Backend:**
- Languages: `python`, `javascript`, `typescript`, `go`, `rust`, `java`
- Frameworks: `fastapi`, `django`, `express`, `spring`, `actix`
- Databases: `postgresql`, `mysql`, `mongodb`, `redis`
- ORM/DB Tools: `sqlalchemy`, `prisma`, `sequelize`, `alembic`

**Frontend:**
- Languages: `javascript`, `typescript`
- Frameworks: `react`, `vue`, `angular`, `svelte`, `nextjs`
- Styling: `tailwind`, `css`, `sass`, `styled-components`
- State: `redux`, `zustand`, `react-query`

**QA/Testing:**
- Testing: `pytest`, `jest`, `cypress`, `selenium`
- Types: `unit-testing`, `integration-testing`, `e2e-testing`
- Tools: `coverage`, `api-testing`, `validation`

**DevOps:**
- Containers: `docker`, `kubernetes`
- CI/CD: `github-actions`, `gitlab-ci`, `jenkins`
- Cloud: `aws`, `gcp`, `azure`
- IaC: `terraform`, `ansible`

## How It Works

### 1. Project Creation
The launcher spawns a project creator agent that:
- Calls `mcp__marcus__create_project` with your spec
- Creates tasks and dependencies in Marcus/Planka
- Saves project info for workers

### 2. Agent Registration
Each worker agent:
- Reads project info
- Registers itself with Marcus
- Registers N subagents (configurable per agent)
- Enters continuous work loop

### 3. Task Assignment
Agents continuously:
- Request tasks from Marcus (`request_next_task`)
- Marcus assigns based on skills and dependencies
- Agent checks dependencies via `get_task_context`
- Agent completes task and reports progress
- Commits to `main` branch
- Immediately requests next task

### 4. Coordination
- **No branches**: All agents work on `main`
- **Marcus coordinates**: Assigns tasks to prevent conflicts
- **Dependency tracking**: Agents see what others built
- **Artifacts**: Agents share specs/docs via `log_artifact`
- **Decisions**: Architectural choices logged via `log_decision`

## Example Experiments

### Task Management API

A full REST API with auth, users, projects, tasks, and comments.

```bash
# Copy the example config
cp examples/task_management_api.yaml ~/experiments/task-api/config.yaml

# Copy the spec from the old demo
cp ../examples/multi_agent_demo/PROJECT_SPEC.md ~/experiments/task-api/project_spec.md

# Run it
python run_experiment.py ~/experiments/task-api
```

Agents: 4 agents, 13 subagents total
- Foundation: Database models, migrations (5 subagents)
- Auth: JWT, bcrypt, auth endpoints (3 subagents)
- API: CRUD endpoints for projects/tasks (3 subagents)
- Integration: End-to-end tests, validation (2 subagents)

### Custom Experiment Ideas

**E-commerce Platform:**
```yaml
agents:
  - {id: agent_backend, role: backend, skills: [python, fastapi, stripe], subagents: 5}
  - {id: agent_frontend, role: frontend, skills: [react, typescript, tailwind], subagents: 4}
  - {id: agent_devops, role: devops, skills: [docker, aws, terraform], subagents: 2}
```

**Data Pipeline:**
```yaml
agents:
  - {id: agent_etl, role: backend, skills: [python, pandas, airflow], subagents: 4}
  - {id: agent_ml, role: backend, skills: [python, scikit-learn, mlflow], subagents: 3}
  - {id: agent_api, role: backend, skills: [python, fastapi, redis], subagents: 2}
```

**Mobile App Backend:**
```yaml
agents:
  - {id: agent_api, role: backend, skills: [node, express, mongodb], subagents: 4}
  - {id: agent_realtime, role: backend, skills: [node, socket-io, redis], subagents: 2}
  - {id: agent_push, role: backend, skills: [node, firebase, apns], subagents: 2}
```

## MLflow Integration

Marcus maintains full MLflow tracking for experiments. All agent actions, task completion, and progress are automatically tracked.

To view experiment metrics:
```bash
# MLflow UI (if you have MLflow server running)
mlflow ui

# Or check Marcus MCP experiment status
# (via your Claude Code session)
mcp__marcus__get_experiment_status()
```

## Commands Reference

```bash
# Initialize new experiment
python run_experiment.py --init <experiment_dir>

# Validate experiment config
python run_experiment.py --validate <experiment_dir>

# Run experiment
python run_experiment.py <experiment_dir>

# Direct spawner usage (advanced)
python spawn_agents.py <experiment_dir>
```

## Troubleshooting

### "Marcus MCP server not running"
```bash
# Start Marcus server
cd /Users/lwgray/dev/marcus
./marcus start
```

### "No suitable tasks" loops
- Agents waiting for dependencies to complete
- Check terminal windows - other agents may be working
- Marcus assigns tasks as dependencies are satisfied

### Merge conflicts on main
- Rare - Marcus coordinates to prevent this
- If it happens: manually resolve and commit
- Agents will continue from resolved state

### Agent stuck/not progressing
- Check the agent's terminal window for errors
- Look in `experiment_dir/logs/` for detailed logs
- Use `mcp__marcus__diagnose_project` to check for gridlock

## Best Practices

### Agent Configuration
- **3-5 agents** optimal for most projects
- **2-5 subagents** per agent
- Match skills to your tech stack
- Specialized roles reduce conflicts

### Project Specs
- Be specific about technical requirements
- List concrete deliverables
- Include API contracts or schemas
- Mention testing requirements (coverage, etc.)

### Monitoring
- Keep terminal windows visible
- Watch for agent errors or blockers
- Check implementation/ directory for code
- Review commits for progress

### Cleanup
- Each experiment is self-contained
- Delete experiment directory when done
- Keep successful experiments as templates

## Advanced Usage

### Custom Templates

Create your own agent prompt template:
```bash
cp templates/agent_prompt.md my_custom_prompt.md
# Edit to customize agent behavior
```

Modify `spawn_agents.py` to use your template.

### Multiple Experiments

Run multiple experiments simultaneously:
```bash
# Terminal 1
python run_experiment.py ~/experiments/project-a

# Terminal 2
python run_experiment.py ~/experiments/project-b
```

Each has isolated agents, tasks, and implementation directories.

### Reusing Configurations

Save successful configs as templates:
```bash
cp ~/experiments/successful-api/config.yaml examples/my_api_template.yaml
```

Share with team or reuse for similar projects.

## Contributing

This framework is part of the Marcus project. Improvements welcome:

1. Better agent coordination strategies
2. Additional tech stack examples
3. Progress visualization tools
4. Experiment comparison analytics

## License

Part of the Marcus Multi-Agent System.
