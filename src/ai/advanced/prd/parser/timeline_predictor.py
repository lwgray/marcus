"""
Timeline prediction functionality.

This module handles project timeline estimation and milestone planning.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.ai.providers.llm_abstraction import LLMAbstraction

from .models import ProjectConstraints

logger = logging.getLogger(__name__)


class TimelinePredictor:
    """Handles timeline prediction and milestone planning."""

    def __init__(self, llm_provider: LLMAbstraction):
        """Initialize timeline predictor."""
        self.llm_provider = llm_provider

    async def predict_timeline(
        self,
        tasks: List[Any],  # List[Task]
        dependencies: List[Dict[str, Any]],
        constraints: ProjectConstraints,
    ) -> Dict[str, Any]:
        """
        Predict project timeline based on tasks and dependencies.

        Returns
        -------
        Dict[str, Any]
            Timeline predictions including milestones and critical path
        """
        logger.info("Predicting project timeline")

        # Calculate basic timeline
        total_effort = sum(getattr(task, "estimated_effort", 8) for task in tasks)

        # Calculate duration based on team size
        team_capacity = constraints.team_size * 40  # hours per week
        weeks_needed = total_effort / team_capacity

        # Add buffer for dependencies and coordination
        buffer_factor = 1.2 + (0.1 * len(dependencies) / max(len(tasks), 1))
        adjusted_weeks = weeks_needed * buffer_factor

        # Calculate end date
        start_date = datetime.now()
        end_date = start_date + timedelta(weeks=adjusted_weeks)

        # Generate milestones
        milestones = await self._calculate_milestone_dates(tasks, start_date, end_date)

        # Identify critical path
        critical_path = await self._identify_critical_path_tasks(tasks, dependencies)

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "duration_weeks": round(adjusted_weeks, 1),
            "total_effort_hours": total_effort,
            "milestones": milestones,
            "critical_path": critical_path,
            "confidence": 0.7,  # Timeline confidence
        }

    async def _calculate_milestone_dates(
        self,
        tasks: List[Any],
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Calculate milestone dates."""
        duration = end_date - start_date

        milestones = [
            {
                "name": "Project Kickoff",
                "date": start_date.isoformat(),
                "deliverables": ["Project setup", "Team onboarding"],
            },
            {
                "name": "Design Complete",
                "date": (start_date + duration * 0.2).isoformat(),
                "deliverables": ["Architecture design", "API specifications"],
            },
            {
                "name": "MVP Complete",
                "date": (start_date + duration * 0.6).isoformat(),
                "deliverables": ["Core features", "Basic testing"],
            },
            {
                "name": "Beta Release",
                "date": (start_date + duration * 0.8).isoformat(),
                "deliverables": ["Full features", "Integration testing"],
            },
            {
                "name": "Final Release",
                "date": end_date.isoformat(),
                "deliverables": ["Production ready", "Documentation"],
            },
        ]

        return milestones

    async def _identify_critical_path_tasks(
        self,
        tasks: List[Any],
        dependencies: List[Dict[str, Any]],
    ) -> List[str]:
        """Identify tasks on the critical path."""
        # Simple critical path identification
        # In reality, this would use CPM algorithm
        critical_tasks = []

        # Tasks with many dependencies are often critical
        task_ids = [getattr(t, "id", f"task-{i}") for i, t in enumerate(tasks)]

        for task_id in task_ids:
            dep_count = sum(
                1
                for d in dependencies
                if d.get("to_task") == task_id or d.get("from_task") == task_id
            )

            if dep_count >= 2:
                critical_tasks.append(task_id)

        return critical_tasks[:5]  # Top 5 critical tasks
