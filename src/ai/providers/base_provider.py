"""
Base LLM Provider Interface.

Defines the interface that all LLM providers must implement.
Separated to avoid circular imports.

This module provides the abstract base class and data structures
for implementing LLM providers (OpenAI, Anthropic, etc.).

Classes
-------
SemanticAnalysis
    Result of semantic task analysis by LLM
SemanticDependency
    Semantic relationship between tasks
EffortEstimate
    AI-powered effort estimation result
BaseLLMProvider
    Abstract base class for LLM providers

Examples
--------
>>> class CustomProvider(BaseLLMProvider):
...     async def analyze_task(self, task, context):
...         # Custom implementation
...         return SemanticAnalysis(...)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List

from src.core.models import Task


@dataclass
class SemanticAnalysis:
    """
    Result of semantic task analysis.

    Contains LLM's understanding of task meaning and implications.

    Attributes
    ----------
    task_intent : str
        LLM's interpretation of what the task aims to achieve
    semantic_dependencies : list of str
        Tasks that logically should complete before this one
    risk_factors : list of str
        Identified risks or complexity factors
    suggestions : list of str
        LLM-generated improvement suggestions
    confidence : float
        Model's confidence in analysis (0.0-1.0)
    reasoning : str
        Explanation of the analysis logic
    risk_assessment : dict
        Detailed risk breakdown by category
    fallback_used : bool
        Whether a fallback model was used
    """

    task_intent: str
    semantic_dependencies: List[str]
    risk_factors: List[str]
    suggestions: List[str]
    confidence: float
    reasoning: str
    risk_assessment: Dict[str, Any]
    fallback_used: bool = False


@dataclass
class SemanticDependency:
    """
    Semantic dependency relationship between tasks.

    Represents LLM-inferred dependencies based on task meaning.

    Attributes
    ----------
    dependent_task_id : str
        ID of task that depends on another
    dependency_task_id : str
        ID of task that must complete first
    confidence : float
        Confidence in this dependency (0.0-1.0)
    reasoning : str
        Explanation of why dependency exists
    dependency_type : str
        Type of dependency: 'logical', 'technical', or 'temporal'

    Examples
    --------
    >>> dep = SemanticDependency(
    ...     dependent_task_id="deploy-api",
    ...     dependency_task_id="test-api",
    ...     confidence=0.95,
    ...     reasoning="Deployment requires successful tests",
    ...     dependency_type="logical"
    ... )
    """

    dependent_task_id: str
    dependency_task_id: str
    confidence: float
    reasoning: str
    dependency_type: str  # 'logical', 'technical', 'temporal'


@dataclass
class EffortEstimate:
    """
    AI-powered effort estimation.

    Provides intelligent time estimates based on task analysis.

    Attributes
    ----------
    estimated_hours : float
        Estimated hours to complete the task
    confidence : float
        Confidence in the estimate (0.0-1.0)
    factors : list of str
        Factors considered in the estimation
    similar_tasks : list of str
        IDs of similar historical tasks used for reference
    risk_multiplier : float
        Risk adjustment factor (1.0 = no risk, >1.0 = added risk)

    Notes
    -----
    The final estimate should be: estimated_hours * risk_multiplier
    """

    estimated_hours: float
    confidence: float
    factors: List[str]
    similar_tasks: List[str]
    risk_multiplier: float


class BaseLLMProvider(ABC):
    """
    Base class for LLM providers.

    Defines the interface that all LLM providers must implement
    to integrate with Marcus AI system.

    Methods
    -------
    analyze_task(task, context)
        Perform semantic analysis on a task
    infer_dependencies(tasks)
        Infer logical dependencies between tasks
    generate_enhanced_description(task, context)
        Create improved task descriptions
    estimate_effort(task, context)
        Estimate task completion time
    analyze_blocker(task, blocker, context)
        Analyze blockers and suggest solutions

    Notes
    -----
    All methods are async to support various LLM APIs.
    Implementations should handle rate limiting and retries.

    Examples
    --------
    >>> provider = OpenAIProvider(api_key="...")
    >>> analysis = await provider.analyze_task(task, context)
    >>> print(f"Task intent: {analysis.task_intent}")
    """

    @abstractmethod
    async def analyze_task(
        self, task: Task, context: Dict[str, Any]
    ) -> SemanticAnalysis:
        """
        Analyze task semantics using LLM.

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
        pass

    @abstractmethod
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
            Inferred dependency relationships

        Notes
        -----
        This supplements rule-based dependency detection with
        semantic understanding of task relationships.
        """
        pass

    @abstractmethod
    async def generate_enhanced_description(
        self, task: Task, context: Dict[str, Any]
    ) -> str:
        """
        Generate enhanced task description.

        Parameters
        ----------
        task : Task
            Task needing description enhancement
        context : dict
            Project context for better understanding

        Returns
        -------
        str
            Enhanced description with more clarity and detail
        """
        pass

    @abstractmethod
    async def estimate_effort(
        self, task: Task, context: Dict[str, Any]
    ) -> EffortEstimate:
        """
        Estimate task effort using AI analysis.

        Parameters
        ----------
        task : Task
            Task to estimate
        context : dict
            Historical data and project context

        Returns
        -------
        EffortEstimate
            AI-powered effort estimation with confidence
        """
        pass

    @abstractmethod
    async def analyze_blocker(
        self, task: Task, blocker: str, context: Dict[str, Any]
    ) -> List[str]:
        """
        Analyze blocker and suggest solutions.

        Parameters
        ----------
        task : Task
            The blocked task
        blocker : str
            Description of what's blocking progress
        context : dict
            Additional context about the situation

        Returns
        -------
        list of str
            Prioritized list of solution suggestions
        """
        pass
