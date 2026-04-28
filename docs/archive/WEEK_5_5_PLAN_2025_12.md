# Week 5.5: REST API Completion & Terminal Streaming

**Duration**: 2-3 days
**Goal**: Add missing REST APIs for CATO dashboard integration
**Why This Week Exists**: CATO unified dashboard needs REST endpoints for Launch tab and Terminals tab. Week 5 implemented `/api/cato/*` endpoints for Live/Historical tabs, but Launch and Terminals tabs need additional APIs.

**Critical For**: CATO Bundling (Weeks 8-11) - without these APIs, 2 out of 6 dashboard tabs cannot function

---

## Overview

### What You're Building

1. **Launch Tab REST APIs** - HTTP endpoints for agent registration, project creation, task management
2. **Terminal Streaming Infrastructure** - Real-time terminal output streaming for agent monitoring

### Why These Are Missing from Week 5

Week 5 focused on CATO-specific visualization endpoints (`/api/cato/snapshot`, `/api/cato/events/stream`). Those endpoints serve the Live and Historical tabs.

However, the unified dashboard also has:
- **Launch Tab**: Needs REST APIs to register agents, create projects, manage tasks
- **Terminals Tab**: Needs terminal streaming to show live agent output

Marcus currently only has MCP tools for these operations (not REST endpoints), and has no terminal streaming at all.

---

## Day 1: Launch Tab REST APIs

### Goal

Create REST endpoints that wrap existing MCP tools so the CATO web dashboard can call them via HTTP.

### Background

The Launch tab UI needs to:
- Register new agents
- List all agents
- Create projects via natural language
- List all projects
- Create tasks
- List tasks with filters

Marcus already has MCP tools for these operations (`register_agent`, `create_project`), but the web dashboard needs REST endpoints.

---

### Step 1.1: Create Marcus REST API Routes

Create `src/api/marcus_routes.py`:

