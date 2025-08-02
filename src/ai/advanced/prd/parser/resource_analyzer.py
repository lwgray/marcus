"""
Resource analysis functionality.

This module handles resource requirement analysis and capacity planning.
"""

import logging
from typing import Any, Dict, List

from src.ai.providers.llm_abstraction import LLMAbstraction

from .models import PRDAnalysis, ProjectConstraints

logger = logging.getLogger(__name__)


class ResourceAnalyzer:
    """Handles resource requirement analysis."""

    def __init__(self, llm_provider: LLMAbstraction):
        """Initialize resource analyzer."""
        self.llm_provider = llm_provider

    async def analyze_resource_requirements(
        self,
        analysis: PRDAnalysis,
        tasks: List[Any],  # List[Task]
        constraints: ProjectConstraints,
    ) -> Dict[str, Any]:
        """
        Analyze resource requirements for the project.

        Returns
        -------
        Dict[str, Any]
            Resource requirements including skills, tools, and team composition
        """
        logger.info("Analyzing resource requirements")

        # Analyze skill requirements
        skill_requirements = await self._analyze_skill_requirements(analysis, tasks)

        # Analyze technology requirements
        tech_requirements = await self._analyze_tech_requirements(analysis)

        # Analyze external dependencies
        external_deps = await self._analyze_external_dependencies(analysis)

        # Calculate optimal team size
        optimal_team = self._calculate_optimal_team_size(tasks, constraints)

        # Identify specialized roles
        specialized_roles = await self._identify_specialized_roles(analysis, tasks)

        return {
            "skill_requirements": skill_requirements,
            "technology_requirements": tech_requirements,
            "external_dependencies": external_deps,
            "optimal_team_size": optimal_team,
            "specialized_roles": specialized_roles,
            "estimated_budget": self._estimate_budget(optimal_team, len(tasks)),
        }

    async def _analyze_skill_requirements(
        self,
        analysis: PRDAnalysis,
        tasks: List[Any],
    ) -> List[Dict[str, Any]]:
        """Analyze required skills for the project."""
        skills = []

        # Extract skills from task types
        task_types = set()
        for task in tasks:
            task_type = getattr(task, "type", "general")
            task_types.add(task_type)

        # Map task types to skills
        skill_map = {
            "design": ["UI/UX Design", "System Architecture"],
            "implementation": ["Programming", "Database Design"],
            "testing": ["Test Automation", "QA"],
            "infrastructure": ["DevOps", "Cloud Architecture"],
            "documentation": ["Technical Writing"],
        }

        for task_type in task_types:
            for skill in skill_map.get(task_type, ["General Development"]):
                skills.append(
                    {
                        "skill": skill,
                        "level": "intermediate",
                        "required_for": task_type,
                    }
                )

        return skills

    async def _analyze_tech_requirements(
        self,
        analysis: PRDAnalysis,
    ) -> List[str]:
        """Analyze technology requirements."""
        tech_reqs = []

        # From technical constraints
        tech_reqs.extend(analysis.technical_constraints)

        # Common requirements based on project type
        if any("api" in obj.lower() for obj in analysis.business_objectives):
            tech_reqs.append("API Development Framework")

        if any(
            "web" in req.get("description", "").lower()
            for req in analysis.functional_requirements
        ):
            tech_reqs.append("Web Framework")

        return list(set(tech_reqs))

    async def _analyze_external_dependencies(self, analysis: PRDAnalysis) -> List[str]:
        """Analyze external dependencies."""
        deps = []

        # Check for third-party integrations
        for req in analysis.functional_requirements:
            desc = req.get("description", "").lower()
            if "integrate" in desc or "third-party" in desc:
                deps.append("Third-party API integrations")

        return deps

    def _calculate_optimal_team_size(
        self,
        tasks: List[Any],
        constraints: ProjectConstraints,
    ) -> int:
        """Calculate optimal team size."""
        total_effort = sum(getattr(task, "estimated_effort", 8) for task in tasks)

        # If deadline exists, calculate based on that
        if constraints.deadline:
            from datetime import datetime

            weeks = max(1, (constraints.deadline - datetime.now()).days / 7)
            hours_needed_per_week = total_effort / weeks
            optimal_size = int(hours_needed_per_week / 30)  # 30 productive hours/week
        else:
            # Default calculation
            optimal_size = min(max(3, len(tasks) // 10), 10)  # Max team size

        return optimal_size

    async def _identify_specialized_roles(
        self,
        analysis: PRDAnalysis,
        tasks: List[Any],
    ) -> List[Dict[str, str]]:
        """Identify specialized roles needed."""
        roles = [
            {
                "role": "Tech Lead",
                "count": 1,
                "responsibility": "Architecture and technical decisions",
            },
            {
                "role": "Backend Developer",
                "count": 2,
                "responsibility": "Server-side implementation",
            },
        ]

        # Add roles based on requirements
        if any(
            "ui" in req.get("description", "").lower()
            for req in analysis.functional_requirements
        ):
            roles.append(
                {
                    "role": "Frontend Developer",
                    "count": 1,
                    "responsibility": "User interface implementation",
                }
            )

        if any(
            "security" in constraint.lower()
            for constraint in analysis.technical_constraints
        ):
            roles.append(
                {
                    "role": "Security Engineer",
                    "count": 1,
                    "responsibility": "Security implementation and review",
                }
            )

        return roles

    def _estimate_budget(self, team_size: int, task_count: int) -> Dict[str, float]:
        """Estimate project budget."""
        # Simple estimation
        avg_rate = 100  # $/hour
        hours_per_task = 12  # average

        labor_cost = team_size * task_count * hours_per_task * avg_rate

        return {
            "labor": labor_cost,
            "infrastructure": labor_cost * 0.1,
            "tools": labor_cost * 0.05,
            "contingency": labor_cost * 0.15,
            "total": labor_cost * 1.3,
        }
