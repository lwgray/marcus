# Marcus Web Console - Implementation Plan

## Overview

Build a web-based experiment dashboard for Marcus that allows developers to:
1. Configure experiments with optimal agent counts
2. Launch multiple AI coding agents (Claude, Cursor, Amp, etc.) in web terminals
3. Monitor agent health and automatically recover stuck agents
4. Track experiment progress in real-time

**Target Users**: Developers testing Marcus changes locally
**Tech Stack**: Python (FastAPI backend) + HTML/JS (frontend) + xterm.js (terminals)
**OS Support**: Linux, macOS, Windows

---

## Phase 1: Backend Foundation (Week 1)

### Goal
Create a FastAPI server that manages experiments and terminal sessions.

### Tasks

#### 1.1 Project Setup
**File**: `dev-tools/web-console/backend/pyproject.toml`

```toml
[project]
name = "marcus-web-console"
version = "0.1.0"
description = "Web-based experiment dashboard for Marcus"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pyyaml>=6.0",
    "psutil>=5.9.0",  # For process monitoring
    "pywinpty>=2.0.0; platform_system=='Windows'",
]

[project.scripts]
marcus-web-console = "marcus_web_console.server:main"
```

**What to do**:
1. Create `dev-tools/web-console/backend/` directory
2. Create the `pyproject.toml` file above
3. Create `marcus_web_console/` package directory
4. Create `marcus_web_console/__init__.py` (empty file)
5. Test install: `pip install -e dev-tools/web-console/backend/`

---

#### 1.2 Terminal Session Manager
**File**: `dev-tools/web-console/backend/marcus_web_console/terminal.py`

This module manages PTY (pseudo-terminal) sessions for spawning AI tools.

```python
"""
Terminal session management for web console.

Handles spawning AI coding tools (claude, cursor, amp, etc.) in PTY sessions
and bridging them to WebSocket connections.
"""

import asyncio
import os
import pty
import subprocess
import sys
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class TerminalSession:
    """
    Manages a single terminal session running an AI coding tool.

    Parameters
    ----------
    session_id : str
        Unique identifier for this session
    command : str
        Command to run (e.g., 'claude', 'cursor', 'amp')
    cwd : Path
        Working directory for the session
    env : dict, optional
        Environment variables

    Attributes
    ----------
    last_activity : float
        Timestamp of last I/O activity (for health monitoring)
    is_healthy : bool
        Whether the session appears to be working
    """

    def __init__(
        self,
        session_id: str,
        command: str,
        cwd: Path,
        env: Optional[Dict[str, str]] = None
    ):
        self.session_id = session_id
        self.command = command
        self.cwd = cwd
        self.env = env or os.environ.copy()

        # PTY file descriptors
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None

        # Process
        self.process: Optional[subprocess.Popen] = None

        # Health monitoring
        self.last_activity = 0.0
        self.last_output = ""
        self.is_healthy = True

    async def start(self) -> None:
        """
        Start the terminal session.

        Creates a PTY and spawns the command.

        Raises
        ------
        RuntimeError
            If session fails to start
        """
        import time

        if sys.platform == "win32":
            # Windows: use winpty
            await self._start_windows()
        else:
            # Unix: use PTY
            await self._start_unix()

        self.last_activity = time.time()
        logger.info(f"Started terminal session: {self.session_id} ({self.command})")

    async def _start_unix(self) -> None:
        """Start session on Unix-like systems."""
        self.master_fd, self.slave_fd = pty.openpty()

        self.process = subprocess.Popen(
            [self.command],
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
            cwd=str(self.cwd),
            env=self.env,
            preexec_fn=os.setsid  # Create new session
        )

    async def _start_windows(self) -> None:
        """Start session on Windows."""
        import winpty

        self.process = winpty.PTY(80, 24)
        self.process.spawn(self.command, cwd=str(self.cwd), env=self.env)

    def write(self, data: bytes) -> None:
        """
        Write data to the terminal.

        Parameters
        ----------
        data : bytes
            Data to write
        """
        import time

        if sys.platform == "win32":
            self.process.write(data.decode())
        else:
            os.write(self.master_fd, data)

        self.last_activity = time.time()

    async def read(self, size: int = 1024) -> bytes:
        """
        Read data from the terminal.

        Parameters
        ----------
        size : int
            Maximum bytes to read

        Returns
        -------
        bytes
            Data read from terminal
        """
        import time

        try:
            if sys.platform == "win32":
                data = self.process.read(size).encode()
            else:
                data = os.read(self.master_fd, size)

            if data:
                self.last_activity = time.time()
                self.last_output = data.decode('utf-8', errors='replace')

            return data
        except (OSError, BlockingIOError):
            return b""

    def inject_command(self, command: str) -> None:
        """
        Inject a command into the terminal.

        Useful for recovery - e.g., restarting an agent that got stuck.

        Parameters
        ----------
        command : str
            Command to inject (will append newline)

        Examples
        --------
        >>> session.inject_command("mcp__marcus__request_next_task()")
        """
        cmd_bytes = f"{command}\n".encode()
        self.write(cmd_bytes)
        logger.info(f"Injected command into {self.session_id}: {command}")

    def check_health(self, timeout_seconds: float = 300) -> bool:
        """
        Check if the session is healthy.

        A session is considered unhealthy if:
        - No activity for > timeout_seconds
        - Process has died

        Parameters
        ----------
        timeout_seconds : float
            Inactivity threshold (default: 5 minutes)

        Returns
        -------
        bool
            True if healthy, False otherwise
        """
        import time

        # Check if process is alive
        if self.process and self.process.poll() is not None:
            logger.warning(f"Session {self.session_id} process died")
            self.is_healthy = False
            return False

        # Check for activity timeout
        inactive_time = time.time() - self.last_activity
        if inactive_time > timeout_seconds:
            logger.warning(
                f"Session {self.session_id} inactive for {inactive_time:.1f}s"
            )
            self.is_healthy = False
            return False

        self.is_healthy = True
        return True

    def cleanup(self) -> None:
        """Clean up the terminal session."""
        if self.process:
            if sys.platform == "win32":
                self.process.close()
            else:
                self.process.terminate()
                self.process.wait(timeout=5)

        if self.master_fd:
            os.close(self.master_fd)
        if self.slave_fd:
            os.close(self.slave_fd)

        logger.info(f"Cleaned up terminal session: {self.session_id}")


class TerminalManager:
    """
    Manages multiple terminal sessions.

    Provides health monitoring and recovery for all sessions.
    """

    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}
        self._health_check_task: Optional[asyncio.Task] = None

    async def create_session(
        self,
        session_id: str,
        command: str,
        cwd: Path,
        env: Optional[Dict[str, str]] = None
    ) -> TerminalSession:
        """
        Create and start a new terminal session.

        Parameters
        ----------
        session_id : str
            Unique session identifier
        command : str
            Command to run (claude, cursor, etc.)
        cwd : Path
            Working directory
        env : dict, optional
            Environment variables

        Returns
        -------
        TerminalSession
            Started terminal session
        """
        session = TerminalSession(session_id, command, cwd, env)
        await session.start()
        self.sessions[session_id] = session

        # Start health monitoring if not already running
        if not self._health_check_task:
            self._health_check_task = asyncio.create_task(
                self._monitor_health()
            )

        return session

    def get_session(self, session_id: str) -> Optional[TerminalSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    async def destroy_session(self, session_id: str) -> bool:
        """
        Destroy a terminal session.

        Parameters
        ----------
        session_id : str
            Session to destroy

        Returns
        -------
        bool
            True if session was destroyed, False if not found
        """
        session = self.sessions.pop(session_id, None)
        if session:
            session.cleanup()
            return True
        return False

    async def _monitor_health(self) -> None:
        """
        Background task to monitor session health.

        Runs every 30 seconds and checks all sessions.
        """
        while True:
            await asyncio.sleep(30)

            unhealthy_sessions = []

            for session_id, session in self.sessions.items():
                if not session.check_health():
                    unhealthy_sessions.append(session_id)

            if unhealthy_sessions:
                logger.warning(
                    f"Found {len(unhealthy_sessions)} unhealthy sessions: "
                    f"{unhealthy_sessions}"
                )
                # Emit event for frontend to handle
                # (This will be connected to WebSocket later)

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of all sessions.

        Returns
        -------
        dict
            Health status for each session
        """
        import time

        status = {}
        for session_id, session in self.sessions.items():
            status[session_id] = {
                "is_healthy": session.is_healthy,
                "last_activity": session.last_activity,
                "inactive_seconds": time.time() - session.last_activity,
                "process_alive": (
                    session.process.poll() is None
                    if session.process else False
                ),
            }

        return status
```

