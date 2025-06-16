"""
Simplified MCP Kanban Client that works with existing MCP architecture.
This version doesn't create its own connection but provides a clean interface
to the kanban MCP tools that are already available.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime

from src.core.models import Task, TaskStatus, Priority


class MCPKanbanClientSimplified:
    """Simplified client that uses existing MCP kanban tools through function calls"""
    
    def __init__(self, mcp_function_caller=None):
        """
        Initialize with a function that can call MCP tools.
        In production, this would be the MCP tool calling interface.
        For testing, this could be a mock.
        """
        self.mcp_call = mcp_function_caller
        self.board_id: Optional[str] = None
        self.project_id: Optional[str] = None
    
    async def initialize(self, project_name: str = "Task Master Test"):
        """Initialize by finding the project and board"""
        if not self.mcp_call:
            raise RuntimeError("MCP function caller not provided")
        
        # Get projects
        projects_result = await self.mcp_call("mcp_kanban_project_board_manager", {
            "action": "get_projects",
            "page": 1,
            "perPage": 25
        })
        
        # Find the project
        projects = projects_result.get("items", []) if isinstance(projects_result, dict) else projects_result
        for project in projects:
            if project_name in project.get("name", ""):
                self.project_id = project["id"]
                break
        
        if not self.project_id:
            raise ValueError(f"Project '{project_name}' not found")
        
        # Get boards for project
        boards_result = await self.mcp_call("mcp_kanban_project_board_manager", {
            "action": "get_boards",
            "page": 1,
            "perPage": 25
        })
        
        # Find board for our project
        boards = boards_result.get("items", []) if isinstance(boards_result, dict) else boards_result
        for board in boards:
            if board.get("projectId") == self.project_id:
                self.board_id = board["id"]
                break
        
        if not self.board_id:
            raise ValueError(f"No board found for project '{project_name}'")
    
    async def get_available_tasks(self) -> List[Task]:
        """Get all available tasks from the board"""
        if not self.board_id:
            raise RuntimeError("Not initialized - call initialize() first")
        
        # Get all cards
        cards = await self.mcp_call("mcp_kanban_card_manager", {
            "action": "get_all",
            "boardId": self.board_id
        })
        
        tasks = []
        card_list = cards if isinstance(cards, list) else [cards] if cards else []
        
        for card in card_list:
            # Convert to Task object
            task = self._card_to_task(card)
            # Only return unassigned tasks (or adapt your logic)
            if not task.assigned_to:
                tasks.append(task)
        
        return tasks
    
    async def get_task_details(self, task_id: str) -> Task:
        """Get detailed information about a specific task"""
        details = await self.mcp_call("mcp_kanban_card_manager", {
            "action": "get_details",
            "cardId": task_id
        })
        
        return self._card_to_task(details)
    
    async def assign_task(self, task_id: str, agent_id: str):
        """Assign a task to an agent"""
        # Add assignment comment
        await self.mcp_call("mcp_kanban_comment_manager", {
            "action": "create",
            "cardId": task_id,
            "text": f"📋 Task assigned to {agent_id} at {datetime.now().isoformat()}"
        })
        
        # Move to appropriate list (you'd need to find the "In Progress" list)
        # This is simplified - you'd want to implement proper list management
    
    async def add_comment(self, task_id: str, text: str):
        """Add a comment to a task"""
        await self.mcp_call("mcp_kanban_comment_manager", {
            "action": "create",
            "cardId": task_id,
            "text": text
        })
    
    async def update_task_status(self, task_id: str, status: str):
        """Update task status by moving between lists"""
        # This would need to implement the logic to move cards between lists
        # based on your board structure
        pass
    
    async def complete_task(self, task_id: str):
        """Mark a task as completed"""
        await self.add_comment(
            task_id,
            f"✅ Task completed at {datetime.now().isoformat()}"
        )
        # Move to Done list
        await self.update_task_status(task_id, "done")
    
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create a new task"""
        # Find the appropriate list (TODO/Backlog)
        lists = await self.mcp_call("mcp_kanban_list_manager", {
            "action": "get_all",
            "boardId": self.board_id
        })
        
        todo_list = None
        for lst in lists:
            if lst.get("name", "").upper() in ["TODO", "TO DO", "BACKLOG"]:
                todo_list = lst
                break
        
        if not todo_list:
            raise ValueError("No TODO list found on board")
        
        # Create the card
        card = await self.mcp_call("mcp_kanban_card_manager", {
            "action": "create",
            "listId": todo_list["id"],
            "name": task_data["name"],
            "description": task_data.get("description", "")
        })
        
        return self._card_to_task(card)
    
    def _card_to_task(self, card: Dict[str, Any]) -> Task:
        """Convert a kanban card to a Task object"""
        return Task(
            id=card["id"],
            name=card.get("name", card.get("title", "")),
            description=card.get("description", ""),
            status=TaskStatus.TODO,  # Simplified - you'd map based on list
            priority=Priority.MEDIUM,  # You'd extract from labels
            assigned_to=card.get("assigned_to"),
            created_at=datetime.fromisoformat(card.get("createdAt", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(card.get("updatedAt", datetime.now().isoformat())),
            due_date=datetime.fromisoformat(card["dueDate"]) if card.get("dueDate") else None,
            estimated_hours=0.0,  # You'd need to store this in card metadata
            actual_hours=0.0,
            dependencies=[],
            labels=[]  # You'd extract from card labels
        )


# For backwards compatibility, you could alias the old class name
MCPKanbanClient = MCPKanbanClientSimplified
