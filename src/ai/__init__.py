"""
Marcus AI Integration Package

Provides AI-enhanced intelligence while preserving rule-based safety guarantees.
Implements hybrid decision making that combines deterministic logic with
semantic understanding and intelligent optimization.
"""

from .core.ai_engine import MarcusAIEngine
from .decisions.hybrid_framework import HybridDecisionFramework
from .providers.llm_abstraction import LLMAbstraction
from .types import AnalysisContext, AssignmentDecision, HybridAnalysis

__all__ = [
    "MarcusAIEngine",
    "LLMAbstraction",
    "HybridDecisionFramework",
    "HybridAnalysis",
    "AnalysisContext",
    "AssignmentDecision",
]
