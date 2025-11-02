"""
Unit tests for PRD complexity classification and constraint extraction.

This module tests the ability of the PRD parser to:
1. Classify feature complexity (atomic, simple, coordinated, distributed)
2. Extract technical constraints from original descriptions
3. Identify components affected by each requirement
4. Determine if design artifacts are needed
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, PRDAnalysis


class TestComplexityClassification:
    """Test feature complexity classification."""

    @pytest.fixture
    def parser(self):
        """Create parser instance with mocked LLM client."""
        parser_instance = AdvancedPRDParser()
        # Mock the llm_client.analyze method
        parser_instance.llm_client.analyze = AsyncMock()
        return parser_instance

    @pytest.mark.asyncio
    async def test_atomic_feature_classification(self, parser):
        """Test that atomic features (single file changes) are correctly classified."""
        # Arrange
        parser.llm_client.analyze.return_value = """{
            "functionalRequirements": [{
                "id": "green_bg",
                "name": "Green Background",
                "description": "Set background color to green",
                "complexity": "atomic",
                "requires_design_artifacts": false,
                "affected_components": ["frontend"]
            }],
            "nonFunctionalRequirements": [],
            "technicalConstraints": ["vanilla-js"],
            "assumptions": []
        }"""

        # Act
        result = await parser._analyze_prd_deeply(
            "Set background to green. Use vanilla JS."
        )

        # Assert
        assert len(result.functional_requirements) == 1
        req = result.functional_requirements[0]
        assert req.get("complexity") == "atomic"
        assert req.get("requires_design_artifacts") is False
        assert "frontend" in req.get("affected_components", [])

    @pytest.mark.asyncio
    async def test_simple_feature_classification(self, parser):
        """Test that simple features (one component) are correctly classified."""
        # Arrange
        parser.llm_client.analyze.return_value = """{
            "functionalRequirements": [{
                "id": "score_display",
                "name": "Score Tracking",
                "description": "Display and update score",
                "complexity": "simple",
                "requires_design_artifacts": false,
                "affected_components": ["frontend"]
            }],
            "nonFunctionalRequirements": [],
            "technicalConstraints": [],
            "assumptions": []
        }"""

        # Act
        result = await parser._analyze_prd_deeply("Add score tracking")

        # Assert
        req = result.functional_requirements[0]
        assert req.get("complexity") == "simple"
        assert req.get("requires_design_artifacts") is False

    @pytest.mark.asyncio
    async def test_coordinated_feature_classification(self, parser):
        """Test that coordinated features (multi-component) are correctly classified."""
        # Arrange
        parser.llm_client.analyze.return_value = """{
            "functionalRequirements": [{
                "id": "user_auth",
                "name": "User Authentication",
                "description": "Login system with API and UI",
                "complexity": "coordinated",
                "requires_design_artifacts": true,
                "affected_components": ["api", "database", "frontend"]
            }],
            "nonFunctionalRequirements": [],
            "technicalConstraints": [],
            "assumptions": []
        }"""

        # Act
        result = await parser._analyze_prd_deeply("Implement user authentication")

        # Assert
        req = result.functional_requirements[0]
        assert req.get("complexity") == "coordinated"
        assert req.get("requires_design_artifacts") is True
        assert len(req.get("affected_components", [])) == 3

    @pytest.mark.asyncio
    async def test_distributed_feature_classification(self, parser):
        """Test that distributed features (multi-service) are correctly classified."""
        # Arrange
        parser.llm_client.analyze.return_value = """{
            "functionalRequirements": [{
                "id": "microservices",
                "name": "Microservice Architecture",
                "description": "Multiple independent services",
                "complexity": "distributed",
                "requires_design_artifacts": true,
                "affected_components": ["auth-service", "user-service", "order-service", "api-gateway"]
            }],
            "nonFunctionalRequirements": [],
            "technicalConstraints": [],
            "assumptions": []
        }"""

        # Act
        result = await parser._analyze_prd_deeply("Build microservice architecture")

        # Assert
        req = result.functional_requirements[0]
        assert req.get("complexity") == "distributed"
        assert req.get("requires_design_artifacts") is True


class TestConstraintExtraction:
    """Test extraction of technical constraints from original descriptions."""

    @pytest.fixture
    def parser(self):
        """Create parser instance with mocked LLM client."""
        parser_instance = AdvancedPRDParser()
        parser_instance.llm_client.analyze = AsyncMock()
        return parser_instance

    @pytest.mark.asyncio
    async def test_vanilla_js_constraint_extraction(self, parser):
        """Test that 'vanilla HTML/CSS/JS' is extracted as a constraint."""
        # Arrange
        parser.llm_client.analyze.return_value = """{
            "functionalRequirements": [{
                "id": "snake_game",
                "name": "Snake Game",
                "description": "Classic snake game",
                "complexity": "coordinated",
                "requires_design_artifacts": true,
                "affected_components": ["frontend"]
            }],
            "nonFunctionalRequirements": [],
            "technicalConstraints": ["vanilla-js", "no-frameworks"],
            "assumptions": []
        }"""

        # Act
        result = await parser._analyze_prd_deeply(
            "Build a snake game. Use vanilla HTML/CSS/JS"
        )

        # Assert
        assert "vanilla-js" in result.technical_constraints
        assert "no-frameworks" in result.technical_constraints

    @pytest.mark.asyncio
    async def test_multiple_constraints_extraction(self, parser):
        """Test extraction of multiple technical constraints."""
        # Arrange
        parser.llm_client.analyze.return_value = """{
            "functionalRequirements": [],
            "nonFunctionalRequirements": [],
            "technicalConstraints": ["python3", "postgresql", "rest-api", "no-orm"],
            "assumptions": []
        }"""

        # Act
        result = await parser._analyze_prd_deeply(
            "Build API with Python 3, PostgreSQL, REST. Don't use ORM."
        )

        # Assert
        assert len(result.technical_constraints) == 4
        assert "python3" in result.technical_constraints
        assert "postgresql" in result.technical_constraints
        assert "rest-api" in result.technical_constraints
        assert "no-orm" in result.technical_constraints

    @pytest.mark.asyncio
    async def test_exclusion_constraints_extraction(self, parser):
        """Test that exclusion constraints (don't use X) are extracted."""
        # Arrange
        parser.llm_client.analyze.return_value = """{
            "functionalRequirements": [],
            "nonFunctionalRequirements": [],
            "technicalConstraints": ["no-react", "no-vue", "no-angular"],
            "assumptions": []
        }"""

        # Act
        result = await parser._analyze_prd_deeply(
            "Build frontend. Don't use React, Vue, or Angular."
        )

        # Assert
        assert "no-react" in result.technical_constraints
        assert "no-vue" in result.technical_constraints
        assert "no-angular" in result.technical_constraints


class TestSnakeGameExample:
    """Test the actual Snake Game example from the issue."""

    @pytest.fixture
    def parser(self):
        """Create parser instance with mocked LLM client."""
        parser_instance = AdvancedPRDParser()
        parser_instance.llm_client.analyze = AsyncMock()
        return parser_instance

    @pytest.mark.asyncio
    async def test_snake_game_green_background_atomic(self, parser):
        """Test that Snake Game green background is classified as atomic."""
        # Arrange
        parser.llm_client.analyze.return_value = """{
            "functionalRequirements": [
                {
                    "id": "green_bg",
                    "name": "Green Background Theme",
                    "description": "Green background for game",
                    "complexity": "atomic",
                    "requires_design_artifacts": false,
                    "affected_components": ["frontend"]
                },
                {
                    "id": "collision",
                    "name": "Collision Detection",
                    "description": "Detect snake collisions",
                    "complexity": "coordinated",
                    "requires_design_artifacts": true,
                    "affected_components": ["game-logic", "rendering"]
                }
            ],
            "nonFunctionalRequirements": [],
            "technicalConstraints": ["vanilla-js", "no-frameworks"],
            "assumptions": []
        }"""

        # Act
        result = await parser._analyze_prd_deeply(
            """Build a snake game with:
            - Green background theme
            - Classic gameplay (grow on eating, die on collision)
            - Keyboard controls
            - Score tracking
            Use vanilla HTML/CSS/JS"""
        )

        # Assert
        green_bg = [r for r in result.functional_requirements if r["id"] == "green_bg"][
            0
        ]
        assert green_bg["complexity"] == "atomic"
        assert green_bg["requires_design_artifacts"] is False

        collision = [
            r for r in result.functional_requirements if r["id"] == "collision"
        ][0]
        assert collision["complexity"] == "coordinated"
        assert collision["requires_design_artifacts"] is True

        assert "vanilla-js" in result.technical_constraints


class TestPRDAnalysisDataclass:
    """Test that PRDAnalysis dataclass has the new fields."""

    def test_prdanalysis_has_constraints_field(self):
        """Test that PRDAnalysis has constraints field."""
        # Arrange & Act
        analysis = PRDAnalysis(
            functional_requirements=[],
            non_functional_requirements=[],
            technical_constraints=["vanilla-js"],
            business_objectives=[],
            user_personas=[],
            success_metrics=[],
            implementation_approach="agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.8,
            original_description="Test description",
        )

        # Assert
        assert hasattr(analysis, "technical_constraints")
        assert analysis.technical_constraints == ["vanilla-js"]

    def test_prdanalysis_has_original_description_field(self):
        """Test that PRDAnalysis has original_description field."""
        # Arrange & Act
        original = "Build a snake game"
        analysis = PRDAnalysis(
            functional_requirements=[],
            non_functional_requirements=[],
            technical_constraints=[],
            business_objectives=[],
            user_personas=[],
            success_metrics=[],
            implementation_approach="agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.8,
            original_description=original,
        )

        # Assert
        assert hasattr(analysis, "original_description")
        assert analysis.original_description == original


class TestAffectedComponents:
    """Test affected_components field extraction and usage."""

    @pytest.fixture
    def parser(self):
        """Create parser instance with mocked LLM client."""
        parser_instance = AdvancedPRDParser()
        parser_instance.llm_client.analyze = AsyncMock()
        return parser_instance

    @pytest.mark.asyncio
    async def test_single_component_feature(self, parser):
        """Test feature affecting single component."""
        # Arrange
        parser.llm_client.analyze.return_value = """{
            "functionalRequirements": [{
                "id": "ui_only",
                "name": "UI Feature",
                "description": "Frontend only feature",
                "complexity": "simple",
                "requires_design_artifacts": false,
                "affected_components": ["frontend"]
            }],
            "nonFunctionalRequirements": [],
            "technicalConstraints": [],
            "assumptions": []
        }"""

        # Act
        result = await parser._analyze_prd_deeply("Add UI feature")

        # Assert
        req = result.functional_requirements[0]
        assert len(req.get("affected_components", [])) == 1
        assert "frontend" in req["affected_components"]

    @pytest.mark.asyncio
    async def test_multi_component_feature(self, parser):
        """Test feature affecting multiple components."""
        # Arrange
        parser.llm_client.analyze.return_value = """{
            "functionalRequirements": [{
                "id": "full_stack",
                "name": "Full Stack Feature",
                "description": "Feature across stack",
                "complexity": "coordinated",
                "requires_design_artifacts": true,
                "affected_components": ["frontend", "api", "database"]
            }],
            "nonFunctionalRequirements": [],
            "technicalConstraints": [],
            "assumptions": []
        }"""

        # Act
        result = await parser._analyze_prd_deeply("Add full stack feature")

        # Assert
        req = result.functional_requirements[0]
        components = req.get("affected_components", [])
        assert len(components) == 3
        assert "frontend" in components
        assert "api" in components
        assert "database" in components
