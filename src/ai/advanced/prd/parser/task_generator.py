"""
Task generation functionality for PRD parser.

This module handles the creation and enhancement of detailed tasks
from PRD requirements.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.ai.providers.llm_abstraction import LLMAbstraction
from src.core.models import Priority, Task, TaskStatus

logger = logging.getLogger(__name__)


class TaskGenerator:
    """Handles task generation and enhancement from PRD requirements."""

    def __init__(self, llm_provider: LLMAbstraction):
        """
        Initialize task generator.

        Parameters
        ----------
        llm_provider : LLMAbstraction
            LLM provider for AI-powered task generation
        """
        self.llm_provider = llm_provider

    async def create_detailed_tasks(
        self,
        task_list: List[Dict[str, Any]],
        project_context: Dict[str, Any],
        constraints: Any,  # ProjectConstraints
    ) -> List[Task]:
        """
        Create detailed Task objects from raw task data.

        Parameters
        ----------
        task_list : List[Dict[str, Any]]
            Raw task data from hierarchy generation
        project_context : Dict[str, Any]
            Project context for task enhancement
        constraints : ProjectConstraints
            Project constraints affecting task creation

        Returns
        -------
        List[Task]
            List of detailed Task objects
        """
        tasks = []
        for task_data in task_list:
            try:
                task = await self._generate_detailed_task(
                    task_data, project_context, constraints
                )
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating task: {e}")
                continue
        return tasks

    async def _generate_detailed_task(
        self,
        task_data: Dict[str, Any],
        project_context: Dict[str, Any],
        constraints: Any,
    ) -> Task:
        """Generate a detailed task with all attributes."""
        # Extract basic info
        task_info = self._extract_task_info(task_data)

        # Enhance with AI if needed
        if task_info.get("needs_enhancement", True):
            task_info = await self._enhance_task_with_ai(task_info, project_context)

        # Create task object
        task = Task(
            title=task_info["title"],
            description=task_info["description"],
            status=TaskStatus.TODO,
            priority=self._determine_priority(task_info, project_context),
            estimated_effort=task_info.get("estimated_hours", 8),
            labels=task_info.get("labels", []),
            acceptance_criteria=task_info.get("acceptance_criteria", []),
            subtasks=task_info.get("subtasks", []),
            due_date=task_info.get("due_date"),
            dependencies=task_info.get("dependencies", []),
            assigned_to=None,  # Will be assigned by scheduler
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        return task

    def _extract_task_info(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract task information from raw data.

        Parameters
        ----------
        task_data : Dict[str, Any]
            Raw task data

        Returns
        -------
        Dict[str, Any]
            Extracted task information
        """
        return {
            "id": task_data.get("id", ""),
            "title": task_data.get("title", ""),
            "description": task_data.get("description", ""),
            "type": task_data.get("type", "implementation"),
            "parent_id": task_data.get("parent_id"),
            "estimated_hours": task_data.get("estimated_hours", 8),
            "labels": task_data.get("labels", []),
            "dependencies": task_data.get("dependencies", []),
            "needs_enhancement": task_data.get("needs_enhancement", True),
        }

    async def _enhance_task_with_ai(
        self,
        task_info: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enhance task details using AI.

        Parameters
        ----------
        task_info : Dict[str, Any]
            Basic task information
        project_context : Dict[str, Any]
            Project context for enhancement

        Returns
        -------
        Dict[str, Any]
            Enhanced task information
        """
        prompt = f"""
        Enhance this task with detailed information:

        Task: {task_info['title']}
        Type: {task_info['type']}
        Initial Description: {task_info.get('description', '')}

        Project Context:
        - Objective: {project_context.get('objective', 'N/A')}
        - Tech Stack: {project_context.get('tech_stack', [])}
        - Team Size: {project_context.get('team_size', 3)}

        Generate:
        1. Detailed description (2-3 sentences)
        2. Acceptance criteria (3-5 items)
        3. Implementation notes
        4. Estimated effort in hours
        5. Risk factors

        Return as JSON.
        """

        # Create a simple context object with max_tokens
        class SimpleContext:
            max_tokens = 2000

        try:
            result = await self.llm_provider.analyze(
                prompt,
                context=SimpleContext(),
            )

            enhanced = result.parsed_data

            # Merge enhancements
            task_info["description"] = enhanced.get(
                "description", task_info["description"]
            )
            task_info["acceptance_criteria"] = enhanced.get("acceptance_criteria", [])
            task_info["implementation_notes"] = enhanced.get("implementation_notes", "")
            task_info["estimated_hours"] = enhanced.get(
                "estimated_hours", task_info["estimated_hours"]
            )
            task_info["risk_factors"] = enhanced.get("risk_factors", [])

        except Exception as e:
            logger.warning(f"AI enhancement failed: {e}")

        return task_info

    def _determine_priority(
        self,
        task_info: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> Priority:
        """
        Determine task priority based on various factors.

        Parameters
        ----------
        task_info : Dict[str, Any]
            Task information
        project_context : Dict[str, Any]
            Project context

        Returns
        -------
        Priority
            Calculated priority
        """
        # Priority scoring
        score = 0

        # Task type weights
        type_weights = {
            "security": 5,
            "infrastructure": 4,
            "core": 4,
            "feature": 3,
            "testing": 2,
            "documentation": 1,
        }

        task_type = task_info.get("type", "feature")
        score += type_weights.get(task_type, 2)

        # Dependencies increase priority
        if task_info.get("dependencies"):
            score += len(task_info["dependencies"])

        # Critical path tasks
        if task_info.get("is_critical_path"):
            score += 3

        # Map score to priority
        if score >= 8:
            return Priority.CRITICAL
        elif score >= 6:
            return Priority.HIGH
        elif score >= 4:
            return Priority.MEDIUM
        else:
            return Priority.LOW
