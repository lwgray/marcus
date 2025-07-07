"""
Agent Management API Endpoints

Provides REST API endpoints for managing coding agents through the web interface.
This allows triggering agent operations to observe pipeline behavior.
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any
import asyncio
from src.api.async_wrapper import async_route

# Import MCP client capabilities
from src.marcus_mcp.tools import (
    register_agent,
    get_agent_status,
    list_registered_agents,
    request_next_task,
    report_task_progress,
    report_blocker,
    get_project_status
)

# Create blueprint
agent_api = Blueprint('agent_management', __name__, url_prefix='/api/agents')

# Import the singleton Marcus server
from src.api.marcus_server_singleton import get_marcus_server


@agent_api.route('/register', methods=['POST'])
@async_route
async def register_new_agent():
    """Register a new agent."""
    data = request.get_json()
    
    # Get the real Marcus server instance
    server = await get_marcus_server()
    
    result = await register_agent(
        agent_id=data.get('agent_id'),
        name=data.get('name'),
        role=data.get('role'),
        skills=data.get('skills', []),
        state=server
    )
    
    return jsonify(result)


@agent_api.route('/list', methods=['GET'])
@async_route
async def list_agents():
    """List all registered agents."""
    # Get the real Marcus server instance
    server = await get_marcus_server()
    result = await list_registered_agents(state=server)
    return jsonify(result)


@agent_api.route('/<agent_id>/status', methods=['GET'])
@async_route
async def get_status(agent_id):
    """Get status of a specific agent."""
    # Get the real Marcus server instance
    server = await get_marcus_server()
    result = await get_agent_status(
        agent_id=agent_id,
        state=server
    )
    return jsonify(result)


@agent_api.route('/<agent_id>/request-task', methods=['POST'])
@async_route
async def request_task(agent_id):
    """Request next task for an agent."""
    # Get the real Marcus server instance
    server = await get_marcus_server()
    result = await request_next_task(
        agent_id=agent_id,
        state=server
    )
    return jsonify(result)


@agent_api.route('/report-progress', methods=['POST'])
@async_route
async def report_progress():
    """Report task progress."""
    data = request.get_json()
    
    # Get the real Marcus server instance
    server = await get_marcus_server()
    
    result = await report_task_progress(
        agent_id=data.get('agent_id'),
        task_id=data.get('task_id'),
        status=data.get('status'),
        progress=data.get('progress', 0),
        message=data.get('message', ''),
        state=server
    )
    
    return jsonify(result)


@agent_api.route('/report-blocker', methods=['POST'])
@async_route
async def report_blocker_endpoint():
    """Report a task blocker."""
    data = request.get_json()
    
    # Get the real Marcus server instance
    server = await get_marcus_server()
    
    result = await report_blocker(
        agent_id=data.get('agent_id'),
        task_id=data.get('task_id'),
        blocker_description=data.get('blocker_description'),
        severity=data.get('severity', 'medium'),
        state=server
    )
    
    return jsonify(result)


@agent_api.route('/project-status', methods=['GET'])
@async_route
async def get_project_status_endpoint():
    """Get current project status."""
    # Get the real Marcus server instance
    server = await get_marcus_server()
    result = await get_project_status(state=server)
    return jsonify(result)


# WebSocket support for real-time agent updates
def setup_agent_websocket_handlers(socketio):
    """Setup WebSocket handlers for agent updates."""
    
    @socketio.on('agent_registered')
    def handle_agent_registered(data):
        """Broadcast when new agent is registered."""
        socketio.emit('agent_update', {
            'type': 'registered',
            'agent_id': data['agent_id'],
            'timestamp': data['timestamp']
        })
    
    @socketio.on('task_assigned')
    def handle_task_assigned(data):
        """Broadcast when task is assigned to agent."""
        socketio.emit('agent_update', {
            'type': 'task_assigned',
            'agent_id': data['agent_id'],
            'task_id': data['task_id'],
            'timestamp': data['timestamp']
        })
    
    @socketio.on('progress_reported')
    def handle_progress_reported(data):
        """Broadcast when agent reports progress."""
        socketio.emit('agent_update', {
            'type': 'progress',
            'agent_id': data['agent_id'],
            'task_id': data['task_id'],
            'progress': data['progress'],
            'status': data['status'],
            'timestamp': data['timestamp']
        })