```python
"""
Marcus REST API Routes for Launch Tab.

Provides REST endpoints for agent registration, project creation,
and task management. These wrap existing MCP tools.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.core.error_responses import handle_mcp_tool_error
from src.core.models import Priority, TaskStatus
from src.state.manager import get_state_manager

router = APIRouter(prefix="/api", tags=["marcus"])


# ========================================
# Agent Management
# ========================================

class RegisterAgentRequest(BaseModel):
    """Request model for agent registration."""
    agent_id: str
    name: str
    role: str
    skills: List[str] = []


@router.post("/agents")
async def register_agent_rest(request: RegisterAgentRequest) -> Dict[str, Any]:
    """
    Register a new agent (REST wrapper for register_agent MCP tool).

    Parameters
    ----------
    request : RegisterAgentRequest
        Agent registration data.

    Returns
    -------
    Dict[str, Any]
        Registration result.

    Examples
    --------
    POST /api/agents
    {
        "agent_id": "agent-1",
        "name": "Builder Agent",
        "role": "developer",
        "skills": ["python", "fastapi"]
    }

    Response:
    {
        "success": true,
        "agent_id": "agent-1",
        "message": "Agent Builder Agent registered"
    }
    """
    try:
        from src.marcus_mcp.tools.core import register_agent

        state = get_state_manager()

        result = await register_agent(
            agent_id=request.agent_id,
            name=request.name,
            role=request.role,
            skills=request.skills,
            state=state
        )

        return result

    except Exception as e:
        return handle_mcp_tool_error(e, "register_agent", request.dict())


@router.get("/agents")
async def list_agents() -> Dict[str, Any]:
    """
    List all registered agents.

    Returns
    -------
    Dict[str, Any]
        List of agents with their details.

    Examples
    --------
    GET /api/agents

    Response:
    {
        "success": true,
        "agents": [
            {
                "agent_id": "agent-1",
                "name": "Builder Agent",
                "role": "developer",
                "status": "active",
                "current_task_id": "T-123",
                "skills": ["python", "fastapi"]
            }
        ],
        "count": 1
    }
    """
    try:
        state = get_state_manager()

        agents = [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "role": agent.role,
                "status": agent.status,
                "current_task_id": agent.current_task_id,
                "skills": agent.skills,
                "task_count": len(agent.task_history)
            }
            for agent in state.agents.values()
        ]

        return {
            "success": True,
            "agents": agents,
            "count": len(agents)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> Dict[str, Any]:
    """
    Get details for a specific agent.

    Parameters
    ----------
    agent_id : str
        The agent ID.

    Returns
    -------
    Dict[str, Any]
        Agent details.
    """
    try:
        state = get_state_manager()

        if agent_id not in state.agents:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        agent = state.agents[agent_id]

        return {
            "success": True,
            "agent": {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "role": agent.role,
                "status": agent.status,
                "current_task_id": agent.current_task_id,
                "skills": agent.skills,
                "task_history": agent.task_history[-10:]  # Last 10 tasks
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# Project Management
# ========================================

class CreateProjectRequest(BaseModel):
    """Request model for project creation."""
    description: str
    project_name: str
    options: Optional[Dict[str, Any]] = None


@router.post("/projects")
async def create_project_rest(request: CreateProjectRequest) -> Dict[str, Any]:
    """
    Create a new project from natural language description.

    Parameters
    ----------
    request : CreateProjectRequest
        Project creation data.

    Returns
    -------
    Dict[str, Any]
        Project creation result.

    Examples
    --------
    POST /api/projects
    {
        "description": "Build a REST API for user management with FastAPI",
        "project_name": "User Management API",
        "options": {
            "complexity": "standard"
        }
    }

    Response:
    {
        "success": true,
        "project_id": "proj-123",
        "tasks_created": 15,
        "board_url": "http://planka.local/boards/456"
    }
    """
    try:
        from src.marcus_mcp.tools.project import create_project

        state = get_state_manager()

        result = await create_project(
            description=request.description,
            project_name=request.project_name,
            options=request.options or {},
            state=state
        )

        return result

    except Exception as e:
        return handle_mcp_tool_error(e, "create_project", request.dict())


@router.get("/projects")
async def list_projects() -> Dict[str, Any]:
    """
    List all projects.

    Returns
    -------
    Dict[str, Any]
        List of projects.

    Examples
    --------
    GET /api/projects

    Response:
    {
        "success": true,
        "projects": [
            {
                "project_id": "proj-123",
                "name": "User Management API",
                "status": "in_progress",
                "task_count": 15,
                "completed_tasks": 3
            }
        ],
        "count": 1
    }
    """
    try:
        state = get_state_manager()

        projects = [
            {
                "project_id": project.project_id,
                "name": project.name,
                "status": project.status,
                "task_count": len(project.task_ids),
                "created_at": project.created_at
            }
            for project in state.projects.values()
        ]

        return {
            "success": True,
            "projects": projects,
            "count": len(projects)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> Dict[str, Any]:
    """
    Get details for a specific project.

    Parameters
    ----------
    project_id : str
        The project ID.

    Returns
    -------
    Dict[str, Any]
        Project details including tasks and features.
    """
    try:
        state = get_state_manager()

        if project_id not in state.projects:
            raise HTTPException(
                status_code=404,
                detail=f"Project {project_id} not found"
            )

        project = state.projects[project_id]

        # Get project tasks
        tasks = [
            state.tasks[task_id]
            for task_id in project.task_ids
            if task_id in state.tasks
        ]

        # Get project features
        features = [
            feature for feature in state.features.values()
            if feature.project_id == project_id
        ]

        return {
            "success": True,
            "project": {
                "project_id": project.project_id,
                "name": project.name,
                "status": project.status,
                "task_count": len(tasks),
                "completed_tasks": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
                "features": [
                    {
                        "feature_id": f.feature_id,
                        "name": f.feature_name,
                        "status": f.status
                    }
                    for f in features
                ],
                "created_at": project.created_at
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# Task Management
# ========================================

class CreateTaskRequest(BaseModel):
    """Request model for task creation."""
    name: str
    description: str
    project_id: str
    feature_id: Optional[str] = None
    priority: str = "medium"
    estimated_hours: float = 8.0
    dependencies: List[str] = []


@router.post("/tasks")
async def create_task_rest(request: CreateTaskRequest) -> Dict[str, Any]:
    """
    Create a new task.

    Parameters
    ----------
    request : CreateTaskRequest
        Task creation data.

    Returns
    -------
    Dict[str, Any]
        Task creation result.

    Examples
    --------
    POST /api/tasks
    {
        "name": "Implement user registration endpoint",
        "description": "Create POST /api/users endpoint with validation",
        "project_id": "proj-123",
        "feature_id": "F-100",
        "priority": "high",
        "estimated_hours": 4.0
    }

    Response:
    {
        "success": true,
        "task_id": "T-IMPL-1",
        "message": "Task created successfully"
    }
    """
    try:
        from src.core.models import Task

        state = get_state_manager()

        # Validate project exists
        if request.project_id not in state.projects:
            raise HTTPException(
                status_code=404,
                detail=f"Project {request.project_id} not found"
            )

        # Validate feature exists (if provided)
        if request.feature_id and request.feature_id not in state.features:
            raise HTTPException(
                status_code=404,
                detail=f"Feature {request.feature_id} not found"
            )

        # Generate task ID
        task_count = len([t for t in state.tasks.values() if t.project_id == request.project_id])
        task_id = f"T-IMPL-{task_count + 1}"

        # Create task
        task = Task(
            id=task_id,
            name=request.name,
            description=request.description,
            status=TaskStatus.TODO,
            priority=Priority(request.priority.lower()),
            estimated_hours=request.estimated_hours,
            labels=[],
            dependencies=request.dependencies,
            project_id=request.project_id,
            feature_id=request.feature_id
        )

        state.tasks[task_id] = task

        # Add to project
        project = state.projects[request.project_id]
        project.task_ids.append(task_id)

        return {
            "success": True,
            "task_id": task_id,
            "message": "Task created successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def list_tasks(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    List tasks with optional filters.

    Parameters
    ----------
    project_id : Optional[str]
        Filter by project ID.
    status : Optional[str]
        Filter by status (todo, in_progress, completed, blocked).
    assigned_to : Optional[str]
        Filter by assigned agent.

    Returns
    -------
    Dict[str, Any]
        List of tasks.

    Examples
    --------
    GET /api/tasks?project_id=proj-123&status=todo

    Response:
    {
        "success": true,
        "tasks": [
            {
                "task_id": "T-IMPL-1",
                "name": "Implement user registration",
                "status": "todo",
                "priority": "high",
                "assigned_to": null,
                "estimated_hours": 4.0
            }
        ],
        "count": 1
    }
    """
    try:
        state = get_state_manager()

        tasks = list(state.tasks.values())

        # Apply filters
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]

        if status:
            tasks = [t for t in tasks if t.status.value == status.lower()]

        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]

        task_list = [
            {
                "task_id": task.id,
                "name": task.name,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority.value,
                "assigned_to": task.assigned_to,
                "estimated_hours": task.estimated_hours,
                "dependencies": task.dependencies,
                "project_id": task.project_id,
                "feature_id": task.feature_id
            }
            for task in tasks
        ]

        return {
            "success": True,
            "tasks": task_list,
            "count": len(task_list)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### Step 1.2: Register Routes in FastAPI App

Update `src/api/main.py`:

```python
"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.cato_routes import router as cato_router
from src.api.marcus_routes import router as marcus_router  # NEW

