"""
Anthropic Claude Provider for Marcus AI.

Implements semantic task analysis, dependency inference, and intelligent
enhancement using Anthropic's Claude models.
"""

import json
import logging
import os
from typing import Any, Dict, List

import httpx

from src.core.models import Task
from src.utils.json_parser import parse_ai_json_response, parse_json_response

from .base_provider import (
    BaseLLMProvider,
    EffortEstimate,
    SemanticAnalysis,
    SemanticDependency,
)

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """

    Anthropic Claude provider for semantic AI analysis.

    Uses Claude to provide intelligent task analysis, dependency inference,
    and project understanding while maintaining safety and reliability.
    """

    def __init__(self) -> None:
        # Try to get API key from config first, fall back to env var
        from src.config.config_loader import get_config

        config = get_config()
        self.api_key = config.get("ai.anthropic_api_key") or os.getenv(
            "ANTHROPIC_API_KEY"
        )
        if not self.api_key:
            raise ValueError("Anthropic API key not found in config or environment")

        self.base_url = "https://api.anthropic.com/v1"
        self.model = config.get(
            "ai.model", "claude-3-haiku-20240307"
        )  # Fast model for quick responses
        self.max_tokens = config.get("ai.max_tokens", 2048)
        self.timeout = 30.0

        # HTTP client with proper headers
        # Disable HTTP/2 to avoid connection issues in Docker environments
        self.client = httpx.AsyncClient(
            headers={
                "x-api-key": self.api_key,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            timeout=self.timeout,
            http2=False,
        )

        logger.info(f"Anthropic provider initialized with model: {self.model}")

    async def analyze_task(
        self, task: Task, context: Dict[str, Any]
    ) -> SemanticAnalysis:
        """
        Analyze task semantics using Claude.

        Args
        ----
            task: Task to analyze
            context: Project context

        Returns
        -------
            Semantic analysis with intent, dependencies, and risks
        """
        prompt = self._build_task_analysis_prompt(task, context)

        try:
            response = await self._call_claude(prompt)
            return self._parse_task_analysis_response(response)

        except Exception as e:
            logger.error(f"Anthropic task analysis failed: {e}")
            # Return safe fallback
            return SemanticAnalysis(
                task_intent="unknown",
                semantic_dependencies=[],
                risk_factors=["ai_analysis_failed"],
                suggestions=["Review task manually"],
                confidence=0.1,
                reasoning=f"AI analysis failed: {str(e)}",
                risk_assessment={"availability": "degraded"},
            )

    async def infer_dependencies(self, tasks: List[Task]) -> List[SemanticDependency]:
        """
        Infer semantic dependencies between tasks using Claude.

        Args
        ----
            tasks: List of tasks to analyze

        Returns
        -------
            List of inferred semantic dependencies
        """
        if len(tasks) < 2:
            return []

        prompt = self._build_dependency_inference_prompt(tasks)

        try:
            response = await self._call_claude(prompt)
            return self._parse_dependency_response(response, tasks)

        except Exception as e:
            logger.error(f"Anthropic dependency inference failed: {e}")
            return []

    async def generate_enhanced_description(
        self, task: Task, context: Dict[str, Any]
    ) -> str:
        """
        Generate enhanced task description using Claude.

        Args
        ----
            task: Task to enhance
            context: Project context

        Returns
        -------
            Enhanced description
        """
        prompt = self._build_enhancement_prompt(task, context)

        try:
            response = await self._call_claude(prompt)
            return self._parse_enhancement_response(response, task)

        except Exception as e:
            logger.error(f"Anthropic description enhancement failed: {e}")
            return task.description or task.name

    async def estimate_effort(
        self, task: Task, context: Dict[str, Any]
    ) -> EffortEstimate:
        """
        Estimate task effort using Claude.

        Args
        ----
            task: Task to estimate
            context: Project context with historical data

        Returns
        -------
            Effort estimate with confidence and factors
        """
        prompt = self._build_estimation_prompt(task, context)

        try:
            response = await self._call_claude(prompt)
            return self._parse_estimation_response(response)

        except Exception as e:
            logger.error(f"Anthropic effort estimation failed: {e}")
            return EffortEstimate(
                estimated_hours=8.0,  # Safe default
                confidence=0.1,
                factors=["ai_estimation_failed"],
                similar_tasks=[],
                risk_multiplier=1.5,
            )

    async def analyze_blocker(
        self, task: Task, blocker: str, context: Dict[str, Any]
    ) -> List[str]:
        """
        Analyze blocker and suggest solutions using Claude.

        Args
        ----
            task: Blocked task
            blocker: Blocker description
            context: Additional context

        Returns
        -------
            List of suggested solutions
        """
        prompt = self._build_blocker_analysis_prompt(task, blocker, context)

        try:
            response = await self._call_claude(prompt)
            return self._parse_blocker_response(response)

        except Exception as e:
            logger.error(f"Anthropic blocker analysis failed: {e}")
            return [
                "Review task requirements and dependencies",
                "Check documentation for similar issues",
                "Consult with team lead or senior developer",
            ]

    def _build_task_analysis_prompt(self, task: Task, context: Dict[str, Any]) -> str:
        """Build prompt for task semantic analysis."""
        project_type = context.get("project_type", "general")
        tech_stack = context.get("tech_stack", [])

        return f"""
You are an expert software project manager analyzing a development task.

Task Information:
- Name: {task.name}
- Description: {task.description or 'No description provided'}
- Priority: {task.priority}
- Current Status: {task.status}

Project Context:
- Project Type: {project_type}
- Technology Stack: {', '.join(tech_stack) if tech_stack else 'Not specified'}
- Team Size: {context.get('team_size', 'Unknown')}

Please analyze this task and provide a JSON response with the following
structure:
{{
  "task_intent": "Brief description of what this task is trying to accomplish",
  "semantic_dependencies": [
    "List of task types that should logically come before this"
  ],
  "risk_factors": ["List of potential risks or complications"],
  "suggestions": ["List of recommendations for successful completion"],
  "confidence": 0.0-1.0,
  "reasoning": "Explanation of your analysis",
  "risk_assessment": {{
    "technical_complexity": "low|medium|high",
    "user_impact": "low|medium|high",
    "rollback_difficulty": "low|medium|high"
  }}
}}

Focus on:
1. Understanding the true intent beyond just the task name
2. Identifying logical prerequisites and dependencies
3. Assessing risks specific to the technology stack
4. Providing actionable suggestions

Respond only with valid JSON."""

    def _build_dependency_inference_prompt(self, tasks: List[Task]) -> str:
        """Build prompt for dependency inference."""
        task_list = "\n".join(
            [
                f"- {task.id}: {task.name} | {task.description or 'No description'}"
                for task in tasks
            ]
        )

        return f"""
You are analyzing task dependencies for a software project.

Tasks to analyze:
{task_list}

Please identify logical dependencies between these tasks and return a JSON
array with this structure:
[
  {{
    "dependent_task_id": "task_that_depends",
    "dependency_task_id": "task_that_must_come_first",
    "confidence": 0.0-1.0,
    "reasoning": "Why this dependency exists",
    "dependency_type": "logical|technical|temporal"
  }}
]

Guidelines:
1. Only suggest dependencies that are logically necessary
2. Focus on "must come before" relationships, not just "nice to have"
3. Consider technical prerequisites (e.g., API before frontend integration)
4. Consider logical flow (e.g., design before implementation, testing before deployment)
5. High confidence (>0.8) should be reserved for clear, mandatory dependencies

Respond only with valid JSON array."""

    def _build_enhancement_prompt(self, task: Task, context: Dict[str, Any]) -> str:
        """Build prompt for task description enhancement."""
        project_type = context.get("project_type", "general")

        return f"""
You are enhancing a task description to make it more detailed and actionable.

Current Task:
- Name: {task.name}
- Description: {task.description or 'No description provided'}

Project Context:
- Type: {project_type}
- Technology: {', '.join(context.get('tech_stack', []))}

Please provide an enhanced description that includes:
1. Clear objective and success criteria
2. Specific technical requirements
3. Key considerations or gotchas
4. Definition of done

Keep it concise but comprehensive. Focus on what a developer needs to know
to complete the task successfully.

Enhanced Description:"""

    def _build_estimation_prompt(self, task: Task, context: Dict[str, Any]) -> str:
        """Build prompt for effort estimation."""
        historical_data = context.get("historical_data", [])
        similar_tasks = [
            h
            for h in historical_data
            if h.get("task_type") == self._classify_task_type(task)
        ]

        similar_tasks_text = ""
        if similar_tasks:
            similar_tasks_text = "\nSimilar historical tasks:\n" + "\n".join(
                [
                    f"- {h.get('name', 'Unknown')}: "
                    f"{h.get('actual_hours', 'Unknown')} hours"
                    for h in similar_tasks[:3]
                ]
            )

        return f"""
You are estimating development effort for a task.

Task: {task.name}
Description: {task.description or 'No description'}
Project Type: {context.get('project_type', 'general')}
Technology: {', '.join(context.get('tech_stack', []))}
{similar_tasks_text}

Please provide a JSON response:
{{
  "estimated_hours": float,
  "confidence": 0.0-1.0,
  "factors": ["List of factors affecting the estimate"],
  "similar_tasks": ["List of similar task patterns"],
  "risk_multiplier": 1.0-3.0
}}

Consider:
1. Task complexity and scope
2. Technology familiarity
3. Integration requirements
4. Testing needs
5. Documentation requirements

Respond only with valid JSON."""

    def _build_blocker_analysis_prompt(
        self, task: Task, blocker: str, context: Dict[str, Any]
    ) -> str:
        """Build prompt for blocker analysis."""
        agent_info = context.get("agent", {})
        severity = context.get("severity", "unknown")

        return f"""
You are helping resolve a development blocker.

Task: {task.name}
Description: {task.description or 'No description'}
Blocker: {blocker}
Severity: {severity}
Agent: {agent_info.get('name', 'Unknown')} ({agent_info.get('role', 'Developer')})

Please provide 3-5 specific, actionable suggestions to resolve this blocker.
Focus on practical steps the developer can take.

Format as a JSON array of strings:
["suggestion1", "suggestion2", "suggestion3"]

Suggestions should be:
1. Specific and actionable
2. Ordered by likelihood to resolve the issue
3. Include both immediate fixes and alternative approaches
4. Consider the technology stack and project context

Respond only with valid JSON array."""

    async def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        Generate a completion for the given prompt.

        Args
        ----
            prompt: The prompt to complete
            max_tokens: Maximum tokens in response

        Returns
        -------
            The completion text
        """
        self.max_tokens = max_tokens
        return await self._call_claude(prompt)

    async def _call_claude(self, prompt: str) -> str:
        """
        Make API call to Claude.

        Args
        ----
            prompt: Prompt to send to Claude

        Returns
        -------
            Claude's response text
        """
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = await self.client.post(f"{self.base_url}/messages", json=payload)
            response.raise_for_status()

            data = response.json()
            return str(data["content"][0]["text"])

        except httpx.TimeoutException:
            raise Exception("Claude API request timed out")
        except httpx.HTTPStatusError as e:
            raise Exception(
                f"Claude API error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            raise Exception(f"Claude API call failed: {str(e)}")

    def _parse_task_analysis_response(self, response: str) -> SemanticAnalysis:
        """Parse Claude's task analysis response."""
        try:
            data = parse_ai_json_response(response)
            return SemanticAnalysis(
                task_intent=data.get("task_intent", "unknown"),
                semantic_dependencies=data.get("semantic_dependencies", []),
                risk_factors=data.get("risk_factors", []),
                suggestions=data.get("suggestions", []),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", "No reasoning provided"),
                risk_assessment=data.get("risk_assessment", {}),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse Claude task analysis: {e}")
            return SemanticAnalysis(
                task_intent="parse_error",
                semantic_dependencies=[],
                risk_factors=["response_parsing_failed"],
                suggestions=["Retry analysis"],
                confidence=0.1,
                reasoning="Failed to parse AI response",
                risk_assessment={},
            )

    def _parse_dependency_response(
        self, response: str, tasks: List[Task]
    ) -> List[SemanticDependency]:
        """Parse Claude's dependency inference response."""
        try:
            data = parse_json_response(response)
            dependencies = []

            task_ids = {task.id for task in tasks}

            # Handle both list format and dict with dependencies list
            if isinstance(data, list):
                deps_list = data
            elif isinstance(data, dict) and "dependencies" in data:
                deps_list = data["dependencies"]
            elif isinstance(data, dict):
                deps_list = [data]  # Single dependency as dict
            else:
                deps_list = []

            for dep in deps_list:
                # Validate task IDs exist
                if (
                    dep.get("dependent_task_id") in task_ids
                    and dep.get("dependency_task_id") in task_ids
                ):
                    dependencies.append(
                        SemanticDependency(
                            dependent_task_id=dep["dependent_task_id"],
                            dependency_task_id=dep["dependency_task_id"],
                            confidence=float(dep.get("confidence", 0.5)),
                            reasoning=dep.get("reasoning", ""),
                            dependency_type=dep.get("dependency_type", "logical"),
                        )
                    )

            return dependencies

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse Claude dependency response: {e}")
            return []

    def _parse_enhancement_response(self, response: str, task: Task) -> str:
        """Parse Claude's description enhancement response."""
        # Claude returns enhancement directly as text
        enhanced = response.strip()

        # Ensure we have some content
        if len(enhanced) < 10:
            return task.description or task.name

        return enhanced

    def _parse_estimation_response(self, response: str) -> EffortEstimate:
        """Parse Claude's effort estimation response."""
        try:
            data = parse_ai_json_response(response)
            return EffortEstimate(
                estimated_hours=float(data.get("estimated_hours", 8.0)),
                confidence=float(data.get("confidence", 0.5)),
                factors=data.get("factors", []),
                similar_tasks=data.get("similar_tasks", []),
                risk_multiplier=float(data.get("risk_multiplier", 1.0)),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse Claude estimation response: {e}")
            return EffortEstimate(
                estimated_hours=8.0,
                confidence=0.1,
                factors=["parsing_failed"],
                similar_tasks=[],
                risk_multiplier=1.5,
            )

    def _parse_blocker_response(self, response: str) -> List[str]:
        """Parse Claude's blocker analysis response."""
        try:
            data = parse_json_response(response)
            if isinstance(data, list):
                return [str(s) for s in data]
            elif isinstance(data, dict) and "suggestions" in data:
                return [str(s) for s in data["suggestions"]]
            else:
                return [str(data)]
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse Claude blocker response: {e}")
            # Try to extract suggestions from text
            lines = response.strip().split("\n")
            suggestions_list: List[str] = []
            for line in lines:
                if line.strip() and not line.startswith("#"):
                    suggestions_list.append(line.strip("- ").strip())
            return (
                suggestions_list[:5]
                if suggestions_list
                else ["Review and retry the task"]
            )

    def _classify_task_type(self, task: Task) -> str:
        """Classify task type for historical comparison."""
        task_text = f"{task.name} {task.description or ''}".lower()

        if any(word in task_text for word in ["test", "qa", "verify"]):
            return "testing"
        elif any(word in task_text for word in ["deploy", "release"]):
            return "deployment"
        elif any(word in task_text for word in ["design", "ui", "mockup"]):
            return "design"
        elif any(word in task_text for word in ["api", "endpoint", "service"]):
            return "backend"
        elif any(word in task_text for word in ["frontend", "client", "react"]):
            return "frontend"
        else:
            return "development"

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
