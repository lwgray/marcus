"""
Planka implementation of KanbanInterface

Adapts the existing MCP Kanban client to work with the common interface
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.models import Priority, Task, TaskStatus
from src.integrations.kanban_interface import KanbanInterface, KanbanProvider
from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient


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
        self.client = SimpleMCPKanbanClient(config.get('mcp_function_caller'))
        self.project_name = config.get('project_name', 'Task Master Test')
        self.connected = False

    async def connect(self) -> bool:
        """Connect to Planka via MCP"""
        try:
            await self.client.initialize(self.project_name)
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
            if card_data['id'] == task_id:
                return await self.client._card_to_task(card_data)
        return None

    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create new task in Planka"""
        if not self.connected:
            await self.connect()

        # Map to Planka card structure
        card_data = {
            'name': task_data.get('name', 'Untitled Task'),
            'description': task_data.get('description', ''),
            'dueDate': task_data.get('due_date'),
            'position': 65535  # Default position
        }

        # Find backlog list
        lists = await self.client._get_lists()
        backlog_list = None
        for list_data in lists:
            if 'backlog' in list_data['name'].lower():
                backlog_list = list_data
                break

        if not backlog_list:
            raise ValueError("No backlog list found")

        # Create card
        result = await self.client.mcp_call("mcp_kanban_create_card", {
            'listId': backlog_list['id'],
            'name': card_data['name'],
            'description': card_data['description'],
            'position': card_data['position']
        })

        # Convert to Task
        return await self.client._card_to_task(result)

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Task:
        """Update existing task"""
        if not self.connected:
            await self.connect()

        # Check if status is being updated
        if 'status' in updates:
            status = updates['status']
            # Map TaskStatus to column names
            status_to_column = {
                TaskStatus.TODO: 'backlog',
                TaskStatus.IN_PROGRESS: 'in progress',
                TaskStatus.DONE: 'done',
                TaskStatus.BLOCKED: 'blocked'
            }

            # Move to appropriate column if status changed
            if status in status_to_column:
                await self.move_task_to_column(task_id, status_to_column[status])

        # Update card details (if update_task_details exists)
        if hasattr(self.client, 'update_task_details'):
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
        await self.move_task_to_column(task_id, 'in progress')

        return True

    async def move_task_to_column(self, task_id: str, column_name: str) -> bool:
        """Move task to specific column"""
        if not self.connected:
            await self.connect()

        # Map column names to Planka lists
        column_map = {
            'backlog': 'Backlog',
            'ready': 'Ready',
            'in progress': 'In Progress',
            'blocked': 'Blocked',
            'done': 'Done'
        }

        target_list_name = column_map.get(column_name.lower(), column_name)

        # Find target list
        lists = await self.client._get_lists()
        target_list = None
        for list_data in lists:
            if target_list_name.lower() in list_data['name'].lower():
                target_list = list_data
                break

        if not target_list:
            return False

        # Move card
        await self.client.mcp_call("mcp_kanban_move_card", {
            'cardId': task_id,
            'listId': target_list['id'],
            'position': 65535
        })

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

        # Create list name to ID mapping
        list_map = {list_data['name'].lower(): list_data['id'] for list_data in lists}

        metrics = {
            'total_tasks': len(cards),
            'backlog_tasks': 0,
            'in_progress_tasks': 0,
            'completed_tasks': 0,
            'blocked_tasks': 0
        }

        # Count tasks by status
        for card in cards:
            list_id = card.get('listId')
            for list_data in lists:
                if list_data['id'] == list_id:
                    list_name = list_data['name'].lower()
                    if 'backlog' in list_name or 'ready' in list_name:
                        metrics['backlog_tasks'] += 1
                    elif 'progress' in list_name:
                        metrics['in_progress_tasks'] += 1
                    elif 'done' in list_name or 'complete' in list_name:
                        metrics['completed_tasks'] += 1
                    elif 'blocked' in list_name:
                        metrics['blocked_tasks'] += 1
                    break

        return metrics

    async def report_blocker(self, task_id: str, blocker_description: str, severity: str = "medium") -> bool:
        """Report blocker on task"""
        if not self.connected:
            await self.connect()

        # Add blocker as comment and label
        await self.add_comment(task_id, f"🚫 BLOCKER ({severity}): {blocker_description}")

        # Move to blocked column if exists
        await self.move_task_to_column(task_id, "Blocked")

        return True

    async def update_task_progress(self, task_id: str, progress_data: Dict[str, Any]) -> bool:
        """Update task progress"""
        if not self.connected:
            await self.connect()

        # Add progress comment
        progress = progress_data.get('progress', 0)
        status = progress_data.get('status', '')
        message = progress_data.get('message', '')

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
            if status == 'in_progress' and progress < 100:
                await self.move_task_to_column(task_id, "In Progress")
            elif status == 'completed' or progress >= 100:
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
            sorted_items = sorted(checklist_items, key=lambda x: x.get('position', 0))

            # Update checklist items
            for idx, item in enumerate(sorted_items):
                should_be_completed = idx < items_to_complete
                is_completed = item.get('isCompleted', False)

                # Only update if state needs to change
                if should_be_completed != is_completed:
                    await self.client.update_card_task(
                        item['id'],
                        should_be_completed
                    )

        except Exception as e:
            # Log error but don't fail the progress update
            print(f"Warning: Could not update checklist items: {e}")
