"""
Integration tests for bundled domain-based design tasks (GH-108).

Tests the end-to-end flow of bundled domain designs with real AI calls
and Kanban integration.
"""

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
from src.core.models import Priority


@pytest.mark.integration
@pytest.mark.asyncio
class TestBundledDomainDesignsE2E:
    """End-to-end tests for bundled domain designs with real AI."""

    @pytest.fixture
    def parser(self):
        """Create AdvancedPRDParser with real dependencies."""
        return AdvancedPRDParser()

    @pytest.fixture
    def sample_prd_ecommerce(self):
        """Sample PRD for e-commerce application."""
        return """
        Build an e-commerce platform with the following features:

        1. User Management
           - User registration with email verification
           - User login with JWT authentication
           - Password reset functionality
           - User profile management

        2. Product Catalog
           - Product listing with pagination
           - Product search and filtering
           - Product detail pages
           - Category management

        3. Shopping Experience
           - Shopping cart functionality
           - Add/remove items from cart
           - Update item quantities
           - Cart persistence across sessions

        4. Order Processing
           - Checkout workflow
           - Payment integration
           - Order confirmation emails
           - Order history tracking
        """

    @pytest.mark.slow
    async def test_bundled_designs_created_for_ecommerce_domains(
        self, parser, sample_prd_ecommerce
    ):
        """Test bundled design tasks are created for e-commerce domains.

        This test verifies that:
        1. Domain discovery groups related features correctly
        2. One bundled design task is created per domain
        3. Bundled design tasks include all features in the domain
        4. Design tasks have proper metadata
        """
        # Arrange
        constraints = ProjectConstraints(
            team_size=5,
            complexity_mode="standard",
        )

        # Act - Analyze PRD and generate tasks
        analysis = await parser._analyze_prd_deeply(sample_prd_ecommerce)
        result = await parser.parse_prd_to_tasks(sample_prd_ecommerce, constraints)

        # Assert - Check domain discovery
        assert hasattr(parser, "_domain_mapping")
        assert len(parser._domain_mapping) >= 2  # At least 2 domains

        # Should discover domains like "User Management", "Shopping", etc.
        domain_names = list(parser._domain_mapping.keys())
        assert any("User" in d or "Auth" in d for d in domain_names)
        assert any("Product" in d or "Catalog" in d for d in domain_names)

        # Assert - Check bundled design tasks
        assert hasattr(parser, "_bundled_designs")
        bundled_designs = parser._bundled_designs

        # Should have design tasks matching discovered domains
        assert len(bundled_designs) == len(parser._domain_mapping)

        # Assert - Check design tasks in result
        design_tasks = [t for t in result.tasks if "design" in t.id.lower()]

        # Should have bundled designs (not per-feature)
        assert len(design_tasks) > 0
        assert len(design_tasks) < len(
            analysis.functional_requirements
        )  # Fewer than features

        # Verify design task structure
        for design_task in design_tasks:
            # Should have high priority
            assert design_task.priority == Priority.HIGH

            # Should have design label
            assert (
                "design" in design_task.labels or "architecture" in design_task.labels
            )

            # Should have reasonable estimated hours
            assert design_task.estimated_hours > 0

    @pytest.mark.slow
    async def test_implement_tasks_depend_on_bundled_designs(
        self, parser, sample_prd_ecommerce
    ):
        """Test implement tasks depend on their domain's bundled design.

        Verifies that dependency inference creates proper dependencies from
        implement/test tasks to bundled design tasks.
        """
        # Arrange
        constraints = ProjectConstraints(
            team_size=5,
            complexity_mode="standard",
        )

        # Act
        result = await parser.parse_prd_to_tasks(sample_prd_ecommerce, constraints)

        # Get design and implement tasks
        design_tasks = [t for t in result.tasks if "design" in t.id.lower()]
        implement_tasks = [t for t in result.tasks if "implement" in t.id.lower()]

        # Assert - Implement tasks should exist
        assert len(implement_tasks) > 0

        # Assert - Implement tasks should depend on design tasks
        design_task_ids = {t.id for t in design_tasks}

        for impl_task in implement_tasks:
            # Check if this implement task has design dependencies
            design_deps = [d for d in impl_task.dependencies if d in design_task_ids]

            # Should have at least one design dependency
            assert (
                len(design_deps) > 0
            ), f"Implement task {impl_task.id} should depend on design"

    @pytest.mark.slow
    async def test_bundled_designs_scale_with_complexity_mode(self, parser):
        """Test bundled designs respect complexity mode.

        Verifies that complexity mode (prototype/standard/enterprise) affects
        task generation appropriately.
        """
        simple_prd = """
        Create a simple blog with:
        - Post creation
        - Post listing
        - Comments
        """

        # Test prototype mode
        prototype_constraints = ProjectConstraints(
            team_size=2,
            complexity_mode="prototype",
        )
        prototype_result = await parser.parse_prd_to_tasks(
            simple_prd, prototype_constraints
        )

        # Test standard mode
        standard_constraints = ProjectConstraints(
            team_size=5,
            complexity_mode="standard",
        )
        standard_result = await parser.parse_prd_to_tasks(
            simple_prd, standard_constraints
        )

        # Assert - Both should have bundled designs
        prototype_designs = [
            t for t in prototype_result.tasks if "design" in t.id.lower()
        ]
        standard_designs = [
            t for t in standard_result.tasks if "design" in t.id.lower()
        ]

        assert len(prototype_designs) > 0
        assert len(standard_designs) > 0

        # Standard mode should have more comprehensive tasks
        assert len(standard_result.tasks) >= len(prototype_result.tasks)

    @pytest.mark.slow
    async def test_bundled_design_includes_coordination_guidance(
        self, parser, sample_prd_ecommerce
    ):
        """Test bundled design tasks include agent coordination guidance.

        Verifies that design task descriptions include instructions for
        agents on how to use get_task_context() and log_artifact().
        """
        # Arrange
        constraints = ProjectConstraints(
            team_size=5,
            complexity_mode="standard",
        )

        # Act
        result = await parser.parse_prd_to_tasks(sample_prd_ecommerce, constraints)

        # Get design tasks
        design_tasks = [t for t in result.tasks if "design" in t.id.lower()]

        # Assert - Design tasks should have coordination guidance
        for design_task in design_tasks:
            description = design_task.description.lower()

            # Should mention key coordination concepts
            assert (
                "component" in description or "architecture" in description
            ), f"Design task {design_task.name} should mention components/architecture"

            assert (
                "get_task_context" in description or "context" in description
            ), f"Design task {design_task.name} should mention context retrieval"

            assert (
                "log_artifact" in description or "artifact" in description
            ), f"Design task {design_task.name} should mention artifact logging"

    @pytest.mark.slow
    async def test_domains_discovered_semantically(self, parser):
        """Test domain discovery groups features semantically.

        Verifies that AI-based domain discovery groups related features
        based on semantic similarity rather than just keywords.
        """
        # PRD with features that should be grouped by semantic relationship
        prd = """
        Build a social media platform:

        1. User Authentication - Login, registration, password reset
        2. Profile Management - Edit profile, upload avatar, bio
        3. Post Creation - Write posts, add images, tag friends
        4. News Feed - View posts from friends, like, comment
        5. Direct Messaging - Send private messages, group chats
        6. Notifications - Receive alerts for likes, comments, messages
        """

        constraints = ProjectConstraints(
            team_size=5,
            complexity_mode="standard",
        )

        # Act
        await parser.parse_prd_to_tasks(prd, constraints)

        # Assert - Domain discovery should have happened
        assert hasattr(parser, "_domain_mapping")
        domains = parser._domain_mapping

        # Should discover logical domains like:
        # - User/Auth domain (authentication + profile)
        # - Content domain (posts + feed)
        # - Communication domain (messaging + notifications)
        assert (
            len(domains) >= 2 and len(domains) <= 5
        ), "Should discover 2-5 logical domains"

        # Verify semantic grouping by checking feature distribution
        for domain_name, feature_ids in domains.items():
            # Each domain should have at least one feature
            assert len(feature_ids) > 0, f"Domain {domain_name} should have features"

            # No domain should have all features (that would mean no grouping)
            assert len(feature_ids) < 6, "Features should be distributed across domains"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.kanban
class TestBundledDomainDesignsWithKanban:
    """Integration tests for bundled domain designs with Kanban boards."""

    @pytest.mark.slow
    async def test_bundled_designs_created_on_kanban_board(self):
        """Test bundled design tasks are created on Kanban board.

        This is a placeholder for future Kanban integration testing.
        Requires Kanban server setup.
        """
        pytest.skip("Requires Kanban server - manual testing recommended")

    @pytest.mark.slow
    async def test_bundled_design_dependencies_visible_in_kanban(self):
        """Test dependencies from implement tasks to bundled designs are
        visible in Kanban.

        This is a placeholder for future Kanban integration testing.
        Requires Kanban server setup.
        """
        pytest.skip("Requires Kanban server - manual testing recommended")