**What to do**:
1. Create the file above
2. Read through the code - understand PTY basics
3. Note the `inject_command()` method - this is how we'll recover agents
4. Note the `check_health()` method - this detects stuck agents
5. Test it manually:
   ```python
   import asyncio
   from pathlib import Path
   from marcus_web_console.terminal import TerminalManager

   async def test():
       manager = TerminalManager()
       session = await manager.create_session(
           "test-1", "bash", Path.cwd()
       )
       session.write(b"echo hello\n")
       data = await session.read()
       print(data)

   asyncio.run(test())
   ```

---

#### 1.3 Marcus MCP Client
**File**: `dev-tools/web-console/backend/marcus_web_console/marcus_client.py`

This wraps Marcus MCP calls by spawning Claude Code and parsing results.

```python
"""
Marcus MCP client for web console.

Calls Marcus MCP tools by spawning Claude Code CLI and parsing responses.
"""

import asyncio
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MarcusMCPClient:
    """
    Client for calling Marcus MCP tools.

    Uses Claude Code CLI to make MCP calls and parses responses.
    """

    def __init__(self):
        self.claude_cmd = "claude"

    async def ping(self) -> bool:
        """
        Test Marcus MCP connection.

        Returns
        -------
        bool
            True if Marcus is reachable
        """
        try:
            result = await self._call_mcp("mcp__marcus__ping()")
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Marcus ping failed: {e}")
            return False

    async def create_project(
        self,
        project_name: str,
        description: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a Marcus project.

        Parameters
        ----------
        project_name : str
            Name of the project
        description : str
            Full project specification
        options : dict
            Project options (complexity, provider, etc.)

        Returns
        -------
        dict
            Project creation result with project_id, board_id, tasks_created

        Examples
        --------
        >>> result = await client.create_project(
        ...     "Blog Platform",
        ...     "Build a blog...",
        ...     {"complexity": "standard"}
        ... )
        >>> project_id = result["project_id"]
        """
        # Escape description for JSON
        escaped_desc = json.dumps(description)
        options_json = json.dumps(options)

        script = f"""
import json

result = mcp__marcus__create_project(
    project_name="{project_name}",
    description={escaped_desc},
    options={options_json}
)

print("MARCUS_RESULT_START")
print(json.dumps(result))
print("MARCUS_RESULT_END")
"""

        output = await self._run_claude_script(script)
        return self._parse_result(output)

    async def get_optimal_agent_count(
        self,
        include_details: bool = True
    ) -> Dict[str, Any]:
        """
        Get optimal agent count for current project.

        Parameters
        ----------
        include_details : bool
            Include parallelism timeline details

        Returns
        -------
        dict
            Optimal agent analysis with recommended count, critical path, etc.

        Examples
        --------
        >>> analysis = await client.get_optimal_agent_count()
        >>> print(f"Recommended: {analysis['optimal_agents']} agents")
        """
        script = f"""
import json

result = mcp__marcus__get_optimal_agent_count(
    include_details={str(include_details)}
)

print("MARCUS_RESULT_START")
print(json.dumps(result))
print("MARCUS_RESULT_END")
"""

        output = await self._run_claude_script(script)
        return self._parse_result(output)

    async def _run_claude_script(self, script: str) -> str:
        """
        Run a Python script through Claude Code CLI.

        Parameters
        ----------
        script : str
            Python code to execute

        Returns
        -------
        str
            Claude's output
        """
        # Write script to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(script)
            script_file = f.name

        try:
            # Run claude with the script
            process = await asyncio.create_subprocess_exec(
                self.claude_cmd,
                "--dangerously-skip-permissions",
                "--print",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Send script as stdin
            with open(script_file, 'r') as f:
                script_content = f.read()

            stdout, stderr = await process.communicate(
                input=script_content.encode()
            )

            output = stdout.decode()

            if process.returncode != 0:
                logger.error(f"Claude failed: {stderr.decode()}")
                raise RuntimeError(f"Claude execution failed: {stderr.decode()}")

            return output

        finally:
            # Clean up temp file
            Path(script_file).unlink()

    def _parse_result(self, output: str) -> Dict[str, Any]:
        """
        Parse JSON result from Claude output.

        Parameters
        ----------
        output : str
            Full Claude output

        Returns
        -------
        dict
            Parsed JSON result

        Raises
        ------
        ValueError
            If result markers not found or JSON invalid
        """
        try:
            start_marker = "MARCUS_RESULT_START"
            end_marker = "MARCUS_RESULT_END"

            start_idx = output.index(start_marker) + len(start_marker)
            end_idx = output.index(end_marker)

            json_str = output[start_idx:end_idx].strip()
            return json.loads(json_str)

        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse Marcus result: {e}")
            logger.debug(f"Output was: {output}")
            raise ValueError(f"Could not parse Marcus MCP response: {e}")
```

