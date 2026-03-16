"""
Unit tests for prototype project documentation generation.

Verifies that projects with "prototype" in the name or using prototype
complexity mode still receive documentation tasks (fix for issue #147).
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.adaptive_documentation import (
    AdaptiveDocumentationGenerator,
    DocumentationContext,
)
from src.integrations.documentation_tasks import DocumentationTaskGenerator


class TestPrototypeDocumentation:
    """Test suite for prototype project documentation."""

    @pytest.fixture
    def sample_tasks(self) -> list[Task]:
        """Create sample tasks for testing."""
        return [
            Task(
                id="task_1",
                name="Setup database",
                description="Setup PostgreSQL database",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                labels=["type:feature", "component:database"],
                dependencies=[],
                estimated_hours=4.0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                assigned_to=None,
                due_date=None,
            ),
            Task(
                id="task_2",
                name="Implement API endpoints",
                description="Create REST API",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                labels=["type:feature", "component:api"],
                dependencies=["task_1"],
                estimated_hours=8.0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                assigned_to=None,
                due_date=None,
            ),
            Task(
                id="task_3",
                name="Write unit tests",
                description="Add test coverage",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                labels=["type:testing"],
                dependencies=["task_2"],
                estimated_hours=4.0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                assigned_to=None,
                due_date=None,
            ),
        ]

    def test_prototype_name_gets_documentation(self, sample_tasks: list[Task]) -> None:
        """Test projects with 'prototype' in name get documentation."""
        # Arrange
        generator = AdaptiveDocumentationGenerator()
        context = DocumentationContext(
            source_type="nlp_project",
            work_type="new_system",
            project_name="Blog Prototype Platform",
            existing_tasks=sample_tasks,
            completed_work=[],
            feature_labels=set(),
            metadata={},
        )

        # Act
        should_add = generator.should_add_documentation(context)

        # Assert
        assert (
            should_add is True
        ), "Projects with 'prototype' in name should get documentation"

    def test_poc_name_skips_documentation(self, sample_tasks: list[Task]) -> None:
        """Test projects with 'poc' in name skip documentation."""
        # Arrange
        generator = AdaptiveDocumentationGenerator()
        context = DocumentationContext(
            source_type="nlp_project",
            work_type="new_system",
            project_name="Simple POC Test",
            existing_tasks=sample_tasks,
            completed_work=[],
            feature_labels=set(),
            metadata={},
        )

        # Act
        should_add = generator.should_add_documentation(context)

        # Assert
        assert should_add is False, "POC projects should skip documentation"

    def test_demo_name_skips_documentation(self, sample_tasks: list[Task]) -> None:
        """Test projects with 'demo' in name skip documentation."""
        # Arrange
        generator = AdaptiveDocumentationGenerator()
        context = DocumentationContext(
            source_type="nlp_project",
            work_type="new_system",
            project_name="Quick Demo App",
            existing_tasks=sample_tasks,
            completed_work=[],
            feature_labels=set(),
            metadata={},
        )

        # Act
        should_add = generator.should_add_documentation(context)

        # Assert
        assert should_add is False, "Demo projects should skip documentation"

    def test_experiment_name_skips_documentation(
        self, sample_tasks: list[Task]
    ) -> None:
        """Test projects with 'experiment' in name skip documentation."""
        # Arrange
        generator = AdaptiveDocumentationGenerator()
        context = DocumentationContext(
            source_type="nlp_project",
            work_type="new_system",
            project_name="ML Experiment Framework",
            existing_tasks=sample_tasks,
            completed_work=[],
            feature_labels=set(),
            metadata={},
        )

        # Act
        should_add = generator.should_add_documentation(context)

        # Assert
        assert should_add is False, "Experiment projects should skip documentation"

    def test_legacy_generator_prototype_gets_documentation(self) -> None:
        """Test legacy generator allows prototype projects."""
        # Arrange & Act
        should_add = DocumentationTaskGenerator.should_add_documentation_task(
            project_description="Build a blog prototype platform",
            task_count=5,
        )

        # Assert
        assert (
            should_add is True
        ), "Legacy generator should allow prototype in description"

    def test_legacy_generator_poc_skips_documentation(self) -> None:
        """Test legacy generator skips POC projects."""
        # Arrange & Act
        should_add = DocumentationTaskGenerator.should_add_documentation_task(
            project_description="Quick POC for testing API",
            task_count=5,
        )

        # Assert
        assert should_add is False, "Legacy generator should skip POC projects"

    def test_legacy_generator_tiny_project_gets_documentation(self) -> None:
        """Test legacy generator allows tiny projects."""
        # Arrange & Act
        should_add = DocumentationTaskGenerator.should_add_documentation_task(
            project_description="Build a simple blog",
            task_count=2,
        )

        # Assert
        assert (
            should_add is True
        ), "Legacy generator should allow tiny projects to have documentation"

    def test_tiny_project_gets_documentation(self, sample_tasks: list[Task]) -> None:
        """Test projects with <3 tasks get documentation."""
        # Arrange
        generator = AdaptiveDocumentationGenerator()
        tiny_tasks = sample_tasks[:2]  # Only 2 tasks
        context = DocumentationContext(
            source_type="nlp_project",
            work_type="new_system",
            project_name="Blog Platform",
            existing_tasks=tiny_tasks,
            completed_work=[],
            feature_labels=set(),
            metadata={},
        )

        # Act
        should_add = generator.should_add_documentation(context)

        # Assert
        assert should_add is True, "Projects with <3 tasks should get documentation"

    def test_github_issue_always_gets_documentation(
        self, sample_tasks: list[Task]
    ) -> None:
        """Test GitHub issues get documentation even with skip keywords."""
        # Arrange
        generator = AdaptiveDocumentationGenerator()
        context = DocumentationContext(
            source_type="github_issue",
            work_type="bug_fix",
            project_name="Quick Demo POC",
            existing_tasks=sample_tasks,
            completed_work=[],
            feature_labels=set(),
            metadata={},
        )

        # Act
        should_add = generator.should_add_documentation(context)

        # Assert
        assert (
            should_add is True
        ), "GitHub issues should get documentation even with skip keywords"

    def test_normal_project_gets_documentation(self, sample_tasks: list[Task]) -> None:
        """Test normal projects get documentation."""
        # Arrange
        generator = AdaptiveDocumentationGenerator()
        context = DocumentationContext(
            source_type="nlp_project",
            work_type="new_system",
            project_name="E-commerce Platform",
            existing_tasks=sample_tasks,
            completed_work=[],
            feature_labels=set(),
            metadata={},
        )

        # Act
        should_add = generator.should_add_documentation(context)

        # Assert
        assert should_add is True, "Normal projects should get documentation"

    def test_prototype_creates_documentation_task(
        self, sample_tasks: list[Task]
    ) -> None:
        """Test prototype projects create documentation tasks."""
        # Arrange
        generator = AdaptiveDocumentationGenerator()
        context = DocumentationContext(
            source_type="nlp_project",
            work_type="new_system",
            project_name="Blog Prototype Platform",
            existing_tasks=sample_tasks,
            completed_work=[],
            feature_labels=set(),
            metadata={},
        )

        # Act
        doc_tasks = generator.create_documentation_tasks(context)

        # Assert
        assert (
            len(doc_tasks) > 0
        ), "Prototype projects should create documentation tasks"
        assert any(
            "documentation" in task.labels for task in doc_tasks
        ), "Created tasks should have documentation label"
        assert any(
            "Blog Prototype Platform" in task.name for task in doc_tasks
        ), "Task name should include project name"
