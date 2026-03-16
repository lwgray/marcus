"""
Unit tests for intelligent task pattern selection.

This module tests the ability to select appropriate task patterns based on:
1. Feature complexity (atomic, simple, coordinated, distributed)
2. Project complexity mode (prototype, standard, enterprise)
3. Presence of design artifacts requirement
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser


class TestAtomicFeaturePatterns:
    """Test task pattern selection for atomic features."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    def test_atomic_generates_one_task_prototype(self, parser):
        """Test that atomic features generate 1 task in prototype mode."""
        # Arrange
        requirement = {
            "id": "green_bg",
            "name": "Green Background",
            "complexity": "atomic",
            "requires_design_artifacts": False,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="prototype")

        # Assert
        assert len(tasks) == 1
        assert tasks[0]["type"] == "implementation"

    def test_atomic_generates_one_task_standard(self, parser):
        """Test that atomic features generate 1 task in standard mode."""
        # Arrange
        requirement = {
            "id": "green_bg",
            "name": "Green Background",
            "complexity": "atomic",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="standard")

        # Assert
        assert len(tasks) == 1
        assert tasks[0]["type"] == "implementation"

    def test_atomic_generates_two_tasks_enterprise(self, parser):
        """Test that atomic features generate 2 tasks in enterprise mode (impl + test)."""
        # Arrange
        requirement = {
            "id": "green_bg",
            "name": "Green Background",
            "complexity": "atomic",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="enterprise")

        # Assert
        assert len(tasks) == 2
        assert tasks[0]["type"] == "implementation"
        assert tasks[1]["type"] == "testing"


class TestSimpleFeaturePatterns:
    """Test task pattern selection for simple features."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    def test_simple_generates_one_task_prototype(self, parser):
        """Test that simple features generate 1 task in prototype mode."""
        # Arrange
        requirement = {
            "id": "score_display",
            "name": "Score Tracking",
            "complexity": "simple",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="prototype")

        # Assert
        assert len(tasks) == 1
        assert tasks[0]["type"] == "implementation"

    def test_simple_generates_two_tasks_standard(self, parser):
        """Test that simple features generate 2 tasks in standard mode."""
        # Arrange
        requirement = {
            "id": "score_display",
            "name": "Score Tracking",
            "complexity": "simple",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="standard")

        # Assert
        assert len(tasks) == 2
        assert tasks[0]["type"] == "implementation"
        assert tasks[1]["type"] == "testing"

    def test_simple_generates_three_tasks_enterprise(self, parser):
        """Test that simple features generate 3 tasks in enterprise mode."""
        # Arrange
        requirement = {
            "id": "score_display",
            "name": "Score Tracking",
            "complexity": "simple",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="enterprise")

        # Assert
        assert len(tasks) == 3
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert tasks[2]["type"] == "testing"


class TestCoordinatedFeaturePatterns:
    """Test task pattern selection for coordinated features."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    def test_coordinated_generates_two_tasks_prototype(self, parser):
        """Test that coordinated features generate 2 tasks in prototype mode."""
        # Arrange
        requirement = {
            "id": "user_auth",
            "name": "User Authentication",
            "complexity": "coordinated",
            "requires_design_artifacts": True,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="prototype")

        # Assert
        assert len(tasks) == 2
        assert tasks[0]["type"] == "implementation"
        assert tasks[1]["type"] == "testing"

    def test_coordinated_generates_three_tasks_standard(self, parser):
        """Test that coordinated features generate 3 tasks in standard mode."""
        # Arrange
        requirement = {
            "id": "user_auth",
            "name": "User Authentication",
            "complexity": "coordinated",
            "requires_design_artifacts": True,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="standard")

        # Assert
        assert len(tasks) == 3
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert tasks[2]["type"] == "testing"

    def test_coordinated_generates_three_tasks_enterprise(self, parser):
        """Test that coordinated features generate 3 tasks in enterprise mode."""
        # Arrange
        requirement = {
            "id": "user_auth",
            "name": "User Authentication",
            "complexity": "coordinated",
            "requires_design_artifacts": True,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="enterprise")

        # Assert
        assert len(tasks) == 3
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert tasks[2]["type"] == "testing"


