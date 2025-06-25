"""
Pytest fixtures for visualization system tests.

This module provides common fixtures for testing visualization components,
including mock data, temporary directories, and simulated Socket.IO connections.

Notes
-----
These fixtures create realistic test data that matches the actual data structures
used by the PM Agent visualization system.
"""
import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock
import asyncio

from src.core.models import (
    ProjectState, WorkerStatus, Task, TaskStatus, 
    Priority, RiskLevel, BlockerReport
)


@pytest.fixture
def temp_log_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for log files.
    
    Yields
    ------
    Path
        Path to a temporary directory that is automatically cleaned up.
    
    Notes
    -----
    The directory and all contents are removed after the test completes.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_log_file(temp_log_dir: Path) -> Path:
    """
    Create a sample structured log file with test events.
    
    Parameters
    ----------
    temp_log_dir : Path
        Temporary directory for creating the log file.
    
    Returns
    -------
    Path
        Path to the created log file containing sample events.
    
    Notes
    -----
    The log file contains JSONL formatted events simulating worker
    registration and task assignment.
    """
    log_file = temp_log_dir / "test_conversation.jsonl"
    
    events = [
        {
            "timestamp": datetime.now().isoformat(),
            "event_type": "worker_event",
            "event_name": "worker_registered",
            "data": {
                "worker_id": "worker-001",
                "name": "Test Worker",
                "skills": ["python", "api"]
            }
        },
        {
            "timestamp": datetime.now().isoformat(),
            "event_type": "pm_event",
            "event_name": "task_assigned",
            "data": {
                "task_id": "task-001",
                "worker_id": "worker-001",
                "confidence": 0.85
            }
        }
    ]
    
    with open(log_file, 'w') as f:
        for event in events:
            f.write(json.dumps(event) + '\n')
    
    return log_file


@pytest.fixture
def mock_socketio() -> AsyncMock:
    """
    Create a mock Socket.IO server for testing real-time features.
    
    Returns
    -------
    AsyncMock
        Mock Socket.IO server with emit and event handling capabilities.
    
    Notes
    -----
    The mock supports emit() for sending events and on() for registering
    event handlers, simulating real Socket.IO behavior.
    """
    sio = AsyncMock()
    sio.emit = AsyncMock()
    sio.event = Mock(side_effect=lambda f: f)
    sio.on = Mock(side_effect=lambda event: lambda f: f)
    return sio


@pytest.fixture
def sample_worker_status() -> WorkerStatus:
    """
    Create a sample WorkerStatus object for testing.
    
    Returns
    -------
    WorkerStatus
        A worker status with realistic test data including skills,
        current tasks, and performance metrics.
    
    Examples
    --------
    >>> worker = sample_worker_status()
    >>> assert worker.worker_id == "worker-001"
    >>> assert "python" in worker.skills
    """
    return WorkerStatus(
        worker_id="worker-001",
        name="Test Worker",
        role="Developer",
        email="test@example.com",
        current_tasks=["task-001"],
        completed_tasks_count=5,
        capacity=0.8,
        skills=["python", "api", "testing"],
        availability="online",
        performance_score=0.9
    )


@pytest.fixture
def sample_project_state() -> ProjectState:
    """
    Create a sample ProjectState object for testing.
    
    Returns
    -------
    ProjectState
        A project state with task counts, progress metrics, and risk assessment.
    
    Notes
    -----
    The sample state represents a project with 30% completion, medium risk,
    and a mix of task statuses.
    """
    return ProjectState(
        board_id="board-001",
        project_name="Test Project",
        total_tasks=10,
        completed_tasks=3,
        in_progress_tasks=4,
        blocked_tasks=1,
        progress_percent=30.0,
        overdue_tasks=[],
        team_velocity=1.5,
        risk_level=RiskLevel.MEDIUM,
        last_updated=datetime.now()
    )


@pytest.fixture
def sample_task() -> Task:
    """
    Create a sample Task object for testing.
    
    Returns
    -------
    Task
        A task with standard properties including status, priority,
        and assignment information.
    
    Notes
    -----
    The task is configured as in-progress with high priority,
    simulating an active work item.
    """
    return Task(
        id="task-001",
        name="Test Task",
        description="A test task for unit testing",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.HIGH,
        assigned_to="worker-001",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=4.0,
        actual_hours=2.0,
        dependencies=[],
        labels=["backend", "api"]
    )