**What to do**:
1. Create the file above
2. Understand how it works: spawns Claude, injects Python script, parses output
3. Test it:
   ```python
   import asyncio
   from marcus_web_console.marcus_client import MarcusMCPClient

   async def test():
       client = MarcusMCPClient()

       # Test ping
       alive = await client.ping()
       print(f"Marcus alive: {alive}")

       # Test create project (make sure Marcus is running!)
       result = await client.create_project(
           "Test Project",
           "Build a simple test app",
           {"complexity": "prototype"}
       )
       print(f"Project: {result}")

       # Test optimal count
       optimal = await client.get_optimal_agent_count()
       print(f"Optimal agents: {optimal}")

   asyncio.run(test())
   ```

---

#### 1.4 FastAPI Server
**File**: `dev-tools/web-console/backend/marcus_web_console/server.py`

This is the main web server that ties everything together.

```python
"""
Marcus Web Console - Main Server.

FastAPI server providing REST API and WebSocket endpoints for the
web-based experiment dashboard.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .terminal import TerminalManager
from .marcus_client import MarcusMCPClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Marcus Web Console")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global managers
terminal_manager = TerminalManager()
marcus_client = MarcusMCPClient()

# In-memory experiment storage (TODO: use database in production)
experiments: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateExperimentRequest(BaseModel):
    """Request to create a new experiment."""
    name: str
    description: str
    complexity: str = "standard"
    base_dir: Optional[str] = None


class CreateExperimentResponse(BaseModel):
    """Response from creating experiment."""
    experiment_id: str
    directory: str


class AnalyzeProjectResponse(BaseModel):
    """Response from project analysis."""
    success: bool
    optimal_agents: int
    critical_path_hours: float
    max_parallelism: int
    total_tasks: int
    efficiency_gain_percent: float
    parallel_opportunities: Optional[List[Dict[str, Any]]] = None


class AgentConfig(BaseModel):
    """Configuration for a single agent."""
    role: str
    tool: str  # claude, cursor, amp, etc.
    count: int
    skills: List[str]


class LaunchAgentsRequest(BaseModel):
    """Request to launch agents."""
    agent_configs: List[AgentConfig]


class TerminalHealthStatus(BaseModel):
    """Health status of a terminal."""
    terminal_id: str
    is_healthy: bool
    last_activity: float
    inactive_seconds: float
    process_alive: bool


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Marcus Web Console API", "status": "running"}


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.

    Returns
    -------
    dict
        Server health and Marcus connection status
    """
    marcus_alive = await marcus_client.ping()

    return {
        "status": "healthy",
        "marcus_connected": marcus_alive,
        "active_experiments": len(experiments),
        "active_terminals": len(terminal_manager.sessions),
    }


@app.post("/api/experiments", response_model=CreateExperimentResponse)
async def create_experiment(request: CreateExperimentRequest):
    """
    Create a new experiment.

    Sets up directory structure for the experiment.

    Parameters
    ----------
    request : CreateExperimentRequest
        Experiment configuration

    Returns
    -------
    CreateExperimentResponse
        Experiment ID and directory path
    """
    import uuid

    experiment_id = str(uuid.uuid4())[:8]

    # Determine base directory
    if request.base_dir:
        base_dir = Path(request.base_dir)
    else:
        base_dir = Path.home() / "marcus-experiments"

    # Create experiment directory
    exp_dir = base_dir / request.name.lower().replace(' ', '-')
    exp_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (exp_dir / "implementation").mkdir(exist_ok=True)
    (exp_dir / "logs").mkdir(exist_ok=True)
    (exp_dir / "prompts").mkdir(exist_ok=True)

    # Initialize git in implementation directory
    import subprocess
    try:
        subprocess.run(
            ["git", "init"],
            cwd=exp_dir / "implementation",
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "checkout", "-b", "main"],
            cwd=exp_dir / "implementation",
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        logger.warning(f"Git init failed: {e}")

    # Store experiment
    experiments[experiment_id] = {
        "id": experiment_id,
        "name": request.name,
        "description": request.description,
        "complexity": request.complexity,
        "directory": str(exp_dir),
        "implementation_dir": str(exp_dir / "implementation"),
        "project_id": None,  # Set after Marcus creates project
        "board_id": None,
        "terminals": [],
    }

    logger.info(f"Created experiment {experiment_id}: {request.name}")

    return CreateExperimentResponse(
        experiment_id=experiment_id,
        directory=str(exp_dir)
    )


@app.post("/api/experiments/{experiment_id}/analyze")
async def analyze_experiment(experiment_id: str):
    """
    Analyze project and get optimal agent count.

    Calls Marcus MCP to create the project and calculate optimal agents.

    Parameters
    ----------
    experiment_id : str
        Experiment to analyze

    Returns
    -------
    AnalyzeProjectResponse
        Optimal agent analysis
    """
    if experiment_id not in experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")

    experiment = experiments[experiment_id]

    # Create project in Marcus
    logger.info(f"Creating Marcus project for experiment {experiment_id}")

    project_result = await marcus_client.create_project(
        project_name=experiment["name"],
        description=experiment["description"],
        options={"complexity": experiment["complexity"]}
    )

    if not project_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Project creation failed: {project_result.get('error')}"
        )

    # Store project info
    experiment["project_id"] = project_result["project_id"]
    experiment["board_id"] = project_result.get("board_id")
    experiment["tasks_created"] = project_result.get("tasks_created", 0)

    # Get optimal agent count
    logger.info("Calculating optimal agent count")

    analysis = await marcus_client.get_optimal_agent_count(include_details=True)

    if not analysis.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Agent analysis failed: {analysis.get('error')}"
        )

    return AnalyzeProjectResponse(**analysis)


@app.post("/api/experiments/{experiment_id}/agents/launch")
async def launch_agents(experiment_id: str, request: LaunchAgentsRequest):
    """
    Launch configured agents for the experiment.

    Creates terminal sessions for each agent.

    Parameters
    ----------
    experiment_id : str
        Experiment to launch agents for
    request : LaunchAgentsRequest
        Agent configurations

    Returns
    -------
    dict
        List of created terminal IDs
    """
    if experiment_id not in experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")

    experiment = experiments[experiment_id]
    implementation_dir = Path(experiment["implementation_dir"])

    terminals_created = []

    # Create terminals for each agent configuration
    for config in request.agent_configs:
        for i in range(config.count):
            terminal_id = f"{experiment_id}_{config.role}_{i+1}"

            # Create terminal session
            session = await terminal_manager.create_session(
                session_id=terminal_id,
                command=config.tool,  # claude, cursor, amp, etc.
                cwd=implementation_dir,
            )

            # Auto-inject startup commands
            startup_script = f"""
# Marcus Agent Startup
# Experiment: {experiment['name']}
# Role: {config.role}
# Skills: {', '.join(config.skills)}

# Register with Marcus
mcp__marcus__register_agent(
    agent_id="{terminal_id}",
    name="{config.role}_{i+1}",
    role="{config.role}",
    skills={config.skills}
)

# Start work loop
while true:
    mcp__marcus__request_next_task(agent_id="{terminal_id}")
    # Work on task...
    # Report progress...
done
"""

            # Inject the startup script
            session.inject_command(startup_script)

            terminals_created.append(terminal_id)
            experiment["terminals"].append(terminal_id)

    logger.info(
        f"Launched {len(terminals_created)} agents for experiment {experiment_id}"
    )

    return {
        "success": True,
        "terminals": terminals_created,
        "message": f"Launched {len(terminals_created)} agents"
    }


@app.get("/api/experiments/{experiment_id}/health")
async def get_experiment_health(experiment_id: str):
    """
    Get health status of all agents in an experiment.

    Parameters
    ----------
    experiment_id : str
        Experiment to check

    Returns
    -------
    dict
        Health status for each terminal
    """
    if experiment_id not in experiments:
        raise HTTPException(status_code=404, detail="Experiment not found")

    experiment = experiments[experiment_id]
    terminal_ids = experiment["terminals"]

    health_status = []

    for terminal_id in terminal_ids:
        session = terminal_manager.get_session(terminal_id)
        if session:
            health_status.append({
                "terminal_id": terminal_id,
                "is_healthy": session.is_healthy,
                "last_activity": session.last_activity,
                "inactive_seconds": (
                    __import__('time').time() - session.last_activity
                ),
                "process_alive": (
                    session.process.poll() is None
                    if session.process else False
                ),
            })
        else:
            health_status.append({
                "terminal_id": terminal_id,
                "is_healthy": False,
                "error": "Session not found"
            })

    return {
        "experiment_id": experiment_id,
        "terminals": health_status,
        "total": len(terminal_ids),
        "healthy": sum(1 for t in health_status if t.get("is_healthy", False))
    }


@app.post("/api/terminals/{terminal_id}/recover")
async def recover_terminal(terminal_id: str):
    """
    Attempt to recover a stuck terminal.

    Injects commands to restart the agent work loop.

    Parameters
    ----------
    terminal_id : str
        Terminal to recover

    Returns
    -------
    dict
        Recovery status
    """
    session = terminal_manager.get_session(terminal_id)

    if not session:
        raise HTTPException(status_code=404, detail="Terminal not found")

    # Inject recovery commands
    recovery_script = """
# Attempting recovery...
mcp__marcus__request_next_task(agent_id="{terminal_id}")
""".format(terminal_id=terminal_id)

    session.inject_command(recovery_script)

    logger.info(f"Recovery attempted for terminal {terminal_id}")

    return {
        "success": True,
        "terminal_id": terminal_id,
        "message": "Recovery commands injected"
    }


@app.websocket("/ws/terminal/{terminal_id}")
async def terminal_websocket(websocket: WebSocket, terminal_id: str):
    """
    WebSocket endpoint for terminal I/O.

    Bidirectional stream between web UI and terminal session.

    Parameters
    ----------
    websocket : WebSocket
        WebSocket connection
    terminal_id : str
        Terminal session ID
    """
    await websocket.accept()

    session = terminal_manager.get_session(terminal_id)

    if not session:
        await websocket.close(code=4004, reason="Terminal not found")
        return

    # Read from terminal and send to WebSocket
    async def read_loop():
        while True:
            try:
                data = await session.read()
                if data:
                    await websocket.send_bytes(data)
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Read loop error: {e}")
                break

    # Write from WebSocket to terminal
    async def write_loop():
        try:
            while True:
                message = await websocket.receive_bytes()
                session.write(message)
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {terminal_id}")
        except Exception as e:
            logger.error(f"Write loop error: {e}")

    # Run both loops concurrently
    await asyncio.gather(
        read_loop(),
        write_loop(),
        return_exceptions=True
    )


# ============================================================================
# Static Files & Startup
# ============================================================================

# Serve static frontend files (will create in Phase 2)
# app.mount("/", StaticFiles(directory="static", html=True), name="static")


def main():
    """Entry point for the web console."""
    import uvicorn

    print("=" * 70)
    print("Marcus Web Console")
    print("=" * 70)
    print()
    print("🌐 Starting server...")
    print("📍 URL: http://localhost:8000")
    print("📡 API Docs: http://localhost:8000/docs")
    print()
    print("Press Ctrl+C to stop")
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
```

