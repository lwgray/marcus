"""
OpenAI Provider for Marcus AI.

Implements semantic task analysis using OpenAI's GPT models as a fallback
or alternative to Anthropic Claude.

This provider integrates with OpenAI's API to provide:
- Task semantic analysis
- Dependency inference
- Enhanced descriptions
- Effort estimation
- Blocker analysis

Classes
-------
OpenAIProvider
    OpenAI GPT provider implementation

Notes
-----
Requires OPENAI_API_KEY environment variable.
Model selection via OPENAI_MODEL environment variable.
"""

import logging
import json
import os
from typing import Dict, List, Any
import httpx

from src.core.models import Task
from .base_provider import BaseLLMProvider, SemanticAnalysis, SemanticDependency, EffortEstimate

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI GPT provider for semantic AI analysis.
    
    Provides fallback capability when Anthropic is unavailable
    or alternative AI perspective for comparison.
    
    Parameters
    ----------
    None
    
    Attributes
    ----------
    api_key : str
        OpenAI API key from environment
    base_url : str
        OpenAI API base URL
    model : str
        GPT model to use (default: gpt-3.5-turbo)
    max_tokens : int
        Maximum tokens for responses
    timeout : float
        API request timeout in seconds
    client : httpx.AsyncClient
        Async HTTP client for API calls
    
    Raises
    ------
    ValueError
        If OPENAI_API_KEY is not set
    
    Examples
    --------
    >>> provider = OpenAIProvider()
    >>> analysis = await provider.analyze_task(task, context)
    """
    
    def __init__(self) -> None:
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.base_url = "https://api.openai.com/v1"
        self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')  # Cost-effective model
        self.max_tokens = 2048
        self.timeout = 30.0
        
        # HTTP client
        self.client = httpx.AsyncClient(
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            },
            timeout=self.timeout
        )
        
        logger.info(f"OpenAI provider initialized with model: {self.model}")
    
    async def analyze_task(self, task: Task, context: Dict[str, Any]) -> SemanticAnalysis:
        """
        Analyze task semantics using GPT.
        
        Parameters
        ----------
        task : Task
            Task to analyze
        context : dict
            Project context
            
        Returns
        -------
        SemanticAnalysis
            Semantic analysis with fallback on error
        """
        messages = [
            {
                "role": "system",
                "content": "You are an expert software project manager analyzing development tasks. Respond only with valid JSON."
            },
            {
                "role": "user", 
                "content": self._build_task_analysis_prompt(task, context)
            }
        ]
        
        try:
            response = await self._call_openai(messages)
            return self._parse_task_analysis_response(response)
            
        except Exception as e:
            logger.error(f"OpenAI task analysis failed: {e}")
            return SemanticAnalysis(
                task_intent="unknown",
                semantic_dependencies=[],
                risk_factors=["ai_analysis_failed"],
                suggestions=["Review task manually"],
                confidence=0.1,
                reasoning=f"OpenAI analysis failed: {str(e)}",
                risk_assessment={'availability': 'degraded'}
            )
    
    async def infer_dependencies(self, tasks: List[Task]) -> List[SemanticDependency]:
        """
        Infer semantic dependencies using GPT.
        
        Parameters
        ----------
        tasks : list of Task
            Tasks to analyze for dependencies
            
        Returns
        -------
        list of SemanticDependency
            Inferred dependencies, empty list on error
        """
        if len(tasks) < 2:
            return []
        
        messages = [
            {
                "role": "system",
                "content": "You are analyzing task dependencies. Respond only with valid JSON array."
            },
            {
                "role": "user",
                "content": self._build_dependency_inference_prompt(tasks)
            }
        ]
        
        try:
            response = await self._call_openai(messages)
            return self._parse_dependency_response(response, tasks)
            
        except Exception as e:
            logger.error(f"OpenAI dependency inference failed: {e}")
            return []
    
    async def generate_enhanced_description(self, task: Task, context: Dict[str, Any]) -> str:
        """Generate enhanced description using GPT"""
        messages = [
            {
                "role": "system",
                "content": "You are enhancing task descriptions for software development. Be concise but thorough."
            },
            {
                "role": "user",
                "content": self._build_enhancement_prompt(task, context)
            }
        ]
        
        try:
            response = await self._call_openai(messages)
            return response.strip()
            
        except Exception as e:
            logger.error(f"OpenAI description enhancement failed: {e}")
            return task.description or task.name
    
    async def estimate_effort(self, task: Task, context: Dict[str, Any]) -> EffortEstimate:
        """Estimate effort using GPT"""
        messages = [
            {
                "role": "system",
                "content": "You are estimating development effort. Respond only with valid JSON."
            },
            {
                "role": "user",
                "content": self._build_estimation_prompt(task, context)
            }
        ]
        
        try:
            response = await self._call_openai(messages)
            return self._parse_estimation_response(response)
            
        except Exception as e:
            logger.error(f"OpenAI effort estimation failed: {e}")
            return EffortEstimate(
                estimated_hours=8.0,
                confidence=0.1,
                factors=["ai_estimation_failed"],
                similar_tasks=[],
                risk_multiplier=1.5
            )
    
    async def analyze_blocker(self, task: Task, blocker: str, context: Dict[str, Any]) -> List[str]:
        """Analyze blocker using GPT"""
        messages = [
            {
                "role": "system", 
                "content": "You are helping resolve development blockers. Respond with a JSON array of specific suggestions."
            },
            {
                "role": "user",
                "content": self._build_blocker_analysis_prompt(task, blocker, context)
            }
        ]
        
        try:
            response = await self._call_openai(messages)
            return self._parse_blocker_response(response)
            
        except Exception as e:
            logger.error(f"OpenAI blocker analysis failed: {e}")
            return [
                "Check task requirements and prerequisites",
                "Review relevant documentation",
                "Seek assistance from team members"
            ]
    
    def _build_task_analysis_prompt(self, task: Task, context: Dict[str, Any]) -> str:
        """Build task analysis prompt for GPT"""
        return f"""
