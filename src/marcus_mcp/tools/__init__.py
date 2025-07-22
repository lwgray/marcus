"""
MCP Tools Package

This package contains all MCP tool implementations organized by domain:
- agent: Agent management (register, status, list)
- task: Task operations (request, progress, blockers)
- attachment: Design artifact sharing (upload, download, list)
- project: Project monitoring
- system: System health and diagnostics
- nlp: Natural language processing tools
"""

from .agent import get_agent_status, list_registered_agents, register_agent
from .attachment import (
    download_design_artifact,
    get_dependency_artifacts,
    list_design_artifacts,
    upload_design_artifact,
)
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
    # Attachment tools
    "upload_design_artifact",
    "download_design_artifact",
    "list_design_artifacts",
    "get_dependency_artifacts",
    # Project tools
    "get_project_status",
    # System tools
    "ping",
    "check_assignment_health",
    # NLP tools
    "create_project",
    "add_feature",
]
