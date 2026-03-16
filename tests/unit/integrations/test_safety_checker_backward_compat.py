"""
Unit tests for SafetyChecker backward compatibility with per-feature designs.

Tests verify that the bundled design changes (GH-108) don't break existing
workflows that use per-feature design tasks.
"""

from datetime import datetime, timezone

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.nlp_task_utils import SafetyChecker, TaskType


def create_test_task(
    task_id: str,
    name: str,
    description: str,
    labels: list,
    dependencies: list = None,
) -> Task:
    """Helper to create test Task with default values."""
    return Task(
        id=task_id,
        name=name,
        description=description,
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=1.0,
        dependencies=dependencies or [],
        labels=labels,
    )


class TestPerFeatureDesignBackwardCompatibility:
    """Test backward compatibility with per-feature design tasks."""

    @pytest.fixture
    def safety_checker(self):
        """Create SafetyChecker instance."""
        return SafetyChecker()

    @pytest.fixture
    def per_feature_design_tasks(self):
        """Create tasks using per-feature design pattern (legacy)."""
        return [
            create_test_task(
                "task_user_login_design",
                "Design User Login",
                "Design the user login feature",
                ["type:design", "feature:authentication"],
            ),
            create_test_task(
                "task_user_login_implement",
                "Implement User Login",
                "Implement the user login feature",
                ["type:implementation", "feature:authentication"],
            ),
            create_test_task(
                "task_product_search_design",
                "Design Product Search",
                "Design the product search feature",
                ["type:design", "feature:catalog"],
            ),
            create_test_task(
                "task_product_search_implement",
                "Implement Product Search",
                "Implement the product search feature",
                ["type:implementation", "feature:catalog"],
            ),
        ]

    def test_per_feature_designs_create_dependencies(
        self, safety_checker, per_feature_design_tasks
    ):
        """Test that per-feature designs still create dependencies."""
        # Act
        result = safety_checker.apply_implementation_dependencies(
            per_feature_design_tasks
        )

        # Assert - find the implement tasks
        login_impl = next(t for t in result if t.id == "task_user_login_implement")
        search_impl = next(t for t in result if t.id == "task_product_search_implement")

        # Should have dependencies on their design tasks
        assert (
            "task_user_login_design" in login_impl.dependencies
        ), "Per-feature design dependency not created for login!"
        assert (
            "task_product_search_design" in search_impl.dependencies
        ), "Per-feature design dependency not created for search!"

    def test_per_feature_designs_no_cross_domain_deps(
        self, safety_checker, per_feature_design_tasks
    ):
        """Test that per-feature designs don't create cross-domain dependencies."""
        # Act
        result = safety_checker.apply_implementation_dependencies(
            per_feature_design_tasks
        )

        # Assert - find the implement tasks
        login_impl = next(t for t in result if t.id == "task_user_login_implement")
        search_impl = next(t for t in result if t.id == "task_product_search_implement")

        # Should NOT have cross-domain dependencies
        assert (
            "task_product_search_design" not in login_impl.dependencies
        ), "Cross-domain dependency created (login -> search design)!"
        assert (
            "task_user_login_design" not in search_impl.dependencies
        ), "Cross-domain dependency created (search -> login design)!"


class TestSimpleProjectsWithoutBundledDesigns:
    """Test that simple projects without bundled designs still work."""

    @pytest.fixture
    def safety_checker(self):
        """Create SafetyChecker instance."""
        return SafetyChecker()

    @pytest.fixture
    def simple_project_tasks(self):
        """Create simple project tasks (no bundled designs)."""
        return [
            create_test_task(
                "task_1_design",
                "Design Feature 1",
                "Design feature 1",
                ["type:design", "feature:feature1"],
            ),
            create_test_task(
                "task_1_implement",
                "Implement Feature 1",
                "Implement feature 1",
                ["type:implementation", "feature:feature1"],
            ),
            create_test_task(
                "task_2_design",
                "Design Feature 2",
                "Design feature 2",
                ["type:design", "feature:feature2"],
            ),
            create_test_task(
                "task_2_implement",
                "Implement Feature 2",
                "Implement feature 2",
                ["type:implementation", "feature:feature2"],
            ),
        ]

    def test_simple_projects_create_dependencies(
        self, safety_checker, simple_project_tasks
    ):
        """Test that simple projects without bundled designs still create dependencies."""
        # Act
        result = safety_checker.apply_implementation_dependencies(simple_project_tasks)

        # Assert
        impl1 = next(t for t in result if t.id == "task_1_implement")
        impl2 = next(t for t in result if t.id == "task_2_implement")

        # Should have dependencies on their design tasks
        assert (
            "task_1_design" in impl1.dependencies
        ), "Simple project design dependency not created for feature 1!"
        assert (
            "task_2_design" in impl2.dependencies
        ), "Simple project design dependency not created for feature 2!"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def safety_checker(self):
        """Create SafetyChecker instance."""
        return SafetyChecker()

    def test_empty_task_list(self, safety_checker):
        """Test with empty task list."""
        # Act
        result = safety_checker.apply_implementation_dependencies([])

        # Assert - should return empty list without crashing
        assert result == []
