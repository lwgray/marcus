"""
Planka implementation of KanbanInterface

Adapts the existing MCP Kanban client to work with the common interface
"""

import logging
from typing import Any, Dict, List, Optional, Union

from src.core.models import Task, TaskStatus
from src.integrations.kanban_client import KanbanClient
from src.integrations.kanban_interface import KanbanInterface, KanbanProvider

logger = logging.getLogger(__name__)


class PlankaKanban(KanbanInterface):
    """Planka kanban board implementation"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Planka connection

        Args:
            config: Dictionary containing:
                - project_name: Name of the project in Planka
                - mcp_function_caller: Function to call MCP tools
        """
        super().__init__(config)
        self.provider = KanbanProvider.PLANKA
        self.client = KanbanClient(config.get("mcp_function_caller"))
        self.project_name = config.get("project_name", "Task Master Test")
        self.connected = False

    async def connect(self) -> bool:
        """Connect to Planka via MCP"""
        try:
            await self.client.initialize(self.project_name)
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Planka: {e}")
            # Re-raise the exception so it propagates up
            raise

    async def disconnect(self):
        """Disconnect from Planka"""
        self.connected = False

    async def get_available_tasks(self) -> List[Task]:
        """Get unassigned tasks from backlog"""
        if not self.connected:
            await self.connect()

        tasks = await self.client.get_available_tasks()
        return tasks

    async def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get specific task by ID"""
        if not self.connected:
            await self.connect()

        cards = await self.client._get_cards()
        for card_data in cards:
            if card_data["id"] == task_id:
                return await self.client._card_to_task(card_data)
        return None

    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create new task in Planka"""
        if not self.connected:
            await self.connect()

        # Map to Planka card structure
        card_data = {
            "name": task_data.get("name", "Untitled Task"),
            "description": task_data.get("description", ""),
            "dueDate": task_data.get("due_date"),
            "position": 65535,  # Default position
        }

        # Find backlog list
        lists = await self.client._get_lists()
        backlog_list = None
        for list_data in lists:
            if "backlog" in list_data["name"].lower():
                backlog_list = list_data
                break

        if not backlog_list:
            raise ValueError("No backlog list found")

        # Create card
        result = await self.client.mcp_call(
            "mcp_kanban_create_card",
            {
                "listId": backlog_list["id"],
                "name": card_data["name"],
                "description": card_data["description"],
                "position": card_data["position"],
            },
        )

        # Convert to Task
        return await self.client._card_to_task(result)

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Task:
        """Update existing task"""
        if not self.connected:
            await self.connect()

        # Debug logging
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"update_task called with task_id={task_id}, updates={updates}")

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
                logger.warning(f"Status {status} not found in status_to_column mapping")

        # Update card details (if update_task_details exists)
        if hasattr(self.client, "update_task_details"):
            await self.client.update_task_details(task_id, updates)

        # Get updated task
        return await self.get_task_by_id(task_id)

    async def assign_task(self, task_id: str, assignee_id: str) -> bool:
        """Assign task to worker"""
        if not self.connected:
            await self.connect()

        # Add assignment comment
        await self.client.assign_task(task_id, assignee_id)

        # Move to In Progress column
        await self.move_task_to_column(task_id, "in progress")

        return True

    async def move_task_to_column(self, task_id: str, column_name: str) -> bool:
        """Move task to specific column"""
        if not self.connected:
            await self.connect()

        # Map column names to Planka lists
        column_map = {
            "backlog": "Backlog",
            "ready": "Ready",
            "in progress": "In Progress",
            "blocked": "Blocked",
            "done": "Done",
        }

        target_list_name = column_map.get(column_name.lower(), column_name)

        # Find target list
        lists = await self.client._get_lists()

        # Debug logging
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            f"Looking for list: '{target_list_name}' (from column_name: '{column_name}')"
        )
        logger.info(f"Available lists: {[lst['name'] for lst in lists]}")

        target_list = None
        for list_data in lists:
            if target_list_name.lower() in list_data["name"].lower():
                target_list = list_data
                break

        if not target_list:
            logger.error(f"Could not find list matching '{target_list_name}'")
            return False

        # Move card
        await self.client.mcp_call(
            "mcp_kanban_move_card",
            {"cardId": task_id, "listId": target_list["id"], "position": 65535},
        )

        return True

    async def add_comment(self, task_id: str, comment: str) -> bool:
        """Add comment to task"""
        if not self.connected:
            await self.connect()

        return await self.client.add_comment(task_id, comment)

    async def get_project_metrics(self) -> Dict[str, Any]:
        """Get project metrics"""
        if not self.connected:
            await self.connect()

        cards = await self.client._get_cards()
        lists = await self.client._get_lists()

        # Create list name to ID mapping (removed - not used)

        metrics = {
            "total_tasks": len(cards),
            "backlog_tasks": 0,
            "in_progress_tasks": 0,
            "completed_tasks": 0,
            "blocked_tasks": 0,
        }

        # Count tasks by status
        for card in cards:
            list_id = card.get("listId")
            for list_data in lists:
                if list_data["id"] == list_id:
                    list_name = list_data["name"].lower()
                    if "backlog" in list_name or "ready" in list_name:
                        metrics["backlog_tasks"] += 1
                    elif "progress" in list_name:
                        metrics["in_progress_tasks"] += 1
                    elif "done" in list_name or "complete" in list_name:
                        metrics["completed_tasks"] += 1
                    elif "blocked" in list_name:
                        metrics["blocked_tasks"] += 1
                    break

        return metrics

    async def report_blocker(
        self, task_id: str, blocker_description: str, severity: str = "medium"
    ) -> bool:
        """Report blocker on task"""
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
        """Update task progress"""
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
        """Update checklist items based on progress percentage"""
        try:
            # Get all checklist items for the card
            checklist_items = await self.client.get_card_tasks(task_id)

            if not checklist_items:
                return

            # Calculate how many items should be completed based on progress
            total_items = len(checklist_items)
            items_to_complete = int((progress / 100) * total_items)

            # Sort items by position to maintain order
            sorted_items = sorted(checklist_items, key=lambda x: x.get("position", 0))

            # Update checklist items
            for idx, item in enumerate(sorted_items):
                should_be_completed = idx < items_to_complete
                is_completed = item.get("isCompleted", False)

                # Only update if state needs to change
                if should_be_completed != is_completed:
                    await self.client.update_card_task(item["id"], should_be_completed)

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
        """
        if not self.connected:
            await self.connect()

        try:
            # If content is bytes, convert to base64
            if isinstance(content, bytes):
                import base64

                content = base64.b64encode(content).decode()

            # Call the MCP attachment manager
            result = await self.client.mcp_call(
                "mcp_kanban_attachment_manager",
                {
                    "action": "upload",
                    "cardId": task_id,
                    "filename": filename,
                    "content": content,
                    "contentType": content_type,
                },
            )

            if result:
                return {
                    "success": True,
                    "data": {
                        "id": result.get("id"),
                        "filename": result.get("filename", filename),
                        "url": result.get("url"),
                        "size": len(content) if isinstance(content, str) else 0,
                    },
                }
            else:
                return {"success": False, "error": "Failed to upload attachment"}

        except Exception as e:
            logger.error(f"Error uploading attachment: {str(e)}")
            return {"success": False, "error": f"Failed to upload attachment: {str(e)}"}

    async def get_attachments(self, task_id: str) -> Dict[str, Any]:
        """Get all attachments for a Planka card."""
        if not self.connected:
            await self.connect()

        try:
            result = await self.client.mcp_call(
                "mcp_kanban_attachment_manager",
                {
                    "action": "get_all",
                    "cardId": task_id,
                },
            )

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
            return {"success": False, "error": f"Failed to get attachments: {str(e)}"}

    async def download_attachment(
        self, attachment_id: str, filename: str, task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Download an attachment from Planka."""
        if not self.connected:
            await self.connect()

        try:
            result = await self.client.mcp_call(
                "mcp_kanban_attachment_manager",
                {
                    "action": "download",
                    "id": attachment_id,
                    "filename": filename,
                },
            )

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
                return {"success": False, "error": "Failed to download attachment"}

        except Exception as e:
            logger.error(f"Error downloading attachment: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to download attachment: {str(e)}",
            }

    async def delete_attachment(
        self, attachment_id: str, task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete an attachment from Planka."""
        if not self.connected:
            await self.connect()

        try:
            result = await self.client.mcp_call(
                "mcp_kanban_attachment_manager",
                {
                    "action": "delete",
                    "id": attachment_id,
                },
            )

            return {
                "success": result.get("success", False),
                "error": result.get("error") if not result.get("success") else None,
            }

        except Exception as e:
            logger.error(f"Error deleting attachment: {str(e)}")
            return {"success": False, "error": f"Failed to delete attachment: {str(e)}"}

    async def update_attachment(
        self,
        attachment_id: str,
        filename: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update attachment metadata in Planka."""
        if not self.connected:
            await self.connect()

        if not filename:
            return {
                "success": False,
                "error": "Filename is required for Planka attachment updates",
            }

        try:
            result = await self.client.mcp_call(
                "mcp_kanban_attachment_manager",
                {
                    "action": "update",
                    "id": attachment_id,
                    "name": filename,
                },
            )

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
                return {"success": False, "error": "Failed to update attachment"}

        except Exception as e:
            logger.error(f"Error updating attachment: {str(e)}")
            return {"success": False, "error": f"Failed to update attachment: {str(e)}"}
