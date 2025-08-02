"""
Advanced PRD Parser for Marcus Phase 4.

Transform natural language requirements into actionable tasks with
deep understanding, intelligent task breakdown, and risk assessment.
"""

# Core exports
from .advanced_parser import AdvancedPRDParser
from .models import PRDAnalysis, ProjectConstraints, TaskGenerationResult

__all__ = [
    "AdvancedPRDParser",
    "PRDAnalysis",
    "TaskGenerationResult",
    "ProjectConstraints",
]
