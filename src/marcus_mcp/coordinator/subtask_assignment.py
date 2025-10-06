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
