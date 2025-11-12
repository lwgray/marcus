# Marcus Unified Master Implementation Plan

**Date**: 2025-01-11
**Status**: Active Implementation
**Total Duration**: 13-16 weeks
**Current Phase**: Phase 3 (In Progress)

---

## Executive Summary

This document unifies all Marcus implementation plans into a single, coherent roadmap. It integrates:
- **Phase 3**: Post-project analysis (historical UI in Cato)
- **MVP Weeks 1-6**: Core features, workspace isolation, telemetry
- **Cato MCP Integration**: Replace Planka with Cato MCP (no Docker)
- **Web Console**: Multi-agent experiment launcher with full Kanban

**Key Goals**:
1. ✅ **Remove Docker dependency** - Marcus works standalone
2. ✅ **Simplify onboarding** - < 5 minute setup (single install: `pip install marcus`)
3. ✅ **Enable multi-agent testing** - Web-based experiment launcher
4. ✅ **Provide observability** - Historical analysis + real-time monitoring
5. ✅ **Monitor adoption** - Opt-in multi-user telemetry
6. ✅ **Unified product experience** - Bundle Cato with Marcus using git submodule

---

## Implementation Timeline

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Phase 3  │ MVP Week 1-6              │ Cato MCP       │ Web Console              │
│ (Week 1) │ (Weeks 2-7)               │ (Weeks 8-10)   │ (Weeks 11-13)           │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 🔨 Now   │ Configuration,            │ SQLite Kanban  │ Terminal Launcher +     │
│          │ Features, Workspaces,     │ Replace Planka │ Experiment Dashboard    │
│          │ Telemetry                 │ (No Docker!)   │                         │
└──────────────────────────────────────────────────────────────────────────────────┘

