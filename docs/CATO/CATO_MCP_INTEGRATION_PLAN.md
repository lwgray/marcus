# Cato Bundled Architecture Implementation Plan

**Date:** 2025-11-11 (Original), 2025-12-21 (Updated for 8-week schedule)
**Goal:** Bundle Cato dashboard with Marcus for unified user experience
**Timeline:** Covered by Weeks 4-7 in current 8-week implementation plan (see DEVELOPMENT_GUIDE.md)
**Note:** This plan was originally Weeks 8-11 in the 13-week schedule
**For:** Junior engineers and contributors

---

## Table of Contents

1. [What Problem Are We Solving?](#what-problem-are-we-solving)
2. [Bundled Architecture Overview](#bundled-architecture-overview)
3. [Implementation Strategy](#implementation-strategy)
4. [Detailed Implementation Steps](#detailed-implementation-steps)
5. [Unified Dashboard Design](#unified-dashboard-design)
6. [Testing Strategy](#testing-strategy)
7. [Glossary](#glossary)

---

## What Problem Are We Solving?

### The Vision: One Unified System

**Current State**: Marcus and Cato are two separate projects that users must install and run independently:

```bash
# What users do now (complex):
cd ~/dev/marcus && pip install -e .
cd ~/dev/cato && npm install && npm run dev

# Start Marcus MCP server
python -m src.marcus_mcp.server

# Start Cato backend
cd ~/dev/cato/backend && uvicorn main:app

# Start Cato frontend
cd ~/dev/cato/frontend && npm run dev

# Open multiple browser tabs to use different features
```

**Desired State**: Marcus bundles Cato as an integrated dashboard:

```bash
# What users will do (simple):
pip install marcus                    # Installs everything (Marcus + Cato)
marcus start                          # Launches unified dashboard
# Browser opens automatically to http://localhost:5173
# All features accessible in one interface
```

### Why Bundle with Git Submodules?

**Git submodules** allow us to:
1. **Keep Cato development independent**: Cato has its own repository, commit history, and releases
2. **Bundle seamlessly**: Marcus references Cato as `src/dashboard/` submodule
3. **Synchronized releases**: When Marcus v0.1.0 releases, it pins to a specific Cato version
4. **Maintainability**: Bug fixes to Cato can be developed independently, then pulled into Marcus

---

## Bundled Architecture Overview

### Repository Structure

```
~/dev/marcus/                          ← Main Marcus repository
├── src/
│   ├── dashboard/                     ← Git submodule pointing to ~/dev/cato
│   │   ├── backend/                   ← Cato backend (FastAPI)
│   │   ├── frontend/                  ← Cato frontend (React/Vite)
│   │   └── README.md                  ← Cato's README
│   ├── marcus_mcp/                    ← Marcus MCP server
│   ├── core/                          ← Marcus core logic
│   └── ...
├── pyproject.toml                     ← Includes Cato's dependencies
├── package.json                       ← Runs npm scripts for Cato
└── .gitmodules                        ← Git submodule configuration
```

### Git Submodule Configuration

**.gitmodules file** (in Marcus repository):

```ini
[submodule "src/dashboard"]
    path = src/dashboard
    url = https://github.com/yourusername/cato.git
    branch = main
```

**What this means:**
- `src/dashboard/` is a reference to the Cato repository
- When you clone Marcus, it can automatically pull Cato
- Marcus pins to a specific Cato commit (reproducible builds)

### Installation Architecture

```
User runs: pip install marcus
    ↓
setup.py / pyproject.toml runs:
    ├─ Install Marcus Python dependencies
    ├─ Install Cato Python dependencies (from src/dashboard/backend)
    ├─ Run npm install (install Cato frontend dependencies)
    ├─ Run npm run build (build Cato frontend for production)
    └─ Install CLI command: marcus
```

**Result**: User has complete system with single `pip install`

### Unified Startup

```
User runs: marcus start
    ↓
Marcus CLI starts:
    ├─ Marcus MCP Server (port 4298)
    ├─ Cato Backend (port 4301) - serves API + static frontend
    └─ Opens browser to http://localhost:4301 (unified dashboard)
```

**Result**: One command starts everything, browser opens automatically

---

## Implementation Strategy

### Alignment with UNIFIED_MASTER_IMPLEMENTATION_PLAN.md

This plan implements **Weeks 4-7** from the current 8-week implementation plan (originally Weeks 8-11 in the 13-week plan):

- **Week 4**: Git submodule setup, repository integration (originally Week 8)
- **Week 5**: Unified installation (`pip install marcus` bundles everything) (originally Week 9)
- **Week 6**: Unified startup (`marcus start` launches everything) (originally Week 10)
- **Week 7**: Unified dashboard UI (6 tabs: Launch, Terminals, Kanban, Live, Historical, Global) (originally Week 11)

### Key Principles

1. **Cato remains independent**: Can be developed, tested, and released separately
2. **Marcus bundles Cato**: Users don't need to know Cato is separate
3. **Unified user experience**: Single installation, single startup, single dashboard
4. **Backward compatibility**: Existing Marcus features continue working

---

## Detailed Implementation Steps

### Week 4: Git Submodule Setup (Originally Week 8)

**Reference**: See DEVELOPMENT_GUIDE.md Week 4 section for current plan

#### Day 1-2: Initialize Submodule

```bash
# In Marcus repository
cd ~/dev/marcus

# Add Cato as submodule
git submodule add https://github.com/yourusername/cato.git src/dashboard

# Initialize and update submodule
git submodule init
git submodule update --remote

# Commit submodule reference
git add .gitmodules src/dashboard
git commit -m "feat: add Cato dashboard as git submodule"
```

**Verify**:
```bash
# Check submodule status
git submodule status

# Should see:
# +<commit-hash> src/dashboard (heads/main)
```

#### Day 3-4: Update Build Configuration

**Update pyproject.toml**:

```toml
[project]
name = "marcus"
version = "0.1.0"
dependencies = [
    "anthropic>=0.25.0",
    "fastapi>=0.110.0",
    "uvicorn>=0.27.0",
    # ... Marcus dependencies ...
    # Cato backend dependencies (from src/dashboard/backend)
    "fastapi>=0.110.0",
    "sqlalchemy>=2.0.0",
    "websockets>=12.0"
]

[project.scripts]
marcus = "src.cli.main:cli"

[tool.setuptools]
packages = ["src", "src.dashboard"]
```

**Create package.json** (in Marcus root):

```json
{
  "name": "marcus-unified",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "install-dashboard": "cd src/dashboard/frontend && npm install",
    "build-dashboard": "cd src/dashboard/frontend && npm run build",
    "dev-dashboard": "cd src/dashboard/frontend && npm run dev",
    "postinstall": "npm run install-dashboard && npm run build-dashboard"
  },
  "devDependencies": {
    "concurrently": "^8.0.0"
  }
}
```

**What this does:**
- `npm install` (run by `pip install marcus`) → installs Cato frontend deps → builds Cato
- Built Cato frontend gets bundled with Marcus package

#### Day 5: Test Installation Flow

```bash
# Clean install test
cd ~/dev/marcus
pip install -e .

# Verify:
# 1. Marcus Python package installed
python -c "import src.marcus_mcp.server; print('Marcus OK')"

# 2. Cato frontend built
ls src/dashboard/frontend/dist/

# 3. Marcus CLI available
marcus --version
```

---

### Week 5: Unified Installation (Originally Week 9)

**Reference**: See DEVELOPMENT_GUIDE.md Week 5 section for current plan

#### Consolidate Dependencies

**Goal**: Single `pip install marcus` installs everything (no separate `pip install cato` needed)

**Update setup.py** (if using setuptools):

```python
from setuptools import setup, find_packages
from setuptools.command.install import install
import subprocess
import os

class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install.run(self)

        # Build Cato frontend
        print("Building Cato dashboard...")
        cwd = os.path.dirname(os.path.abspath(__file__))
        dashboard_path = os.path.join(cwd, "src", "dashboard", "frontend")

        if os.path.exists(dashboard_path):
            subprocess.check_call(["npm", "install"], cwd=dashboard_path)
            subprocess.check_call(["npm", "run", "build"], cwd=dashboard_path)
            print("✓ Cato dashboard built successfully")
        else:
            print("⚠ Warning: Cato dashboard not found (did you init submodules?)")

setup(
    name="marcus",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Marcus dependencies
        "anthropic>=0.25.0",
        "fastapi>=0.110.0",
        # ... etc ...
    ],
    cmdclass={
        'install': PostInstallCommand,
    },
    entry_points={
        'console_scripts': [
            'marcus=src.cli.main:cli',
        ],
    },
)
```

**Test**:

```bash
# Clean environment
conda create -n test-marcus python=3.11
conda activate test-marcus

# Install from source
cd ~/dev/marcus
pip install -e .

# Verify everything installed
marcus --version
python -c "import src.dashboard.backend.main; print('Cato backend OK')"
ls src/dashboard/frontend/dist/index.html || echo "Frontend build failed!"
```

---

### Week 6: Unified Startup (Originally Week 10)

**Reference**: See DEVELOPMENT_GUIDE.md Week 6 section for current plan

#### Implement `marcus start` Command

**Create src/cli/commands/start.py**:

```python
"""
Unified startup command - Start Marcus + Cato with one command.
"""
import click
import subprocess
import asyncio
import webbrowser
import time
from pathlib import Path
import sys

@click.command()
@click.option('--port', default=4301, help='Dashboard port (default: 4301)')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
@click.option('--dev', is_flag=True, help='Development mode (hot reload)')
def start(port: int, no_browser: bool, dev: bool) -> None:
    """
    Start Marcus and Cato dashboard with one command.

    This command starts:
    1. Marcus MCP Server (port 4298)
    2. Cato Backend API (port 4301)
    3. Cato Frontend (served by Cato backend)

    The browser automatically opens to http://localhost:4301

    Examples:

        # Start everything
        marcus start

        # Development mode (hot reload)
        marcus start --dev

        # Custom port
        marcus start --port 8000
    """
    click.echo("🚀 Starting Marcus + Cato unified dashboard...\n")

    asyncio.run(_start_services(port, no_browser, dev))


async def _start_services(port: int, no_browser: bool, dev: bool) -> None:
    """Start all services."""
    processes = []

    try:
        # Step 1: Start Marcus MCP Server
        click.echo("📡 Starting Marcus MCP Server (port 4298)...")
        marcus_mcp = subprocess.Popen(
            [sys.executable, "-m", "src.marcus_mcp.server"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(("Marcus MCP Server", marcus_mcp))
        await asyncio.sleep(2)  # Wait for startup

        if marcus_mcp.poll() is not None:
            click.echo("❌ Marcus MCP Server failed to start")
            return

        click.echo("✓ Marcus MCP Server started\n")

        # Step 2: Start Cato Backend
        click.echo(f"🔧 Starting Cato Backend API (port {port})...")

        dashboard_path = Path(__file__).parent.parent.parent / "dashboard" / "backend"

        cato_backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app",
             "--host", "0.0.0.0", "--port", str(port)],
            cwd=str(dashboard_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(("Cato Backend", cato_backend))
        await asyncio.sleep(3)  # Wait for startup

        if cato_backend.poll() is not None:
            click.echo("❌ Cato Backend failed to start")
            return

        click.echo("✓ Cato Backend started\n")

        # Step 3: Open browser (unless disabled)
        dashboard_url = f"http://localhost:{port}"

        if not no_browser:
            click.echo(f"🌐 Opening browser to {dashboard_url}...")
            await asyncio.sleep(1)  # Give server time to be ready
            webbrowser.open(dashboard_url)

        # Success message
        click.echo("\n" + "="*60)
        click.echo("✅ Marcus is running!")
        click.echo("="*60)
        click.echo(f"\n  Dashboard: {dashboard_url}")
        click.echo("  Marcus MCP: Running on port 4298")
        click.echo("\nPress Ctrl+C to stop all services\n")

        # Keep alive
        try:
            while True:
                await asyncio.sleep(1)

                # Health check
                if marcus_mcp.poll() is not None:
                    click.echo("\n❌ Marcus MCP Server crashed")
                    break
                if cato_backend.poll() is not None:
                    click.echo("\n❌ Cato Backend crashed")
                    break

        except KeyboardInterrupt:
            click.echo("\n\n⏹ Stopping services...")

    finally:
        # Cleanup: stop all processes
        for name, proc in processes:
            click.echo(f"  Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

        click.echo("✓ All services stopped\n")


# Register with CLI
def register(cli):
    """Register start command with main CLI."""
    cli.add_command(start)
```

**Register in src/cli/main.py**:

```python
import click
from src.cli.commands import start

@click.group()
def cli():
    """Marcus CLI - Multi-Agent Resource Coordination System"""
    pass

# Register commands
start.register(cli)

if __name__ == "__main__":
    cli()
```

**Test**:

```bash
marcus start

# Should see:
# 🚀 Starting Marcus + Cato unified dashboard...
# 📡 Starting Marcus MCP Server (port 4298)...
# ✓ Marcus MCP Server started
# 🔧 Starting Cato Backend API (port 4301)...
# ✓ Cato Backend started
# 🌐 Opening browser to http://localhost:4301...
# ✅ Marcus is running!
```

---

### Week 7: Unified Dashboard UI (Originally Week 11)

**Reference**: See DEVELOPMENT_GUIDE.md Week 7 section for current plan

#### Design: 6-Tab Unified Dashboard

**Goal**: Merge Marcus launch interface with Cato visualization into one cohesive dashboard

```
┌────────────────────────────────────────────────────────────┐
│  Marcus Dashboard                          [User] [Settings]│
├────────────────────────────────────────────────────────────┤
│  🚀 Launch  |  💻 Terminals  |  📋 Kanban  |  📊 Live  |  📚 Historical  |  🌍 Global │
├────────────────────────────────────────────────────────────┤
│                                                              │
│  [Content area - changes based on selected tab]             │
│                                                              │
└────────────────────────────────────────────────────────────┘
```

**Tab Descriptions**:

1. **🚀 Launch**: Agent registration, project creation, task assignment (current Marcus UI)
2. **💻 Terminals**: Live agent terminal outputs (current Marcus terminal view)
3. **📋 Kanban**: Kanban board integration with Planka/GitHub (if enabled)
4. **📊 Live**: Real-time network graph, agent swim lanes (current Cato live mode)
5. **📚 Historical**: Post-project analysis, retrospective (current Cato historical mode)
6. **🌍 Global**: Cross-project insights, system-wide metrics (new feature)

#### Implementation: Create Unified Layout

**File**: `src/dashboard/frontend/src/layouts/UnifiedDashboard.tsx`

```typescript
import React, { useState } from 'react';
import { Tabs, Tab, Box, AppBar, Toolbar, Typography } from '@mui/material';

// Import tab components
import LaunchTab from '../components/tabs/LaunchTab';
import TerminalsTab from '../components/tabs/TerminalsTab';
import KanbanTab from '../components/tabs/KanbanTab';
import LiveTab from '../components/tabs/LiveTab';
import HistoricalTab from '../components/tabs/HistoricalTab';
import GlobalTab from '../components/tabs/GlobalTab';

export const UnifiedDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Marcus Dashboard
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Tab Navigation */}
      <Tabs value={activeTab} onChange={handleTabChange} centered>
        <Tab label="🚀 Launch" />
        <Tab label="💻 Terminals" />
        <Tab label="📋 Kanban" />
        <Tab label="📊 Live" />
        <Tab label="📚 Historical" />
        <Tab label="🌍 Global" />
      </Tabs>

      {/* Tab Content */}
      <Box sx={{ flexGrow: 1, p: 3, overflow: 'auto' }}>
        {activeTab === 0 && <LaunchTab />}
        {activeTab === 1 && <TerminalsTab />}
        {activeTab === 2 && <KanbanTab />}
        {activeTab === 3 && <LiveTab />}
        {activeTab === 4 && <HistoricalTab />}
        {activeTab === 5 && <GlobalTab />}
      </Box>
    </Box>
  );
};
```

**Update App Entry Point**:

**File**: `src/dashboard/frontend/src/App.tsx`

```typescript
import React from 'react';
import { UnifiedDashboard } from './layouts/UnifiedDashboard';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
  },
});

function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <UnifiedDashboard />
    </ThemeProvider>
  );
}

export default App;
```

---

## Unified Dashboard Design

### Tab 1: 🚀 Launch

**Purpose**: Agent registration, project creation, task assignment

**Features**:
- Register new agents (provide agent_id, name, role, skills)
- Create projects via natural language
- View agent status (active, idle, working)
- Manual task assignment controls

**Data Source**: Marcus MCP Server (`/api/agents`, `/api/projects`)

---

### Tab 2: 💻 Terminals

**Purpose**: Live agent terminal outputs

**Features**:
- Multiple terminal panes (one per agent)
- Real-time output streaming (WebSocket or SSE)
- Filter by agent
- Copy output to clipboard

**Data Source**: Marcus MCP Server (`/api/agents/{agent_id}/terminal/stream`)

---

### Tab 3: 📋 Kanban

**Purpose**: Kanban board integration (if enabled)

**Features**:
- Embedded Planka/GitHub Projects view (iframe or API integration)
- Drag-and-drop task management
- Filter by project, status, assignee
- Create tasks directly from dashboard

**Data Source**: Kanban provider API (Planka, GitHub, Linear)

---

### Tab 4: 📊 Live (Cato Live Mode)

**Purpose**: Real-time visualization of running project

**Features**:
- Network graph (agents, tasks, dependencies)
- Agent swim lanes (timeline view)
- Live metrics panel (active agents, task throughput)
- Health check status

**Data Source**: Cato Backend (`/api/cato/snapshot`, `/api/cato/events/stream`)

---

### Tab 5: 📚 Historical (Cato Historical Mode)

**Purpose**: Post-project analysis and retrospective

**Features**:
- Project retrospective view
- Decision log
- Failure analysis
- Performance metrics
- Agent fidelity scores

**Data Source**: Marcus history files (`~/.marcus/history/{project_id}/`)

---

### Tab 6: 🌍 Global

**Purpose**: Cross-project insights and system-wide metrics

**Features**:
- All projects dashboard (multi-project view)
- System-wide agent performance
- Cross-project comparisons
- Resource utilization trends
- Global search across all projects

**Data Source**: Aggregated from all projects

---

## Testing Strategy

### Unit Tests

**Submodule Integration**:
```python
# tests/unit/test_submodule_integration.py
def test_dashboard_submodule_exists():
    """Test that dashboard submodule is present."""
    dashboard_path = Path("src/dashboard")
    assert dashboard_path.exists()
    assert (dashboard_path / "backend").exists()
    assert (dashboard_path / "frontend").exists()
```

**CLI Command**:
```python
# tests/unit/cli/test_start_command.py
def test_start_command_available():
    """Test that 'marcus start' command is registered."""
    from src.cli.main import cli
    assert 'start' in [cmd.name for cmd in cli.commands.values()]
```

### Integration Tests

**Full Installation Flow**:
```bash
# tests/integration/test_installation.sh
#!/bin/bash
set -e

# Clean environment
conda create -n test-install python=3.11 -y
conda activate test-install

# Install Marcus (should bundle Cato)
cd ~/dev/marcus
git submodule update --init --recursive
pip install -e .

# Verify installation
marcus --version
python -c "import src.dashboard.backend.main"
test -f src/dashboard/frontend/dist/index.html

echo "✓ Installation test passed"
```

**Startup Test**:
```python
# tests/integration/test_unified_startup.py
import subprocess
import requests
import time

def test_unified_startup():
    """Test that 'marcus start' launches all services."""
    # Start Marcus
    proc = subprocess.Popen(
        ["marcus", "start", "--no-browser"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    time.sleep(10)  # Wait for startup

    try:
        # Check Marcus MCP Server
        # (add health check endpoint)

        # Check Cato Backend
        response = requests.get("http://localhost:4301/health")
        assert response.status_code == 200

        # Check Cato Frontend (static files served)
        response = requests.get("http://localhost:4301")
        assert response.status_code == 200
        assert "Marcus Dashboard" in response.text

    finally:
        proc.terminate()
        proc.wait()
```

### E2E Tests

**Complete User Flow**:
1. User runs `pip install marcus`
2. User runs `marcus start`
3. Browser opens to dashboard
4. User navigates through all 6 tabs
5. Each tab loads without errors
6. User creates a project from Launch tab
7. Project appears in Live tab
8. User stops services with Ctrl+C

---

## Glossary

### Git Submodule
A Git repository embedded inside another Git repository. Allows Marcus to reference Cato's code while keeping Cato's development independent.

### Bundled Architecture
Packaging multiple components (Marcus + Cato) as a single installable unit so users only need one command to install everything.

### Unified Dashboard
Single web interface that combines all Marcus and Cato features in one place with consistent navigation and user experience.

### Static Site Serving
Cato backend serves pre-built frontend files (HTML, CSS, JS) from `dist/` folder. No separate frontend server needed in production.

### Post-Install Hook
Script that runs automatically after `pip install` completes. Used to build Cato frontend as part of Marcus installation.

---

## Summary

**What This Plan Achieves:**

1. ✅ **Single Installation**: `pip install marcus` installs everything (no separate Cato install)
2. ✅ **Single Startup**: `marcus start` launches all services with one command
3. ✅ **Unified Dashboard**: All features accessible in one browser window with 6 tabs
4. ✅ **Independent Development**: Cato remains a separate repository for independent releases
5. ✅ **Simplified UX**: Users don't need to know Marcus and Cato are separate projects

**Timeline**: Covered by **Weeks 4-7** in current 8-week implementation plan (see DEVELOPMENT_GUIDE.md)

**Status**: ⏳ Not yet started (waiting for Weeks 1-3 MVP to complete)

---

**For Complete Implementation Details**:

See [UNIFIED_MASTER_IMPLEMENTATION_PLAN.md](../UNIFIED_MASTER_IMPLEMENTATION_PLAN.md) for:
- Week-by-week breakdown
- Day-by-day tasks
- Code examples
- Testing requirements
- Success criteria

**Questions or Issues?**
- Review unified master plan
- Check existing week plans (WEEK_1-6)
- Open GitHub issue
- Join team discussions

---

**Related Documents**:
- [UNIFIED_MASTER_IMPLEMENTATION_PLAN.md](../UNIFIED_MASTER_IMPLEMENTATION_PLAN.md) - Complete 13-16 week roadmap
- [WEEK_5_PLAN.md](../implementation/WEEK_5_PLAN.md) - Telemetry & CATO API integration
- [PROGRESSIVE_FEEDBACK_REQUIREMENTS.md](PROGRESSIVE_FEEDBACK_REQUIREMENTS.md) - UX for long operations
- [CATO_UX_ANALYSIS_AND_RECOMMENDATIONS.md](CATO_UX_ANALYSIS_AND_RECOMMENDATIONS.md) - Dashboard UX improvements

---

Last Updated: 2025-11-11
