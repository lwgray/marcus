# Marcus Development Guide

**Version**: 2.0
**Last Updated**: 2025-12-21
**Audience**: Junior engineers and new contributors
**Purpose**: Step-by-step guide for building Marcus from foundation to production

**Updated Schedule**: This guide now follows an 8-week implementation plan focused on telemetry and unified dashboard delivery.

---

## Table of Contents

1. [What is Marcus?](#what-is-marcus)
2. [What You'll Build](#what-youll-build)
3. [Architecture Overview](#architecture-overview)
4. [Prerequisites](#prerequisites)
5. [Development Roadmap](#development-roadmap)
6. [Phase 1: MVP Foundation (Weeks 1-3)](#phase-1-mvp-foundation-weeks-1-3)
7. [Phase 2: Unified Dashboard (Weeks 4-7)](#phase-2-unified-dashboard-weeks-4-7)
8. [Phase 3: Web Console (Week 8 - Optional)](#phase-3-web-console-week-8---optional)
9. [Phase 4: Advanced Features](#phase-4-advanced-features)
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
✅ Real-time visualization (unified dashboard)
✅ Telemetry and event broadcasting
✅ Production-ready validations
✅ BYOA architecture (Bring Your Own Agent - agents voluntarily pull work)

---

## What You'll Build

By following this guide, you will build a complete multi-agent orchestration system:

```
End State: Marcus v1.0
    ├── Core Orchestration (MVP - Weeks 1-3)
    │   ├── Configuration system
    │   ├── Telemetry & event broadcasting
    │   └── Production validations
    │
    ├── Unified Dashboard (Weeks 4-7)
    │   ├── Git submodule integration (Cato)
    │   ├── Single installation (pip install marcus)
    │   ├── Single startup (marcus start)
    │   └── 6-tab dashboard (Launch, Terminals, Kanban, Live, Historical, Global)
    │
    └── Development Tools (Optional)
        └── Web Console (Week 8 - experiment dashboard with terminal monitoring)
```

**Timeline**: 3 weeks (MVP) + 4 weeks (Dashboard) + 1 week (Web Console) = **8 weeks total**

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
   - Manages tasks and projects
   - Provides MCP tools for agents
   - Tracks history and telemetry

2. **Telemetry System** - Event tracking and broadcasting
   - User journey tracking
   - Research event logging
   - Real-time event streaming (SSE)

3. **Cato Dashboard** - Real-time visualization
   - Live network graph (agents, tasks, dependencies)
   - Historical analysis
   - Global insights

4. **Web Console** (Optional) - Development tool
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
Weeks 1-3:  MVP Foundation (Core Marcus features)
Weeks 4-7:  Unified Dashboard (Cato bundling)
Week 8:     Web Console (Development tool - OPTIONAL)
```

### Timeline

| Phase | Duration | What You Build | Status |
|-------|----------|----------------|--------|
| **Week 1** | 1-2 days | Configuration system polish | ⏳ Mostly complete |
| **Week 2** | 5 days | Telemetry & CATO API integration | ⏳ Not started |
| **Week 3** | 5 days | Production validations & Docker | ⏳ Not started |
| **Week 4** | 5 days | Git submodule setup | ⏳ Not started |
| **Week 5** | 5 days | Unified installation | ⏳ Not started |
| **Week 6** | 5 days | Unified startup command | ⏳ Not started |
| **Week 7** | 5 days | Unified dashboard UI | ⏳ Not started |
| **Week 8** | 5-10 days | Web Console (OPTIONAL) | ⏳ Not started |

---

## Phase 1: MVP Foundation (Weeks 1-3)

### Overview

**Goal**: Build the core Marcus orchestration system that coordinates AI agents.

**What You'll Build**:
- Type-safe configuration system
- Telemetry and event broadcasting
- Production validations
- Pip packaging

**Status**: ⏳ **NOT STARTED** (ready to begin)

---

### Step 1: Week 1 - Configuration System

**Status Update**: Configuration system is ~80% complete. Existing `src/config/settings.py` provides working config management. Week 1 focus should be on polish and type-safe dataclass conversion if desired.

**Recommended Effort**: 1-2 days (reduced from 5 days)

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

### Step 2: Week 2 - Telemetry & CATO API Integration

#### What You're Building

Comprehensive telemetry system for user journey tracking and research events, plus real-time event broadcasting for the Cato dashboard.

**Why This Matters**:
- **Research**: Track agent behavior for MAS (Multi-Agent System) research
- **Observability**: See what agents are doing in real-time
- **Visualization**: Provide real-time data streams for the Cato dashboard
- **User Analytics**: Understand how users interact with Marcus

#### Documentation

📄 **Plan**: `docs/implementation/WEEK_2_PLAN.md` (formerly WEEK_5_PLAN.md)

#### Key Deliverables

```python
# src/telemetry/journey_tracker.py - User journey tracking
class UserJourneyTracker:
    def log_milestone(self, milestone: str, metadata: dict) -> None:
        """Log user journey milestone (first project, first agent, etc.)"""

# src/telemetry/research_logger.py - Research event logging
class ResearchEventLogger:
    def log_event(self, event_type: str, data: dict) -> None:
        """Log research events for MAS behavioral study"""

# src/api/cato_routes.py - CATO dashboard integration
@router.get("/api/cato/snapshot")
async def get_snapshot():
    """Get current project state snapshot"""

@router.get("/api/cato/events/stream")
async def stream_events() -> StreamingResponse:
    """SSE stream for real-time Marcus events"""
```

- User journey tracking system
- Research event logging
- CATO dashboard integration API (`/api/cato/...`)
- Real-time event broadcasting with SSE (Server-Sent Events)

#### What to Do

```bash
# 1. Read the week plan
cat docs/implementation/WEEK_2_PLAN.md

# 2. Follow day-by-day instructions:
#    Monday: User journey tracking
#    Tuesday: Research event logging
#    Wednesday: CATO snapshot API
#    Thursday: Real-time event broadcasting (SSE)
#    Friday: Week 2 testing & documentation

# 3. Verify completion
curl http://localhost:4301/api/cato/snapshot && echo "Week 2: ✓"
curl http://localhost:4301/api/cato/events/stream && echo "SSE: ✓"
pytest tests/unit/telemetry/ -v
```

#### Success Criteria

✅ User journey tracking logs milestones
✅ Research events captured with structured data
✅ `/api/cato/snapshot` returns project state
✅ `/api/cato/events/stream` broadcasts real-time events via SSE
✅ All tests pass: `pytest tests/unit/telemetry/ -v`
✅ Cato dashboard receives real-time updates

---

### Step 3: Week 3 - Production Validations & Docker

**Status Update**: Marcus already has extensive validation systems and pip packaging. Week 3 focuses on filling gaps, adding Docker support, and final polish.

#### What You're Building

Core validations to prevent runtime errors, pip packaging setup, and comprehensive documentation.

**Why This Matters**: The MVP is feature-complete but not production-ready. Week 3 adds:
- **Validations**: Catch errors before they cause problems (invalid dependencies, circular deps, invalid status transitions)
- **Pip Packaging**: Easy installation with `pip install marcus`
- **Documentation**: Complete user and API documentation

#### Documentation

📄 **Plan**: `docs/implementation/WEEK_3_PLAN.md` (formerly WEEK_6_PLAN.md)

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
cat docs/implementation/WEEK_3_PLAN.md

# 2. Follow day-by-day instructions:
#    Monday: Core validations (Issues #118-125)
#    Tuesday: Pip packaging setup
#    Wednesday: Documentation & examples
#    Thursday: Final testing & bug fixes
#    Friday: MVP release preparation

# 3. Verify completion
pip install -e . && marcus --version && echo "Week 3: ✓"
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

## Phase 2: Unified Dashboard (Weeks 4-7)

### Overview

**Goal**: Bundle the Cato dashboard with Marcus for a unified user experience.

**What You'll Build**:
- Git submodule integration (Cato → Marcus)
- Unified installation (`pip install marcus` installs everything)
- Unified startup (`marcus start` launches everything)
- Unified dashboard with 6 tabs (Launch, Terminals, Kanban, Live, Historical, Global)

**Status**: ⏳ **Not Started**

---

### Step 4: Week 4 - Git Submodule Setup

#### What You're Building

Integrate Cato as a git submodule at `src/dashboard/` and configure build system to bundle it with Marcus.

**Why This Matters**: Users should not need to install Marcus and Cato separately. By using git submodules:
- Cato remains an independent repository (can be developed separately)
- Marcus references a specific Cato commit (reproducible builds)
- `pip install marcus` automatically installs and builds Cato

#### Documentation

📄 **Plan**: `docs/CATO/CATO_MCP_INTEGRATION_PLAN.md` (Week 4 section)

#### Key Deliverables

```bash
# Repository structure after Week 4
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
# Focus on "Week 4: Git Submodule Setup" section

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
python -c "import src.dashboard.backend.main; print('Week 4: ✓')"
```

#### Success Criteria

✅ `src/dashboard/` submodule exists and points to Cato
✅ `git submodule status` shows correct commit
✅ `package.json` created with build scripts
✅ `pyproject.toml` updated with Cato dependencies
✅ `pip install -e .` builds Cato frontend automatically
✅ `src/dashboard/frontend/dist/` contains built frontend

---

### Step 5: Week 5 - Unified Installation

#### What You're Building

Consolidate all dependencies so `pip install marcus` installs Marcus + Cato in one command.

**Why This Matters**: Users should run one command to install everything. No separate `npm install` or build steps needed.

#### Documentation

📄 **Plan**: `docs/CATO/CATO_MCP_INTEGRATION_PLAN.md` (Week 5 section)

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
# Focus on "Week 5: Unified Installation" section

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

### Step 6: Week 6 - Unified Startup Command

#### What You're Building

Implement `marcus start` command that launches Marcus MCP server + Cato backend with one command.

**Why This Matters**: Users should run one command to start everything. No separate terminal windows needed.

#### Documentation

📄 **Plan**: `docs/CATO/CATO_MCP_INTEGRATION_PLAN.md` (Week 6 section)

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
# Focus on "Week 6: Unified Startup" section

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

### Step 7: Week 7 - Unified Dashboard UI

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

📄 **Plan**: `docs/CATO/CATO_MCP_INTEGRATION_PLAN.md` (Week 7 section)

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
# Focus on "Week 7: Unified Dashboard UI" section

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

## Phase 3: Web Console (Week 8 - Optional)

### Overview

**Goal**: Build a web-based experiment dashboard for developers testing Marcus locally.

**Timeline**: Week 8 (5-10 days, optional)

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

### Step 8: Week 8 - Web Console

#### What You're Building

Complete web-based experiment dashboard with FastAPI backend and xterm.js frontend for managing multi-agent experiments.

**Why This Matters**: Developers need a way to:
- Configure experiments with optimal agent counts
- Launch multiple AI tools (Claude, Cursor, Amp) in terminals
- Monitor agent health in real-time
- Recover stuck agents automatically
- Run controlled MAS research experiments

#### Documentation

📄 **Plan**: `dev-tools/web-console/IMPLEMENTATION_PLAN.md`

#### Key Deliverables

**Backend**:
```python
# Terminal management with PTY sessions
class TerminalSession:
    def inject_command(self, command: str) -> None:
        """Inject command into terminal for recovery."""

    def check_health(self, timeout_seconds: float) -> bool:
        """Check if session is healthy (detect stuck agents)."""

# Marcus MCP client
class MarcusMCPClient:
    async def create_project(self, name: str, description: str, options: dict) -> dict:
        """Create Marcus project."""

    async def get_optimal_agent_count(self) -> dict:
        """Get optimal agent count for project."""
```

**Frontend**:
```html
<!-- Wizard flow: Configure → Analyze → Launch → Monitor -->
<div class="terminals-grid">
  <div class="terminal-container">
    <div class="terminal-header">
      agent-1 <span class="health-indicator"></span>
    </div>
    <div id="term-agent-1"></div> <!-- xterm.js instance -->
  </div>
</div>
```

Complete deliverables:
- Backend: Terminal management, Marcus MCP integration, FastAPI server
- Frontend: Wizard UI, xterm.js terminal grid, health monitoring
- Health checks and auto-recovery system
- Browser notifications for unhealthy agents

#### What to Do

```bash
# 1. Read the implementation plan
cat dev-tools/web-console/IMPLEMENTATION_PLAN.md

# 2. Create project structure
mkdir -p dev-tools/web-console/backend/marcus_web_console
mkdir -p dev-tools/web-console/backend/static
cd dev-tools/web-console/backend

# 3. Implement backend (Phase 1)
# - Create terminal.py (PTY session management)
# - Create marcus_client.py (Marcus MCP integration)
# - Create server.py (FastAPI with REST + WebSocket)

# 4. Implement frontend (Phase 2)
# - Create static/index.html (wizard flow + xterm.js grid)
# - Add CSS for dark theme and responsive layout
# - Add JavaScript for wizard logic and WebSocket connections

# 5. Install and test
pip install -e .
marcus serve  # Start Marcus MCP server (separate terminal)
marcus-web-console  # Start web console

# 6. Test full workflow
open http://localhost:8000
# - Step 1: Create experiment configuration
# - Step 2: View optimal agent analysis
# - Step 3: Launch agents in terminals
# - Step 4: Monitor health and test recovery
```

#### Success Criteria

✅ Backend: FastAPI server starts on port 8000
✅ Backend: Can create experiments and call Marcus MCP
✅ Backend: WebSocket streams terminal I/O
✅ Backend: Health monitoring detects inactive sessions
✅ Frontend: Wizard flow works (Configure → Analyze → Launch → Monitor)
✅ Frontend: Terminal grid displays with xterm.js
✅ Frontend: Health indicators update in real-time
✅ Frontend: Recovery button can inject commands
✅ Integration: Browser notifications for unhealthy agents
✅ Integration: Auto-recovery triggers after inactivity

---

## Phase 4: Advanced Features (Post-MVP)

### Overview

**Status**: ⏳ **Not Started**
**Priority**: OPTIONAL (post-v1.0 enhancements)

**Timeline**: After Week 8 (as needed)

These features enhance the user experience but are not required for v1.0 release. Implement based on user feedback and priorities.

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
| **This Guide** | `docs/DEVELOPMENT_GUIDE.md` | Step-by-step 8-week implementation roadmap |
| **Unified Master Plan** | `docs/UNIFIED_MASTER_IMPLEMENTATION_PLAN.md` | Complete implementation overview |
| **MVP Summary** | `docs/MVP_IMPLEMENTATION_PLAN.md` | MVP overview (updated for 8-week schedule) |
| **Week 1 Plan** | `docs/implementation/WEEK_1_PLAN.md` | Configuration system (polish only) |
| **Week 2 Plan** | `docs/implementation/WEEK_2_PLAN.md` | Telemetry & CATO API (formerly Week 5) |
| **Week 3 Plan** | `docs/implementation/WEEK_3_PLAN.md` | Production validations & Docker (formerly Week 6) |
| **Cato Bundling** | `docs/CATO/CATO_MCP_INTEGRATION_PLAN.md` | Weeks 4-7 (git submodules, unified dashboard) |
| **Web Console** | `dev-tools/web-console/IMPLEMENTATION_PLAN.md` | Week 8 development tool (OPTIONAL) |
| **Progressive Feedback** | `docs/CATO/PROGRESSIVE_FEEDBACK_REQUIREMENTS.md` | UX feature spec |
| **UX Improvements** | `docs/CATO/CATO_UX_ANALYSIS_AND_RECOMMENDATIONS.md` | Dashboard UX audit |
| **Alignment Evaluation** | `docs/MVP_CATO_ALIGNMENT_EVALUATION.md` | MVP→CATO alignment analysis |

**Note**: Original Week 2-4 plans (Feature entity, Git worktrees, Feature context) are marked as DEFERRED in `docs/implementation/` - not needed for MVP.

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
⏳ Week 1:  Configuration System Polish (START HERE - mostly complete)
⏳ Week 2:  Telemetry & CATO API Integration
⏳ Week 3:  Production Validations & Docker
⏳ Week 4:  Git Submodule Setup
⏳ Week 5:  Unified Installation
⏳ Week 6:  Unified Startup Command
⏳ Week 7:  Unified Dashboard UI
⏳ Week 8:  Web Console (OPTIONAL)
```

**Total**: 8 weeks (7 weeks required + 1 week optional)

**What Was Removed from Original Plan:**
- Week 2: Feature entity & infrastructure (deferred - not needed for MVP)
- Week 3: Git worktree workspace isolation (deferred - not needed for MVP)
- Week 4: Feature context aggregation (deferred - not needed for MVP)
- Week 5.5: REST API Completion (integrated into Week 2)

**Why These Were Removed:**
The original plan included feature-level abstraction, git worktree isolation, and feature context building. After evaluating current needs and the Cato dashboard's data requirements, these features are not necessary for the MVP. The Cato dashboard works with project → task → subtask hierarchy without requiring feature entities. These capabilities can be added later if needed.

### What You'll Have Built

After completing this guide:

**Core System** (Weeks 1-3):
- Multi-agent orchestration engine
- Real-time telemetry and event broadcasting
- CATO API integration (snapshot + SSE event streaming)
- Production-ready with validations and Docker

**Unified Dashboard** (Weeks 4-7):
- Single installation (`pip install marcus`)
- Single startup (`marcus start`)
- 6-tab dashboard (Launch, Terminals, Kanban, Live, Historical, Global)
- Bundled Cato visualization

**Development Tools** (Week 8, OPTIONAL):
- Web-based experiment dashboard
- Multi-agent terminal monitoring
- Health checks and auto-recovery

---

## Next Steps

### If You're Starting Fresh

```bash
# 1. START WITH WEEK 1 (Configuration System Polish)
cat docs/implementation/WEEK_1_PLAN.md
# Note: ~80% complete, focus on polish only (1-2 days)

# 2. Continue with Week 2 (Telemetry & CATO API)
cat docs/implementation/WEEK_2_PLAN.md
# This is the NEW Week 2 (formerly Week 5 + Week 5.5 content)
# Includes telemetry, REST APIs, and terminal streaming

# 3. Complete Week 3 (Production Validations & Docker)
cat docs/implementation/WEEK_3_PLAN.md
# This is the NEW Week 3 (formerly Week 6)

# 4. After Week 3, test the complete MVP
pytest tests/ -v --cov=src
# Fix any bugs, improve documentation

# 5. Move to Weeks 4-7 (Cato Bundling)
cat docs/CATO/CATO_MCP_INTEGRATION_PLAN.md
# Follow Week 4-7 instructions for unified dashboard

# 6. (Optional) Build Web Console (Week 8)
cat dev-tools/web-console/IMPLEMENTATION_PLAN.md
```

### If You're Joining Mid-Project

```bash
# 1. Read this guide completely (DEVELOPMENT_GUIDE.md)

# 2. Check project status
git log --oneline --graph --all
# Look for commit messages indicating completed weeks

# 3. Read completed week plans
# Note: Original Week 2-4 plans are DEFERRED (not implemented)
# Current plan: Week 1 → Week 2 (Telemetry) → Week 3 (Validations) → Weeks 4-7 (Cato)

# 4. Run verification tests
pytest tests/ -v

# 5. Continue from next incomplete week
# Check the roadmap in this guide to see current status
```

---

**Questions?** Open a GitHub issue or discussion.
**Found a bug?** Report it with reproduction steps.
**Improved the docs?** Submit a PR!

Good luck building Marcus! 🚀
