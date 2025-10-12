"""
Planka implementation of KanbanInterface.

Adapts the existing MCP Kanban client to work with the common interface.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from mcp import ClientSession, StdioServerParameters
from src.core.models import Task, TaskStatus
from src.integrations.kanban_client import KanbanClient
from src.integrations.kanban_interface import KanbanInterface, KanbanProvider

logger = logging.getLogger(__name__)


def _extract_text_content(result: Any) -> Optional[str]:
    """
    Safely extract text content from MCP result.

    Parameters
    ----------
    result : Any
        The MCP result object to extract text from.

    Returns
    -------
    Optional[str]
        Extracted text content, or None if not available.
    """
    if not result or not hasattr(result, "content") or not result.content:
        return None

    content = result.content[0]
    if isinstance(content, TextContent):
        return str(content.text) if content.text is not None else None
    return None


class PlankaKanban(KanbanInterface):  # type: ignore[misc]
    """Planka kanban board implementation."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Planka connection.

        Parameters
        ----------
        config : Dict[str, Any]
            Dictionary containing:
                - project_name: Name of the project in Planka
        """
        super().__init__(config)
        self.provider = KanbanProvider.PLANKA
        self.client = KanbanClient()
        self.project_name = config.get("project_name", "Task Master Test")
        self.connected = False

        # Store server parameters for MCP calls
        # Use local path for kanban-mcp
        kanban_mcp_path = os.path.expanduser("~/dev/kanban-mcp/dist/index.js")
        self._server_params = StdioServerParameters(
            command="node",
            args=[kanban_mcp_path],
            env=os.environ.copy(),
        )

    async def connect(self) -> bool:
        """
        Connect to Planka via MCP.

        Returns
        -------
        bool
            True if connection successful, raises exception otherwise.
        """
        try:
            # Test connection by trying to get board summary
            summary = await self.client.get_board_summary()
            self.connected = bool(summary)
            return self.connected
        except Exception as e:
            logger.error(f"Failed to connect to Planka: {e}")
            # Re-raise the exception so it propagates up
            raise

    async def disconnect(self) -> None:
        """Disconnect from Planka."""
        self.connected = False

    async def get_available_tasks(self) -> List[Task]:
        """
        Get unassigned tasks from backlog.

        Returns
        -------
        List[Task]
            List of available tasks from the backlog.
        """
        if not self.connected:
            await self.connect()

        tasks = await self.client.get_available_tasks()
        return tasks  # type: ignore[no-any-return]

    async def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks from the board.

        Returns
        -------
        List[Task]
            List of all tasks on the board.
        """
        if not self.connected:
            await self.connect()

        tasks = await self.client.get_all_tasks()
        return tasks  # type: ignore[no-any-return]

    async def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        Get specific task by ID.

        Parameters
        ----------
        task_id : str
            The ID of the task to retrieve.

        Returns
        -------
        Optional[Task]
            The task if found, None otherwise.
        """
        if not self.connected:
            await self.connect()

        # Get all tasks and find the one with matching ID
        all_tasks = await self.client.get_all_tasks()
        for task in all_tasks:
            if task.id == task_id:
                return task
        return None

    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """
        Create new task in Planka.

        Parameters
        ----------
        task_data : Dict[str, Any]
            Dictionary containing task data (name, description, due_date).

        Returns
        -------
        Task
            The newly created task object.
        """
        if not self.connected:
            await self.connect()

        # Map to Planka card structure
        card_data = {
            "name": task_data.get("name", "Untitled Task"),
            "description": task_data.get("description", ""),
            "dueDate": task_data.get("due_date"),
            "position": 65535,  # Default position
        }

        # Determine target list based on status
        status = task_data.get("status")
        target_list_name = "backlog"  # Default to backlog for TODO status

        # Map TaskStatus enum to list names
        if isinstance(status, TaskStatus):
            status_to_list = {
                TaskStatus.TODO: "backlog",
                TaskStatus.IN_PROGRESS: "in progress",
                TaskStatus.DONE: "done",
                TaskStatus.BLOCKED: "blocked",
            }
            target_list_name = status_to_list.get(status, "backlog")
        elif isinstance(status, str):
            # Handle string status values
            status_lower = status.lower()
            if status_lower in ["done", "completed"]:
                target_list_name = "done"
            elif status_lower in ["in_progress", "in progress", "active"]:
                target_list_name = "in progress"
            elif status_lower in ["blocked", "on hold"]:
                target_list_name = "blocked"

        # Find target list and create card using direct MCP call
        async with stdio_client(self._server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Get lists for the board
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {"action": "get_all", "boardId": self.client.board_id},
                )

                lists_text = _extract_text_content(lists_result)
                if not lists_text:
                    raise ValueError("Could not get board lists")

                lists_data = json.loads(lists_text)
                lists = (
                    lists_data
                    if isinstance(lists_data, list)
                    else lists_data.get("items", [])
                )

                # Find target list
                target_list = None
                for list_data in lists:
                    if target_list_name.lower() in list_data["name"].lower():
                        target_list = list_data
                        break

                if not target_list:
                    # Fallback to backlog if target list not found
                    logger.warning(
                        f"Could not find list '{target_list_name}', "
                        "falling back to backlog"
                    )
                    for list_data in lists:
                        if "backlog" in list_data["name"].lower():
                            target_list = list_data
                            break

                if not target_list:
                    raise ValueError(
                        f"No suitable list found "
                        f"(tried '{target_list_name}' and 'backlog')"
                    )

                # Create card
                result = await session.call_tool(
                    "mcp_kanban_create_card",
                    {
                        "listId": target_list["id"],
                        "name": card_data["name"],
                        "description": card_data["description"],
                        "position": card_data["position"],
                    },
                )

                result_text = _extract_text_content(result)
                if not result_text:
                    raise ValueError("Failed to create card")

                card_result = json.loads(result_text)

                # Convert to Task using the client's method
                return self.client._card_to_task(card_result)

    async def update_task(
        self, task_id: str, updates: Dict[str, Any]
    ) -> Optional[Task]:
        """
        Update existing task.

        Parameters
        ----------
        task_id : str
            The ID of the task to update.
        updates : Dict[str, Any]
            Dictionary containing fields to update.

        Returns
        -------
        Optional[Task]
            The updated task object.
        """
        if not self.connected:
            await self.connect()

        # Debug logging
        logger.info(f"update_task called with task_id={task_id}, " f"updates={updates}")

        # Check if status is being updated
        if "status" in updates:
            status = updates["status"]
            logger.info(f"Status update requested: {status} (type: {type(status)})")

            # Map TaskStatus to column names
            status_to_column = {
                TaskStatus.TODO: "backlog",
                TaskStatus.IN_PROGRESS: "in progress",
                TaskStatus.DONE: "done",
                TaskStatus.BLOCKED: "blocked",
            }

            # Move to appropriate column if status changed
            if status in status_to_column:
                logger.info(f"Moving task to column: {status_to_column[status]}")
                await self.move_task_to_column(task_id, status_to_column[status])
            else:
                logger.warning(
                    f"Status {status} not found in status_to_column " f"mapping"
                )

        # Update card details using direct MCP calls for other fields
        if any(key in updates for key in ["name", "description", "due_date"]):
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    update_data = {"id": task_id}
                    if "name" in updates:
                        update_data["name"] = updates["name"]
                    if "description" in updates:
                        update_data["description"] = updates["description"]
                    if "due_date" in updates:
                        update_data["dueDate"] = updates["due_date"]

                    await session.call_tool("mcp_kanban_update_card", update_data)

        # Get updated task
        updated_task = await self.get_task_by_id(task_id)
        if updated_task is None:
            raise ValueError(f"Task {task_id} not found after update")
        return updated_task

    async def assign_task(self, task_id: str, assignee_id: str) -> bool:
        """
        Assign task to worker.

        Parameters
        ----------
        task_id : str
            The ID of the task to assign.
        assignee_id : str
            The ID of the worker to assign the task to.

        Returns
        -------
        bool
            True if assignment successful.
        """
        if not self.connected:
            await self.connect()

        # Use the client's assign_task method which handles both
        # comment and move
        await self.client.assign_task(task_id, assignee_id)
        return True

    async def move_task_to_column(self, task_id: str, column_name: str) -> bool:
        """
        Move task to specific column.

        Parameters
        ----------
        task_id : str
            The ID of the task to move.
        column_name : str
            The name of the target column.

        Returns
        -------
        bool
            True if move successful.
        """
        if not self.connected:
            await self.connect()

        # Map column names to Planka lists
        # For blocked status, support both "On Hold" and "Blocked"
        column_map = {
            "backlog": "Backlog",
            "ready": "Ready",
            "in progress": "In Progress",
            "blocked": ["On Hold", "Blocked"],  # Try On Hold first, then Blocked
            "done": "Done",
        }

        target_list_names = column_map.get(column_name.lower(), column_name)
        # Convert to list if it's a single string
        if isinstance(target_list_names, str):
            target_list_names = [target_list_names]

        # Find target list using MCP call
        async with stdio_client(self._server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {"action": "get_all", "boardId": self.client.board_id},
                )

                lists_text = _extract_text_content(lists_result)
                if not lists_text:
                    return False

                lists_data = json.loads(lists_text)
                lists = (
                    lists_data
                    if isinstance(lists_data, list)
                    else lists_data.get("items", [])
                )

                # Debug logging
                logger.info(
                    f"Looking for list: {target_list_names} "
                    f"(from column_name: '{column_name}')"
                )
                logger.info(f"Available lists: {[lst['name'] for lst in lists]}")

                target_list = None
                # Try each possible list name in order
                for target_list_name in target_list_names:
                    for list_data in lists:
                        if target_list_name.lower() in list_data["name"].lower():
                            target_list = list_data
                            break
                    if target_list:
                        break

                if not target_list:
                    logger.error(
                        f"Could not find list matching any of {target_list_names}"
                    )
                    return False

                # Move card
                move_result = await session.call_tool(
                    "mcp_kanban_card_manager",
                    {
                        "action": "move",
                        "id": task_id,
                        "listId": target_list["id"],
                        "position": 65535,
                    },
                )

                return bool(move_result)

    async def add_comment(self, task_id: str, comment: str) -> bool:
        """
        Add comment to task.

        Parameters
        ----------
        task_id : str
            The ID of the task to comment on.
        comment : str
            The comment text to add.

        Returns
        -------
        bool
            True if comment added successfully.
        """
        if not self.connected:
            await self.connect()

        try:
            await self.client.add_comment(task_id, comment)
            return True
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            return False

    async def get_project_metrics(self) -> Dict[str, Any]:
        """
        Get project metrics.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing task counts by status.
        """
        if not self.connected:
            await self.connect()

        # Get all tasks using client methods
        all_tasks = await self.client.get_all_tasks()

        metrics = {
            "total_tasks": len(all_tasks),
            "backlog_tasks": 0,
            "in_progress_tasks": 0,
            "completed_tasks": 0,
            "blocked_tasks": 0,
        }

        # Count tasks by status using Task.status directly
        for task in all_tasks:
            if task.status == TaskStatus.TODO:
                metrics["backlog_tasks"] += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                metrics["in_progress_tasks"] += 1
            elif task.status == TaskStatus.DONE:
                metrics["completed_tasks"] += 1
            elif task.status == TaskStatus.BLOCKED:
                metrics["blocked_tasks"] += 1

        return metrics

    async def report_blocker(
        self, task_id: str, blocker_description: str, severity: str = "medium"
    ) -> bool:
        """
        Report blocker on task.

        Parameters
        ----------
        task_id : str
            The ID of the task to report blocker for.
        blocker_description : str
            Description of the blocker.
        severity : str, optional
            Severity level (default is "medium").

        Returns
        -------
        bool
            True if blocker reported successfully.
        """
        if not self.connected:
            await self.connect()

        # Add blocker as comment and label
        await self.add_comment(
            task_id, f"🚫 BLOCKER ({severity}): {blocker_description}"
        )

        # Move to blocked column if exists
        await self.move_task_to_column(task_id, "Blocked")

        return True

    async def update_task_progress(
        self, task_id: str, progress_data: Dict[str, Any]
    ) -> bool:
        """
        Update task progress.

        Parameters
        ----------
        task_id : str
            The ID of the task to update progress for.
        progress_data : Dict[str, Any]
            Dictionary containing progress, status, and message.

        Returns
        -------
        bool
            True if progress updated successfully.
        """
        if not self.connected:
            await self.connect()

        # Add progress comment
        progress = progress_data.get("progress", 0)
        status = progress_data.get("status", "")
        message = progress_data.get("message", "")

        comment = f"📊 Progress Update: {progress}%"
        if status:
            comment += f" | Status: {status}"
        if message:
            comment += f" | {message}"

        await self.add_comment(task_id, comment)

        # Update checklist items based on progress
        await self._update_checklist_progress(task_id, progress)

        # Move to appropriate column based on status
        if status:
            if status == "in_progress" and progress < 100:
                await self.move_task_to_column(task_id, "In Progress")
            elif status == "completed" or progress >= 100:
                await self.move_task_to_column(task_id, "Done")

        return True

    async def _update_checklist_progress(self, task_id: str, progress: int) -> None:
        """
        Update checklist items based on progress percentage.

        Parameters
        ----------
        task_id : str
            The ID of the task to update checklist for.
        progress : int
            The progress percentage (0-100).
        """
        try:
            # Use MCP to get and update checklist items
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # Get card tasks (checklist items)
                    tasks_result = await session.call_tool(
                        "mcp_kanban_task_manager",
                        {"action": "get_all", "cardId": task_id},
                    )

                    tasks_text = _extract_text_content(tasks_result)
                    if not tasks_text:
                        return

                    checklist_data = json.loads(tasks_text)
                    checklist_items = (
                        checklist_data
                        if isinstance(checklist_data, list)
                        else checklist_data.get("items", [])
                    )

                    if not checklist_items:
                        return

                    # Calculate how many items should be completed based on progress
                    total_items = len(checklist_items)
                    items_to_complete = int((progress / 100) * total_items)

                    # Sort items by position to maintain order
                    sorted_items = sorted(
                        checklist_items, key=lambda x: x.get("position", 0)
                    )

                    # Update checklist items
                    for idx, item in enumerate(sorted_items):
                        should_be_completed = idx < items_to_complete
                        is_completed = item.get("isCompleted", False)

                        # Only update if state needs to change
                        if should_be_completed != is_completed:
                            await session.call_tool(
                                "mcp_kanban_task_manager",
                                {
                                    "action": "update",
                                    "id": item["id"],
                                    "isCompleted": should_be_completed,
                                },
                            )

        except Exception as e:
            # Log error but don't fail the progress update
            logger.warning(f"Could not update checklist items: {e}")

    # Attachment methods implementation for Planka

    async def upload_attachment(
        self,
        task_id: str,
        filename: str,
        content: Union[str, bytes],
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload an attachment to a Planka card.

        Uses the kanban-mcp attachment manager to upload files.

        Parameters
        ----------
        task_id : str
            The ID of the task to attach the file to.
        filename : str
            Name of the file to upload.
        content : Union[str, bytes]
            The file content (string or bytes).
        content_type : Optional[str], optional
            MIME type of the content.

        Returns
        -------
        Dict[str, Any]
            Result dictionary with success status and attachment data.
        """
        if not self.connected:
            await self.connect()

        try:
            # If content is bytes, convert to base64
            if isinstance(content, bytes):
                import base64

                content = base64.b64encode(content).decode()

            # Call the MCP attachment manager
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    attachment_result = await session.call_tool(
                        "mcp_kanban_attachment_manager",
                        {
                            "action": "upload",
                            "cardId": task_id,
                            "filename": filename,
                            "content": content,
                            "contentType": content_type,
                        },
                    )

                    result_text = _extract_text_content(attachment_result)
                    result = json.loads(result_text) if result_text else None

            if result:
                return {
                    "success": True,
                    "data": {
                        "id": result.get("id"),
                        "filename": result.get("filename", filename),
                        "url": result.get("url"),
                        "size": (len(content) if isinstance(content, str) else 0),
                    },
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to upload attachment",
                }

        except Exception as e:
            logger.error(f"Error uploading attachment: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to upload attachment: {str(e)}",
            }

    async def get_attachments(self, task_id: str) -> Dict[str, Any]:
        """
        Get all attachments for a Planka card.

        Parameters
        ----------
        task_id : str
            The ID of the task to get attachments for.

        Returns
        -------
        Dict[str, Any]
            Result dictionary with success status and attachments list.
        """
        if not self.connected:
            await self.connect()

        try:
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    attachment_result = await session.call_tool(
                        "mcp_kanban_attachment_manager",
                        {
                            "action": "get_all",
                            "cardId": task_id,
                        },
                    )

                    result_text = _extract_text_content(attachment_result)
                    result = json.loads(result_text) if result_text else None

            if isinstance(result, list):
                # Format attachments
                attachments = []
                for att in result:
                    attachments.append(
                        {
                            "id": att.get("id"),
                            "filename": att.get("name"),
                            "url": att.get("url"),
                            "created_at": att.get("createdAt"),
                            "created_by": att.get("userId"),
                        }
                    )

                return {"success": True, "data": attachments}
            else:
                return {"success": True, "data": []}

        except Exception as e:
            logger.error(f"Error getting attachments: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get attachments: {str(e)}",
            }

    async def download_attachment(
        self, attachment_id: str, filename: str, task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Download an attachment from Planka.

        Parameters
        ----------
        attachment_id : str
            The ID of the attachment to download.
        filename : str
            The filename to use for the downloaded attachment.
        task_id : Optional[str], optional
            The task ID (not used for Planka).

        Returns
        -------
        Dict[str, Any]
            Result dictionary with success status and attachment content.
        """
        if not self.connected:
            await self.connect()

        try:
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    attachment_result = await session.call_tool(
                        "mcp_kanban_attachment_manager",
                        {
                            "action": "download",
                            "id": attachment_id,
                            "filename": filename,
                        },
                    )

                    result_text = _extract_text_content(attachment_result)
                    result = json.loads(result_text) if result_text else None

            if result and result.get("content"):
                return {
                    "success": True,
                    "data": {
                        "content": result.get("content"),
                        "filename": result.get("filename", filename),
                        "content_type": None,  # Planka doesn't provide this
                    },
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to download attachment",
                }

        except Exception as e:
            logger.error(f"Error downloading attachment: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to download attachment: {str(e)}",
            }

    async def delete_attachment(
        self, attachment_id: str, task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete an attachment from Planka.

        Parameters
        ----------
        attachment_id : str
            The ID of the attachment to delete.
        task_id : Optional[str], optional
            The task ID (not used for Planka).

        Returns
        -------
        Dict[str, Any]
            Result dictionary with success status.
        """
        if not self.connected:
            await self.connect()

        try:
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    attachment_result = await session.call_tool(
                        "mcp_kanban_attachment_manager",
                        {
                            "action": "delete",
                            "id": attachment_id,
                        },
                    )

                    result_text = _extract_text_content(attachment_result)
                    result = json.loads(result_text) if result_text else None

            return {
                "success": result.get("success", False) if result else False,
                "error": (
                    result.get("error")
                    if result and not result.get("success")
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Error deleting attachment: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to delete attachment: {str(e)}",
            }

    async def update_attachment(
        self,
        attachment_id: str,
        filename: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update attachment metadata in Planka.

        Parameters
        ----------
        attachment_id : str
            The ID of the attachment to update.
        filename : Optional[str], optional
            New filename for the attachment.
        task_id : Optional[str], optional
            The task ID (not used for Planka).

        Returns
        -------
        Dict[str, Any]
            Result dictionary with success status and updated data.
        """
        if not self.connected:
            await self.connect()

        if not filename:
            return {
                "success": False,
                "error": "Filename is required for Planka attachment updates",
            }

        try:
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    attachment_result = await session.call_tool(
                        "mcp_kanban_attachment_manager",
                        {
                            "action": "update",
                            "id": attachment_id,
                            "name": filename,
                        },
                    )

                    result_text = _extract_text_content(attachment_result)
                    result = json.loads(result_text) if result_text else None

            if result:
                return {
                    "success": True,
                    "data": {
                        "id": result.get("id"),
                        "filename": result.get("name", filename),
                        "url": result.get("url"),
                    },
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update attachment",
                }

        except Exception as e:
            logger.error(f"Error updating attachment: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to update attachment: {str(e)}",
            }
