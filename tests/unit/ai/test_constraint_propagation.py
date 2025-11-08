"""
Unit tests for constraint propagation through task generation pipeline.

This module tests that technical constraints extracted during PRD analysis
flow through the entire task generation pipeline and appear in task descriptions.

The goal is to ensure constraints like "vanilla-js" or "no-frameworks" are
preserved throughout the process and influence task descriptions.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, PRDAnalysis


class TestConstraintPropagationToTaskDescriptions:
    """Test that constraints appear in generated task descriptions."""

    @pytest.fixture
    def parser(self):
        """Create parser instance with mocked LLM client."""
        parser_instance = AdvancedPRDParser()
        parser_instance.llm_client.analyze = AsyncMock()
        return parser_instance

    @pytest.fixture
    def mock_analysis_with_constraints(self):
        """Create mock PRDAnalysis with technical constraints."""
        return PRDAnalysis(
            functional_requirements=[
                {
                    "id": "snake_game",
                    "name": "Snake Game",
                    "description": "Classic snake game with collision detection",
                    "complexity": "coordinated",
                    "requires_design_artifacts": True,
                }
            ],
            non_functional_requirements=[],
            technical_constraints=["vanilla-js", "no-frameworks", "html5-canvas"],
            business_objectives=[],
            user_personas=[],
            success_metrics=[],
            implementation_approach="agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.9,
            original_description="Build a snake game. Use vanilla HTML/CSS/JS only.",
        )

    @pytest.mark.asyncio
    async def test_constraints_passed_to_description_generation(
        self, parser, mock_analysis_with_constraints
    ):
        """Test that technical constraints are passed to task description generation."""
        # Arrange
        parser.llm_client.analyze.return_value = (
            "Design API using vanilla JavaScript without any frameworks"
        )

        # Act
        description = await parser._generate_task_description_for_type(
            base_description="Classic snake game with collision detection",
            task_type="design",
            feature_name="Snake Game",
            constraints=mock_analysis_with_constraints.technical_constraints,
            original_description=mock_analysis_with_constraints.original_description,
        )

        # Assert
        # Verify that LLM was called with a prompt containing constraints
        assert parser.llm_client.analyze.called
        call_args = parser.llm_client.analyze.call_args
        prompt = call_args[0][0]  # First positional argument is the prompt
        prompt_lower = prompt.lower()
        # Check for vanilla js (could be "vanilla-js", "vanilla js", or "vanilla javascript")
        assert (
            "vanilla" in prompt_lower and "js" in prompt_lower
        ) or "vanilla javascript" in prompt_lower
        # Check for framework prohibition (could be "no-frameworks", "without frameworks", etc.)
        assert "framework" in prompt_lower

    @pytest.mark.asyncio
    async def test_original_description_included_in_prompt(
        self, parser, mock_analysis_with_constraints
    ):
        """Test that original user description is included in AI prompt."""
        # Arrange
        parser.llm_client.analyze.return_value = "Implement using vanilla HTML/CSS/JS"

        # Act
        description = await parser._generate_task_description_for_type(
            base_description="Classic snake game",
            task_type="implementation",
            feature_name="Snake Game",
            constraints=mock_analysis_with_constraints.technical_constraints,
            original_description=mock_analysis_with_constraints.original_description,
        )

        # Assert
        call_args = parser.llm_client.analyze.call_args
        prompt = call_args[0][0]
        assert (
            "vanilla HTML/CSS/JS" in prompt
            or mock_analysis_with_constraints.original_description in prompt
        )


class TestConstraintValidation:
    """Test that generated descriptions don't violate constraints."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    def test_detect_framework_violation_in_description(self, parser):
        """Test detection of framework usage that violates constraints."""
        # Arrange
        description = "Implement the feature using React components and hooks"
        constraints = ["vanilla-js", "no-frameworks", "no-react"]

        # Act
        violations = parser._check_constraint_violations(description, constraints)

        # Assert
        assert len(violations) > 0
        assert any("react" in v.lower() for v in violations)

    def test_no_violations_with_vanilla_js(self, parser):
        """Test that vanilla JS description passes validation."""
        # Arrange
        description = (
            "Implement using plain JavaScript with DOM manipulation "
            "and HTML5 Canvas API"
        )
        constraints = ["vanilla-js", "no-frameworks"]

        # Act
        violations = parser._check_constraint_violations(description, constraints)

        # Assert
        assert len(violations) == 0

    def test_detect_orm_violation(self, parser):
        """Test detection of ORM usage when constrained."""
        # Arrange
        description = "Set up SQLAlchemy ORM models and relationships"
        constraints = ["no-orm", "raw-sql-only"]

        # Act
        violations = parser._check_constraint_violations(description, constraints)

        # Assert
        assert len(violations) > 0
        assert any("orm" in v.lower() or "sqlalchemy" in v.lower() for v in violations)


