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


def _determine_task_type(task: Task) -> str:
    """
    Determine the task type (design/implementation/testing) from task name and labels.

    This logic mirrors the type detection in AIAnalysisEngine.generate_task_instructions()
    to ensure consistency.

    Parameters
    ----------
    task : Task
        The task to determine type for

    Returns
    -------
    str
        Task type: "design", "testing", or "implementation"
    """
    task_name_lower = task.name.lower()
    task_labels = getattr(task, "labels", []) or []

    # Check name and labels for explicit type indicators
    if "design" in task_name_lower or "type:design" in task_labels:
        return "design"
    elif "test" in task_name_lower or "type:testing" in task_labels:
        return "testing"
    else:
        return "implementation"


def _are_dependencies_satisfied(task: Task, all_tasks: List[Task]) -> bool:
    """
    Check if all dependencies of a task are completed.

    This ensures that subtasks from a parent task are only available
    after all of the parent task's dependencies are satisfied.

    Parameters
    ----------
    task : Task
        The task to check dependencies for
    all_tasks : List[Task]
        All tasks in the project

    Returns
    -------
    bool
        True if all dependencies are satisfied (or no dependencies exist)
    """
    if not task.dependencies:
        return True

    # Create a mapping of task IDs to their status
    task_status_map = {t.id: t.status for t in all_tasks}

    # Check if all dependencies are DONE
    for dep_id in task.dependencies:
        dep_status = task_status_map.get(dep_id)
        if dep_status != TaskStatus.DONE:
            logger.debug(
                f"Parent task {task.name} has unsatisfied dependency: "
                f"{dep_id} (status: {dep_status})"
            )
            return False

    return True


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

        # Skip if parent task is already DONE (allow TODO and IN_PROGRESS)
        # This enables parallel assignment of multiple subtasks from the same parent
        if task.status == TaskStatus.DONE:
            continue

        # GH-64: Check if parent task dependencies are satisfied
        # Subtasks should only be available after parent's dependencies complete
        if not _are_dependencies_satisfied(task, project_tasks):
            logger.debug(
                f"Skipping subtasks for '{task.name}' - "
                "parent dependencies not satisfied"
            )
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
        Task object representing the subtask with parent task type metadata
    """
    # Determine parent task type
    parent_task_type = _determine_task_type(parent_task)

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

    # Add parent task type as metadata
    # This ensures subtasks inherit the correct instruction type
    task._parent_task_type = parent_task_type  # type: ignore[attr-defined]

    logger.debug(
        f"Converted subtask '{subtask.name}' with parent task type: {parent_task_type}"
    )

    return task


async def check_and_complete_parent_task(
    parent_task_id: str,
    subtask_manager: SubtaskManager,
    kanban_client: Any,
    state: Any = None,
) -> bool:
    """
    Check if all subtasks are complete and auto-complete parent task.

    CRITICAL: Also rolls up subtask artifacts and decisions to parent task
    so that dependent tasks can see the work done by subtasks.

    Parameters
    ----------
    parent_task_id : str
        ID of the parent task
    subtask_manager : SubtaskManager
        Manager tracking all subtasks
    kanban_client : Any
        Kanban client for updating task status
    state : Any, optional
        Marcus server state for accessing artifacts and context

    Returns
    -------
    bool
        True if parent was auto-completed
    """
    if subtask_manager.is_parent_complete(parent_task_id):
        logger.info(
            f"All subtasks complete for {parent_task_id} " "- auto-completing parent"
        )

        # CRITICAL FIX: Roll up subtask artifacts and decisions to parent
        # This ensures dependent tasks can see what subtasks produced
        if state:
            await _rollup_subtask_artifacts_to_parent(
                parent_task_id, subtask_manager, state
            )
            await _rollup_subtask_decisions_to_parent(
                parent_task_id, subtask_manager, state
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


async def _rollup_subtask_artifacts_to_parent(
    parent_task_id: str, subtask_manager: SubtaskManager, state: Any
) -> None:
    """
    Roll up all subtask artifacts to the parent task.

    This ensures that when Task 2 depends on Task 1, and both have subtasks,
    Task 2's subtasks can see the artifacts produced by Task 1's subtasks.

    Parameters
    ----------
    parent_task_id : str
        ID of the parent task
    subtask_manager : SubtaskManager
        Manager tracking all subtasks
    state : Any
        Marcus server state for accessing task_artifacts
    """
    if not hasattr(state, "task_artifacts"):
        return

    subtasks = subtask_manager.get_subtasks(parent_task_id)
    if not subtasks:
        return

    # Initialize parent's artifact list if not exists
    if parent_task_id not in state.task_artifacts:
        state.task_artifacts[parent_task_id] = []

    # Collect artifacts from all subtasks
    rollup_count = 0
    for subtask in subtasks:
        if subtask.id in state.task_artifacts:
            for artifact in state.task_artifacts[subtask.id]:
                # Add subtask context to artifact
                rollup_artifact = artifact.copy()
                rollup_artifact["from_subtask"] = subtask.id
                rollup_artifact["from_subtask_name"] = subtask.name
                rollup_artifact["description"] = (
                    f"[From subtask: {subtask.name}] "
                    f"{rollup_artifact.get('description', '')}"
                )

                # Add to parent's artifacts
                state.task_artifacts[parent_task_id].append(rollup_artifact)
                rollup_count += 1

    if rollup_count > 0:
        logger.info(
            f"Rolled up {rollup_count} artifacts from {len(subtasks)} subtasks "
            f"to parent task {parent_task_id}"
        )


async def _rollup_subtask_decisions_to_parent(
    parent_task_id: str, subtask_manager: SubtaskManager, state: Any
) -> None:
    """
    Roll up all subtask decisions to the parent task.

    This ensures that when Task 2 depends on Task 1, and both have subtasks,
    Task 2's subtasks can see the decisions made by Task 1's subtasks.

    Parameters
    ----------
    parent_task_id : str
        ID of the parent task
    subtask_manager : SubtaskManager
        Manager tracking all subtasks
    state : Any
        Marcus server state for accessing context.decisions
    """
    if not hasattr(state, "context") or not state.context:
        return

    subtasks = subtask_manager.get_subtasks(parent_task_id)
    if not subtasks:
        return

    # Collect decisions from all subtasks and re-log them for parent
    rollup_count = 0
    for subtask in subtasks:
        # Find decisions made during this subtask
        subtask_decisions = [
            d for d in state.context.decisions if d.task_id == subtask.id
        ]

        for decision in subtask_decisions:
            # Re-log the decision with parent task ID
            await state.context.log_decision(
                agent_id=decision.agent_id,
                task_id=parent_task_id,
                what=f"[From subtask: {subtask.name}] {decision.what}",
                why=decision.why,
                impact=decision.impact,
            )
            rollup_count += 1

    if rollup_count > 0:
        logger.info(
            f"Rolled up {rollup_count} decisions from {len(subtasks)} subtasks "
            f"to parent task {parent_task_id}"
        )


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

        # Use local path for kanban-mcp
        import os

        from mcp.client.stdio import stdio_client
        from mcp.types import TextContent

        from mcp import ClientSession, StdioServerParameters

        kanban_mcp_path = os.path.expanduser("~/dev/kanban-mcp/dist/index.js")
        server_params = StdioServerParameters(
            command="node",
            args=[kanban_mcp_path],
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
