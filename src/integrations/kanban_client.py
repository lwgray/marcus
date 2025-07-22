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
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters
from src.core.models import Priority, Task, TaskStatus

logger = logging.getLogger(__name__)


class KanbanClient:
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
    >>> client = KanbanClient()
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
        Planka environment variables. Config file takes precedence.
        """
        # Initialize attributes
        self.board_id: Optional[str] = None
        self.project_id: Optional[str] = None

        # Load config first - this may set environment variables
        self._load_config()

        # Set environment for Planka from .env or use defaults (only if not already set by config)
        if "PLANKA_BASE_URL" not in os.environ:
            os.environ["PLANKA_BASE_URL"] = "http://localhost:3333"
        if "PLANKA_AGENT_EMAIL" not in os.environ:
            os.environ["PLANKA_AGENT_EMAIL"] = "demo@demo.demo"
        if "PLANKA_AGENT_PASSWORD" not in os.environ:
            os.environ["PLANKA_AGENT_PASSWORD"] = "demo"

    def _load_config(self) -> None:
        """
        Load configuration from config_marcus.json file.

        Reads project_id, board_id, and Planka credentials from the configuration file if it exists.
        Prints confirmation message to stderr for debugging.

        Notes
        -----
        The config file is searched in multiple locations:
        1. Current working directory
        2. Project root (relative to this file)
        """
        # Try multiple locations for config file
        from pathlib import Path

        config_paths = [
            Path("config_marcus.json"),  # Current directory
            Path(__file__).parent.parent.parent / "config_marcus.json",  # Project root
        ]

        config_path = None
        for path in config_paths:
            if path.exists():
                config_path = path
                break

        if config_path:
            with open(config_path, "r") as f:
                config = json.load(f)
                self.project_id = config.get("project_id")
                self.board_id = config.get("board_id")

                # Load Planka credentials from config if available
                planka_config = config.get("planka", {})
                if planka_config.get("base_url"):
                    os.environ["PLANKA_BASE_URL"] = planka_config["base_url"]
                if planka_config.get("email"):
                    os.environ["PLANKA_AGENT_EMAIL"] = planka_config["email"]
                if planka_config.get("password"):
                    os.environ["PLANKA_AGENT_PASSWORD"] = planka_config["password"]

                # Config loaded successfully - don't print as it interferes with MCP stdio
        else:
            print(
                f"❌ config_marcus.json not found in any of the following locations:",
                file=sys.stderr,
            )
            for path in config_paths:
                print(f"   - {path.absolute()}", file=sys.stderr)

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
        >>> client = KanbanClient()
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
            command="node", args=["../kanban-mcp/dist/index.js"], env=os.environ.copy()
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # First get all lists for the board
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {"action": "get_all", "boardId": self.board_id},
                )

                all_cards = []
                if (
                    lists_result
                    and hasattr(lists_result, "content")
                    and lists_result.content
                ):
                    lists_data = json.loads(lists_result.content[0].text)
                    lists = (
                        lists_data
                        if isinstance(lists_data, list)
                        else lists_data.get("items", [])
                    )

                    # Get cards from each list
                    for lst in lists:
                        list_id = lst.get("id")
                        if list_id:
                            # Get cards for this list
                            cards_result = await session.call_tool(
                                "mcp_kanban_card_manager",
                                {"action": "get_all", "listId": list_id},
                            )

                            if (
                                cards_result
                                and hasattr(cards_result, "content")
                                and cards_result.content
                            ):
                                cards_text = cards_result.content[0].text
                                if cards_text and cards_text.strip():
                                    cards_data = json.loads(cards_text)
                                    cards_list = (
                                        cards_data
                                        if isinstance(cards_data, list)
                                        else cards_data.get("items", [])
                                    )
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

                # Apply the same dependency ID mapping and filtering as get_all_tasks()
                # Build mapping of original IDs to new IDs
                id_mapping = {}
                for task in tasks:
                    if hasattr(task, "_original_id") and task._original_id:
                        id_mapping[task._original_id] = task.id

                # Resolve dependencies using the mapping
                if id_mapping:
                    logger.debug(
                        f"Resolving dependencies with ID mapping: {id_mapping}"
                    )
                    for task in tasks:
                        if task.dependencies:
                            resolved_deps = []
                            for dep_id in task.dependencies:
                                if dep_id in id_mapping:
                                    # Dependency exists on the board - resolve it
                                    resolved_id = id_mapping[dep_id]
                                    logger.debug(
                                        f"Resolved dependency {dep_id} -> {resolved_id}"
                                    )
                                    resolved_deps.append(resolved_id)
                                else:
                                    # Dependency doesn't exist on the board - check if it's already a board ID
                                    if dep_id in [t.id for t in tasks]:
                                        # It's a valid board ID, keep it
                                        resolved_deps.append(dep_id)
                                    else:
                                        # Orphaned dependency - skip it
                                        logger.warning(
                                            f"Skipping orphaned dependency '{dep_id}' for task '{task.name}'"
                                        )
                            task.dependencies = resolved_deps

                return tasks

    async def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks from the kanban board regardless of status or assignment.

        Retrieves tasks from all lists on the board, including assigned,
        unassigned, completed, and blocked tasks.

        Returns
        -------
        List[Task]
            List of all tasks on the board

        Raises
        ------
        RuntimeError
            If board_id is not set in configuration

        Examples
        --------
        >>> client = KanbanClient()
        >>> tasks = await client.get_all_tasks()
        >>> print(f"Total tasks on board: {len(tasks)}")

        Notes
        -----
        This method creates a new MCP session for the operation.
        Unlike get_available_tasks(), this includes tasks in all states
        and with any assignment status.
        """
        if not self.board_id:
            raise RuntimeError("Board ID not set")

        # Use the exact same pattern as working scripts
        server_params = StdioServerParameters(
            command="node", args=["../kanban-mcp/dist/index.js"], env=os.environ.copy()
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # First get all lists for the board
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {"action": "get_all", "boardId": self.board_id},
                )

                all_cards = []
                if (
                    lists_result
                    and hasattr(lists_result, "content")
                    and lists_result.content
                ):
                    lists_data = json.loads(lists_result.content[0].text)
                    lists = (
                        lists_data
                        if isinstance(lists_data, list)
                        else lists_data.get("items", [])
                    )

                    # Get cards from each list
                    for lst in lists:
                        list_id = lst.get("id")
                        if list_id:
                            # Get cards for this list
                            cards_result = await session.call_tool(
                                "mcp_kanban_card_manager",
                                {"action": "get_all", "listId": list_id},
                            )

                            if (
                                cards_result
                                and hasattr(cards_result, "content")
                                and cards_result.content
                            ):
                                cards_text = cards_result.content[0].text
                                if cards_text and cards_text.strip():
                                    cards_data = json.loads(cards_text)
                                    cards_list = (
                                        cards_data
                                        if isinstance(cards_data, list)
                                        else cards_data.get("items", [])
                                    )
                                    # Add list name to each card
                                    for card in cards_list:
                                        card["listName"] = lst.get("name", "")
                                        all_cards.append(card)

                tasks = []

                # Convert all cards to tasks (no filtering)
                for card in all_cards:
                    task = self._card_to_task(card)
                    tasks.append(task)

                # Build mapping of original IDs to new IDs
                id_mapping = {}
                for task in tasks:
                    if hasattr(task, "_original_id") and task._original_id:
                        id_mapping[task._original_id] = task.id

                # Resolve dependencies using the mapping
                if id_mapping:
                    logger.debug(
                        f"Resolving dependencies with ID mapping: {id_mapping}"
                    )
                    for task in tasks:
                        if task.dependencies:
                            resolved_deps = []
                            for dep_id in task.dependencies:
                                if dep_id in id_mapping:
                                    # Dependency exists on the board - resolve it
                                    resolved_id = id_mapping[dep_id]
                                    logger.debug(
                                        f"Resolved dependency {dep_id} -> {resolved_id}"
                                    )
                                    resolved_deps.append(resolved_id)
                                else:
                                    # Dependency doesn't exist on the board - check if it's already a board ID
                                    if dep_id in [t.id for t in tasks]:
                                        # It's a valid board ID, keep it
                                        resolved_deps.append(dep_id)
                                    else:
                                        # Orphaned dependency - skip it
                                        logger.warning(
                                            f"Skipping orphaned dependency '{dep_id}' for task '{task.name}'"
                                        )
                            task.dependencies = resolved_deps

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
            command="node", args=["../kanban-mcp/dist/index.js"], env=os.environ.copy()
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
                        "text": f"📋 Task assigned to {agent_id} at {datetime.now().isoformat()}",
                    },
                )

                # Move to In Progress
                # First get lists
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {"action": "get_all", "boardId": self.board_id},
                )

                if lists_result and hasattr(lists_result, "content"):
                    lists_data = json.loads(lists_result.content[0].text)
                    lists = (
                        lists_data
                        if isinstance(lists_data, list)
                        else lists_data.get("items", [])
                    )

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
                                "listId": in_progress_list["id"],
                            },
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
            command="node", args=["../kanban-mcp/dist/index.js"], env=os.environ.copy()
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "mcp_kanban_project_board_manager",
                    {
                        "action": "get_board_summary",
                        "boardId": self.board_id,
                        "includeTaskDetails": False,
                    },
                )

                if result and hasattr(result, "content"):
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
        - assigned_to is extracted from card users/assignment fields
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

        # Extract assignment information
        # Check for assignments in the card data structure
        assigned_to = None

        # Try different possible assignment fields
        if card.get("users"):  # Planka assigns users to cards
            users = card.get("users", [])
            if users and len(users) > 0:
                # Take the first assigned user as the assignee
                assigned_to = (
                    users[0].get("username")
                    or users[0].get("email")
                    or users[0].get("name")
                )
        elif card.get("assignedTo"):  # Alternative field name
            assigned_to = card.get("assignedTo")
        elif card.get("assigned_to"):  # Another alternative
            assigned_to = card.get("assigned_to")

        # Parse dependencies from description if they exist
        description = card.get("description", "")
        dependencies = self._parse_dependencies_from_description(description)
        original_id = self._parse_original_id_from_description(description)

        # Parse labels from the card
        labels = []
        if card.get("labels"):
            for label in card.get("labels", []):
                if isinstance(label, dict) and label.get("name"):
                    labels.append(label["name"])
                elif isinstance(label, str):
                    labels.append(label)

        task = Task(
            id=card.get("id", ""),
            name=task_name,
            description=description,
            status=status,
            priority=Priority.MEDIUM,
            assigned_to=assigned_to,
            created_at=created_at,
            updated_at=updated_at,
            due_date=None,
            estimated_hours=0.0,
            actual_hours=0.0,
            dependencies=dependencies,
            labels=labels,
        )

        # Store original ID as a custom attribute
        if original_id:
            task._original_id = original_id

        return task

    def _parse_dependencies_from_description(self, description: str) -> List[str]:
        """
        Parse task dependencies from the description field.

        Dependencies are stored in the description as:
        🔗 Dependencies: task_id_1, task_id_2, task_id_3

        Parameters
        ----------
        description : str
            Task description that may contain dependencies

        Returns
        -------
        List[str]
            List of task IDs that this task depends on
        """
        if not description:
            return []

        import re

        # Look for the dependencies line
        pattern = r"🔗 Dependencies:\s*([^\n]+)"
        match = re.search(pattern, description)

        if match:
            deps_str = match.group(1)
            # Split by comma and clean up each dependency ID
            dependencies = [dep.strip() for dep in deps_str.split(",") if dep.strip()]
            return dependencies

        return []

    def _parse_original_id_from_description(self, description: str) -> Optional[str]:
        """
        Parse the original task ID from the description field.

        Original ID is stored in the description as:
        🏷️ Original ID: task_get_hello_design

        Parameters
        ----------
        description : str
            Task description that may contain original ID

        Returns
        -------
        Optional[str]
            Original task ID if found, None otherwise
        """
        if not description:
            return None

        import re

        # Look for the original ID line
        pattern = r"🏷️ Original ID:\s*([^\n]+)"
        match = re.search(pattern, description)

        if match:
            return match.group(1).strip()

        return None

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
            command="node", args=["../kanban-mcp/dist/index.js"], env=os.environ.copy()
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                await session.call_tool(
                    "mcp_kanban_comment_manager",
                    {"action": "create", "cardId": task_id, "text": comment_text},
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
            "done": ["done", "completed"],
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
            command="node", args=["../kanban-mcp/dist/index.js"], env=os.environ.copy()
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Get all lists
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {"action": "get_all", "boardId": self.board_id},
                )

                if lists_result and hasattr(lists_result, "content"):
                    lists_data = json.loads(lists_result.content[0].text)
                    lists = (
                        lists_data
                        if isinstance(lists_data, list)
                        else lists_data.get("items", [])
                    )

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
                                "position": 65535,  # Default position at end of list
                            },
                        )
                    else:
                        raise RuntimeError(
                            f"No list found matching keywords: {list_keywords}"
                        )