**What to do**:
1. Create the file above
2. Review each endpoint - understand what it does
3. Install the package: `pip install -e dev-tools/web-console/backend/`
4. Test the server:
   ```bash
   # Make sure Marcus is running first!
   marcus serve

   # In another terminal:
   marcus-web-console

   # Visit http://localhost:8000/docs to see API docs
   ```
5. Test the API with curl:
   ```bash
   # Health check
   curl http://localhost:8000/api/health

   # Create experiment
   curl -X POST http://localhost:8000/api/experiments \
     -H "Content-Type: application/json" \
     -d '{"name": "Test Project", "description": "A test", "complexity": "prototype"}'
   ```

## Phase 2: Frontend (Week 2)

### Goal
Create a simple web UI for the experiment dashboard.

### Tasks

#### 2.1 HTML/CSS/JS Frontend
**File**: `dev-tools/web-console/backend/static/index.html`

Create a single-page application using vanilla HTML/JS (no framework needed for MVP).

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Marcus Web Console</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1e1e1e;
            color: #d4d4d4;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: #252526;
            padding: 20px;
            border-bottom: 2px solid #3e3e3e;
        }
        
        h1 {
            font-size: 24px;
            margin-bottom: 10px;
        }
        
        .wizard-steps {
            display: flex;
            gap: 20px;
            margin-top: 10px;
        }
        
        .step {
            padding: 10px 20px;
            background: #3e3e3e;
            border-radius: 4px;
            opacity: 0.5;
        }
        
        .step.active {
            opacity: 1;
            background: #0e639c;
        }
        
        .content {
            flex: 1;
            padding: 20px;
            overflow: auto;
        }
        
        .card {
            background: #252526;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        button {
            background: #0e639c;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        
        button:hover { background: #1177bb; }
        button:disabled {
            background: #666;
            cursor: not-allowed;
        }
        
        input, select, textarea {
            width: 100%;
            padding: 10px;
            background: #3c3c3c;
            border: 1px solid #3e3e3e;
            color: #d4d4d4;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        
        .terminals-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 10px;
        }
        
        .terminal-container {
            background: #1e1e1e;
            border: 1px solid #3e3e3e;
            border-radius: 4px;
            height: 400px;
            display: flex;
            flex-direction: column;
        }
        
        .terminal-header {
            background: #2d2d30;
            padding: 8px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .health-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4ec9b0;
        }
        
        .health-indicator.unhealthy {
            background: #f48771;
        }
        
        .terminal-body {
            flex: 1;
            padding: 5px;
        }
        
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Marcus Web Console</h1>
        <div class="wizard-steps">
            <div class="step active" id="step-1">1. Configure</div>
            <div class="step" id="step-2">2. Analyze</div>
            <div class="step" id="step-3">3. Launch</div>
            <div class="step" id="step-4">4. Monitor</div>
        </div>
    </div>
    
    <div class="content">
        <!-- Step 1: Configure Experiment -->
        <div id="page-configure" class="page">
            <div class="card">
                <h2>Create Experiment</h2>
                <label>Project Name:</label>
                <input type="text" id="project-name" placeholder="My Awesome Project" />
                
                <label>Project Description:</label>
                <textarea id="project-description" rows="8" 
                          placeholder="Describe what you want to build..."></textarea>
                
                <label>Complexity:</label>
                <select id="complexity">
                    <option value="prototype">Prototype (Simple)</option>
                    <option value="standard" selected>Standard</option>
                    <option value="enterprise">Enterprise (Complex)</option>
                </select>
                
                <button onclick="createExperiment()">Create & Analyze</button>
            </div>
        </div>
        
        <!-- Step 2: Analyze Results -->
        <div id="page-analyze" class="page hidden">
            <div class="card">
                <h2>Optimal Agent Analysis</h2>
                <div id="analysis-results"></div>
                <button onclick="showAgentConfig()">Configure Agents</button>
            </div>
        </div>
        
        <!-- Step 3: Configure Agents -->
        <div id="page-agents" class="page hidden">
            <div class="card">
                <h2>Agent Configuration</h2>
                <div id="agent-config-ui"></div>
                <button onclick="launchAgents()">Launch Experiment</button>
            </div>
        </div>
        
        <!-- Step 4: Monitor Terminals -->
        <div id="page-monitor" class="page hidden">
            <div class="card">
                <h2>Agent Terminals</h2>
                <div class="terminals-grid" id="terminals-grid"></div>
            </div>
        </div>
    </div>
    
    <script>
        let currentExperiment = null;
        let terminals = [];
        let healthCheckInterval = null;
        
        // Page navigation
        function showPage(pageId) {
            document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
            document.getElementById(`page-${pageId}`).classList.remove('hidden');
            
            // Update step indicators
            const stepMap = {
                'configure': 1,
                'analyze': 2,
                'agents': 3,
                'monitor': 4
            };
            const activeStep = stepMap[pageId];
            document.querySelectorAll('.step').forEach((step, idx) => {
                step.classList.toggle('active', idx + 1 <= activeStep);
            });
        }
        
        // Step 1: Create experiment
        async function createExperiment() {
            const name = document.getElementById('project-name').value;
            const description = document.getElementById('project-description').value;
            const complexity = document.getElementById('complexity').value;
            
            if (!name || !description) {
                alert('Please fill in all fields');
                return;
            }
            
            // Create experiment
            const createResp = await fetch('/api/experiments', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, description, complexity })
            });
            
            currentExperiment = await createResp.json();
            
            // Analyze project
            const analyzeResp = await fetch(
                `/api/experiments/${currentExperiment.experiment_id}/analyze`,
                { method: 'POST' }
            );
            
            const analysis = await analyzeResp.json();
            
            // Display results
            displayAnalysis(analysis);
            showPage('analyze');
        }
        
        // Display analysis results
        function displayAnalysis(analysis) {
            const html = `
                <p><strong>Total Tasks:</strong> ${analysis.total_tasks}</p>
                <p><strong>Critical Path:</strong> ${analysis.critical_path_hours.toFixed(1)} hours</p>
                <p><strong>Max Parallelism:</strong> ${analysis.max_parallelism} tasks simultaneously</p>
                <p><strong>Recommended Agents:</strong> <span style="color: #4ec9b0; font-size: 24px">${analysis.optimal_agents}</span></p>
                <p><strong>Efficiency Gain:</strong> ${analysis.efficiency_gain_percent}% vs single agent</p>
            `;
            document.getElementById('analysis-results').innerHTML = html;
            currentExperiment.analysis = analysis;
        }
        
        // Step 2: Show agent configuration
        function showAgentConfig() {
            const optimal = currentExperiment.analysis.optimal_agents;
            
            // Simple config: distribute agents across roles
            const html = `
                <p>Configure ${optimal} agents across different roles:</p>
                <label>Backend Agents:</label>
                <input type="number" id="backend-count" value="${Math.floor(optimal / 2)}" min="0" />
                <label>Backend Tool:</label>
                <select id="backend-tool">
                    <option value="claude">Claude Code</option>
                    <option value="cursor">Cursor CLI</option>
                    <option value="amp">Amp</option>
                </select>
                
                <label>Frontend Agents:</label>
                <input type="number" id="frontend-count" value="${Math.ceil(optimal / 2)}" min="0" />
                <label>Frontend Tool:</label>
                <select id="frontend-tool">
                    <option value="claude">Claude Code</option>
                    <option value="cursor">Cursor CLI</option>
                </select>
            `;
            document.getElementById('agent-config-ui').innerHTML = html;
            showPage('agents');
        }
        
        // Step 3: Launch agents
        async function launchAgents() {
            const backendCount = parseInt(document.getElementById('backend-count').value);
            const backendTool = document.getElementById('backend-tool').value;
            const frontendCount = parseInt(document.getElementById('frontend-count').value);
            const frontendTool = document.getElementById('frontend-tool').value;
            
            const agentConfigs = [];
            
            if (backendCount > 0) {
                agentConfigs.push({
                    role: 'backend',
                    tool: backendTool,
                    count: backendCount,
                    skills: ['python', 'fastapi', 'postgresql']
                });
            }
            
            if (frontendCount > 0) {
                agentConfigs.push({
                    role: 'frontend',
                    tool: frontendTool,
                    count: frontendCount,
                    skills: ['react', 'typescript', 'tailwind']
                });
            }
            
            const resp = await fetch(
                `/api/experiments/${currentExperiment.experiment_id}/agents/launch`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ agent_configs: agentConfigs })
                }
            );
            
            const result = await resp.json();
            terminals = result.terminals;
            
            // Show monitoring page
            setupTerminals();
            showPage('monitor');
            
            // Start health monitoring
            startHealthMonitoring();
        }
        
        // Step 4: Setup terminal grid
        function setupTerminals() {
            const grid = document.getElementById('terminals-grid');
            grid.innerHTML = '';
            
            terminals.forEach(terminalId => {
                const container = document.createElement('div');
                container.className = 'terminal-container';
                container.innerHTML = `
                    <div class="terminal-header">
                        <span>${terminalId}</span>
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <div class="health-indicator" id="health-${terminalId}"></div>
                            <button onclick="recoverTerminal('${terminalId}')" style="padding: 4px 8px; font-size: 12px;">Recover</button>
                        </div>
                    </div>
                    <div class="terminal-body" id="term-${terminalId}"></div>
                `;
                grid.appendChild(container);
                
                // Create xterm instance
                const term = new Terminal({
                    fontSize: 13,
                    theme: {
                        background: '#1e1e1e',
                        foreground: '#d4d4d4'
                    }
                });
                
                const fitAddon = new FitAddon.FitAddon();
                term.loadAddon(fitAddon);
                term.open(document.getElementById(`term-${terminalId}`));
                fitAddon.fit();
                
                // Connect WebSocket
                const ws = new WebSocket(`ws://${location.host}/ws/terminal/${terminalId}`);
                
                ws.onmessage = (event) => {
                    event.data.arrayBuffer().then(buffer => {
                        term.write(new Uint8Array(buffer));
                    });
                };
                
                term.onData((data) => {
                    ws.send(new TextEncoder().encode(data));
                });
            });
        }
        
        // Health monitoring
        function startHealthMonitoring() {
            healthCheckInterval = setInterval(async () => {
                const resp = await fetch(
                    `/api/experiments/${currentExperiment.experiment_id}/health`
                );
                const health = await resp.json();
                
                health.terminals.forEach(t => {
                    const indicator = document.getElementById(`health-${t.terminal_id}`);
                    if (indicator) {
                        indicator.classList.toggle('unhealthy', !t.is_healthy);
                        
                        // Auto-recover if unhealthy for > 2 minutes
                        if (!t.is_healthy && t.inactive_seconds > 120) {
                            console.log(`Auto-recovering ${t.terminal_id}`);
                            recoverTerminal(t.terminal_id);
                        }
                    }
                });
            }, 30000); // Check every 30 seconds
        }
        
        // Recover terminal
        async function recoverTerminal(terminalId) {
            await fetch(`/api/terminals/${terminalId}/recover`, {
                method: 'POST'
            });
            alert(`Recovery commands sent to ${terminalId}`);
        }
    </script>
