"""
Unit tests for integration-aware requirement filtering.

Tests that integration requirements (infrastructure, glue, assembly) are
never filtered out regardless of complexity mode.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser
from src.ai.validation.task_completeness_validator import StructuredIntents


@pytest.mark.asyncio
async def test_prototype_mode_preserves_integration_requirements() -> None:
    """
    Test that prototype mode filters features but preserves integration.

    Scenario: 10 requirements (8 features + 2 integration)
    Expected: 2 features + 2 integration = 4 total requirements
    """
    parser = AdvancedPRDParser()

    # Mock 10 requirements: 8 features + 2 integration
    requirements = [
        {"id": "req-1", "name": "User authentication", "description": "Login system"},
        {"id": "req-2", "name": "User profiles", "description": "Profile management"},
        {"id": "req-3", "name": "Search functionality", "description": "Search API"},
        {"id": "req-4", "name": "Notifications", "description": "Push notifications"},
        {"id": "req-5", "name": "Analytics", "description": "Usage tracking"},
        {
            "id": "req-6",
            "name": "Payment processing",
            "description": "Stripe integration",
        },
        {"id": "req-7", "name": "Admin dashboard", "description": "Admin panel"},
        {"id": "req-8", "name": "Email service", "description": "Email templates"},
        # Integration requirements (should never be filtered)
        {"id": "req-9", "name": "API server setup", "description": "Express server"},
        {"id": "req-10", "name": "Database configuration", "description": "DB setup"},
    ]

    # Open-ended PRD (not explicit, so filtering will apply)
    prd_content = """
    Build a web application that needs user authentication, profiles,
    search, notifications, analytics, payment processing, admin dashboard,
    email service, API server infrastructure, and database setup.
    """

    # Mock the validator to classify req-9 and req-10 as integration
    mock_intents = StructuredIntents(
        component_intents=[
            "User authentication",
            "User profiles",
            "Search",
            "Notifications",
            "Analytics",
            "Payments",
            "Admin",
            "Email",
        ],
        integration_intents=[
            "API server setup",
            "Database configuration",
        ],
        all_intents=[
            "User authentication",
            "User profiles",
            "Search",
            "Notifications",
            "Analytics",
            "Payments",
            "Admin",
            "Email",
            "API server setup",
            "Database configuration",
        ],
    )

    with patch("src.ai.validation.TaskCompletenessValidator") as MockValidator:
        mock_validator_instance = MockValidator.return_value
        mock_validator_instance.extract_intents = AsyncMock(return_value=mock_intents)

        # Call filter with prototype mode
        filtered = await parser._filter_requirements_by_size(
            requirements=requirements,
            project_size="prototype",
            team_size=2,
            prd_content=prd_content,
        )

        # Verify validator was called
        mock_validator_instance.extract_intents.assert_called_once()

        # Verify filtering results
        # Prototype should keep 2 features + 2 integration = 4 total
        assert len(filtered) == 4, f"Expected 4 requirements, got {len(filtered)}"

        # Verify integration requirements are included
        filtered_ids = [req["id"] for req in filtered]
        assert (
            "req-9" in filtered_ids
        ), "API server setup (integration) should be preserved"
        assert (
            "req-10" in filtered_ids
        ), "Database configuration (integration) should be preserved"

        # Verify only 2 features were kept
        feature_ids = [id for id in filtered_ids if id not in ["req-9", "req-10"]]
        assert len(feature_ids) == 2, f"Expected 2 features, got {len(feature_ids)}"


@pytest.mark.asyncio
async def test_standard_mode_preserves_integration_requirements() -> None:
    """
    Test that standard mode filters features but preserves integration.

    Scenario: 10 requirements (8 features + 2 integration)
    Expected: 3-5 features + 2 integration = 5-7 total requirements
    """
    parser = AdvancedPRDParser()

    requirements = [
        {"id": f"feature-{i}", "name": f"Feature {i}", "description": "Feature"}
        for i in range(1, 9)
    ]
    requirements.extend(
        [
            {
                "id": "integration-1",
                "name": "Server infrastructure",
                "description": "API server",
            },
            {
                "id": "integration-2",
                "name": "Deployment pipeline",
                "description": "CI/CD",
            },
        ]
    )

    prd_content = "Build a system with 8 features and server infrastructure"

    mock_intents = StructuredIntents(
        component_intents=[f"Feature {i}" for i in range(1, 9)],
        integration_intents=["Server infrastructure", "Deployment pipeline"],
        all_intents=[f"Feature {i}" for i in range(1, 9)]
        + ["Server infrastructure", "Deployment pipeline"],
    )

    with patch("src.ai.validation.TaskCompletenessValidator") as MockValidator:
        mock_validator_instance = MockValidator.return_value
        mock_validator_instance.extract_intents = AsyncMock(return_value=mock_intents)

        # Call filter with standard mode (team_size=3)
        filtered = await parser._filter_requirements_by_size(
            requirements=requirements,
            project_size="standard",
            team_size=3,
            prd_content=prd_content,
        )

        # Standard with team_size=3 should keep 3 features + 2 integration = 5
        assert len(filtered) == 5, f"Expected 5 requirements, got {len(filtered)}"

        # Verify both integration requirements are included
        filtered_ids = [req["id"] for req in filtered]
        assert "integration-1" in filtered_ids
        assert "integration-2" in filtered_ids


@pytest.mark.asyncio
async def test_enterprise_mode_keeps_all_requirements() -> None:
    """
    Test that enterprise mode keeps all requirements without filtering.
    """
    parser = AdvancedPRDParser()

    requirements = [{"id": f"req-{i}", "name": f"Req {i}"} for i in range(1, 21)]

    prd_content = "Enterprise system with 20 requirements"

    mock_intents = StructuredIntents(
        component_intents=[f"Req {i}" for i in range(1, 19)],
        integration_intents=["Req 19", "Req 20"],
        all_intents=[f"Req {i}" for i in range(1, 21)],
    )

    with patch("src.ai.validation.TaskCompletenessValidator") as MockValidator:
        mock_validator_instance = MockValidator.return_value
        mock_validator_instance.extract_intents = AsyncMock(return_value=mock_intents)

        # Call filter with enterprise mode
        filtered = await parser._filter_requirements_by_size(
            requirements=requirements,
            project_size="enterprise",
            team_size=5,
            prd_content=prd_content,
        )

        # Enterprise should keep all 20 requirements
        assert len(filtered) == 20, f"Expected 20 requirements, got {len(filtered)}"


@pytest.mark.asyncio
async def test_explicit_requirements_bypass_filtering() -> None:
    """
    Test that explicit user requirements bypass all filtering logic.

    When user explicitly lists requirements, they're all kept regardless
    of complexity mode or integration classification.
    """
    parser = AdvancedPRDParser()

    requirements = [{"id": f"req-{i}", "name": f"Tool {i}"} for i in range(1, 11)]

    # Explicit PRD with numbered list
    prd_content = """
    Create these 10 tools:
    1. Tool 1
    2. Tool 2
    3. Tool 3
    4. Tool 4
    5. Tool 5
    6. Tool 6
    7. Tool 7
    8. Tool 8
    9. Tool 9
    10. Tool 10
    """

    # Even in prototype mode with explicit requirements, all should be kept
    filtered = await parser._filter_requirements_by_size(
        requirements=requirements,
        project_size="prototype",
        team_size=2,
        prd_content=prd_content,
    )

    # All 10 should be kept because they're explicit
    assert len(filtered) == 10, f"Expected 10 requirements, got {len(filtered)}"


@pytest.mark.asyncio
async def test_validator_failure_graceful_fallback() -> None:
    """
    Test that if validator fails, filtering still works (without protection).
    """
    parser = AdvancedPRDParser()

    requirements = [{"id": f"req-{i}", "name": f"Req {i}"} for i in range(1, 6)]

    prd_content = "Build 5 features"

    with patch("src.ai.validation.TaskCompletenessValidator") as MockValidator:
        # Make validator raise an exception
        mock_validator_instance = MockValidator.return_value
        mock_validator_instance.extract_intents = AsyncMock(
            side_effect=Exception("Validator error")
        )

        # Call filter with prototype mode
        filtered = await parser._filter_requirements_by_size(
            requirements=requirements,
            project_size="prototype",
            team_size=2,
            prd_content=prd_content,
        )

        # Should fall back to filtering all requirements (prototype keeps 2)
        assert (
            len(filtered) == 2
        ), f"Expected fallback to 2 requirements, got {len(filtered)}"
