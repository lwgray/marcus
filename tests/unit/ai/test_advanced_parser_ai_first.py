"""
Unit tests for AI-first task description functionality in AdvancedPRDParser.

Tests the helper methods that enable clean, AI-generated task descriptions
instead of template boilerplate.
"""

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, PRDAnalysis
from src.core.models import Priority


class TestExtractTaskType:
    """Test suite for _extract_task_type method."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for testing."""
        return AdvancedPRDParser()

    def test_extract_design_type(self, parser):
        """Test extraction of 'design' from task_id."""
        task_id = "task_user_login_design"
        assert parser._extract_task_type(task_id) == "design"

    def test_extract_implement_type(self, parser):
        """Test extraction of 'implement' from task_id."""
        task_id = "task_user_login_implement"
        assert parser._extract_task_type(task_id) == "implement"

    def test_extract_test_type(self, parser):
        """Test extraction of 'test' from task_id."""
        task_id = "task_user_login_test"
        assert parser._extract_task_type(task_id) == "test"

    def test_extract_type_case_insensitive(self, parser):
        """Test type extraction is case insensitive."""
        assert parser._extract_task_type("TASK_DESIGN_1") == "design"
        assert parser._extract_task_type("Task_Implement_1") == "implement"

    def test_unknown_type_defaults_to_implement(self, parser):
        """Test unknown task types default to 'implement'."""
        task_id = "task_user_login_unknown"
        assert parser._extract_task_type(task_id) == "implement"


class TestFindMatchingRequirement:
    """Test suite for _find_matching_requirement method."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for testing."""
        return AdvancedPRDParser()

    @pytest.fixture
    def sample_analysis(self):
        """Create sample PRDAnalysis with requirements."""
        return PRDAnalysis(
            functional_requirements=[
                {
                    "id": "user_login",
                    "name": "User Login",
                    "description": "Users can log in with email and password",
                    "priority": "high",
                },
                {
                    "id": "todo_list_management",
                    "name": "Todo Management",
                    "description": "Users can create, read, update, delete todos",
                    "priority": "medium",
                },
            ],
            non_functional_requirements=[
                {
                    "id": "performance_requirement",
                    "name": "Performance",
                    "description": "System handles 100 concurrent users",
                    "category": "performance",
                }
            ],
            technical_constraints=["Use JWT tokens"],
            business_objectives=["Improve user engagement"],
            user_personas=[],
            success_metrics=["User retention rate"],
            implementation_approach="Agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.85,
        )

    def test_find_functional_requirement(self, parser, sample_analysis):
        """Test finding a functional requirement by task_id."""
        task_id = "task_user_login_design"
        result = parser._find_matching_requirement(task_id, sample_analysis)

        assert result is not None
        assert result["id"] == "user_login"
        assert result["name"] == "User Login"
        assert "email and password" in result["description"]

    def test_find_different_functional_requirement(self, parser, sample_analysis):
        """Test finding a different functional requirement."""
        task_id = "task_todo_list_management_implement"
        result = parser._find_matching_requirement(task_id, sample_analysis)

        assert result is not None
        assert result["id"] == "todo_list_management"
        assert "create, read, update, delete" in result["description"]

    def test_find_non_functional_requirement(self, parser, sample_analysis):
        """Test finding a non-functional requirement."""
        task_id = "nfr_task_performance_requirement"
        result = parser._find_matching_requirement(task_id, sample_analysis)

        assert result is not None
        assert result["id"] == "performance_requirement"
        assert "100 concurrent users" in result["description"]

    def test_requirement_not_found_returns_none(self, parser, sample_analysis):
        """Test that non-existent requirement returns None."""
        task_id = "task_nonexistent_feature_design"
        result = parser._find_matching_requirement(task_id, sample_analysis)

        assert result is None

    def test_unknown_task_format_returns_none(self, parser, sample_analysis):
        """Test that unknown task_id format returns None."""
        task_id = "invalid_format"
        result = parser._find_matching_requirement(task_id, sample_analysis)

        assert result is None