</body>
</html>
```

**What to do**:
1. Create `dev-tools/web-console/backend/static/` directory
2. Create the HTML file above
3. Uncomment the static files mount in `server.py`:
   ```python
   # In server.py, uncomment this line:
   app.mount("/", StaticFiles(directory="static", html=True), name="static")
   ```
4. Test the full workflow:
   - Start Marcus: `marcus serve`
   - Start web console: `marcus-web-console`
   - Open http://localhost:8000
   - Create an experiment
   - Configure agents
   - Launch and monitor

---

## Phase 3: Agent Health Monitoring & Recovery

### How Agent Health Detection Works

#### Detection Methods

**1. Inactivity Timeout**
- **What**: Tracks last I/O activity timestamp
- **Threshold**: 5 minutes (configurable)
- **Triggers**: When `time.time() - last_activity > timeout_seconds`
- **Location**: `terminal.py` → `TerminalSession.check_health()`

**2. Process Death Detection**
- **What**: Checks if subprocess is still running
- **Check**: `process.poll() is not None` (returns exit code if dead)
- **Triggers**: Immediately when process terminates
- **Location**: `terminal.py` → `TerminalSession.check_health()`

**3. Pattern Detection (Future Enhancement)**
- **What**: Look for error patterns in terminal output
- **Examples**:
  - "No tasks available" loops
  - API errors
  - Authentication failures
- **Implementation**: Parse `last_output` in health check
- **Example**:
  ```python
  def check_health(self, timeout_seconds: float = 300) -> bool:
      # Existing checks...
      
      # Pattern detection
      if "No suitable tasks found" in self.last_output:
          # Count consecutive occurrences
          if self._no_task_count > 10:
              logger.warning("Agent stuck in 'no tasks' loop")
              self.is_healthy = False
              return False
      
      return True
  ```

#### Health Check Schedule

```
TerminalManager._monitor_health() runs in background:
├─ Every 30 seconds
├─ For each session:
│  ├─ Call session.check_health()
│  ├─ If unhealthy:
│  │  ├─ Log warning
│  │  ├─ Emit event (for frontend notification)
│  │  └─ Mark as unhealthy
│  └─ If healthy: continue
└─ Report unhealthy sessions
```

### Command Injection for Recovery

#### How It Works

When an agent gets stuck, we can "inject" commands directly into its terminal to restart it.

**Technical Mechanism**:
```python
def inject_command(self, command: str) -> None:
    """
    Write command directly to the PTY master file descriptor.
    
    This is like typing into the terminal - the AI tool receives it
    as if the user typed it.
    """
    cmd_bytes = f"{command}\n".encode()
    os.write(self.master_fd, cmd_bytes)
