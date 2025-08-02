"""
Data models for the Advanced PRD Parser.

This module contains the data classes used to structure PRD analysis results,
task generation results, and project constraints.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.models import Task


@dataclass
class PRDAnalysis:
    """Deep analysis of a PRD document."""

    functional_requirements: List[Dict[str, Any]]
    non_functional_requirements: List[Dict[str, Any]]
    technical_constraints: List[str]
    business_objectives: List[str]
    user_personas: List[Dict[str, Any]]
    success_metrics: List[str]
    implementation_approach: str
    complexity_assessment: Dict[str, Any]
    risk_factors: List[Dict[str, Any]]
    confidence: float


@dataclass
class TaskGenerationResult:
    """Result of PRD-to-tasks conversion."""

    tasks: List[Task]
    task_hierarchy: Dict[str, List[str]]  # parent_id -> [child_ids]
    dependencies: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    estimated_timeline: Dict[str, Any]
    resource_requirements: Dict[str, Any]
    success_criteria: List[str]
    generation_confidence: float


@dataclass
class ProjectConstraints:
    """Constraints for task generation."""

    deadline: Optional[datetime] = None
    budget_limit: Optional[float] = None
    team_size: int = 3
    available_skills: Optional[List[str]] = None
    technology_constraints: Optional[List[str]] = None
    quality_requirements: Optional[Dict[str, Any]] = None
    deployment_target: str = "local"  # local, dev, prod, remote

    def __post_init__(self) -> None:
        """Initialize optional fields and validate constraints."""
        if self.available_skills is None:
            self.available_skills = []
        if self.technology_constraints is None:
            self.technology_constraints = []
        if self.quality_requirements is None:
            self.quality_requirements = {}
        # Validate deployment target
        if self.deployment_target not in ["local", "dev", "prod", "remote"]:
            self.deployment_target = "local"