Total: 13-16 weeks
```

---

## Phase Overview

### Phase 3: Post-Project Analysis (Week 1) 🔨 IN PROGRESS

**Duration**: 4-5 days
**Status**: Currently Working
**Goal**: Add historical project analysis to Cato dashboard
**Location**: `docs/post_project_analysis/PHASE_3_IMPLEMENTATION_PLAN.md`

**Key Deliverables**:
- Mode toggle in Cato (Live ↔ Historical)
- Historical analysis backend endpoints
- Retrospective dashboard
- Requirement fidelity visualization
- Decision impact visualization
- Failure diagnosis display

**Dependencies**: Phase 1-2 (Complete)

**Success Criteria**:
- ✅ Can switch between live and historical modes
- ✅ Can analyze any completed project
- ✅ All Phase 2 insights displayed clearly
- ✅ Zero regression in live monitoring mode

**Timeline**:
- Day 1-2: Backend API endpoints
- Day 3: Store integration (mode toggle)
- Day 4: Historical views (Part 1)
- Day 5: Historical views (Part 2) + polish

---

### MVP: Core Features (Weeks 2-7)

**Duration**: 6 weeks
**Status**: In Progress (Started, Not Complete)
**Goal**: Implement core Marcus features for production readiness
**Location**: `docs/implementation/MVP_IMPLEMENTATION_PLAN.md`

**Key Deliverables** (by week):

#### Week 1: Configuration & Foundation ⏳
**Goal**: Centralize configuration management
- Type-safe configuration system
- Validation with clear error messages
- Environment variable override support
- Configuration documentation
- **Issue**: #68

#### Week 2: Workspace Isolation - Phase 1 ⏳
**Goal**: Add Feature entity and prepare infrastructure
- Project and Feature dataclasses
- Feature-aware artifact and decision logging
- Feature indexing system
- WorkspaceManager skeleton

#### Week 3: Workspace Isolation - Phase 2 ⏳
**Goal**: Implement git worktree-based workspace isolation
- Full WorkspaceManager implementation
- Git worktree creation and cleanup
- Workspace conflict detection
- Integration with task assignment

#### Week 4: Feature Context Aggregation 📅
**Goal**: Implement comprehensive feature context building
- FeatureContextBuilder
- Git commit tracking and annotation
- Context injection system
- `get_feature_context` and `get_feature_status` MCP tools

#### Week 5: Telemetry & CATO Integration 📅
**Goal**: Add user journey tracking and CATO dashboard integration

**Monday-Friday** (Core Telemetry):
- User journey milestone tracking
- Research event logging (for MAS studies)
- CATO dashboard integration API
- Real-time event broadcasting (SSE)

**Saturday-Sunday** (EXTENDED - Multi-User Telemetry):
- Privacy & security guidelines
- Central telemetry backend service (FastAPI + PostgreSQL)
- Marcus client telemetry uploader (opt-in)
- Cato global metrics dashboard

**What's Collected** (Anonymized):
- ✅ Milestone completion rates
- ✅ Feature usage counts
- ✅ Error types (sanitized)
- ✅ System metadata (OS, versions)

**What's NOT Collected**:
- ❌ Source code or file contents
- ❌ API keys or credentials
- ❌ Personal information (names, emails, IP)
- ❌ Task descriptions or project details

**See**: `docs/TELEMETRY_PRIVACY.md` for complete details

#### Week 6: Production Readiness 📅
**Goal**: Core validations, Docker deployment, and MVP release
- Core validations (Issues #118-125)
- Multi-stage Dockerfile and Docker Compose
- Comprehensive user documentation
- Performance testing and bug fixes
- MVP release (v0.1.0)

**Dependencies**: None (standalone phase after Phase 3)

**Success Criteria**:
- ✅ All 6 weeks complete
- ✅ 100+ tests passing (95%+ coverage)
- ✅ Feature entity working
- ✅ Workspace isolation working
- ✅ Telemetry system working (local + optional remote)
- ✅ CATO integration working

---

### Cato MCP Integration (Weeks 8-10)

**Duration**: 2-3 weeks
**Status**: Not Started
**Goal**: Replace Planka with Cato MCP to remove Docker dependency + **Bundle Cato with Marcus**
**Location**: `docs/CATO/CATO_MCP_INTEGRATION_PLAN.md`

**Why This Matters**:
- ✅ No Docker required for Marcus
- ✅ Single command setup: `pip install marcus && marcus start`
- ✅ Cato reads/writes Marcus's existing SQLite database
- ✅ Better visualization than Planka
- ✅ Integrated with CATO dashboard (from Week 5)
- ✅ **Unified product**: Cato bundled with Marcus via git submodule

**Bundled Architecture**:
```
~/dev/marcus/
├── src/
│   ├── core/
│   ├── mcp/
│   └── dashboard/          ← Git submodule (points to ~/dev/cato)
├── dev-tools/
│   └── web-console/
├── pyproject.toml          ← pip install marcus installs everything
└── .gitmodules             ← Git submodule configuration

# Cato remains independently developable at ~/dev/cato
# Marcus bundles it for unified user experience
```

**Key Deliverables**:

#### Week 8: Stage 0-1 (Planning + Git Submodule + Read-Only MCP)
- **Git submodule setup** (integrate ~/dev/cato into ~/dev/marcus/src/dashboard/)
- **Update pyproject.toml** to include Cato dependencies
- Cato MCP server (read-only operations)
- MCP protocol implementation
- Basic Kanban UI in Cato

#### Week 9: Stage 2-3 (Write Operations + Marcus Integration)
- `CatoKanbanProvider` (implements `KanbanInterface`)
- Write operations (create task, update status, assign)
- Marcus integration (replace Planka config with Cato MCP)
- Migration tool: `marcus migrate --from planka --to cato-mcp`

#### Week 10: Stage 4-6 (UI Polish + Testing + Migration)
- Multi-project support in Cato UI
- Drag-and-drop task management
- Feature visualization (if MVP features available)
- Comprehensive testing
- Documentation and migration guide

**Architecture** (Bundled):
```
┌─────────────────────────────────────────────────────────┐
│ Marcus Installation (pip install marcus)                │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │ Marcus CLI (marcus start)                      │    │
│  │  • Starts all services in unified process      │    │
│  │  • Port 4298: Marcus MCP Server                │    │
│  │  • Port 4301: Cato Backend (from submodule)    │    │
│  │  • Port 5173: Unified Dashboard                │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  Marcus Kitchen ←──────────┐                            │
│      ↓                     │                            │
│      ↓ (MCP protocol)      │ (reads/writes directly)   │
│      ↓                     │                            │
│  Cato MCP Server ──────────┤                            │
│  (src/dashboard/)          │                            │
│      ↑                     │                            │
│      │ (HTTP API)          ↓                            │
│      │              Marcus SQLite Database              │
│  Unified Dashboard         (single source)              │
│  (port 5173)                                            │
│                                                          │
└─────────────────────────────────────────────────────────┘

