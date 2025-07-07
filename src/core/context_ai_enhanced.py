"""
AI-Enhanced Context System

Extends the base Context system with AI-powered dependency inference
using LLMs for more intelligent and flexible dependency detection.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.context import Context, DependentTask
from src.core.models import Task
from src.core.resilience import RetryConfig, with_fallback, with_retry
from src.integrations.ai_analysis_engine import AIAnalysisEngine

logger = logging.getLogger(__name__)


class ContextAIEnhanced(Context):
    """
    Enhanced Context system with AI-powered dependency inference.

    Uses LLMs to intelligently detect dependencies between tasks instead
    of relying on hardcoded patterns.
    """

    def __init__(self, *args, ai_engine: Optional[AIAnalysisEngine] = None, **kwargs):
        """
        Initialize AI-enhanced context system.

        Args:
            ai_engine: Optional AI analysis engine for dependency inference
            *args, **kwargs: Arguments passed to base Context class
        """
        super().__init__(*args, **kwargs)
        self.ai_engine = ai_engine or AIAnalysisEngine()
        self.ai_inference_enabled = True

    async def analyze_dependencies(
        self, tasks: List[Task], infer_implicit: bool = True
    ) -> Dict[str, List[str]]:
        """
        Analyze task list to identify dependencies using AI when available.

        Falls back to pattern-based inference if AI is unavailable or disabled.

        Args:
            tasks: List of all tasks
            infer_implicit: Whether to infer implicit dependencies (default: True)

        Returns:
            Mapping of task_id to list of dependent task IDs
        """
        # First, get explicit dependencies from base implementation
        dependency_map = await super().analyze_dependencies(tasks, infer_implicit=False)

        # Then, use AI for implicit dependency inference if enabled
        if infer_implicit and self.ai_inference_enabled and self.ai_engine:
            try:
                ai_dependencies = await self._infer_dependencies_with_ai(tasks)

                # Merge AI-inferred dependencies
                for task_id, dependents in ai_dependencies.items():
                    if task_id not in dependency_map:
                        dependency_map[task_id] = []

                    for dependent_id in dependents:
                        if dependent_id not in dependency_map[task_id]:
                            dependency_map[task_id].append(dependent_id)
                            logger.info(
                                f"AI inferred: Task {dependent_id} depends on {task_id}"
                            )

            except Exception as e:
                logger.warning(
                    f"AI dependency inference failed, using pattern-based fallback: {e}"
                )
                # Fall back to pattern-based inference
                return await super().analyze_dependencies(tasks, infer_implicit=True)

        return dependency_map

    @with_retry(RetryConfig(max_attempts=2, base_delay=1.0))
    @with_fallback(lambda self, tasks: self._fallback_inference(tasks))
    async def _infer_dependencies_with_ai(
        self, tasks: List[Task]
    ) -> Dict[str, List[str]]:
        """
        Use AI to infer task dependencies intelligently.

        Args:
            tasks: List of tasks to analyze

        Returns:
            Mapping of task_id to list of dependent task IDs
        """
        # Prepare task information for AI analysis
        task_info = []
        for task in tasks:
            task_info.append(
                {
                    "id": task.id,
                    "name": task.name,
                    "description": task.description or "",
                    "labels": task.labels or [],
                    "status": task.status.value,
                    "estimated_hours": task.estimated_hours,
                }
            )

        # Create prompt for AI
        prompt = f"""Analyze the following tasks and identify logical dependencies between them.
A task B depends on task A if task A must be completed before task B can reasonably begin.

Tasks:
{json.dumps(task_info, indent=2)}

Identify dependencies based on:
1. Natural workflow order (e.g., design before implementation, implementation before testing)
2. Technical requirements (e.g., database schema before models, backend API before frontend)
3. Component relationships (e.g., authentication before authorization)
4. Data flow (e.g., data model before business logic)
5. Infrastructure needs (e.g., setup before development)

