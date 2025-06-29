"""
System Health and Diagnostics Tools for Marcus MCP

This module contains tools for system monitoring and health checks:
- ping: Check Marcus connectivity and status
- check_assignment_health: Monitor assignment system health
"""

from datetime import datetime
from typing import Dict, Any
from src.logging.conversation_logger import conversation_logger, log_thinking
from src.visualization.conversation_adapter import log_agent_event
from src.monitoring.assignment_monitor import AssignmentHealthChecker


async def ping(echo: str, state: Any) -> Dict[str, Any]:
    """
    Check Marcus status and connectivity.
    
    Simple health check endpoint that verifies the Marcus system
    is online and responsive. Can echo back a message.
    
    Args:
        echo: Optional message to echo back
        state: Marcus server state instance
        
    Returns:
        Dict with status, provider info, and timestamp
    """
    # Log the ping request immediately
    state.log_event("ping_request", {
        "echo": echo,
        "source": "mcp_client"
    })
    
    # Log conversation event for visualization
    log_agent_event("ping_request", {
        "echo": echo,
        "source": "mcp_client"
    })
    
    # Also use structured logging
    log_thinking("marcus", f"Received ping request with echo: {echo}")
    
    response = {
        "success": True,
        "status": "online",
        "provider": state.provider,
        "echo": echo or "pong",
        "timestamp": datetime.now().isoformat()
    }
    
    # Log the response immediately
    state.log_event("ping_response", response)
    
    # Also use structured logging
    conversation_logger.log_kanban_interaction(
        action="ping",
        direction="response",
        data=response
    )
    
    return response


async def check_assignment_health(state: Any) -> Dict[str, Any]:
    """
    Check the health of the assignment tracking system.
    
    Performs comprehensive health checks on:
    - Assignment persistence layer
    - Kanban client connectivity
    - Assignment monitor status
    - In-memory state consistency
    
    Args:
        state: Marcus server state instance
        
    Returns:
        Dict with detailed health status and metrics
    """
    try:
        # Initialize health checker
        health_checker = AssignmentHealthChecker(
            state.assignment_persistence,
            state.kanban_client,
            state.assignment_monitor
        )
        
        # Run health check
        health_status = await health_checker.check_assignment_health()
        
        # Add current in-memory state info
        health_status["in_memory_state"] = {
            "agent_tasks": len(state.agent_tasks),
            "tasks_being_assigned": len(state.tasks_being_assigned),
            "monitor_running": state.assignment_monitor._running if state.assignment_monitor else False
        }
        
        return {
            "success": True,
            **health_status
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }