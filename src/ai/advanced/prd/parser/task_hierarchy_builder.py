"""
Task hierarchy building functionality.

This module handles the creation of hierarchical task structures from
PRD analysis results.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.ai.providers.llm_abstraction import LLMAbstraction

from .models import PRDAnalysis, ProjectConstraints

logger = logging.getLogger(__name__)


class TaskHierarchyBuilder:
    """Builds hierarchical task structures from PRD analysis."""

    def __init__(self, llm_provider: LLMAbstraction):
        """
        Initialize task hierarchy builder.

        Parameters
        ----------
        llm_provider : LLMAbstraction
            LLM provider for AI-powered task generation
        """
        self.llm_provider = llm_provider

    async def generate_task_hierarchy(
        self,
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
        """
        Generate hierarchical task structure from PRD analysis.

        Parameters
        ----------
        analysis : PRDAnalysis
            PRD analysis results
        constraints : ProjectConstraints
            Project constraints

        Returns
        -------
        Tuple[List[Dict[str, Any]], Dict[str, List[str]]]
            Task list and hierarchy mapping
        """
        logger.info("Generating task hierarchy from PRD analysis")

        task_list = []
        hierarchy = {}

        # Generate epics from functional requirements
        for idx, req in enumerate(analysis.functional_requirements):
            if self._should_skip_requirement(req, constraints):
                continue

            epic = await self._create_epic_from_requirement(req, idx, constraints)

            if epic:
                task_list.append(epic)

                # Break down epic into tasks
                subtasks = await self._break_down_epic(epic, analysis, constraints)

                task_list.extend(subtasks)
                hierarchy[epic["id"]] = [task["id"] for task in subtasks]

        # Add NFR tasks
        nfr_tasks = await self._create_nfr_tasks(
            analysis.non_functional_requirements, constraints
        )
        task_list.extend(nfr_tasks)

        # Add infrastructure tasks if needed
        if self._needs_infrastructure_setup(analysis, constraints):
            infra_tasks = await self._create_infrastructure_tasks(analysis, constraints)
            task_list.extend(infra_tasks)

        return task_list, hierarchy

    async def _create_epic_from_requirement(
        self,
        requirement: Dict[str, Any],
        index: int,
        constraints: ProjectConstraints,
    ) -> Optional[Dict[str, Any]]:
        """Create an epic from a functional requirement."""
        epic_id = f"EPIC-{index + 1}"

        # Check if should skip based on deployment target
        if self._should_skip_epic(epic_id, constraints.deployment_target):
            return None

        epic = {
            "id": epic_id,
            "title": f"Implement {requirement.get('description', 'Feature')}",
            "description": requirement.get("description", ""),
            "type": "epic",
            "priority": requirement.get("priority", "medium"),
            "complexity": requirement.get("complexity", "medium"),
            "labels": ["epic", requirement.get("category", "feature")],
            "estimated_hours": 0,  # Will be sum of subtasks
        }

        return epic

    async def _break_down_epic(
        self,
        epic: Dict[str, Any],
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
    ) -> List[Dict[str, Any]]:
        """
        Break down an epic into smaller tasks.

        Parameters
        ----------
        epic : Dict[str, Any]
            Epic to break down
        analysis : PRDAnalysis
            PRD analysis for context
        constraints : ProjectConstraints
            Project constraints

        Returns
        -------
        List[Dict[str, Any]]
            List of subtasks
        """
        prompt = f"""
        Break down this epic into specific development tasks:

        Epic: {epic['title']}
        Description: {epic['description']}
        Complexity: {epic['complexity']}

        Context:
        - Project Size: {constraints.deployment_target}
        - Team Size: {constraints.team_size}
        - Tech Constraints: {constraints.technology_constraints}

        Generate 3-8 specific tasks that cover:
        1. Design/Architecture (if needed)
        2. Implementation
        3. Testing
        4. Documentation (if needed)
        5. Integration (if needed)

        For each task provide:
        - title
        - description
        - type (design/implementation/testing/documentation/integration)
        - estimated_hours
        - dependencies (task IDs if any)

        Return as JSON list.
        """

        # Create a simple context object with max_tokens
        class SimpleContext:
            max_tokens = 2000

        try:
            result = await self.llm_provider.analyze(
                prompt,
                context=SimpleContext(),
            )

            tasks = result.parsed_data
            if not isinstance(tasks, list):
                tasks = tasks.get("tasks", [])

            # Process and validate tasks
            processed_tasks = []
            for idx, task in enumerate(tasks):
                task_id = f"{epic['id']}-TASK-{idx + 1}"

                if self._should_skip_task(
                    task.get("type", "implementation"), constraints.deployment_target
                ):
                    continue

                processed_task = {
                    "id": task_id,
                    "parent_id": epic["id"],
                    "title": task.get("title", ""),
                    "description": task.get("description", ""),
                    "type": task.get("type", "implementation"),
                    "estimated_hours": task.get("estimated_hours", 8),
                    "dependencies": task.get("dependencies", []),
                    "labels": [
                        task.get("type", "implementation"),
                        epic.get("category", "feature"),
                    ],
                }

                processed_tasks.append(processed_task)

            return processed_tasks

        except Exception as e:
            logger.error(f"Failed to break down epic: {e}")
            # Return minimal task breakdown on failure
            return [
                {
                    "id": f"{epic['id']}-TASK-1",
                    "parent_id": epic["id"],
                    "title": f"Implement {epic['title']}",
                    "description": "Main implementation task",
                    "type": "implementation",
                    "estimated_hours": 16,
                    "dependencies": [],
                    "labels": ["implementation"],
                }
            ]

    async def _create_nfr_tasks(
        self,
        nfrs: List[Dict[str, Any]],
        constraints: ProjectConstraints,
    ) -> List[Dict[str, Any]]:
        """Create tasks from non-functional requirements."""
        tasks = []

        for idx, nfr in enumerate(nfrs):
            if self._should_skip_nfr(nfr, constraints):
                continue

            task = {
                "id": f"NFR-TASK-{idx + 1}",
                "title": f"Implement {nfr.get('category', 'NFR')}: {nfr.get('description', '')}",
                "description": nfr.get("description", ""),
                "type": "nfr",
                "category": nfr.get("category", "quality"),
                "estimated_hours": 8,
                "labels": ["nfr", nfr.get("category", "quality")],
                "metric": nfr.get("metric", ""),
                "target": nfr.get("target", ""),
            }

            tasks.append(task)

        return tasks

    async def _create_infrastructure_tasks(
        self,
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
    ) -> List[Dict[str, Any]]:
        """Create infrastructure setup tasks."""
        tasks = []

        # Basic infrastructure tasks
        infra_needs = [
            {
                "title": "Set up development environment",
                "type": "infrastructure",
                "hours": 4,
                "deployment": ["local", "dev"],
            },
            {
                "title": "Configure CI/CD pipeline",
                "type": "infrastructure",
                "hours": 8,
                "deployment": ["dev", "prod", "remote"],
            },
            {
                "title": "Set up monitoring and logging",
                "type": "infrastructure",
                "hours": 6,
                "deployment": ["prod", "remote"],
            },
            {
                "title": "Configure security and access controls",
                "type": "infrastructure",
                "hours": 8,
                "deployment": ["prod", "remote"],
            },
        ]

        for idx, infra in enumerate(infra_needs):
            if constraints.deployment_target not in infra["deployment"]:
                continue

            task = {
                "id": f"INFRA-{idx + 1}",
                "title": infra["title"],
                "description": f"Infrastructure task for {constraints.deployment_target} deployment",
                "type": "infrastructure",
                "estimated_hours": infra["hours"],
                "labels": ["infrastructure", "setup"],
            }

            tasks.append(task)

        return tasks

    def _should_skip_requirement(
        self,
        requirement: Dict[str, Any],
        constraints: ProjectConstraints,
    ) -> bool:
        """Check if requirement should be skipped based on constraints."""
        # Skip low priority requirements for MVP/small projects
        if constraints.deployment_target == "local":
            return requirement.get("priority") == "low"

        return False

    def _should_skip_epic(self, epic_id: str, deployment_target: str) -> bool:
        """Check if epic should be skipped based on deployment target."""
        # Skip certain epics for local/MVP deployments
        skip_patterns = {
            "local": ["EPIC-[8-9]\\d+", "advanced", "enterprise"],
            "dev": ["EPIC-9\\d+", "enterprise"],
        }

        patterns = skip_patterns.get(deployment_target, [])
        for pattern in patterns:
            if re.match(pattern, epic_id):
                return True

        return False

    def _should_skip_task(self, task_type: str, deployment_target: str) -> bool:
        """Check if task type should be skipped."""
        skip_map = {
            "local": ["monitoring", "analytics", "reporting"],
            "dev": ["analytics"],
        }

        skip_types = skip_map.get(deployment_target, [])
        return task_type in skip_types

    def _should_skip_nfr(
        self,
        nfr: Dict[str, Any],
        constraints: ProjectConstraints,
    ) -> bool:
        """Check if NFR should be skipped."""
        if constraints.deployment_target == "local":
            # Skip advanced NFRs for local deployment
            skip_categories = ["scalability", "high-availability", "compliance"]
            return nfr.get("category") in skip_categories

        return False

    def _needs_infrastructure_setup(
        self,
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
    ) -> bool:
        """Check if project needs infrastructure setup tasks."""
        # Always need some infrastructure except for pure local
        return (
            constraints.deployment_target != "local"
            or len(analysis.technical_constraints) > 2
        )