app = FastAPI(title="Marcus API", version="0.1.0")

# Enable CORS for CATO dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(cato_router)
app.include_router(marcus_router)  # NEW


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
```

---

### Step 1.3: Write Tests

Create `tests/unit/api/test_marcus_routes.py`:

```python
"""
Tests for Marcus REST API routes.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock, patch

from src.api.main import app


class TestMarcusRoutes:
    """Test Marcus REST API routes"""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_state(self):
        """Create mock state."""
        from src.core.models import Agent, Project, Task, TaskStatus, Priority

        state = Mock()
        state.agents = {
            "agent-1": Agent(
                agent_id="agent-1",
                name="Test Agent",
                role="developer",
                status="active",
                current_task_id=None,
                task_history=[],
                skills=["python"]
            )
        }
        state.projects = {}
        state.tasks = {}
        state.features = {}

        return state

    @patch('src.api.marcus_routes.get_state_manager')
    def test_list_agents(self, mock_get_state, client, mock_state):
        """Test listing agents."""
        mock_get_state.return_value = mock_state

        response = client.get("/api/agents")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 1
        assert data["agents"][0]["agent_id"] == "agent-1"

    @patch('src.api.marcus_routes.get_state_manager')
    @patch('src.marcus_mcp.tools.core.register_agent')
    async def test_register_agent(self, mock_register, mock_get_state, client, mock_state):
        """Test registering agent via REST."""
        mock_get_state.return_value = mock_state
        mock_register.return_value = {"success": True, "agent_id": "agent-2"}

        response = client.post("/api/agents", json={
            "agent_id": "agent-2",
            "name": "New Agent",
            "role": "tester",
            "skills": ["pytest"]
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
```

Run tests:
```bash
pytest tests/unit/api/test_marcus_routes.py -v
```

---

### Success Criteria for Day 1

- ✅ All Launch tab REST APIs implemented
- ✅ Routes registered in FastAPI app
- ✅ CORS configured for dashboard
- ✅ All tests pass
- ✅ Can call APIs via curl/Postman:
  ```bash
  # Register agent
  curl -X POST http://localhost:4301/api/agents \
    -H "Content-Type: application/json" \
    -d '{"agent_id": "agent-1", "name": "Test", "role": "dev", "skills": []}'

  # List agents
  curl http://localhost:4301/api/agents

  # Create project
  curl -X POST http://localhost:4301/api/projects \
    -H "Content-Type: application/json" \
    -d '{"description": "Build API", "project_name": "Test Project"}'
  ```

---

## Day 2-3: Terminal Streaming Infrastructure

### Goal

Enable real-time streaming of agent terminal output to CATO dashboard Terminals tab.

### Background

The Terminals tab needs to show live output from agents as they work. This requires:
1. **PTY (Pseudo-Terminal) Management** - Capture agent stdout/stderr
2. **Buffering** - Store output until dashboard requests it
3. **Streaming API** - Server-Sent Events endpoint to stream output
4. **Command Injection** - Ability to send commands to stuck agents

---

### Day 2 Morning: Terminal Manager

Create `src/terminal/manager.py`:

```python
"""
Terminal manager for agent output streaming.