Git Repository Structure:
~/dev/marcus/
├── src/dashboard/  ← Git submodule (~/dev/cato)
└── ...

~/dev/cato/  ← Can still develop independently
└── ...
```

**Dependencies**:
- MVP Week 2 (Feature entity) - recommended but not required
- Phase 3 (Cato dashboard exists)

**Success Criteria**:
- ✅ Marcus works without Docker
- ✅ Can switch from Planka to Cato MCP via config change
- ✅ All Marcus MCP tools work (create_project, request_next_task, etc.)
- ✅ Cato UI provides drag-and-drop Kanban
- ✅ Migration preserves all data
- ✅ Setup time < 5 minutes for new users

---

### Web Console: Unified Dashboard (Weeks 11-13)

**Duration**: 2-3 weeks
**Status**: Not Started
**Goal**: **Merge Cato + Web Console into unified dashboard** with experiment launcher, terminals, and Kanban
**Location**: `dev-tools/web-console/IMPLEMENTATION_PLAN.md`

**Why This Matters**:
- ✅ **Single unified interface** - No switching between Cato and Web Console
- ✅ OS-agnostic multi-agent testing (no more osascript/xdotool)
- ✅ Visual experiment monitoring (all agents in browser)
- ✅ Agent health monitoring with auto-recovery
- ✅ Professional Kanban board (drag-drop, real-time updates)
- ✅ Historical + Live monitoring in one place

**Unified Dashboard Design**:
```
Marcus Dashboard (Port 5173)
┌─────────────────────────────────────────────────────────┐
│ 🚀 Launch │ 💻 Terminals │ 📋 Kanban │ 📊 Live │ 📈 Historical │ 🌍 Global │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  🚀 Launch Tab:                                         │
│     • Experiment configuration                          │
│     • Agent count selector                              │
│     • Project complexity picker                         │
│     • "Start Experiment" button                         │
│                                                          │
│  💻 Terminals Tab:                                      │
│     • Multi-terminal grid (xterm.js)                    │
│     • Agent health indicators (🟢🟡🔴)                   │
│     • Recovery buttons                                   │
│                                                          │
│  📋 Kanban Tab:                                         │
│     • Full Kanban board (TODO | IN PROGRESS | DONE)    │
│     • Drag-and-drop task management                     │
│     • Real-time updates                                  │
│                                                          │
│  📊 Live Tab:                                           │
│     • Network graph (from Phase 1-2)                    │
│     • Swim lanes                                         │
│     • Real-time metrics                                  │
│                                                          │
│  📈 Historical Tab:                                     │
│     • Post-project analysis (from Phase 3)              │
│     • Retrospectives                                     │
│     • Decision impact                                    │
│                                                          │
│  🌍 Global Tab (if opted in):                           │
│     • Cross-user metrics                                 │
│     • Milestone completion rates                         │
│     • Popular features                                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Key Deliverables**:

#### Week 11: Unified Dashboard Foundation + Backend
- **Merge Cato React app with Web Console** (unified codebase)
- **Add tab navigation** (Launch, Terminals, Kanban, Live, Historical, Global)
- **Marcus CLI enhancement**: `marcus start` launches all services
- Terminal session management (PTY for Unix, winpty for Windows)
- WebSocket server for real-time terminal I/O
- Experiment manager (orchestrates multi-agent runs)
- Agent health monitoring (5-min inactivity timeout)
- Command injection for stuck agent recovery
- REST API:
  - `POST /api/experiment/start`
  - `GET /api/experiment/{id}/status`
  - `POST /api/experiment/{id}/recover/{agent_id}`
  - `DELETE /api/experiment/{id}`

