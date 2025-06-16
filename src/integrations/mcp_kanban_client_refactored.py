"""
Refactored MCP Kanban Client with proper async context manager pattern
"""

import asyncio
from typing import List, Dict, Optional, Any, AsyncContextManager
from datetime import datetime
import json
import os
import shutil
import subprocess
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.core.models import Task, TaskStatus, Priority, ProjectState
from src.config.settings import Settings


class MCPConnection:
    """Manages a single MCP connection with proper lifecycle management"""
    
    def __init__(self, command: str, args: List[str], env: Dict[str, str]):
        self.server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        self.session: Optional[ClientSession] = None
        self._transport_context = None
        self._read_stream = None
        self._write_stream = None
        
    async def __aenter__(self):
        """Enter the async context manager"""
        # Start the transport
        self._transport_context = stdio_client(self.server_params)
        self._read_stream, self._write_stream = await self._transport_context.__aenter__()
        
        # Create and initialize session
        self.session = ClientSession(self._read_stream, self._write_stream)
        await self.session.initialize()
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager"""
        self.session = None
        if self._transport_context:
            await self._transport_context.__aexit__(exc_type, exc_val, exc_tb)
            
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool"""
        if not self.session:
            raise RuntimeError("Connection not active")
        return await self.session.call_tool(tool_name, arguments)