class TestDistributedFeaturePatterns:
    """Test task pattern selection for distributed features."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    def test_distributed_generates_two_tasks_prototype(self, parser):
        """Test that distributed features generate 2 tasks in prototype mode."""
        # Arrange
        requirement = {
            "id": "microservices",
            "name": "Microservice Architecture",
            "complexity": "distributed",
            "requires_design_artifacts": True,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="prototype")

        # Assert
        assert len(tasks) == 2
        assert tasks[0]["type"] == "implementation"
        assert tasks[1]["type"] == "testing"

    def test_distributed_generates_three_tasks_standard(self, parser):
        """Test that distributed features generate 3 tasks in standard mode."""
        # Arrange
        requirement = {
            "id": "microservices",
            "name": "Microservice Architecture",
            "complexity": "distributed",
            "requires_design_artifacts": True,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="standard")

        # Assert
        assert len(tasks) == 3
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert tasks[2]["type"] == "testing"

    def test_distributed_generates_three_tasks_enterprise(self, parser):
        """Test that distributed features generate 3 tasks in enterprise mode."""
        # Arrange
        requirement = {
            "id": "microservices",
            "name": "Microservice Architecture",
            "complexity": "distributed",
            "requires_design_artifacts": True,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="enterprise")

        # Assert
        assert len(tasks) == 3
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert tasks[2]["type"] == "testing"


class TestTaskIdGeneration:
    """Test that task IDs are generated correctly."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    def test_task_ids_have_correct_format(self, parser):
        """Test that generated task IDs follow naming convention."""
        # Arrange
        requirement = {
            "id": "user_auth",
            "name": "User Authentication",
            "complexity": "coordinated",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="standard")

        # Assert
        assert tasks[0]["id"] == "task_user_auth_design"
        assert tasks[1]["id"] == "task_user_auth_implement"
        assert tasks[2]["id"] == "task_user_auth_test"

    def test_task_names_include_feature_name(self, parser):
        """Test that generated task names include the feature name."""
        # Arrange
        requirement = {
            "id": "user_auth",
            "name": "User Authentication",
            "complexity": "coordinated",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="standard")

        # Assert
        assert "User Authentication" in tasks[0]["name"]
        assert "User Authentication" in tasks[1]["name"]
        assert "User Authentication" in tasks[2]["name"]


class TestBreakDownEpicIntegration:
    """Test that _break_down_epic uses _select_task_pattern."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    @pytest.fixture
    def mock_analysis(self):
        """Create mock PRDAnalysis."""
        return Mock(functional_requirements=[])

    @pytest.fixture
    def mock_constraints_standard(self):
        """Create mock constraints with standard mode."""
        constraints = Mock()
        constraints.quality_requirements = {"project_size": "standard"}
        return constraints

    @pytest.mark.asyncio
    async def test_break_down_epic_uses_complexity(
        self, parser, mock_analysis, mock_constraints_standard
    ):
        """Test that _break_down_epic respects complexity field."""
        # Arrange
        requirement = {
            "id": "atomic_feature",
            "name": "Atomic Feature",
            "complexity": "atomic",
            "priority": "high",
        }

        # Act
        tasks = await parser._break_down_epic(
            requirement, mock_analysis, mock_constraints_standard
        )

        # Assert
        assert len(tasks) == 1  # Atomic should only get 1 task in standard mode
        assert tasks[0]["type"] == "implementation"

    @pytest.mark.asyncio
    async def test_break_down_epic_defaults_to_coordinated_if_no_complexity(
        self, parser, mock_analysis, mock_constraints_standard
    ):
        """Test that _break_down_epic defaults to coordinated for backward compatibility."""
        # Arrange
        requirement = {
            "id": "old_feature",
            "name": "Old Feature Without Complexity",
            "priority": "high",
            # No complexity field (for backward compatibility)
        }

        # Act
        tasks = await parser._break_down_epic(
            requirement, mock_analysis, mock_constraints_standard
        )

        # Assert
        # Should default to coordinated behavior (3 tasks)
        assert len(tasks) == 3
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert tasks[2]["type"] == "testing"


class TestComplexityModeEffects:
    """Test how complexity mode affects task generation."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    def test_prototype_simplifies_coordinated_features(self, parser):
        """Test that prototype mode simplifies coordinated features."""
        # Arrange
        requirement = {
            "id": "complex_feature",
            "name": "Complex Feature",
            "complexity": "coordinated",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="prototype")

        # Assert
        # Prototype should skip design phase for speed
        assert len(tasks) == 2
        assert tasks[0]["type"] == "implementation"
        assert tasks[1]["type"] == "testing"

    def test_enterprise_adds_design_to_simple_features(self, parser):
        """Test that enterprise mode adds design phase to simple features."""
        # Arrange
        requirement = {
            "id": "simple_feature",
            "name": "Simple Feature",
            "complexity": "simple",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="enterprise")

        # Assert
        # Enterprise should add design for traceability
        assert len(tasks) == 3
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert tasks[2]["type"] == "testing"

    def test_standard_mode_uses_intelligent_patterns(self, parser):
        """Test that standard mode uses complexity-based patterns."""
        # Arrange
        atomic_req = {"id": "atomic", "name": "Atomic", "complexity": "atomic"}
        simple_req = {"id": "simple", "name": "Simple", "complexity": "simple"}
        coordinated_req = {
            "id": "coordinated",
            "name": "Coordinated",
            "complexity": "coordinated",
        }

        # Act
        atomic_tasks = parser._select_task_pattern(
            atomic_req, complexity_mode="standard"
        )
        simple_tasks = parser._select_task_pattern(
            simple_req, complexity_mode="standard"
        )
        coordinated_tasks = parser._select_task_pattern(
            coordinated_req, complexity_mode="standard"
        )

        # Assert
        assert len(atomic_tasks) == 1  # Just implementation
        assert len(simple_tasks) == 2  # Implementation + test
        assert len(coordinated_tasks) == 3  # Design + implementation + test
