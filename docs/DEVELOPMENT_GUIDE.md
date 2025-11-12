# Marcus Development Guide

**Version**: 1.0
**Last Updated**: 2025-11-11
**Audience**: Junior engineers and new contributors
**Purpose**: Step-by-step guide for building Marcus from foundation to production

**⚠️ CRITICAL**: Read [MVP_CATO_ALIGNMENT_EVALUATION.md](MVP_CATO_ALIGNMENT_EVALUATION.md) first to understand MVP→CATO alignment and required Week 5.5 addition.

---

## Table of Contents

1. [What is Marcus?](#what-is-marcus)
2. [What You'll Build](#what-youll-build)
3. [Architecture Overview](#architecture-overview)
4. [Prerequisites](#prerequisites)
5. [Development Roadmap](#development-roadmap)
6. [Phase 1: MVP Foundation (Weeks 1-6 + Week 5.5)](#phase-1-mvp-foundation-weeks-1-6--week-55)
7. [Phase 2: Cato Bundling (Weeks 8-11)](#phase-2-cato-bundling-weeks-8-11)
8. [Phase 3: Web Console (Development Tool)](#phase-3-web-console-development-tool)
9. [Phase 4: Advanced Features (Weeks 12+)](#phase-4-advanced-features-weeks-12)
10. [Documentation Index](#documentation-index)
11. [Verification & Testing](#verification--testing)
12. [Getting Help](#getting-help)

---

## What is Marcus?

**Marcus** (Multi-Agent Resource Coordination and Understanding System) is an orchestration system that coordinates multiple AI coding agents to work together on software projects.

### The Problem Marcus Solves

When building software with AI agents:
- **Agents need task coordination** - Who works on what? What order?
- **Agents need context** - What has been done? What decisions were made?
- **Agents need isolation** - How to work in parallel without conflicts?
- **Users need visibility** - What's happening? How's progress?

Marcus provides:
✅ Task orchestration with dependency management
✅ Workspace isolation (git worktrees for parallel work)
✅ Feature context aggregation (automatic context from commits/artifacts/decisions)
✅ Real-time visualization (unified dashboard)
✅ BYOA architecture (Bring Your Own Agent - agents voluntarily pull work)

---

## What You'll Build

By following this guide, you will build a complete multi-agent orchestration system:

```
End State: Marcus v1.0
    ├── Core Orchestration (MVP - Weeks 1-6)
    │   ├── Configuration system
    │   ├── Workspace isolation (git worktrees)
    │   ├── Feature context aggregation
    │   ├── Telemetry & event broadcasting
    │   └── Production validations
    │
    ├── Unified Dashboard (Weeks 8-11)
    │   ├── Git submodule integration (Cato)
    │   ├── Single installation (pip install marcus)
    │   ├── Single startup (marcus start)
    │   └── 6-tab dashboard (Launch, Terminals, Kanban, Live, Historical, Global)
    │
    └── Development Tools (Optional)
        └── Web Console (experiment dashboard with terminal monitoring)
```

**Timeline**: 11 weeks (MVP) + 2 weeks (Web Console) = **13 weeks total**

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Marcus v1.0 System                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Unified Dashboard (Cato)                  │   │
│  │  🚀 Launch | 💻 Terminals | 📋 Kanban | 📊 Live     │   │
│  │            📚 Historical | 🌍 Global                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↕                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Marcus MCP Server (Port 4298)             │   │
│  │  • Agent registration                                │   │
│  │  • Task assignment                                   │   │
│  │  • Context building                                  │   │
│  │  • Event broadcasting                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↕                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Workspace Manager (Git Worktrees)           │   │
│  │  • Feature branch creation                           │   │
│  │  • Worktree isolation                                │   │
│  │  • Conflict prevention                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↕                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │     AI Agents (Claude, Cursor, Amp, etc.)           │   │
│  │  • Pull tasks via MCP                                │   │
│  │  • Work in isolated workspaces                       │   │
│  │  • Report progress & artifacts                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Marcus MCP Server** - Core orchestration engine
   - Manages tasks, projects, features
   - Provides MCP tools for agents
   - Tracks history and context

2. **Workspace Manager** - Git worktree isolation
   - Creates isolated workspaces for parallel work
   - Manages feature branches
   - Prevents conflicts

3. **Feature Context Builder** - Automatic context aggregation
   - Tracks commits by feature/task
   - Aggregates artifacts and decisions
   - Provides rich context for agents

4. **Cato Dashboard** - Real-time visualization
   - Live network graph (agents, tasks, dependencies)
   - Historical analysis
   - Global insights

5. **Web Console** (Optional) - Development tool
   - Multi-agent terminal monitoring
   - Health checks and auto-recovery
   - Experiment dashboard

---

## Prerequisites

### Required Skills

- **Python 3.11+** - Intermediate level
- **Git** - Basic branching, worktrees
- **FastAPI** - Basic API development
- **React/TypeScript** - For dashboard work (Weeks 8-11)
- **Testing** - pytest, TDD mindset

### Required Tools

```bash
# Python environment
python --version  # Must be 3.11+
conda --version   # Or virtualenv

# Git
git --version

# Node.js (for Cato dashboard)
node --version    # Must be 18+
npm --version

# Docker (for Week 6)
docker --version
docker-compose --version
```

### Optional Tools

```bash
# Kanban board (choose one)
# - Planka (recommended for local dev)
# - GitHub Projects
# - Linear

# AI coding tools (for testing)
claude --version   # Claude Code CLI
cursor --version   # Cursor CLI
```

### Clone the Repository

```bash
# Clone Marcus
git clone https://github.com/yourusername/marcus.git
cd marcus

# Checkout develop branch (all work happens here)
git checkout develop

# Create your feature branch
git checkout -b feature/your-name/implementation

# Install Marcus in development mode
pip install -e .
```

---

## Development Roadmap

### Overview

```
Weeks 1-6:   MVP Foundation (Core Marcus features)
Weeks 8-11:  Cato Bundling (Unified dashboard)
Weeks 12-13: Web Console (Development tool - OPTIONAL)
Weeks 14+:   Advanced Features (Progressive feedback, UX improvements)

Note: Reserve buffer time after Week 6 for integration testing before Week 8
```

### Timeline

| Phase | Duration | What You Build | Status |
|-------|----------|----------------|--------|
| **Week 1** | 5 days | Configuration system | ⏳ Not started |
| **Week 2** | 5 days | Feature entity & infrastructure | ⏳ Not started |
| **Week 3** | 5 days | Git worktree workspace isolation | ⏳ Not started |
| **Week 4** | 5 days | Feature context aggregation | ⏳ Not started |
| **Week 5** | 5 days | Telemetry & CATO API integration | ⏳ Not started |
| **Week 6** | 5 days | Production validations & Docker | ⏳ Not started |
| **Week 8** | 5 days | Git submodule setup | ⏳ Not started |
| **Week 9** | 5 days | Unified installation | ⏳ Not started |
| **Week 10** | 5 days | Unified startup command | ⏳ Not started |
| **Week 11** | 5 days | Unified dashboard UI | ⏳ Not started |
| **Week 12-13** | 10 days | Web Console (OPTIONAL) | ⏳ Not started |

---

## Phase 1: MVP Foundation (Weeks 1-6 + Week 5.5)

### Overview

**Goal**: Build the core Marcus orchestration system that coordinates AI agents.

**What You'll Build**:
- Type-safe configuration system
- Feature entity for grouping tasks
- Git worktree-based workspace isolation
- Automatic feature context building
- Telemetry and event broadcasting
- REST APIs for Launch Tab (agents, projects, tasks)
- Terminal streaming infrastructure (PTY + SSE)
- Production validations
- Pip packaging

**Status**: ⏳ **NOT STARTED** (ready to begin)

**⚠️ CRITICAL UPDATE REQUIRED**: After completing this evaluation, **Week 5.5 (REST API Completion)** must be added between Week 5 and Week 6. See [MVP_CATO_ALIGNMENT_EVALUATION.md](MVP_CATO_ALIGNMENT_EVALUATION.md) for details.

**Missing Components Identified**:
- Launch tab REST APIs (`/api/agents`, `/api/projects`, `/api/tasks`)
- Terminal streaming API (`/api/agents/{agent_id}/terminal/stream`)
- These are CRITICAL for CATO bundling (Weeks 8-11) to function

**Recommendation**: Plan for **Week 5.5 (2-3 days)** before starting Week 6.

---

### Step 1: Week 1 - Configuration System

#### What You're Building

A centralized, type-safe configuration system that consolidates all Marcus settings into one place.

**Why This Matters**: Currently, configuration is scattered across multiple files. This makes deployment difficult and error-prone. A centralized config system enables:
- Easy deployment (single config file)
- Clear validation errors
- Environment variable overrides for production

#### Documentation

📄 **Plan**: `docs/implementation/WEEK_1_PLAN.md`

#### Key Deliverables

```python
# src/config/marcus_config.py - Type-safe configuration
@dataclass
class MarcusConfig:
    mcp: MCPSettings
    ai: AISettings
    kanban: KanbanSettings
    features: FeaturesSettings
    # ... other settings
```

- `config_marcus.example.json` - Template for users
- Validation framework with clear error messages
- Environment variable override support
- Migration of existing code to use new config

#### What to Do

```bash
# 1. Read the week plan
cat docs/implementation/WEEK_1_PLAN.md

# 2. Follow day-by-day instructions:
#    Monday: Create configuration data structure
#    Tuesday: Add validation & environment overrides
#    Wednesday: Migrate existing code
#    Thursday: Create config_marcus.example.json
#    Friday: Testing, documentation & backward compatibility

# 3. Verify completion
python -c "from src.config.marcus_config import MarcusConfig; print('Week 1: ✓')"
pytest tests/unit/config/ -v --cov=src.config
```

#### Success Criteria

✅ `src/config/marcus_config.py` exists with type-safe dataclasses
✅ `config_marcus.example.json` template created
✅ All tests pass: `pytest tests/unit/config/ -v`
✅ Validation errors are clear and actionable
✅ Environment variables override config file settings

#### Related Issue

🔗 [Issue #68: Configuration Centralization](https://github.com/yourusername/marcus/issues/68)

---

### Step 2: Week 2 - Feature Entity & Infrastructure

#### What You're Building

Add a "Feature" entity that groups related tasks together, and extend artifact/decision logging to track by feature.

**Why This Matters**: Projects are too large to visualize as one unit. Features (like "user authentication" or "payment processing") are the right level of granularity for:
- Context building (what's the state of this feature?)
- Workspace isolation (each feature gets its own worktree)
- Progress tracking (how's this feature coming along?)

#### Documentation

📄 **Plan**: `docs/implementation/WEEK_2_PLAN.md`

#### Key Deliverables

```python
# src/core/models.py - Feature dataclass
@dataclass
class Feature:
    feature_id: str
    feature_name: str
    project_id: str
    design_task_id: Optional[str]
    feature_branch: str
    status: str
    created_at: datetime
    task_ids: list[str]
```

- Feature entity dataclass
- Extended artifact logging with `feature_id`
- Extended decision logging with `feature_id`
- Feature indexing system
- WorkspaceManager skeleton

#### What to Do

```bash
# 1. Read the week plan
cat docs/implementation/WEEK_2_PLAN.md

# 2. Follow day-by-day instructions:
#    Monday: Add Project and Feature entities
#    Tuesday: Extend artifact and decision logging with feature_id
#    Wednesday: Artifact and decision indexing by feature
#    Thursday: Create WorkspaceManager skeleton
#    Friday: Week 2 integration & testing

# 3. Verify completion
python -c "from src.core.models import Feature; print('Week 2: ✓')"
pytest tests/unit/core/ -v
```

#### Success Criteria

✅ `Feature` dataclass exists in `src/core/models.py`
✅ Artifact logging includes `feature_id` parameter
✅ Decision logging includes `feature_id` parameter
✅ Feature indexing system works
✅ `WorkspaceManager` skeleton created
✅ All tests pass: `pytest tests/unit/core/ -v`

---

### Step 3: Week 3 - Git Worktree Workspace Isolation

#### What You're Building

Full implementation of WorkspaceManager using git worktrees for parallel task execution.

**Why This Matters**: Multiple agents working on the same codebase will conflict (file locks, merge conflicts). Git worktrees solve this by:
- Creating isolated working directories for each task
- Sharing the same .git directory (efficient)
- Allowing parallel work without conflicts
- Automatic cleanup after task completion

#### Documentation

📄 **Plan**: `docs/implementation/WEEK_3_PLAN.md`

#### Key Deliverables

```python
# src/workspace/manager.py - Full WorkspaceManager
class WorkspaceManager:
    async def create_workspace(self, task: Task, feature_branch: str) -> WorkspaceInfo:
        """Create isolated workspace using git worktrees."""
        # Creates git worktree at .marcus/worktrees/{task_id}/
```

- GitOperations class for feature branch management
- Full WorkspaceManager with worktree creation/cleanup
- Integration with `request_next_task` MCP tool
- Automatic workspace cleanup on task completion

#### What to Do

```bash
# 1. Read the week plan
cat docs/implementation/WEEK_3_PLAN.md

# 2. Follow day-by-day instructions:
#    Monday: Implement git worktree creation
#    Tuesday: Implement workspace cleanup
#    Wednesday: Integrate with task assignment
#    Thursday: Add workspace conflict detection
#    Friday: Week 3 testing & documentation

# 3. Verify completion
python -c "from src.workspace.manager import WorkspaceManager; print('Week 3: ✓')"
pytest tests/unit/workspace/ -v
```

#### Success Criteria

✅ `WorkspaceManager.create_workspace()` creates git worktrees
✅ `WorkspaceManager.cleanup_workspace()` removes worktrees
✅ Integration with `request_next_task` works
✅ Conflict detection prevents double-assignment
✅ All tests pass: `pytest tests/unit/workspace/ -v`

---

### Step 4: Week 4 - Feature Context Aggregation

#### What You're Building

Automatic context building that aggregates everything about a feature: commits, artifacts, decisions, and task history.

**Why This Matters**: Agents need rich context to work effectively. When an agent picks up a task, they should know:
- What's been done so far?
- What decisions were made?
- What files were changed?
- What artifacts exist?

The FeatureContextBuilder automatically aggregates this from git commits, artifact logs, and decision logs.

#### Documentation

📄 **Plan**: `docs/implementation/WEEK_4_PLAN.md`

#### Key Deliverables

```python
# src/context/feature_builder.py - FeatureContextBuilder
class FeatureContextBuilder:
    def build_feature_context(self, feature_id: str, ...) -> FeatureContext:
        """Build complete context for a feature from artifacts, decisions, commits."""
```

- `CommitTracker` for tracking commits by feature/task
- `FeatureContextBuilder` for aggregating feature data
- `get_feature_context` MCP tool
- `get_feature_status` MCP tool
- Integration with task assignment (automatic context injection)

#### What to Do

```bash
# 1. Read the week plan
cat docs/implementation/WEEK_4_PLAN.md

# 2. Follow day-by-day instructions:
#    Monday: Create FeatureContextBuilder
#    Tuesday: Implement git commit tracking
#    Wednesday: Implement context injection
#    Thursday: Add get_feature_context MCP tool
#    Friday: Add get_feature_status tool & testing

# 3. Verify completion
python -c "from src.context.feature_builder import FeatureContextBuilder; print('Week 4: ✓')"
pytest tests/unit/context/ -v
```

#### Success Criteria

✅ `CommitTracker` tracks commits by feature/task
✅ `FeatureContextBuilder.build_feature_context()` aggregates all data
✅ `get_feature_context` MCP tool works
✅ `get_feature_status` MCP tool works
✅ Context automatically injected into task assignments
✅ All tests pass: `pytest tests/unit/context/ -v`

---

### Step 5: Week 5 - Telemetry & CATO API Integration

#### What You're Building

Telemetry system for user journey tracking and research events, plus API endpoints for the Cato dashboard.

**Why This Matters**:
- **Research**: Track agent behavior for MAS (Multi-Agent System) research
- **Observability**: See what agents are doing in real-time
- **Visualization**: Provide data for the Cato dashboard

#### Documentation

📄 **Plan**: `docs/implementation/WEEK_5_PLAN.md`

#### Key Deliverables

```python
# src/telemetry/journey_tracker.py - User journey tracking
class UserJourneyTracker:
    def log_milestone(self, milestone: str, metadata: dict) -> None:
        """Log user journey milestone."""

# API endpoints for Cato
# /api/cato/snapshot - Get current project state
# /api/cato/events/stream - SSE stream for real-time events
```

- User journey tracking system
- Research event logging
- CATO dashboard integration API (`/api/cato/...`)
- Real-time event broadcasting with SSE (Server-Sent Events)

#### What to Do

```bash
# 1. Read the week plan
cat docs/implementation/WEEK_5_PLAN.md

# 2. Follow day-by-day instructions:
#    Monday: User journey tracking
#    Tuesday: Research event logging
#    Wednesday: CATO dashboard integration API
#    Thursday: Real-time event broadcasting
#    Friday: Week 5 testing & documentation

# 3. Verify completion
curl http://localhost:4301/api/cato/snapshot && echo "Week 5: ✓"
pytest tests/unit/telemetry/ -v
```

#### Success Criteria

✅ User journey tracking logs milestones
✅ Research events captured with structured data
✅ `/api/cato/snapshot` returns project state
✅ `/api/cato/events/stream` broadcasts real-time events
✅ All tests pass: `pytest tests/unit/telemetry/ -v`

---

### Step 5.5: Week 5.5 - REST API Completion [CRITICAL]

#### What You're Building

REST API endpoints for the Launch Tab and terminal streaming infrastructure for the Terminals Tab.

**Why This Matters**: Week 5 implemented `/api/cato/*` endpoints for Live/Historical tabs, but Launch and Terminals tabs need different APIs:
- **Launch Tab** needs REST endpoints for agent registration, project creation, task management
- **Terminals Tab** needs real-time terminal output streaming via PTY sessions
- Without these, **CATO bundling (Weeks 8-11) will have non-functional tabs**

#### Documentation

📄 **Plan**: `docs/implementation/WEEK_5.5_PLAN.md`

#### Key Deliverables

```python
# src/api/marcus_routes.py - Launch Tab REST APIs
@router.post("/api/agents")
async def register_agent_rest(request: RegisterAgentRequest):
    """Register a new agent (REST wrapper for MCP tool)."""

@router.get("/api/agents")
async def list_agents():
    """List all registered agents."""

@router.post("/api/projects")
async def create_project_rest(request: CreateProjectRequest):
    """Create a new project from natural language."""

# src/terminal/manager.py - Terminal streaming
class TerminalManager:
    async def create_terminal(self, agent_id: str) -> TerminalSession:
        """Create PTY session for agent."""

    async def get_output(self, agent_id: str) -> list[dict]:
        """Get buffered output from agent terminal."""

# src/api/terminal_routes.py - Terminal streaming API
@router.get("/api/agents/{agent_id}/terminal/stream")
async def stream_agent_terminal(agent_id: str) -> StreamingResponse:
    """Stream agent terminal output via Server-Sent Events."""
```

- Launch Tab REST APIs (`POST /api/agents`, `GET /api/agents`, `POST /api/projects`, `GET /api/projects`, `POST /api/tasks`, `GET /api/tasks`)
- Terminal streaming infrastructure (TerminalManager with PTY sessions)
- Terminal streaming API (`GET /api/agents/{agent_id}/terminal/stream`, `POST /api/agents/{agent_id}/terminal/input`)
- Command injection support for agent recovery

#### What to Do

```bash
# 1. Read the week plan
cat docs/implementation/WEEK_5.5_PLAN.md

# 2. Follow day-by-day instructions:
#    Day 1: Launch Tab REST APIs (marcus_routes.py)
#    Day 2-3: Terminal streaming infrastructure (manager.py + terminal_routes.py)

# 3. Verify completion
curl http://localhost:4301/api/agents && echo "Launch APIs: ✓"
curl http://localhost:4301/api/agents/test-agent/terminal/stream && echo "Terminal streaming: ✓"
pytest tests/unit/api/test_marcus_routes.py -v
pytest tests/unit/terminal/ -v
```

#### Success Criteria

✅ All Launch Tab REST endpoints functional (`/api/agents`, `/api/projects`, `/api/tasks`)
✅ Terminal streaming infrastructure working with PTY sessions
✅ SSE streaming endpoint delivers real-time terminal output
✅ Command injection works for stuck agent recovery
✅ All tests pass: `pytest tests/unit/api/ tests/unit/terminal/ -v`

**⚠️ CRITICAL**: Do NOT skip Week 5.5. Without these APIs, CATO bundling in Weeks 8-11 will be non-functional.

---

### Step 6: Week 6 - Production Validations & Pip Packaging

#### What You're Building

Core validations to prevent runtime errors, pip packaging setup, and comprehensive documentation.

**Why This Matters**: The MVP is feature-complete but not production-ready. Week 6 adds:
- **Validations**: Catch errors before they cause problems (invalid dependencies, circular deps, invalid status transitions)
- **Pip Packaging**: Easy installation with `pip install marcus`
- **Documentation**: Complete user and API documentation

#### Documentation

📄 **Plan**: `docs/implementation/WEEK_6_PLAN.md`

#### Key Deliverables

```python
# src/validation/task_validator.py - Task validation
class TaskValidator:
    def validate_task_dependencies(self, task_id: str, dependencies: List[str]) -> None:
        """Validate that all task dependencies exist."""

    def validate_status_transition(self, task_id: str, current_status: TaskStatus,
                                   new_status: TaskStatus) -> None:
        """Validate task status transition is valid."""
```

```python
# setup.py - Pip packaging configuration
from setuptools import setup, find_packages

setup(
    name="marcus",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        # ... other dependencies
    ],
    entry_points={
        "console_scripts": [
            "marcus=src.cli:main",
        ],
    },
)
```

- 7 core validations (Issues #118-125)
- Pip packaging setup (`setup.py`, `pyproject.toml`)
- CLI entry point (`marcus start`)
- Comprehensive documentation
- Final testing and bug fixes

#### What to Do

```bash
# 1. Read the week plan
cat docs/implementation/WEEK_6_PLAN.md

# 2. Follow day-by-day instructions:
#    Monday: Core validations (Issues #118-125)
#    Tuesday: Pip packaging setup
#    Wednesday: Documentation & examples
#    Thursday: Final testing & bug fixes
#    Friday: MVP release preparation

# 3. Verify completion
pip install -e . && marcus --version && echo "Week 6: ✓"
pytest tests/ --cov=src --cov-report=term-missing
```

#### Success Criteria

✅ 7 core validations implemented and tested
✅ Pip package installs successfully (`pip install marcus`)
✅ CLI works (`marcus start`, `marcus --version`)
✅ All tests pass with 95%+ coverage
✅ Documentation complete (README, QUICKSTART, API Reference)
✅ MVP v0.1.0 ready for release

#### Related Issues

🔗 [Issues #118-125: Core Validations](https://github.com/yourusername/marcus/issues)

---

**Note**: After completing Week 5.5 and Week 6, reserve time for integration testing, bug fixes, and documentation improvements before proceeding to Cato bundling.

---

## Phase 2: Cato Bundling (Weeks 8-11)

### Overview

**Goal**: Bundle the Cato dashboard with Marcus for a unified user experience.

**What You'll Build**:
- Git submodule integration (Cato → Marcus)
- Unified installation (`pip install marcus` installs everything)
- Unified startup (`marcus start` launches everything)
- Unified dashboard with 6 tabs (Launch, Terminals, Kanban, Live, Historical, Global)

**Status**: ⏳ **Not Started**

---

### Step 7: Week 8 - Git Submodule Setup

#### What You're Building

Integrate Cato as a git submodule at `src/dashboard/` and configure build system to bundle it with Marcus.

**Why This Matters**: Users should not need to install Marcus and Cato separately. By using git submodules:
- Cato remains an independent repository (can be developed separately)
- Marcus references a specific Cato commit (reproducible builds)
- `pip install marcus` automatically installs and builds Cato

#### Documentation

📄 **Plan**: `docs/CATO/CATO_MCP_INTEGRATION_PLAN.md` (Week 8 section)

#### Key Deliverables

```bash
# Repository structure after Week 8
~/dev/marcus/
├── src/
│   ├── dashboard/          ← Git submodule pointing to Cato
│   │   ├── backend/
│   │   └── frontend/
│   ├── marcus_mcp/
│   └── ...
├── .gitmodules             ← Submodule configuration
├── package.json            ← NPM scripts for Cato
└── pyproject.toml          ← Updated with Cato dependencies
```

- `.gitmodules` file with Cato reference
- `package.json` with npm scripts for building Cato
- Updated `pyproject.toml` with Cato backend dependencies
- Post-install hook to build Cato frontend

#### What to Do

```bash
# 1. Read the plan
cat docs/CATO/CATO_MCP_INTEGRATION_PLAN.md
# Focus on "Week 8: Git Submodule Setup" section

# 2. Add Cato as submodule
cd ~/dev/marcus
git checkout develop
git submodule add https://github.com/yourusername/cato.git src/dashboard
git submodule init
git submodule update --remote

# 3. Create package.json (see plan for content)
# 4. Update pyproject.toml (see plan for content)

# 5. Test installation
pip install -e .
ls src/dashboard/frontend/dist/  # Should contain built frontend

# 6. Verify
git submodule status
python -c "import src.dashboard.backend.main; print('Week 8: ✓')"
```

#### Success Criteria

✅ `src/dashboard/` submodule exists and points to Cato
✅ `git submodule status` shows correct commit
✅ `package.json` created with build scripts
✅ `pyproject.toml` updated with Cato dependencies
✅ `pip install -e .` builds Cato frontend automatically
✅ `src/dashboard/frontend/dist/` contains built frontend

---

### Step 8: Week 9 - Unified Installation

#### What You're Building

Consolidate all dependencies so `pip install marcus` installs Marcus + Cato in one command.

**Why This Matters**: Users should run one command to install everything. No separate `npm install` or build steps needed.

#### Documentation

📄 **Plan**: `docs/CATO/CATO_MCP_INTEGRATION_PLAN.md` (Week 9 section)

#### Key Deliverables

```python
# setup.py - Post-install hook
class PostInstallCommand(install):
    def run(self):
        install.run(self)
        # Build Cato frontend during pip install
        subprocess.check_call(["npm", "install"], cwd="src/dashboard/frontend")
        subprocess.check_call(["npm", "run", "build"], cwd="src/dashboard/frontend")
```

- Updated `setup.py` with PostInstallCommand
- Consolidated dependency list
- Installation verification script

#### What to Do

```bash
# 1. Read the plan
cat docs/CATO/CATO_MCP_INTEGRATION_PLAN.md
# Focus on "Week 9: Unified Installation" section

# 2. Update setup.py (see plan for PostInstallCommand class)

# 3. Test clean installation
conda create -n test-marcus python=3.11
conda activate test-marcus
cd ~/dev/marcus
pip install -e .

# 4. Verify everything installed
marcus --version
python -c "import src.dashboard.backend.main; print('Cato backend OK')"
test -f src/dashboard/frontend/dist/index.html || echo "Build failed!"

# 5. Test from scratch (simulating user install)
conda create -n fresh-install python=3.11
conda activate fresh-install
pip install git+https://github.com/yourusername/marcus.git
marcus --version
```

#### Success Criteria

✅ Single `pip install marcus` installs everything
✅ No separate `npm install` needed
✅ Cato frontend built automatically during install
✅ Installation works from PyPI (or git URL)
✅ All dependencies resolved correctly

---

### Step 9: Week 10 - Unified Startup Command

#### What You're Building

Implement `marcus start` command that launches Marcus MCP server + Cato backend with one command.

**Why This Matters**: Users should run one command to start everything. No separate terminal windows needed.

#### Documentation

📄 **Plan**: `docs/CATO/CATO_MCP_INTEGRATION_PLAN.md` (Week 10 section)

#### Key Deliverables

```python
# src/cli/commands/start.py - Unified startup
@click.command()
def start(port: int, no_browser: bool, dev: bool) -> None:
    """
    Start Marcus and Cato dashboard with one command.

    Starts:
    1. Marcus MCP Server (port 4298)
    2. Cato Backend API (port 4301)
    3. Opens browser to http://localhost:4301
    """
    # ... implementation
```

- `src/cli/commands/start.py` - Unified startup command
- Process management (start, monitor, stop all services)
- Automatic browser opening
- Graceful shutdown on Ctrl+C

#### What to Do

```bash
# 1. Read the plan
cat docs/CATO/CATO_MCP_INTEGRATION_PLAN.md
# Focus on "Week 10: Unified Startup" section

# 2. Create src/cli/commands/start.py (see plan for complete code)

# 3. Register command in src/cli/main.py
# from src.cli.commands import start
# start.register(cli)

# 4. Test unified startup
marcus start

# Should see:
# 🚀 Starting Marcus + Cato unified dashboard...
# 📡 Starting Marcus MCP Server (port 4298)...
# ✓ Marcus MCP Server started
# 🔧 Starting Cato Backend API (port 4301)...
# ✓ Cato Backend started
# 🌐 Opening browser to http://localhost:4301...
# ✅ Marcus is running!

# 5. Verify services running
curl http://localhost:4298/health  # Marcus MCP
curl http://localhost:4301/health  # Cato backend
curl http://localhost:4301/        # Cato frontend (static)

# 6. Test graceful shutdown (Ctrl+C)
# All services should stop cleanly
```

#### Success Criteria

✅ `marcus start` launches all services
✅ Marcus MCP Server starts on port 4298
✅ Cato Backend starts on port 4301
✅ Browser opens automatically to http://localhost:4301
✅ Ctrl+C stops all services gracefully
✅ Health checks confirm services running

---

### Step 10: Week 11 - Unified Dashboard UI

#### What You're Building

Create the unified 6-tab dashboard that combines Marcus launch interface with Cato visualization.

**Why This Matters**: Users need a single interface to:
- Launch projects and register agents (Launch tab)
- Monitor agent terminals (Terminals tab)
- View Kanban boards (Kanban tab)
- See real-time visualization (Live tab)
- Analyze completed projects (Historical tab)
- Get system-wide insights (Global tab)

#### Documentation

📄 **Plan**: `docs/CATO/CATO_MCP_INTEGRATION_PLAN.md` (Week 11 section)

#### Key Deliverables

```typescript
// src/dashboard/frontend/src/layouts/UnifiedDashboard.tsx
export const UnifiedDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Box>
      <Tabs value={activeTab} onChange={handleTabChange}>
        <Tab label="🚀 Launch" />
        <Tab label="💻 Terminals" />
        <Tab label="📋 Kanban" />
        <Tab label="📊 Live" />
        <Tab label="📚 Historical" />
        <Tab label="🌍 Global" />
      </Tabs>

      {/* Tab content */}
    </Box>
  );
};
```

- `UnifiedDashboard.tsx` - Main layout with 6 tabs
- 6 tab components:
  1. `LaunchTab.tsx` - Agent registration, project creation
  2. `TerminalsTab.tsx` - Live agent terminal outputs
  3. `KanbanTab.tsx` - Kanban board integration
  4. `LiveTab.tsx` - Real-time network graph (existing Cato)
  5. `HistoricalTab.tsx` - Post-project analysis (existing Cato)
  6. `GlobalTab.tsx` - Cross-project insights (new)
- Updated `App.tsx` to use UnifiedDashboard

#### What to Do

```bash
# 1. Read the plan
cat docs/CATO/CATO_MCP_INTEGRATION_PLAN.md
# Focus on "Week 11: Unified Dashboard UI" section

# 2. Create unified layout
cd src/dashboard/frontend

# Create layouts directory
mkdir -p src/layouts

# Create UnifiedDashboard.tsx (see plan for complete code)
# Create src/components/tabs/ directory
# Create each tab component:
#   - LaunchTab.tsx
#   - TerminalsTab.tsx
#   - KanbanTab.tsx
#   - LiveTab.tsx (reuse existing Cato live view)
#   - HistoricalTab.tsx (reuse existing Cato historical view)
#   - GlobalTab.tsx (new)

# 3. Update App.tsx to use UnifiedDashboard

# 4. Build and test
npm run build
marcus start
# Navigate to http://localhost:4301
# Click through all 6 tabs
# Verify each tab loads correctly

# 5. Test each tab functionality
# - Launch: Create project, register agent
# - Terminals: See agent output (requires agents running)
# - Kanban: View Planka board (if configured)
# - Live: See real-time network graph
# - Historical: Load completed project
# - Global: View system metrics
```

#### Success Criteria

✅ Dashboard shows 6 tabs in navigation
✅ All tabs load without errors
✅ Navigation between tabs is smooth
✅ Launch tab can create projects and register agents
✅ Terminals tab shows live agent outputs
✅ Kanban tab displays board (if configured)
✅ Live tab shows real-time network graph
✅ Historical tab shows completed project analysis
✅ Global tab shows system-wide metrics
✅ UI is responsive and polished

---

## Phase 3: Web Console (Development Tool)

### Overview

**Goal**: Build a web-based experiment dashboard for developers testing Marcus locally.

**What You'll Build**:
- Multi-agent terminal monitoring (xterm.js)
- Health checks and auto-recovery for stuck agents
- Experiment configuration wizard
- Command injection for agent recovery

**Status**: ⏳ **Not Started**
**Priority**: OPTIONAL (for advanced users)

**Why Build This**: The web console is a development tool for running controlled experiments. It's useful for:
- Testing Marcus changes with multiple agents
- Monitoring agent health in real-time
- Recovering stuck agents automatically
- Running MAS (Multi-Agent System) research experiments

---

### Step 11: Week 12 - Web Console Backend

#### What You're Building

FastAPI backend that manages experiments, terminal sessions, and Marcus MCP integration.

**Why This Matters**: Developers need a way to:
- Configure experiments with optimal agent counts
- Launch multiple AI tools (Claude, Cursor, Amp) in terminals
- Monitor agent health
- Recover stuck agents automatically

#### Documentation

📄 **Plan**: `dev-tools/web-console/IMPLEMENTATION_PLAN.md` (Phase 1)

#### Key Deliverables

```python
# Terminal management with PTY sessions
class TerminalSession:
    def inject_command(self, command: str) -> None:
        """Inject command into terminal for recovery."""

    def check_health(self, timeout_seconds: float) -> bool:
        """Check if session is healthy (detect stuck agents)."""

# Marcus MCP client (calls via Claude Code CLI)
class MarcusMCPClient:
    async def create_project(self, name: str, description: str, options: dict) -> dict:
        """Create Marcus project."""

    async def get_optimal_agent_count(self) -> dict:
        """Get optimal agent count for project."""
```

- `terminal.py` - Terminal session management with PTY
- `marcus_client.py` - Marcus MCP integration
- `server.py` - FastAPI server with REST API + WebSocket
- Experiment management (create, analyze, launch, monitor)
- Health monitoring and auto-recovery

#### What to Do

```bash
# 1. Read the plan
cat dev-tools/web-console/IMPLEMENTATION_PLAN.md
# Focus on "Phase 1: Backend Foundation"

# 2. Create project structure
mkdir -p dev-tools/web-console/backend/marcus_web_console
cd dev-tools/web-console/backend

# 3. Create pyproject.toml (see plan)
# 4. Create terminal.py (see plan for complete code)
# 5. Create marcus_client.py (see plan)
# 6. Create server.py (see plan)

# 7. Install and test
pip install -e .
marcus-web-console

# 8. Test API
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/experiments \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "description": "Test project", "complexity": "prototype"}'

# 9. Visit API docs
open http://localhost:8000/docs
```

#### Success Criteria

✅ FastAPI server starts on port 8000
✅ Can create experiments via API
✅ Can analyze projects (calls Marcus MCP)
✅ Can launch agent terminals
✅ WebSocket streams terminal I/O
✅ Health monitoring detects inactive sessions
✅ Recovery endpoint can inject commands

---

### Step 12: Week 13 - Web Console Frontend

#### What You're Building

Single-page web UI for the experiment dashboard with xterm.js terminals.

**Why This Matters**: Developers need a visual interface to:
- Configure experiments (wizard flow)
- See optimal agent recommendations
- Launch agents with different AI tools
- Monitor multiple terminal windows
- Recover stuck agents with one click

#### Documentation

📄 **Plan**: `dev-tools/web-console/IMPLEMENTATION_PLAN.md` (Phase 2)

#### Key Deliverables

```html
<!-- Wizard flow -->
Step 1: Configure → Step 2: Analyze → Step 3: Launch → Step 4: Monitor

<!-- Terminal grid with xterm.js -->
<div class="terminals-grid">
  <!-- Each agent gets a terminal window -->
  <div class="terminal-container">
    <div class="terminal-header">
      agent-1 <span class="health-indicator"></span>
    </div>
    <div id="term-agent-1"></div> <!-- xterm.js instance -->
  </div>
</div>
```

- `static/index.html` - Single-page application
- Wizard flow (Configure → Analyze → Launch → Monitor)
- xterm.js terminal grid
- Health indicators with auto-recovery
- Browser notifications for unhealthy agents

#### What to Do

```bash
# 1. Read the plan
cat dev-tools/web-console/IMPLEMENTATION_PLAN.md
# Focus on "Phase 2: Frontend"

# 2. Create static directory
mkdir -p dev-tools/web-console/backend/static

# 3. Create index.html (see plan for complete code)
# Includes:
#   - CSS for dark theme
#   - JavaScript for wizard flow
#   - xterm.js integration
#   - WebSocket connection per terminal
#   - Health monitoring

# 4. Enable static file serving in server.py
# Uncomment:
# app.mount("/", StaticFiles(directory="static", html=True), name="static")

# 5. Test full workflow
marcus serve  # Start Marcus MCP server
marcus-web-console  # Start web console
open http://localhost:8000

# 6. Walk through wizard
# - Step 1: Create experiment
# - Step 2: View optimal agent analysis
# - Step 3: Configure agents (backend: 2, frontend: 2)
# - Step 4: Monitor terminals
# - Test recovery button
```

#### Success Criteria

✅ Wizard flow works (Configure → Analyze → Launch → Monitor)
✅ Terminal grid displays correctly with xterm.js
✅ WebSocket streams terminal I/O in real-time
✅ Health indicators update (green = healthy, red = unhealthy)
✅ Recovery button injects commands to restart agents
✅ Browser notifications appear for unhealthy agents
✅ Auto-recovery triggers after 2 minutes of inactivity

---

## Phase 4: Advanced Features (Weeks 12+)

### Overview

**Status**: ⏳ **Not Started**
**Priority**: OPTIONAL (post-MVP enhancements)

These features enhance the user experience but are not required for v1.0 release.

---

### Optional Feature 1: Progressive Feedback UI

#### What You're Building

Progressive loading indicators for long-running operations (project creation, task decomposition).

**Why This Matters**: Project creation can take 30-60 seconds. Users need visual feedback showing progress.

#### Documentation

📄 **Plan**: `docs/CATO/PROGRESSIVE_FEEDBACK_REQUIREMENTS.md`

#### What to Do

```bash
# 1. Read the requirements
cat docs/CATO/PROGRESSIVE_FEEDBACK_REQUIREMENTS.md

# 2. Implement progressive indicators
# - Task decomposition progress (0% → 25% → 50% → 75% → 100%)
# - Streaming updates via SSE
# - Skeleton loaders while loading
# - Optimistic UI updates

# 3. Test with slow network
# Simulate delay to see progressive feedback
```

---

### Optional Feature 2: UX Improvements

#### What You're Building

Dashboard UX enhancements based on usability audit.

**Why This Matters**: The dashboard should be intuitive and delightful to use.

#### Documentation

📄 **Plan**: `docs/CATO/CATO_UX_ANALYSIS_AND_RECOMMENDATIONS.md`

#### What to Do

```bash
# 1. Read the UX analysis
cat docs/CATO/CATO_UX_ANALYSIS_AND_RECOMMENDATIONS.md

# 2. Implement prioritized improvements
# - Tooltips for all controls
# - Keyboard shortcuts
# - Responsive design
# - Dark/light theme toggle
# - Accessibility (ARIA labels, keyboard navigation)
```

---

### Optional Feature 3: Cross-Project Insights (Global Tab)

#### What You're Building

System-wide analytics across all projects.

**Why This Matters**: Users running multiple projects need:
- Which agents are most effective?
- Where are bottlenecks across projects?
- Resource utilization trends

#### What to Do

```bash
# 1. Design global metrics
# - Agent performance across all projects
# - Task completion rates
# - Bottleneck detection
# - Resource utilization

# 2. Implement aggregation
# - Query all project history files
# - Aggregate metrics
# - Cache results for performance

# 3. Build Global tab UI
# - Charts (agent performance, task throughput)
# - Tables (project comparison)
# - Filters (date range, project type)
```

---

## Documentation Index

### Quick Reference

| Document | Location | Purpose |
|----------|----------|---------|
| **This Guide** | `docs/DEVELOPMENT_GUIDE.md` | Step-by-step implementation roadmap |
| **Unified Master Plan** | `docs/UNIFIED_MASTER_IMPLEMENTATION_PLAN.md` | Complete 13-16 week overview |
| **MVP Summary** | `docs/MVP_IMPLEMENTATION_PLAN.md` | MVP overview (Weeks 1-6) |
| **Week 1 Plan** | `docs/implementation/WEEK_1_PLAN.md` | Configuration system |
| **Week 2 Plan** | `docs/implementation/WEEK_2_PLAN.md` | Feature entity |
| **Week 3 Plan** | `docs/implementation/WEEK_3_PLAN.md` | Workspace isolation |
| **Week 4 Plan** | `docs/implementation/WEEK_4_PLAN.md` | Feature context |
| **Week 5 Plan** | `docs/implementation/WEEK_5_PLAN.md` | Telemetry & CATO API |
| **Week 6 Plan** | `docs/implementation/WEEK_6_PLAN.md` | Validations & Docker |
| **Cato Bundling** | `docs/CATO/CATO_MCP_INTEGRATION_PLAN.md` | Weeks 8-11 (git submodules, unified dashboard) |
| **Web Console** | `dev-tools/web-console/IMPLEMENTATION_PLAN.md` | Development tool (OPTIONAL) |
| **Progressive Feedback** | `docs/CATO/PROGRESSIVE_FEEDBACK_REQUIREMENTS.md` | UX feature spec |
| **UX Improvements** | `docs/CATO/CATO_UX_ANALYSIS_AND_RECOMMENDATIONS.md` | Dashboard UX audit |

### Architecture & Design

| Document | Location | Purpose |
|----------|----------|---------|
| **Workspace Isolation Design** | `docs/design/workspace-isolation-and-feature-context.md` | Git worktree architecture |
| **Feature Context Design** | `docs/design/feature-context.md` | Context aggregation design |
| **Telemetry Design** | `docs/design/telemetry-system.md` | Event tracking architecture |

### User Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| **README** | `README.md` | Project overview |
| **Configuration Guide** | `docs/CONFIGURATION.md` | How to configure Marcus |
| **Deployment Guide** | `docs/deployment/DOCKER.md` | How to deploy with Docker |
| **API Reference** | `docs/api/README.md` | MCP tool documentation |
| **Testing Guide** | `docs/testing/MANUAL_TEST_CHECKLIST.md` | How to test Marcus |

### Development Tools

| Document | Location | Purpose |
|----------|----------|---------|
| **Experiment Protocol** | `dev-tools/experiments/docs/EXPERIMENT-PROTOCOL.md` | How to run experiments |
| **Experiment Guide** | `dev-tools/experiments/docs/EXPERIMENT_GUIDE.md` | Best practices |
| **Optimal Agents** | `dev-tools/experiments/docs/OPTIMAL_AGENTS.md` | Agent optimization |
| **Scoring Rubric** | `dev-tools/experiments/docs/PROJECT-SCORING-RUBRIC.md` | Quality metrics |

---

## Verification & Testing

### After Each Week

Run these checks to verify completion:

```bash
# 1. Run unit tests for that week's code
pytest tests/unit/<module>/ -v

# 2. Check test coverage
pytest tests/unit/<module>/ --cov=src.<module> --cov-report=term-missing

# 3. Run type checking
mypy src/<module>/

# 4. Run linting
black src/<module>/
isort src/<module>/
flake8 src/<module>/

# 5. Manual verification (see success criteria in each week section)
```

### Before Moving to Next Phase

```bash
# Phase 1 → Phase 2 (MVP → Cato Bundling)
pytest tests/ -v --cov=src --cov-report=html
mypy src/
docker build -t marcus:latest .
docker-compose up -d
curl http://localhost:4298/health  # Marcus MCP
curl http://localhost:4301/health  # Cato API

# Phase 2 → Phase 3 (Cato Bundling → Web Console)
pip install -e .  # Clean install
marcus start  # Should launch everything
open http://localhost:4301  # Dashboard should load with 6 tabs
# Manually test each tab

# Phase 3 complete (Web Console)
marcus-web-console  # Should start
open http://localhost:8000  # Should show experiment wizard
```

---

## Getting Help

### When You're Stuck

1. **Check the week plan** - Each week has detailed day-by-day instructions
2. **Review test cases** - Tests show expected behavior
3. **Check related issues** - GitHub issues have context and discussion
4. **Read design docs** - Architecture decisions explained in `docs/design/`
5. **Ask questions** - Open a GitHub discussion or issue

### Common Issues

#### "I don't understand what this week is building"

→ Read the "Why This Matters" section in the week plan
→ Review the success criteria
→ Look at test cases to see expected behavior

#### "Tests are failing"

→ Read the test names (they describe what should happen)
→ Check if you followed TDD (write tests first!)
→ Review error messages carefully
→ Compare your code to examples in the plan

#### "I'm confused about the architecture"

→ Read `docs/UNIFIED_MASTER_IMPLEMENTATION_PLAN.md` for big picture
→ Check `docs/design/` for specific component designs
→ Draw diagrams to visualize data flow

#### "The plan is unclear or incomplete"

→ Open a GitHub issue to improve the documentation
→ Ask for clarification in discussions
→ Reference similar code in the codebase

### Resources

- **GitHub Discussions**: Ask questions, share ideas
- **GitHub Issues**: Report bugs, request features
- **Documentation**: `docs/` directory
- **Examples**: `dev-tools/examples/` directory
- **Tests**: `tests/` directory (shows how to use code)

---

## Summary: Your Journey

### Week-by-Week Roadmap

```
⏳ Week 1:  Configuration System (START HERE)
⏳ Week 2:  Feature Entity
⏳ Week 3:  Workspace Isolation (Git Worktrees)
⏳ Week 4:  Feature Context Aggregation
⏳ Week 5:  Telemetry & CATO API
⏳ Week 6:  Validations & Docker
⏳ Week 8:  Git Submodule Setup (after Week 6 testing)
⏳ Week 9:  Unified Installation
⏳ Week 10: Unified Startup Command
⏳ Week 11: Unified Dashboard UI
⏳ Week 12: Web Console Backend (OPTIONAL)
⏳ Week 13: Web Console Frontend (OPTIONAL)
```

### What You'll Have Built

After completing this guide:

**Core System** (Weeks 1-6):
- Multi-agent orchestration engine
- Workspace isolation with git worktrees
- Automatic feature context building
- Real-time telemetry and event broadcasting
- Production-ready with validations and Docker

**Unified Dashboard** (Weeks 8-11):
- Single installation (`pip install marcus`)
- Single startup (`marcus start`)
- 6-tab dashboard (Launch, Terminals, Kanban, Live, Historical, Global)
- Bundled Cato visualization

**Development Tools** (Weeks 12-13, OPTIONAL):
- Web-based experiment dashboard
- Multi-agent terminal monitoring
- Health checks and auto-recovery

---

## Next Steps

### If You're Starting Fresh

```bash
# 1. START WITH WEEK 1 (Configuration System)
cat docs/implementation/WEEK_1_PLAN.md
# Follow the day-by-day instructions

# 2. Continue sequentially through Weeks 2-6
# Each week has detailed instructions in docs/implementation/

# 3. After Week 6, test the complete MVP
pytest tests/ -v --cov=src
# Fix any bugs, improve documentation

# 4. Move to Week 8 (Git Submodule Setup)
cat docs/CATO/CATO_MCP_INTEGRATION_PLAN.md
# Follow Week 8-11 instructions

# 5. (Optional) Build Web Console (Weeks 12-13)
cat dev-tools/web-console/IMPLEMENTATION_PLAN.md
```

### If You're Joining Mid-Project

```bash
# 1. Read this guide completely (DEVELOPMENT_GUIDE.md)
# 2. Check project status (which weeks are done?)
git log --oneline --graph --all
# Look for commit messages indicating completed weeks

# 3. Read all completed week plans to understand what was built
cat docs/implementation/WEEK_*_PLAN.md

# 4. Run verification tests
pytest tests/ -v

# 5. Continue from next incomplete week
# Example: If Week 3 is done, start with Week 4
cat docs/implementation/WEEK_4_PLAN.md
```

---

**Questions?** Open a GitHub issue or discussion.
**Found a bug?** Report it with reproduction steps.
**Improved the docs?** Submit a PR!

Good luck building Marcus! 🚀
