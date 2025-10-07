"""
Task Graph Validator for Marcus.

Validates task graphs BEFORE committing to Kanban to prevent:
1. Circular dependencies
2. Final tasks with no dependencies (PROJECT_SUCCESS jumping the line)
3. Orphaned dependencies (references to non-existent tasks)

This is PREVENTATIVE validation (raises exceptions) not DIAGNOSTIC (logs warnings).
"""

import logging
from typing import Dict, List, Tuple

from src.core.models import Task

logger = logging.getLogger(__name__)


class TaskGraphValidator:
    """
    Validates task dependency graphs before commit.

    CRITICAL: This validator RAISES exceptions for invalid graphs.
    It is designed to PREVENT invalid graphs from being created.
    """

    @staticmethod
    def validate_before_commit(tasks: List[Task]) -> None:
        """
        Validate task graph before committing to Kanban.

        Raises ValueError if graph is invalid.

        Parameters
        ----------
        tasks : List[Task]
            Tasks to validate

        Raises
        ------
        ValueError
            If graph contains circular dependencies, orphaned dependencies,
            or final tasks with no dependencies
        """
        if not tasks:
            return

        # Build task ID map
        task_map = {task.id: task for task in tasks}

        # Run all validations
        TaskGraphValidator._validate_no_orphaned_dependencies(tasks, task_map)
        TaskGraphValidator._validate_no_circular_dependencies(tasks, task_map)
        TaskGraphValidator._validate_final_tasks_have_dependencies(tasks, task_map)

        logger.info(f"✓ Task graph validation passed for {len(tasks)} tasks")

    @staticmethod
    def _validate_no_orphaned_dependencies(
        tasks: List[Task], task_map: Dict[str, Task]
    ) -> None:
        """
        Check that all dependency IDs reference existing tasks.

        Parameters
        ----------
        tasks : List[Task]
            All tasks
        task_map : Dict[str, Task]
            Map of task ID to task

        Raises
        ------
        ValueError
            If any dependency references non-existent task
        """
        orphaned_deps: List[Tuple[str, str]] = []

        for task in tasks:
            if task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id not in task_map:
                        orphaned_deps.append((task.id, dep_id))

        if orphaned_deps:
            error_msg = (
                f"INVALID TASK GRAPH: Found {len(orphaned_deps)} "
                "orphaned dependencies:\n"
            )
            for task_id, dep_id in orphaned_deps[:5]:
                task = task_map[task_id]
                error_msg += (
                    f"  • Task '{task.name}' ({task_id}) depends on "
                    f"non-existent task {dep_id}\n"
                )

            if len(orphaned_deps) > 5:
                error_msg += f"  ... and {len(orphaned_deps) - 5} more\n"

            error_msg += "\nFIX: Remove invalid dependencies before " "creating tasks."
            logger.error(error_msg)
            raise ValueError(error_msg)

    @staticmethod
    def _validate_no_circular_dependencies(
        tasks: List[Task], task_map: Dict[str, Task]
    ) -> None:
        """
        Check for circular dependencies using DFS cycle detection.

        Parameters
        ----------
        tasks : List[Task]
            All tasks
        task_map : Dict[str, Task]
            Map of task ID to task

        Raises
        ------
        ValueError
            If circular dependencies exist
        """
        # Track visit state: white (unvisited), gray (visiting), black (visited)
        color: Dict[str, str] = {task.id: "white" for task in tasks}
        parent: Dict[str, str] = {}

        def dfs_visit(task_id: str, path: List[str]) -> Tuple[bool, List[str]]:
            """Visit node in DFS. Returns True if cycle found."""
            if color[task_id] == "gray":
                # Found back edge - cycle detected
                cycle_start = path.index(task_id)
                cycle = path[cycle_start:] + [task_id]
                return True, cycle

            if color[task_id] == "black":
                return False, []

            # Mark as visiting
            color[task_id] = "gray"
            path.append(task_id)

            task = task_map[task_id]
            if task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id in task_map:  # Skip orphaned deps (caught by other check)
                        parent[dep_id] = task_id
                        has_cycle, cycle = dfs_visit(dep_id, path)
                        if has_cycle:
                            return True, cycle

            # Mark as visited
            color[task_id] = "black"
            path.pop()
            return False, []

        # Check each unvisited node
        for task in tasks:
            if color[task.id] == "white":
                has_cycle, cycle = dfs_visit(task.id, [])
                if has_cycle:
                    # Build human-readable cycle description
                    cycle_names = [
                        "{} ({})".format(task_map[tid].name, tid) for tid in cycle
                    ]
                    error_msg = (
                        "INVALID TASK GRAPH: Circular dependency detected!\n\n"
                        "Cycle path ({} tasks):\n".format(len(cycle))
                    )
                    for i, name in enumerate(cycle_names):
                        arrow = " → " if i < len(cycle_names) - 1 else ""
                        error_msg += f"  {i+1}. {name}{arrow}\n"

                    error_msg += (
                        "\nFIX: Break the cycle by removing one of the "
                        "dependencies above.\n"
                        "Common cause: Task A depends on B, B depends on C, "
                        "C depends on A."
                    )

                    logger.error(error_msg)
                    raise ValueError(error_msg)

    @staticmethod
    def _validate_final_tasks_have_dependencies(
        tasks: List[Task], task_map: Dict[str, Task]
    ) -> None:
        """
        Check that final/documentation tasks depend on implementation tasks.

        This prevents PROJECT_SUCCESS from completing before the actual work.

        Parameters
        ----------
        tasks : List[Task]
            All tasks
        task_map : Dict[str, Task]
            Map of task ID to task

        Raises
        ------
        ValueError
            If final tasks have no dependencies but implementation tasks exist
        """
        # Find implementation tasks (exclude documentation/final tasks)
        implementation_tasks = [
            t
            for t in tasks
            if not any(
                label in t.labels
                for label in ["documentation", "final", "verification"]
            )
        ]

        # Find final tasks
        final_tasks = [
            t
            for t in tasks
            if any(label in t.labels for label in ["final", "verification"])
            or "PROJECT_SUCCESS" in t.name
        ]

        # If no implementation tasks, nothing to validate
        if not implementation_tasks:
            return

        # Check each final task
        invalid_final_tasks: List[Task] = []
        for task in final_tasks:
            if not task.dependencies or len(task.dependencies) == 0:
                invalid_final_tasks.append(task)

        if invalid_final_tasks:
            error_msg = (
                "INVALID TASK GRAPH: {} final tasks have NO dependencies "
                "but {} implementation tasks exist!\n\n".format(
                    len(invalid_final_tasks), len(implementation_tasks)
                )
            )

            for task in invalid_final_tasks:
                error_msg += "  • {} ({})\n".format(task.name, task.id)
                error_msg += "    Labels: {}\n".format(task.labels)
                error_msg += "    Dependencies: {}\n\n".format(
                    task.dependencies or "[]"
                )

            error_msg += (
                "FIX: Final tasks MUST depend on implementation tasks.\n"
                "Common cause: DocumentationTaskGenerator called before "
                "implementation tasks created.\n"
                "Solution: Call enhance_project_with_documentation() AFTER "
                "all implementation tasks are created."
            )

            logger.error(error_msg)
            raise ValueError(error_msg)

    @staticmethod
    def validate_and_log(tasks: List[Task]) -> Tuple[bool, str]:
        """
        Validate task graph and return (is_valid, error_message).

        Non-raising version for diagnostic purposes.

        Parameters
        ----------
        tasks : List[Task]
            Tasks to validate

        Returns
        -------
        Tuple[bool, str]
            (is_valid, error_message). If valid, error_message is empty string.
        """
        try:
            TaskGraphValidator.validate_before_commit(tasks)
            return True, ""
        except ValueError as e:
            return False, str(e)
