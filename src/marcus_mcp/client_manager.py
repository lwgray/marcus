"""
Client session management for role-based access control.

This module manages client sessions and their associated permissions,
allowing dynamic tool access based on client roles.
"""

import asyncio
import asyncio.tasks as asyncio_tasks
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from mcp.types import Tool

from .tools.auth import DEFAULT_TOOLS, ROLE_TOOLS


class ClientSession:
    """Represents a connected client session with role-based permissions."""

    def __init__(self, session_id: str, transport: str = "stdio"):
        self.session_id = session_id
        self.transport = transport
        self.client_id: Optional[str] = None
        self.client_type: Optional[str] = None
        self.role: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
        self.connected_at = datetime.now()
        self.last_activity = datetime.now()
        self.allowed_tools: Set[str] = set(DEFAULT_TOOLS)
        self.authenticated = False

    def authenticate(
        self,
        client_id: str,
        client_type: str,
        role: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Authenticate the client and set permissions."""
        self.client_id = client_id
        self.client_type = client_type
        self.role = role
        self.metadata = metadata or {}
        self.authenticated = True

        # Update allowed tools based on client type
        tools = ROLE_TOOLS.get(client_type, DEFAULT_TOOLS)
        if isinstance(tools, list):
            self.allowed_tools = set(tools)
        # else case is unreachable since we always get a list or use DEFAULT_TOOLS

    def has_access_to_tool(self, tool_name: str) -> bool:
        """Check if client has access to a specific tool."""
        if "*" in self.allowed_tools:
            return True
        return tool_name in self.allowed_tools

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()


class ClientManager:
    """Manages client sessions and role-based access control."""

    def __init__(self, server_instance: Any):
        self.server = server_instance
        self.sessions: Dict[str, ClientSession] = {}
        self._cleanup_task: Optional[asyncio_tasks.Task[None]] = None

    async def start(self) -> None:
        """Start the client manager."""
        # Start cleanup task for expired sessions
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())

    async def stop(self) -> None:
        """Stop the client manager."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    def create_session(
        self, session_id: str, transport: str = "stdio"
    ) -> ClientSession:
        """Create a new client session."""
        session = ClientSession(session_id, transport)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ClientSession]:
        """Get a client session by ID."""
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str) -> None:
        """Remove a client session."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    async def authenticate_client(
        self,
        session_id: str,
        client_id: str,
        client_type: str,
        role: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Authenticate a client and update their permissions."""
        session = self.get_session(session_id)
        if not session:
            return False

        # Authenticate the session
        session.authenticate(client_id, client_type, role, metadata)

        # Log authentication
        self.server.log_event(
            "client_authenticated",
            {
                "session_id": session_id,
                "client_id": client_id,
                "client_type": client_type,
                "role": role,
                "transport": session.transport,
            },
        )

        # If using stdio transport with MCP server, notify tool list change
        if hasattr(self.server, "server") and hasattr(
            self.server.server, "notification"
        ):
            try:
                # Send notification that tools have changed
                await self.server.server.notification(
                    method="notifications/tools/list_changed"
                )
            except Exception as e:
                # Log but don't fail authentication
                self.server.log_event(
                    "notification_error",
                    {"error": str(e), "notification": "tools/list_changed"},
                )

        return True

    def get_session_tools(self, session_id: str) -> Set[str]:
        """Get allowed tools for a session."""
        session = self.get_session(session_id)
        if not session:
            return set(DEFAULT_TOOLS)
        return session.allowed_tools

    def has_tool_access(self, session_id: str, tool_name: str) -> bool:
        """Check if a session has access to a tool."""
        session = self.get_session(session_id)
        if not session:
            # Allow default tools for unknown sessions
            return tool_name in DEFAULT_TOOLS
        return session.has_access_to_tool(tool_name)

    async def _cleanup_expired_sessions(self) -> None:
        """Periodically clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                now = datetime.now()
                expired_sessions = []

                for session_id, session in self.sessions.items():
                    # Remove sessions inactive for more than 1 hour
                    if (now - session.last_activity).seconds > 3600:
                        expired_sessions.append(session_id)

                for session_id in expired_sessions:
                    self.remove_session(session_id)
                    self.server.log_event("session_expired", {"session_id": session_id})

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.server.log_event("cleanup_error", {"error": str(e)})