class TestConstraintPropagationEndToEnd:
    """Test constraint flow from PRD analysis through task generation."""

    @pytest.fixture
    def parser(self):
        """Create parser instance with mocked LLM client."""
        parser_instance = AdvancedPRDParser()
        parser_instance.llm_client.analyze = AsyncMock()
        return parser_instance

    @pytest.fixture
    def mock_constraints(self):
        """Create mock ProjectConstraints."""
        constraints = Mock()
        constraints.technology_constraints = ["vanilla-js"]
        constraints.quality_requirements = {"project_size": "standard"}
        return constraints

    @pytest.mark.asyncio
    async def test_end_to_end_constraint_propagation(self, parser, mock_constraints):
        """Test that constraints flow from analysis through to task descriptions."""
        # Arrange
        parser.llm_client.analyze.return_value = (
            "Design game architecture using vanilla JavaScript patterns"
        )

        analysis = PRDAnalysis(
            functional_requirements=[
                {
                    "id": "game",
                    "name": "Game Feature",
                    "description": "Build game",
                    "complexity": "simple",
                }
            ],
            non_functional_requirements=[],
            technical_constraints=["vanilla-js", "no-frameworks"],
            business_objectives=[],
            user_personas=[],
            success_metrics=[],
            implementation_approach="agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.8,
            original_description="Build a game. Use vanilla JS only.",
        )

        # Store the task metadata
        parser._task_metadata = {
            "task_game_implement": {
                "original_name": "Implement Game Feature",
                "type": "implementation",
                "epic_id": "epic_game",
                "requirement": analysis.functional_requirements[0],
            }
        }

        # Act
        task = await parser._generate_detailed_task(
            task_id="task_game_implement",
            epic_id="epic_game",
            analysis=analysis,
            constraints=mock_constraints,
            sequence=1,
        )

        # Assert
        # Verify constraints were passed to description generation
        assert parser.llm_client.analyze.called
        call_args = parser.llm_client.analyze.call_args
        prompt = call_args[0][0]
        assert (
            "vanilla" in prompt.lower()
            or "no-frameworks" in prompt.lower()
            or "constraint" in prompt.lower()
        )


class TestConstraintFormattingInPrompts:
    """Test how constraints are formatted in AI prompts."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    def test_format_constraints_for_prompt(self, parser):
        """Test that constraints are formatted properly for AI prompts."""
        # Arrange
        constraints = ["vanilla-js", "no-frameworks", "html5-canvas"]

        # Act
        formatted = parser._format_constraints_for_prompt(constraints)

        # Assert
        assert "vanilla" in formatted.lower()
        assert "framework" in formatted.lower()
        assert "canvas" in formatted.lower()
        # Should be readable, not just comma-separated
        assert len(formatted) > len(", ".join(constraints))

    def test_format_empty_constraints(self, parser):
        """Test handling of empty constraint list."""
        # Arrange
        constraints = []

        # Act
        formatted = parser._format_constraints_for_prompt(constraints)

        # Assert
        assert formatted == "" or formatted.lower() == "none"

    def test_format_exclusion_constraints(self, parser):
        """Test formatting of exclusion constraints (no-X patterns)."""
        # Arrange
        constraints = ["no-react", "no-vue", "no-angular", "no-orm"]

        # Act
        formatted = parser._format_constraints_for_prompt(constraints)

        # Assert
        # Should convert "no-X" to readable "do not use X"
        assert (
            "do not use" in formatted.lower()
            or "avoid" in formatted.lower()
            or "without" in formatted.lower()
        )
