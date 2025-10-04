"""
Extended Kanban Client with Create Task Functionality.

This module extends the KanbanClient to add create_task functionality
for creating new tasks on the kanban board.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters
from src.core.models import Priority, Task
from src.integrations.kanban_client import KanbanClient
from src.integrations.label_helper import LabelManagerHelper

logger = logging.getLogger(__name__)


class KanbanClientWithCreate(KanbanClient):
    """
    Extended kanban client that adds create_task functionality.

    This client extends KanbanClient to provide the ability to create
    new tasks on the kanban board, which is required for the natural language
    project creation features.
    """

    def __init__(self) -> None:
        """Initialize the extended kanban client."""
        super().__init__()
        # Ensure Planka credentials are set for label operations
        self._ensure_planka_credentials()

    def _ensure_planka_credentials(self) -> None:
        """Ensure Planka credentials are set in environment."""
        # These should already be set by parent class, but ensure they're available
        if "PLANKA_BASE_URL" not in os.environ:
            os.environ["PLANKA_BASE_URL"] = "http://localhost:3333"
        if "PLANKA_AGENT_EMAIL" not in os.environ:
            os.environ["PLANKA_AGENT_EMAIL"] = "demo@demo.demo"
        if "PLANKA_AGENT_PASSWORD" not in os.environ:
            os.environ["PLANKA_AGENT_PASSWORD"] = "demo"  # nosec B105

    def _build_task_metadata(self, task_data: Dict[str, Any]) -> Optional[str]:
        """
        Build metadata comment for task description.

        This includes priority, estimates, and dependencies formatted
        in a way that can be parsed back out when reading tasks.

        Parameters
        ----------
        task_data : Dict[str, Any]
            Task data dictionary

        Returns
        -------
        Optional[str]
            Formatted metadata comment or None if no metadata
        """
        metadata_parts = []

        # Always include original ID if present
        if task_data.get("original_id"):
            metadata_parts.append(f"🏷️ Original ID: {task_data['original_id']}")

        if task_data.get("estimated_hours"):
            metadata_parts.append(f"⏱️ Estimated: {task_data['estimated_hours']} hours")

        if task_data.get("priority"):
            priority_emoji = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            emoji = priority_emoji.get(task_data["priority"].lower(), "⚪")
            metadata_parts.append(f"{emoji} Priority: {task_data['priority'].upper()}")

        if task_data.get("dependencies"):
            deps = ", ".join(task_data["dependencies"])
            metadata_parts.append(f"🔗 Dependencies: {deps}")

        if metadata_parts:
            header = "📋 Task Metadata (Auto-generated)\n"
            return header + "\n".join(metadata_parts)

        return None

    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """
        Create a new task on the kanban board.

        Parameters
        ----------
        task_data : Dict[str, Any]
            Dictionary containing task information:
            - name: Task title (required)
            - description: Task description
            - priority: Priority level (urgent, high, medium, low)
            - labels: List of labels/tags
            - estimated_hours: Time estimate
            - dependencies: List of task IDs this depends on

        Returns
        -------
        Task
            The created Task object with assigned ID

        Raises
        ------
        RuntimeError
            If board_id is not set or task creation fails

        Examples
        --------
        >>> task_data = {
        ...     "name": "Implement user authentication",
        ...     "description": "Add JWT-based auth to the API",
        ...     "priority": "high",
        ...     "labels": ["backend", "security"],
        ...     "estimated_hours": 16
        ... }
        >>> task = await client.create_task(task_data)
        >>> print(f"Created task: {task.name} with ID: {task.id}")
        """
        if not self.board_id:
            from src.core.error_framework import ConfigurationError, ErrorContext

            raise ConfigurationError(
                "Board ID must be set before creating tasks. "
                "Check your marcus.config.json kanban configuration or ensure "
                "the kanban client is properly initialized with a valid board.",
                context=ErrorContext(
                    operation="create_task",
                    integration_name="kanban_client_with_create",
                    custom_context={
                        "task_name": task_data.get("name", "unknown"),
                        "service_name": "Kanban Client",
                        "config_type": "board configuration",
                        "missing_field": "board_id",
                    },
                ),
            )

        server_params = StdioServerParameters(
            command="node", args=[self.kanban_mcp_path], env=os.environ.copy()
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # First, find the appropriate list to add the task to
                # Default to "Backlog" or "TODO" list
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {"action": "get_all", "boardId": self.board_id},
                )

                target_list = None
                if (
                    lists_result
                    and hasattr(lists_result, "content")
                    and lists_result.content
                ):
                    content_item = lists_result.content[0]
                    if hasattr(content_item, "text"):
                        lists_data = json.loads(content_item.text)
                        lists = (
                            lists_data
                            if isinstance(lists_data, list)
                            else lists_data.get("items", [])
                        )
                    else:
                        lists = []

                    # Look for Backlog or TODO list
                    for lst in lists:
                        list_name_lower = lst.get("name", "").lower()
                        if "backlog" in list_name_lower or "todo" in list_name_lower:
                            target_list = lst
                            break

                    # If no backlog/todo list found, use the first list
                    if not target_list and lists:
                        target_list = lists[0]

                if not target_list:
                    from src.core.error_framework import (
                        ErrorContext,
                        KanbanIntegrationError,
                    )

                    raise KanbanIntegrationError(
                        board_name=str(self.board_id),
                        operation="find_target_list",
                        context=ErrorContext(
                            operation="create_task",
                            integration_name="kanban_client_with_create",
                            custom_context={
                                "board_id": str(self.board_id),
                                "task_name": task_data.get("name", "unknown"),
                                "details": (
                                    f"No suitable list found for new tasks on board "
                                    f"{self.board_id}. Expected a list named 'Backlog' "
                                    f"or 'TODO', or at least one list to exist. Please "
                                    f"check that your kanban "
                                    f"board is properly configured with lists."
                                ),
                            },
                        ),
                    )

                # Prepare card data
                card_name = task_data.get("name", "Untitled Task")
                card_description = task_data.get("description", "")

                # Add metadata (including dependencies) to description
                metadata = self._build_task_metadata(task_data)
                if metadata:
                    if card_description:
                        card_description = f"{card_description}\n\n{metadata}"
                    else:
                        card_description = metadata

                # Create the card
                create_result = await session.call_tool(
                    "mcp_kanban_card_manager",
                    {
                        "action": "create",
                        "listId": target_list["id"],
                        "name": card_name,
                        "description": card_description,
                        "position": 65535,  # Add at end of list
                    },
                )

                if not create_result or not hasattr(create_result, "content"):
                    from src.core.error_framework import (
                        ErrorContext,
                        KanbanIntegrationError,
                    )

                    raise KanbanIntegrationError(
                        board_name=str(self.board_id),
                        operation="create_card",
                        context=ErrorContext(
                            operation="create_task",
                            integration_name="kanban_client_with_create",
                            custom_context={
                                "board_id": str(self.board_id),
                                "task_name": card_name,
                                "list_id": target_list["id"] if target_list else None,
                                "details": (
                                    f"Failed to create card '{card_name}' on board "
                                    f"{self.board_id}. The kanban-mcp server may be "
                                    f"down, the board may not exist, or there may be "
                                    f"issues. Check kanban-mcp server logs."
                                ),
                            },
                        ),
                    )

                # Parse the created card
                content_item = create_result.content[0]
                if hasattr(content_item, "text"):
                    created_card_data = json.loads(content_item.text)
                else:
                    created_card_data = {}
                created_card = (
                    created_card_data
                    if isinstance(created_card_data, dict)
                    else created_card_data.get("item", {})
                )

                # Add labels if provided
                if task_data.get("labels"):
                    await self._add_labels_to_card(
                        session, created_card["id"], task_data["labels"]
                    )

                # Add subtasks/acceptance criteria if provided
                if task_data.get("acceptance_criteria") or task_data.get("subtasks"):
                    checklist_items = []

                    # Add acceptance criteria as checklist items
                    if task_data.get("acceptance_criteria"):
                        logger.debug(
                            f"Found {len(task_data['acceptance_criteria'])} acceptance "
                            f"criteria for task '{card_name}'"
                        )
                        for criteria in task_data["acceptance_criteria"]:
                            checklist_items.append(f"✓ {criteria}")

                    # Add subtasks as checklist items
                    if task_data.get("subtasks"):
                        logger.debug(
                            f"Found {len(task_data['subtasks'])} subtasks for task "
                            f"'{card_name}'"
                        )
                        for subtask in task_data["subtasks"]:
                            checklist_items.append(f"• {subtask}")

                    if checklist_items:
                        logger.debug(
                            f"Adding {len(checklist_items)} checklist items to card"
                        )
                        await self._add_checklist_items(
                            session, created_card["id"], checklist_items
                        )

                # Add initial comment with task metadata
                metadata_comment = self._build_metadata_comment(task_data)
                if metadata_comment:
                    await session.call_tool(
                        "mcp_kanban_comment_manager",
                        {
                            "action": "create",
                            "cardId": created_card["id"],
                            "text": metadata_comment,
                        },
                    )

                # Convert the created card to a Task object
                created_card["listName"] = target_list.get("name", "")
                task = self._card_to_task(created_card)

                # Override with provided data
                if "priority" in task_data:
                    task.priority = self._parse_priority(task_data["priority"])
                if "estimated_hours" in task_data:
                    task.estimated_hours = float(task_data["estimated_hours"])
                if "labels" in task_data:
                    task.labels = task_data["labels"]
                if "dependencies" in task_data:
                    task.dependencies = task_data["dependencies"]

                return task

    def _parse_priority(self, priority_str: str) -> Priority:
        """
        Parse priority string to Priority enum.

        Parameters
        ----------
        priority_str : str
            Priority string (urgent, high, medium, low)

        Returns
        -------
        Priority
            Corresponding Priority enum value
        """
        priority_map = {
            "urgent": Priority.URGENT,
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW,
        }
        return priority_map.get(priority_str.lower(), Priority.MEDIUM)

    def _build_metadata_comment(self, task_data: Dict[str, Any]) -> Optional[str]:
        """
        Build a metadata comment for the task.

        Parameters
        ----------
        task_data : Dict[str, Any]
            Task data containing metadata

        Returns
        -------
        Optional[str]
            Formatted metadata comment or None if no metadata
        """
        metadata_parts = []

        if task_data.get("estimated_hours"):
            metadata_parts.append(f"⏱️ Estimated: {task_data['estimated_hours']} hours")

        if task_data.get("priority"):
            priority_emoji = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            emoji = priority_emoji.get(task_data["priority"].lower(), "⚪")
            metadata_parts.append(f"{emoji} Priority: {task_data['priority'].upper()}")

        if task_data.get("dependencies"):
            deps = ", ".join(task_data["dependencies"])
            metadata_parts.append(f"🔗 Dependencies: {deps}")

        if metadata_parts:
            header = "📋 Task Metadata (Auto-generated)\n"
            return header + "\n".join(metadata_parts)

        return None

    async def _add_labels_to_card(
        self, session: Any, card_id: str, labels: List[str]
    ) -> None:
        """
        Add labels to a card, creating them if necessary.

        Parameters
        ----------
        session : Any
            MCP client session
        card_id : str
            ID of the card to add labels to
        labels : List[str]
            List of label names to add
        """
        try:
            # Ensure board_id is not None for label operations
            if not self.board_id:
                logger.error("board_id is required for label operations")
                return

            # Use the label manager helper for simplified label management
            label_helper = LabelManagerHelper(session, self.board_id)

            # Add all labels to the card
            # The helper will handle checking if they exist, creating them if needed,
            # and adding them to the card
            added_ids = await label_helper.add_labels_to_card(card_id, labels)

            if added_ids:
                logger.info(f"Successfully added {len(added_ids)} labels to card")

        except Exception as e:
            logger.error(f"Error in _add_labels_to_card: {e}")
            # Don't fail task creation if labels fail

    async def _add_checklist_items(
        self, session: Any, card_id: str, items: List[str]
    ) -> None:
        """
        Add checklist items (subtasks/acceptance criteria) to a card.

        Parameters
        ----------
        session : Any
            MCP client session
        card_id : str
            ID of the card to add items to
        items : List[str]
            List of checklist item names
        """
        try:
            position = 65536
            for item in items:
                try:
                    result = await session.call_tool(
                        "mcp_kanban_task_manager",
                        {
                            "action": "create",
                            "cardId": card_id,
                            "name": item,
                            "position": position,
                        },
                    )
                    if result and hasattr(result, "content"):
                        logger.debug(
                            f"Created checklist item '{item[:30]}...' - "
                            f"response has content"
                        )
                    else:
                        logger.debug(
                            f"Created checklist item '{item[:30]}...' - "
                            f"no response content"
                        )
                    position += 65536
                except Exception as e:
                    logger.error(f"Failed to create checklist item '{item}': {e}")

        except Exception as e:
            logger.error(f"Error in _add_checklist_items: {e}")
            # Don't fail task creation if checklist fails

    async def create_tasks_batch(self, tasks_data: list[Dict[str, Any]]) -> list[Task]:
        """
        Create multiple tasks in batch.

        Parameters
        ----------
        tasks_data : list[Dict[str, Any]]
            List of task data dictionaries

        Returns
        -------
        list[Task]
            List of created Task objects

        Notes
        -----
        This method creates tasks sequentially to maintain order and
        handle dependencies properly.
        """
        created_tasks = []

        for task_data in tasks_data:
            try:
                task = await self.create_task(task_data)
                created_tasks.append(task)
            except Exception as e:
                logger.error(
                    f"Failed to create task '{task_data.get('name', 'Unknown')}': "
                    f"{str(e)}"
                )
                # Continue with other tasks even if one fails
                continue

        return created_tasks
