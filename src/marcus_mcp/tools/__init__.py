"""
MCP Tools Package

This package contains all MCP tool implementations organized by domain:
- agent: Agent management (register, status, list)
- task: Task operations (request, progress, blockers)
- project: Project monitoring
- system: System health and diagnostics
- nlp: Natural language processing tools
"""

from .agent import get_agent_status, list_registered_agents, register_agent
from .nlp import add_feature, create_project
from .project import get_project_status
from .system import check_assignment_health, ping
from .task import report_blocker, report_task_progress, request_next_task

__all__ = [
    # Agent tools
    "register_agent",
    "get_agent_status",
    "list_registered_agents",
    # Task tools
    "request_next_task",
    "report_task_progress",
    "report_blocker",
    # Project tools
    "get_project_status",
    # System tools
    "ping",
    "check_assignment_health",
    # NLP tools
    "create_project",
    "add_feature",
]
