import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import os
import shutil
import subprocess

from mcp import ClientSession, StdioServerParameters
from mcp import stdio_client

from src.core.models import Task, TaskStatus, Priority, ProjectState
from src.config.settings import Settings


class MCPKanbanClient:
    """Client for interacting with MCP Kanban server - Fixed with proper Node.js path"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.board_id: Optional[str] = None
        self.project_id: Optional[str] = None
        self.settings = Settings()
        self._stdio_transport = None
    
    def _find_node_executable(self) -> str:
        """Find Node.js executable in common locations"""
        # Try common locations for Node.js
        possible_paths = [
            "/usr/local/bin/node",
            "/opt/homebrew/bin/node", 
            "/usr/bin/node",
            shutil.which("node"),  # Check PATH
        ]
        
        for path in possible_paths:
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                try:
                    # Test that it's actually node
                    result = subprocess.run([path, "--version"], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and "v" in result.stdout:
                        print(f"✅ Found Node.js at: {path}")
                        return path
                except:
                    continue
        
        # If not found, try to find it through system
        try:
            result = subprocess.run(["which", "node"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                node_path = result.stdout.strip()
                if os.path.isfile(node_path):
                    print(f"✅ Found Node.js via which: {node_path}")
                    return node_path
        except:
            pass
        
        raise RuntimeError(
            "Node.js not found! Please install Node.js or add it to your PATH.\n"
            "Common solutions:\n"
            "1. Install Node.js: brew install node\n"  
            "2. Add to PATH: export PATH=/usr/local/bin:$PATH\n"
            "3. Use full path in environment variable"
        )
    
    async def connect(self):
        """Connect to the existing MCP Kanban server"""
        # Find Node.js executable
        try:
            node_executable = self._find_node_executable()
        except RuntimeError as e:
            print(f"❌ {e}")
            raise
        
        # Use the same configuration from your MCP config file but with full path
        kanban_command = node_executable
        kanban_args = ["/Users/lwgray/dev/kanban-mcp/dist/index.js"]
        
        print(f"🔗 Connecting to MCP server: {kanban_command} {' '.join(kanban_args)}")
        
        server_params = StdioServerParameters(
            command=kanban_command,
            args=kanban_args,
            env={
                "PLANKA_BASE_URL": "http://localhost:3333",
                "PLANKA_AGENT_EMAIL": "demo@demo.demo", 
                "PLANKA_AGENT_PASSWORD": "demo"
            }
        )
        
        # Use stdio_client as a context manager
        self._stdio_transport = stdio_client(server_params)
        read, write = await self._stdio_transport.__aenter__()
        
        # Create session with the streams
        self.session = ClientSession(read, write)
        
        # Initialize the session
        await self.session.initialize()
        
        # Get available projects with proper pagination
        result = await self._call_tool("mcp_kanban_project_board_manager", {
            "action": "get_projects",
            "page": 1,
            "perPage": 25
        })
        
        if result:
            # Handle paginated response
            projects = result.get("items", []) if isinstance(result, dict) else result
            projects = projects if isinstance(projects, list) else [projects]
            
            # Find Task Master Test project
            for project in projects:
                if "Task Master Test" in project.get("name", ""):
                    self.project_id = project["id"]
                    print(f"✅ Found Task Master Test project (ID: {self.project_id})")
                    
                    # Get boards for this project with proper pagination
                    board_result = await self._call_tool("mcp_kanban_project_board_manager", {
                        "action": "get_boards",
                        "page": 1,
                        "perPage": 25
                    })
                    
                    if board_result:
                        # Handle paginated response
                        boards = board_result.get("items", []) if isinstance(board_result, dict) else board_result
                        boards = boards if isinstance(boards, list) else [boards]
                        
                        # Find board for our project
                        for board in boards:
                            if board.get("projectId") == self.project_id:
                                self.board_id = board["id"]
                                print(f"✅ Found board (ID: {self.board_id})")
                                break
                    break
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self._stdio_transport:
            await self._stdio_transport.__aexit__(None, None, None)
    
    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool and return the result"""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        result = await self.session.call_tool(tool_name, arguments)
        return result
    
    async def get_available_tasks(self) -> List[Task]:
        """Get all unassigned tasks from the board"""
        if not self.board_id:
            raise RuntimeError("Board ID not set - call connect() first")
        
        # Get all cards from the board (not filtered by column)
        cards = await self._call_tool("mcp_kanban_card_manager", {
            "action": "get_all",
            "boardId": self.board_id
        })
        
        tasks = []
        if cards:
            card_list = cards if isinstance(cards, list) else [cards]
            for card in card_list:
                # Get detailed task info
                try:
                    details = await self._call_tool("mcp_kanban_card_manager", {
                        "action": "get_details",
                        "cardId": card["id"]
                    })
                    
                    task = self._card_to_task(details if details else card)
                    # Filter for unassigned tasks in TODO-like lists
                    if not task.assigned_to and self._is_available_task(card):
                        tasks.append(task)
                except Exception as e:
                    print(f"⚠️  Error getting details for card {card.get('id')}: {e}")
                    # Fallback to basic card data
                    task = self._card_to_task(card)
                    if not task.assigned_to and self._is_available_task(card):
                        tasks.append(task)
        
        return tasks
    
    def _is_available_task(self, card: Dict[str, Any]) -> bool:
        """Check if a task is in an available state (TODO, Backlog, etc.)"""
        # Get the list name from card data
        list_name = card.get("listName", "").upper()
        available_states = ["TODO", "TO DO", "BACKLOG", "READY"]
        return any(state in list_name for state in available_states)
    
    async def get_task_details(self, task_id: str) -> Task:
        """Get detailed information about a specific task"""
        details = await self._call_tool("mcp_kanban_card_manager", {
            "action": "get_details",
            "cardId": task_id
        })
        
        return self._card_to_task(details)
    
    async def assign_task(self, task_id: str, agent_id: str):
        """Assign a task to an agent"""
        # Add assignment comment
        await self.add_comment(
            task_id,
            f"📋 Task assigned to {agent_id} at {datetime.now().isoformat()}"
        )
        
        # Move to IN PROGRESS list
        await self._move_to_list(task_id, "In Progress")
    
    async def _move_to_list(self, task_id: str, target_list_name: str):
        """Move a card to a specific list by name"""
        if not self.board_id:
            raise RuntimeError("Board ID not set")
        
        # Get all lists for the board
        lists = await self._call_tool("mcp_kanban_list_manager", {
            "action": "get_all",
            "boardId": self.board_id
        })
        
        # Find the target list
        target_list = None
        for lst in lists:
            if target_list_name.lower() in lst.get("name", "").lower():
                target_list = lst
                break
        
        if target_list:
            # Move the card
            await self._call_tool("mcp_kanban_card_manager", {
                "action": "move",
                "id": task_id,
                "listId": target_list["id"]
            })
        else:
            print(f"⚠️  Warning: Could not find list '{target_list_name}' on board")
    
    async def update_task_status(self, task_id: str, status: str):
        """Update the status of a task by moving it to appropriate list"""
        status_to_list = {
            "todo": "To Do",
            "in_progress": "In Progress", 
            "blocked": "On Hold",
            "done": "Done",
            "ready": "To Do"
        }
        
        target_list = status_to_list.get(status.lower(), "To Do")
        await self._move_to_list(task_id, target_list)
    
    async def update_task_progress(self, task_id: str, progress: int):
        """Update task progress percentage via comment (Planka doesn't have built-in progress)"""
        await self.add_comment(
            task_id,
            f"📊 Progress update: {progress}% complete"
        )
    
    async def complete_task(self, task_id: str):
        """Mark a task as completed"""
        await self.update_task_status(task_id, "done")
        
        await self.add_comment(
            task_id,
            f"✅ Task completed at {datetime.now().isoformat()}"
        )
    
    async def add_comment(self, task_id: str, text: str):
        """Add a comment to a task"""
        await self._call_tool("mcp_kanban_comment_manager", {
            "action": "create",
            "cardId": task_id,
            "text": text
        })
    
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create a new task on the board"""
        if not self.board_id:
            raise RuntimeError("Board ID not set")
        
        # Get the TODO list
        lists = await self._call_tool("mcp_kanban_list_manager", {
            "action": "get_all",
            "boardId": self.board_id
        })
        
        todo_list = None
        for lst in lists:
            list_name = lst.get("name", "").upper()
            if any(name in list_name for name in ["TODO", "TO DO", "BACKLOG"]):
                todo_list = lst
                break
        
        if not todo_list:
            raise ValueError("No TODO list found on board")
        
        # Create the card
        card = await self._call_tool("mcp_kanban_card_manager", {
            "action": "create",
            "listId": todo_list["id"],
            "name": task_data["name"],
            "description": task_data.get("description", "")
        })
        
        # Add labels if specified
        if task_data.get("labels"):
            for label_name in task_data["labels"]:
                await self._add_label_to_card(card["id"], label_name)
        
        return self._card_to_task(card)
    
    async def _add_label_to_card(self, card_id: str, label_name: str):
        """Add a label to a card by name"""
        try:
            # Get available labels
            labels = await self._call_tool("mcp_kanban_label_manager", {
                "action": "get_all",
                "boardId": self.board_id
            })
            
            # Find matching label
            for label in labels:
                if label_name.lower() in label.get("name", "").lower():
                    await self._call_tool("mcp_kanban_label_manager", {
                        "action": "add_to_card",
                        "cardId": card_id,
                        "labelId": label["id"]
                    })
                    break
        except Exception as e:
            print(f"⚠️  Warning: Could not add label '{label_name}': {e}")
    
    async def add_dependency(self, task_id: str, depends_on_id: str):
        """Add a dependency between tasks (via comment since Planka doesn't have native dependencies)"""
        await self.add_comment(
            task_id,
            f"🔗 Depends on task: {depends_on_id}"
        )
        
        await self.add_comment(
            depends_on_id,
            f"🔗 Task {task_id} depends on this task"
        )
    
    async def get_dependent_tasks(self, task_id: str) -> List[Task]:
        """Get all tasks that depend on a given task (by parsing comments)"""
        # This would require parsing all comments across the board
        # For now, return empty list - would need more sophisticated implementation
        return []
    
    async def get_board_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the board"""
        if not self.board_id:
            raise RuntimeError("Board ID not set")
        
        summary = await self._call_tool("mcp_kanban_project_board_manager", {
            "action": "get_board_summary",
            "boardId": self.board_id
        })
        
        return summary
    
    def _card_to_task(self, card: Dict[str, Any]) -> Task:
        """Convert a kanban card to a Task object"""
        # Handle both 'name' and 'title' fields
        task_name = card.get("name") or card.get("title", "")
        
        # Parse created/updated dates
        created_at = card.get("createdAt", card.get("created_at"))
        updated_at = card.get("updatedAt", card.get("updated_at"))
        
        if created_at:
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = datetime.now()
        else:
            created_at = datetime.now()
        
        if updated_at:
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except:
                updated_at = created_at
        else:
            updated_at = created_at
        
        # Parse due date
        due_date = card.get("dueDate")
        if due_date:
            try:
                due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            except:
                due_date = None
        
        return Task(
            id=card["id"],
            name=task_name,
            description=card.get("description", ""),
            status=self._map_status_from_list(card),
            priority=self._extract_priority_from_labels(card),
            assigned_to=card.get("assigned_to"),  # Planka might not have this field
            created_at=created_at,
            updated_at=updated_at,
            due_date=due_date,
            estimated_hours=0.0,  # Would need to parse from description or comments
            actual_hours=0.0,
            dependencies=[],  # Would need to parse from comments
            labels=self._extract_labels(card)
        )
    
    def _map_status_from_list(self, card: Dict[str, Any]) -> TaskStatus:
        """Map list name to TaskStatus"""
        list_name = card.get("listName", "").upper()
        
        if any(name in list_name for name in ["TODO", "BACKLOG"]):
            return TaskStatus.TODO
        elif "PROGRESS" in list_name:
            return TaskStatus.IN_PROGRESS
        elif any(name in list_name for name in ["HOLD", "BLOCKED"]):
            return TaskStatus.BLOCKED
        elif "DONE" in list_name:
            return TaskStatus.DONE
        else:
            return TaskStatus.TODO
    
    def _extract_priority_from_labels(self, card: Dict[str, Any]) -> Priority:
        """Extract priority from card labels"""
        labels = card.get("labels", [])
        
        for label in labels:
            label_name = label.get("name", "").upper()
            if "CRITICAL" in label_name or "P0" in label_name:
                return Priority.URGENT
            elif "HIGH" in label_name or "P1" in label_name:
                return Priority.HIGH
            elif "MEDIUM" in label_name or "P2" in label_name:
                return Priority.MEDIUM
            elif "LOW" in label_name or "P3" in label_name:
                return Priority.LOW
        
        return Priority.MEDIUM
    
    def _extract_labels(self, card: Dict[str, Any]) -> List[str]:
        """Extract label names from card"""
        labels = card.get("labels", [])
        return [label.get("name", "") for label in labels if label.get("name")]
