"""
Subtask Assignment Logic for Marcus.

This module handles finding and assigning subtasks to agents,
integrating with the existing task assignment workflow.
"""

import logging
from typing import Any, List, Optional

from src.core.models import Task, TaskStatus
from src.marcus_mcp.coordinator.subtask_manager import Subtask, SubtaskManager

logger = logging.getLogger(__name__)


def find_next_available_subtask(
    agent_id: str,
    project_tasks: List[Task],
    subtask_manager: SubtaskManager,
    assigned_task_ids: set[str],
) -> Optional[Subtask]:
    """
    Find the next available subtask for an agent.

    Checks all tasks with subtasks to find one that:
    - Has incomplete subtasks
    - Has subtasks with satisfied dependencies
    - Is not already assigned

    Parameters
    ----------
    agent_id : str
        ID of the requesting agent
    project_tasks : List[Task]
        All tasks in the project
    subtask_manager : SubtaskManager
        Manager tracking all subtasks
    assigned_task_ids : set[str]
        IDs of tasks/subtasks already assigned

    Returns
    -------
    Optional[Subtask]
        Next available subtask or None
    """
    # Find all tasks that have been decomposed
    for task in project_tasks:
        if not subtask_manager.has_subtasks(task.id):
            continue

        # Skip if parent task is not in TODO status
        if task.status != TaskStatus.TODO:
            continue

        # Get all subtasks for this parent
        subtasks = subtask_manager.get_subtasks(task.id)

        # Get completed subtask IDs
        completed_subtask_ids = {s.id for s in subtasks if s.status == TaskStatus.DONE}

        # Find next available subtask
        next_subtask = subtask_manager.get_next_available_subtask(
            task.id, completed_subtask_ids
        )

        if next_subtask and next_subtask.id not in assigned_task_ids:
            logger.info(
                f"Found available subtask {next_subtask.name} "
                f"for parent task {task.name}"
            )
            return next_subtask

    logger.debug("No available subtasks found")
    return None


def convert_subtask_to_task(subtask: Subtask, parent_task: Task) -> Task:
    """
    Convert a Subtask to a Task object for assignment.

    This allows subtasks to be assigned using the existing
    task assignment infrastructure.

    Parameters
    ----------
    subtask : Subtask
        The subtask to convert
    parent_task : Task
        The parent task this subtask belongs to

    Returns
    -------
    Task
        Task object representing the subtask
    """
    # Create a Task object from the Subtask
    task = Task(
        id=subtask.id,
        name=subtask.name,
        description=subtask.description,
        status=subtask.status,
        priority=subtask.priority,
        assigned_to=subtask.assigned_to,
        created_at=subtask.created_at,
        updated_at=subtask.created_at,  # Use created_at as updated_at
        due_date=parent_task.due_date,  # Inherit from parent
        estimated_hours=subtask.estimated_hours,
        dependencies=subtask.dependencies,
        labels=parent_task.labels,  # Inherit labels from parent
        project_id=parent_task.project_id,
        project_name=parent_task.project_name,
    )

    return task


async def check_and_complete_parent_task(
    parent_task_id: str,
    subtask_manager: SubtaskManager,
    kanban_client: Any,
) -> bool:
    """
    Check if all subtasks are complete and auto-complete parent task.

    Parameters
    ----------
    parent_task_id : str
        ID of the parent task
    subtask_manager : SubtaskManager
        Manager tracking all subtasks
    kanban_client : Any
        Kanban client for updating task status

    Returns
    -------
    bool
        True if parent was auto-completed
    """
    if subtask_manager.is_parent_complete(parent_task_id):
        logger.info(
            f"All subtasks complete for {parent_task_id} " "- auto-completing parent"
        )

        # Update parent task to DONE
        await kanban_client.update_task(
            parent_task_id,
            {
                "status": TaskStatus.DONE,
                "progress": 100,
            },
        )

        # Add completion comment
        subtasks = subtask_manager.get_subtasks(parent_task_id)
        completion_comment = (
            f"✅ **Auto-completed**: All {len(subtasks)} "
            "subtasks completed\n\n"
            "Completed subtasks:\n"
        )
        for subtask in subtasks:
            completion_comment += f"- {subtask.name}\n"

        await kanban_client.add_comment(parent_task_id, completion_comment)

        return True

    return False