Manages pseudo-terminal (PTY) sessions for each agent to capture
their terminal output in real-time.
"""

import asyncio
import logging
import os
import pty
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class TerminalSession:
    """
    A terminal session for an agent.

    Attributes
    ----------
    agent_id : str
        Agent identifier
    master_fd : int
        Master file descriptor for PTY
    slave_fd : int
        Slave file descriptor for PTY
    output_buffer : deque
        Buffered output lines
    created_at : str
        ISO timestamp of session creation
    """

    agent_id: str
    master_fd: int
    slave_fd: int
    output_buffer: deque
    created_at: str


class TerminalManager:
    """
    Manages terminal sessions for agents.

    Each agent gets a PTY session that captures stdout/stderr.
    Output is buffered and streamed to dashboard via SSE.

    Examples
    --------
    >>> manager = TerminalManager()
    >>> session = await manager.create_terminal("agent-1")
    >>> output = await manager.get_output("agent-1")
    >>> print(output)
    """

    def __init__(self, buffer_size: int = 1000):
        """
        Initialize terminal manager.

        Parameters
        ----------
        buffer_size : int
            Max number of output lines to buffer per agent.
        """
        self.buffer_size = buffer_size
        self.sessions: Dict[str, TerminalSession] = {}
        self._readers: Dict[str, asyncio.Task] = {}

    async def create_terminal(self, agent_id: str) -> TerminalSession:
        """
        Create PTY session for agent.

        Parameters
        ----------
        agent_id : str
            Agent identifier.

        Returns
        -------
        TerminalSession
            Created session.
        """
        if agent_id in self.sessions:
            logger.warning(f"Terminal already exists for {agent_id}")
            return self.sessions[agent_id]

        # Create PTY
        master_fd, slave_fd = pty.openpty()

        # Create session
        session = TerminalSession(
            agent_id=agent_id,
            master_fd=master_fd,
            slave_fd=slave_fd,
            output_buffer=deque(maxlen=self.buffer_size),
            created_at=datetime.now(timezone.utc).isoformat()
        )

        self.sessions[agent_id] = session

        # Start reader task
        reader_task = asyncio.create_task(self._read_output(agent_id))
        self._readers[agent_id] = reader_task

        logger.info(f"Created terminal session for {agent_id}")
        return session

    async def _read_output(self, agent_id: str) -> None:
        """
        Read output from PTY in background task.

        Parameters
        ----------
        agent_id : str
            Agent identifier.
        """
        session = self.sessions.get(agent_id)
        if not session:
            return

        try:
            while True:
                # Read from master FD (non-blocking)
                try:
                    data = os.read(session.master_fd, 1024)
                    if data:
                        # Decode and buffer
                        text = data.decode("utf-8", errors="replace")
                        lines = text.split("\n")

                        for line in lines:
                            if line.strip():
                                session.output_buffer.append({
                                    "line": line,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                })

                except OSError:
                    # No data available
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            # Task cancelled during cleanup
            logger.info(f"Reader task cancelled for {agent_id}")

    async def get_output(
        self,
        agent_id: str,
        last_n_lines: Optional[int] = None
    ) -> list[dict]:
        """
        Get buffered output from agent terminal.

        Parameters
        ----------
        agent_id : str
            Agent identifier.
        last_n_lines : Optional[int]
            Number of recent lines to return. If None, return all.

        Returns
        -------
        list[dict]
            List of output line dictionaries with 'line' and 'timestamp'.
        """
        session = self.sessions.get(agent_id)
        if not session:
            return []

        if last_n_lines:
            # Get last N lines
            buffer_list = list(session.output_buffer)
            return buffer_list[-last_n_lines:]
        else:
            # Get all buffered lines
            return list(session.output_buffer)

    async def send_input(self, agent_id: str, input_data: str) -> None:
        """
        Send input to agent's terminal (command injection for recovery).

        Parameters
        ----------
        agent_id : str
            Agent identifier.
        input_data : str
            Input to send (command).
        """
        session = self.sessions.get(agent_id)
        if not session:
            raise ValueError(f"No terminal session for agent {agent_id}")

        # Write to slave FD
        input_bytes = (input_data + "\n").encode("utf-8")
        os.write(session.slave_fd, input_bytes)

        logger.info(f"Sent input to {agent_id}: {input_data}")

    async def close_terminal(self, agent_id: str) -> None:
        """
        Close terminal session for agent.

        Parameters
        ----------
        agent_id : str
            Agent identifier.
        """
        session = self.sessions.get(agent_id)
        if not session:
            return

        # Cancel reader task
        if agent_id in self._readers:
            self._readers[agent_id].cancel()
            del self._readers[agent_id]

        # Close file descriptors
        try:
            os.close(session.master_fd)
            os.close(session.slave_fd)
        except OSError:
            pass

        # Remove session
        del self.sessions[agent_id]

        logger.info(f"Closed terminal session for {agent_id}")

    def get_active_sessions(self) -> list[str]:
        """Get list of agent IDs with active terminal sessions."""
        return list(self.sessions.keys())


# Global instance
_terminal_manager: Optional[TerminalManager] = None


def get_terminal_manager() -> TerminalManager:
    """Get global terminal manager instance."""
    global _terminal_manager
    if _terminal_manager is None:
        _terminal_manager = TerminalManager()
    return _terminal_manager
```

---

### Day 2 Afternoon: Terminal Streaming API

Create `src/api/terminal_routes.py`:

```python
"""
Terminal streaming API routes.