```

**Use Cases**:

1. **Agent stopped requesting tasks**:
   ```python
   session.inject_command("mcp__marcus__request_next_task(agent_id='agent-1')")
   ```

2. **Agent waiting at prompt**:
   ```python
   session.inject_command("\x03")  # Ctrl+C
   session.inject_command("mcp__marcus__request_next_task(agent_id='agent-1')")
   ```

3. **Agent needs fresh context**:
   ```python
   session.inject_command("# Resuming work after inactivity")
   session.inject_command("mcp__marcus__get_task_context(task_id='task-123')")
   session.inject_command("# Continue working on task")
   ```

#### Recovery Strategies

**Strategy 1: Simple Nudge** (Default)
```python
@app.post("/api/terminals/{terminal_id}/recover")
async def recover_terminal(terminal_id: str):
    session = terminal_manager.get_session(terminal_id)
    
    # Just request next task
    session.inject_command(
        f"mcp__marcus__request_next_task(agent_id='{terminal_id}')"
    )
```

**Strategy 2: Full Restart**
```python
@app.post("/api/terminals/{terminal_id}/restart")
async def restart_terminal(terminal_id: str):
    session = terminal_manager.get_session(terminal_id)
    
    # Send Ctrl+C to interrupt
    session.write(b"\x03")
    await asyncio.sleep(0.5)
    
    # Re-inject startup script
    startup = f"""
# Restarting agent...
mcp__marcus__register_agent(agent_id='{terminal_id}', ...)
mcp__marcus__request_next_task(agent_id='{terminal_id}')
"""
    session.inject_command(startup)