#### Week 12: Unified Dashboard - Launch + Terminals Tabs
- **🚀 Launch Tab**:
  - Experiment configuration UI
  - Agent count selector (1-10 agents)
  - Project complexity picker (prototype, standard, enterprise)
  - "Start Experiment" button with validation
- **💻 Terminals Tab**:
  - xterm.js integration for browser terminals
  - Multi-terminal grid layout (2x3, 2x4, 3x3)
  - Real-time terminal I/O via WebSocket
  - Agent health indicators (🟢 Green / 🟡 Yellow / 🔴 Red)
  - Recovery buttons for stuck agents
  - Experiment controls (pause, resume, stop)

#### Week 13: Unified Dashboard - Kanban + Polish
- **📋 Kanban Tab**:
  - Professional Kanban board UI (React + drag-drop)
  - Real-time task updates (WebSocket sync with backend)
  - Columns: TODO, IN PROGRESS, DONE
  - Task cards with:
    - Task name and description
    - Priority indicator
    - Assigned agent (with avatar)
    - Status history
    - Progress percentage
  - Drag-and-drop task movement
  - Task filtering (by agent, priority, status)
  - Bulk operations (assign multiple, bulk status change)
  - **Integration with Cato MCP backend** (uses same SQLite DB)
- **📊 Live, 📈 Historical, 🌍 Global Tabs** (already exist from Cato, just add to nav)
- **Polish**: Unified branding, responsive design, keyboard shortcuts

**Architecture** (Unified):
```
┌─────────────────────────────────────────────────────────────────────┐
│ Browser - Marcus Unified Dashboard (Port 5173)                     │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────────┐│
│ │ Tab Navigation:                                                  ││
│ │ 🚀 Launch │ 💻 Terminals │ 📋 Kanban │ 📊 Live │ 📈 Hist │ 🌍 Global ││
│ └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  Active Tab Content:                                               │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ [Launch] Experiment Config, Agent Selector, Start Button       │ │
│  │ [Terminals] Multi-terminal Grid with xterm.js (🟢🟡🔴)         │ │
│  │ [Kanban] Drag-drop board (TODO | IN PROGRESS | DONE)          │ │
│  │ [Live] Network graph, Swim lanes (from Cato Phase 1-2)        │ │
│  │ [Historical] Post-project analysis (from Cato Phase 3)         │ │
│  │ [Global] Cross-user metrics (from Week 5 telemetry)           │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└───────────────────────┬──────────────────┬──────────────────────────┘
                        │ WebSocket        │ HTTP API
                        ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Marcus Backend Services (started by `marcus start`)                │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Marcus MCP Server (Port 4298)                                  │ │
│  │  • create_project, request_next_task, report_task_progress    │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Cato Backend (Port 4301) - From Git Submodule                  │ │
│  │  • Kanban MCP Server                                           │ │
│  │  • Historical Analysis API                                     │ │
│  │  • Live Monitoring API                                         │ │
│  └────────────────────────────┬──────────────────────────────────┘ │
│                                │                                   │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Web Console Backend (Port 5174)                                │ │
│  │  • Terminal Manager (PTY Sessions)                             │ │
│  │  • Experiment Manager                                          │ │
│  │  • WebSocket Server (real-time terminal I/O)                   │ │
│  └────────────────────────────┬──────────────────────────────────┘ │
│                                │                                   │
└────────────────────────────────┼───────────────────────────────────┘
                                 ▼
                    ┌────────────────────────────┐
                    │ Marcus SQLite Database     │
                    │ (Single Source of Truth)   │
                    │  • Tasks                   │
                    │  • Projects                │
                    │  • Features                │
                    │  • Decisions               │
                    │  • Artifacts               │
                    │  • Telemetry Events        │
                    └────────────────────────────┘
```

