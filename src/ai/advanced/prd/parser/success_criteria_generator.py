"""
Success criteria generation functionality.

This module handles the generation of project success criteria and metrics.
"""

import logging
from typing import Any, Dict, List

from src.ai.providers.llm_abstraction import LLMAbstraction

from .models import PRDAnalysis

logger = logging.getLogger(__name__)


class SuccessCriteriaGenerator:
    """Handles success criteria generation."""

    def __init__(self, llm_provider: LLMAbstraction):
        """Initialize success criteria generator."""
        self.llm_provider = llm_provider

    async def generate_success_criteria(
        self,
        analysis: PRDAnalysis,
        tasks: List[Any],  # List[Task]
    ) -> List[str]:
        """
        Generate success criteria for the project.

        Parameters
        ----------
        analysis : PRDAnalysis
            PRD analysis results
        tasks : List[Task]
            Generated tasks

        Returns
        -------
        List[str]
            List of measurable success criteria
        """
        logger.info("Generating project success criteria")

        # Start with success metrics from analysis
        criteria = list(analysis.success_metrics)

        # Generate additional criteria based on objectives
        prompt = f"""
        Generate measurable success criteria for this project:

        Business Objectives:
        {analysis.business_objectives}

        Functional Requirements Summary:
        {len(analysis.functional_requirements)} core features

        Non-Functional Requirements:
        {[nfr.get('category') for nfr in analysis.non_functional_requirements]}

        Generate 5-8 specific, measurable success criteria that cover:
        1. Functional completeness
        2. Performance targets
        3. Quality metrics
        4. User satisfaction
        5. Business impact

        Each criterion should be SMART (Specific, Measurable, Achievable, Relevant, Time-bound).

        Return as JSON list of strings.
        """

        # Create a simple context object with max_tokens
        class SimpleContext:
            max_tokens = 2000

        try:
            result = await self.llm_provider.analyze(
                prompt,
                context=SimpleContext(),
            )

            generated_criteria = result.parsed_data
            if isinstance(generated_criteria, list):
                criteria.extend(generated_criteria)

        except Exception as e:
            logger.error(f"Failed to generate additional criteria: {e}")

        # Add task-based criteria
        criteria.extend(self._generate_task_based_criteria(tasks))

        # Remove duplicates and return
        return list(dict.fromkeys(criteria))[:10]  # Max 10 criteria

    def _generate_task_based_criteria(self, tasks: List[Any]) -> List[str]:
        """Generate criteria based on task analysis."""
        criteria = []

        # Completion criteria
        total_tasks = len(tasks)
        criteria.append(f"Successfully complete all {total_tasks} identified tasks")

        # Quality criteria
        test_tasks = sum(
            1
            for task in tasks
            if "test" in task.title.lower() or getattr(task, "type", "") == "testing"
        )

        if test_tasks > 0:
            criteria.append(
                f"Achieve 90% test coverage with all {test_tasks} test suites passing"
            )

        # Performance criteria
        perf_tasks = sum(
            1
            for task in tasks
            if "performance" in task.title.lower() or "optimize" in task.title.lower()
        )

        if perf_tasks > 0:
            criteria.append("Meet all performance benchmarks defined in NFRs")

        return criteria
