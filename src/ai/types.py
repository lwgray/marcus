"""
Shared types and data classes for Marcus AI

Contains data structures used across multiple AI components
to avoid circular imports.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from src.core.models import Task


@dataclass
class AnalysisContext:
    """Context for AI analysis operations"""
    task: Task
    project_context: Dict[str, Any]
    historical_data: List[Dict[str, Any]]
    team_context: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class AIInsights:
    """AI-generated insights about a task or decision"""
    task_intent: str
    semantic_dependencies: List[str]
    risk_factors: List[str]
    suggestions: List[str]
    confidence: float
    reasoning: str
    risk_assessment: Dict[str, Any]


@dataclass
class HybridAnalysis:
    """Result of hybrid rule-based + AI analysis"""
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
    """Result from rule-based analysis"""
    is_valid: bool
    confidence: float
    reason: str
    safety_critical: bool = False
    mandatory: bool = False


@dataclass
class AIOptimizationResult:
    """Result of AI optimization analysis"""
    confidence: float
    optimization_score: float
    improvements: List[str]
    semantic_confidence: Optional[float] = None
    risk_mitigation: Optional[List[str]] = None
    estimated_completion_time: Optional[float] = None


@dataclass
class AssignmentDecision:
    """Final decision on task assignment"""
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
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class AssignmentContext:
    """Context for assignment decision"""
    task: Task
    agent_id: str
    agent_status: Dict[str, Any]
    available_tasks: List[Task]
    project_context: Dict[str, Any]
    team_status: Dict[str, Any]