Return ONLY a JSON object with this structure:
{{
    "dependencies": [
        {{
            "task_id": "ID of the task that must be completed first",
            "dependent_ids": ["IDs of tasks that depend on this task"],
            "reasoning": "Brief explanation of why this dependency exists",
            "confidence": 0.0-1.0
        }}
    ],
    "insights": "Overall insights about the task structure and dependencies"
}}

Focus on the most important and logical dependencies. Do not create unnecessary dependencies."""

        # Call AI for analysis
        response = await self.ai_engine._call_claude(prompt)

        # Parse response
        try:
            result = json.loads(response)

            # Convert to dependency map format
            dependency_map = {}

            for dep in result.get("dependencies", []):
                task_id = dep["task_id"]
                dependent_ids = dep["dependent_ids"]
                confidence = dep.get("confidence", 0.8)

                # Only include high-confidence dependencies
                if confidence >= 0.7:
                    if task_id not in dependency_map:
                        dependency_map[task_id] = []

                    dependency_map[task_id].extend(dependent_ids)

                    # Log the reasoning for transparency
                    logger.debug(
                        f"AI dependency: {dep['reasoning']} (confidence: {confidence})"
                    )

            # Store insights for later use
            if "insights" in result:
                await self._store_ai_insights(result["insights"], tasks)

            return dependency_map

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise

    async def _store_ai_insights(self, insights: str, tasks: List[Task]):
        """Store AI insights about task structure for future reference"""
        insight_data = {
            "timestamp": datetime.now().isoformat(),
            "task_count": len(tasks),
            "insights": insights,
            "task_names": [t.name for t in tasks],
        }

        # Store via persistence if available
        if self.persistence:
            await self.persistence.store(
                "ai_dependency_insights",
                f"insights_{datetime.now().timestamp()}",
                insight_data,
            )

        # Emit event if available
        if self.events:
            await self.events.publish(
                "AI_DEPENDENCY_ANALYSIS", "context_ai", insight_data
            )

    def _fallback_inference(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """
        Fallback to pattern-based inference when AI is unavailable.

        This is synchronous to work with the fallback decorator.
        """
        logger.info("Using pattern-based dependency inference as fallback")

        # Create a minimal pattern-based inference
        dependency_map = {}

        for i, task in enumerate(tasks):
            for j, other_task in enumerate(tasks):
                if i >= j:
                    continue

                # Simple keyword-based rules
                task_name_lower = task.name.lower()
                other_name_lower = other_task.name.lower()

                # Testing depends on implementation
                if "test" in task_name_lower and not "test" in other_name_lower:
                    if any(
                        word in other_name_lower
                        for word in ["implement", "build", "create"]
                    ):
                        if other_task.id not in dependency_map:
                            dependency_map[other_task.id] = []
                        dependency_map[other_task.id].append(task.id)

                # Deployment depends on testing
                if "deploy" in task_name_lower and "test" in other_name_lower:
                    if other_task.id not in dependency_map:
                        dependency_map[other_task.id] = []
                    dependency_map[other_task.id].append(task.id)

        return dependency_map

    async def get_dependency_explanation(
        self, task_id: str, dependency_id: str
    ) -> Optional[str]:
        """
        Get AI-generated explanation for why a dependency exists.

        Args:
            task_id: The dependent task
            dependency_id: The task it depends on

        Returns:
            Explanation string or None
        """
        if not self.ai_engine or not self.ai_inference_enabled:
            return None

        try:
            # Find the tasks
            all_tasks = []
            task = None
            dependency = None

            # This would need access to task data - simplified for now
            prompt = f"""Explain why task '{task_id}' depends on task '{dependency_id}' in one clear sentence.
Focus on the logical or technical reason for this dependency."""

            response = await self.ai_engine._call_claude(prompt)
            return response.strip()

        except Exception as e:
            logger.error(f"Failed to get dependency explanation: {e}")
            return None

    def disable_ai_inference(self):
        """Disable AI inference and use only pattern-based inference"""
        self.ai_inference_enabled = False
        logger.info("AI dependency inference disabled")

    def enable_ai_inference(self):
        """Enable AI inference for dependencies"""
        self.ai_inference_enabled = True
        logger.info("AI dependency inference enabled")
