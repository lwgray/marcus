"""
Task Assignment Integration with Subtasks.

This module integrates subtask assignment into the existing
task assignment workflow without modifying core task.py logic.
"""

import logging
from typing import Any, Awaitable, Callable, Optional

from src.core.models import Task
from src.marcus_mcp.coordinator.subtask_assignment import (
    convert_subtask_to_task,
    find_next_available_subtask,
)

logger = logging.getLogger(__name__)


async def find_optimal_task_with_subtasks(
    agent_id: str,
    state: Any,
    fallback_task_finder: Callable[[str, Any], Awaitable[Optional[Task]]],
) -> Optional[Task]:
    """
    Find optimal task for agent, prioritizing subtasks.

    Checks for available subtasks first, then falls back to
    regular task assignment if no subtasks available.

    Parameters
    ----------
    agent_id : str
        ID of the requesting agent
    state : Any
        Marcus server state instance
    fallback_task_finder : Callable[[str, Any], Awaitable[Optional[Task]]]
        Original task finder function to use if no subtasks

    Returns
    -------
    Optional[Task]
        Task or Subtask (converted to Task) for assignment
    """
    # Check if subtask feature is enabled
    from src.config.settings import Settings

    settings = Settings()
    if not settings.is_subtasks_enabled():
        logger.debug("Subtask feature is disabled, using fallback")
        return await fallback_task_finder(agent_id, state)

    # Check if subtask manager is available
    if not hasattr(state, "subtask_manager") or not state.subtask_manager:
        logger.debug("SubtaskManager not available, using fallback")
        return await fallback_task_finder(agent_id, state)

    # Get assigned task IDs
    assigned_task_ids = {a.task_id for a in state.agent_tasks.values()}
    persisted_assigned_ids = (
        await state.assignment_persistence.get_all_assigned_task_ids()
    )
    all_assigned_ids = (
        assigned_task_ids | persisted_assigned_ids | state.tasks_being_assigned
    )

    # Try to find available subtask
    subtask = find_next_available_subtask(
        agent_id,
        state.project_tasks,
        state.subtask_manager,
        all_assigned_ids,
    )

    if subtask:
        # Find parent task for context
        parent_task = next(
            (t for t in state.project_tasks if t.id == subtask.parent_task_id),
            None,
        )

        if parent_task:
            # Update parent task to IN_PROGRESS if it's still TODO
            # (first subtask being assigned)
            from src.core.models import TaskStatus

            if parent_task.status == TaskStatus.TODO:
                logger.info(
                    f"Moving parent task '{parent_task.name}' to IN_PROGRESS "
                    f"(first subtask assignment)"
                )
                try:
                    await state.kanban_client.update_task(
                        parent_task.id,
                        {"status": TaskStatus.IN_PROGRESS},
                    )
                    # Update local state
                    parent_task.status = TaskStatus.IN_PROGRESS
                except Exception as e:
                    logger.error(
                        f"Failed to update parent task status: {e}",
                        exc_info=True,
                    )

            # Convert subtask to Task for assignment
            task = convert_subtask_to_task(subtask, parent_task)

            # Add metadata to help identify this as a subtask
            # This will help with instruction generation
            # These are dynamic attributes added at runtime
            task._is_subtask = True  # type: ignore[attr-defined]
            task._parent_task_id = parent_task.id  # type: ignore[attr-defined]
            task._parent_task_name = parent_task.name  # type: ignore[attr-defined]

            logger.info(
                f"Assigning subtask {subtask.name} "
                f"(parent: {parent_task.name}) to {agent_id}"
            )
            return task
        else:
            logger.warning(
                f"Parent task {subtask.parent_task_id} "
                f"not found for subtask {subtask.id}"
            )

    # No subtasks available, use fallback
    logger.debug("No available subtasks, using fallback task finder")
    return await fallback_task_finder(agent_id, state)
