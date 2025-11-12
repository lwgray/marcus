# MVP → CATO Bundling Alignment Evaluation

**Date**: 2025-11-11
**Evaluator**: Development team
**Purpose**: Ensure MVP (Weeks 1-6) provides exactly what CATO Bundling (Weeks 8-11) needs

---

## Executive Summary

**Status**: ⚠️ **CRITICAL GAPS IDENTIFIED** - MVP requires additions to support CATO bundling

**Key Findings**:
- ✅ **Live Tab**: Fully supported by MVP Week 5 CATO API endpoints
- ⚠️ **Launch Tab**: Missing REST API endpoints (only MCP tools exist)
- ❌ **Terminals Tab**: Terminal streaming API completely missing from MVP
- ⚠️ **Kanban Tab**: Depends on external Kanban provider (not Marcus responsibility)
- ✅ **Historical Tab**: Supported by existing project history system
- ⚠️ **Global Tab**: Can be built on existing APIs, but needs aggregation logic

**Recommendation**: **Add Week 5.5 (2-3 days)** to implement missing REST APIs before Week 6

---

## What MVP (Weeks 1-6) Builds

### Week 1: Configuration System
**Deliverables**:
- Type-safe configuration with dataclass validation
- Environment variable override support
- Single source of truth for settings

**Relevance to CATO**: ✅ Foundation for configuring dashboard port, features

---

### Week 2: Feature Entity & Infrastructure
**Deliverables**:
- Project and Feature dataclasses
- Feature-aware artifact and decision logging
- Feature indexing system
- WorkspaceManager skeleton

**Relevance to CATO**: ✅ Data models that CATO dashboard will visualize

---

### Week 3: Workspace Isolation (Git Worktrees)
**Deliverables**:
- GitOperations for safe git command execution
- WorkspaceManager with worktree creation/cleanup
- Workspace conflict prevention
- Integration with task assignment

**Relevance to CATO**: ✅ Enables parallel agent execution (visible in Live tab)

---

### Week 4: Feature Context Aggregation
**Deliverables**:
- CommitTracker for git commit tracking by task_id and feature_id
- Feature context aggregation (tasks + artifacts + decisions + commits)
- Git commit tracking and annotation

**Relevance to CATO**: ✅ Provides rich context for Historical tab retrospectives

---

### Week 5: Telemetry & CATO API Integration ⭐
**Deliverables**:
- User journey tracking (JourneyMilestone, AuditLogger)
- Research event logging (ResearchEventLogger)
- **CATO API Endpoints**:
  - ✅ `GET /api/cato/snapshot` - System snapshot (agents, tasks, projects, features)
  - ✅ `GET /api/cato/events/stream` - Real-time SSE event stream
  - ✅ `GET /api/cato/metrics/journey` - User journey metrics
  - ✅ `GET /api/cato/metrics/research` - Research-grade MAS metrics
  - ✅ `GET /api/cato/agent/{agent_id}` - Agent detail view

**Relevance to CATO**: ✅ **CRITICAL** - Powers Live tab and Historical tab

---

### Week 6: Production Readiness
**Deliverables**:
- Validation framework (TaskValidator, ProjectValidator)
- Core validations (#118-125)
- Docker multi-stage builds
- Comprehensive documentation

**Relevance to CATO**: ✅ Production deployment infrastructure

---

## What CATO Bundling (Weeks 8-11) Needs

### Week 8: Git Submodule Setup
**Requirements**:
- Marcus must be functional with working MCP server
- CATO API endpoints must exist for integration testing

**MVP Provides**: ✅ Yes (if missing APIs are added in Week 5.5)

---

### Week 9: Unified Installation
**Requirements**:
- Marcus installable via `pip install marcus`
- All dependencies manageable via Python packaging

**MVP Provides**: ✅ Yes (Week 1 configuration + Week 6 Docker)

---

### Week 10: Unified Startup
**Requirements**:
- Marcus MCP Server launchable on port 4298
- Cato Backend can connect to Marcus APIs

**MVP Provides**: ✅ Yes (Marcus MCP server exists, API endpoints in Week 5)

---

### Week 11: Unified Dashboard UI
**Requirements by Tab**:

#### Tab 1: 🚀 Launch
**Needs**:
- `POST /api/agents` - Register new agent
- `GET /api/agents` - List all agents
- `POST /api/projects` - Create project via NLP
- `GET /api/projects` - List all projects
- `POST /api/tasks` - Create task
- `GET /api/tasks` - List tasks

**MVP Provides**: ❌ **MISSING** - Only MCP tools exist (`register_agent`, `create_project`), no REST endpoints

**Impact**: **CRITICAL** - Launch tab cannot function without these APIs

---

#### Tab 2: 💻 Terminals
**Needs**:
- `GET /api/agents/{agent_id}/terminal/stream` - WebSocket or SSE stream of agent terminal output
- Terminal output capture system
- PTY (pseudo-terminal) management

**MVP Provides**: ❌ **COMPLETELY MISSING** - No terminal streaming in MVP

**Impact**: **CRITICAL** - Terminals tab cannot function

---

#### Tab 3: 📋 Kanban
**Needs**:
- Kanban board integration API (Planka, GitHub, Linear)

**MVP Provides**: ⚠️ **PARTIAL** - Marcus has Kanban integration via MCP tools, but no REST API proxy

**Impact**: **MEDIUM** - Can embed Planka iframe, but ideal UX needs REST proxy

---

#### Tab 4: 📊 Live (Network Graph & Metrics)
**Needs**:
- `GET /api/cato/snapshot` - System state snapshot
- `GET /api/cato/events/stream` - Real-time event stream
- Agent, task, project, feature serialization

**MVP Provides**: ✅ **FULLY PROVIDED** by Week 5

**Impact**: **NONE** - Live tab will work perfectly

---

#### Tab 5: 📚 Historical (Post-Project Analysis)
**Needs**:
- `GET /api/cato/metrics/research` - Research metrics
- `GET /api/cato/metrics/journey` - Journey metrics
- Access to project history files (`~/.marcus/history/{project_id}/`)

**MVP Provides**: ✅ **FULLY PROVIDED** by Week 5 + existing history system

**Impact**: **NONE** - Historical tab will work

---

#### Tab 6: 🌍 Global (Cross-Project Insights)
**Needs**:
- Aggregation logic across multiple projects
- `/api/cato/global/metrics` - System-wide metrics

**MVP Provides**: ⚠️ **PARTIAL** - Can aggregate from `/api/cato/snapshot` calls, but needs dedicated endpoint

**Impact**: **LOW** - Can be implemented in Week 11 on top of existing APIs

---

## Gap Analysis Summary

### CRITICAL Gaps (Must Fix Before Week 8)

| Gap | Location | Impact | Recommendation |
|-----|----------|--------|----------------|
| **REST API for Launch Tab** | MVP Week 5 | Launch tab non-functional | Add Week 5.5 (2 days) |
| **Terminal Streaming API** | MVP Week 5 | Terminals tab non-functional | Add Week 5.5 (2 days) |

### Medium Priority Gaps (Can Address in Week 11)

| Gap | Location | Impact | Recommendation |
|-----|----------|--------|----------------|
| **Kanban REST proxy** | Week 11 | Sub-optimal Kanban UX | Implement during Week 11 Tab 3 work |
| **Global metrics endpoint** | Week 11 | Global tab less efficient | Implement during Week 11 Tab 6 work |

---

## Detailed Gap Specifications

### Gap 1: Launch Tab REST APIs ❌ CRITICAL

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

**Solution**: Implement during Week 11 Tab 6 work. Not a blocker.

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
