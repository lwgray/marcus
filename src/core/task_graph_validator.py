"""
Task Graph Validator for Marcus.

Validates and AUTO-FIXES task graphs BEFORE committing to Kanban:
1. Removes orphaned dependencies (references to non-existent tasks)
2. Breaks circular dependencies by removing edges
3. Adds dependencies to final tasks (PROJECT_SUCCESS jumping the line)

This is CORRECTIVE validation (fixes problems) not PREVENTATIVE (raises exceptions).
Users get valid task graphs automatically, with warnings about what was fixed.
"""

import logging
from typing import Dict, List, Tuple

from src.core.models import Task

logger = logging.getLogger(__name__)


class TaskGraphValidator:
    """
    Validates and auto-fixes task dependency graphs before commit.

    Primary method: validate_and_fix() - Automatically fixes issues
    Legacy method: validate_strictly() - Raises exceptions (for tests/debugging)
    """

    @staticmethod
    def validate_and_fix(tasks: List[Task]) -> Tuple[List[Task], List[str]]:
        """
        Validate and automatically fix task graph issues.

        This is the PRIMARY method for task graph validation.
        It fixes problems automatically rather than raising exceptions.

        Parameters
        ----------
        tasks : List[Task]
            Tasks to validate and fix

        Returns
        -------
        Tuple[List[Task], List[str]]
            (fixed_tasks, user_warnings)
            - fixed_tasks: Tasks with issues corrected
            - user_warnings: Human-readable descriptions of what was fixed

        Notes
        -----
        This method NEVER raises exceptions for fixable issues.
        Users always get valid task graphs.
        """
        if not tasks:
            return tasks, []

        # Build task ID map
        task_map = {task.id: task for task in tasks}
        all_warnings: List[str] = []

        # Fix 1: Remove orphaned dependencies
        tasks, warnings = TaskGraphValidator._fix_orphaned_dependencies(tasks, task_map)
        all_warnings.extend(warnings)

        # Fix 2: Break circular dependencies
        tasks, warnings = TaskGraphValidator._fix_circular_dependencies(tasks, task_map)
        all_warnings.extend(warnings)

        # Fix 3: Add dependencies to final tasks
        tasks, warnings = TaskGraphValidator._fix_final_tasks_missing_dependencies(
            tasks, task_map
        )
        all_warnings.extend(warnings)

        if all_warnings:
            logger.warning(f"Auto-fixed {len(all_warnings)} task graph issues")
            for warning in all_warnings:
                logger.info(f"  • {warning}")
        else:
            logger.info(f"✓ Task graph validation passed for {len(tasks)} tasks")

        return tasks, all_warnings

    @staticmethod
    def validate_strictly(tasks: List[Task]) -> None:
        """
        Validate task graph with strict checking (raises exceptions).

        LEGACY METHOD: Used for tests and debugging only.
        For production use validate_and_fix() instead.

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

        # Run all validations (these raise on issues)
        TaskGraphValidator._validate_no_orphaned_dependencies(tasks, task_map)
        TaskGraphValidator._validate_no_circular_dependencies(tasks, task_map)
        TaskGraphValidator._validate_final_tasks_have_dependencies(tasks, task_map)

        logger.info(f"✓ Strict task graph validation passed for {len(tasks)} tasks")

    # Legacy alias for backward compatibility
    validate_before_commit = validate_strictly

    @staticmethod
    def _fix_orphaned_dependencies(
        tasks: List[Task], task_map: Dict[str, Task]
    ) -> Tuple[List[Task], List[str]]:
        """
        Remove dependencies that reference non-existent tasks.

        Parameters
        ----------
        tasks : List[Task]
            All tasks
        task_map : Dict[str, Task]
            Map of task ID to task

        Returns
        -------
        Tuple[List[Task], List[str]]
            (fixed_tasks, warnings)
        """
        warnings = []

        for task in tasks:
            if task.dependencies:
                original_count = len(task.dependencies)
                # Keep only dependencies that exist
                valid_deps = [d for d in task.dependencies if d in task_map]

                if len(valid_deps) < original_count:
                    removed_count = original_count - len(valid_deps)
                    task.dependencies = valid_deps
                    warnings.append(
                        f"Removed {removed_count} invalid "
                        f"{'dependency' if removed_count == 1 else 'dependencies'} "
                        f"from '{task.name}'"
                    )

        return tasks, warnings

    @staticmethod
    def _fix_circular_dependencies(
        tasks: List[Task], task_map: Dict[str, Task]
    ) -> Tuple[List[Task], List[str]]:
        """
        Break circular dependency cycles by removing edges.

        Strategy: Remove the last edge in the cycle (least disruptive).

        Parameters
        ----------
        tasks : List[Task]
            All tasks
        task_map : Dict[str, Task]
            Map of task ID to task

        Returns
        -------
        Tuple[List[Task], List[str]]
            (fixed_tasks, warnings)
        """
        warnings = []
        max_iterations = 10  # Prevent infinite loops

        for iteration in range(max_iterations):
            # Detect cycle using DFS
            cycle = TaskGraphValidator._detect_cycle(tasks, task_map)

            if not cycle:
                break  # No more cycles

            # Break the cycle by removing last edge
            # Cycle format: [A, B, C, A] means A→B→C→A
            if len(cycle) >= 2:
                # Remove dependency from second-to-last to last
                task_id_to_fix = cycle[-2]
                dep_to_remove = cycle[-1]

                task_to_fix = task_map[task_id_to_fix]
                if dep_to_remove in task_to_fix.dependencies:
                    task_to_fix.dependencies.remove(dep_to_remove)
                    warnings.append(
                        f"Broke circular dependency: removed link from "
                        f"'{task_to_fix.name}' to '{task_map[dep_to_remove].name}'"
                    )

        return tasks, warnings

    @staticmethod
    def _detect_cycle(tasks: List[Task], task_map: Dict[str, Task]) -> List[str]:
        """
        Detect a single cycle in the task graph using DFS.

        Returns
        -------
        List[str]
            Cycle as list of task IDs, or empty list if no cycle.
            Format: [A, B, C, A] means A→B→C→A
        """
        color: Dict[str, str] = {task.id: "white" for task in tasks}

        def dfs_visit(task_id: str, path: List[str]) -> List[str]:
            """Visit node in DFS. Returns cycle if found, empty list otherwise."""
            if color[task_id] == "gray":
                # Found back edge - cycle detected
                cycle_start = path.index(task_id)
                return path[cycle_start:] + [task_id]

            if color[task_id] == "black":
                return []

            # Mark as visiting
            color[task_id] = "gray"
            path.append(task_id)

            task = task_map[task_id]
            if task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id in task_map:
                        cycle = dfs_visit(dep_id, path)
                        if cycle:
                            return cycle

            # Mark as visited
            color[task_id] = "black"
            path.pop()
            return []

        # Check each unvisited node
        for task in tasks:
            if color[task.id] == "white":
                cycle = dfs_visit(task.id, [])
                if cycle:
                    return cycle

        return []

    @staticmethod
    def _fix_final_tasks_missing_dependencies(
        tasks: List[Task], task_map: Dict[str, Task]
    ) -> Tuple[List[Task], List[str]]:
        """
        Add implementation task dependencies to final tasks.

        Ensures PROJECT_SUCCESS and other final tasks only complete
        after all implementation work is done.

        Parameters
        ----------
        tasks : List[Task]
            All tasks
        task_map : Dict[str, Task]
            Map of task ID to task

        Returns
        -------
        Tuple[List[Task], List[str]]
            (fixed_tasks, warnings)
        """
        warnings: List[str] = []

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

        # If no implementation tasks, nothing to fix
        if not implementation_tasks or not final_tasks:
            return tasks, warnings

        # Check each final task
        for final_task in final_tasks:
            if not final_task.dependencies or len(final_task.dependencies) == 0:
                # Add ALL implementation task IDs as dependencies
                impl_ids = [t.id for t in implementation_tasks]
                final_task.dependencies = impl_ids
                warnings.append(
                    f"Added {len(impl_ids)} implementation task "
                    f"{'dependency' if len(impl_ids) == 1 else 'dependencies'} "
                    f"to '{final_task.name}' to ensure it runs last"
                )

        return tasks, warnings

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