class MCPKanbanClient:
    """Refactored client for interacting with MCP Kanban server"""
    
    def __init__(self):
        self.board_id: Optional[str] = None
        self.project_id: Optional[str] = None
        self.settings = Settings()
        self._node_path: Optional[str] = None
        self._kanban_mcp_path = "/Users/lwgray/dev/kanban-mcp/dist/index.js"
        
        # Load configuration from config_pm_agent.json
        self._load_config()
        
        # Use config values or defaults for Planka credentials
        self._env = {
            "PLANKA_BASE_URL": os.environ.get("PLANKA_BASE_URL", "http://localhost:3333"),
            "PLANKA_AGENT_EMAIL": os.environ.get("PLANKA_AGENT_EMAIL", "demo@demo.demo"), 
            "PLANKA_AGENT_PASSWORD": os.environ.get("PLANKA_AGENT_PASSWORD", "demo")
        }
    
    def _load_config(self):
        """Load configuration from config_pm_agent.json"""
        config_path = "config_pm_agent.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.project_id = config.get("project_id")
                    self.board_id = config.get("board_id")
                    
                    # Also update Planka credentials if provided
                    if "planka" in config:
                        planka_config = config["planka"]
                        if "base_url" in planka_config:
                            os.environ["PLANKA_BASE_URL"] = planka_config["base_url"]
                        if "email" in planka_config:
                            os.environ["PLANKA_AGENT_EMAIL"] = planka_config["email"]
                        if "password" in planka_config:
                            os.environ["PLANKA_AGENT_PASSWORD"] = planka_config["password"]
                    
                    print(f"✅ Loaded config: project_id={self.project_id}, board_id={self.board_id}", file=sys.stderr)
            except Exception as e:
                print(f"⚠️ Error loading config_pm_agent.json: {e}", file=sys.stderr)
    
    def _find_node_executable(self) -> str:
        """Find Node.js executable in common locations"""
        if self._node_path:
            return self._node_path
            
        possible_paths = [
            "/usr/local/bin/node",
            "/opt/homebrew/bin/node", 
            "/usr/bin/node",
            shutil.which("node"),
        ]
        
        for path in possible_paths:
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                try:
                    result = subprocess.run([path, "--version"], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and "v" in result.stdout:
                        self._node_path = path
                        return path
                except:
                    continue
        
        raise RuntimeError("Node.js not found! Please install Node.js or add it to your PATH.")
    
    @asynccontextmanager
    async def connect(self):
        """Create a connection context that can be used for operations"""
        node_path = self._find_node_executable()
        
        async with MCPConnection(node_path, [self._kanban_mcp_path], self._env) as conn:
            # If project/board not set, try to find them
            if not self.project_id:
                await self._find_project(conn)
            if not self.board_id and self.project_id:
                await self._find_board(conn)
                
            yield conn
    
    async def _find_project(self, conn: MCPConnection):
        """Find the Task Master Test project"""
        # Skip if already set from config
        if self.project_id:
            print(f"✅ Using configured project ID: {self.project_id}", file=sys.stderr)
            return
            
        result = await conn.call_tool("mcp_kanban_project_board_manager", {
            "action": "get_projects",
            "page": 1,
            "perPage": 25
        })
        
        # Parse response
        if hasattr(result, 'content') and result.content:
            data = json.loads(result.content[0].text)
            projects = data.get("items", []) if isinstance(data, dict) else data
            
            for project in (projects if isinstance(projects, list) else [projects]):
                if "Task Master Test" in project.get("name", ""):
                    self.project_id = project["id"]
                    print(f"✅ Found project: {project['name']} (ID: {self.project_id})", file=sys.stderr)
                    break
    
    async def _find_board(self, conn: MCPConnection):
        """Find a board for the project"""
        # Skip if already set from config
        if self.board_id:
            print(f"✅ Using configured board ID: {self.board_id}", file=sys.stderr)
            return
            
        if not self.project_id:
            return
            
        result = await conn.call_tool("mcp_kanban_project_board_manager", {
            "action": "get_boards",
            "projectId": self.project_id,
            "page": 1,
            "perPage": 25
        })
        
        # Parse response
        if hasattr(result, 'content') and result.content:
            data = json.loads(result.content[0].text)
            boards = data if isinstance(data, list) else data.get("items", [])
            
            if boards:
                board = boards[0]  # Use first board
                self.board_id = board["id"]
                print(f"✅ Found board: {board['name']} (ID: {self.board_id})", file=sys.stderr)
    
    async def get_available_tasks(self) -> List[Task]:
        """Get all unassigned tasks from the board"""
        if not self.board_id:
            raise RuntimeError("Board ID not set")
        
        async with self.connect() as conn:
            result = await conn.call_tool("mcp_kanban_card_manager", {
                "action": "get_all",
                "boardId": self.board_id
            })
            
            tasks = []
            if hasattr(result, 'content') and result.content:
                data = json.loads(result.content[0].text)
                cards = data if isinstance(data, list) else data.get("items", [])
                
                for card in cards:
                    task = self._card_to_task(card)
                    if not task.assigned_to and self._is_available_task(card):
                        tasks.append(task)
            
            return tasks
    
    async def get_task_details(self, task_id: str) -> Task:
        """Get detailed information about a specific task"""
        async with self.connect() as conn:
            result = await conn.call_tool("mcp_kanban_card_manager", {
                "action": "get_details",
                "cardId": task_id
            })
            
            if hasattr(result, 'content') and result.content:
                data = json.loads(result.content[0].text)
                return self._card_to_task(data)
            
            raise ValueError(f"Could not get details for task {task_id}")
    
    async def assign_task(self, task_id: str, agent_id: str):
        """Assign a task to an agent"""
        async with self.connect() as conn:
            # Add assignment comment
            await conn.call_tool("mcp_kanban_comment_manager", {
                "action": "create",
                "cardId": task_id,
                "text": f"📋 Task assigned to {agent_id} at {datetime.now().isoformat()}"
            })
            
            # Move to IN PROGRESS list
            await self._move_to_list(conn, task_id, "In Progress")
    
    async def _move_to_list(self, conn: MCPConnection, task_id: str, target_list_name: str):
        """Move a card to a specific list by name"""
        if not self.board_id:
            raise RuntimeError("Board ID not set")
        
        # Get all lists for the board
        result = await conn.call_tool("mcp_kanban_list_manager", {
            "action": "get_all",
            "boardId": self.board_id
        })
        
        if hasattr(result, 'content') and result.content:
            data = json.loads(result.content[0].text)
            lists = data if isinstance(data, list) else data.get("items", [])
            
            # Find the target list
            target_list = None
            for lst in lists:
                if target_list_name.lower() in lst.get("name", "").lower():
                    target_list = lst
                    break
            
            if target_list:
                # Move the card
                await conn.call_tool("mcp_kanban_card_manager", {
                    "action": "move",
                    "id": task_id,
                    "listId": target_list["id"]
                })
            else:
                print(f"⚠️  Warning: Could not find list '{target_list_name}' on board", file=sys.stderr)
    
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
        
        async with self.connect() as conn:
            await self._move_to_list(conn, task_id, target_list)
    
    async def update_task_progress(self, task_id: str, progress: int):
        """Update task progress percentage via comment"""
        async with self.connect() as conn:
            await conn.call_tool("mcp_kanban_comment_manager", {
                "action": "create",
                "cardId": task_id,
                "text": f"📊 Progress update: {progress}% complete"
            })
    
    async def complete_task(self, task_id: str):
        """Mark a task as completed"""
        async with self.connect() as conn:
            await self.update_task_status(task_id, "done")
            await conn.call_tool("mcp_kanban_comment_manager", {
                "action": "create",
                "cardId": task_id,
                "text": f"✅ Task completed at {datetime.now().isoformat()}"
            })
    
    async def add_comment(self, task_id: str, text: str):
        """Add a comment to a task"""
        async with self.connect() as conn:
            await conn.call_tool("mcp_kanban_comment_manager", {
                "action": "create",
                "cardId": task_id,
                "text": text
            })
    
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create a new task on the board"""
        if not self.board_id:
            raise RuntimeError("Board ID not set")
        
        async with self.connect() as conn:
            # Get the TODO list
            lists_result = await conn.call_tool("mcp_kanban_list_manager", {
                "action": "get_all",
                "boardId": self.board_id
            })
            
            todo_list = None
            if hasattr(lists_result, 'content') and lists_result.content:
                data = json.loads(lists_result.content[0].text)
                lists = data if isinstance(data, list) else data.get("items", [])
                
                for lst in lists:
                    list_name = lst.get("name", "").upper()
                    if any(name in list_name for name in ["TODO", "TO DO", "BACKLOG"]):
                        todo_list = lst
                        break
            
            if not todo_list:
                raise ValueError("No TODO list found on board")
            
            # Create the card
            result = await conn.call_tool("mcp_kanban_card_manager", {
                "action": "create",
                "listId": todo_list["id"],
                "name": task_data["name"],
                "description": task_data.get("description", "")
            })
            
            if hasattr(result, 'content') and result.content:
                card_data = json.loads(result.content[0].text)
                
                # Add labels if specified
                if task_data.get("labels"):
                    for label_name in task_data["labels"]:
                        await self._add_label_to_card(conn, card_data["id"], label_name)
                
                return self._card_to_task(card_data)
            
            raise ValueError("Failed to create task")
    
    async def _add_label_to_card(self, conn: MCPConnection, card_id: str, label_name: str):
        """Add a label to a card by name"""
        try:
            # Get available labels
            result = await conn.call_tool("mcp_kanban_label_manager", {
                "action": "get_all",
                "boardId": self.board_id
            })
            
            if hasattr(result, 'content') and result.content:
                data = json.loads(result.content[0].text)
                labels = data if isinstance(data, list) else data.get("items", [])
                
                # Find matching label
                for label in labels:
                    if label_name.lower() in label.get("name", "").lower():
                        await conn.call_tool("mcp_kanban_label_manager", {
                            "action": "add_to_card",
                            "cardId": card_id,
                            "labelId": label["id"]
                        })
                        break
        except Exception as e:
            print(f"⚠️  Warning: Could not add label '{label_name}': {e}", file=sys.stderr)
    
    async def get_board_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the board"""
        if not self.board_id:
            raise RuntimeError("Board ID not set")
        
        async with self.connect() as conn:
            result = await conn.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_board_summary",
                "boardId": self.board_id
            })
            
            if hasattr(result, 'content') and result.content:
                return json.loads(result.content[0].text)
            
            return {}
    
    async def check_connection(self) -> bool:
        """Check if connection to kanban-mcp is possible"""
        try:
            async with self.connect() as conn:
                # Try a simple operation to verify connection
                result = await conn.call_tool("mcp_kanban_project_board_manager", {
                    "action": "get_projects",
                    "page": 1,
                    "perPage": 1
                })
                return hasattr(result, 'content') and result.content is not None
        except Exception:
            return False
    
    # Helper methods remain the same
    def _is_available_task(self, card: Dict[str, Any]) -> bool:
        """Check if a task is in an available state"""
        list_name = card.get("listName", "").upper()
        available_states = ["TODO", "TO DO", "BACKLOG", "READY"]
        return any(state in list_name for state in available_states)
    
    def _card_to_task(self, card: Dict[str, Any]) -> Task:
        """Convert a kanban card to a Task object"""
        task_name = card.get("name") or card.get("title", "")
        
        # Parse dates
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
            assigned_to=card.get("assigned_to"),
            created_at=created_at,
            updated_at=updated_at,
            due_date=due_date,
            estimated_hours=0.0,
            actual_hours=0.0,
            dependencies=[],
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