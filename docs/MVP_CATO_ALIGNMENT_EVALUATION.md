# MVP → CATO Bundling Alignment Evaluation

**Date**: 2025-12-21 (Original) — **Re-evaluated 2026-04-27**
**Evaluator**: Development team
**Purpose**: Ensure MVP (Weeks 1-3) provides exactly what CATO Bundling (Weeks 4-7) needs

---

## ⚠ 2026-04 Re-evaluation: MISALIGNED

**Status**: ⚠️ **MISALIGNED** — the original "ready for Cato bundling"
verdict no longer holds. The MVP shipped in a different shape than this
document predicted, and Cato has evolved independently of Marcus core.

**What is actually true today:**

| Original claim | 2026-04 reality |
|---|---|
| ✅ Week 2 CATO API endpoints will power Live Tab | ❌ The REST endpoints (`/api/cato/snapshot`, `/api/cato/events/stream`, `/api/cato/metrics/journey`, `/api/cato/metrics/research`) are **not built**. Cato consumes Marcus state by reading SQLite + Planka directly. |
| ✅ Week 2 Launch Tab REST APIs included | ❌ Launch tab REST endpoints (`POST /api/agents`, `POST /api/projects`, `POST /api/tasks`) are **not built**. Project creation flows through MCP tools. |
| ✅ Week 2 Terminal Streaming integrated | ❌ `TerminalManager` / PTY service / `GET /api/agents/{id}/terminal/stream` SSE are **not built**. Terminal monitoring lives in Posidonius (sibling repo) and the `/marcus` skill via tmux. |
| ✅ Week 3 Production validations | ✅ Production-grade validation shipped, recently hardened (#421, #337). Different shape than the original `#118-125` plan but solid. |

**What that means for Cato bundling (Weeks 4-7):**

- The "Cato consumes the Marcus REST API" assumption is wrong. Cato today
  is a **read-side dashboard** that pulls from SQLite + Planka.
- A literal git-submodule bundling will work for shipping a single install,
  but it will **not** give Cato the real-time event stream this document
  promised — that requires net-new SSE work in Marcus core.
- A new alignment design is needed before any Week-4 work begins.

**Recommended next step (one of):**

1. **Revive the REST surface** — implement the `/api/cato/*` endpoints and
   migrate Cato off direct SQLite reads. Highest fidelity, most work.
2. **Treat Cato as a sibling product** — keep Cato independent, ship them
   as separate installs, defer the "unified dashboard" goal to the
   proposed Marcus Studio desktop shell (issue #443).
3. **Hybrid** — bundle Cato as a submodule for one-command install, but
   keep its SQLite-reading data path; layer SSE on top later.

**This document should not be used as a green-light for Week 4 work in
its current form.** The rest of the file below is preserved for historical
context.

---

### 2026-04 Triage Decisions

After walking the original commitments item-by-item, the following
decisions have been recorded:

| Item | Original commitment | Decision | Rationale |
|---|---|---|---|
| **`/api/cato/*` REST endpoints** (`/snapshot`, `/events/stream`, `/metrics/journey`, `/metrics/research`) | Build in Week 2 to power Cato Live/Historical tabs | **DEFER** | Cato will continue reading SQLite + Planka directly. Build the REST surface only when Marcus Studio (issue #443) needs it. |
| **Launch tab REST APIs** (`POST/GET /api/agents`, `/api/projects`, `/api/tasks`) | Build in Week 2 to let a frontend create projects without speaking MCP | **DROP** | MCP is the only protocol Marcus needs to expose. Any non-MCP client must speak MCP. No REST wrapper will be built. |
| **Terminal streaming + `TerminalManager`** (PTY service, `/api/agents/{id}/terminal/stream` SSE) | Build in Week 2 to power the Terminals tab | **DROP** | Marcus core does not own terminals. Terminal monitoring stays in Posidonius and tmux. |
| **Cato as git submodule at `src/dashboard/`** (Weeks 4–6: unified install + `marcus start` launches Cato) | Bundle Cato into Marcus for single-command install | **DROP** | Cato remains a sibling product, shipped separately. No submodule integration. |
| **Launch tab (🚀)** (Week 7) | Cato UI for creating projects via REST | **DEFER** | Backend dropped (item above). Tab cannot work as originally specified. Revisit at Marcus Studio M0 (#443) where the launch flow gets redesigned. |
| **Terminals tab (💻)** (Week 7) | Cato UI for live agent terminals via PTY/SSE | **DEFER** | Backend dropped. Revisit at Marcus Studio M0 — the natural place is Posidonius integration (#443 §10). |
| **Kanban tab (📋) REST proxy** (Week 7 optional) | Wrap Planka/Jira/Linear behind a Marcus REST proxy | **DROP** | Planka iframe stays the model. Multi-provider work belongs to a separate roadmap item, not this 8-week MVP plan. |
| **Global tab (🌍) `/api/cato/global/metrics`** (Week 7 low-priority gap) | Cross-project aggregation endpoint | **KEEP** | Build the aggregation endpoint when Global tab is built. Small, useful, no dependencies on the dropped items. |

**Implications for this document:**

- The original "ALIGNED" verdict is permanently superseded.
- Of the original Week 2–7 commitments, only one item survives:
  **the Global tab aggregation endpoint** (item 1.8). Everything else is
  dropped or deferred to Marcus Studio (#443).
- The Live/Historical Cato tab requirements (§Tab 4, §Tab 5) are met
  by direct SQLite + Planka reads, not Marcus REST.
- This document is now primarily a **historical record** of the original
  8-week plan, plus a single live commitment (Global tab aggregation).
- Future "unified dashboard" work belongs in Marcus Studio (#443),
  not in this 8-week MVP plan.

---

## (Historical) Original Executive Summary

**Status (as of 2025-12-21)**: ✅ **ALIGNED** - New 8-week plan provides exactly what CATO bundling needs

**Key Findings**:
- ✅ **Live Tab**: Fully supported by Week 2 CATO API endpoints
- ✅ **Launch Tab**: REST API endpoints included in Week 2
- ✅ **Terminals Tab**: Terminal streaming integrated into Week 2
- ⚠️ **Kanban Tab**: Depends on external Kanban provider (not Marcus responsibility)
- ✅ **Historical Tab**: Supported by existing project history system
- ⚠️ **Global Tab**: Can be built on existing APIs, needs aggregation logic

**Recommendation (now superseded by 2026-04 re-evaluation above):**
The new 8-week plan is "ready for Cato bundling" - no gaps identified.

**What Changed from Original Plan:**
- Removed Feature entities (Week 2 original) - not needed for Cato dashboard
- Removed Git worktrees (Week 3 original) - not needed for current use case
- Removed Feature context (Week 4 original) - not needed for Cato dashboard
- Integrated REST APIs and Terminal streaming into Week 2 Telemetry

---

## What MVP (Weeks 1-3) Builds

### Week 1: Configuration System
**Deliverables**:
- Type-safe configuration with dataclass validation
- Environment variable override support
- Single source of truth for settings

**Status**: ✅ ~80% complete (polish only)

**Relevance to CATO**: ✅ Foundation for configuring dashboard port, features

---

### Week 2: Telemetry & CATO API Integration ⭐
**Deliverables**:
- User journey tracking (JourneyMilestone, AuditLogger)
- Research event logging (ResearchEventLogger)
- **CATO API Endpoints**:
  - ✅ `GET /api/cato/snapshot` - System snapshot
  - ✅ `GET /api/cato/events/stream` - Real-time SSE event stream
  - ✅ `GET /api/cato/metrics/journey` - User journey metrics
  - ✅ `GET /api/cato/metrics/research` - Research-grade MAS metrics
- **Launch Tab REST APIs** (formerly Week 5.5):
  - ✅ `POST /api/agents`, `GET /api/agents`
  - ✅ `POST /api/projects`, `GET /api/projects`
  - ✅ `POST /api/tasks`, `GET /api/tasks`
- **Terminal Streaming** (formerly Week 5.5):
  - ✅ `GET /api/agents/{agent_id}/terminal/stream` - SSE terminal output
  - ✅ `POST /api/agents/{agent_id}/terminal/input` - Command injection
  - ✅ TerminalManager with PTY sessions

**Relevance to CATO**: ✅ **CRITICAL** - Powers Live, Launch, and Terminals tabs

---

### Week 3: Production Validations & Docker
**Deliverables**:
- Validation framework (TaskValidator, ProjectValidator)
- Core validations (#118-125)
- Docker multi-stage builds
- Comprehensive documentation

**Status**: ✅ ~70% complete (fill gaps)

**Relevance to CATO**: ✅ Production deployment infrastructure

---

## What CATO Bundling (Weeks 4-7) Needs

### Week 4: Git Submodule Setup
(Now Week 4 in new schedule)

**Requirements**:
- Marcus must be functional with working MCP server
- CATO API endpoints must exist for integration testing

**MVP Provides**: ✅ Yes (Week 2 includes all APIs)

---

### Week 5: Unified Installation
(Now Week 5 in new schedule)

**Requirements**:
- Marcus installable via `pip install marcus`
- All dependencies manageable via Python packaging

**MVP Provides**: ✅ Yes (Week 1 configuration + Week 3 Docker)

---

### Week 6: Unified Startup
(Now Week 6 in new schedule)

**Requirements**:
- Marcus MCP Server launchable on port 4298
- Cato Backend can connect to Marcus APIs

**MVP Provides**: ✅ Yes (Marcus MCP server exists, API endpoints in Week 2)

---

### Week 7: Unified Dashboard UI
(Now Week 7 in new schedule)
**Requirements by Tab**:

#### Tab 1: 🚀 Launch
**Needs**:
- `POST /api/agents` - Register new agent
- `GET /api/agents` - List all agents
- `POST /api/projects` - Create project via NLP
- `GET /api/projects` - List all projects
- `POST /api/tasks` - Create task
- `GET /api/tasks` - List tasks

**MVP Provides**: ✅ **PROVIDED** - Week 2 includes all REST endpoints

**Impact**: **NONE** - Fully supported

---

#### Tab 2: 💻 Terminals
**Needs**:
- `GET /api/agents/{agent_id}/terminal/stream` - SSE stream of agent terminal output
- Terminal output capture system
- PTY (pseudo-terminal) management

**MVP Provides**: ✅ **PROVIDED** - Week 2 includes TerminalManager + streaming API

**Impact**: **NONE** - Fully supported

---

#### Tab 3: 📋 Kanban
**Needs**:
- Kanban board integration API (Planka, GitHub, Linear)

**MVP Provides**: ⚠️ **PARTIAL** - Marcus has Kanban integration via MCP tools, but no REST API proxy

**Impact**: **MEDIUM** - Can embed Planka iframe (sufficient for v1.0), REST proxy optional for Week 7

---

#### Tab 4: 📊 Live (Network Graph & Metrics)
**Needs**:
- `GET /api/cato/snapshot` - System state snapshot
- `GET /api/cato/events/stream` - Real-time event stream
- Agent, task, project serialization

**MVP Provides**: ✅ **FULLY PROVIDED** by Week 2

**Impact**: **NONE** - Live tab will work perfectly

---

#### Tab 5: 📚 Historical (Post-Project Analysis)
**Needs**:
- `GET /api/cato/metrics/research` - Research metrics
- `GET /api/cato/metrics/journey` - Journey metrics
- Access to project history files (`~/.marcus/history/{project_id}/`)

**MVP Provides**: ✅ **FULLY PROVIDED** by Week 2 + existing history system

**Impact**: **NONE** - Historical tab will work

---

#### Tab 6: 🌍 Global (Cross-Project Insights)
**Needs**:
- Aggregation logic across multiple projects
- `/api/cato/global/metrics` - System-wide metrics

**MVP Provides**: ⚠️ **PARTIAL** - Can aggregate from `/api/cato/snapshot` calls, but needs dedicated endpoint

**Impact**: **LOW** - Can be implemented in Week 7 on top of existing APIs

---

## Gap Analysis Summary

### CRITICAL Gaps
**NONE** - All critical dependencies provided by new Week 2

### Medium Priority Gaps (Can Address in Week 7)

| Gap | Location | Impact | Recommendation |
|-----|----------|--------|----------------|
| **Kanban REST proxy** | Week 7 | Sub-optimal Kanban UX | Implement during Week 7 Tab 3 work |
| **Global metrics endpoint** | Week 7 | Global tab less efficient | Implement during Week 7 Tab 6 work |

---

## What Was Removed from Original Plan

### Feature Entity & Infrastructure (Original Week 2)
**Why Removed**: Cato dashboard works with project → task → subtask hierarchy. It doesn't need or expect feature entities. The Feature dataclass would add complexity without providing value for the MVP dashboard.

### Git Worktree Workspace Isolation (Original Week 3)
**Why Removed**: Current system with 5 agents working on main branch works fine without conflicts. Git worktrees add complexity that isn't needed yet. Can be added later if scaling to 50+ agents.

### Feature Context Aggregation (Original Week 4)
**Why Removed**: Depends on Feature entities which were removed. Context aggregation for Build Kits can be implemented later when Build Kits development begins (Months 3-4).

### Week 5.5 REST API Completion (Original insertion)
**Why Removed**: Integrated into Week 2. REST APIs and Terminal streaming are now part of the main Telemetry week instead of a separate week.

**Result**: 13-week plan → 8-week plan with same Cato bundling outcome

---

## Original Gap 1: Launch Tab REST APIs (NOW RESOLVED)

**What's Missing**:
```python
# src/api/marcus_routes.py (DOES NOT EXIST IN MVP)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["marcus"])

# Agent Management
@router.post("/agents")
async def register_agent_rest(
    agent_id: str,
    name: str,
    role: str,
    skills: list[str]
) -> dict:
    """REST endpoint for agent registration (wraps MCP tool)."""
    # Calls existing register_agent MCP tool
    pass

@router.get("/agents")
async def list_agents() -> dict:
    """List all registered agents."""
    pass

# Project Management
@router.post("/projects")
async def create_project_rest(
    description: str,
    project_name: str,
    options: dict | None = None
) -> dict:
    """REST endpoint for project creation (wraps create_project MCP tool)."""
    # Calls existing create_project MCP tool
    pass

@router.get("/projects")
async def list_projects() -> dict:
    """List all projects."""
    pass

@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> dict:
    """Get project details."""
    pass

# Task Management
@router.post("/tasks")
async def create_task_rest(
    name: str,
    description: str,
    project_id: str,
    feature_id: str | None = None,
    priority: str = "medium",
    estimated_hours: float = 8.0
) -> dict:
    """REST endpoint for task creation."""
    pass

@router.get("/tasks")
async def list_tasks(
    project_id: str | None = None,
    status: str | None = None
) -> dict:
    """List tasks with optional filters."""
    pass
```

**Why This Is Missing**:
- MVP Week 5 focuses on CATO-specific endpoints (`/api/cato/*`)
- MCP tools exist for these operations but no REST wrappers
- Frontend needs REST endpoints, not MCP protocol

**Solution**: Add these endpoints to Week 5 (extend by 2 days) or create Week 5.5

---

### Gap 2: Terminal Streaming API ❌ CRITICAL

**What's Missing**:
```python
# src/api/terminal_routes.py (DOES NOT EXIST IN MVP)

from fastapi import APIRouter, WebSocket
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/agents", tags=["terminals"])

@router.get("/{agent_id}/terminal/stream")
async def stream_agent_terminal(agent_id: str) -> StreamingResponse:
    """
    Stream agent terminal output via Server-Sent Events.

    Returns
    -------
    StreamingResponse
        SSE stream of terminal output
    """
    async def event_generator():
        terminal_manager = get_terminal_manager()

        while True:
            # Get new output from agent's PTY
            output = await terminal_manager.get_output(agent_id)

            if output:
                yield f"data: {json.dumps({'output': output})}\n\n"

            await asyncio.sleep(0.1)  # 100ms poll interval

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/{agent_id}/terminal/input")
async def send_terminal_input(agent_id: str, input_data: str) -> dict:
    """Send input to agent's terminal (command injection recovery)."""
    terminal_manager = get_terminal_manager()
    await terminal_manager.send_input(agent_id, input_data)
    return {"success": True}
```

**Additionally Needs**:
```python
# src/terminal/manager.py (DOES NOT EXIST IN MVP)

import pty
import os
import asyncio
from typing import Dict, Optional

class TerminalManager:
    """Manages PTY sessions for each agent."""

    def __init__(self):
        self.terminals: Dict[str, TerminalSession] = {}

    async def create_terminal(self, agent_id: str) -> TerminalSession:
        """Create PTY for agent."""
        master, slave = pty.openpty()
        session = TerminalSession(agent_id, master, slave)
        self.terminals[agent_id] = session
        return session

    async def get_output(self, agent_id: str) -> Optional[str]:
        """Read buffered output from agent's PTY."""
        session = self.terminals.get(agent_id)
        if not session:
            return None

        return await session.read_output()

    async def send_input(self, agent_id: str, input_data: str) -> None:
        """Send input to agent's PTY (command injection)."""
        session = self.terminals.get(agent_id)
        if session:
            await session.write_input(input_data)
```

**Why This Is Missing**:
- Terminals tab is a brand new feature not in original Marcus scope
- Requires PTY management infrastructure
- Requires buffering and streaming architecture

**Solution**: Add terminal infrastructure to Week 5.5 (2-3 days of work)

---

### Gap 3: Kanban REST Proxy ⚠️ MEDIUM

**What's Missing**:
```python
# src/api/kanban_routes.py (DOES NOT EXIST IN MVP)

@router.get("/api/kanban/boards")
async def list_kanban_boards() -> dict:
    """List available Kanban boards from configured provider."""
    kanban_client = get_kanban_client()  # Planka, GitHub, Linear
    boards = await kanban_client.list_boards()
    return {"boards": boards}

@router.get("/api/kanban/boards/{board_id}/tasks")
async def get_board_tasks(board_id: str) -> dict:
    """Get tasks from Kanban board."""
    kanban_client = get_kanban_client()
    tasks = await kanban_client.get_tasks(board_id)
    return {"tasks": tasks}
```

**Why This Is Missing**:
- Kanban integration exists in Marcus via MCP tools
- No REST API proxy to expose Kanban data to web dashboard

**Solution**: Can be deferred to Week 11 (Kanban tab implementation). Fallback: embed Planka iframe.

---

### Gap 4: Global Metrics Endpoint ⚠️ LOW

**What's Missing**:
```python
# Addition to src/api/cato_routes.py

@router.get("/api/cato/global/metrics")
async def get_global_metrics() -> dict:
    """
    Get system-wide metrics across all projects.

    Returns
    -------
    dict
        Aggregated metrics from all projects
    """
    state = get_state_manager()

    # Aggregate across all projects
    all_projects = state.projects.values()

    metrics = {
        "total_projects": len(all_projects),
        "total_agents_ever": len(state.agents),
        "total_tasks_completed": sum(
            1 for t in state.tasks.values()
            if t.status == TaskStatus.COMPLETED
        ),
        "cross_project_insights": {
            # Agent performance across projects
            # Common blockers
            # Resource utilization trends
        }
    }

    return {"success": True, "metrics": metrics}
```

**Why This Is Missing**:
- Global tab is a new feature
- Can be built on top of existing `/api/cato/snapshot` by calling it for each project

**Solution**: Implement during Week 7 Tab 6 work. Not a blocker (optional).

---

## Recommendations

### No Action Required

The new 8-week plan provides **100% of critical dependencies** for Cato bundling.

### Updated MVP Timeline

**New 8-Week Structure**:
```
Week 1: Configuration (polish existing)
Week 2: Telemetry & CATO API (includes REST APIs + Terminal streaming)
Week 3: Production Validations & Docker
---
Week 4: Git Submodule Setup (READY - no blockers)
Week 5: Unified Installation
Week 6: Unified Startup
Week 7: Unified Dashboard UI
Week 8: Web Console (optional)
```

**What This Achieves**:
- ✅ All 6 dashboard tabs supported
- ✅ Launch tab: REST APIs in Week 2
- ✅ Terminals tab: Terminal streaming in Week 2
- ✅ Live tab: Event streaming in Week 2
- ✅ Historical tab: Existing history system
- ✅ Kanban tab: Iframe fallback (REST proxy optional)
- ⚠️ Global tab: Can aggregate from existing APIs

---

## Alignment Verification Checklist

Use this checklist to verify alignment before starting Week 4 (Git Submodule):

### Launch Tab Requirements (Week 2 Deliverables)
- [ ] `POST /api/agents` endpoint exists and tested
- [ ] `GET /api/agents` endpoint exists and tested
- [ ] `POST /api/projects` endpoint exists and tested
- [ ] `GET /api/projects` endpoint exists and tested
- [ ] `POST /api/tasks` endpoint exists and tested
- [ ] `GET /api/tasks` endpoint exists and tested

### Terminals Tab Requirements (Week 2 Deliverables)
- [ ] `GET /api/agents/{agent_id}/terminal/stream` endpoint exists
- [ ] `POST /api/agents/{agent_id}/terminal/input` endpoint exists
- [ ] TerminalManager captures agent output
- [ ] Streaming works for multiple agents
- [ ] Command injection tested

### Live Tab Requirements (Week 2 Deliverables)
- [ ] `GET /api/cato/snapshot` exists
- [ ] `GET /api/cato/events/stream` exists

### Historical Tab Requirements (Already Exists)
- [x] `GET /api/cato/metrics/journey` exists
- [x] `GET /api/cato/metrics/research` exists
- [x] Project history system exists

### Kanban Tab Requirements (Deferred to Week 7)
- [ ] Kanban REST proxy (implement in Week 7, or use iframe fallback)

### Global Tab Requirements (Deferred to Week 7)
- [ ] `/api/cato/global/metrics` (implement in Week 7 on top of existing APIs)

---

## Conclusion

**Final Verdict**: ✅ **MVP IS ALIGNED WITH CATO BUNDLING**

**Summary**:
- New 8-week plan provides **100% of critical dependencies**
- **Medium gaps**: Kanban proxy and Global metrics can be deferred to Week 7
- **Removed complexity**: Features, Worktrees, Context not needed for Cato dashboard

**Timeline Comparison**:
- **Original**: 13 weeks (6 weeks MVP + Week 5.5 + 4 weeks Cato + 2 weeks Console)
- **New**: 8 weeks (3 weeks MVP + 4 weeks Cato + 1 week Console)
- **Savings**: 5 weeks removed by eliminating unused features

**Action Items**:
1. ✅ Complete Week 1 polish (1-2 days)
2. ✅ Execute Week 2 Telemetry & APIs (5 days)
3. ✅ Execute Week 3 Validations & Docker (5 days)
4. ✅ Proceed to Week 4 Git Submodule (no blockers)

**Once Week 3 is complete**, MVP will provide **100% of what Cato bundling needs**, with remaining items (Kanban proxy, Global metrics) implementable during Week 7 tab-specific work.

---

**Status**: ✅ **READY TO EXECUTE** - No planning gaps identified

**Last Updated**: 2025-12-21 (Revised for 8-week schedule)

---
---

# HISTORICAL ANALYSIS (Original 13-Week Plan)

The sections below document the original gap analysis from the 13-week plan. These are kept for historical reference only. The current 8-week plan resolves all identified gaps.

---

## Recommendations

### Immediate Action Required: Add Week 5.5

**Insert between Week 5 and Week 6**: **Week 5.5 - REST API Completion (2-3 days)**

#### Day 1: Launch Tab REST APIs
**Goal**: Create REST endpoints that wrap existing MCP tools

**Tasks**:
1. Create `src/api/marcus_routes.py`
2. Implement:
   - `POST /api/agents` (wraps `register_agent` MCP tool)
   - `GET /api/agents`
   - `POST /api/projects` (wraps `create_project` MCP tool)
   - `GET /api/projects`
   - `GET /api/projects/{project_id}`
   - `POST /api/tasks`
   - `GET /api/tasks`
3. Register router in FastAPI app
4. Write tests for all endpoints

**Success Criteria**:
- ✅ All Launch tab endpoints functional
- ✅ Postman/curl can create agents, projects, tasks
- ✅ All tests pass

---

#### Day 2-3: Terminal Streaming Infrastructure
**Goal**: Enable real-time terminal output streaming

**Tasks**:
1. **Day 2 Morning**: Create `src/terminal/manager.py`
   - TerminalManager class
   - PTY session management
   - Output buffering
2. **Day 2 Afternoon**: Create `src/api/terminal_routes.py`
   - `GET /api/agents/{agent_id}/terminal/stream` (SSE endpoint)
   - `POST /api/agents/{agent_id}/terminal/input` (command injection)
3. **Day 3**: Integration and testing
   - Integrate TerminalManager with agent execution
   - Capture agent stdout/stderr to PTY
   - Test streaming with real agent
   - Write unit and integration tests

**Success Criteria**:
- ✅ Agent terminal output streams to dashboard
- ✅ Command injection works for stuck agents
- ✅ Multiple agents can stream simultaneously
- ✅ All tests pass

---

### Updated MVP Timeline

**Before Fix**:
```
Week 1: Configuration
Week 2: Feature Entity
Week 3: Workspace Isolation
Week 4: Feature Context
Week 5: Telemetry & CATO API
Week 6: Validations & Docker
---
Week 8: Git Submodule Setup (BLOCKED - missing APIs)
```

**After Fix**:
```
Week 1: Configuration
Week 2: Feature Entity
Week 3: Workspace Isolation
Week 4: Feature Context
Week 5: Telemetry & CATO API
Week 5.5: REST API Completion (NEW - 2-3 days) ⭐
Week 6: Validations & Docker
---
Week 8: Git Submodule Setup (UNBLOCKED)
Week 9: Unified Installation
Week 10: Unified Startup
Week 11: Unified Dashboard UI
```

---

## Alignment Verification Checklist

Use this checklist to verify alignment before starting Week 8:

### Launch Tab Requirements
- [ ] `POST /api/agents` endpoint exists and tested
- [ ] `GET /api/agents` endpoint exists and tested
- [ ] `POST /api/projects` endpoint exists and tested
- [ ] `GET /api/projects` endpoint exists and tested
- [ ] `POST /api/tasks` endpoint exists and tested
- [ ] `GET /api/tasks` endpoint exists and tested

### Terminals Tab Requirements
- [ ] `GET /api/agents/{agent_id}/terminal/stream` endpoint exists
- [ ] `POST /api/agents/{agent_id}/terminal/input` endpoint exists
- [ ] TerminalManager captures agent output
- [ ] Streaming works for multiple agents
- [ ] Command injection tested

### Live Tab Requirements (Already Met)
- [x] `GET /api/cato/snapshot` exists (Week 5)
- [x] `GET /api/cato/events/stream` exists (Week 5)

### Historical Tab Requirements (Already Met)
- [x] `GET /api/cato/metrics/journey` exists (Week 5)
- [x] `GET /api/cato/metrics/research` exists (Week 5)
- [x] Project history system exists

### Kanban Tab Requirements (Deferred)
- [ ] Kanban REST proxy (implement in Week 11, or use iframe fallback)

### Global Tab Requirements (Deferred)
- [ ] `/api/cato/global/metrics` (implement in Week 11 on top of existing APIs)

---

## Conclusion

**Final Verdict**: ⚠️ **MVP REQUIRES ADDITIONS**

**Summary**:
- MVP provides **60% of what CATO bundling needs**
- **Critical gaps**: Launch tab REST APIs and Terminal streaming
- **Solution**: Add **Week 5.5 (2-3 days)** to implement missing pieces
- **Medium gaps**: Kanban proxy and Global metrics can be deferred to Week 11

**Action Items**:
1. ✅ Approve Week 5.5 addition to timeline
2. ✅ Update WEEK_5_PLAN.md to include REST API endpoints
3. ✅ Create WEEK_5.5_PLAN.md for terminal streaming
4. ✅ Update DEVELOPMENT_GUIDE.md with Week 5.5
5. ✅ Verify all dependencies before Week 8

**Once Week 5.5 is complete**, MVP will provide **95% of what CATO bundling needs**, with remaining 5% (Kanban proxy, Global metrics) implementable during Week 11 tab-specific work.

---

**Status**: ⏳ **Week 5.5 needs to be planned and added to MVP**

**Last Updated**: 2025-11-11
