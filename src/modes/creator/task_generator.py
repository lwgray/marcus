"""
Task Generator for Marcus Creator Mode

Generates properly ordered tasks from templates to prevent illogical assignments.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.core.models import Priority, Task, TaskStatus
from src.modes.creator.template_library import (
    PhaseTemplate,
    ProjectSize,
    ProjectTemplate,
    TaskTemplate,
)

logger = logging.getLogger(__name__)


class TaskGenerator:
    """Generates task structures from templates or requirements"""

    def __init__(self) -> None:
        self.generated_tasks: List[Task] = []
        self.task_map: Dict[str, Task] = {}  # name -> Task mapping for dependencies

    async def generate_from_template(
        self, template: ProjectTemplate, customizations: Dict[str, Any]
    ) -> List[Task]:
        """
        Generate tasks from template with customizations

        Args:
            template: Project template to use
            customizations: Custom parameters like size, excluded_phases, etc.

        Returns:
            List of generated tasks with proper dependencies
        """
        # Extract customizations
        project_size = customizations.get("size", ProjectSize.MEDIUM)
        excluded_phases: List[str] = customizations.get("excluded_phases", [])
        additional_labels: List[str] = customizations.get("labels", [])
        project_name = customizations.get("project_name", template.name)
        start_date = customizations.get("start_date", datetime.now())

        logger.info(
            f"Generating tasks from template '{template.name}' with size '{project_size.value}'"
        )

        # Reset state
        self.generated_tasks = []
        self.task_map = {}

        # Generate tasks for each phase
        current_date = start_date

        for phase in template.phases:
            if phase.name.lower() in excluded_phases:
                logger.info(f"Skipping excluded phase: {phase.name}")
                continue

            phase_tasks = await self._generate_phase_tasks(
                phase=phase,
                template=template,
                project_size=project_size,
                additional_labels=additional_labels,
                project_name=project_name,
                start_date=current_date,
            )

            # Update start date for next phase based on this phase's duration
            if phase_tasks:
                phase_duration = sum(t.estimated_hours for t in phase_tasks)
                # Assume 6 productive hours per day
                days_needed = (phase_duration / 6) + 2  # Add buffer
                current_date += timedelta(days=days_needed)

            self.generated_tasks.extend(phase_tasks)

        # Resolve dependencies
        await self._resolve_dependencies()

        # Validate task order
        await self._validate_task_order()

        logger.info(f"Generated {len(self.generated_tasks)} tasks from template")

        return self.generated_tasks

    async def _generate_phase_tasks(
        self,
        phase: PhaseTemplate,
        template: ProjectTemplate,
        project_size: ProjectSize,
        additional_labels: List[str],
        project_name: str,
        start_date: datetime,
    ) -> List[Task]:
        """Generate tasks for a single phase"""
        phase_tasks: List[Task] = []

        for task_template in phase.tasks:
            # Skip optional tasks for MVP
            if project_size == ProjectSize.MVP and task_template.optional:
                continue

            # Check conditions
            if not self._check_conditions(task_template.conditions, project_size):
                continue

            # Adjust task for size
            adjusted_template = template._adjust_task_for_size(
                task_template, project_size
            )

            # Create Task object
            task = await self._create_task_from_template(
                task_template=adjusted_template,
                phase_name=phase.name,
                additional_labels=additional_labels,
                project_name=project_name,
                phase_order=phase.order,
            )

            phase_tasks.append(task)
            self.task_map[task.name] = task

        return phase_tasks

    async def _create_task_from_template(
        self,
        task_template: TaskTemplate,
        phase_name: str,
        additional_labels: List[str],
        project_name: str,
        phase_order: int,
    ) -> Task:
        """Create a Task object from a TaskTemplate"""
        # Combine labels
        labels = [f"phase:{phase_name.lower()}"]
        labels.extend(task_template.labels)
        labels.extend(additional_labels)

        # Generate unique ID
        task_id = str(uuid.uuid4())

        # Create description with context
        description = f"{task_template.description}\n\n"
        description += f"Project: {project_name}\n"
        description += f"Phase: {phase_name}\n"

        if task_template.dependencies:
            description += f"Depends on: {', '.join(task_template.dependencies)}\n"

        # Create task
        task = Task(
            id=task_id,
            name=task_template.name,
            description=description.strip(),
            status=TaskStatus.TODO,
            priority=task_template.priority,
            labels=list(set(labels)),  # Remove duplicates
            estimated_hours=task_template.estimated_hours,
            dependencies=[],  # Will be resolved later
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,  # Can be calculated based on dependencies
            assigned_to=None,
            source_context={
                "template_name": task_template.name,
                "phase_order": phase_order,
                "phase_name": phase_name,
            },
        )

        return task

    async def _resolve_dependencies(self) -> None:
        """Resolve task dependencies by name"""
        for task in self.generated_tasks:
            # Get template dependencies from source_context
            task_name = (
                task.source_context.get("template_name", task.name)
                if task.source_context
                else task.name
            )

            # Find the original template
            for template_task in self._find_template_dependencies(task_name):
                if template_task in self.task_map:
                    dependency = self.task_map[template_task]
                    task.dependencies.append(dependency.id)
                else:
                    logger.warning(
                        f"Dependency '{template_task}' not found for task '{task.name}'"
                    )

    def _find_template_dependencies(self, task_name: str) -> List[str]:
        """Find dependencies from the original template"""
        # This is a simplified version - in practice, we'd look up the template
        # For now, we'll parse from the task description
        for task in self.generated_tasks:
            if (
                task.source_context
                and task.source_context.get("template_name") == task_name
            ):
                if "Depends on:" in task.description:
                    deps_line = task.description.split("Depends on:")[1].split("\n")[0]
                    return [d.strip() for d in deps_line.split(",")]
        return []

    async def _validate_task_order(self) -> None:
        """Validate that task dependencies make sense"""
        errors: List[str] = []

        for task in self.generated_tasks:
            task_phase = (
                task.source_context.get("phase_order", 0) if task.source_context else 0
            )

            for dep_id in task.dependencies:
                dep_task = next(
                    (t for t in self.generated_tasks if t.id == dep_id), None
                )
                if dep_task:
                    dep_phase = (
                        dep_task.source_context.get("phase_order", 0)
                        if dep_task.source_context
                        else 0
                    )

                    # Dependency should be in same or earlier phase
                    if dep_phase > task_phase:
                        errors.append(
                            f"Task '{task.name}' (phase {task_phase}) depends on "
                            f"'{dep_task.name}' (phase {dep_phase}) which comes later"
                        )

        if errors:
            for error in errors:
                logger.error(error)
            raise ValueError("Invalid task dependencies detected")

    async def create_task_hierarchy(
        self, tasks: List[Dict[str, Any]], project_name: str = "unnamed_project"
    ) -> List[Task]:
        """
        Create proper task objects from raw task data

        Args:
            tasks: List of task dictionaries
            project_name: Name of the project for working directory

        Returns:
            List of Task objects with proper structure
        """
        created_tasks: List[Task] = []
        task_id_map: Dict[str, str] = {}  # temporary name -> id mapping

        # First pass: create all tasks
        for task_data in tasks:
            task_id = str(uuid.uuid4())

            task = Task(
                id=task_id,
                name=task_data.get("name", "Unnamed task"),
                description=task_data.get("description", ""),
                status=TaskStatus.TODO,
                priority=self._parse_priority(task_data.get("priority", "medium")),
                labels=task_data.get("labels", []),
                estimated_hours=task_data.get("estimated_hours", 0),
                dependencies=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                assigned_to=None,
            )

            created_tasks.append(task)
            task_id_map[task.name] = task_id

        # Second pass: resolve dependencies
        for i, task_data in enumerate(tasks):
            if "depends_on" in task_data:
                task = created_tasks[i]
                for dep_name in task_data["depends_on"]:
                    if dep_name in task_id_map:
                        task.dependencies.append(task_id_map[dep_name])
                    else:
                        logger.warning(
                            f"Dependency '{dep_name}' not found for task '{task.name}'"
                        )

        return created_tasks

    def _check_conditions(
        self, conditions: Dict[str, Any], project_size: ProjectSize
    ) -> bool:
        """Check if task conditions are met"""
        if not conditions:
            return True

        # Check size conditions
        if "min_size" in conditions:
            size_order = [
                ProjectSize.MVP,
                ProjectSize.SMALL,
                ProjectSize.MEDIUM,
                ProjectSize.LARGE,
                ProjectSize.ENTERPRISE,
            ]
            min_size = ProjectSize(conditions["min_size"])
            if size_order.index(project_size) < size_order.index(min_size):
                return False

        # Check feature flags
        if "requires_features" in conditions:
            # TODO: Implement feature checking
            pass

        return True

    def _parse_priority(self, priority_str: str) -> Priority:
        """Parse priority string to Priority enum"""
        priority_map = {
            "low": Priority.LOW,
            "medium": Priority.MEDIUM,
            "high": Priority.HIGH,
            "urgent": Priority.URGENT,
        }

        return priority_map.get(priority_str.lower(), Priority.MEDIUM)
