"""
Risk assessment functionality.

This module handles risk analysis and mitigation strategy generation.
"""

import logging
from typing import Any, Dict, List

from src.ai.providers.llm_abstraction import LLMAbstraction

from .models import PRDAnalysis, ProjectConstraints

logger = logging.getLogger(__name__)


class RiskAssessor:
    """Handles risk assessment and mitigation planning."""

    def __init__(self, llm_provider: LLMAbstraction):
        """
        Initialize risk assessor.

        Parameters
        ----------
        llm_provider : LLMAbstraction
            LLM provider for AI-powered analysis
        """
        self.llm_provider = llm_provider

    async def assess_implementation_risks(
        self,
        analysis: PRDAnalysis,
        tasks: List[Any],  # List[Task]
        constraints: ProjectConstraints,
    ) -> Dict[str, Any]:
        """
        Assess implementation risks for the project.

        Parameters
        ----------
        analysis : PRDAnalysis
            PRD analysis results
        tasks : List[Task]
            Generated tasks
        constraints : ProjectConstraints
            Project constraints

        Returns
        -------
        Dict[str, Any]
            Risk assessment results
        """
        logger.info("Assessing implementation risks")

        # Analyze different risk categories
        complexity_risks = await self._analyze_complexity_risks(analysis, tasks)
        constraint_risks = await self._analyze_constraint_risks(analysis, constraints)
        resource_risks = self._analyze_resource_risks(tasks, constraints)

        # Generate mitigation strategies
        mitigation_strategies = await self._generate_mitigation_strategies(
            complexity_risks + constraint_risks + resource_risks
        )

        return {
            "overall_risk_level": self._calculate_overall_risk_level(
                complexity_risks, constraint_risks, resource_risks
            ),
            "complexity_risks": complexity_risks,
            "constraint_risks": constraint_risks,
            "resource_risks": resource_risks,
            "mitigation_strategies": mitigation_strategies,
            "risk_factors": analysis.risk_factors,
        }

    async def _analyze_complexity_risks(
        self,
        analysis: PRDAnalysis,
        tasks: List[Any],
    ) -> List[Dict[str, Any]]:
        """Analyze risks from technical complexity."""
        risks = []

        complexity = analysis.complexity_assessment
        if complexity.get("technical_complexity", 0) > 7:
            risks.append(
                {
                    "type": "technical",
                    "severity": "high",
                    "description": "High technical complexity may lead to delays",
                    "probability": 0.7,
                    "impact": "schedule",
                }
            )

        # Check for complex integrations
        integration_tasks = [
            t
            for t in tasks
            if "integration" in t.title.lower() or "integrate" in t.description.lower()
        ]

        if len(integration_tasks) > 3:
            risks.append(
                {
                    "type": "integration",
                    "severity": "medium",
                    "description": "Multiple integration points increase failure risk",
                    "probability": 0.6,
                    "impact": "quality",
                }
            )

        return risks

    async def _analyze_constraint_risks(
        self,
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
    ) -> List[Dict[str, Any]]:
        """Analyze risks from project constraints."""
        prompt = f"""
        Analyze risks from these project constraints:

        Technical Constraints: {analysis.technical_constraints}
        Deadline: {constraints.deadline}
        Team Size: {constraints.team_size}
        Available Skills: {constraints.available_skills}

        Identify:
        1. Resource constraint risks
        2. Timeline risks
        3. Skill gap risks
        4. Technology risks

        Return as JSON list with type, severity, description, probability.
        """

        # Create a simple context object with max_tokens
        class SimpleContext:
            max_tokens = 2000

        try:
            result = await self.llm_provider.analyze(
                prompt,
                context=SimpleContext(),
            )

            return result.parsed_data if isinstance(result.parsed_data, list) else []

        except Exception as e:
            logger.error(f"Constraint risk analysis failed: {e}")
            return []

    def _analyze_resource_risks(
        self,
        tasks: List[Any],
        constraints: ProjectConstraints,
    ) -> List[Dict[str, Any]]:
        """Analyze resource-related risks."""
        risks = []

        # Calculate total effort
        total_effort = sum(getattr(task, "estimated_effort", 8) for task in tasks)

        # Team capacity
        team_capacity = constraints.team_size * 40 * 4  # hours per month

        if constraints.deadline:
            # Calculate available time
            from datetime import datetime

            weeks_available = max(1, (constraints.deadline - datetime.now()).days / 7)
            available_hours = constraints.team_size * 40 * weeks_available

            if total_effort > available_hours * 0.8:
                risks.append(
                    {
                        "type": "resource",
                        "severity": "high",
                        "description": "Insufficient time for estimated effort",
                        "probability": 0.8,
                        "impact": "schedule",
                    }
                )

        return risks

    async def _generate_mitigation_strategies(
        self,
        risks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate mitigation strategies for identified risks."""
        strategies = []

        for risk in risks:
            if risk["severity"] == "high":
                strategy = {
                    "risk_type": risk["type"],
                    "strategy": self._get_mitigation_strategy(risk),
                    "priority": "immediate",
                }
                strategies.append(strategy)

        return strategies

    def _get_mitigation_strategy(self, risk: Dict[str, Any]) -> str:
        """Get appropriate mitigation strategy for risk type."""
        strategies = {
            "technical": "Break down complex components, add spikes for unknowns",
            "integration": "Create integration tests early, use mocks",
            "resource": "Prioritize MVP features, consider extending timeline",
            "skill": "Plan training time, consider external expertise",
        }

        return strategies.get(risk["type"], "Monitor closely and adjust plan as needed")

    def _calculate_overall_risk_level(
        self,
        complexity_risks: List[Dict[str, Any]],
        constraint_risks: List[Dict[str, Any]],
        resource_risks: List[Dict[str, Any]],
    ) -> str:
        """Calculate overall project risk level."""
        all_risks = complexity_risks + constraint_risks + resource_risks

        high_risks = sum(1 for r in all_risks if r.get("severity") == "high")
        medium_risks = sum(1 for r in all_risks if r.get("severity") == "medium")

        if high_risks >= 2:
            return "high"
        elif high_risks >= 1 or medium_risks >= 3:
            return "medium"
        else:
            return "low"