Provides real-time terminal output streaming for CATO Terminals tab.
"""

import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.terminal.manager import get_terminal_manager

router = APIRouter(prefix="/api/agents", tags=["terminals"])


@router.get("/{agent_id}/terminal/stream")
async def stream_agent_terminal(agent_id: str) -> StreamingResponse:
    """
    Stream agent terminal output via Server-Sent Events.

    Parameters
    ----------
    agent_id : str
        Agent identifier.

    Returns
    -------
    StreamingResponse
        SSE stream of terminal output.

    Examples
    --------
    Client-side (JavaScript):
    ```javascript
    const eventSource = new EventSource('/api/agents/agent-1/terminal/stream');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data.line);
    };
    ```
    """
    terminal_manager = get_terminal_manager()

    # Create terminal if doesn't exist
    if agent_id not in terminal_manager.get_active_sessions():
        await terminal_manager.create_terminal(agent_id)

    async def event_generator():
        """Generate SSE events from terminal output."""
        last_position = 0

        while True:
            try:
                # Get new output since last position
                all_output = await terminal_manager.get_output(agent_id)

                # Send new lines
                new_lines = all_output[last_position:]
                for line_data in new_lines:
                    yield f"data: {json.dumps(line_data)}\n\n"

                last_position = len(all_output)

                # Keep-alive
                await asyncio.sleep(0.5)

            except Exception as e:
                # Send error and stop
                error_event = {
                    "error": str(e),
                    "type": "error"
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class SendInputRequest(BaseModel):
    """Request model for sending terminal input."""
    input: str


@router.post("/{agent_id}/terminal/input")
async def send_terminal_input(
    agent_id: str,
    request: SendInputRequest
) -> Dict[str, Any]:
    """
    Send input to agent's terminal (command injection for recovery).

    Parameters
    ----------
    agent_id : str
        Agent identifier.
    request : SendInputRequest
        Input data.

    Returns
    -------
    Dict[str, Any]
        Success response.

    Examples
    --------
    POST /api/agents/agent-1/terminal/input
    {
        "input": "CTRL+C"
    }

    Response:
    {
        "success": true,
        "message": "Input sent to agent-1"
    }
    """
    terminal_manager = get_terminal_manager()

    if agent_id not in terminal_manager.get_active_sessions():
        raise HTTPException(
            status_code=404,
            detail=f"No terminal session for agent {agent_id}"
        )

    try:
        await terminal_manager.send_input(agent_id, request.input)

        return {
            "success": True,
            "message": f"Input sent to {agent_id}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/terminal/output")
async def get_terminal_output(
    agent_id: str,
    last_n_lines: Optional[int] = Query(100)
) -> Dict[str, Any]:
    """
    Get recent terminal output (non-streaming).

    Parameters
    ----------
    agent_id : str
        Agent identifier.
    last_n_lines : Optional[int]
        Number of recent lines to return.

    Returns
    -------
    Dict[str, Any]
        Terminal output.
    """
    terminal_manager = get_terminal_manager()

    if agent_id not in terminal_manager.get_active_sessions():
        # Create terminal if it doesn't exist
        await terminal_manager.create_terminal(agent_id)

    output = await terminal_manager.get_output(agent_id, last_n_lines)

    return {
        "success": True,
        "agent_id": agent_id,
        "output": output,
        "line_count": len(output)
    }
```

Register in `src/api/main.py`:

```python
from src.api.terminal_routes import router as terminal_router

app.include_router(terminal_router)
```

---

### Day 3: Integration & Testing

#### Step 3.1: Integrate with Agent Execution

When agents execute tasks, redirect their output to terminal:

```python
# In src/marcus_mcp/tools/core.py

from src.terminal.manager import get_terminal_manager

async def request_next_task(agent_id: str, state: Any) -> dict:
    """Assign task and set up terminal capture."""
    # ... existing task assignment logic ...

    # Create terminal session for agent
    terminal_manager = get_terminal_manager()
    await terminal_manager.create_terminal(agent_id)

    return {"success": True, "task": task_data}
```

#### Step 3.2: Write Tests

Create `tests/unit/terminal/test_manager.py`:

```python
"""Tests for TerminalManager."""

import pytest
import asyncio

from src.terminal.manager import TerminalManager


class TestTerminalManager:
    """Test TerminalManager"""

    @pytest.fixture
    def manager(self):
        """Create TerminalManager."""
        return TerminalManager()

    @pytest.mark.asyncio
    async def test_create_terminal(self, manager):
        """Test creating terminal session."""
        session = await manager.create_terminal("agent-1")

        assert session.agent_id == "agent-1"
        assert "agent-1" in manager.get_active_sessions()

    @pytest.mark.asyncio
    async def test_get_output(self, manager):
        """Test getting terminal output."""
        await manager.create_terminal("agent-1")

        # Should start empty
        output = await manager.get_output("agent-1")
        assert len(output) == 0

    @pytest.mark.asyncio
    async def test_close_terminal(self, manager):
        """Test closing terminal."""
        await manager.create_terminal("agent-1")
        await manager.close_terminal("agent-1")

        assert "agent-1" not in manager.get_active_sessions()
```

Run tests:
```bash
pytest tests/unit/terminal/ -v
```

---

### Success Criteria for Days 2-3

- ✅ TerminalManager implemented and tested
- ✅ SSE streaming endpoint functional
- ✅ Command injection endpoint working
- ✅ Integration with agent execution
- ✅ All tests pass
- ✅ Can test with curl:
  ```bash
  # Stream terminal output
  curl -N http://localhost:4301/api/agents/agent-1/terminal/stream

  # Send input (command injection)
  curl -X POST http://localhost:4301/api/agents/agent-1/terminal/input \
    -H "Content-Type: application/json" \
    -d '{"input": "ls -la"}'
  ```

---

## Week 5.5 Complete

### Deliverables

1. ✅ **Launch Tab REST APIs**
   - Agent registration: `POST /api/agents`
   - Agent listing: `GET /api/agents`
   - Project creation: `POST /api/projects`
   - Project listing: `GET /api/projects`
   - Task creation: `POST /api/tasks`
   - Task listing: `GET /api/tasks`

2. ✅ **Terminal Streaming Infrastructure**
   - TerminalManager with PTY sessions
   - SSE streaming: `GET /api/agents/{agent_id}/terminal/stream`
   - Command injection: `POST /api/agents/{agent_id}/terminal/input`
   - Output buffering and retrieval

### Impact on CATO Bundling

**Before Week 5.5**: 2 out of 6 dashboard tabs non-functional (Launch, Terminals)

**After Week 5.5**: All 6 dashboard tabs ready for integration
- ✅ Launch Tab: Can register agents, create projects, manage tasks
- ✅ Terminals Tab: Can stream real-time agent output
- ✅ Kanban Tab: Can embed Kanban provider (Week 11)
- ✅ Live Tab: Powered by Week 5 `/api/cato/snapshot`
- ✅ Historical Tab: Powered by Week 5 research metrics
- ✅ Global Tab: Can be built on existing APIs (Week 11)

---

## Next Steps

After completing Week 5.5, proceed to:
- **Week 6**: Production validations and Docker (as planned)
- **Week 8**: Git submodule setup (no longer blocked)

---

**Status**: ⏳ Not Started
**Estimated Duration**: 2-3 days
**Priority**: CRITICAL for CATO bundling
