"""
MCP Client for Worker Agents to connect to Marcus Server.

This module provides a comprehensive client implementation for worker agents to
communicate with the Marcus server using the Model Context Protocol (MCP).
It handles all aspects of worker-server communication including connection
management, task lifecycle operations, and error recovery.

The client supports:
- Secure MCP connection establishment and management
- Agent registration with role and skill specification
- Task request and assignment handling
- Progress reporting with milestone tracking
- Blocker reporting with severity classification
- Project status monitoring

Classes
-------
WorkerMCPClient
    Main client class for MCP communication with Marcus server

Examples
--------
Basic worker agent workflow:

>>> import asyncio
>>> from src.worker.client import WorkerMCPClient
>>>
>>> async def worker_main():
...     client = WorkerMCPClient()
...     async with client.connect_to_marcus() as session:
...         # Register agent
...         result = await client.register_agent(
...             "worker-001",
...             "Backend Developer",
...             "Developer",
...             ["python", "fastapi", "postgresql"]
...         )
...
...         # Work loop
...         while True:
...             task = await client.request_next_task("worker-001")
...             if not task.get('task'):
...                 break
...
...             # Report progress milestones
...             await client.report_task_progress(
...                 "worker-001", task['task']['id'], "in_progress", 25
...             )
...
...             # Complete task
...             await client.report_task_progress(
...                 "worker-001", task['task']['id'], "completed", 100
...             )
>>>
>>> asyncio.run(worker_main())

Notes
-----
This client requires the Marcus MCP server to be running and accessible.
All communication is asynchronous and uses the MCP stdio transport protocol.
Workers should handle connection failures gracefully and implement retry logic.
"""

import asyncio
import json
import os
import secrets
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, TypeVar, Union

from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters
from mcp.types import TextContent, CallToolResult, ListToolsResult

# Type variable for retry decorator
T = TypeVar("T")