```

**Strategy 3: Context Refresh**
```python
@app.post("/api/terminals/{terminal_id}/refresh")
async def refresh_context(terminal_id: str):
    session = terminal_manager.get_session(terminal_id)
    
    # Get current task
    session.inject_command(f"""
# Refreshing context...
task = mcp__marcus__request_next_task(agent_id='{terminal_id}')
if task:
    context = mcp__marcus__get_task_context(task_id=task['task_id'])
    print(f"Resuming: {{task['title']}}")
""")
```

### User Notifications

#### Browser Notifications

```javascript
// In the frontend health monitoring loop
function checkHealth() {
    fetch(`/api/experiments/${experimentId}/health`)
        .then(r => r.json())
        .then(health => {
            health.terminals.forEach(t => {
                if (!t.is_healthy) {
                    // Show browser notification
                    if (Notification.permission === 'granted') {
                        new Notification('Agent Stuck', {
                            body: `${t.terminal_id} has been inactive for ${Math.round(t.inactive_seconds / 60)} minutes`,
                            icon: '/icon.png',
                            tag: t.terminal_id  // Prevent duplicates
                        });
                    }
                    
                    // Update UI indicator
                    updateHealthIndicator(t.terminal_id, false);
                    
                    // Auto-recover after 2 minutes
                    if (t.inactive_seconds > 120) {
                        autoRecover(t.terminal_id);
                    }
                }
            });
        });
}

