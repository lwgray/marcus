"""
Local LLM Provider for Marcus AI.

Implements support for local models via Ollama or other OpenAI-compatible servers.
This provider enables running Marcus with complete local AI inference, removing
dependency on external API services.

Classes
-------
LocalLLMProvider
    Local model provider supporting Ollama and OpenAI-compatible endpoints

Notes
-----
Requires a local LLM server running (e.g., Ollama, llama.cpp server, etc.)
Model selection via MARCUS_LOCAL_LLM_PATH environment variable.
Base URL configurable via MARCUS_LOCAL_LLM_URL (defaults to Ollama).

Examples
--------
>>> # With Ollama running locally
>>> os.environ['MARCUS_LOCAL_LLM_PATH'] = 'codellama:13b'
>>> os.environ['MARCUS_LLM_PROVIDER'] = 'local'
>>> provider = LocalLLMProvider('codellama:13b')
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from src.core.models import Task
from src.utils.json_parser import parse_ai_json_response

from .base_provider import (
    BaseLLMProvider,
    EffortEstimate,
    SemanticAnalysis,
    SemanticDependency,
)

logger = logging.getLogger(__name__)


class LocalLLMProvider(BaseLLMProvider):
    """
    Local LLM provider for semantic AI analysis.

    Supports Ollama and other OpenAI-compatible local inference servers.
    Optimized for coding and reasoning tasks with models like CodeLlama,
    DeepSeek-Coder, or Mixtral.

    Parameters
    ----------
    model_name : str
        Name of the model to use (e.g., 'codellama:13b', 'deepseek-coder:6.7b')

    Attributes
    ----------
    base_url : str
        Local LLM server URL (default: http://localhost:11434/v1 for Ollama)
    model : str
        Model identifier for the local server
    max_tokens : int
        Maximum tokens for responses
    timeout : float
        API request timeout in seconds
    client : httpx.AsyncClient
        Async HTTP client for API calls

    Examples
    --------
    >>> provider = LocalLLMProvider('codellama:13b')
    >>> analysis = await provider.analyze_task(task, context)
    """

    def __init__(self, model_name: str) -> None:
        """
        Initialize local LLM provider.

        Parameters
        ----------
        model_name : str
            Model to use (e.g., 'codellama:13b')
        """
        # Get config for local LLM settings
        from src.config.config_loader import get_config
        config = get_config()
        ai_config = config.get("ai", {})
        
        # Support different local LLM servers - config first, env var as override
        self.base_url = ai_config.get("local_url", "http://localhost:11434/v1")
        if os.getenv("MARCUS_LOCAL_LLM_URL"):
            self.base_url = os.getenv("MARCUS_LOCAL_LLM_URL")
            
        self.model = model_name
        self.max_tokens = 4096  # Most local models support longer context
        self.timeout = 120.0  # Longer timeout for local inference

        # Get API key from config or env var
        api_key = ai_config.get("local_key", "none")
        if os.getenv("MARCUS_LOCAL_LLM_KEY"):
            api_key = os.getenv("MARCUS_LOCAL_LLM_KEY")

        # HTTP client for OpenAI-compatible API
        self.client = httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                # Ollama doesn't require auth, but some servers might
                "Authorization": f"Bearer {api_key}",
            },
            timeout=self.timeout,
            base_url=self.base_url,
        )

        logger.info(
            f"Local LLM provider initialized with model: {self.model} at {self.base_url}"
        )

    async def analyze_task(
        self, task: Task, context: Dict[str, Any]
    ) -> SemanticAnalysis:
        """
        Analyze task semantics using local LLM.

        Parameters
        ----------
        task : Task
            Task to analyze
        context : dict
            Project context including related tasks

        Returns
        -------
        SemanticAnalysis
            Comprehensive semantic analysis of the task
        """
        prompt = self._build_task_analysis_prompt(task, context)

        try:
            response = await self._call_local_llm(prompt)
            return self._parse_task_analysis_response(response)

        except Exception as e:
            logger.error(f"Local LLM task analysis failed: {e}")
            # Return safe fallback
            return SemanticAnalysis(
                task_intent="unknown",
                semantic_dependencies=[],
                risk_factors=["local_llm_analysis_failed"],
                suggestions=["Review task manually"],
                confidence=0.1,
                reasoning=f"Local LLM analysis failed: {str(e)}",
                risk_assessment={"availability": "degraded"},
            )

    async def infer_dependencies(self, tasks: List[Task]) -> List[SemanticDependency]:
        """
        Infer semantic dependencies between tasks.

        Parameters
        ----------
        tasks : list of Task
            All tasks to analyze for dependencies

        Returns
        -------
        list of SemanticDependency
            Inferred dependencies with confidence scores
        """
        prompt = self._build_dependency_inference_prompt(tasks)

        try:
            response = await self._call_local_llm(prompt)
            return self._parse_dependency_response(response)

        except Exception as e:
            logger.error(f"Local LLM dependency inference failed: {e}")
            return []

    async def generate_enhanced_description(
        self, task: Task, context: Dict[str, Any]
    ) -> str:
        """
        Generate enhanced task description.

        Parameters
        ----------
        task : Task
            Task needing better description
        context : dict
            Project context

        Returns
        -------
        str
            Enhanced, detailed task description
        """
        prompt = f"""Given this task: '{task.name}'
Current description: '{task.description or "No description"}'
Project context: {json.dumps(context.get('project_type', 'software development'))}

Generate a clear, actionable description that includes:
1. What needs to be done
2. Key technical considerations
3. Success criteria

Enhanced description:"""

        try:
            response = await self._call_local_llm(prompt, max_tokens=500)
            return response.strip()

        except Exception as e:
            logger.error(f"Local LLM description generation failed: {e}")
            return task.description or task.name

    async def estimate_effort(
        self, task: Task, context: Dict[str, Any]
    ) -> EffortEstimate:
        """
        Estimate task effort using local LLM.

        Parameters
        ----------
        task : Task
            Task to estimate
        context : dict
            Project context with team velocity

        Returns
        -------
        EffortEstimate
            Hours estimate with confidence and factors
        """
        prompt = self._build_effort_estimation_prompt(task, context)

        try:
            response = await self._call_local_llm(prompt)
            return self._parse_effort_response(response)

        except Exception as e:
            logger.error(f"Local LLM effort estimation failed: {e}")
            # Safe fallback
            return EffortEstimate(
                hours_estimate=8.0,
                confidence=0.3,
                factors_considered=["default_estimate"],
                reasoning="Local LLM unavailable, using default",
            )

    async def analyze_blocker(
        self, task: Task, blocker: str, context: Dict[str, Any]
    ) -> List[str]:
        """
        Analyze blocker and suggest solutions.

        Parameters
        ----------
        task : Task
            Blocked task
        blocker : str
            Description of the blocker
        context : dict
            Additional context including severity

        Returns
        -------
        list of str
            Prioritized solution suggestions
        """
        severity = context.get("severity", "medium")
        agent_info = context.get("agent", {})

        prompt = f"""Task: {task.name}
Blocker: {blocker}
Severity: {severity}
Agent: {agent_info.get('name', 'Unknown')} (Skills: {agent_info.get('skills', [])})

Analyze this blocker and provide 3-5 specific, actionable solutions.
Focus on practical steps the developer can take immediately.

Solutions:"""

        try:
            response = await self._call_local_llm(prompt)
            # Parse numbered list
            solutions = []
            for line in response.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    # Remove numbering/bullets
                    solution = line.lstrip("0123456789.-) ").strip()
                    if solution:
                        solutions.append(solution)

            return solutions[:5] if solutions else self._get_fallback_solutions()

        except Exception as e:
            logger.error(f"Local LLM blocker analysis failed: {e}")
            return self._get_fallback_solutions()

    async def complete(
        self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7
    ) -> str:
        """
        Generic completion endpoint for direct LLM access.

        Parameters
        ----------
        prompt : str
            The prompt to complete
        max_tokens : int
            Maximum tokens to generate
        temperature : float
            Sampling temperature (0.0-1.0)

        Returns
        -------
        str
            The completion text
        """
        return await self._call_local_llm(prompt, max_tokens, temperature)

    async def _call_local_llm(
        self, prompt: str, max_tokens: Optional[int] = None, temperature: float = 0.7
    ) -> str:
        """
        Make a request to the local LLM server.

        Parameters
        ----------
        prompt : str
            The prompt to send
        max_tokens : int, optional
            Max tokens to generate
        temperature : float
            Sampling temperature

        Returns
        -------
        str
            The model's response

        Raises
        ------
        Exception
            If the API call fails
        """
        if max_tokens is None:
            max_tokens = self.max_tokens

        # OpenAI-compatible format
        request_data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an AI assistant helping with software development task analysis. "
                    "Provide clear, structured responses focusing on practical implementation details.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        try:
            response = await self.client.post("/chat/completions", json=request_data)
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Try Ollama's native API format
                return await self._call_ollama_native(prompt, max_tokens, temperature)
            raise Exception(f"Local LLM API error: {e.response.status_code} - {e.response.text}")

        except Exception as e:
            logger.error(f"Local LLM call failed: {e}")
            raise

    async def _call_ollama_native(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> str:
        """
        Fallback to Ollama's native API format.

        Some Ollama installations might not have OpenAI compatibility enabled.
        """
        # Ollama native endpoint
        native_url = self.base_url.replace("/v1", "")
        
        request_data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        try:
            response = await self.client.post(
                f"{native_url}/api/generate", json=request_data
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]

        except Exception as e:
            logger.error(f"Ollama native API call failed: {e}")
            raise Exception(f"Failed to connect to local LLM server: {str(e)}")

    def _build_task_analysis_prompt(
        self, task: Task, context: Dict[str, Any]
    ) -> str:
        """Build prompt for task analysis."""
        return f"""Analyze this software development task:

Task: {task.name}
Description: {task.description or 'No description provided'}
Priority: {task.priority}
Labels: {task.labels}

Project context:
- Type: {context.get('project_type', 'software project')}
- Related tasks: {len(context.get('available_tasks', []))} tasks in project

Provide a JSON response with:
{{
    "task_intent": "What this task aims to achieve",
    "semantic_dependencies": ["task names that should complete first"],
    "risk_factors": ["potential risks or complexities"],
    "suggestions": ["specific improvements or considerations"],
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of analysis",
    "risk_assessment": {{
        "technical": "low/medium/high",
        "timeline": "low/medium/high",
        "dependencies": "low/medium/high"
    }}
}}"""

    def _parse_task_analysis_response(self, response: str) -> SemanticAnalysis:
        """Parse task analysis response."""
        try:
            data = parse_ai_json_response(response)

            return SemanticAnalysis(
                task_intent=data.get("task_intent", "unknown"),
                semantic_dependencies=data.get("semantic_dependencies", []),
                risk_factors=data.get("risk_factors", []),
                suggestions=data.get("suggestions", []),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                risk_assessment=data.get("risk_assessment", {}),
            )

        except Exception as e:
            logger.warning(f"Failed to parse task analysis: {e}")
            # Return minimal valid response
            return SemanticAnalysis(
                task_intent="parse_error",
                semantic_dependencies=[],
                risk_factors=["response_parsing_failed"],
                suggestions=[],
                confidence=0.1,
                reasoning=str(e),
                risk_assessment={},
            )

    def _build_dependency_inference_prompt(self, tasks: List[Task]) -> str:
        """Build prompt for dependency inference."""
        task_list = "\n".join(
            [f"- {t.id}: {t.name} ({t.status})" for t in tasks[:20]]  # Limit for context
        )

        return f"""Analyze these tasks and identify logical dependencies:

{task_list}

Return a JSON array of dependencies:
[
    {{
        "dependent_task_id": "task that depends",
        "dependency_task_id": "task that must complete first",
        "confidence": 0.0-1.0,
        "reasoning": "why this dependency exists",
        "dependency_type": "logical|technical|temporal"
    }}
]

Focus on clear dependencies like:
- Tests before deployment
- Setup before implementation
- Data models before APIs"""

    def _parse_dependency_response(self, response: str) -> List[SemanticDependency]:
        """Parse dependency inference response."""
        try:
            data = parse_ai_json_response(response)
            if not isinstance(data, list):
                data = data.get("dependencies", [])

            dependencies = []
            for dep in data:
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

        except Exception as e:
            logger.warning(f"Failed to parse dependencies: {e}")
            return []

    def _build_effort_estimation_prompt(
        self, task: Task, context: Dict[str, Any]
    ) -> str:
        """Build prompt for effort estimation."""
        return f"""Estimate effort for this task:

Task: {task.name}
Description: {task.description or 'No description'}
Priority: {task.priority}
Current estimate: {task.estimated_hours or 'None'}

Team context:
- Average velocity: {context.get('avg_velocity', 'unknown')}
- Tech stack: {context.get('tech_stack', [])}

Provide a JSON response:
{{
    "hours_estimate": number,
    "confidence": 0.0-1.0,
    "factors_considered": ["list of factors"],
    "reasoning": "explanation"
}}"""

    def _parse_effort_response(self, response: str) -> EffortEstimate:
        """Parse effort estimation response."""
        try:
            data = parse_ai_json_response(response)

            return EffortEstimate(
                hours_estimate=float(data.get("hours_estimate", 8.0)),
                confidence=float(data.get("confidence", 0.5)),
                factors_considered=data.get("factors_considered", []),
                reasoning=data.get("reasoning", ""),
            )

        except Exception as e:
            logger.warning(f"Failed to parse effort estimate: {e}")
            return EffortEstimate(
                hours_estimate=8.0,
                confidence=0.3,
                factors_considered=["parse_error"],
                reasoning=str(e),
            )

    def _get_fallback_solutions(self) -> List[str]:
        """Get generic fallback solutions for blockers."""
        return [
            "Review task requirements and dependencies",
            "Check project documentation for similar issues",
            "Consult with team lead or senior developer",
            "Break down the task into smaller components",
            "Research the specific error or issue online",
        ]