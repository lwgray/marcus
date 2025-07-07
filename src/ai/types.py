"""
Shared types and data classes for Marcus AI.

This module contains data structures used across multiple AI components
to avoid circular imports. These types define the contracts between
different parts of the AI system.

Classes
-------
AnalysisContext
    Context data for AI analysis operations
AIInsights
    AI-generated insights about tasks and decisions
HybridAnalysis
    Combined result of rule-based and AI analysis
RuleBasedResult
    Result from deterministic rule-based analysis
AIOptimizationResult
    AI-powered optimization suggestions
AssignmentDecision
    Final decision on task assignment
AssignmentContext
    Full context for assignment decisions

Notes
-----
All dataclasses are frozen where appropriate to ensure immutability
of analysis results. Timestamps are automatically added to decisions
for audit trails.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from src.core.models import Task


@dataclass
class AnalysisContext:
    """
    Context for AI analysis operations.
    
    Provides all necessary information for making intelligent
    task assignment decisions.
    
    Attributes
    ----------
    task : Task
        The task being analyzed for assignment
    project_context : dict
        Current project state including available and assigned tasks
    historical_data : list of dict
        Historical performance and assignment data
    team_context : dict, optional
        Team composition and skill information
    constraints : dict, optional
        Project constraints (deadlines, resources, etc.)
    
    Examples
    --------
    >>> context = AnalysisContext(
    ...     task=task_to_assign,
    ...     project_context={"available_tasks": tasks},
    ...     historical_data=performance_history
    ... )
    """
    task: Task
    project_context: Dict[str, Any]
    historical_data: List[Dict[str, Any]]
    team_context: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class AIInsights:
    """
    AI-generated insights about a task or decision.
    
    Contains semantic understanding and risk analysis from AI models.
    
    Attributes
    ----------
    task_intent : str
        AI's understanding of what the task aims to achieve
    semantic_dependencies : list of str
        Inferred dependencies based on task meaning
    risk_factors : list of str
        Identified risks or potential issues
    suggestions : list of str
        AI-generated improvement suggestions
    confidence : float
        AI model's confidence in its analysis (0.0-1.0)
    reasoning : str
        Explanation of AI's analysis process
    risk_assessment : dict
        Detailed risk breakdown by category
    
    Notes
    -----
    These insights supplement but never override rule-based decisions.
    """
    task_intent: str
    semantic_dependencies: List[str]
    risk_factors: List[str]
    suggestions: List[str]
    confidence: float
    reasoning: str
    risk_assessment: Dict[str, Any]


@dataclass
class HybridAnalysis:
    """
    Result of hybrid rule-based + AI analysis.
    
    Combines deterministic rules with AI enhancement for optimal decisions.
    
    Attributes
    ----------
    allow_assignment : bool
        Final decision on whether to allow task assignment
    confidence : float
        Combined confidence score (0.0-1.0)
    reason : str
        Human-readable explanation of the decision
    safety_critical : bool
        Whether safety rules were involved in decision
    ai_confidence : float, optional
        AI model's confidence if AI was used
    ai_insights : AIInsights, optional
        Detailed AI analysis if available
    fallback_mode : bool
        Whether system fell back to rules-only mode
    confidence_breakdown : dict, optional
        Component confidence scores and weights
    optimization_score : float, optional
        AI's optimization score for this assignment
    
    Examples
    --------
    >>> result = HybridAnalysis(
    ...     allow_assignment=True,
    ...     confidence=0.85,
    ...     reason="All checks passed with high confidence"
    ... )
    """
    allow_assignment: bool
    confidence: float
    reason: str
    safety_critical: bool = False
    ai_confidence: Optional[float] = None
    ai_insights: Optional[AIInsights] = None
    fallback_mode: bool = False
    confidence_breakdown: Optional[Dict[str, float]] = None
    optimization_score: Optional[float] = None


@dataclass
class RuleBasedResult:
    """
    Result from rule-based analysis.
    
    Represents deterministic validation results that provide safety guarantees.
    
    Attributes
    ----------
    is_valid : bool
        Whether the assignment passes all rules
    confidence : float
        Rule engine confidence (typically high: 0.8-1.0)
    reason : str
        Explanation of the validation result
    safety_critical : bool
        Whether this involves safety-critical rules
    mandatory : bool
        Whether this rule cannot be overridden
    
    Notes
    -----
    When mandatory=True, the decision cannot be changed by AI.
    """
    is_valid: bool
    confidence: float
    reason: str
    safety_critical: bool = False
    mandatory: bool = False


@dataclass
class AIOptimizationResult:
    """
    Result of AI optimization analysis.
    
    Contains AI-powered suggestions for optimizing task execution.
    
    Attributes
    ----------
    confidence : float
        AI's confidence in optimization suggestions (0.0-1.0)
    optimization_score : float
        Score indicating assignment quality (0.0-1.0)
    improvements : list of str
        Suggested improvements for task execution
    semantic_confidence : float, optional
        Confidence in semantic understanding
    risk_mitigation : list of str, optional
        Strategies to mitigate identified risks
    estimated_completion_time : float, optional
        AI estimate of task duration in hours
    """
    confidence: float
    optimization_score: float
    improvements: List[str]
    semantic_confidence: Optional[float] = None
    risk_mitigation: Optional[List[str]] = None
    estimated_completion_time: Optional[float] = None


@dataclass
class AssignmentDecision:
    """
    Final decision on task assignment.
    
    Represents the complete decision including rule validation,
    AI enhancement, and audit information.
    
    Attributes
    ----------
    allow : bool
        Whether to allow the assignment
    confidence : float
        Overall confidence in decision (0.0-1.0)
    reason : str
        Primary reason for the decision
    ai_suggestions : AIOptimizationResult, optional
        AI optimization suggestions if rules passed
    optimization_score : float, optional
        AI's score for assignment quality
    confidence_breakdown : dict, optional
        Detailed confidence components
    safety_critical : bool
        Whether safety rules were involved
    mandatory_rule_applied : bool
        Whether mandatory rules were applied
    timestamp : datetime
        When the decision was made (auto-set)
    
    Methods
    -------
    __post_init__()
        Automatically sets timestamp if not provided
    
    Examples
    --------
    >>> decision = AssignmentDecision(
    ...     allow=True,
    ...     confidence=0.92,
    ...     reason="All validations passed"
    ... )
    >>> print(f"Decision at {decision.timestamp}: {decision.allow}")
    """
    allow: bool
    confidence: float
    reason: str
    
    # AI enhancements (only when rules allow)
    ai_suggestions: Optional[AIOptimizationResult] = None
    optimization_score: Optional[float] = None
    
    # Confidence breakdown
    confidence_breakdown: Optional[Dict[str, float]] = None
    
    # Safety tracking
    safety_critical: bool = False
    mandatory_rule_applied: bool = False
    
    # Context
    timestamp: datetime = None
    
    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class AssignmentContext:
    """
    Context for assignment decision.
    
    Complete context needed to make informed assignment decisions.
    
    Attributes
    ----------
    task : Task
        Task being considered for assignment
    agent_id : str
        ID of agent to potentially assign to
    agent_status : dict
        Current status and workload of the agent
    available_tasks : list of Task
        All unassigned tasks in the project
    project_context : dict
        Project metadata and configuration
    team_status : dict
        Status of all team members and assignments
    
    Notes
    -----
    This context is passed through the entire decision pipeline
    to ensure all components have necessary information.
    """
    task: Task
    agent_id: str
    agent_status: Dict[str, Any]
    available_tasks: List[Task]
    project_context: Dict[str, Any]
    team_status: Dict[str, Any]