class TestGenerateTaskLabels:
    """Test suite for _generate_task_labels method."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for testing."""
        return AdvancedPRDParser()

    @pytest.fixture
    def sample_analysis(self):
        """Create sample PRDAnalysis for testing."""
        return PRDAnalysis(
            functional_requirements=[],
            non_functional_requirements=[],
            technical_constraints=[],
            business_objectives=[],
            user_personas=[],
            success_metrics=[],
            implementation_approach="Agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.85,
        )

    def test_generates_task_type_label(self, parser, sample_analysis):
        """Test that task type is always included in labels."""
        labels = parser._generate_task_labels("design", "User Login", sample_analysis)

        assert "design" in labels

    def test_generates_authentication_label(self, parser, sample_analysis):
        """Test authentication-related features get auth label."""
        labels = parser._generate_task_labels(
            "implement", "User Authentication", sample_analysis
        )

        assert "authentication" in labels

    def test_generates_api_label(self, parser, sample_analysis):
        """Test API-related features get api label."""
        labels = parser._generate_task_labels(
            "implement", "API Endpoint Creation", sample_analysis
        )

        assert "api" in labels

    def test_generates_user_management_label(self, parser, sample_analysis):
        """Test user-related features get user-management label."""
        labels = parser._generate_task_labels(
            "implement", "User Profile Management", sample_analysis
        )

        assert "user-management" in labels

    def test_removes_duplicate_labels(self, parser, sample_analysis):
        """Test that duplicate labels are removed."""
        # "User API" should trigger both "user-management" and "api"
        labels = parser._generate_task_labels(
            "implement", "User API Endpoint", sample_analysis
        )

        # Check no duplicates (convert to set and back)
        assert len(labels) == len(set(labels))

    def test_preserves_label_order(self, parser, sample_analysis):
        """Test that task type label comes first."""
        labels = parser._generate_task_labels(
            "design", "User Authentication API", sample_analysis
        )

        assert labels[0] == "design"


class TestAIFirstIntegration:
    """Integration tests for AI-first task description flow."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for testing."""
        return AdvancedPRDParser()

    @pytest.fixture
    def sample_analysis(self):
        """Create sample PRDAnalysis matching real task generation."""
        return PRDAnalysis(
            functional_requirements=[
                {
                    "id": "user_registration",
                    "name": "User Registration",
                    "description": "Allow users to register with email and password",
                    "priority": "high",
                }
            ],
            non_functional_requirements=[],
            technical_constraints=["Use bcrypt for passwords"],
            business_objectives=["Grow user base"],
            user_personas=[],
            success_metrics=["Registration conversion rate"],
            implementation_approach="Agile",
            complexity_assessment={"technical": "Medium"},
            risk_factors=[],
            confidence=0.85,
        )

    def test_design_task_extracts_correctly(self, parser, sample_analysis):
        """Test complete flow for design task."""
        task_id = "task_user_registration_design"

        task_type = parser._extract_task_type(task_id)
        requirement = parser._find_matching_requirement(task_id, sample_analysis)
        labels = parser._generate_task_labels(
            task_type, requirement["name"], sample_analysis
        )

        assert task_type == "design"
        assert (
            requirement["description"]
            == "Allow users to register with email and password"
        )
        assert "design" in labels
        assert "user-management" in labels

    def test_implement_task_extracts_correctly(self, parser, sample_analysis):
        """Test complete flow for implement task."""
        task_id = "task_user_registration_implement"

        task_type = parser._extract_task_type(task_id)
        requirement = parser._find_matching_requirement(task_id, sample_analysis)

        assert task_type == "implement"
        assert requirement["id"] == "user_registration"

    def test_requirement_description_is_clean(self, parser, sample_analysis):
        """Test that requirement description is clean (no template boilerplate)."""
        task_id = "task_user_registration_design"
        requirement = parser._find_matching_requirement(task_id, sample_analysis)

        description = requirement["description"]

        # Should NOT contain template phrases
        assert "Research and design architecture" not in description
        assert "Create documentation defining approach" not in description

        # Should contain actual requirement
        assert "register" in description.lower()
        assert "email" in description.lower()
