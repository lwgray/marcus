"""Basic Creator Mode for Marcus Hybrid Approach.

Implements the Creator Mode that generates project structures from requirements
to prevent illogical task assignments like "Deploy to production" first.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.models import Task
from src.modes.creator.task_generator import TaskGenerator
from src.modes.creator.template_library import (
    APIServiceTemplate,
    MobileAppTemplate,
    ProjectSize,
    WebAppTemplate,
)

logger = logging.getLogger(__name__)


class BasicCreatorMode:
    """Basic Creator Mode implementation."""

    def __init__(self) -> None:
        self.templates = {
            "web": WebAppTemplate(),
            "api": APIServiceTemplate(),
            "mobile": MobileAppTemplate(),
        }
        self.task_generator = TaskGenerator()
        self.state: Dict[str, Any] = {"active_project": None, "generated_tasks": []}

    async def initialize(self, saved_state: Dict[str, Any]) -> None:
        """Initialize mode with saved state."""
        if saved_state:
            self.state.update(saved_state)
            logger.info("Creator mode initialized with saved state")
        else:
            logger.info("Creator mode initialized with default state")

    async def get_state(self) -> Dict[str, Any]:
        """Get current mode state for saving."""
        return self.state.copy()

    async def get_status(self) -> Dict[str, Any]:
        """Get current mode status."""
        return {
            "mode": "creator",
            "active_project": self.state.get("active_project"),
            "generated_tasks_count": len(self.state.get("generated_tasks") or []),
            "available_templates": list(self.templates.keys()),
        }

    async def create_project_from_template(
        self,
        template_name: str,
        project_name: str,
        customizations: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new project from a template.

        Parameters
        ----------
        template_name : str
            Name of template to use ('web', 'api', 'mobile').
        project_name : str
            Name for the new project.
        customizations : Optional[Dict[str, Any]]
            Custom parameters (size, excluded_phases, etc.).

        Returns
        -------
        Dict[str, Any]
            Result containing generated tasks.
        """
        if template_name not in self.templates:
            return {
                "success": False,
                "error": f"Template '{template_name}' not found",
                "available_templates": list(self.templates.keys()),
            }

        template = self.templates[template_name]
        customizations = customizations or {}
        customizations["project_name"] = project_name

        try:
            # Generate tasks from template
            generated_tasks = await self.task_generator.generate_from_template(
                template=template, customizations=customizations
            )

            # Update state
            self.state["active_project"] = {
                "name": project_name,
                "template": template_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "customizations": customizations,
            }
            self.state["generated_tasks"] = [
                self._task_to_dict(task) for task in generated_tasks
            ]

            logger.info(
                f"Generated {len(generated_tasks)} tasks for project '{project_name}'"
            )

            return {
                "success": True,
                "project_name": project_name,
                "template_used": template_name,
                "tasks_generated": len(generated_tasks),
                "tasks": [self._task_to_dict(task) for task in generated_tasks],
                "phases": self._get_phases_summary(generated_tasks),
                "estimated_total_hours": sum(
                    t.estimated_hours for t in generated_tasks
                ),
            }

        except Exception as e:
            logger.error(f"Error generating project from template: {e}")
            return {"success": False, "error": str(e)}

    async def customize_project(self, adjustments: Dict[str, Any]) -> Dict[str, Any]:
        """Customize the currently active project.

        Parameters
        ----------
        adjustments : Dict[str, Any]
            Adjustments to make (add/remove phases, change size, etc.).

        Returns
        -------
        Dict[str, Any]
            Updated project information.
        """
        if not self.state.get("active_project"):
            return {"success": False, "error": "No active project to customize"}

        try:
            active_project = self.state["active_project"]
            if not isinstance(active_project, dict):
                return {"success": False, "error": "Invalid active project state"}

            # Apply adjustments
            project_customizations = active_project.get("customizations", {})
            if not isinstance(project_customizations, dict):
                project_customizations = {}
            customizations = project_customizations.copy()
            customizations.update(adjustments)

            # Regenerate with new customizations
            template_name = active_project.get("template")
            if not template_name or template_name not in self.templates:
                return {"success": False, "error": "Invalid template in active project"}
            template = self.templates[template_name]
            generated_tasks = await self.task_generator.generate_from_template(
                template=template, customizations=customizations
            )

            # Update state
            if isinstance(self.state.get("active_project"), dict):
                self.state["active_project"]["customizations"] = customizations
            self.state["generated_tasks"] = [
                self._task_to_dict(task) for task in generated_tasks
            ]

            return {
                "success": True,
                "message": "Project customized successfully",
                "tasks_generated": len(generated_tasks),
                "tasks": [self._task_to_dict(task) for task in generated_tasks],
            }

        except Exception as e:
            logger.error(f"Error customizing project: {e}")
            return {"success": False, "error": str(e)}

    async def get_available_templates(self) -> Dict[str, Any]:
        """Get list of available project templates."""
        templates_info = {}

        for name, template in self.templates.items():
            templates_info[name] = {
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "phases": [
                    {
                        "name": phase.name,
                        "description": phase.description,
                        "task_count": len(phase.tasks),
                    }
                    for phase in template.phases
                ],
                "total_tasks": len(template.get_all_tasks()),
                "estimated_hours": {
                    size.value: sum(
                        t.estimated_hours for t in template.get_all_tasks(size)
                    )
                    for size in ProjectSize
                },
            }

        return {
            "templates": templates_info,
            "project_sizes": [size.value for size in ProjectSize],
        }

    async def preview_template(
        self, template_name: str, size: Optional[str] = None
    ) -> Dict[str, Any]:
        """Preview what a template would generate.

        Parameters
        ----------
        template_name : str
            Template to preview.
        size : Optional[str]
            Project size to preview.

        Returns
        -------
        Dict[str, Any]
            Preview of tasks that would be generated.
        """
        if template_name not in self.templates:
            return {"success": False, "error": f"Template '{template_name}' not found"}

        template = self.templates[template_name]
        project_size = ProjectSize(size) if size else ProjectSize.MEDIUM

        # Get tasks without generating IDs
        preview_tasks = template.get_all_tasks(project_size)

        phases_preview: Dict[str, Dict[str, Any]] = {}
        for task in preview_tasks:
            phase = getattr(task, "phase", "Unknown")
            if phase not in phases_preview:
                phases_preview[phase] = {"tasks": [], "estimated_hours": 0}

            task_list = phases_preview[phase]["tasks"]
            if isinstance(task_list, list):
                task_list.append(
                    {
                        "name": task.name,
                        "description": task.description,
                        "estimated_hours": task.estimated_hours,
                        "priority": task.priority.value,
                        "optional": task.optional,
                    }
                )
            phases_preview[phase]["estimated_hours"] += task.estimated_hours

        return {
            "success": True,
            "template_name": template.name,
            "size": project_size.value,
            "total_tasks": len(preview_tasks),
            "total_estimated_hours": sum(t.estimated_hours for t in preview_tasks),
            "phases": phases_preview,
        }

    async def create_from_description(
        self, description: str, project_name: str
    ) -> Dict[str, Any]:
        """Create project from natural language description.

        This is a simplified version - Phase 2 will add AI-powered analysis.

        Parameters
        ----------
        description : str
            Project description.
        project_name : str
            Name for the project.

        Returns
        -------
        Dict[str, Any]
            Generated project or template recommendation.
        """
        description_lower = description.lower()

        # Simple keyword matching to suggest template
        if any(
            word in description_lower for word in ["mobile", "app", "ios", "android"]
        ):
            suggested_template = "mobile"
        elif any(
            word in description_lower
            for word in ["api", "service", "endpoint", "backend"]
        ):
            suggested_template = "api"
        elif any(
            word in description_lower
            for word in ["web", "website", "frontend", "full-stack"]
        ):
            suggested_template = "web"
        else:
            suggested_template = "web"  # Default

        # Suggest size based on description
        if any(
            word in description_lower
            for word in ["mvp", "prototype", "quick", "simple"]
        ):
            suggested_size = ProjectSize.MVP
        elif any(
            word in description_lower for word in ["enterprise", "large", "complex"]
        ):
            suggested_size = ProjectSize.LARGE
        else:
            suggested_size = ProjectSize.MEDIUM

        # Generate project with suggestions
        customizations = {"size": suggested_size, "description_provided": description}

        result = await self.create_project_from_template(
            template_name=suggested_template,
            project_name=project_name,
            customizations=customizations,
        )

        if result.get("success"):
            result["suggestion_reasoning"] = (
                f"Based on your description, I suggested a {suggested_template} "
                f"project with {suggested_size.value} size. You can customize this."
            )

        return result

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert Task object to dictionary."""
        return {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "labels": task.labels,
            "estimated_hours": task.estimated_hours,
            "dependencies": task.dependencies,
            "phase": task.source_context.get("phase") if task.source_context else None,
            "phase_order": (
                task.source_context.get("phase_order") if task.source_context else None
            ),
            "generated": (
                task.source_context.get("generated", False)
                if task.source_context
                else False
            ),
        }

    def _get_phases_summary(self, tasks: List[Task]) -> Dict[str, Any]:
        """Get summary of phases in the generated tasks."""
        phases: Dict[str, Dict[str, Any]] = {}

        for task in tasks:
            phase = (
                task.source_context.get("phase", "Unknown")
                if task.source_context
                else "Unknown"
            )
            phase_order = (
                task.source_context.get("phase_order", 0) if task.source_context else 0
            )

            if phase not in phases:
                phases[phase] = {
                    "order": phase_order,
                    "task_count": 0,
                    "estimated_hours": 0,
                    "task_names": [],
                }

            phases[phase]["task_count"] += 1
            phases[phase]["estimated_hours"] += task.estimated_hours
            phases[phase]["task_names"].append(task.name)

        # Sort by order
        sorted_phases = dict(sorted(phases.items(), key=lambda x: x[1]["order"]))

        return sorted_phases
