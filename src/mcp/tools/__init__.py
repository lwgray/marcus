"""
MCP Tools Package

This package contains all MCP tool implementations organized by domain:
- agent_tools: Agent management (register, status, list)
- task_tools: Task operations (request, progress, blockers)
- project_tools: Project monitoring
- system_tools: System health and diagnostics
- nlp_tools: Natural language processing tools
"""

from .agent_tools import (
    register_agent,
    get_agent_status,
    list_registered_agents
)

from .task_tools import (
    request_next_task,
    report_task_progress,
    report_blocker
)

from .project_tools import (
    get_project_status
)

from .system_tools import (
    ping,
    check_assignment_health
)

from .nlp_tools import (
    create_project,
    add_feature
)

__all__ = [
    # Agent tools
    'register_agent',
    'get_agent_status', 
    'list_registered_agents',
    # Task tools
    'request_next_task',
    'report_task_progress',
    'report_blocker',
    # Project tools
    'get_project_status',
    # System tools
    'ping',
    'check_assignment_health',
    # NLP tools
    'create_project',
    'add_feature'
]