Analyze this software development task:

Task: {task.name}
Description: {task.description or 'No description'}
Priority: {task.priority}
Project Type: {context.get('project_type', 'general')}
Tech Stack: {', '.join(context.get('tech_stack', []))}

Provide JSON response:
{{
  "task_intent": "what this task accomplishes",
  "semantic_dependencies": ["prerequisites needed"],
  "risk_factors": ["potential risks"],
  "suggestions": ["recommendations"],
  "confidence": 0.0-1.0,
  "reasoning": "analysis explanation",
  "risk_assessment": {{
    "technical_complexity": "low|medium|high",
    "user_impact": "low|medium|high",
    "rollback_difficulty": "low|medium|high"
  }}
}}"""
    
    def _build_dependency_inference_prompt(self, tasks: List[Task]) -> str:
        """Build dependency inference prompt"""
        task_list = "\n".join([
            f"{task.id}: {task.name} - {task.description or 'No description'}"
            for task in tasks
        ])
        
        return f"""
Identify dependencies between these tasks:

{task_list}

Return JSON array:
[
  {{
    "dependent_task_id": "task_that_depends",
    "dependency_task_id": "prerequisite_task",
    "confidence": 0.0-1.0,
    "reasoning": "why dependency exists",
    "dependency_type": "logical|technical|temporal"
  }}
]

Only include necessary dependencies."""
    
    def _build_enhancement_prompt(self, task: Task, context: Dict[str, Any]) -> str:
        """Build enhancement prompt"""
        return f"""
Enhance this task description:

Current: {task.name}
Description: {task.description or 'No description'}
Project: {context.get('project_type', 'general')}

Provide enhanced description with:
- Clear objective
- Technical requirements  
- Success criteria
- Key considerations

Enhanced Description:"""
    
    def _build_estimation_prompt(self, task: Task, context: Dict[str, Any]) -> str:
        """Build estimation prompt"""
        return f"""
Estimate effort for this task:

Task: {task.name}
Description: {task.description or 'No description'}
Technology: {', '.join(context.get('tech_stack', []))}

JSON response:
{{
  "estimated_hours": float,
  "confidence": 0.0-1.0,
  "factors": ["factors affecting estimate"],
  "similar_tasks": ["similar task patterns"],
  "risk_multiplier": 1.0-3.0
}}"""
    
    def _build_blocker_analysis_prompt(self, task: Task, blocker: str, context: Dict[str, Any]) -> str:
        """Build blocker analysis prompt"""
        return f"""