def _extract_text_from_result(result: CallToolResult) -> str:
    """Extract text content from MCP tool call result.
    
    Args:
        result: The CallToolResult from MCP tool call
        
    Returns:
        str: The text content if available, empty string otherwise
    """
    if not result.content:
        return ""
    
    for content_item in result.content:
        # Check if it's a TextContent object or has a text attribute (for testing)
        if isinstance(content_item, TextContent) or hasattr(content_item, 'text'):
            return content_item.text
    
    return ""


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator for retrying operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays

    Returns:
        Decorated function that retries on failure
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except (ConnectionError, RuntimeError, asyncio.TimeoutError) as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Last attempt failed
                        print(
                            f"❌ {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(initial_delay * (exponential_base**attempt), max_delay)

                    # Add jitter if enabled
                    if jitter:
                        # Use cryptographically secure random for jitter
                        secure_random = secrets.SystemRandom()
                        delay = delay * (0.5 + secure_random.random())

                    print(
                        f"⚠️  {func.__name__} failed (attempt {attempt + 1}/{max_attempts}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )

                    await asyncio.sleep(delay)

            # Should never reach here, but just in case
            raise last_exception or RuntimeError(f"{func.__name__} failed unexpectedly")

        return wrapper

    return decorator


class WorkerMCPClient:
    """
    MCP Client for workers to communicate with Marcus.

    This class provides a high-level interface for worker agents to communicate
    with the Marcus server using the Model Context Protocol (MCP). It manages
    connection lifecycle, handles all Marcus operations, and provides robust
    error handling and recovery mechanisms.

    The client operates asynchronously and maintains a persistent connection
    to the Marcus server through stdio pipes. It supports the full workflow
    of agent registration, task management, progress reporting, and status
    monitoring required for autonomous worker operation.

    Attributes
    ----------
    session : Optional[ClientSession]
        The active MCP client session, None when disconnected

    Methods
    -------
    connect_to_marcus()
        Async context manager for establishing MCP connection
    register_agent(agent_id, name, role, skills)
        Register worker agent with Marcus system
    request_next_task(agent_id)
        Request next available task assignment
    report_task_progress(agent_id, task_id, status, progress, message)
        Report task progress and status updates
    report_blocker(agent_id, task_id, blocker_description, severity)
        Report task blockers for AI assistance
    get_project_status()
        Retrieve current project status and metrics

    Examples
    --------
    Basic usage pattern:

    >>> client = WorkerMCPClient()
    >>> async with client.connect_to_marcus() as session:
    ...     # Register with Marcus
    ...     await client.register_agent(
    ...         "dev-worker-1",
    ...         "Development Worker",
    ...         "Software Developer",
    ...         ["python", "javascript", "testing"]
    ...     )
    ...
    ...     # Request and work on tasks
    ...     task_response = await client.request_next_task("dev-worker-1")
    ...     if task_response.get('task'):
    ...         task_id = task_response['task']['id']
    ...
    ...         # Report progress milestones
    ...         await client.report_task_progress(
    ...             "dev-worker-1", task_id, "in_progress", 50,
    ...             "Completed initial implementation"
    ...         )
    ...
    ...         # Report completion
    ...         await client.report_task_progress(
    ...             "dev-worker-1", task_id, "completed", 100,
    ...             "Task completed successfully with tests"
    ...         )

    Error handling example:

    >>> try:
    ...     async with client.connect_to_marcus() as session:
    ...         await client.register_agent("worker-1", "Worker", "Dev", [])
    ... except RuntimeError as e:
    ...     print(f"Connection failed: {e}")
    ... except Exception as e:
    ...     print(f"Unexpected error: {e}")

    Notes
    -----
    - All methods require an active connection established via connect_to_marcus()
    - The client automatically handles JSON serialization/deserialization
    - Connection failures raise RuntimeError with descriptive messages
    - Workers should implement retry logic for transient failures
    - Session management is handled automatically by the context manager
    """

    def __init__(self) -> None:
        """
        Initialize the WorkerMCPClient.

        Creates a new MCP client instance with no active connection.
        The session will be established when using the connect_to_marcus()
        context manager.

        Parameters
        ----------
        None

        Attributes
        ----------
        session : Optional[ClientSession]
            Initially None, set when connection is established

        Examples
        --------
        >>> client = WorkerMCPClient()
        >>> print(client.session)  # None until connected
        None
        """
        self.session: Optional[ClientSession] = None
        self._connection_attempts = 0
        self._last_connection_time = 0.0

    @asynccontextmanager
    async def connect_to_marcus(self) -> AsyncIterator[ClientSession]:
        """
        Establish connection to Marcus MCP server.

        This async context manager handles the complete lifecycle of connecting
        to the Marcus server using the Model Context Protocol (MCP) over stdio.
        It spawns the server process, establishes communication streams, initializes
        the session, and ensures proper cleanup on exit.

        The connection uses stdio pipes to communicate with the Marcus server
        process. The server command is dynamically constructed relative to the
        current module location to ensure portability.

        Yields
        ------
        ClientSession
            An active MCP client session for communication with Marcus

        Raises
        ------
        RuntimeError
            If the server process fails to start or connection cannot be established
        ConnectionError
            If MCP initialization fails or server is unreachable
        OSError
            If the server script file cannot be found or executed

        Examples
        --------
        Basic connection usage:

        >>> client = WorkerMCPClient()
        >>> async with client.connect_to_marcus() as session:
        ...     # Session is active and ready for use
        ...     tools = await session.list_tools()
        ...     print(f"Available tools: {[t.name for t in tools]}")

        Connection with error handling:

        >>> try:
        ...     async with client.connect_to_marcus() as session:
        ...         await client.register_agent("worker-1", "Test", "Developer", [])
        ... except RuntimeError as e:
        ...     print(f"Failed to connect: {e}")
        ... except Exception as e:
        ...     print(f"Unexpected error: {e}")

        Notes
        -----
        - The context manager automatically handles server process lifecycle
        - Session cleanup is guaranteed even if exceptions occur
        - Server output is captured and available for debugging
        - The connection verifies available tools upon successful initialization
        - Multiple concurrent connections from the same client are not supported
        """
        # Marcus server command
        server_cmd = [
            "python",
            os.path.join(os.path.dirname(__file__), "..", "..", "marcus_mcp_server.py"),
        ]

        server_params = StdioServerParameters(
            command=server_cmd[0], args=server_cmd[1:], env=None
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                self.session = session
                await session.initialize()

                # List available tools to verify connection
                tools_response = await session.list_tools()
                # Handle both real ListToolsResult objects and mock lists
                if hasattr(tools_response, 'tools'):
                    tools = tools_response.tools
                else:
                    # For testing, tools_response might be a list directly
                    tools = tools_response  # type: ignore
                print(
                    f"Connected to Marcus. Available tools: {[t.name for t in tools]}"
                )

                yield session

    def _should_attempt_reconnect(self) -> bool:
        """Check if we should attempt to reconnect based on recent attempts"""
        current_time = time.time()

        # Reset attempt counter if it's been more than 5 minutes
        if current_time - self._last_connection_time > 300:
            self._connection_attempts = 0

        # Allow up to 5 rapid reconnection attempts
        return self._connection_attempts < 5

    async def ensure_connected(self) -> bool:
        """Ensure we have an active connection, attempt reconnect if needed"""
        if self.session and not getattr(self.session, "_closed", True):
            return True

        if not self._should_attempt_reconnect():
            print("⚠️  Too many reconnection attempts, please wait before retrying")
            return False

        print("🔄 Attempting to reconnect to Marcus...")
        self._connection_attempts += 1
        self._last_connection_time = time.time()

        try:
            # Try to establish new connection
            async with self.connect_to_marcus() as session:
                self.session = session
                print("✅ Reconnected to Marcus successfully")
                self._connection_attempts = 0  # Reset on success
                return True
        except Exception as e:
            print(f"❌ Reconnection failed: {e}")
            return False

    async def register_agent(
        self, agent_id: str, name: str, role: str, skills: List[str]
    ) -> Dict[str, Any]:
        """
        Register worker agent with the Marcus system.

        This method registers a new worker agent with the Marcus server,
        providing identification, role information, and skill capabilities.
        Registration is required before an agent can request tasks or participate
        in the project workflow.

        The registration process validates agent information and creates a new
        agent record in the Marcus system. Agents can only be registered once
        per session; subsequent registrations with the same agent_id will update
        the existing record.

        Parameters
        ----------
        agent_id : str
            Unique identifier for the worker agent (e.g., "backend-dev-001")
            Must be unique across the Marcus system
        name : str
            Human-readable display name for the agent (e.g., "Backend Developer")
        role : str
            Agent's primary role or function (e.g., "Software Developer", "QA Engineer")
        skills : List[str]
            List of technical skills and capabilities the agent possesses
            (e.g., ["python", "fastapi", "postgresql", "docker"])

        Returns
        -------
        Dict[str, Any]
            Registration response containing:
            - success: bool indicating registration success
            - agent_id: str confirming the registered agent ID
            - message: str with registration status details
            - timestamp: str with registration time

        Raises
        ------
        RuntimeError
            If no active connection exists to Marcus server
        ValueError
            If required parameters are missing or invalid
        ConnectionError
            If communication with Marcus server fails

        Examples
        --------
        Register a backend developer:

        >>> client = WorkerMCPClient()
        >>> async with client.connect_to_marcus() as session:
        ...     result = await client.register_agent(
        ...         agent_id="backend-dev-001",
        ...         name="Backend Developer Alpha",
        ...         role="Software Developer",
        ...         skills=["python", "fastapi", "postgresql", "redis", "docker"]
        ...     )
        ...     print(f"Registration: {result['success']}")

        Register a frontend specialist:

        >>> result = await client.register_agent(
        ...     "frontend-dev-001",
        ...     "Frontend Specialist",
        ...     "UI/UX Developer",
        ...     ["javascript", "react", "typescript", "css", "webpack"]
        ... )

        Register a QA engineer:

        >>> result = await client.register_agent(
        ...     "qa-engineer-001",
        ...     "Quality Assurance Engineer",
        ...     "QA Engineer",
        ...     ["selenium", "pytest", "cypress", "performance-testing"]
        ... )

        Notes
        -----
        - Agent IDs should follow a consistent naming convention
        - Skills list helps Marcus with optimal task assignment
        - Role information is used for task categorization and routing
        - Registration must complete before requesting tasks
        """
        if not self.session:
            raise RuntimeError("Not connected to Marcus")

        result = await self.session.call_tool(
            "register_agent",
            arguments={
                "agent_id": agent_id,
                "name": name,
                "role": role,
                "skills": skills,
            },
        )

        text_content = _extract_text_from_result(result)
        return json.loads(text_content) if text_content else {}

    @retry_with_backoff(max_attempts=3, initial_delay=2.0)
    async def request_next_task(self, agent_id: str) -> Dict[str, Any]:
        """
        Request next available task assignment from Marcus.

        This method requests the next optimal task assignment for the specified
        agent from the Marcus server. The Marcus uses intelligent task
        routing based on agent skills, current workload, task priorities, and
        dependencies to assign the most appropriate task.

        If no tasks are available or suitable for the agent, an empty response
        is returned. Agents should implement polling or wait strategies when
        no tasks are available.

        Parameters
        ----------
        agent_id : str
            Unique identifier of the agent requesting a task
            Must match a previously registered agent ID

        Returns
        -------
        Dict[str, Any]
            Task assignment response containing:
            - task: Dict[str, Any] or None
                Task object with details if assigned, None if no tasks available
                Task object includes:
                - id: str - unique task identifier
                - title: str - task title/summary
                - description: str - detailed task description
                - priority: str - task priority level
                - estimated_hours: float - estimated completion time
                - labels: List[str] - task categorization labels
                - dependencies: List[str] - prerequisite task IDs
            - message: str - status message about task assignment
            - timestamp: str - assignment timestamp

        Raises
        ------
        RuntimeError
            If no active connection exists to Marcus server
        ValueError
            If agent_id is invalid or agent not registered
        ConnectionError
            If communication with Marcus server fails

        Examples
        --------
        Request task in work loop:

        >>> client = WorkerMCPClient()
        >>> async with client.connect_to_marcus() as session:
        ...     # Register first
        ...     await client.register_agent("dev-001", "Developer", "Engineer", ["python"])
        ...
        ...     # Request task
        ...     response = await client.request_next_task("dev-001")
        ...     if response.get('task'):
        ...         task = response['task']
        ...         print(f"Assigned task: {task['title']}")
        ...         print(f"Priority: {task['priority']}")
        ...         print(f"Estimated hours: {task['estimated_hours']}")
        ...     else:
        ...         print("No tasks available")

        Continuous task processing:

        >>> while True:
        ...     response = await client.request_next_task("dev-001")
        ...     task = response.get('task')
        ...
        ...     if not task:
        ...         await asyncio.sleep(30)  # Wait before next request
        ...         continue
        ...
        ...     # Process the assigned task
        ...     await process_task(task)
        ...
        ...     # Report completion
        ...     await client.report_task_progress(
        ...         "dev-001", task['id'], "completed", 100
        ...     )

        Handle task dependencies:

        >>> response = await client.request_next_task("dev-001")
        >>> task = response.get('task')
        >>> if task and task.get('dependencies'):
        ...     print(f"Task depends on: {task['dependencies']}")
        ...     # These dependencies should be completed first

        Notes
        -----
        - Agents should only request tasks when ready to work on them
        - Task assignment considers agent skills and current workload
        - Empty responses indicate no suitable tasks are currently available
        - Agents must report progress before requesting additional tasks
        - Task dependencies are automatically resolved by Marcus
        """
        if not self.session:
            raise RuntimeError("Not connected to Marcus")

        result = await self.session.call_tool(
            "request_next_task", arguments={"agent_id": agent_id}
        )

        text_content = _extract_text_from_result(result)
        return json.loads(text_content) if text_content else {}

    @retry_with_backoff(max_attempts=3, initial_delay=1.0, max_delay=30.0)
    async def report_task_progress(
        self,
        agent_id: str,
        task_id: str,
        status: str,
        progress: int = 0,
        message: str = "",
    ) -> Dict[str, Any]:
        """
        Report task progress and status updates to Marcus.

        This method allows agents to report their progress on assigned tasks,
        including status changes, completion percentages, and descriptive messages.
        Progress reporting is essential for project monitoring, coordination,
        and providing visibility into agent activities.

        Agents should report progress at key milestones (25%, 50%, 75%, 100%)
        and whenever status changes occur. The Marcus uses this information
        for real-time project tracking, dependency management, and resource
        allocation decisions.

        Parameters
        ----------
        agent_id : str
            Unique identifier of the agent reporting progress
            Must match a previously registered agent ID
        task_id : str
            Unique identifier of the task being updated
            Must match a task ID from a previous task assignment
        status : str
            Current task status, must be one of:
            - "in_progress": Task is actively being worked on
            - "completed": Task has been fully completed
            - "blocked": Task cannot proceed due to dependencies or issues
            - "paused": Task work has been temporarily suspended
        progress : int, optional
            Completion percentage from 0 to 100, by default 0
            Should reflect actual work completed, not time elapsed
        message : str, optional
            Descriptive message about current progress, by default ""
            Should provide meaningful details about what was accomplished

        Returns
        -------
        Dict[str, Any]
            Progress report response containing:
            - success: bool indicating if report was processed
            - task_id: str confirming the updated task
            - status: str confirming the new status
            - progress: int confirming the progress percentage
            - timestamp: str when the progress was recorded
            - message: str with any additional feedback

        Raises
        ------
        RuntimeError
            If no active connection exists to Marcus server
        ValueError
            If agent_id, task_id, or status values are invalid
            If progress is not between 0 and 100
        ConnectionError
            If communication with Marcus server fails

        Examples
        --------
        Report task start:

        >>> await client.report_task_progress(
        ...     agent_id="dev-001",
        ...     task_id="task-123",
        ...     status="in_progress",
        ...     progress=0,
        ...     message="Started analysis of requirements"
        ... )

        Report milestone progress:

        >>> await client.report_task_progress(
        ...     "dev-001", "task-123", "in_progress", 25,
        ...     "Completed database schema design and validation"
        ... )
        >>>
        >>> await client.report_task_progress(
        ...     "dev-001", "task-123", "in_progress", 50,
        ...     "Implemented core API endpoints with error handling"
        ... )
        >>>
        >>> await client.report_task_progress(
        ...     "dev-001", "task-123", "in_progress", 75,
        ...     "Added comprehensive test coverage and documentation"
        ... )

        Report task completion:

        >>> await client.report_task_progress(
        ...     "dev-001", "task-123", "completed", 100,
        ...     "Task completed successfully. All tests passing, deployed to staging."
        ... )

        Report blocked status:

        >>> await client.report_task_progress(
        ...     "dev-001", "task-123", "blocked", 30,
        ...     "Waiting for database migration approval from DevOps team"
        ... )

        Batch progress reporting:

        >>> progress_updates = [
        ...     (25, "Database setup complete"),
        ...     (50, "API implementation finished"),
        ...     (75, "Tests and documentation added"),
        ...     (100, "Task completed and verified")
        ... ]
        >>>
        >>> for progress, msg in progress_updates:
        ...     status = "completed" if progress == 100 else "in_progress"
        ...     await client.report_task_progress(
        ...         "dev-001", "task-123", status, progress, msg
        ...     )

        Notes
        -----
        - Progress should be reported honestly and reflect actual completion
        - Status "completed" should only be used when task is fully finished
        - Descriptive messages help with project coordination and debugging
        - Progress reports are used for dependency tracking and scheduling
        - Frequent updates provide better visibility but avoid spam reporting
        """
        if not self.session:
            raise RuntimeError("Not connected to Marcus")

        result = await self.session.call_tool(
            "report_task_progress",
            arguments={
                "agent_id": agent_id,
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "message": message,
            },
        )

        text_content = _extract_text_from_result(result)
        return json.loads(text_content) if text_content else {}

    @retry_with_backoff(max_attempts=3, initial_delay=1.0, max_delay=30.0)
    async def report_blocker(
        self,
        agent_id: str,
        task_id: str,
        blocker_description: str,
        severity: str = "medium",
    ) -> Dict[str, Any]:
        """
        Report task blockers to Marcus for AI assistance and resolution.

        This method allows agents to report issues that prevent task completion,
        triggering AI-powered analysis and recommendation systems. The Marcus
        can provide suggested solutions, escalate to human oversight, or
        reassign tasks based on blocker severity and type.

        Blockers are categorized by severity and analyzed for patterns that
        might indicate systemic issues. The AI analysis engine can suggest
        solutions, alternative approaches, or resource adjustments to resolve
        blockers efficiently.

        Parameters
        ----------
        agent_id : str
            Unique identifier of the agent reporting the blocker
            Must match a previously registered agent ID
        task_id : str
            Unique identifier of the blocked task
            Must match a task ID from a previous task assignment
        blocker_description : str
            Detailed description of the blocking issue
            Should include error messages, context, and attempted solutions
        severity : str, optional
            Severity level of the blocker, by default "medium"
            Must be one of:
            - "low": Minor issue that doesn't prevent progress
            - "medium": Significant issue that slows progress
            - "high": Critical issue that completely blocks progress

        Returns
        -------
        Dict[str, Any]
            Blocker report response containing:
            - success: bool indicating if blocker was recorded
            - blocker_id: str unique identifier for this blocker
            - suggestions: List[str] AI-generated resolution suggestions
            - escalated: bool whether issue was escalated for human review
            - estimated_resolution_time: str predicted time to resolve
            - related_blockers: List[str] similar issues across the project
            - timestamp: str when the blocker was reported

        Raises
        ------
        RuntimeError
            If no active connection exists to Marcus server
        ValueError
            If agent_id, task_id, or severity values are invalid
            If blocker_description is empty or too short
        ConnectionError
            If communication with Marcus server fails

        Examples
        --------
        Report a database connection issue:

        >>> await client.report_blocker(
        ...     agent_id="dev-001",
        ...     task_id="task-456",
        ...     blocker_description='''
        ...     Cannot connect to PostgreSQL database. Error:
        ...     "connection to server on socket failed: No such file or directory"
        ...
        ...     Attempted solutions:
        ...     1. Verified PostgreSQL service is running
        ...     2. Checked connection string configuration
        ...     3. Tested network connectivity
        ...
        ...     Environment: Local development, macOS, PostgreSQL 14
        ...     ''',
        ...     severity="high"
        ... )

        Report a dependency conflict:

        >>> await client.report_blocker(
        ...     "dev-001", "task-789",
        ...     '''
        ...     Package dependency conflict preventing installation:
        ...     requests==2.25.1 conflicts with urllib3>=1.26.0,<1.27
        ...
        ...     Current environment uses requests for API calls,
        ...     new package requires incompatible urllib3 version.
        ...     ''',
        ...     "medium"
        ... )

        Report missing documentation:

        >>> await client.report_blocker(
        ...     "dev-001", "task-321",
        ...     "API endpoint documentation missing for /api/v2/users. "
        ...     "Cannot implement frontend integration without knowing "
        ...     "expected request/response format and authentication requirements.",
        ...     "low"
        ... )

        Report environmental issue:

        >>> response = await client.report_blocker(
        ...     "qa-001", "task-654",
        ...     '''
        ...     Test environment not accessible. Staging server returns 502 Bad Gateway.
        ...
        ...     Error occurs for all API endpoints. Browser shows:
        ...     "502 Bad Gateway - nginx/1.18.0"
        ...
        ...     Cannot complete integration testing without working environment.
        ...     ''',
        ...     "high"
        ... )
        >>>
        >>> # Check AI suggestions
        >>> for suggestion in response.get('suggestions', []):
        ...     print(f"Suggestion: {suggestion}")

        Handle blocker response:

        >>> response = await client.report_blocker(
        ...     "dev-001", "task-123", "Complex blocker description", "medium"
        ... )
        >>>
        >>> if response.get('escalated'):
        ...     print("Blocker escalated to human review")
        >>>
        >>> if response.get('suggestions'):
        ...     print("AI suggestions available:")
        ...     for i, suggestion in enumerate(response['suggestions'], 1):
        ...         print(f"{i}. {suggestion}")

        Notes
        -----
        - Provide detailed blocker descriptions for better AI analysis
        - Include error messages, logs, and attempted solutions
        - Use appropriate severity levels to prioritize resolution
        - AI suggestions may include alternative approaches or workarounds
        - High severity blockers may trigger immediate human notification
        - Related blockers help identify systemic project issues
        """
        if not self.session:
            raise RuntimeError("Not connected to Marcus")

        result = await self.session.call_tool(
            "report_blocker",
            arguments={
                "agent_id": agent_id,
                "task_id": task_id,
                "blocker_description": blocker_description,
                "severity": severity,
            },
        )

        text_content = _extract_text_from_result(result)
        return json.loads(text_content) if text_content else {}

    async def get_project_status(self) -> Dict[str, Any]:
        """
        Retrieve current project status and metrics from Marcus.

        This method fetches comprehensive project status information including
        task progress, agent activities, performance metrics, and overall
        project health indicators. The status information helps agents
        understand the broader project context and make informed decisions
        about their work priorities.

        The project status includes real-time metrics about task completion
        rates, agent productivity, blocker resolution times, and resource
        utilization across the entire project ecosystem.

        Returns
        -------
        Dict[str, Any]
            Project status response containing:
            - project_info: Dict[str, Any]
                Basic project information:
                - id: str - unique project identifier
                - name: str - project display name
                - start_date: str - project start timestamp
                - target_completion: str - planned completion date
                - status: str - overall project status
            - task_metrics: Dict[str, Any]
                Task-related statistics:
                - total_tasks: int - total number of tasks
                - completed_tasks: int - number of completed tasks
                - in_progress_tasks: int - actively worked tasks
                - blocked_tasks: int - tasks with blockers
                - pending_tasks: int - unassigned tasks
                - completion_rate: float - percentage of tasks completed
            - agent_metrics: Dict[str, Any]
                Agent activity statistics:
                - total_agents: int - number of registered agents
                - active_agents: int - currently working agents
                - idle_agents: int - agents waiting for tasks
                - avg_tasks_per_agent: float - task distribution metric
            - performance_metrics: Dict[str, Any]
                Performance indicators:
                - avg_task_completion_time: float - hours per task
                - blocker_resolution_time: float - average blocker resolution
                - throughput: float - tasks completed per day
                - efficiency_score: float - overall productivity metric
            - recent_activity: List[Dict[str, Any]]
                Recent project events and milestones
            - health_indicators: Dict[str, Any]
                Project health status:
                - overall_health: str - green/yellow/red status
                - risk_factors: List[str] - identified project risks
                - recommendations: List[str] - suggested improvements
            - timestamp: str - when status was generated

        Raises
        ------
        RuntimeError
            If no active connection exists to Marcus server
        ConnectionError
            If communication with Marcus server fails
        PermissionError
            If agent doesn't have permission to view project status

        Examples
        --------
        Basic status check:

        >>> status = await client.get_project_status()
        >>> print(f"Project: {status['project_info']['name']}")
        >>> print(f"Overall Status: {status['project_info']['status']}")
        >>> print(f"Tasks Completed: {status['task_metrics']['completed_tasks']}")
        >>> print(f"Active Agents: {status['agent_metrics']['active_agents']}")

        Monitor project health:

        >>> status = await client.get_project_status()
        >>> health = status['health_indicators']
        >>>
        >>> print(f"Project Health: {health['overall_health']}")
        >>> if health['risk_factors']:
        ...     print("Risk Factors:")
        ...     for risk in health['risk_factors']:
        ...         print(f"  - {risk}")
        >>>
        >>> if health['recommendations']:
        ...     print("Recommendations:")
        ...     for rec in health['recommendations']:
        ...         print(f"  - {rec}")

        Track progress metrics:

        >>> status = await client.get_project_status()
        >>> metrics = status['task_metrics']
        >>>
        >>> completion_pct = (metrics['completed_tasks'] / metrics['total_tasks']) * 100
        >>> print(f"Project Progress: {completion_pct:.1f}%")
        >>>
        >>> if metrics['blocked_tasks'] > 0:
        ...     print(f"Warning: {metrics['blocked_tasks']} blocked tasks")

        Performance analysis:

        >>> status = await client.get_project_status()
        >>> perf = status['performance_metrics']
        >>>
        >>> print(f"Average task completion: {perf['avg_task_completion_time']:.1f} hours")
        >>> print(f"Daily throughput: {perf['throughput']:.1f} tasks/day")
        >>> print(f"Efficiency score: {perf['efficiency_score']:.2f}")

        Review recent activity:

        >>> status = await client.get_project_status()
        >>> print("Recent Activity:")
        >>> for activity in status['recent_activity'][-5:]:  # Last 5 events
        ...     print(f"  {activity['timestamp']}: {activity['description']}")

        Agent status overview:

        >>> status = await client.get_project_status()
        >>> agents = status['agent_metrics']
        >>>
        >>> utilization = (agents['active_agents'] / agents['total_agents']) * 100
        >>> print(f"Agent Utilization: {utilization:.1f}%")
        >>> print(f"Idle Agents: {agents['idle_agents']}")

        Notes
        -----
        - Status information is real-time but may have slight delays
        - Metrics are calculated based on recent activity windows
        - Health indicators use predictive algorithms for risk assessment
        - Performance metrics help identify optimization opportunities
        - Status data can be used for automated decision making
        - Large projects may have paginated or summarized data
        """
        if not self.session:
            raise RuntimeError("Not connected to Marcus")

        result = await self.session.call_tool("get_project_status", arguments={})

        text_content = _extract_text_from_result(result)
        return json.loads(text_content) if text_content else {}