// Request notification permission on page load
if (Notification.permission === 'default') {
    Notification.requestPermission();
}
```

#### Visual Indicators

```css
.health-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #4ec9b0; /* Green = healthy */
    animation: pulse 2s infinite;
}

.health-indicator.unhealthy {
    background: #f48771; /* Red = unhealthy */
    animation: blink 1s infinite;
}

@keyframes blink {
    0%, 50%, 100% { opacity: 1; }
    25%, 75% { opacity: 0.3; }
}
```

#### Email/Slack Notifications (Future)

```python
# In server.py - health monitoring callback
async def on_unhealthy_session(session_id: str, inactive_seconds: float):
    """Called when a session becomes unhealthy."""
    
    # Send notification
    await send_slack_notification(
        channel="#marcus-experiments",
        message=f"🚨 Agent {session_id} stuck (inactive {inactive_seconds}s)"
    )
    
    # Or email
    await send_email(
        to=user_email,
        subject="Marcus Agent Stuck",
        body=f"Agent {session_id} needs attention"
    )
```

---

## Testing & Debugging

### Manual Testing Checklist

**Backend**:
- [ ] Can create experiment
- [ ] Can analyze project (calls Marcus MCP)
- [ ] Can launch agents
- [ ] Can recover agents
- [ ] Health monitoring detects inactive sessions
- [ ] WebSocket streams terminal I/O correctly

**Frontend**:
- [ ] Wizard flow works (Configure → Analyze → Launch → Monitor)
- [ ] Terminal grid displays correctly
- [ ] Health indicators update
- [ ] Recovery button works
- [ ] Notifications appear for unhealthy agents

**Integration**:
- [ ] Marcus MCP connection works
- [ ] Agents register successfully
- [ ] Tasks are assigned and completed
- [ ] Multiple agents can work concurrently
- [ ] Recovery restarts stuck agents

### Common Issues & Solutions

**Issue**: Marcus not found
```bash
# Solution: Make sure Marcus is running
marcus serve

# Check if accessible
curl http://localhost:4298/health
```

**Issue**: Claude command not found
```bash
# Solution: Ensure Claude Code CLI is installed and in PATH
which claude

# If not found:
# - Install Claude Code
# - Add to PATH
```

**Issue**: Terminal not displaying
```
# Solution: Check browser console for WebSocket errors
# Common causes:
- WebSocket connection failed (backend not running)
- Terminal ID mismatch
- xterm.js not loaded
```

**Issue**: Agents not recovering
```python
# Debug: Check if command injection worked
session = terminal_manager.get_session(terminal_id)
print(f"Last output: {session.last_output}")
print(f"Process alive: {session.process.poll() is None}")

# Try manual injection
session.inject_command("echo 'test'")
```

---

## Deployment Considerations

### For Local Development (Current Scope)
- Single-user, runs on localhost
- No authentication needed
- Use in-memory storage for experiments

### For Team Use (Future)
- Add user authentication
- Use SQLite/PostgreSQL for experiment storage
- Add access control (users can only see their experiments)
- Deploy behind reverse proxy (nginx)

### Security Notes
- **Never expose publicly without authentication**
- Command injection is powerful - only allow authorized users
- Validate all user inputs
- Limit terminal access to project directories only

---

## Next Steps

After completing Phases 1-2, consider:

1. **Add experiment templates**
   - Pre-configured project types
   - Save/load experiment configs

2. **Enhance monitoring**
   - Task progress visualization
   - Agent utilization graphs
   - MLflow integration dashboard

3. **Better recovery**
   - Smart recovery strategies
   - Agent behavior learning
   - Automatic task reassignment

4. **Collaboration features**
   - Multiple users on same experiment
   - Chat between agents
   - Shared experiment library

---

## Questions to Ask if Stuck

1. **Marcus not responding?**
   - Is `marcus serve` running?
   - Check `marcus status`
   - Look at Marcus logs

2. **Terminals not working?**
   - Is the AI tool installed? (`which claude`)
   - Check WebSocket connection in browser DevTools
   - Look at backend logs for errors

3. **Health checks not detecting issues?**
   - Adjust `timeout_seconds` in `check_health()`
   - Add more detection patterns
   - Check if `last_activity` is updating

4. **Recovery not working?**
   - Verify command injection with `echo test`
   - Check if process is actually alive
   - Try manual commands in terminal first

5. **Frontend issues?**
   - Check browser console for errors
   - Verify API endpoints with `curl`
   - Test with FastAPI docs UI first

---

## Summary

You'll build:
1. **Backend**: FastAPI server managing experiments, terminals, and Marcus integration
2. **Frontend**: Simple web UI for the experiment workflow
3. **Health Monitoring**: Automatic detection of stuck agents
4. **Recovery**: Command injection to restart agents

Key files:
- `backend/marcus_web_console/terminal.py` - Terminal management + health checks
- `backend/marcus_web_console/marcus_client.py` - Marcus MCP integration
- `backend/marcus_web_console/server.py` - Main API server
- `backend/static/index.html` - Web UI

Start with Phase 1 (backend), test thoroughly, then move to Phase 2 (frontend).

Good luck! 🚀