@pytest.fixture
def sample_blocker() -> BlockerReport:
    """
    Create a sample BlockerReport object for testing.
    
    Returns
    -------
    BlockerReport
        An unresolved blocker report with high severity.
    
    Notes
    -----
    The blocker simulates a database connection issue, which is
    a common type of technical blocker.
    """
    return BlockerReport(
        task_id="task-001",
        reporter_id="worker-001",
        description="Database connection timeout",
        severity=RiskLevel.HIGH,
        reported_at=datetime.now(),
        resolved=False,
        resolution=None,
        resolved_at=None
    )


@pytest.fixture
def event_samples() -> Dict[str, Dict[str, Any]]:
    """
    Provide a collection of sample events for testing.
    
    Returns
    -------
    Dict[str, Dict[str, Any]]
        Dictionary mapping event names to event data structures.
    
    Notes
    -----
    Events include worker registration, task assignment, progress updates,
    blocker reports, and PM decisions. Each event follows the standard
    event structure with timestamp, type, name, and data fields.
    """
    return {
        "worker_registered": {
            "timestamp": datetime.now().isoformat(),
            "event_type": "worker_event",
            "event_name": "worker_registered",
            "data": {
                "worker_id": "worker-001",
                "name": "Test Worker",
                "skills": ["python", "api"]
            }
        },
        "task_assigned": {
            "timestamp": datetime.now().isoformat(),
            "event_type": "pm_event",
            "event_name": "task_assigned",
            "data": {
                "task_id": "task-001",
                "worker_id": "worker-001",
                "task_name": "Build API",
                "confidence": 0.85,
                "reasoning": "Best skill match"
            }
        },
        "progress_reported": {
            "timestamp": datetime.now().isoformat(),
            "event_type": "worker_event",
            "event_name": "progress_reported",
            "data": {
                "task_id": "task-001",
                "worker_id": "worker-001",
                "progress": 50,
                "status": "in_progress"
            }
        },
        "blocker_reported": {
            "timestamp": datetime.now().isoformat(),
            "event_type": "worker_event",
            "event_name": "blocker_reported",
            "data": {
                "task_id": "task-001",
                "worker_id": "worker-001",
                "description": "Database connection failed",
                "severity": "high"
            }
        },
        "decision_made": {
            "timestamp": datetime.now().isoformat(),
            "event_type": "pm_event",
            "event_name": "decision_made",
            "data": {
                "decision_id": "dec-001",
                "decision_type": "task_assignment",
                "options": ["worker-001", "worker-002"],
                "selected": "worker-001",
                "confidence": 0.85,
                "reasoning": "Better skill match"
            }
        }
    }


@pytest.fixture
async def mock_health_monitor() -> 'HealthMonitor':
    """
    Create a mock health monitor with sample analysis data.
    
    Returns
    -------
    HealthMonitor
        A health monitor instance with pre-populated analysis results.
    
    Notes
    -----
    The mock monitor contains a recent health analysis showing good
    overall health with medium risk level.
    """
    from src.visualization.health_monitor import HealthMonitor
    monitor = HealthMonitor()
    monitor.last_analysis = {
        "timestamp": datetime.now().isoformat(),
        "overall_health": "good",
        "risk_level": "medium",
        "metrics": {
            "velocity": 1.5,
            "blocked_tasks": 1,
            "worker_utilization": 0.75
        }
    }
    return monitor


@pytest.fixture
def async_mock_callback() -> AsyncMock:
    """
    Create an async mock callback for testing asynchronous operations.
    
    Returns
    -------
    AsyncMock
        An async mock that can be used as a callback in async tests.
    
    Examples
    --------
    >>> callback = async_mock_callback()
    >>> await callback("test_data")
    >>> callback.assert_called_once_with("test_data")
    """
    return AsyncMock()


@pytest.fixture
def mock_aiohttp_app() -> Mock:
    """
    Create a mock aiohttp application for testing web endpoints.
    
    Returns
    -------
    Mock
        Mock aiohttp application with router methods.
    
    Notes
    -----
    The mock includes router methods (add_get, add_post, add_static)
    for verifying endpoint registration.
    """
    app = Mock()
    app.router = Mock()
    app.router.add_get = Mock()
    app.router.add_post = Mock()
    app.router.add_static = Mock()
    return app