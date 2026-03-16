"""
Core domain fixtures for Marcus testing.

Provides real implementations for core Marcus components including
tasks, projects, agents, and basic data structures.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from src.core.context import Context
from src.core.models import Priority, Task, TaskStatus, WorkerStatus


@pytest.fixture
def sample_task():
    """Create a real sample task for testing."""
    return Task(
        id="task-001",
        name="Implement user authentication",
        description="Add login and signup functionality with OAuth support",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=datetime.now(timezone.utc) + timedelta(days=7),
        estimated_hours=8.0,
        labels=["backend", "security", "authentication"],
    )


@pytest.fixture
def sample_high_priority_task():
    """Create a high priority task for testing."""
    return Task(
        id="task-002",
        name="Fix critical database bug",
        description="Database connection failing intermittently",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.CRITICAL,
        assigned_to="agent-001",
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        updated_at=datetime.now(timezone.utc),
        due_date=datetime.now(timezone.utc) + timedelta(hours=6),
        estimated_hours=4.0,
        labels=["backend", "database", "bugfix"],
    )


@pytest.fixture
def sample_completed_task():
    """Create a completed task for testing."""
    return Task(
        id="task-003",
        name="Update documentation",
        description="Update API documentation for new endpoints",
        status=TaskStatus.DONE,
        priority=Priority.MEDIUM,
        assigned_to="agent-002",
        created_at=datetime.now(timezone.utc) - timedelta(days=3),
        updated_at=datetime.now(timezone.utc) - timedelta(hours=1),
        due_date=datetime.now(timezone.utc) - timedelta(hours=2),
        estimated_hours=2.0,
        labels=["documentation", "api"],
    )


@pytest.fixture
def task_list(sample_task, sample_high_priority_task, sample_completed_task):
    """Create a list of sample tasks."""
    return [sample_task, sample_high_priority_task, sample_completed_task]


@pytest.fixture
def sample_worker_status():
    """Create a sample worker status for testing."""
    return WorkerStatus(
        worker_id="worker-001",
        name="Backend Specialist",
        available=True,
        current_tasks=2,
        max_capacity=5,
        skills=["python", "django", "postgresql", "redis"],
        last_heartbeat=datetime.now(timezone.utc),
        performance_metrics={"completed_tasks": 15, "average_time": 4.2},
    )


@pytest.fixture
def sample_frontend_worker():
    """Create a frontend-focused worker status for testing."""
    return WorkerStatus(
        worker_id="worker-002",
        name="Frontend Developer",
        available=True,
        current_tasks=1,
        max_capacity=4,
        skills=["javascript", "react", "css", "html"],
        last_heartbeat=datetime.now(timezone.utc),
        performance_metrics={"completed_tasks": 12, "average_time": 3.8},
    )


@pytest.fixture
def worker_list(sample_worker_status, sample_frontend_worker):
    """Create a list of sample workers."""
    return [sample_worker_status, sample_frontend_worker]


@pytest.fixture
def sample_context():
    """Create a real context instance for testing."""
    context = Context()
    context.project_name = "Test Project"
    context.technology_stack = ["python", "postgresql", "react"]
    context.team_size = 3
    context.deadline = datetime.now(timezone.utc) + timedelta(weeks=2)
    return context


@pytest.fixture
def project_metadata():
    """Create project metadata for testing."""
    return {
        "name": "E-commerce Platform",
        "description": "Modern e-commerce platform with microservices architecture",
        "technology_stack": ["python", "fastapi", "postgresql", "redis", "react"],
        "team_size": 5,
        "estimated_duration_weeks": 12,
        "complexity": "high",
        "domain": "e-commerce",
        "phase": "implementation",
    }