async def update_subtask_progress_in_parent(
    parent_task_id: str,
    subtask_id: str,
    subtask_manager: SubtaskManager,
    kanban_client: Any,
) -> None:
    """
    Update parent task progress based on subtask completion.

    Also checks off the corresponding checklist item in Planka.

    Parameters
    ----------
    parent_task_id : str
        ID of the parent task
    subtask_id : str
        ID of the completed subtask
    subtask_manager : SubtaskManager
        Manager tracking all subtasks
    kanban_client : Any
        Kanban client for updating task status
    """
    # Get the completed subtask
    subtask = subtask_manager.subtasks.get(subtask_id)
    if not subtask:
        logger.warning(f"Subtask {subtask_id} not found in manager")
        return

    # Mark checklist item as complete in Planka
    await _mark_checklist_item_complete(parent_task_id, subtask.name)

    # Calculate parent task progress
    progress = subtask_manager.get_completion_percentage(parent_task_id)

    # Update parent task progress
    await kanban_client.update_task_progress(
        parent_task_id,
        {
            "progress": int(progress),
            "status": "in_progress",
            "message": f"Subtask completed: {subtask_id}",
        },
    )

    # Add progress comment
    subtasks = subtask_manager.get_subtasks(parent_task_id)
    completed = sum(1 for s in subtasks if s.status == TaskStatus.DONE)

    progress_comment = (
        f"📊 **Progress Update**: {completed}/{len(subtasks)} "
        f"subtasks completed ({progress:.0f}%)"
    )
    await kanban_client.add_comment(parent_task_id, progress_comment)


async def _mark_checklist_item_complete(parent_card_id: str, subtask_name: str) -> None:
    """
    Mark a checklist item (Planka task) as complete.

    Parameters
    ----------
    parent_card_id : str
        ID of the parent card in Planka
    subtask_name : str
        Name of the subtask to mark complete
    """
    try:
        import json
        import os

        from mcp.client.stdio import stdio_client
        from mcp.types import TextContent

        from mcp import ClientSession, StdioServerParameters

        server_params = StdioServerParameters(
            command="node",
            args=["/app/kanban-mcp/dist/index.js"],
            env=os.environ.copy(),
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Get all checklist items for the card
                result = await session.call_tool(
                    "mcp_kanban_task_manager",
                    {"action": "get_all", "cardId": parent_card_id},
                )

                if not result or not hasattr(result, "content") or not result.content:
                    logger.warning(
                        f"No checklist items found for card {parent_card_id}"
                    )
                    return

                content = result.content[0]
                if isinstance(content, TextContent):
                    tasks_text = str(content.text)
                    checklist_data = json.loads(tasks_text)
                    checklist_items = (
                        checklist_data
                        if isinstance(checklist_data, list)
                        else checklist_data.get("items", [])
                    )

                    # Find the matching checklist item
                    for item in checklist_items:
                        if item.get("name") == subtask_name:
                            task_id = item.get("id")
                            if task_id and not item.get("isCompleted"):
                                # Mark as complete
                                await session.call_tool(
                                    "mcp_kanban_task_manager",
                                    {
                                        "action": "update",
                                        "id": task_id,
                                        "isCompleted": True,
                                    },
                                )
                                logger.info(
                                    f"✅ Checked off checklist item '{subtask_name}' "
                                    f"on card {parent_card_id}"
                                )
                            break

    except Exception as e:
        logger.error(
            f"Error marking checklist item complete for '{subtask_name}': {e}",
            exc_info=True,
        )
