"""
AI domain fixtures for Marcus testing.

Provides real AI-related objects for testing AI components,
analysis engines, and enrichment systems without external API calls.
"""

from datetime import datetime
from typing import Any, Dict, List

import pytest

from src.ai.enrichment.intelligent_enricher import EnhancementResult, ProjectContext
from src.ai.providers.base_provider import EffortEstimate, SemanticAnalysis


@pytest.fixture
def sample_semantic_analysis():
    """Create a real semantic analysis result for testing."""
    return SemanticAnalysis(
        complexity_score=0.75,
        technical_keywords=["authentication", "oauth", "security", "jwt", "hash"],
        domain_area="backend",
        estimated_effort=8.0,
        confidence=0.85,
        key_concepts=["user management", "security", "authentication flow"],
        dependencies=["database", "encryption library"],
        risks=["security vulnerabilities", "oauth configuration complexity"],
    )


@pytest.fixture
def sample_effort_estimate():
    """Create a real effort estimate for testing."""
    return EffortEstimate(
        total_hours=12.5,
        confidence_level=0.8,
        breakdown={
            "design": 2.0,
            "implementation": 8.0,
            "testing": 1.5,
            "documentation": 1.0,
        },
        complexity_factors=["oauth integration", "security requirements"],
        assumptions=["existing user model", "standard authentication flow"],
    )


@pytest.fixture
def sample_project_context():
    """Create a real project context for AI operations."""
    return ProjectContext(
        project_name="User Management System",
        technology_stack=["python", "fastapi", "postgresql", "react"],
        team_composition={
            "backend_developers": 2,
            "frontend_developers": 1,
            "devops": 1,
        },
        project_phase="implementation",
        deadline=datetime.now().isoformat(),
        complexity_level="medium",
        domain="web_application",
        existing_tasks=[
            {"id": "task-001", "name": "Setup database", "status": "done"},
            {"id": "task-002", "name": "Create API endpoints", "status": "in_progress"},
        ],
    )


@pytest.fixture
def sample_enhancement_result():
    """Create a real enhancement result for testing."""
    return EnhancementResult(
        original_task_id="task-001",
        enhanced_description="Implement user authentication system with OAuth 2.0 support, including login, signup, password reset, and JWT token management",
        suggested_labels=["backend", "security", "authentication", "oauth"],
        confidence_score=0.87,
        estimated_effort=12.0,
        complexity_assessment="medium-high",
        risk_factors=["oauth configuration", "security implementation"],
        dependencies=["user database schema", "encryption library"],
        acceptance_criteria=[
            "Users can register with email and password",
            "OAuth login works with Google and GitHub",
            "JWT tokens are properly generated and validated",
            "Password reset functionality works",
            "All authentication endpoints are secured",
        ],
        technical_notes="Consider implementing rate limiting and account lockout for security",
    )


@pytest.fixture
def ai_analysis_context():
    """Create context for AI analysis operations."""
    return {
        "project_domain": "web_development",
        "technical_stack": ["python", "javascript", "postgresql"],
        "team_expertise": ["backend", "frontend", "databases"],
        "project_complexity": "medium",
        "current_phase": "implementation",
        "available_resources": ["development team", "staging environment"],
        "constraints": ["2-week deadline", "security requirements"],
    }


@pytest.fixture
def enrichment_settings():
    """Create real enrichment settings for testing."""
    return {
        "enhancement_confidence_threshold": 0.7,
        "max_description_length": 500,
        "max_acceptance_criteria": 5,
        "enable_technical_analysis": True,
        "enable_risk_assessment": True,
        "enable_dependency_detection": True,
        "effort_estimation_model": "hybrid",
    }
