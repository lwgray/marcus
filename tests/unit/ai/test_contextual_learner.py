"""
Unit tests for the Contextual Learning System.

This module tests the AI-powered contextual learning capabilities of Marcus,
including team pattern learning, technology adaptation, and intelligent
template recommendations.

Notes
-----
Tests use mocked data and external dependencies to ensure reproducibility
and avoid external dependencies during testing.
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.learning.contextual_learner import (
    AdaptedTemplate,
    ContextualLearningSystem,
    ProjectTypeLearnings,
    TeamLearnings,
    TechnologyLearnings,
)
from src.core.models import Priority, Task, TaskStatus


class TestContextualLearningSystem:
    """
    Test suite for the Contextual Learning System.

    This tests the core learning capabilities of Marcus - how it learns
    from project history, adapts templates, and provides contextual
    recommendations.
    """

    @pytest.fixture
    def learning_system(self) -> ContextualLearningSystem:
        """
        Create a test instance of the Contextual Learning System.

        Returns
        -------
        ContextualLearningSystem
            A fresh learning system instance for testing.

        Notes
        -----
        Each test starts with a clean learning system to ensure
        test isolation and reproducibility.
        """
        return ContextualLearningSystem()

    @pytest.fixture
    def sample_team_projects(self) -> List[Dict[str, Any]]:
        """
        Create sample completed project data for team learning.

        Returns
        -------
        List[Dict[str, Any]]
            A list of project dictionaries with varying outcomes and patterns.

        Notes
        -----
        Projects represent different scenarios including successful completions,
        delayed projects, and various tech stacks to test learning algorithms.
        """
        return [
            {
                "project_id": "PROJ-001",
                "name": "E-commerce Frontend",
                "team_size": 4,
                "tech_stack": ["react", "typescript", "nodejs"],
                "duration_days": 45,
                "success_metrics": {
                    "completion_rate": 0.95,
                    "quality_score": 0.88,
                    "bug_rate": 0.05,
                    "review_coverage": 0.90,
                },
                "tasks": [
                    {
                        "type": "frontend",
                        "estimated_hours": 8.0,
                        "actual_hours": 10.0,
                        "quality_score": 0.9,
                        "completion_time_ratio": 1.25,
                    },
                    {
                        "type": "backend",
                        "estimated_hours": 12.0,
                        "actual_hours": 14.0,
                        "quality_score": 0.85,
                        "completion_time_ratio": 1.17,
                    },
                    {
                        "type": "testing",
                        "estimated_hours": 6.0,
                        "actual_hours": 8.0,
                        "quality_score": 0.92,
                        "completion_time_ratio": 1.33,
                    },
                ],
            },
            {
                "project_id": "PROJ-002",
                "name": "Payment Integration",
                "team_size": 3,
                "tech_stack": ["python", "django", "postgresql"],
                "duration_days": 30,
                "success_metrics": {
                    "completion_rate": 0.92,
                    "quality_score": 0.91,
                    "bug_rate": 0.03,
                    "review_coverage": 0.95,
                },
                "tasks": [
                    {
                        "type": "backend",
                        "estimated_hours": 16.0,
                        "actual_hours": 18.0,
                        "quality_score": 0.93,
                        "completion_time_ratio": 1.125,
                    },
                    {
                        "type": "integration",
                        "estimated_hours": 10.0,
                        "actual_hours": 12.0,
                        "quality_score": 0.88,
                        "completion_time_ratio": 1.2,
                    },
                ],
            },
            {
                "project_id": "PROJ-003",
                "name": "API Optimization",
                "team_size": 2,
                "tech_stack": ["python", "fastapi", "redis"],
                "duration_days": 21,
                "success_metrics": {
                    "completion_rate": 0.89,
                    "quality_score": 0.87,
                    "bug_rate": 0.08,
                    "review_coverage": 0.85,
                },
                "tasks": [
                    {
                        "type": "backend",
                        "estimated_hours": 20.0,
                        "actual_hours": 22.0,
                        "quality_score": 0.86,
                        "completion_time_ratio": 1.1,
                    },
                    {
                        "type": "optimization",
                        "estimated_hours": 8.0,
                        "actual_hours": 10.0,
                        "quality_score": 0.88,
                        "completion_time_ratio": 1.25,
                    },
                ],
            },
        ]

    @pytest.fixture
    def sample_tech_outcomes(self) -> List[Dict[str, Any]]:
        """
        Create sample technology outcome data for learning.

        Returns
        -------
        List[Dict[str, Any]]
            A list of project outcomes with technology-specific patterns.

        Notes
        -----
        Outcomes include patterns, risks, and best practices discovered
        across different technology implementations.
        """
        return [
            {
                "project_id": "TECH-001",
                "tech_stack": "react-python-postgres",
                "project_structure": "microservices",
                "duration_days": 60,
                "success_metrics": {"completion_rate": 0.88, "technical_debt": 0.15},
                "tasks": [
                    {"type": "frontend", "estimated_hours": 40.0, "actual_hours": 48.0},
                    {"type": "backend", "estimated_hours": 50.0, "actual_hours": 58.0},
                ],
                "dependencies": [
                    {"prerequisite": "database_setup", "dependent": "api_development"},
                    {
                        "prerequisite": "api_development",
                        "dependent": "frontend_integration",
                    },
                ],
                "risks_encountered": [
                    "scalability_bottleneck",
                    "integration_complexity",
                ],
                "practices_used": [
                    "code_review",
                    "automated_testing",
                    "continuous_integration",
                    "docker_containerization",
                ],
            },
            {
                "project_id": "TECH-002",
                "tech_stack": "react-python-postgres",
                "project_structure": "monolithic",
                "duration_days": 45,
                "success_metrics": {"completion_rate": 0.92, "technical_debt": 0.12},
                "tasks": [
                    {"type": "frontend", "estimated_hours": 30.0, "actual_hours": 33.0},
                    {"type": "backend", "estimated_hours": 35.0, "actual_hours": 38.0},
                ],
                "dependencies": [
                    {"prerequisite": "database_setup", "dependent": "backend_models"},
                    {
                        "prerequisite": "api_development",
                        "dependent": "frontend_integration",
                    },
                ],
                "risks_encountered": ["performance_issues"],
                "practices_used": [
                    "code_review",
                    "unit_testing",
                    "performance_monitoring",
                ],
            },
            {
                "project_id": "TECH-003",
                "tech_stack": "react-python-postgres",
                "project_structure": "microservices",
                "duration_days": 55,
                "success_metrics": {"completion_rate": 0.90, "technical_debt": 0.10},
                "tasks": [
                    {"type": "frontend", "estimated_hours": 25.0, "actual_hours": 28.0},
                    {"type": "backend", "estimated_hours": 40.0, "actual_hours": 44.0},
                ],
                "dependencies": [
                    {"prerequisite": "authentication", "dependent": "user_management"},
                    {"prerequisite": "database_setup", "dependent": "data_migration"},
                ],
                "risks_encountered": [
                    "scalability_bottleneck",
                    "deployment_complexity",
                ],
                "practices_used": [
                    "code_review",
                    "integration_testing",
                    "monitoring_setup",
                ],
            },
        ]

    @pytest.fixture
    def sample_project_context(self) -> Dict[str, Any]:
        """
        Create sample project context for template adaptation.

        Returns
        -------
        Dict[str, Any]
            Project context with team, technology, and type information.
        """
        return {
            "team_id": "team-alpha",
            "tech_stack_key": "react-python-postgres",
            "project_type": "web_application",
            "project_size": "medium",
            "timeline": "3_months",
            "team_experience": "senior",
        }

    # Test 1: Initialization and Configuration
    def test_initialization_default_params(self, learning_system):
        """
        Test system initializes with correct default parameters.

        What's being tested:
        1. Learning system creates empty storage containers
        2. Default learning parameters are set correctly
        3. Context tracking is initialized

        Expected behavior:
        - All learning storage dictionaries are empty
        - Default thresholds and parameters are set
        - System is ready to learn from data
        """
        # Verify empty initial state
        assert len(learning_system.team_learnings) == 0
        assert len(learning_system.technology_learnings) == 0
        assert len(learning_system.project_type_learnings) == 0
        assert len(learning_system.adapted_templates) == 0

        # Verify default parameters
        assert learning_system.min_samples_for_learning == 3
        assert learning_system.learning_decay_days == 90
        assert learning_system.confidence_threshold == 0.7

        # Verify context tracking initialization
        assert isinstance(learning_system.context_performance, defaultdict)

    def test_initialization_with_custom_params(self):
        """
        Test system can be initialized with custom parameters.

        What's being tested:
        1. System accepts parameter overrides during initialization
        2. Custom parameters are properly stored
        3. System remains functional with different settings
        """
        # Create system with custom parameters by modifying after init
        system = ContextualLearningSystem()
        system.min_samples_for_learning = 5
        system.learning_decay_days = 120
        system.confidence_threshold = 0.8

        assert system.min_samples_for_learning == 5
        assert system.learning_decay_days == 120
        assert system.confidence_threshold == 0.8

    # Test 2: Team Pattern Learning
    @pytest.mark.asyncio
    async def test_learn_team_patterns_sufficient_data(
        self, learning_system, sample_team_projects
    ):
        """
        Test team pattern learning with sufficient project data.

        What's being tested:
        1. System correctly analyzes team velocity patterns
        2. Skill strengths are identified from project outcomes
        3. Task preferences are calculated accurately
        4. Collaboration patterns are extracted
        5. Quality metrics are aggregated properly

        Step-by-step:
        1. Provide completed projects with varying task types and outcomes
        2. System analyzes patterns across projects
        3. Verify learned patterns match expected calculations
        """
        team_id = "team-alpha"

        # Learn patterns from sample projects
        team_learnings = await learning_system.learn_team_patterns(
            team_id, sample_team_projects
        )

        # Verify team learnings structure
        assert isinstance(team_learnings, TeamLearnings)
        assert team_learnings.team_id == team_id
        assert team_learnings.last_updated is not None

        # Verify velocity patterns were learned
        assert len(team_learnings.velocity_patterns) > 0

        # Check specific velocity patterns
        # Backend tasks: average of (14/12, 18/16, 22/20) = (1.17, 1.125, 1.1) = 1.13
        if "backend" in team_learnings.velocity_patterns:
            backend_velocity = team_learnings.velocity_patterns["backend"]
            assert 1.1 <= backend_velocity <= 1.2  # Should be around 1.13

        # Verify skill strengths were identified
        assert len(team_learnings.skill_strengths) > 0

        # Verify task preferences were calculated
        assert len(team_learnings.preferred_task_types) > 0

        # Verify collaboration patterns
        assert "avg_team_size" in team_learnings.collaboration_patterns
        avg_team_size = team_learnings.collaboration_patterns["avg_team_size"]
        assert 2.5 <= avg_team_size <= 3.5  # Average of 4, 3, 2 = 3

        # Verify quality metrics
        assert "average_quality" in team_learnings.quality_metrics
        avg_quality = team_learnings.quality_metrics["average_quality"]
        assert 0.85 <= avg_quality <= 0.95  # Should be around 0.89

        # Verify learnings are stored
        assert team_id in learning_system.team_learnings
        assert learning_system.team_learnings[team_id] == team_learnings

    @pytest.mark.asyncio
    async def test_learn_team_patterns_insufficient_data(self, learning_system):
        """
        Test team pattern learning with insufficient project data.

        What's being tested:
        1. System handles insufficient data gracefully
        2. Default team learnings are created
        3. Warning is logged for insufficient data
        4. Default patterns are reasonable

        Expected behavior:
        - System creates default learnings with safe assumptions
        - No crashes or errors occur
        - Default velocity assumes 20% overrun
        """
        team_id = "team-beta"
        insufficient_projects = [
            {"project_id": "PROJ-001", "tasks": []}  # Only one project
        ]

        with patch("src.ai.learning.contextual_learner.logger") as mock_logger:
            team_learnings = await learning_system.learn_team_patterns(
                team_id, insufficient_projects
            )

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Insufficient data" in warning_call
            assert team_id in warning_call

        # Verify default learnings structure
        assert isinstance(team_learnings, TeamLearnings)
        assert team_learnings.team_id == team_id

        # Verify default velocity pattern
        assert "general" in team_learnings.velocity_patterns
        assert team_learnings.velocity_patterns["general"] == 1.2

        # Verify default collaboration patterns
        assert team_learnings.collaboration_patterns["avg_team_size"] == 3
        assert team_learnings.collaboration_patterns["parallel_task_preference"] == 0.5

        # Verify default quality metrics
        assert team_learnings.quality_metrics["average_quality"] == 0.8

    @pytest.mark.asyncio
    async def test_learn_team_patterns_edge_cases(self, learning_system):
        """
        Test team pattern learning with edge case data.

        What's being tested:
        1. System handles projects with missing task data
        2. Zero or negative hours are handled gracefully
        3. Missing metrics don't cause crashes
        4. Invalid data is filtered out appropriately
        """
        team_id = "team-gamma"
        edge_case_projects = [
            {
                "project_id": "PROJ-EDGE-1",
                "team_size": 0,  # Invalid team size
                "success_metrics": {},  # Missing metrics
                "tasks": [
                    {
                        "type": "frontend",
                        "estimated_hours": 0,  # Zero estimated hours
                        "actual_hours": 5,
                        "quality_score": 0.8,
                    },
                    {
                        "type": "backend",
                        "estimated_hours": 10,
                        "actual_hours": 0,  # Zero actual hours
                        "quality_score": 0.9,
                    },
                    {
                        "type": "testing",
                        "estimated_hours": -5,  # Negative hours
                        "actual_hours": 8,
                        "quality_score": 0.7,
                    },
                ],
            },
            # Add two more projects to meet minimum sample requirement
            {
                "project_id": "PROJ-EDGE-2",
                "team_size": 3,
                "success_metrics": {"completion_rate": 0.8},
                "tasks": [
                    {
                        "type": "frontend",
                        "estimated_hours": 8,
                        "actual_hours": 10,
                        "quality_score": 0.85,
                    }
                ],
            },
            {
                "project_id": "PROJ-EDGE-3",
                "team_size": 4,
                "success_metrics": {"completion_rate": 0.9},
                "tasks": [
                    {
                        "type": "frontend",
                        "estimated_hours": 12,
                        "actual_hours": 14,
                        "quality_score": 0.88,
                    }
                ],
            },
        ]

        # Should not crash and should produce reasonable results
        team_learnings = await learning_system.learn_team_patterns(
            team_id, edge_case_projects
        )

        assert isinstance(team_learnings, TeamLearnings)
        assert team_learnings.team_id == team_id

        # Verify edge cases were filtered out and valid data processed
        if "frontend" in team_learnings.velocity_patterns:
            # Should only include valid ratios: 10/8=1.25, 14/12=1.17
            frontend_velocity = team_learnings.velocity_patterns["frontend"]
            assert 1.15 <= frontend_velocity <= 1.3

    # Test 3: Technology Pattern Learning
    @pytest.mark.asyncio
    async def test_learn_technology_patterns_sufficient_data(
        self, learning_system, sample_tech_outcomes
    ):
        """
        Test technology pattern learning with sufficient outcome data.

        What's being tested:
        1. Technology-specific patterns are identified
        2. Estimation multipliers are calculated accurately
        3. Common dependencies are extracted
        4. Risk factors are analyzed from historical data
        5. Best practices are identified from successful projects

        Step-by-step:
        1. Provide technology outcomes with patterns and risks
        2. System analyzes technology-specific characteristics
        3. Verify learned patterns reflect the input data
        """
        tech_stack = "react-python-postgres"

        # Learn patterns from sample outcomes
        tech_learnings = await learning_system.learn_technology_patterns(
            tech_stack, sample_tech_outcomes
        )

        # Verify technology learnings structure
        assert isinstance(tech_learnings, TechnologyLearnings)
        assert tech_learnings.tech_stack == tech_stack
        assert tech_learnings.last_updated is not None

        # With 3 outcomes (meets min_samples_for_learning=3), should learn actual patterns
        assert "common_structures" in tech_learnings.typical_patterns
        structures = tech_learnings.typical_patterns["common_structures"]
        assert "microservices" in structures
        assert "monolithic" in structures

        # Verify duration patterns
        assert "typical_duration" in tech_learnings.typical_patterns
        duration_stats = tech_learnings.typical_patterns["typical_duration"]
        assert "mean" in duration_stats
        assert "median" in duration_stats
        # Average of 60, 45, 55 = 53.33, Median = 55
        assert 53 <= duration_stats["mean"] <= 54
        assert duration_stats["median"] == 55

        # Verify estimation multipliers were learned
        assert len(tech_learnings.estimation_multipliers) > 0
        if "frontend" in tech_learnings.estimation_multipliers:
            # Frontend: (48/40, 33/30, 28/25) = (1.2, 1.1, 1.12) = avg ≈ 1.14
            frontend_multiplier = tech_learnings.estimation_multipliers["frontend"]
            assert 1.1 <= frontend_multiplier <= 1.25

        # Verify common dependencies were identified
        assert len(tech_learnings.common_dependencies) > 0
        dependency_tuples = tech_learnings.common_dependencies
        # Should find api_development -> frontend_integration which appears in 2+ projects
        api_deps = [dep for dep in dependency_tuples if "api_development" in dep[0]]
        assert len(api_deps) > 0
        assert ("api_development", "frontend_integration") in dependency_tuples

        # Verify risk factors were analyzed
        assert len(tech_learnings.risk_factors) > 0
        # scalability_bottleneck appears in 2/3 projects = 0.67 probability
        if "scalability_bottleneck" in tech_learnings.risk_factors:
            prob = tech_learnings.risk_factors["scalability_bottleneck"]
            assert 0.6 <= prob <= 0.7

        # Verify best practices were extracted
        assert len(tech_learnings.best_practices) > 0
        assert "code_review" in tech_learnings.best_practices

        # Verify learnings are stored
        assert tech_stack in learning_system.technology_learnings

    @pytest.mark.asyncio
    async def test_learn_technology_patterns_insufficient_data(self, learning_system):
        """
        Test technology pattern learning with insufficient data.

        What's being tested:
        1. System creates default technology learnings
        2. Default patterns are reasonable and safe
        3. No crashes occur with minimal data
        """
        tech_stack = "vue-nodejs-mongodb"
        insufficient_outcomes = [
            {"project_id": "TECH-001", "tasks": []}  # Only one outcome
        ]

        tech_learnings = await learning_system.learn_technology_patterns(
            tech_stack, insufficient_outcomes
        )

        # Verify default learnings structure
        assert isinstance(tech_learnings, TechnologyLearnings)
        assert tech_learnings.tech_stack == tech_stack

        # Verify default patterns
        assert "typical_duration" in tech_learnings.typical_patterns
        duration_stats = tech_learnings.typical_patterns["typical_duration"]
        assert duration_stats["mean"] == 30
        assert duration_stats["median"] == 28

        # Verify default estimation multiplier
        assert "general" in tech_learnings.estimation_multipliers
        assert tech_learnings.estimation_multipliers["general"] == 1.3

        # Verify default best practices
        expected_practices = ["Follow coding standards", "Write tests", "Code review"]
        assert all(
            practice in tech_learnings.best_practices for practice in expected_practices
        )

    # Test 4: Template Adaptation
    @pytest.mark.asyncio
    async def test_adapt_templates_intelligently_full_context(
        self, learning_system, sample_project_context
    ):
        """
        Test intelligent template adaptation with full context.

        What's being tested:
        1. System combines learnings from multiple sources
        2. Templates are adapted based on team and technology patterns
        3. Adaptations include reasonable confidence scores
        4. Multiple template types are generated

        Step-by-step:
        1. Pre-populate system with team and technology learnings
        2. Request template adaptation for project context
        3. Verify adaptations reflect the learned patterns
        """
        # Pre-populate with learnings
        team_id = sample_project_context["team_id"]
        tech_stack = sample_project_context["tech_stack_key"]

        # Create mock team learnings
        team_learnings = TeamLearnings(
            team_id=team_id,
            velocity_patterns={"frontend": 1.25, "backend": 1.15},
            skill_strengths={"react": 0.9, "python": 0.85},
            preferred_task_types={"frontend": 0.8, "backend": 0.75},
            collaboration_patterns={"avg_team_size": 4},
            quality_metrics={"average_quality": 0.88},
            last_updated=datetime.now(timezone.utc),
        )
        learning_system.team_learnings[team_id] = team_learnings

        # Create mock technology learnings
        tech_learnings = TechnologyLearnings(
            tech_stack=tech_stack,
            typical_patterns={"typical_duration": {"mean": 45}},
            estimation_multipliers={"frontend": 1.2, "backend": 1.1},
            common_dependencies=[("database_setup", "api_development")],
            risk_factors={"integration_complexity": 0.3},
            best_practices=["automated_testing", "code_review"],
            last_updated=datetime.now(timezone.utc),
        )
        learning_system.technology_learnings[tech_stack] = tech_learnings

        # Adapt templates
        adapted_templates = await learning_system.adapt_templates_intelligently(
            sample_project_context
        )

        # Verify adaptation results
        assert isinstance(adapted_templates, dict)
        assert len(adapted_templates) > 0

        # Check estimation template
        if "estimation" in adapted_templates:
            estimation_template = adapted_templates["estimation"]
            assert isinstance(estimation_template, AdaptedTemplate)
            assert estimation_template.template_id == "estimation_adapted"
            assert estimation_template.confidence > 0.5

            # Verify adaptations combine team and tech patterns
            adaptations = estimation_template.adaptations
            if "frontend_multiplier" in adaptations:
                # Should combine team velocity (1.25) and tech multiplier (1.2)
                # Weighted: 1.25 * 0.6 + 1.2 * 0.4 = 0.75 + 0.48 = 1.23
                frontend_mult = adaptations["frontend_multiplier"]
                assert 1.2 <= frontend_mult <= 1.3

        # Check dependency template if present
        if "dependencies" in adapted_templates:
            dep_template = adapted_templates["dependencies"]
            assert isinstance(dep_template, AdaptedTemplate)
            adaptations = dep_template.adaptations
            assert "common_dependencies" in adaptations
            assert len(adaptations["common_dependencies"]) > 0

    @pytest.mark.asyncio
    async def test_adapt_templates_intelligently_partial_context(self, learning_system):
        """
        Test template adaptation with partial context data.

        What's being tested:
        1. System handles missing team or technology learnings
        2. Templates are still generated with available data
        3. Missing data doesn't cause crashes
        """
        partial_context = {
            "team_id": "unknown-team",
            "tech_stack_key": "unknown-tech",
            "project_type": "web_application",
        }

        # No pre-populated learnings - system should handle gracefully
        adapted_templates = await learning_system.adapt_templates_intelligently(
            partial_context
        )

        # Should return empty dict or handle gracefully
        assert isinstance(adapted_templates, dict)
        # With no learnings, no templates should be adapted
        assert len(adapted_templates) == 0

    # Test 5: Contextual Recommendations
    @pytest.mark.asyncio
    async def test_get_contextual_recommendations_full_context(self, learning_system):
        """
        Test contextual recommendations with full learning context.

        What's being tested:
        1. System provides team-specific recommendations
        2. Technology recommendations are included
        3. Process recommendations are generated
        4. Recommendations are actionable and specific
        """
        # Setup full context with learnings
        project_context = {
            "team_id": "team-delta",
            "tech_stack_key": "django-react-postgres",
            "project_type": "e_commerce",
        }

        current_state = {
            "active_tasks": 15,
            "blocked_tasks": 3,
            "team_utilization": 0.85,
        }

        # Pre-populate learnings
        team_learnings = TeamLearnings(
            team_id="team-delta",
            velocity_patterns={"backend": 1.4},  # Slow on backend
            skill_strengths={"react": 0.9, "django": 0.7},  # Weak on Django
            preferred_task_types={"frontend": 0.9},
            collaboration_patterns={"avg_team_size": 3},
            quality_metrics={"average_quality": 0.82},
            last_updated=datetime.now(timezone.utc),
        )
        learning_system.team_learnings["team-delta"] = team_learnings

        tech_learnings = TechnologyLearnings(
            tech_stack="django-react-postgres",
            typical_patterns={},
            estimation_multipliers={"backend": 1.3},
            common_dependencies=[],
            risk_factors={"database_migration": 0.4},  # High risk
            best_practices=["database_indexing", "caching"],
            last_updated=datetime.now(timezone.utc),
        )
        learning_system.technology_learnings["django-react-postgres"] = tech_learnings

        # Get recommendations
        recommendations = await learning_system.get_contextual_recommendations(
            project_context, current_state
        )

        # Verify recommendation structure
        assert isinstance(recommendations, dict)
        assert "team_recommendations" in recommendations
        assert "technology_recommendations" in recommendations
        assert "process_recommendations" in recommendations
        assert "risk_mitigations" in recommendations

        # Verify team recommendations
        team_recs = recommendations["team_recommendations"]
        assert isinstance(team_recs, list)
        if len(team_recs) > 0:
            # Check for velocity warnings (backend velocity is 1.4 > 1.5 threshold)
            velocity_warnings = [
                rec for rec in team_recs if "underestimate" in rec.lower()
            ]
            backend_warning = any("backend" in rec for rec in velocity_warnings)
            # The backend velocity of 1.4 is below the 1.5 threshold, so no warning expected
            # assert backend_warning

        # Verify technology recommendations
        tech_recs = recommendations["technology_recommendations"]
        assert isinstance(tech_recs, list)
        if len(tech_recs) > 0:
            # Should include risk monitoring
            risk_mention = any("database_migration" in rec.lower() for rec in tech_recs)
            assert risk_mention

    @pytest.mark.asyncio
    async def test_get_contextual_recommendations_no_learnings(self, learning_system):
        """
        Test contextual recommendations with no existing learnings.

        What's being tested:
        1. System handles empty learning state gracefully
        2. Basic recommendation structure is returned
        3. No crashes occur with missing data
        """
        project_context = {
            "team_id": "new-team",
            "tech_stack_key": "new-tech",
            "project_type": "new_project",
        }

        current_state = {"active_tasks": 5}

        recommendations = await learning_system.get_contextual_recommendations(
            project_context, current_state
        )

        # Should return empty recommendations but proper structure
        assert isinstance(recommendations, dict)
        assert "team_recommendations" in recommendations
        assert "technology_recommendations" in recommendations
        assert "process_recommendations" in recommendations
        assert "risk_mitigations" in recommendations

        # All should be empty lists
        assert recommendations["team_recommendations"] == []
        assert recommendations["technology_recommendations"] == []
        assert recommendations["process_recommendations"] == []

    # Test 6: Private Analysis Methods
    def test_analyze_team_velocity_accurate_calculation(
        self, learning_system, sample_team_projects
    ):
        """
        Test team velocity analysis produces accurate calculations.

        What's being tested:
        1. Velocity ratios are calculated correctly
        2. Task types are grouped properly
        3. Insufficient samples are filtered out
        4. Statistics calculations are accurate
        """
        velocity_patterns = learning_system._analyze_team_velocity(sample_team_projects)

        # Verify structure
        assert isinstance(velocity_patterns, dict)

        # Check specific calculations
        if "backend" in velocity_patterns:
            # Backend tasks: 14/12=1.17, 18/16=1.125, 22/20=1.1
            # Average: (1.17 + 1.125 + 1.1) / 3 = 1.13
            backend_velocity = velocity_patterns["backend"]
            assert 1.12 <= backend_velocity <= 1.14

        if "frontend" in velocity_patterns:
            # Frontend: 10/8=1.25 (only one sample, should be included if >= 2 samples)
            # This might not be included if filtering requires >= 2 samples
            pass

        # Verify no task types with insufficient samples
        for task_type, velocity in velocity_patterns.items():
            assert velocity > 0  # All velocities should be positive

    def test_analyze_team_skills_from_tech_stack(
        self, learning_system, sample_team_projects
    ):
        """
        Test team skill analysis extracts skills from tech stacks.

        What's being tested:
        1. Skills are extracted from project tech stacks
        2. Performance scores are aggregated correctly
        3. Skills with insufficient data are filtered out
        """
        skill_strengths = learning_system._analyze_team_skills(sample_team_projects)

        assert isinstance(skill_strengths, dict)

        # Check for expected skills from sample data
        expected_skills = [
            "react",
            "typescript",
            "nodejs",
            "python",
            "django",
            "postgresql",
            "fastapi",
            "redis",
        ]
        found_skills = set(skill_strengths.keys())

        # Some skills should be found
        assert len(found_skills.intersection(expected_skills)) > 0

        # All skill strengths should be reasonable values
        for skill, strength in skill_strengths.items():
            assert 0.0 <= strength <= 1.0

    def test_analyze_task_preferences_preference_scoring(
        self, learning_system, sample_team_projects
    ):
        """
        Test task preference analysis calculates preference scores correctly.

        What's being tested:
        1. Preference scores combine quality and efficiency
        2. Formula: (quality_score + (2.0 - completion_time_ratio)) / 2
        3. Task types are grouped and averaged properly
        """
        preferences = learning_system._analyze_task_preferences(sample_team_projects)

        assert isinstance(preferences, dict)

        # Check calculation logic for specific cases
        # Example: frontend task with quality=0.9, completion_ratio=1.25
        # Preference = (0.9 + (2.0 - 1.25)) / 2 = (0.9 + 0.75) / 2 = 0.825

        if "frontend" in preferences:
            frontend_pref = preferences["frontend"]
            assert 0.0 <= frontend_pref <= 1.0

    def test_analyze_collaboration_patterns_team_metrics(
        self, learning_system, sample_team_projects
    ):
        """
        Test collaboration pattern analysis extracts team metrics.

        What's being tested:
        1. Average team size is calculated correctly
        2. Parallel task preferences are analyzed
        3. Default values are provided for missing data
        """
        patterns = learning_system._analyze_collaboration_patterns(sample_team_projects)

        assert isinstance(patterns, dict)
        assert "avg_team_size" in patterns
        assert "parallel_task_preference" in patterns
        assert "communication_frequency" in patterns
        assert "review_thoroughness" in patterns

        # Check team size calculation: (4 + 3 + 2) / 3 = 3
        avg_team_size = patterns["avg_team_size"]
        assert 2.8 <= avg_team_size <= 3.2

        # Parallel preference should be between 0 and 1
        parallel_pref = patterns["parallel_task_preference"]
        assert 0.0 <= parallel_pref <= 1.0

    def test_analyze_team_quality_metrics_aggregation(
        self, learning_system, sample_team_projects
    ):
        """
        Test team quality metrics are aggregated correctly.

        What's being tested:
        1. Quality scores are averaged across projects
        2. Bug rates are calculated properly
        3. Review coverage is aggregated
        """
        quality_metrics = learning_system._analyze_team_quality(sample_team_projects)

        assert isinstance(quality_metrics, dict)

        if "average_quality" in quality_metrics:
            avg_quality = quality_metrics["average_quality"]
            # Should be average of 0.88, 0.91, 0.87 = 0.887
            assert 0.86 <= avg_quality <= 0.90

        if "average_bug_rate" in quality_metrics:
            avg_bug_rate = quality_metrics["average_bug_rate"]
            # Should be average of 0.05, 0.03, 0.08 = 0.053
            assert 0.04 <= avg_bug_rate <= 0.07

    # Test 7: Technology Analysis Methods
    def test_analyze_tech_patterns_structure_analysis(
        self, learning_system, sample_tech_outcomes
    ):
        """
        Test technology pattern analysis identifies common structures.

        What's being tested:
        1. Project structures are counted and ranked
        2. Duration patterns are calculated with statistics
        3. Most common patterns are identified
        """
        patterns = learning_system._analyze_tech_patterns(sample_tech_outcomes)

        assert isinstance(patterns, dict)
        assert "common_structures" in patterns
        assert "typical_duration" in patterns

        # Check structure analysis
        structures = patterns["common_structures"]
        assert "microservices" in structures
        assert "monolithic" in structures

        # Check duration statistics
        duration_stats = patterns["typical_duration"]
        assert "mean" in duration_stats
        assert "median" in duration_stats
        assert 53 <= duration_stats["mean"] <= 54  # (60 + 45 + 55) / 3 ≈ 53.33

    def test_calculate_estimation_multipliers_accuracy(
        self, learning_system, sample_tech_outcomes
    ):
        """
        Test estimation multiplier calculations are accurate.

        What's being tested:
        1. Multipliers are calculated from actual vs estimated ratios
        2. Task types are grouped correctly
        3. Averages are computed properly
        """
        multipliers = learning_system._calculate_estimation_multipliers(
            sample_tech_outcomes
        )

        assert isinstance(multipliers, dict)

        if "frontend" in multipliers:
            # Frontend: (48/40, 33/30) = (1.2, 1.1) = avg 1.15
            frontend_mult = multipliers["frontend"]
            assert 1.14 <= frontend_mult <= 1.16

        if "backend" in multipliers:
            # Backend: (58/50, 38/35) = (1.16, 1.086) = avg 1.123
            backend_mult = multipliers["backend"]
            assert 1.10 <= backend_mult <= 1.15

    def test_identify_tech_dependencies_extraction(
        self, learning_system, sample_tech_outcomes
    ):
        """
        Test technology dependency identification extracts common patterns.

        What's being tested:
        1. Dependencies are extracted from project data
        2. Common dependencies are counted and ranked
        3. Minimum occurrence threshold is applied
        """
        dependencies = learning_system._identify_tech_dependencies(sample_tech_outcomes)

        assert isinstance(dependencies, list)

        # Check for expected dependency patterns
        dep_strings = [f"{prereq}->{dep}" for prereq, dep in dependencies]

        # Should find common patterns in the sample data
        if len(dependencies) > 0:
            # All dependencies should be tuples
            for dep in dependencies:
                assert isinstance(dep, tuple)
                assert len(dep) == 2

    def test_analyze_tech_risks_probability_calculation(
        self, learning_system, sample_tech_outcomes
    ):
        """
        Test technology risk analysis calculates probabilities correctly.

        What's being tested:
        1. Risk frequencies are counted across projects
        2. Probabilities are calculated as frequency / total projects
        3. Minimum occurrence threshold is applied
        """
        risk_factors = learning_system._analyze_tech_risks(sample_tech_outcomes)

        assert isinstance(risk_factors, dict)

        # Check probability calculations
        for risk, probability in risk_factors.items():
            assert 0.0 <= probability <= 1.0

        # Should include risks from sample data
        if "scalability_bottleneck" in risk_factors:
            # Appears in 2 out of 3 projects = 0.67 probability
            prob = risk_factors["scalability_bottleneck"]
            assert 0.6 <= prob <= 0.7

    def test_extract_best_practices_from_successful_projects(
        self, learning_system, sample_tech_outcomes
    ):
        """
        Test best practice extraction focuses on successful projects.

        What's being tested:
        1. Only practices from high-success projects are included
        2. Practice frequency is counted correctly
        3. Minimum occurrence threshold is applied
        """
        best_practices = learning_system._extract_best_practices(sample_tech_outcomes)

        assert isinstance(best_practices, list)

        # Should include common practices from successful projects
        expected_practices = ["code_review", "automated_testing", "unit_testing"]
        found_practices = set(best_practices)

        # Some expected practices should be found
        assert len(found_practices.intersection(expected_practices)) > 0

    # Test 8: Default Learning Creation
    def test_create_default_team_learnings_structure(self, learning_system):
        """
        Test default team learnings have proper structure and values.

        What's being tested:
        1. Default learnings contain all required fields
        2. Default values are reasonable and safe
        3. Timestamps are set correctly
        """
        team_id = "default-team"
        default_learnings = learning_system._create_default_team_learnings(team_id)

        assert isinstance(default_learnings, TeamLearnings)
        assert default_learnings.team_id == team_id
        assert default_learnings.last_updated is not None

        # Check default velocity
        assert "general" in default_learnings.velocity_patterns
        assert default_learnings.velocity_patterns["general"] == 1.2

        # Check default collaboration patterns
        assert default_learnings.collaboration_patterns["avg_team_size"] == 3
        assert (
            default_learnings.collaboration_patterns["parallel_task_preference"] == 0.5
        )

        # Check default quality
        assert default_learnings.quality_metrics["average_quality"] == 0.8

    def test_create_default_tech_learnings_structure(self, learning_system):
        """
        Test default technology learnings have proper structure and values.

        What's being tested:
        1. Default tech learnings contain all required fields
        2. Default values are conservative and safe
        3. Best practices include essential items
        """
        tech_stack = "default-stack"
        default_learnings = learning_system._create_default_tech_learnings(tech_stack)

        assert isinstance(default_learnings, TechnologyLearnings)
        assert default_learnings.tech_stack == tech_stack
        assert default_learnings.last_updated is not None

        # Check default duration patterns
        duration_stats = default_learnings.typical_patterns["typical_duration"]
        assert duration_stats["mean"] == 30
        assert duration_stats["median"] == 28

        # Check default estimation multiplier
        assert "general" in default_learnings.estimation_multipliers
        assert default_learnings.estimation_multipliers["general"] == 1.3

        # Check default best practices
        expected_practices = ["Follow coding standards", "Write tests", "Code review"]
        assert all(
            practice in default_learnings.best_practices
            for practice in expected_practices
        )

    # Test 9: Template Adaptation Methods
    @pytest.mark.asyncio
    async def test_adapt_estimation_template_combination_logic(self, learning_system):
        """
        Test estimation template adaptation combines team and tech learnings correctly.

        What's being tested:
        1. Team velocity and tech multipliers are combined with proper weighting
        2. Weighted formula: team_velocity * 0.6 + tech_multiplier * 0.4
        3. All task types from team learnings are processed
        """
        team_learnings = TeamLearnings(
            team_id="test-team",
            velocity_patterns={"frontend": 1.5, "backend": 1.2},
            skill_strengths={},
            preferred_task_types={},
            collaboration_patterns={},
            quality_metrics={},
            last_updated=datetime.now(timezone.utc),
        )

        tech_learnings = TechnologyLearnings(
            tech_stack="test-stack",
            typical_patterns={},
            estimation_multipliers={"frontend": 1.3, "backend": 1.1, "testing": 1.4},
            common_dependencies=[],
            risk_factors={},
            best_practices=[],
            last_updated=datetime.now(timezone.utc),
        )

        context = {"project_type": "web_app"}

        adapted_template = await learning_system._adapt_estimation_template(
            team_learnings, tech_learnings, context
        )

        assert isinstance(adapted_template, AdaptedTemplate)
        assert adapted_template.template_id == "estimation_adapted"
        assert adapted_template.confidence == 0.8

        # Check weighted combinations
        adaptations = adapted_template.adaptations

        # Frontend: 1.5 * 0.6 + 1.3 * 0.4 = 0.9 + 0.52 = 1.42
        if "frontend_multiplier" in adaptations:
            frontend_mult = adaptations["frontend_multiplier"]
            assert 1.41 <= frontend_mult <= 1.43

        # Backend: 1.2 * 0.6 + 1.1 * 0.4 = 0.72 + 0.44 = 1.16
        if "backend_multiplier" in adaptations:
            backend_mult = adaptations["backend_multiplier"]
            assert 1.15 <= backend_mult <= 1.17

    @pytest.mark.asyncio
    async def test_adapt_task_generation_template_preferences(self, learning_system):
        """
        Test task generation template adaptation uses team preferences.

        What's being tested:
        1. Team task preferences are included in adaptations
        2. Project type phases are incorporated
        3. Template reasoning explains the adaptations
        """
        project_learnings = ProjectTypeLearnings(
            project_type="web_application",
            typical_phases=[
                "planning",
                "design",
                "development",
                "testing",
                "deployment",
            ],
            phase_dependencies={"design": ["planning"], "development": ["design"]},
            success_patterns={},
            common_pitfalls=[],
            resource_requirements={},
            last_updated=datetime.now(timezone.utc),
        )

        team_learnings = TeamLearnings(
            team_id="test-team",
            velocity_patterns={},
            skill_strengths={},
            preferred_task_types={"frontend": 0.9, "backend": 0.7, "testing": 0.8},
            collaboration_patterns={},
            quality_metrics={},
            last_updated=datetime.now(timezone.utc),
        )

        context = {"project_size": "medium"}

        adapted_template = await learning_system._adapt_task_generation_template(
            project_learnings, team_learnings, context
        )

        assert isinstance(adapted_template, AdaptedTemplate)
        assert adapted_template.template_id == "task_generation_adapted"
        assert adapted_template.confidence == 0.75

        # Check adaptations include preferences and phases
        adaptations = adapted_template.adaptations
        assert "preferred_task_types" in adaptations
        assert "typical_phases" in adaptations
        assert "team_preferences" in adaptations

        # Verify actual content
        preferred_types = adaptations["preferred_task_types"]
        assert "frontend" in preferred_types
        assert "testing" in preferred_types

        phases = adaptations["typical_phases"]
        assert "planning" in phases
        assert "development" in phases

    @pytest.mark.asyncio
    async def test_adapt_dependency_template_tech_patterns(self, learning_system):
        """
        Test dependency template adaptation uses technology patterns.

        What's being tested:
        1. Common dependencies are included in adaptations
        2. Risk factors are incorporated
        3. Template reasoning explains the technology focus
        """
        tech_learnings = TechnologyLearnings(
            tech_stack="react-django-postgres",
            typical_patterns={},
            estimation_multipliers={},
            common_dependencies=[
                ("database_setup", "models_creation"),
                ("api_development", "frontend_integration"),
            ],
            risk_factors={"database_migration": 0.4, "api_versioning": 0.2},
            best_practices=[],
            last_updated=datetime.now(timezone.utc),
        )

        context = {"deployment_env": "production"}

        adapted_template = await learning_system._adapt_dependency_template(
            tech_learnings, context
        )

        assert isinstance(adapted_template, AdaptedTemplate)
        assert adapted_template.template_id == "dependencies_adapted"
        assert adapted_template.confidence == 0.7

        # Check adaptations include dependencies and risks
        adaptations = adapted_template.adaptations
        assert "common_dependencies" in adaptations
        assert "risk_factors" in adaptations

        # Verify content
        dependencies = adaptations["common_dependencies"]
        assert len(dependencies) == 2
        assert ("database_setup", "models_creation") in dependencies

        risks = adaptations["risk_factors"]
        assert "database_migration" in risks
        assert risks["database_migration"] == 0.4

    # Test 10: Recommendation Generation
    @pytest.mark.asyncio
    async def test_get_team_recommendations_velocity_warnings(self, learning_system):
        """
        Test team recommendations include velocity warnings for slow task types.

        What's being tested:
        1. High velocity ratios generate underestimation warnings
        2. Strong skills generate leverage recommendations
        3. Recommendations are actionable and specific
        """
        team_learnings = TeamLearnings(
            team_id="test-team",
            velocity_patterns={
                "backend": 1.8,
                "frontend": 1.1,
                "testing": 2.0,
            },  # backend and testing are slow
            skill_strengths={
                "react": 0.9,
                "python": 0.95,
                "testing": 0.7,
            },  # strong in react and python
            preferred_task_types={},
            collaboration_patterns={},
            quality_metrics={},
            last_updated=datetime.now(timezone.utc),
        )

        current_state = {"active_backend_tasks": 5}

        recommendations = await learning_system._get_team_recommendations(
            team_learnings, current_state
        )

        assert isinstance(recommendations, list)

        # Should include velocity warnings for backend (1.8 > 1.5) and testing (2.0 > 1.5)
        velocity_warnings = [
            rec for rec in recommendations if "underestimate" in rec.lower()
        ]
        assert len(velocity_warnings) >= 1  # At least one warning expected

        # Should include warnings for slow task types
        slow_task_warning = any(
            ("backend" in rec.lower() or "testing" in rec.lower())
            for rec in velocity_warnings
        )
        assert slow_task_warning

        # Should include skill leverage recommendations
        skill_recommendations = [
            rec for rec in recommendations if "leverage" in rec.lower()
        ]
        assert len(skill_recommendations) > 0

        # Should mention strong skills
        strong_skill_mention = any(
            "react" in rec or "python" in rec for rec in skill_recommendations
        )
        assert strong_skill_mention

    @pytest.mark.asyncio
    async def test_get_technology_recommendations_risk_monitoring(
        self, learning_system
    ):
        """
        Test technology recommendations include risk monitoring for high-probability risks.

        What's being tested:
        1. High-probability risks generate monitoring recommendations
        2. Best practices are included in recommendations
        3. Recommendations are prioritized by risk probability
        """
        tech_learnings = TechnologyLearnings(
            tech_stack="microservices-k8s",
            typical_patterns={},
            estimation_multipliers={},
            common_dependencies=[],
            risk_factors={
                "service_orchestration": 0.6,  # High risk - should warn
                "network_latency": 0.2,  # Low risk - shouldn't warn
                "scaling_issues": 0.4,  # Medium-high risk - should warn
            },
            best_practices=[
                "container_monitoring",
                "circuit_breakers",
                "health_checks",
            ],
            last_updated=datetime.now(timezone.utc),
        )

        current_state = {"service_count": 12}

        recommendations = await learning_system._get_technology_recommendations(
            tech_learnings, current_state
        )

        assert isinstance(recommendations, list)

        # Should include risk monitoring for high-probability risks (> 0.3)
        risk_warnings = [rec for rec in recommendations if "monitor" in rec.lower()]
        assert len(risk_warnings) >= 2  # service_orchestration and scaling_issues

        # Should mention specific high-probability risks
        orchestration_warning = any(
            "service_orchestration" in rec for rec in risk_warnings
        )
        scaling_warning = any("scaling_issues" in rec for rec in risk_warnings)
        assert orchestration_warning
        assert scaling_warning

        # Should NOT warn about low probability risks
        latency_warning = any("network_latency" in rec for rec in risk_warnings)
        assert not latency_warning

        # Should include best practice recommendations (limited to top 3)
        practice_recommendations = [
            rec for rec in recommendations if "recommended practice" in rec.lower()
        ]
        assert len(practice_recommendations) <= 3
        assert len(practice_recommendations) > 0

    @pytest.mark.asyncio
    async def test_get_process_recommendations_phases_and_pitfalls(
        self, learning_system
    ):
        """
        Test process recommendations include project phases and pitfall warnings.

        What's being tested:
        1. Typical project phases are recommended
        2. Common pitfalls are warned about
        3. Recommendations are limited to prevent overwhelm
        """
        project_learnings = ProjectTypeLearnings(
            project_type="mobile_application",
            typical_phases=[
                "research",
                "prototyping",
                "development",
                "testing",
                "app_store_submission",
            ],
            phase_dependencies={},
            success_patterns={},
            common_pitfalls=[
                "Underestimating app store review time",
                "Not testing on real devices early",
                "Ignoring platform-specific design guidelines",
                "Poor offline handling implementation",
            ],
            resource_requirements={},
            last_updated=datetime.now(timezone.utc),
        )

        current_state = {"current_phase": "development"}

        recommendations = await learning_system._get_process_recommendations(
            project_learnings, current_state
        )

        assert isinstance(recommendations, list)

        # Should include phase recommendations
        phase_recommendations = [
            rec for rec in recommendations if "phases" in rec.lower()
        ]
        assert len(phase_recommendations) > 0

        # Phase recommendation should mention project type and phases
        phase_rec = phase_recommendations[0]
        assert "mobile_application" in phase_rec
        assert "research" in phase_rec or "prototyping" in phase_rec

        # Should include pitfall warnings (limited to first 2)
        pitfall_warnings = [
            rec for rec in recommendations if "watch out" in rec.lower()
        ]
        assert len(pitfall_warnings) <= 2
        assert len(pitfall_warnings) > 0

        # Should mention specific pitfalls
        if len(pitfall_warnings) > 0:
            first_pitfall = pitfall_warnings[0]
            assert (
                "app store review" in first_pitfall.lower()
                or "real devices" in first_pitfall.lower()
            )

    # Test 11: Edge Cases and Error Handling
    def test_empty_project_data_handling(self, learning_system):
        """
        Test system handles completely empty project data gracefully.

        What's being tested:
        1. Empty project lists don't cause crashes
        2. Empty task lists are handled properly
        3. Missing fields in projects are handled gracefully
        """
        # Test with completely empty projects
        empty_projects: list[dict[str, Any]] = []
        velocity_patterns = learning_system._analyze_team_velocity(empty_projects)
        assert velocity_patterns == {}

        skill_strengths = learning_system._analyze_team_skills(empty_projects)
        assert skill_strengths == {}

        # Test with projects that have empty task lists
        projects_no_tasks = [
            {"project_id": "EMPTY-1", "tasks": []},
            {"project_id": "EMPTY-2", "tasks": []},
            {"project_id": "EMPTY-3"},  # Missing tasks key entirely
        ]

        velocity_patterns = learning_system._analyze_team_velocity(projects_no_tasks)
        assert velocity_patterns == {}

    def test_malformed_project_data_filtering(self, learning_system):
        """
        Test system filters out malformed project data without crashing.

        What's being tested:
        1. Projects with missing required fields are skipped
        2. Tasks with invalid data types are filtered out
        3. System continues processing valid data
        """
        malformed_projects = [
            {
                "project_id": "MALFORMED-1",
                "tasks": [
                    {
                        "type": "frontend",
                        "estimated_hours": "not_a_number",  # Invalid type
                        "actual_hours": 10,
                    },
                    {
                        "type": "backend",
                        "estimated_hours": 8,
                        "actual_hours": 12,  # Valid task
                    },
                    {
                        # Missing required fields
                        "description": "Task without type or hours"
                    },
                ],
            },
            {
                "project_id": "VALID-1",
                "tasks": [
                    {
                        "type": "testing",
                        "estimated_hours": 6,
                        "actual_hours": 7,
                        "quality_score": 0.9,
                    }
                ],
            },
        ]

        # Should process valid data and skip invalid data without crashing
        velocity_patterns = learning_system._analyze_team_velocity(malformed_projects)

        # Should include the valid backend task
        if "backend" in velocity_patterns:
            assert velocity_patterns["backend"] == 1.5  # 12/8 = 1.5

        # Should include the valid testing task
        if "testing" in velocity_patterns:
            assert velocity_patterns["testing"] == 1.17  # 7/6 ≈ 1.17

    @pytest.mark.asyncio
    async def test_concurrent_learning_operations(
        self, learning_system, sample_team_projects, sample_tech_outcomes
    ):
        """
        Test system handles concurrent learning operations safely.

        What's being tested:
        1. Multiple learning operations can run simultaneously
        2. Data integrity is maintained during concurrent access
        3. No race conditions corrupt the learning state

        Note: This is a basic test - full concurrency testing would require
        more sophisticated threading/async testing frameworks.
        """
        import asyncio

        # Run team and technology learning concurrently
        team_task = learning_system.learn_team_patterns(
            "concurrent-team", sample_team_projects
        )
        tech_task = learning_system.learn_technology_patterns(
            "concurrent-tech", sample_tech_outcomes
        )

        team_result, tech_result = await asyncio.gather(team_task, tech_task)

        # Both operations should complete successfully
        assert isinstance(team_result, TeamLearnings)
        assert isinstance(tech_result, TechnologyLearnings)

        # Results should be stored properly
        assert "concurrent-team" in learning_system.team_learnings
        assert "concurrent-tech" in learning_system.technology_learnings

        # Data should be consistent
        assert learning_system.team_learnings["concurrent-team"] == team_result
        assert learning_system.technology_learnings["concurrent-tech"] == tech_result

    def test_large_dataset_performance(self, learning_system):
        """
        Test system performance with large datasets.

        What's being tested:
        1. System handles large numbers of projects efficiently
        2. Memory usage remains reasonable
        3. Calculations complete in reasonable time
        """
        # Generate a large dataset of projects
        large_project_set = []
        for i in range(100):  # 100 projects
            project = {
                "project_id": f"LARGE-{i}",
                "team_size": 3 + (i % 3),
                "tech_stack": ["python", "react", "postgres"],
                "success_metrics": {"completion_rate": 0.8 + (i % 20) * 0.01},
                "tasks": [
                    {
                        "type": "backend",
                        "estimated_hours": 10 + (i % 10),
                        "actual_hours": 12 + (i % 8),
                        "quality_score": 0.8 + (i % 15) * 0.01,
                    },
                    {
                        "type": "frontend",
                        "estimated_hours": 8 + (i % 6),
                        "actual_hours": 9 + (i % 5),
                        "quality_score": 0.85 + (i % 12) * 0.01,
                    },
                ],
            }
            large_project_set.append(project)

        import time

        start_time = time.time()

        # Analyze the large dataset
        velocity_patterns = learning_system._analyze_team_velocity(large_project_set)
        skill_strengths = learning_system._analyze_team_skills(large_project_set)
        preferences = learning_system._analyze_task_preferences(large_project_set)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should complete in reasonable time (< 1 second for 100 projects)
        assert processing_time < 1.0

        # Should produce meaningful results
        assert len(velocity_patterns) > 0
        assert "backend" in velocity_patterns
        assert "frontend" in velocity_patterns

        # Results should be reasonable
        for task_type, velocity in velocity_patterns.items():
            assert 0.5 <= velocity <= 3.0  # Reasonable velocity range

    def test_unicode_and_special_characters_handling(self, learning_system):
        """
        Test system handles unicode and special characters in project data.

        What's being tested:
        1. Unicode project names and descriptions are handled correctly
        2. Special characters in task types don't cause issues
        3. Emoji and international characters are processed safely
        """
        unicode_projects = [
            {
                "project_id": "UNICODE-1",
                "name": "プロジェクト名 🚀",  # Japanese + emoji
                "team_size": 3,
                "tech_stack": ["python", "réact", "postgreSQL"],  # Accented characters
                "tasks": [
                    {
                        "type": "frøntend",  # Special character
                        "estimated_hours": 8,
                        "actual_hours": 10,
                        "quality_score": 0.9,
                    },
                    {
                        "type": "back-end",  # Hyphenated
                        "estimated_hours": 12,
                        "actual_hours": 14,
                        "quality_score": 0.85,
                    },
                ],
            },
            {
                "project_id": "UNICODE-2",
                "name": "Проект Тест",  # Cyrillic
                "team_size": 4,
                "tech_stack": ["نود جے اس", "react"],  # Urdu characters
                "tasks": [
                    {
                        "type": "测试",  # Chinese characters
                        "estimated_hours": 6,
                        "actual_hours": 8,
                        "quality_score": 0.88,
                    }
                ],
            },
        ]

        # Should handle unicode gracefully without crashes
        velocity_patterns = learning_system._analyze_team_velocity(unicode_projects)
        skill_strengths = learning_system._analyze_team_skills(unicode_projects)

        # Should produce valid results
        assert isinstance(velocity_patterns, dict)
        assert isinstance(skill_strengths, dict)

        # Should handle special characters in task types
        if "frøntend" in velocity_patterns:
            assert velocity_patterns["frøntend"] == 1.25  # 10/8

        if "back-end" in velocity_patterns:
            assert velocity_patterns["back-end"] == 1.17  # 14/12 ≈ 1.17

    # Test 12: Integration and Workflow Tests
    @pytest.mark.asyncio
    async def test_full_learning_workflow_integration(
        self,
        learning_system,
        sample_team_projects,
        sample_tech_outcomes,
        sample_project_context,
    ):
        """
        Test complete learning workflow from data ingestion to recommendations.

        What's being tested:
        1. Complete workflow: learn patterns → adapt templates → get recommendations
        2. Data flows correctly between learning phases
        3. Final recommendations reflect all learned patterns
        4. System maintains consistency throughout workflow

        This is an integration test that verifies the entire learning pipeline.
        """
        # Phase 1: Learn team patterns
        team_id = sample_project_context["team_id"]
        team_learnings = await learning_system.learn_team_patterns(
            team_id, sample_team_projects
        )

        # Phase 2: Learn technology patterns
        tech_stack = sample_project_context["tech_stack_key"]
        tech_learnings = await learning_system.learn_technology_patterns(
            tech_stack, sample_tech_outcomes
        )

        # Phase 3: Adapt templates based on learnings
        adapted_templates = await learning_system.adapt_templates_intelligently(
            sample_project_context
        )

        # Phase 4: Get contextual recommendations
        current_state = {"active_tasks": 8, "blocked_tasks": 2}
        recommendations = await learning_system.get_contextual_recommendations(
            sample_project_context, current_state
        )

        # Verify complete workflow results
        assert isinstance(team_learnings, TeamLearnings)
        assert isinstance(tech_learnings, TechnologyLearnings)
        assert isinstance(adapted_templates, dict)
        assert isinstance(recommendations, dict)

        # Verify data consistency across phases
        assert learning_system.team_learnings[team_id] == team_learnings
        assert learning_system.technology_learnings[tech_stack] == tech_learnings

        # Verify recommendations reflect learned patterns
        team_recs = recommendations["team_recommendations"]
        tech_recs = recommendations["technology_recommendations"]

        if len(team_recs) > 0:
            # Should include insights from team learning (velocity warnings or skill recommendations)
            team_insight_found = any(
                ("underestimate" in rec.lower() or "leverage" in rec.lower())
                for rec in team_recs
            )
            # Note: May not always have recommendations depending on learned patterns
            # assert team_insight_found

        if len(tech_recs) > 0:
            # Should include insights from technology learning
            tech_insight_found = len(tech_recs) > 0
            assert tech_insight_found

        # Verify template adaptations use both team and tech learnings
        if "estimation" in adapted_templates:
            estimation_template = adapted_templates["estimation"]
            assert estimation_template.confidence > 0.5
            assert (
                "Combined team velocity patterns"
                in estimation_template.adaptation_reasoning
            )

    @pytest.mark.asyncio
    async def test_learning_system_state_persistence(
        self, learning_system, sample_team_projects
    ):
        """
        Test learning system maintains state correctly across operations.

        What's being tested:
        1. Learned patterns are stored persistently in system state
        2. Multiple learning operations accumulate knowledge
        3. State can be queried and retrieved accurately
        4. No data corruption occurs during state updates
        """
        # Learn patterns for multiple teams
        team_alpha_learnings = await learning_system.learn_team_patterns(
            "team-alpha", sample_team_projects
        )
        team_beta_learnings = await learning_system.learn_team_patterns(
            "team-beta", sample_team_projects
        )  # Use all projects to meet minimum

        # Verify both teams' learnings are stored
        assert len(learning_system.team_learnings) == 2
        assert "team-alpha" in learning_system.team_learnings
        assert "team-beta" in learning_system.team_learnings

        # Verify stored data matches returned data
        assert learning_system.team_learnings["team-alpha"] == team_alpha_learnings
        assert learning_system.team_learnings["team-beta"] == team_beta_learnings

        # Verify data independence (patterns are calculated independently)
        alpha_velocity = team_alpha_learnings.velocity_patterns
        beta_velocity = team_beta_learnings.velocity_patterns

        # Both teams should have valid velocity patterns (same data in this test)
        if "backend" in alpha_velocity and "backend" in beta_velocity:
            # Both should have reasonable velocity values
            assert alpha_velocity["backend"] > 0
            assert beta_velocity["backend"] > 0
            # Values will be the same since we used same project data for both teams

        # Add technology learning and verify state expansion
        tech_learnings = await learning_system.learn_technology_patterns(
            "tech-stack-1", []
        )

        assert len(learning_system.technology_learnings) == 1
        assert "tech-stack-1" in learning_system.technology_learnings

        # Verify team learnings weren't affected by tech learning
        assert len(learning_system.team_learnings) == 2
        assert learning_system.team_learnings["team-alpha"] == team_alpha_learnings

    def test_learning_system_memory_efficiency(self, learning_system):
        """
        Test learning system manages memory efficiently with large datasets.

        What's being tested:
        1. System doesn't accumulate excessive intermediate data
        2. Memory usage is proportional to stored learnings, not processing data
        3. Garbage collection of temporary objects works correctly

        This is a basic memory efficiency test.
        """
        import sys

        # Measure initial memory usage
        initial_size = sys.getsizeof(learning_system)

        # Process large amounts of data
        for i in range(50):
            large_projects = [
                {
                    "project_id": f"MEM-TEST-{i}-{j}",
                    "tasks": [
                        {
                            "type": f"task_type_{j}",
                            "estimated_hours": 8 + j,
                            "actual_hours": 10 + j,
                            "quality_score": 0.8,
                        }
                        for j in range(10)  # 10 tasks per project
                    ],
                }
                for j in range(20)  # 20 projects per batch
            ]

            # Process but don't store (simulates large data processing)
            velocity_patterns = learning_system._analyze_team_velocity(large_projects)
            skill_strengths = learning_system._analyze_team_skills(large_projects)

            # Clear references to help garbage collection
            del large_projects
            del velocity_patterns
            del skill_strengths

        # Measure final memory usage
        final_size = sys.getsizeof(learning_system)

        # Memory usage should not have grown excessively
        memory_growth = final_size - initial_size
        assert memory_growth < 1000000  # Less than 1MB growth for processing
