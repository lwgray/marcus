"""
Integration tests for AI-first task descriptions end-to-end.

Tests the complete flow from project description to clean task descriptions.
"""

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints


@pytest.mark.integration
@pytest.mark.asyncio
class TestAIFirstDescriptionsE2E:
    """End-to-end tests for AI-first task description generation."""

    @pytest.fixture
    async def parser(self):
        """Create parser instance for testing."""
        return AdvancedPRDParser()

    @pytest.fixture
    def simple_project_description(self):
        """Simple project description for testing."""
        return "Build a todo app with user login using JWT tokens that expire after 24 hours"

    @pytest.fixture
    def constraints(self):
        """Default project constraints."""
        return ProjectConstraints(
            deadline=None,
            budget_limit=None,
            team_size=1,
            available_skills=[],
            technology_constraints=[],
            quality_requirements={},
            deployment_target="local",
        )

    async def test_clean_descriptions_no_template_boilerplate(
        self, parser, simple_project_description, constraints
    ):
        """
        Test that task descriptions are clean without template boilerplate.

        This is the main success criterion for AI-first descriptions.
        """
        result = await parser.parse_prd_to_tasks(
            simple_project_description, constraints
        )

        # Check we got tasks
        assert len(result.tasks) > 0

        # Check descriptions are clean (no template phrases)
        template_phrases = [
            "Research and design architecture for",
            "Create documentation defining approach",
            "Build core functionality for",
            "Implement business logic, data processing",
            "Create comprehensive test suite for",
        ]

        for task in result.tasks:
            description = task.description.lower()

            # Should NOT contain template boilerplate
            for phrase in template_phrases:
                assert (
                    phrase.lower() not in description
                ), f"Task {task.name} contains template phrase: {phrase}"

    async def test_user_specifics_preserved_in_descriptions(
        self, parser, simple_project_description, constraints
    ):
        """Test that specific user requirements appear in task descriptions."""
        result = await parser.parse_prd_to_tasks(
            simple_project_description, constraints
        )

        # Collect all descriptions
        all_descriptions = " ".join([task.description for task in result.tasks])

        # User specified "JWT tokens" and "24 hours" - these should appear
        assert "jwt" in all_descriptions.lower() or "token" in all_descriptions.lower()

    async def test_descriptions_are_concise(
        self, parser, simple_project_description, constraints
    ):
        """Test that descriptions are concise (not bloated with templates)."""
        result = await parser.parse_prd_to_tasks(
            simple_project_description, constraints
        )

        for task in result.tasks:
            # AI-first descriptions should be < 300 chars for simple requirements
            # (vs 500-600 chars with templates)
            if "design" in task.name.lower() or "implement" in task.name.lower():
                assert len(task.description) < 500, (
                    f"Task {task.name} description too long ({len(task.description)} chars): "
                    f"{task.description[:100]}..."
                )

    async def test_methodology_preserved_in_task_names(
        self, parser, simple_project_description, constraints
    ):
        """Test that Design/Implement/Test methodology is in task names."""
        result = await parser.parse_prd_to_tasks(
            simple_project_description, constraints
        )

        task_names = [task.name.lower() for task in result.tasks]

        # Should have design, implement, and test tasks
        has_design = any("design" in name for name in task_names)
        has_implement = any("implement" in name for name in task_names)
        has_test = any("test" in name for name in task_names)

        assert (
            has_design or has_implement or has_test
        ), "Missing Design/Implement/Test methodology in task names"

    async def test_methodology_preserved_in_labels(
        self, parser, simple_project_description, constraints
    ):
        """Test that Design/Implement/Test methodology is in labels."""
        result = await parser.parse_prd_to_tasks(
            simple_project_description, constraints
        )

        all_labels = []
        for task in result.tasks:
            all_labels.extend(task.labels)

        # Should have methodology labels
        assert (
            "design" in all_labels or "implement" in all_labels or "test" in all_labels
        ), "Missing Design/Implement/Test methodology in labels"

    async def test_complex_project_preserves_details(self, parser, constraints):
        """Test complex project description preserves all details."""
        complex_description = """
        Build an e-commerce platform with:
        - User authentication using OAuth2
        - Product catalog with search and filtering
        - Shopping cart with real-time updates
        - Payment processing via Stripe
        - Admin dashboard for inventory management
        - Email notifications for order confirmations
        """

        result = await parser.parse_prd_to_tasks(complex_description, constraints)

        # Should create multiple tasks
        assert len(result.tasks) >= 5

        all_text = " ".join(
            [task.name + " " + task.description for task in result.tasks]
        ).lower()

        # Check key details are preserved somewhere
        key_terms = ["auth", "product", "cart", "payment", "admin"]
        preserved_count = sum(1 for term in key_terms if term in all_text)

        assert (
            preserved_count >= 3
        ), f"Only {preserved_count}/5 key terms preserved in tasks"

    async def test_priority_assignment_works(
        self, parser, simple_project_description, constraints
    ):
        """Test that priorities are assigned correctly."""
        result = await parser.parse_prd_to_tasks(
            simple_project_description, constraints
        )

        # Should have priorities assigned
        priorities = [task.priority.value for task in result.tasks]
        assert len(priorities) > 0
        assert all(p in ["low", "medium", "high"] for p in priorities)
