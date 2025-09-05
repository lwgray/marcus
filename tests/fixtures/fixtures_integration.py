"""
Integration fixtures for Marcus testing.

Provides real integration objects for testing external service
integrations, API clients, and cross-system communication.
"""

import pytest
import os
from typing import Dict, Any, List
from datetime import datetime

from src.integrations.kanban_interface import KanbanInterface


@pytest.fixture
def test_environment_config():
    """Create test environment configuration."""
    return {
        "kanban_provider": "planka",
        "kanban_base_url": "http://localhost:3333",
        "kanban_email": "demo@demo.demo", 
        "kanban_password": "demo",
        "project_id": "1533678301472621705",  # Task Master Test
        "test_mode": True,
        "cleanup_after_tests": True,
    }


@pytest.fixture
def real_kanban_client(test_environment_config):
    """Create a real Kanban client for integration testing.
    
    Note: This requires the Kanban MCP server to be running.
    Mark tests using this fixture with @pytest.mark.integration
    """
    # Only create real client if environment is set up
    if all(key in os.environ for key in ["PLANKA_BASE_URL", "PLANKA_AGENT_EMAIL"]):
        # Return actual client - implementation depends on your KanbanInterface
        return KanbanInterface(
            provider="planka",
            base_url=os.environ["PLANKA_BASE_URL"],
            credentials={
                "email": os.environ["PLANKA_AGENT_EMAIL"],
                "password": os.environ["PLANKA_AGENT_PASSWORD"],
            }
        )
    else:
        pytest.skip("Integration test environment not configured")


@pytest.fixture
def sample_board_data():
    """Create sample board data for testing."""
    return {
        "id": "board-001",
        "name": "Test Development Board",
        "description": "Board for testing development tasks",
        "project_id": "project-001",
        "lists": [
            {"id": "list-001", "name": "Backlog", "position": 1},
            {"id": "list-002", "name": "In Progress", "position": 2}, 
            {"id": "list-003", "name": "Review", "position": 3},
            {"id": "list-004", "name": "Done", "position": 4},
        ],
        "members": [
            {"id": "user-001", "name": "Developer 1", "role": "developer"},
            {"id": "user-002", "name": "Developer 2", "role": "developer"},
        ],
        "created_at": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_kanban_task():
    """Create sample Kanban task data."""
    return {
        "id": "kanban-task-001",
        "name": "Implement user registration",
        "description": "Create user registration endpoint with validation",
        "list_id": "list-001",
        "position": 1,
        "labels": ["backend", "api"],
        "assignees": ["user-001"],
        "due_date": (datetime.now().replace(hour=23, minute=59, second=59)).isoformat(),
        "estimated_hours": 6.0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@pytest.fixture
def api_response_templates():
    """Create templates for API responses."""
    return {
        "success": {
            "success": True,
            "data": {},
            "message": "Operation completed successfully",
            "timestamp": datetime.now().isoformat(),
        },
        "error": {
            "success": False,
            "error": {
                "code": "OPERATION_FAILED", 
                "message": "The operation could not be completed",
                "details": {},
            },
            "timestamp": datetime.now().isoformat(),
        },
        "task_created": {
            "success": True,
            "data": {
                "task": {
                    "id": "new-task-id",
                    "name": "Created task",
                    "status": "created",
                }
            },
            "message": "Task created successfully",
        }
    }


@pytest.fixture
def integration_test_data():
    """Create comprehensive test data for integration scenarios."""
    return {
        "project": {
            "id": "int-project-001",
            "name": "Integration Test Project",
            "boards": ["board-001", "board-002"],
        },
        "tasks": [
            {
                "id": "int-task-001",
                "name": "Setup CI/CD pipeline",
                "type": "infrastructure",
                "priority": "high",
                "estimated_hours": 8.0,
            },
            {
                "id": "int-task-002", 
                "name": "Implement error handling",
                "type": "enhancement",
                "priority": "medium",
                "estimated_hours": 4.0,
            },
        ],
        "agents": [
            {
                "id": "int-agent-001",
                "name": "Integration Tester",
                "skills": ["testing", "automation", "ci/cd"],
                "availability": True,
            }
        ],
    }