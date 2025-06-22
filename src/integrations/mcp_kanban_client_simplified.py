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
        """Get all tasks from the board (not just unassigned)"""
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
            task = await self._card_to_task(card)
            tasks.append(task)
        
        return tasks
    
    async def get_task_details(self, task_id: str) -> Task:
        """Get detailed information about a specific task"""
        details = await self.mcp_call("mcp_kanban_card_manager", {
            "action": "get_details",
            "cardId": task_id
        })
        
        return await self._card_to_task(details)
    
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
    
    async def get_card_tasks(self, card_id: str):
        """Get all checklist tasks for a card"""
        try:
            result = await self.mcp_call("mcp_kanban_task_manager", {
                "action": "get_all",
                "cardId": card_id
            })
            return result if isinstance(result, list) else []
        except:
            return []
    
    async def update_card_task(self, task_id: str, is_completed: bool):
        """Update a checklist task's completion status"""
        try:
            await self.mcp_call("mcp_kanban_task_manager", {
                "action": "update",
                "id": task_id,
                "isCompleted": is_completed
            })
            return True
        except:
            return False
    
    async def create_card_tasks(self, card_id: str, task_names: List[str]):
        """Create checklist tasks for a card"""
        tasks = []
        for idx, name in enumerate(task_names):
            try:
                result = await self.mcp_call("mcp_kanban_task_manager", {
                    "action": "create",
                    "cardId": card_id,
                    "name": name,
                    "position": (idx + 1) * 65536
                })
                tasks.append(result)
            except:
                pass
        return tasks
    
    async def _get_lists(self):
        """Get all lists on the board"""
        if not self.board_id:
            raise RuntimeError("Not initialized - call initialize() first")
        
        result = await self.mcp_call("mcp_kanban_list_manager", {
            "action": "get_all",
            "boardId": self.board_id
        })
        
        return result if isinstance(result, list) else []
    
    async def _get_cards(self):
        """Get all cards on the board"""
        if not self.board_id:
            raise RuntimeError("Not initialized - call initialize() first")
        
        result = await self.mcp_call("mcp_kanban_card_manager", {
            "action": "get_all",
            "boardId": self.board_id
        })
        
        return result if isinstance(result, list) else []
    
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
        
        return await self._card_to_task(card)
    
    async def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID"""
        try:
            card = await self.mcp_call("mcp_kanban_card_manager", {
                "action": "get_details",
                "cardId": task_id
            })
            if card:
                return await self._card_to_task(card)
        except:
            pass
        return None
    
    async def _card_to_task(self, card: Dict[str, Any]) -> Task:
        """Convert a kanban card to a Task object"""
        # Get list information to determine status
        status = TaskStatus.TODO
        if card.get("listId"):
            lists = await self._get_lists()
            for lst in lists:
                if lst["id"] == card["listId"]:
                    list_name = lst["name"].lower()
                    if "progress" in list_name:
                        status = TaskStatus.IN_PROGRESS
                    elif "done" in list_name or "complete" in list_name:
                        status = TaskStatus.DONE
                    elif "blocked" in list_name:
                        status = TaskStatus.BLOCKED
                    break
        
        return Task(
            id=card["id"],
            name=card.get("name", card.get("title", "")),
            description=card.get("description", ""),
            status=status,
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
