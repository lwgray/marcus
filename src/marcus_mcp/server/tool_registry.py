"""
Tool registration for Marcus server.

This module handles registering all tools with FastMCP instances,
organizing the registration by tool category and endpoint type.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

# Import all tool functions
from src.marcus_mcp.tools import (
    add_feature,
    check_assignment_health,
    create_project,
    get_agent_status,
    get_project_status,
    get_task_context,
    list_registered_agents,
    log_artifact,
    ping,
    register_agent,
    report_blocker,
    report_task_progress,
    request_next_task,
)
from src.marcus_mcp.tools.analytics import (
    get_agent_metrics,
    get_project_metrics,
    get_system_metrics,
    get_task_metrics,
)
from src.marcus_mcp.tools.audit_tools import get_usage_report
from src.marcus_mcp.tools.auth import authenticate
from src.marcus_mcp.tools.board_health import (
    check_board_health,
    check_task_dependencies,
)
from src.marcus_mcp.tools.code_metrics import get_code_metrics

# from src.marcus_mcp.tools.decision import log_decision  # Not implemented yet
from src.marcus_mcp.tools.nlp import add_feature as add_feature_nlp
from src.marcus_mcp.tools.nlp import create_project as create_project_nlp

# NOTE: These NLP tools are not yet implemented
# from src.marcus_mcp.tools.nlp import (
#     analyze_task_clarity,
#     extract_entities,
#     generate_task_summary,
#     suggest_task_labels,
# )
from src.marcus_mcp.tools.project_management import (
    get_current_project,
    list_projects,
    switch_project,
)

# from src.marcus_mcp.tools.security import validate_token  # Not implemented yet

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Manages tool registration for FastMCP instances."""

    def __init__(self, server):
        """
        Initialize tool registry.

        Args:
        ----
            server: The MarcusServer instance
        """
        self.server = server

    def register_fastmcp_tools(self, app: FastMCP) -> None:
        """
        Register all tools with a FastMCP instance.

        Args:
        ----
            app: The FastMCP instance to register tools with
        """
        # Register core tools
        self._register_core_tools(app)

        # Register analytics tools
        self._register_analytics_tools(app)

        # Register project management tools
        self._register_project_tools(app)

        # Register health check tools
        self._register_health_tools(app)

        # Register NLP tools if enabled
        if self.server.config.get("features.nlp_tools.enabled", False):
            self._register_nlp_tools(app)

        # Register code analysis tools if GitHub
        if self.server.provider == "github":
            self._register_code_analysis_tools(app)

        # FastMCP doesn't expose tool count directly
        logger.info("Registered tools with FastMCP")

    def register_endpoint_tools(self, app: FastMCP, endpoint_type: str) -> None:
        """
        Register endpoint-specific tools.

        Args:
        ----
            app: The FastMCP instance
            endpoint_type: Type of endpoint (agent, admin, public)
        """
        if endpoint_type == "agent":
            self._register_agent_endpoint_tools(app)
        elif endpoint_type == "admin":
            self._register_admin_endpoint_tools(app)
        elif endpoint_type == "public":
            self._register_public_endpoint_tools(app)
        else:
            logger.warning(f"Unknown endpoint type: {endpoint_type}")
            # Register default tools
            self._register_core_tools(app)

    def _register_core_tools(self, app: FastMCP) -> None:
        """Register core system tools."""

        @app.tool(
            name="ping", description="Check if the server is alive and responding"
        )
        async def ping_tool(echo: str = "") -> Dict[str, Any]:
            """Health check endpoint."""
            return await ping(echo, self.server)

        @app.tool(
            name="register_agent", description="Register a new agent with the system"
        )
        async def register_agent_tool(
            agent_id: str, capabilities: List[str]
        ) -> Dict[str, Any]:
            """Register a new agent."""
            return await register_agent(agent_id, capabilities, self.server)

        @app.tool(
            name="get_agent_status", description="Get the current status of an agent"
        )
        async def get_agent_status_tool(agent_id: str) -> Dict[str, Any]:
            """Get agent status."""
            return await get_agent_status(agent_id, self.server)

        @app.tool(
            name="request_next_task",
            description="Request the next task assignment for an agent",
        )
        async def request_next_task_tool(agent_id: str) -> Dict[str, Any]:
            """Request next task."""
            return await request_next_task(agent_id, self.server)

        @app.tool(
            name="report_task_progress",
            description="Report progress on an assigned task",
        )
        async def report_task_progress_tool(
            agent_id: str,
            task_id: str,
            status: str,
            progress_percentage: int,
            message: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Report task progress."""
            return await report_task_progress(
                agent_id, task_id, status, progress_percentage, self.server, message
            )

        @app.tool(
            name="report_blocker",
            description="Report a blocker preventing task completion",
        )
        async def report_blocker_tool(
            agent_id: str,
            task_id: str,
            blocker_description: str,
            suggested_resolution: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Report a blocker."""
            return await report_blocker(
                agent_id,
                task_id,
                blocker_description,
                self.server,
                suggested_resolution,
            )

        @app.tool(
            name="get_project_status",
            description="Get the current project status and metrics",
        )
        async def get_project_status_tool() -> Dict[str, Any]:
            """Get project status."""
            return await get_project_status(self.server)

        @app.tool(
            name="create_project",
            description="Create a new project (multi-project mode only)",
        )
        async def create_project_tool(
            name: str, board_name: str, description: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a new project."""
            return await create_project(name, board_name, self.server, description)

    def _register_analytics_tools(self, app: FastMCP) -> None:
        """Register analytics tools."""

        @app.tool(
            name="get_agent_metrics",
            description="Get performance metrics for a specific agent",
        )
        async def get_agent_metrics_tool(
            agent_id: str, time_window: Optional[str] = "24h"
        ) -> Dict[str, Any]:
            """Get agent metrics."""
            return await get_agent_metrics(agent_id, time_window, self.server)

        @app.tool(
            name="get_project_metrics",
            description="Get overall project metrics and statistics",
        )
        async def get_project_metrics_tool(
            time_window: Optional[str] = "7d",
        ) -> Dict[str, Any]:
            """Get project metrics."""
            return await get_project_metrics(time_window, self.server)

        @app.tool(
            name="get_system_metrics", description="Get system-wide performance metrics"
        )
        async def get_system_metrics_tool() -> Dict[str, Any]:
            """Get system metrics."""
            return await get_system_metrics(self.server)

        @app.tool(
            name="get_task_metrics", description="Get metrics for a specific task"
        )
        async def get_task_metrics_tool(task_id: str) -> Dict[str, Any]:
            """Get task metrics."""
            return await get_task_metrics(task_id, self.server)

    def _register_project_tools(self, app: FastMCP) -> None:
        """Register project management tools."""
        if self.server.is_multi_project_mode:

            @app.tool(name="list_projects", description="List all available projects")
            async def list_projects_tool() -> Dict[str, Any]:
                """List projects."""
                return await list_projects(self.server)

            @app.tool(
                name="switch_project", description="Switch to a different project"
            )
            async def switch_project_tool(project_name: str) -> Dict[str, Any]:
                """Switch project."""
                return await switch_project(project_name, self.server)

            @app.tool(
                name="get_current_project",
                description="Get the name of the current active project",
            )
            async def get_current_project_tool() -> Dict[str, Any]:
                """Get current project."""
                return await get_current_project(self.server)

        @app.tool(
            name="add_feature",
            description="Add a new feature/user story to the project",
        )
        async def add_feature_tool(
            title: str,
            description: str,
            acceptance_criteria: List[str],
            priority: Optional[str] = "medium",
        ) -> Dict[str, Any]:
            """Add a new feature."""
            return await add_feature(
                title, description, acceptance_criteria, self.server, priority
            )

    def _register_health_tools(self, app: FastMCP) -> None:
        """Register health check tools."""

        @app.tool(
            name="check_board_health",
            description="Check the health of the project board",
        )
        async def check_board_health_tool() -> Dict[str, Any]:
            """Check board health."""
            return await check_board_health(self.server)

        @app.tool(
            name="check_task_dependencies",
            description="Analyze task dependencies and identify issues",
        )
        async def check_task_dependencies_tool() -> Dict[str, Any]:
            """Check task dependencies."""
            return await check_task_dependencies(self.server)

        @app.tool(
            name="check_assignment_health",
            description="Check the health of current task assignments",
        )
        async def check_assignment_health_tool() -> Dict[str, Any]:
            """Check assignment health."""
            return await check_assignment_health(self.server)

    def _register_nlp_tools(self, app: FastMCP) -> None:
        """Register NLP analysis tools."""
        # NOTE: These NLP analysis tools are not yet implemented
        # @app.tool(
        #     name="analyze_task_clarity",
        #     description="Analyze the clarity and completeness of a task description",
        # )
        # async def analyze_task_clarity_tool(task_description: str) -> Dict[str, Any]:
        #     """Analyze task clarity."""
        #     return await analyze_task_clarity(task_description, self.server)

        # @app.tool(
        #     name="generate_task_summary",
        #     description="Generate a concise summary of a task",
        # )
        # async def generate_task_summary_tool(
        #     task_description: str, max_length: Optional[int] = 100
        # ) -> Dict[str, Any]:
        #     """Generate task summary."""
        #     return await generate_task_summary(
        #         task_description, self.server, max_length
        #     )

        # @app.tool(
        #     name="extract_entities",
        #     description="Extract entities (technologies, components, etc.) from text",
        # )
        # async def extract_entities_tool(text: str) -> Dict[str, Any]:
        #     """Extract entities."""
        #     return await extract_entities(text, self.server)

        # @app.tool(
        #     name="suggest_task_labels",
        #     description="Suggest appropriate labels for a task",
        # )
        # async def suggest_task_labels_tool(task_description: str) -> Dict[str, Any]:
        #     """Suggest task labels."""
        #     return await suggest_task_labels(task_description, self.server)

        # Register the actual NLP tools that exist
        @app.tool(
            name="create_project_from_description",
            description="Create a new project from natural language description",
        )
        async def create_project_from_description_tool(
            description: str, project_name: str
        ) -> Dict[str, Any]:
            """Create project from natural language."""
            return await create_project_nlp(description, project_name, self.server)

        @app.tool(
            name="add_feature_to_project",
            description="Add a feature to existing project using natural language",
        )
        async def add_feature_to_project_tool(
            feature_description: str,
        ) -> Dict[str, Any]:
            """Add feature from natural language."""
            return await add_feature_nlp(feature_description, self.server)

    def _register_code_analysis_tools(self, app: FastMCP) -> None:
        """Register code analysis tools (GitHub only)."""

        @app.tool(
            name="get_code_metrics",
            description="Get code metrics for the project repository",
        )
        async def get_code_metrics_tool() -> Dict[str, Any]:
            """Get code metrics."""
            return await get_code_metrics(self.server)

        # NOTE: These tools are not yet implemented in code_metrics.py
        # @app.tool(
        #     name="analyze_code_changes",
        #     description="Analyze code changes in a pull request",
        # )
        # async def analyze_code_changes_tool(pr_number: int) -> Dict[str, Any]:
        #     """Analyze code changes."""
        #     return await analyze_code_changes(pr_number, self.server)

        # @app.tool(
        #     name="get_pr_complexity",
        #     description="Calculate complexity score for a pull request",
        # )
        # async def get_pr_complexity_tool(pr_number: int) -> Dict[str, Any]:
        #     """Get PR complexity."""
        #     return await get_pr_complexity(pr_number, self.server)

        # @app.tool(
        #     name="analyze_pr_impact",
        #     description="Analyze the potential impact of a pull request",
        # )
        # async def analyze_pr_impact_tool(pr_number: int) -> Dict[str, Any]:
        #     """Analyze PR impact."""
        #     return await analyze_pr_impact(pr_number, self.server)

    def _register_agent_endpoint_tools(self, app: FastMCP) -> None:
        """Register tools specific to agent endpoints."""
        # Agents get core tools plus some extras
        self._register_core_tools(app)
        self._register_analytics_tools(app)

        # Add authentication for agents
        @app.tool(
            name="authenticate",
            description="Authenticate an agent and get an access token",
        )
        async def authenticate_tool(
            agent_id: str, secret: Optional[str] = None
        ) -> Dict[str, Any]:
            """Authenticate agent."""
            return await authenticate(agent_id, self.server, secret)

        # Add context tools
        @app.tool(
            name="get_task_context", description="Get enriched context for a task"
        )
        async def get_task_context_tool(task_id: str) -> Dict[str, Any]:
            """Get task context."""
            return await get_task_context(task_id, self.server)

        # NOTE: Decision logging not yet implemented
        # # Add decision logging
        # @app.tool(
        #     name="log_decision",
        #     description="Log an important decision made during task execution",
        # )
        # async def log_decision_tool(
        #     task_id: str,
        #     decision_type: str,
        #     description: str,
        #     rationale: str,
        #     alternatives: Optional[List[str]] = None,
        # ) -> Dict[str, Any]:
        #     """Log decision."""
        #     return await log_decision(
        #         task_id,
        #         decision_type,
        #         description,
        #         rationale,
        #         self.server,
        #         alternatives,
        #     )

        # Add artifact logging
        @app.tool(
            name="log_artifact",
            description="Log an artifact created during task execution",
        )
        async def log_artifact_tool(
            task_id: str,
            artifact_type: str,
            name: str,
            location: str,
            metadata: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Any]:
            """Log artifact."""
            return await log_artifact(
                task_id, artifact_type, name, location, self.server, metadata
            )

    def _register_admin_endpoint_tools(self, app: FastMCP) -> None:
        """Register tools specific to admin endpoints."""
        # Admins get everything
        self.register_fastmcp_tools(app)

        # Add admin-specific tools
        @app.tool(
            name="list_registered_agents",
            description="List all registered agents and their status",
        )
        async def list_registered_agents_tool() -> Dict[str, Any]:
            """List all agents."""
            return await list_registered_agents(self.server)

        @app.tool(
            name="get_usage_report",
            description="Get detailed usage report for cost tracking",
        )
        async def get_usage_report_tool(
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            group_by: Optional[str] = "day",
        ) -> Dict[str, Any]:
            """Get usage report."""
            return await get_usage_report(self.server, start_date, end_date, group_by)

        # NOTE: Token validation not yet implemented
        # # Add token validation
        # @app.tool(name="validate_token", description="Validate an authentication token")
        # async def validate_token_tool(token: str) -> Dict[str, Any]:
        #     """Validate token."""
        #     return await validate_token(token, self.server)

    def _register_public_endpoint_tools(self, app: FastMCP) -> None:
        """Register tools specific to public endpoints."""
        # Public endpoints get limited tools

        @app.tool(name="ping", description="Check if the server is alive")
        async def ping_tool(echo: str = "") -> Dict[str, Any]:
            """Health check."""
            return await ping(echo, self.server)

        @app.tool(name="get_project_status", description="Get public project status")
        async def get_project_status_tool() -> Dict[str, Any]:
            """Get project status."""
            # Return limited info for public
            status = await get_project_status(self.server)
            # Filter sensitive data
            return {
                "tasks_completed": status.get("tasks_completed", 0),
                "tasks_in_progress": status.get("tasks_in_progress", 0),
                "health_score": status.get("health_score", 0),
            }