**Dependencies**:
- Cato MCP Integration (Weeks 8-10) - Provides Kanban backend
- MVP Week 5 (Telemetry) - For monitoring agent behavior

**Success Criteria**:
- ✅ Can launch 6-agent experiment in < 30 seconds
- ✅ All terminals visible and interactive in browser
- ✅ Agent health monitored with 5-minute timeout
- ✅ Can recover stuck agents with one click
- ✅ Works on Mac, Linux, Windows (via browser)
- ✅ Full Kanban UI with drag-and-drop
- ✅ Real-time task updates across all users
- ✅ Professional UI matching modern Kanban tools (Trello, Asana)

---

## Dependencies & Critical Path

```
Phase 1-2 (Complete) ✅
    │
    ├─→ Phase 3 (Week 1) 🔨 IN PROGRESS
    │       │
    │       └─→ Provides Cato dashboard foundation
    │
    └─→ MVP Weeks 1-6 (Weeks 2-7)
            │
            ├─→ Week 1: Configuration ✅ (Issue #68)
            ├─→ Week 2: Feature Entity (needed by Cato MCP)
            ├─→ Week 3: Workspace Isolation
            ├─→ Week 4: Feature Context
            ├─→ Week 5: Telemetry (includes multi-user opt-in backend)
            └─→ Week 6: Production Readiness
                    │
                    ├─→ Cato MCP Integration (Weeks 8-10)
                    │       │
                    │       └─→ Provides Kanban backend for Web Console
                    │
                    └─→ Web Console (Weeks 11-13)
                            │
                            └─→ Complete System ✅
```

**Critical Path**: Phase 3 → MVP → Cato MCP → Web Console

**Parallel Opportunities**:
- Phase 3 can proceed independently (no blocking)
- Week 5 weekend (telemetry backend) can be done separately if needed
- Web Console frontend (Week 12-13) can start while backend (Week 11) is in testing

---

## Week-by-Week Breakdown

### Week 1 (Current): Phase 3 🔨
- Mon-Tue: Backend API endpoints
- Wed: Store integration
- Thu: Historical views (Part 1)
- Fri: Historical views (Part 2) + testing

### Week 2: MVP Week 1 (Configuration)
- Mon: Create configuration data structure
- Tue: Add validation & environment overrides
- Wed: Migrate existing code
- Thu: Create config_marcus.example.json
- Fri: Testing, documentation & backward compatibility

### Week 3: MVP Week 2 (Feature Entity - Foundation)
- Mon: Add Project and Feature entities
- Tue: Extend artifact and decision logging with feature_id
- Wed: Artifact and decision indexing by feature
- Thu: Create WorkspaceManager skeleton
- Fri: Week 2 integration & testing

### Week 4: MVP Week 3 (Git Worktrees)
- Mon: Implement git worktree creation
- Tue: Implement workspace cleanup
- Wed: Integrate with task assignment
- Thu: Add workspace conflict detection
- Fri: Week 3 testing & documentation

### Week 5: MVP Week 4 (Feature Context)
- Mon: Create FeatureContextBuilder
- Tue: Implement git commit tracking
- Wed: Implement context injection
- Thu: Add get_feature_context MCP tool
- Fri: Add get_feature_status tool & testing

### Week 6: MVP Week 5 (Telemetry & CATO)
- Mon: Enhance telemetry system (journey tracking)
- Tue: Research event logging
- Wed: CATO API integration
- Thu: Real-time event broadcasting
- Fri: Documentation & testing
- **Sat**: Privacy guidelines + telemetry backend service
- **Sun**: Marcus client integration + Cato global metrics

