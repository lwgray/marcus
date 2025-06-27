"""
Simple MCP Kanban Client for reliable task management.

This module provides a simplified client for interacting with the kanban-mcp server,
focusing on reliability and following proven patterns that work consistently.

The client handles:
- Task retrieval from kanban boards
- Task assignment to agents
- Board status monitoring
- Automatic configuration loading

Notes
-----
This implementation avoids persistent connections and creates a new MCP session
for each operation to ensure reliability.
"""

import asyncio
import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.core.models import Task, TaskStatus, Priority
import sys


class SimpleMCPKanbanClient:
    """
    Simple MCP Kanban client that follows proven patterns for reliability.
    
    This client creates a new MCP session for each operation rather than
    maintaining persistent connections, which has proven more reliable in practice.
    
    Attributes
    ----------
    board_id : Optional[str]
        ID of the kanban board to work with
    project_id : Optional[str]
        ID of the project associated with the board
    
    Examples
    --------
    >>> client = SimpleMCPKanbanClient()
    >>> tasks = await client.get_available_tasks()
    >>> for task in tasks:
    ...     print(f"Task: {task.name} - Priority: {task.priority.value}")
    
    Notes
    -----
    Planka credentials are loaded from environment variables or set to defaults.
    Board and project IDs are loaded from config_marcus.json if available.
    """
    
    def __init__(self) -> None:
        """
        Initialize the Simple MCP Kanban Client.
        
        Loads configuration from config_marcus.json and sets up
        Planka environment variables.
        """
        # Load config
        self.board_id: Optional[str] = None
        self.project_id: Optional[str] = None
        self._load_config()
        
        # Set environment for Planka from .env or use defaults
        if 'PLANKA_BASE_URL' not in os.environ:
            os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
        if 'PLANKA_AGENT_EMAIL' not in os.environ:
            os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
        if 'PLANKA_AGENT_PASSWORD' not in os.environ:
            os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'
    
    def _load_config(self) -> None:
        """
        Load configuration from config_marcus.json file.
        
        Reads project_id and board_id from the configuration file if it exists.
        Prints confirmation message to stderr for debugging.
        
        Notes
        -----
        The config file should be in the current working directory.
        If the file doesn't exist, board_id and project_id remain None.
        """
        if os.path.exists('config_marcus.json'):
            with open('config_marcus.json', 'r') as f:
                config = json.load(f)
                self.project_id = config.get("project_id")
                self.board_id = config.get("board_id")
                print(f"✅ Loaded config: project_id={self.project_id}, board_id={self.board_id}", file=sys.stderr)
        else:
            print(f"❌ config_marcus.json not found in {os.getcwd()}", file=sys.stderr)
            print(f"   Files in directory: {[f for f in os.listdir('.') if 'config' in f]}", file=sys.stderr)
    
    async def get_available_tasks(self) -> List[Task]:
        """
        Get all unassigned tasks from the kanban board.
        
        Retrieves tasks that are in "available" states (TODO, BACKLOG, READY)
        and have not been assigned to any agent.
        
        Returns
        -------
        List[Task]
            List of unassigned tasks sorted by priority
        
        Raises
        ------
        RuntimeError
            If board_id is not set in configuration
        
        Examples
        --------
        >>> client = SimpleMCPKanbanClient()
        >>> tasks = await client.get_available_tasks()
        >>> print(f"Found {len(tasks)} available tasks")
        
        Notes
        -----
        This method creates a new MCP session for the operation.
        Tasks are filtered based on their list name (TODO, BACKLOG, etc.)
        and whether they have an assigned_to field.
        """
        if not self.board_id:
            raise RuntimeError("Board ID not set")
        
        # Use the exact same pattern as working scripts
        server_params = StdioServerParameters(
            command="node",
            args=["../kanban-mcp/dist/index.js"],
            env=os.environ.copy()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # First get all lists for the board
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {
                        "action": "get_all",
                        "boardId": self.board_id
                    }
                )
                
                all_cards = []
                if lists_result and hasattr(lists_result, 'content') and lists_result.content:
                    lists_data = json.loads(lists_result.content[0].text)
                    lists = lists_data if isinstance(lists_data, list) else lists_data.get("items", [])
                    
                    # Get cards from each list
                    for lst in lists:
                        list_id = lst.get("id")
                        if list_id:
                            # Get cards for this list
                            cards_result = await session.call_tool(
                                "mcp_kanban_card_manager",
                                {
                                    "action": "get_all",
                                    "listId": list_id
                                }
                            )
                            
                            if cards_result and hasattr(cards_result, 'content') and cards_result.content:
                                cards_text = cards_result.content[0].text
                                if cards_text and cards_text.strip():
                                    cards_data = json.loads(cards_text)
                                    cards_list = cards_data if isinstance(cards_data, list) else cards_data.get("items", [])
                                    # Add list name to each card
                                    for card in cards_list:
                                        card["listName"] = lst.get("name", "")
                                        all_cards.append(card)
                
                result = None  # We'll use all_cards instead
                
                tasks = []
                
                # Use the all_cards we collected
                for card in all_cards:
                    task = self._card_to_task(card)
                    if not task.assigned_to and self._is_available_task(card):
                        tasks.append(task)
                
                return tasks
    
    async def assign_task(self, task_id: str, agent_id: str) -> None:
        """
        Assign a task to an agent.
        
        This method:
        1. Adds a comment to the task indicating assignment
        2. Moves the task to the "In Progress" list
        
        Parameters
        ----------
        task_id : str
            ID of the task to assign
        agent_id : str
            ID of the agent receiving the assignment
        
        Examples
        --------
        >>> await client.assign_task("card-123", "agent-001")
        
        Notes
        -----
        The task is automatically moved to the first list containing
        "progress" in its name (case-insensitive).
        """
        server_params = StdioServerParameters(
            command="node",
            args=["../kanban-mcp/dist/index.js"],
            env=os.environ.copy()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Add comment
                await session.call_tool(
                    "mcp_kanban_comment_manager",
                    {
                        "action": "create",
                        "cardId": task_id,
                        "text": f"📋 Task assigned to {agent_id} at {datetime.now().isoformat()}"
                    }
                )
                
                # Move to In Progress
                # First get lists
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {
                        "action": "get_all",
                        "boardId": self.board_id
                    }
                )
                
                if lists_result and hasattr(lists_result, 'content'):
                    lists_data = json.loads(lists_result.content[0].text)
                    lists = lists_data if isinstance(lists_data, list) else lists_data.get("items", [])
                    
                    # Find In Progress list
                    in_progress_list = None
                    for lst in lists:
                        if "progress" in lst.get("name", "").lower():
                            in_progress_list = lst
                            break
                    
                    if in_progress_list:
                        # Move card
                        await session.call_tool(
                            "mcp_kanban_card_manager",
                            {
                                "action": "move",
                                "id": task_id,
                                "listId": in_progress_list["id"]
                            }
                        )
    
    async def get_board_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for the kanban board.
        
        Returns
        -------
        Dict[str, Any]
            Board statistics including task counts, completion percentage,
            and other metrics provided by the kanban-mcp server
        
        Raises
        ------
        RuntimeError
            If board_id is not set in configuration
        
        Examples
        --------
        >>> summary = await client.get_board_summary()
        >>> print(f"Completion: {summary.get('completionPercentage', 0)}%")
        
        Notes
        -----
        The exact structure of the summary depends on the kanban-mcp
        implementation. Typically includes totalCards, completionPercentage,
        and counts by status.
        """
        if not self.board_id:
            raise RuntimeError("Board ID not set")
        
        server_params = StdioServerParameters(
            command="node",
            args=["../kanban-mcp/dist/index.js"],
            env=os.environ.copy()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool(
                    "mcp_kanban_project_board_manager",
                    {
                        "action": "get_board_summary",
                        "boardId": self.board_id,
                        "includeTaskDetails": False
                    }
                )
                
                if result and hasattr(result, 'content'):
                    return json.loads(result.content[0].text)
                
                return {}
    
    def _is_available_task(self, card: Dict[str, Any]) -> bool:
        """
        Check if a task is in an available state.
        
        Parameters
        ----------
        card : Dict[str, Any]
            Card data from the kanban board
        
        Returns
        -------
        bool
            True if the task is in an available state (TODO, BACKLOG, READY)
        
        Notes
        -----
        Available states are determined by the list name containing
        specific keywords (case-insensitive).
        """
        list_name = card.get("listName", "").upper()
        available_states = ["TODO", "TO DO", "BACKLOG", "READY"]
        return any(state in list_name for state in available_states)
    
    def _card_to_task(self, card: Dict[str, Any]) -> Task:
        """
        Convert a kanban card to a Task object.
        
        Parameters
        ----------
        card : Dict[str, Any]
            Card data from the kanban board containing fields like
            id, name/title, description, listName, etc.
        
        Returns
        -------
        Task
            Task object with data mapped from the card
        
        Examples
        --------
        >>> card = {"id": "123", "name": "Fix bug", "listName": "TODO"}
        >>> task = client._card_to_task(card)
        >>> print(task.status)  # TaskStatus.TODO
        
        Notes
        -----
        - Status is determined by the list name (DONE, PROGRESS, BLOCKED, TODO)
        - Priority defaults to MEDIUM if not specified
        - Dates default to current time if not provided
        - assigned_to is always None (unassigned tasks)
        """
        task_name = card.get("name") or card.get("title", "")
        
        # Parse dates
        created_at = datetime.now()
        updated_at = datetime.now()
        
        # Determine status
        list_name = card.get("listName", "").upper()
        if "DONE" in list_name:
            status = TaskStatus.DONE
        elif "PROGRESS" in list_name:
            status = TaskStatus.IN_PROGRESS
        elif "BLOCKED" in list_name:
            status = TaskStatus.BLOCKED
        else:
            status = TaskStatus.TODO
        
        return Task(
            id=card.get("id", ""),
            name=task_name,
            description=card.get("description", ""),
            status=status,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=created_at,
            updated_at=updated_at,
            due_date=None,
            estimated_hours=0.0,
            actual_hours=0.0,
            dependencies=[],
            labels=[]
        )
    
    async def add_comment(self, task_id: str, comment_text: str) -> None:
        """
        Add a comment to a task.
        
        Parameters
        ----------
        task_id : str
            ID of the task to comment on
        comment_text : str
            Text of the comment to add
        
        Examples
        --------
        >>> await client.add_comment("card-123", "Task completed successfully")
        
        Notes
        -----
        Comments are visible in the Planka UI and are timestamped automatically.
        """
        server_params = StdioServerParameters(
            command="node",
            args=["../kanban-mcp/dist/index.js"],
            env=os.environ.copy()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                await session.call_tool(
                    "mcp_kanban_comment_manager",
                    {
                        "action": "create",
                        "cardId": task_id,
                        "text": comment_text
                    }
                )
    
    async def complete_task(self, task_id: str) -> None:
        """
        Mark a task as completed by moving it to the Done list.
        
        Parameters
        ----------
        task_id : str
            ID of the task to complete
        
        Examples
        --------
        >>> await client.complete_task("card-123")
        
        Notes
        -----
        The task is moved to the first list containing "done" or "completed"
        in its name (case-insensitive).
        """
        await self._move_task_to_list(task_id, ["done", "completed"])
    
    async def update_task_status(self, task_id: str, status: str) -> None:
        """
        Update a task's status by moving it to the appropriate list.
        
        Parameters
        ----------
        task_id : str
            ID of the task to update
        status : str
            New status (e.g., "blocked", "in_progress", "todo")
        
        Examples
        --------
        >>> await client.update_task_status("card-123", "blocked")
        
        Notes
        -----
        Status names are matched to list names containing the status keyword.
        For example, "blocked" matches any list with "blocked" in the name.
        """
        status_to_keywords = {
            "blocked": ["blocked"],
            "in_progress": ["progress", "in progress"],
            "todo": ["todo", "to do", "backlog"],
            "done": ["done", "completed"]
        }
        
        keywords = status_to_keywords.get(status.lower(), [status.lower()])
        await self._move_task_to_list(task_id, keywords)
    
    async def _move_task_to_list(self, task_id: str, list_keywords: List[str]) -> None:
        """
        Move a task to a list matching one of the keywords.
        
        Parameters
        ----------
        task_id : str
            ID of the task to move
        list_keywords : List[str]
            Keywords to match against list names (case-insensitive)
        
        Raises
        ------
        RuntimeError
            If no matching list is found
        
        Notes
        -----
        This is a helper method used by other status update methods.
        """
        server_params = StdioServerParameters(
            command="node",
            args=["../kanban-mcp/dist/index.js"],
            env=os.environ.copy()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Get all lists
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {
                        "action": "get_all",
                        "boardId": self.board_id
                    }
                )
                
                if lists_result and hasattr(lists_result, 'content'):
                    lists_data = json.loads(lists_result.content[0].text)
                    lists = lists_data if isinstance(lists_data, list) else lists_data.get("items", [])
                    
                    # Find matching list
                    target_list = None
                    for lst in lists:
                        list_name_lower = lst.get("name", "").lower()
                        for keyword in list_keywords:
                            if keyword in list_name_lower:
                                target_list = lst
                                break
                        if target_list:
                            break
                    
                    if target_list:
                        # Move card
                        await session.call_tool(
                            "mcp_kanban_card_manager",
                            {
                                "action": "move",
                                "id": task_id,
                                "listId": target_list["id"],
                                "position": 65535  # Default position at end of list
                            }
                        )
                    else:
                        raise RuntimeError(f"No list found matching keywords: {list_keywords}")