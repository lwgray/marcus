# Marcus Multi-Agent Demo - Quick Start Guide

## What This Demo Does

Demonstrates Marcus's multi-agent coordination by building a complete **Task Management REST API** with:
- ✅ 15 endpoints (auth, users, projects, tasks, comments)
- ✅ 4 autonomous AI agents working in parallel
- ✅ 20 subagents (5 per agent) for distributed work
- ✅ Real-time MLflow experiment tracking
- ✅ Automated quality validation (80% coverage, 0 mypy errors, 100% API spec compliance)

## Quick Start (3 Steps)

### 1. Start the Demo

```bash
cd examples/multi_agent_demo
./run_demo.sh
```

This spawns:
- **Process 1**: Project creator (creates Marcus project from spec)
- **Process 2**: Foundation Agent (database, models, migrations)
- **Process 3**: Auth Agent (JWT, bcrypt, auth endpoints)
- **Process 4**: API Agent (projects, tasks, comments endpoints)
- **Process 5**: Integration Agent (testing, validation)

Each agent automatically:
- Registers itself + 5 subagents with Marcus
- Selects the project
- Starts MLflow experiment tracking
- Continuously requests and completes tasks
- Commits code with descriptive messages
- Reports progress at 25%, 50%, 75%, 100%

### 2. Monitor Progress (In Separate Terminal)

```bash
# Real-time dashboard
python monitor_agents.py

# Or watch individual logs
tail -f logs/agent_foundation.log
tail -f logs/agent_auth.log
tail -f logs/agent_api.log
tail -f logs/agent_integration.log
```

### 3. Validate Results

```bash
# After agents complete, validate the implementation
python validate_api.py
```

This checks:
- API spec compliance (all 15 endpoints)
- Test coverage (target: 80%+)
- Type safety (target: 0 mypy errors)
- Response format correctness

## Architecture

```
autonomous_agent_spawner.py
├── Process 1: Project Creator
│   └── Uses mcp__marcus__create_project
│
├── Process 2: Foundation Agent (+ 5 subagents)
│   ├── Registers with Marcus
│   ├── Starts experiment tracking
│   └── Works on: Database models, migrations, Pydantic schemas
│
├── Process 3: Auth Agent (+ 5 subagents)
│   └── Works on: JWT tokens, bcrypt, /auth/register, /auth/login
│
├── Process 4: API Agent (+ 5 subagents)
│   └── Works on: Projects CRUD, Tasks CRUD, Comments, pagination
│
└── Process 5: Integration Agent (+ 5 subagents)
    └── Works on: Integration tests, API validation, documentation
```

## What Gets Built

```
implementation/
├── app/
│   ├── main.py              # FastAPI application
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # JWT utilities
│   └── routers/             # API endpoints
│       ├── auth.py          # POST /auth/register, /auth/login
│       ├── users.py         # GET/PUT /users/me
│       ├── projects.py      # CRUD for projects
│       ├── tasks.py         # CRUD + assign for tasks
│       └── comments.py      # Comments on tasks
├── tests/
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_projects.py
│   ├── test_tasks.py
│   └── test_comments.py
├── alembic/                 # Database migrations
└── requirements.txt
```

## Expected Timeline

- **Project Creation**: 30-60 seconds
- **Agent Setup**: 30 seconds (registration + experiment start)
- **Development**: 2-4 hours (4 agents working in parallel)
  - Foundation: ~30-45 minutes (database setup)
  - Auth: ~45-60 minutes (JWT, bcrypt, endpoints)
  - API: ~60-90 minutes (CRUD for projects, tasks, comments)
  - Integration: ~45-60 minutes (tests, validation)

**Total: ~3-4 hours** vs **~8-12 hours single-agent**
**Speedup: 2.5-3x**

## Metrics Tracked (MLflow)

**Parameters:**
- num_agents: 4
- num_subagents: 20
- target_coverage: 80
- target_mypy_errors: 0
- api_endpoints: 15

**Metrics (logged every 30s):**
- Test coverage %
- Mypy error count
- API compliance %
- Endpoints completed
- Build time

**Tags:**
- agent_id, role, project_type, framework

## Viewing Results

### MLflow UI
```bash
cd examples/multi_agent_demo
mlflow ui
# Open http://localhost:5000
```

### Check Implementation
```bash
cd implementation
tree app/
cat app/main.py
pytest --cov
mypy .
```

### Test the API
```bash
# Start the server
cd implementation
uvicorn app.main:app --reload

# In another terminal, test endpoints
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"test","password":"test123"}'  # pragma: allowlist secret
```

## Troubleshooting

**Q: Project creation fails with "No valid session ID"**
A: Ensure Marcus MCP server is running: `ps aux | grep marcus_mcp.server`

**Q: Agents aren't requesting tasks**
A: Check logs in `logs/` directory. Ensure project_info.json was created.

**Q: Claude Code not found**
A: Install Claude Code: https://docs.claude.com/en/docs/claude-code

**Q: How do I stop the demo?**
A: Press Ctrl+C in the terminal running autonomous_agent_spawner.py

## Key Files

- **autonomous_agent_spawner.py** - Spawns all agents
- **monitor_agents.py** - Real-time monitoring dashboard
- **validate_api.py** - Quality validation suite
- **task_management_api_spec.yaml** - OpenAPI specification (source of truth)
- **PROJECT_SPEC.md** - Natural language requirements
- **prompts/Agent_prompt.md** - Agent workflow instructions

## Success Criteria

Demo is successful when:
- ✅ All 15 endpoints implemented
- ✅ 80%+ test coverage
- ✅ 0 mypy errors
- ✅ API validation passes 100%
- ✅ Completed in <50% time of single-agent

## Next Steps

After the demo:
1. Review the generated code in `implementation/`
2. Check MLflow for metrics and timeline
3. Run validation suite to verify quality
4. Try modifying the specification and re-running
5. Experiment with different agent configurations

## Advanced Usage

**Custom agent count:**
Edit `autonomous_agent_spawner.py` and modify `self.agents` list

**Custom subagent count:**
Change `num_subagents` parameter in AgentConfig

**Different specification:**
Edit `PROJECT_SPEC.md` and `task_management_api_spec.yaml`

**Custom project root:**
Modify `project_root` in autonomous_agent_spawner.py

## Support

For issues:
- Check logs in `logs/` directory
- Review Marcus documentation
- Open issue at: https://github.com/anthropics/claude-code/issues
