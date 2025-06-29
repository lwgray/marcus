"""
Planka implementation using SimpleMCPKanbanClient

Direct integration without the mcp_function_caller abstraction
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from src.integrations.kanban_interface import KanbanInterface, KanbanProvider
from src.integrations.kanban_client_with_create import KanbanClientWithCreate
from src.core.models import Task, TaskStatus, Priority


class PlankaKanbanSimple(KanbanInterface):
    """Planka kanban board implementation using direct MCP client"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Planka connection
        
        Args:
            config: Dictionary containing optional configuration
        """
        super().__init__(config)
        self.provider = KanbanProvider.PLANKA
        self.client = KanbanClientWithCreate()
        self.connected = False
        print(f"[PlankaKanbanSimple] Initialized with board_id={self.client.board_id}, project_id={self.client.project_id}")
        
    async def connect(self) -> bool:
        """Connect to Planka via MCP"""
        try:
            # SimpleMCPKanbanClient loads config automatically
            self.connected = True
            return True
        except Exception as e:
            print(f"Failed to connect to Planka: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from Planka"""
        self.connected = False
        
    async def get_available_tasks(self) -> List[Task]:
        """Get unassigned tasks from backlog"""
        try:
            tasks = await self.client.get_available_tasks()
            return tasks
        except Exception as e:
            print(f"Error getting tasks: {e}")
            return []
    
    async def get_all_tasks(self) -> List[Task]:
        """Get all tasks from the board regardless of status or assignment"""
        try:
            tasks = await self.client.get_all_tasks()
            return tasks
        except Exception as e:
            print(f"Error getting all tasks: {e}")
            return []
        
    async def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get specific task by ID"""
        try:
            # SimpleMCPKanbanClient doesn't have get_task_details
            # We need to get all tasks and find the one with matching ID
            tasks = await self.client.get_available_tasks()
            for task in tasks:
                if task.id == task_id:
                    return task
            return None
        except Exception as e:
            print(f"Error getting task {task_id}: {e}")
            return None
        
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create new task in Planka"""
        if not self.connected:
            await self.connect()
        
        try:
            # Use the extended client's create_task method
            return await self.client.create_task(task_data)
        except Exception as e:
            print(f"Error creating task: {e}")
            raise
        
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Task:
        """Update task status or properties"""
        try:
            # Map status updates to list movements
            if 'status' in updates:
                status = updates['status']
                if status == TaskStatus.IN_PROGRESS:
                    # Move to in progress by assigning
                    if 'assigned_to' in updates:
                        await self.client.assign_task(task_id, updates['assigned_to'])
                elif status == TaskStatus.COMPLETED:
                    await self.client.complete_task(task_id)
            
            # Get and return the updated task
            task = await self.get_task_by_id(task_id)
            return task
        except Exception as e:
            print(f"Error updating task {task_id}: {e}")
            # Return the current task state on error
            return await self.get_task_by_id(task_id)
        
    async def add_comment(self, task_id: str, comment: str) -> bool:
        """Add comment to task"""
        try:
            await self.client.add_comment(task_id, comment)
            return True
        except Exception as e:
            print(f"Error adding comment to task {task_id}: {e}")
            return False
        
    async def get_agent_tasks(self, agent_id: str) -> List[Task]:
        """Get all tasks assigned to a specific agent"""
        try:
            # Get all tasks and filter by assignment
            all_tasks = await self.client.get_board_summary()
            # This would need to be implemented based on board structure
            return []
        except Exception as e:
            print(f"Error getting agent tasks: {e}")
            return []
        
    async def get_board_summary(self) -> Dict[str, Any]:
        """Get overall board statistics and summary"""
        try:
            summary = await self.client.get_board_summary()
            return summary
        except Exception as e:
            print(f"Error getting board summary: {e}")
            return {}
    
    async def assign_task(self, task_id: str, assignee_id: str) -> bool:
        """Assign a task to a worker"""
        try:
            await self.client.assign_task(task_id, assignee_id)
            return True
        except Exception as e:
            print(f"Error assigning task {task_id}: {e}")
            return False
    
    async def move_task_to_column(self, task_id: str, column_name: str) -> bool:
        """Move task to a specific column/status"""
        try:
            # SimpleMCPKanbanClient doesn't have direct column movement
            # We'll use status updates as a proxy
            if column_name.lower() in ["done", "completed"]:
                await self.client.complete_task(task_id)
            elif column_name.lower() in ["in progress", "doing"]:
                # This is handled by assign_task in SimpleMCPKanbanClient
                pass
            return True
        except Exception as e:
            print(f"Error moving task {task_id} to {column_name}: {e}")
            return False
    
    async def get_project_metrics(self) -> Dict[str, Any]:
        """Get project metrics and statistics"""
        try:
            summary = await self.client.get_board_summary()
            # Extract metrics from summary
            return {
                "total_tasks": summary.get("totalCards", 0),
                "backlog_tasks": summary.get("backlogCount", 0),
                "in_progress_tasks": summary.get("inProgressCount", 0),
                "completed_tasks": summary.get("doneCount", 0),
                "blocked_tasks": 0  # Not tracked in simple client
            }
        except Exception as e:
            print(f"Error getting project metrics: {e}")
            return {
                "total_tasks": 0,
                "backlog_tasks": 0,
                "in_progress_tasks": 0,
                "completed_tasks": 0,
                "blocked_tasks": 0
            }
    
    async def report_blocker(self, task_id: str, blocker_description: str, severity: str = "medium") -> bool:
        """Report a blocker on a task"""
        try:
            # Add blocker as a comment
            comment = f"🚫 BLOCKER ({severity.upper()}): {blocker_description}"
            await self.client.add_comment(task_id, comment)
            return True
        except Exception as e:
            print(f"Error reporting blocker on task {task_id}: {e}")
            return False
    
    async def update_task_progress(self, task_id: str, progress_data: Dict[str, Any]) -> bool:
        """Update task progress"""
        try:
            # Add progress as a comment
            progress = progress_data.get("progress", 0)
            message = progress_data.get("message", "")
            comment = f"📊 Progress: {progress}% - {message}"
            await self.client.add_comment(task_id, comment)
            
            # Handle status changes
            status = progress_data.get("status")
            if status and progress == 100:
                await self.client.complete_task(task_id)
            
            return True
        except Exception as e:
            print(f"Error updating task progress for {task_id}: {e}")
            return False