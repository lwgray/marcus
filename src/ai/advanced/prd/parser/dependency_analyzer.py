"""
Dependency analysis functionality.

This module handles the inference and analysis of task dependencies.
"""

import logging
from typing import Any, Dict, List

from src.ai.providers.llm_abstraction import LLMAbstraction
from src.intelligence.dependency_inferer_hybrid import HybridDependencyInferer

from .models import PRDAnalysis, ProjectConstraints

logger = logging.getLogger(__name__)


class DependencyAnalyzer:
    """Handles dependency analysis and inference for tasks."""

    def __init__(
        self,
        llm_provider: LLMAbstraction,
        dependency_inferer: HybridDependencyInferer,
    ):
        """
        Initialize dependency analyzer.

        Parameters
        ----------
        llm_provider : LLMAbstraction
            LLM provider for AI-powered analysis
        dependency_inferer : HybridDependencyInferer
            Hybrid dependency inference engine
        """
        self.llm_provider = llm_provider
        self.dependency_inferer = dependency_inferer

    async def infer_smart_dependencies(
        self,
        tasks: List[Any],  # List[Task]
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
    ) -> List[Dict[str, Any]]:
        """
        Infer smart dependencies between tasks.

        Parameters
        ----------
        tasks : List[Task]
            List of tasks to analyze
        analysis : PRDAnalysis
            PRD analysis for context
        constraints : ProjectConstraints
            Project constraints

        Returns
        -------
        List[Dict[str, Any]]
            List of dependency relationships
        """
        logger.info(f"Inferring dependencies for {len(tasks)} tasks")

        # Use hybrid dependency inferer
        dependencies = await self.dependency_inferer.infer_dependencies(
            [
                {
                    "id": task.id if hasattr(task, "id") else f"task-{idx}",
                    "title": task.title,
                    "description": task.description,
                    "type": getattr(task, "type", "implementation"),
                    "labels": task.labels,
                }
                for idx, task in enumerate(tasks)
            ]
        )

        # Add PRD-specific dependencies
        prd_dependencies = await self._add_prd_specific_dependencies(tasks, analysis)
        dependencies.extend(prd_dependencies)

        return dependencies

    async def _add_prd_specific_dependencies(
        self,
        tasks: List[Any],
        analysis: PRDAnalysis,
    ) -> List[Dict[str, Any]]:
        """Add dependencies based on PRD analysis insights."""
        prd_deps = []

        # Add dependencies based on technical constraints
        for constraint in analysis.technical_constraints:
            # Find tasks that might be affected by constraints
            related_tasks = [
                task
                for task in tasks
                if constraint.lower() in task.title.lower()
                or constraint.lower() in task.description.lower()
            ]

            # Create dependencies between related tasks
            for i in range(len(related_tasks) - 1):
                dep = {
                    "from_task": getattr(related_tasks[i], "id", f"task-{i}"),
                    "to_task": getattr(related_tasks[i + 1], "id", f"task-{i + 1}"),
                    "type": "technical_constraint",
                    "reason": f"Shared constraint: {constraint}",
                }
                prd_deps.append(dep)

        return prd_deps