Help resolve this development blocker:

Task: {task.name}
Blocker: {blocker}
Severity: {context.get('severity', 'unknown')}

Provide JSON array of 3-5 specific solutions:
["solution1", "solution2", "solution3"]"""
    
    async def _call_openai(self, messages: List[Dict[str, str]]) -> str:
        """Make API call to OpenAI"""
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.1  # Low temperature for consistent responses
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            return data['choices'][0]['message']['content']
            
        except httpx.TimeoutException:
            raise Exception("OpenAI API request timed out")
        except httpx.HTTPStatusError as e:
            raise Exception(f"OpenAI API error: {e.response.status_code}")
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {str(e)}")
    
    def _parse_task_analysis_response(self, response: str) -> SemanticAnalysis:
        """Parse GPT task analysis response"""
        try:
            data = json.loads(response)
            return SemanticAnalysis(
                task_intent=data.get('task_intent', 'unknown'),
                semantic_dependencies=data.get('semantic_dependencies', []),
                risk_factors=data.get('risk_factors', []),
                suggestions=data.get('suggestions', []),
                confidence=float(data.get('confidence', 0.5)),
                reasoning=data.get('reasoning', 'No reasoning provided'),
                risk_assessment=data.get('risk_assessment', {})
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse OpenAI response: {e}")
            return SemanticAnalysis(
                task_intent="parse_error",
                semantic_dependencies=[],
                risk_factors=["response_parsing_failed"],
                suggestions=["Retry analysis"],
                confidence=0.1,
                reasoning="Failed to parse AI response",
                risk_assessment={}
            )
    
    def _parse_dependency_response(self, response: str, tasks: List[Task]) -> List[SemanticDependency]:
        """Parse dependency inference response"""
        try:
            data = json.loads(response)
            dependencies = []
            task_ids = {task.id for task in tasks}
            
            for dep in data:
                if (dep.get('dependent_task_id') in task_ids and 
                    dep.get('dependency_task_id') in task_ids):
                    dependencies.append(SemanticDependency(
                        dependent_task_id=dep['dependent_task_id'],
                        dependency_task_id=dep['dependency_task_id'],
                        confidence=float(dep.get('confidence', 0.5)),
                        reasoning=dep.get('reasoning', ''),
                        dependency_type=dep.get('dependency_type', 'logical')
                    ))
            
            return dependencies
        except (json.JSONDecodeError, KeyError, ValueError):
            return []
    
    def _parse_estimation_response(self, response: str) -> EffortEstimate:
        """Parse effort estimation response"""
        try:
            data = json.loads(response)
            return EffortEstimate(
                estimated_hours=float(data.get('estimated_hours', 8.0)),
                confidence=float(data.get('confidence', 0.5)),
                factors=data.get('factors', []),
                similar_tasks=data.get('similar_tasks', []),
                risk_multiplier=float(data.get('risk_multiplier', 1.0))
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return EffortEstimate(
                estimated_hours=8.0,
                confidence=0.1,
                factors=["parsing_failed"],
                similar_tasks=[],
                risk_multiplier=1.5
            )
    
    def _parse_blocker_response(self, response: str) -> List[str]:
        """Parse blocker analysis response"""
        try:
            suggestions = json.loads(response)
            if isinstance(suggestions, list):
                return [str(s) for s in suggestions]
            else:
                return [str(suggestions)]
        except (json.JSONDecodeError, ValueError):
            # Extract from text format
            lines = response.strip().split('\n')
            suggestions = []
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    suggestions.append(line.strip('- ').strip())
            return suggestions[:5] if suggestions else ["Review task requirements"]
    
    async def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        Generate a completion for the given prompt
        
        Args:
            prompt: The prompt to complete
            max_tokens: Maximum tokens in response
            
        Returns:
            The completion text
        """
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        self.max_tokens = max_tokens
        
        try:
            response = await self._call_openai(messages)
            return response
        except Exception as e:
            logger.error(f"OpenAI completion failed: {e}")
            raise
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()