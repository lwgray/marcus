"""
Base LLM Provider Interface

Defines the interface that all LLM providers must implement.
Separated to avoid circular imports.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from dataclasses import dataclass

from src.core.models import Task


@dataclass
class SemanticAnalysis:
    """Result of semantic task analysis"""
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
    """Semantic dependency relationship"""
    dependent_task_id: str
    dependency_task_id: str
    confidence: float
    reasoning: str
    dependency_type: str  # 'logical', 'technical', 'temporal'


@dataclass
class EffortEstimate:
    """AI-powered effort estimation"""
    estimated_hours: float
    confidence: float
    factors: List[str]
    similar_tasks: List[str]
    risk_multiplier: float


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""
    
    @abstractmethod
    async def analyze_task(self, task: Task, context: Dict[str, Any]) -> SemanticAnalysis:
        """Analyze task semantics"""
        pass
    
    @abstractmethod
    async def infer_dependencies(self, tasks: List[Task]) -> List[SemanticDependency]:
        """Infer semantic dependencies between tasks"""
        pass
    
    @abstractmethod
    async def generate_enhanced_description(self, task: Task, context: Dict[str, Any]) -> str:
        """Generate enhanced task description"""
        pass
    
    @abstractmethod
    async def estimate_effort(self, task: Task, context: Dict[str, Any]) -> EffortEstimate:
        """Estimate task effort"""
        pass
    
    @abstractmethod
    async def analyze_blocker(self, task: Task, blocker: str, context: Dict[str, Any]) -> List[str]:
        """Analyze blocker and suggest solutions"""
        pass