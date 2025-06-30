"""
Unit tests for Marcus Server (Modular Architecture) - Simple style
"""

import pytest
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import get_tool_definitions, handle_tool_call
from src.core.models import (
    Task, TaskStatus, Priority, RiskLevel,
    ProjectState, WorkerStatus, TaskAssignment
)
import mcp.types as types


def test_server_initialization(monkeypatch):
    """Test server initializes correctly"""
    monkeypatch.setenv('KANBAN_PROVIDER', 'planka')
    monkeypatch.setenv('GITHUB_OWNER', 'test-owner')
    monkeypatch.setenv('GITHUB_REPO', 'test-repo')
    
    server = MarcusServer()
    
    assert server.provider == 'planka'
    assert server.ai_engine is not None
    assert server.monitor is not None
    assert server.comm_hub is not None
    assert server.project_tasks == []
    assert server.agent_tasks == {}
    assert server.agent_status == {}


def test_get_tool_definitions():
    """Test tool definitions are returned correctly"""
    tools = get_tool_definitions()
    
    assert len(tools) > 0
    tool_names = [tool.name for tool in tools]
    
    # Check essential tools are present
    assert 'ping' in tool_names
    assert 'register_agent' in tool_names
    assert 'request_next_task' in tool_names
    assert 'report_task_progress' in tool_names
    assert 'get_project_status' in tool_names
    assert 'create_project' in tool_names
    assert 'add_feature' in tool_names


@pytest.mark.asyncio
async def test_ping_tool(monkeypatch):
    """Test ping tool functionality"""
    monkeypatch.setenv('KANBAN_PROVIDER', 'planka')
    
    # Create server inline to avoid fixture issues
    server = MarcusServer()
    server.kanban_client = AsyncMock()
    server.assignment_monitor = None
    
    result = await handle_tool_call(
        'ping',
        {'echo': 'test'},
        server
    )
    
    assert len(result) == 1
    assert result[0].type == 'text'
    
    data = json.loads(result[0].text)
    assert data['status'] == 'online'
    assert data['echo'] == 'test'
    assert 'timestamp' in data
    assert data['success'] is True
    assert data['provider'] == 'planka'


@pytest.mark.asyncio
async def test_unknown_tool(monkeypatch):
    """Test handling of unknown tool"""
    monkeypatch.setenv('KANBAN_PROVIDER', 'planka')
    
    server = MarcusServer()
    server.kanban_client = AsyncMock()
    server.assignment_monitor = None
    
    result = await handle_tool_call(
        'unknown_tool',
        {},
        server
    )
    
    assert len(result) == 1
    data = json.loads(result[0].text)
    assert 'error' in data
    assert 'Unknown tool' in data['error']


@pytest.mark.asyncio
async def test_register_agent(monkeypatch):
    """Test agent registration"""
    monkeypatch.setenv('KANBAN_PROVIDER', 'planka')
    
    server = MarcusServer()
    server.kanban_client = AsyncMock()
    server.assignment_monitor = None
    
    result = await handle_tool_call(
        'register_agent',
        {
            'agent_id': 'test-001',
            'name': 'Test Agent',
            'role': 'Developer',
            'skills': ['python', 'testing']
        },
        server
    )
    
    data = json.loads(result[0].text)
    assert data['success'] is True
    assert data['agent_id'] == 'test-001'
    assert 'test-001' in server.agent_status


@pytest.mark.asyncio
async def test_report_task_progress(monkeypatch):
    """Test reporting task progress"""
    monkeypatch.setenv('KANBAN_PROVIDER', 'planka')
    
    server = MarcusServer()
    server.kanban_client = AsyncMock()
    server.kanban_client.update_task_progress = AsyncMock()
    server.assignment_monitor = None
    
    # Setup agent and task
    task_id = 'task-001'
    server.agent_status['test-001'] = WorkerStatus(
        worker_id='test-001',
        name='Test Agent',
        role='Developer',
        email='test@example.com',
        current_tasks=[],
        completed_tasks_count=0,
        capacity=40,
        skills=[],
        availability={},
        performance_score=1.0
    )
    server.agent_tasks['test-001'] = TaskAssignment(
        task_id=task_id,
        agent_id='test-001',
        assigned_at=datetime.now(),
        status='in_progress'
    )
    
    result = await handle_tool_call(
        'report_task_progress',
        {
            'agent_id': 'test-001',
            'task_id': task_id,
            'status': 'in_progress',
            'progress': 50,
            'message': 'Halfway done'
        },
        server
    )
    
    data = json.loads(result[0].text)
    assert data['success'] is True
    server.kanban_client.update_task_progress.assert_called_once()


@pytest.mark.asyncio
async def test_get_project_status(monkeypatch):
    """Test getting project status"""
    monkeypatch.setenv('KANBAN_PROVIDER', 'planka')
    
    server = MarcusServer()
    server.kanban_client = AsyncMock()
    server.assignment_monitor = None
    
    # Mock project state
    server.project_state = ProjectState(
        board_id='board-001',
        project_name='Test Project',
        total_tasks=10,
        completed_tasks=5,
        in_progress_tasks=3,
        blocked_tasks=1,
        progress_percent=50.0,
        overdue_tasks=[],
        team_velocity=2.0,
        risk_level=RiskLevel.LOW,
        last_updated=datetime.now()
    )
    
    # Mock board summary
    server.kanban_client.get_board_summary = AsyncMock(return_value={
        'totalCards': 10,
        'doneCount': 5,
        'inProgressCount': 3,
        'backlogCount': 2
    })
    
    result = await handle_tool_call(
        'get_project_status',
        {},
        server
    )
    
    data = json.loads(result[0].text)
    assert 'board_summary' in data or 'total_tasks' in data
    # Check the actual structure returned
    if 'board_summary' in data:
        assert data['board_summary']['totalCards'] == 10
    else:
        assert data.get('total_tasks') == 10
    assert data['completed_tasks'] == 5
    assert data['in_progress_tasks'] == 3
    assert data['completion_percentage'] == 50.0


@pytest.mark.asyncio
async def test_create_project_validation(monkeypatch):
    """Test create_project validates inputs"""
    monkeypatch.setenv('KANBAN_PROVIDER', 'planka')
    
    server = MarcusServer()
    server.kanban_client = AsyncMock()
    server.assignment_monitor = None
    
    result = await handle_tool_call(
        'create_project',
        {
            'description': '',
            'project_name': 'Test'
        },
        server
    )
    
    data = json.loads(result[0].text)
    assert data['success'] is False
    assert 'required' in data['error'].lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])