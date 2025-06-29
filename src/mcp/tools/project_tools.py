"""
Project Monitoring Tools for Marcus MCP

This module contains tools for monitoring project progress and metrics:
- get_project_status: Get comprehensive project metrics and status
"""

from typing import Dict, Any, List
from src.core.models import TaskStatus
from src.logging.conversation_logger import conversation_logger


async def get_project_status(state: Any) -> Dict[str, Any]:
    """
    Get current project status and metrics.
    
    Provides comprehensive project overview including:
    - Task completion statistics
    - Worker availability metrics
    - Kanban provider information
    
    Args:
        state: Marcus server state instance
        
    Returns:
        Dict with project metrics and status
    """
    try:
        # Initialize kanban if needed
        await state.initialize_kanban()
        
        # Refresh state
        await refresh_project_state(state)
        
        if state.project_state:
            # Calculate metrics
            total_tasks = len(state.project_tasks)
            completed = len([t for t in state.project_tasks if t.status == TaskStatus.DONE])
            in_progress = len([t for t in state.project_tasks if t.status == TaskStatus.IN_PROGRESS])
            blocked = len([t for t in state.project_tasks if t.status == TaskStatus.BLOCKED])
            
            # Worker metrics - create snapshot to avoid dictionary mutation during iteration
            active_workers = len([w for w in list(state.agent_status.values()) if len(w.current_tasks) > 0])
            
            return {
                "success": True,
                "project": {
                    "total_tasks": total_tasks,
                    "completed": completed,
                    "in_progress": in_progress,
                    "blocked": blocked,
                    "completion_percentage": (completed / total_tasks * 100) if total_tasks > 0 else 0
                },
                "workers": {
                    "total": len(state.agent_status),
                    "active": active_workers,
                    "available": len(state.agent_status) - active_workers
                },
                "provider": state.provider
            }
        else:
            return {
                "success": False,
                "message": "Project state not available"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Helper function
async def refresh_project_state(state: Any) -> None:
    """
    Refresh the current project state from kanban.
    
    Updates the internal project state with latest data from
    the connected kanban provider.
    
    Args:
        state: Marcus server state instance
    """
    try:
        # Log refresh attempt
        state.log_event("refresh_project_state_start", {
            "kanban_client_exists": state.kanban_client is not None
        })
        
        tasks = await state.kanban_client.get_available_tasks()
        
        # Log tasks retrieved
        state.log_event("refresh_project_state_tasks", {
            "task_count": len(tasks),
            "task_names": [t.name for t in tasks]
        })
        
        # Store tasks separately
        state.project_tasks = tasks
        
        # Calculate task statistics
        completed = len([t for t in tasks if t.status == TaskStatus.DONE])
        in_progress = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])
        todo = len([t for t in tasks if t.status == TaskStatus.TODO])
        blocked = len([t for t in tasks if t.status == TaskStatus.BLOCKED])
        
        # Create project state
        if state.monitor:
            state.project_state = await state.monitor.analyze_project_state(
                tasks=tasks,
                agents=list(state.agent_status.values()),
                completed_count=completed,
                in_progress_count=in_progress,
                todo_count=todo
            )
        
        # Log state update
        state.log_event("refresh_project_state_complete", {
            "total_tasks": len(tasks),
            "completed": completed,
            "in_progress": in_progress,
            "todo": todo,
            "blocked": blocked
        })
        
    except Exception as e:
        conversation_logger.error(f"Failed to refresh project state: {e}")
        state.log_event("refresh_project_state_error", {"error": str(e)})
        raise