### Week 7: MVP Week 6 (Production Readiness)
- Mon: Core validations (Issues #118-125)
- Tue: Docker deployment enhancement
- Wed: Documentation & examples
- Thu: Final testing & bug fixes
- Fri: MVP release preparation

### Week 8: Cato MCP Stage 0-1 + Git Submodule Integration
- **Mon**: Git submodule setup (integrate ~/dev/cato into ~/dev/marcus/src/dashboard/)
- **Tue**: Update pyproject.toml to include Cato dependencies, test bundled install
- **Wed**: Cato MCP server setup (read-only operations)
- **Thu**: MCP protocol implementation
- **Fri**: Basic Kanban UI in Cato + testing bundled installation

### Week 9: Cato MCP Stage 2-3
- Mon-Tue: CatoKanbanProvider implementation
- Wed: Write operations (create, update, assign)
- Thu: Marcus integration
- Fri: Migration tool + testing

### Week 10: Cato MCP Stage 4-6
- Mon: Multi-project support
- Tue: Drag-and-drop UI
- Wed: Feature visualization
- Thu: Comprehensive testing
- Fri: Documentation + polish

### Week 11: Unified Dashboard Foundation + Backend
- **Mon**: Merge Cato React app with Web Console (create unified codebase)
- **Tue**: Add tab navigation framework (Launch, Terminals, Kanban, Live, Historical, Global)
- **Wed**: Terminal session management (PTY for Unix, winpty for Windows)
- **Thu**: WebSocket server + Experiment manager
- **Fri**: REST API + Agent health monitoring + Marcus CLI enhancement (`marcus start`)

### Week 12: Unified Dashboard - Launch + Terminals Tabs
- **Mon**: 🚀 Launch Tab UI (experiment config, agent selector, complexity picker)
- **Tue**: 🚀 Launch Tab logic (validation, start experiment button, API integration)
- **Wed**: 💻 Terminals Tab - xterm.js integration + multi-terminal grid layout
- **Thu**: 💻 Terminals Tab - Agent health indicators (🟢🟡🔴) + recovery buttons
- **Fri**: 💻 Terminals Tab - Experiment controls (pause, resume, stop) + testing

### Week 13: Unified Dashboard - Kanban Tab + Polish
- **Mon**: 📋 Kanban Tab - Board UI foundation (columns: TODO, IN PROGRESS, DONE)
- **Tue**: 📋 Kanban Tab - Drag-and-drop implementation + task cards
- **Wed**: 📋 Kanban Tab - Real-time updates + filtering (by agent, priority, status)
- **Thu**: 📋 Kanban Tab - Bulk operations + Integration with Cato MCP backend
- **Fri**: Polish (unified branding, responsive design, keyboard shortcuts), testing, documentation

---

## Success Metrics

### Phase 3 Complete When:
- ✅ Historical analysis mode works in Cato
- ✅ Can analyze past projects
- ✅ All Phase 2 insights visualized
- ✅ Zero regression in live mode

### MVP Complete When:
- ✅ All 6 weeks delivered
- ✅ 100+ tests passing (95%+ coverage)
- ✅ Feature entity working
- ✅ Workspace isolation working
- ✅ Telemetry working (local + optional multi-user)
- ✅ Docker deployment ready

### Cato MCP Complete When:
- ✅ Marcus works without Docker
- ✅ < 5 minute setup for new users
- ✅ All Kanban operations work via MCP
- ✅ Migration from Planka successful
- ✅ Drag-and-drop UI polished

### Web Console Complete When:
- ✅ Can launch multi-agent experiments in browser
- ✅ All terminals interactive
- ✅ Agent health monitoring working
- ✅ Stuck agent recovery working
- ✅ Full Kanban UI with drag-and-drop
- ✅ Real-time task updates
- ✅ Works on Mac, Linux, Windows

### Overall Success (Bundled Experience):
```bash
# New user experience after completion (UNIFIED):
pip install marcus          # Single install (includes Cato via submodule)
marcus init                 # Interactive 5-minute setup
marcus start                # Starts all services (MCP + Cato + Dashboard)

# Automatically opens browser: http://localhost:5173
# User sees unified dashboard with 6 tabs:
#   🚀 Launch | 💻 Terminals | 📋 Kanban | 📊 Live | 📈 Historical | 🌍 Global

# Workflow:
# 1. Click 🚀 Launch tab → Select project complexity → "Start 6 Agents"
# 2. Click 💻 Terminals tab → Watch agents work in browser (🟢🟡🔴 health)
# 3. Click 📋 Kanban tab → Drag-drop tasks, assign agents
# 4. Click 📊 Live tab → Monitor network graph, swim lanes
# 5. Click 📈 Historical tab → Analyze completed projects
# 6. Click 🌍 Global tab → View cross-user metrics (if opted in)

# All in ONE unified dashboard!
```

**Time to first experiment**: < 5 minutes (vs. 30+ minutes today)
**User Experience**: Single installation, single command, unified interface

---

## Risk Assessment & Mitigation

| Risk | Impact | Probability | Mitigation | Week |
|------|--------|-------------|------------|------|
| Phase 3 blocks MVP | Medium | Low | Phase 3 is independent, can proceed in parallel | 1 |
| Feature entity breaks existing code | High | Medium | Thorough testing, backward compatibility checks | 3 |
| Git worktrees too complex | High | Medium | Use battle-tested libraries, extensive testing | 4 |
| Telemetry privacy concerns | High | Low | Clear documentation, opt-in only, strict PII validation | 6 |
| Cato MCP slower than Planka | Medium | Low | Keep Planka as option, performance testing | 9 |
| Git submodule complexity | Medium | Medium | Document workflow clearly, use git submodule update --init --recursive | 8 |
| Bundled install conflicts | High | Medium | Isolate dependencies with extras_require, thorough testing | 8 |
| Merging Cato + Web Console UIs | High | Medium | Use React Router for tabs, gradual migration, extensive testing | 11 |
| WebSocket connection issues | High | Medium | Connection retry logic, fallback to polling | 11 |
| PTY management across OS | High | High | Use winpty for Windows, pty for Unix, extensive testing | 11 |
| Agent health detection false positives | Medium | Medium | Tune timeout thresholds, pattern detection | 11 |
| Drag-and-drop UI bugs | Medium | Medium | Use proven library (react-beautiful-dnd), thorough testing | 13 |

---

## Progress Tracking

### Overall Progress
- **Phase 3**: 🔨 In Progress (Week 1)
- **MVP**: ⏳ Started (Weeks 2-7)
- **Cato MCP**: 📅 Not Started (Weeks 8-10)
- **Web Console**: 📅 Not Started (Weeks 11-13)

### Milestones
- [ ] Phase 3 Complete (End of Week 1)
- [ ] MVP Week 1-3 Complete (Foundation + Features + Workspaces)
- [ ] MVP Week 4-6 Complete (Context + Telemetry + Production)
- [ ] Cato MCP Complete (No Docker Required!)
- [ ] Web Console Complete (Full System Online)

---

## Documentation Structure

After completion, users will have:

```
docs/
├── README.md (Updated with new features)
├── QUICKSTART.md (5-minute setup guide)
├── TELEMETRY_PRIVACY.md (Privacy policy)
├── CONFIGURATION.md (Config guide)
│
├── post_project_analysis/
│   └── PHASE_3_IMPLEMENTATION_PLAN.md
│
├── implementation/
│   ├── MVP_IMPLEMENTATION_PLAN.md
│   ├── WEEK_1_PLAN.md (Configuration)
│   ├── WEEK_2_PLAN.md (Features - Foundation)
│   ├── WEEK_3_PLAN.md (Git Worktrees)
│   ├── WEEK_4_PLAN.md (Feature Context)
│   ├── WEEK_5_PLAN.md (Telemetry - Extended with multi-user)
│   └── WEEK_6_PLAN.md (Production Readiness)
│
├── CATO/
│   └── CATO_MCP_INTEGRATION_PLAN.md
│
└── dev-tools/
    └── web-console/
        └── IMPLEMENTATION_PLAN.md
```

---

## Next Actions

### Immediate (This Week - Phase 3):
1. ✅ Continue Phase 3 implementation
2. ✅ Complete historical analysis UI in Cato
3. ✅ Test mode switching (Live ↔ Historical)
4. ✅ Document Phase 3 completion

### Week 2 (MVP Week 1 - Configuration):
1. Create configuration data structure
2. Add validation framework
3. Migrate existing code to use new config
4. Test backward compatibility

### Week 6 (MVP Week 5 - Telemetry Extended):
1. Monday-Friday: Local telemetry (journey tracking, research logging, CATO API)
2. Saturday: Build telemetry backend service (privacy-first)
3. Sunday: Integrate Marcus client + Cato global metrics dashboard

### Week 8 (Cato MCP + Bundled Architecture):
1. **Git submodule setup**: Integrate ~/dev/cato into ~/dev/marcus/src/dashboard/
2. **Update pyproject.toml**: Add Cato dependencies, test `pip install marcus`
3. Start Cato MCP server (read-only)
4. Implement MCP protocol
5. Build basic Kanban UI
6. Test bundled installation thoroughly

### Week 11 (Unified Dashboard):
1. **Merge Cato + Web Console**: Create unified React codebase
2. **Add tab navigation**: Launch, Terminals, Kanban, Live, Historical, Global
3. **Enhance Marcus CLI**: `marcus start` launches all services
4. Implement terminal session management
5. Build WebSocket server
6. Create experiment manager

---

## Communication & Collaboration

### Status Updates
- **Weekly**: Progress report on current week
- **Blockers**: Report immediately if stuck
- **Milestones**: Celebrate each phase completion

### Code Reviews
- All PRs target `develop` branch (never `main`)
- Minimum 1 reviewer per PR
- All tests must pass before merge
- Mypy checks must pass

### Testing Strategy
- **Unit tests**: < 100ms, mock all external dependencies
- **Integration tests**: End-to-end workflows
- **Performance tests**: Week 6, 10, 13 (at phase boundaries)
- **Manual testing**: Follow `docs/testing/MANUAL_TEST_CHECKLIST.md`

---

## Appendix: Original Plan Locations

For detailed implementation instructions, refer to:

1. **Phase 3**: `/Users/lwgray/dev/marcus/docs/post_project_analysis/PHASE_3_IMPLEMENTATION_PLAN.md`
2. **MVP**: `/Users/lwgray/dev/marcus/docs/implementation/MVP_IMPLEMENTATION_PLAN.md`
   - Week 1-6: `docs/implementation/WEEK_{1-6}_PLAN.md`
3. **Cato MCP**: `/Users/lwgray/dev/marcus/docs/CATO/CATO_MCP_INTEGRATION_PLAN.md`
4. **Web Console**: `/Users/lwgray/dev/marcus/dev-tools/web-console/IMPLEMENTATION_PLAN.md`

---

## Git Submodule Workflow (Week 8+)

After Week 8, Cato will be integrated as a git submodule. Here's how to work with the bundled architecture:

### Initial Setup (Week 8)
```bash
# From ~/dev/marcus/
cd ~/dev/marcus
git submodule add ../cato src/dashboard
git submodule update --init --recursive
```

### Developer Workflow

**Working on Marcus only**:
```bash
cd ~/dev/marcus
git pull
git submodule update --init --recursive  # Update Cato to latest
# Make changes to Marcus code
git add . && git commit -m "Marcus changes"
git push
```

**Working on Cato independently**:
```bash
cd ~/dev/cato
# Make changes to Cato
git add . && git commit -m "Cato changes"
git push

# Update Marcus to use latest Cato
cd ~/dev/marcus/src/dashboard
git pull origin main
cd ~/dev/marcus
git add src/dashboard
git commit -m "Update Cato submodule to latest"
git push
```

**Testing bundled installation**:
```bash
cd ~/dev/marcus
pip install -e .  # Install Marcus with Cato in editable mode
marcus start      # Should start all services
```

### Benefits of This Approach
- ✅ **Users**: Single `pip install marcus` gets everything
- ✅ **Developers**: Can still develop Cato independently at ~/dev/cato
- ✅ **Version Control**: Git submodule ensures Marcus always uses compatible Cato version
- ✅ **Flexibility**: Can switch between bundled and separate setups easily

---

**Status**: Ready to Execute
**Next Step**: Complete Phase 3 (Historical Analysis in Cato)
**Timeline**: 13-16 weeks total
**Current Week**: Week 1 of 13-16

**Let's build! 🚀**
