"""
Unit tests for complexity-aware task generation.

Tests that complexity mode (prototype/standard/enterprise) correctly influences:
1. Feature breadth (number of features generated)
2. Implementation depth (detail level in feature descriptions)
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints


class TestComplexityAwareGeneration:
    """Test suite for complexity-aware task generation"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client that returns complexity-appropriate responses"""
        mock_client = Mock()
        mock_client.analyze = AsyncMock()
        return mock_client

    @pytest.fixture
    def mock_dependency_inferer(self):
        """Mock dependency inferer"""
        mock_inferer = Mock()
        mock_inferer.infer_dependencies = AsyncMock(return_value=[])
        return mock_inferer

    @pytest.fixture
    def parser(self, mock_llm_client, mock_dependency_inferer):
        """Create AdvancedPRDParser with mocked dependencies"""
        with patch(
            "src.ai.advanced.prd.advanced_parser.LLMAbstraction"
        ) as mock_llm_class:
            mock_llm_class.return_value = mock_llm_client
            with patch(
                "src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"
            ) as mock_dep_class:
                mock_dep_class.return_value = mock_dependency_inferer
                parser = AdvancedPRDParser()
                parser.llm_client = mock_llm_client
                return parser

    @pytest.fixture
    def sample_prd(self):
        """Sample PRD for testing"""
        return "Create a task management application"

    def _create_mock_response(self, feature_count: int, depth: str) -> str:
        """Create a mock AI response with specified feature count and depth"""
        features = []
        for i in range(feature_count):
            if depth == "minimal":
                description = f"Basic feature {i+1}"
                complexity = "atomic"
            elif depth == "standard":
                description = f"Feature {i+1} with error handling and validation"
                complexity = "simple"
            else:  # enterprise
                description = (
                    f"Feature {i+1} with comprehensive error handling, "
                    f"audit logging, monitoring, and edge case coverage"
                )
                complexity = "coordinated"

            features.append(
                {
                    "id": f"feature_{i+1}",
                    "name": f"Feature {i+1}",
                    "description": description,
                    "priority": "high",
                    "complexity": complexity,
                    "requires_design_artifacts": depth == "enterprise",
                    "affected_components": ["api", "database"],
                }
            )

        response = {
            "functionalRequirements": features,
            "nonFunctionalRequirements": [],
            "technicalConstraints": [],
            "businessObjectives": [],
            "userPersonas": [],
            "successMetrics": [],
            "implementationApproach": "agile",
            "complexityAssessment": {
                "technical": "medium",
                "timeline": "weeks",
                "resources": "medium",
            },
            "riskFactors": [],
            "confidence": 0.85,
        }
        return json.dumps(response)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_constraints_passed_to_analyze_prd_deeply(
        self, parser, mock_llm_client, sample_prd
    ):
        """Test that constraints parameter is passed to _analyze_prd_deeply()"""
        # Arrange
        constraints = ProjectConstraints(complexity_mode="prototype")
        mock_llm_client.analyze.return_value = self._create_mock_response(
            feature_count=3, depth="minimal"
        )

        # Act
        await parser._analyze_prd_deeply(sample_prd, constraints)

        # Assert - verify analyze was called and constraints were available
        assert mock_llm_client.analyze.called
        call_args = mock_llm_client.analyze.call_args
        prompt = call_args.kwargs["prompt"]

        # Verify complexity mode is in the prompt
        assert "COMPLEXITY MODE: prototype" in prompt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prototype_mode_prompt_contains_breadth_guidance(
        self, parser, mock_llm_client, sample_prd
    ):
        """Test prototype mode prompt includes feature breadth guidance"""
        # Arrange
        constraints = ProjectConstraints(complexity_mode="prototype")
        mock_llm_client.analyze.return_value = self._create_mock_response(
            feature_count=3, depth="minimal"
        )

        # Act
        await parser._analyze_prd_deeply(sample_prd, constraints)

        # Assert
        call_args = mock_llm_client.analyze.call_args
        prompt = call_args.kwargs["prompt"]

        assert "PROTOTYPE MODE - Speed-focused MVP (3-5 core features)" in prompt
        assert "FEATURE BREADTH:" in prompt
        assert "Include ONLY the absolute minimum" in prompt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prototype_mode_prompt_contains_depth_guidance(
        self, parser, mock_llm_client, sample_prd
    ):
        """Test prototype mode prompt includes implementation depth guidance"""
        # Arrange
        constraints = ProjectConstraints(complexity_mode="prototype")
        mock_llm_client.analyze.return_value = self._create_mock_response(
            feature_count=3, depth="minimal"
        )

        # Act
        await parser._analyze_prd_deeply(sample_prd, constraints)

        # Assert
        call_args = mock_llm_client.analyze.call_args
        prompt = call_args.kwargs["prompt"]

        assert "IMPLEMENTATION DEPTH:" in prompt
        assert 'Use complexity: "atomic" or "simple"' in prompt
        assert "Focus on happy path only" in prompt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_standard_mode_prompt_contains_guidance(
        self, parser, mock_llm_client, sample_prd
    ):
        """Test standard mode prompt includes appropriate guidance"""
        # Arrange
        constraints = ProjectConstraints(complexity_mode="standard")
        mock_llm_client.analyze.return_value = self._create_mock_response(
            feature_count=10, depth="standard"
        )

        # Act
        await parser._analyze_prd_deeply(sample_prd, constraints)

        # Assert
        call_args = mock_llm_client.analyze.call_args
        prompt = call_args.kwargs["prompt"]

        assert "STANDARD MODE - Balanced production app (8-15 features)" in prompt
        assert "Include core features + essential supporting features" in prompt
        assert 'Use complexity: "simple" or "coordinated"' in prompt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enterprise_mode_prompt_contains_breadth_guidance(
        self, parser, mock_llm_client, sample_prd
    ):
        """Test enterprise mode prompt includes comprehensive breadth guidance"""
        # Arrange
        constraints = ProjectConstraints(complexity_mode="enterprise")
        mock_llm_client.analyze.return_value = self._create_mock_response(
            feature_count=25, depth="enterprise"
        )

        # Act
        await parser._analyze_prd_deeply(sample_prd, constraints)

        # Assert
        call_args = mock_llm_client.analyze.call_args
        prompt = call_args.kwargs["prompt"]

        assert "ENTERPRISE MODE - Production-ready system (15-30+ features)" in prompt
        assert "Observability: Monitoring, structured logging" in prompt
        assert "Security: Comprehensive auth, RBAC, audit trails" in prompt
        assert "Admin Tooling: Admin dashboard" in prompt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enterprise_mode_prompt_contains_depth_guidance(
        self, parser, mock_llm_client, sample_prd
    ):
        """Test enterprise mode prompt includes comprehensive depth guidance"""
        # Arrange
        constraints = ProjectConstraints(complexity_mode="enterprise")
        mock_llm_client.analyze.return_value = self._create_mock_response(
            feature_count=25, depth="enterprise"
        )

        # Act
        await parser._analyze_prd_deeply(sample_prd, constraints)

        # Assert
        call_args = mock_llm_client.analyze.call_args
        prompt = call_args.kwargs["prompt"]

        assert "Include comprehensive implementation details" in prompt
        assert 'Use complexity: "coordinated" or "distributed"' in prompt
        assert "security hardening, error recovery, edge cases" in prompt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_exclusions_override_mentioned_in_prompt(
        self, parser, mock_llm_client, sample_prd
    ):
        """Test that prompt emphasizes user exclusions override complexity mode"""
        # Arrange
        constraints = ProjectConstraints(complexity_mode="enterprise")
        mock_llm_client.analyze.return_value = self._create_mock_response(
            feature_count=25, depth="enterprise"
        )

        # Act
        await parser._analyze_prd_deeply(sample_prd, constraints)

        # Assert
        call_args = mock_llm_client.analyze.call_args
        prompt = call_args.kwargs["prompt"]

        assert "User exclusions ALWAYS override complexity mode defaults" in prompt
        assert 'If user says "no authentication", omit it even in enterprise' in prompt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_parse_prd_to_tasks_passes_constraints_to_analyze(
        self, parser, mock_llm_client, sample_prd
    ):
        """Test that parse_prd_to_tasks passes constraints to _analyze_prd_deeply"""
        # Arrange
        constraints = ProjectConstraints(complexity_mode="prototype", team_size=1)
        mock_llm_client.analyze.return_value = self._create_mock_response(
            feature_count=3, depth="minimal"
        )

        # Mock the dependency inference to avoid the AttributeError
        with patch.object(
            parser, "_infer_smart_dependencies", new=AsyncMock(return_value=[])
        ):
            with patch.object(
                parser, "_assess_implementation_risks", new=AsyncMock(return_value={})
            ):
                with patch.object(
                    parser, "_predict_timeline", new=AsyncMock(return_value={})
                ):
                    with patch.object(
                        parser,
                        "_analyze_resource_requirements",
                        new=AsyncMock(return_value={}),
                    ):
                        with patch.object(
                            parser,
                            "_generate_success_criteria",
                            new=AsyncMock(return_value=[]),
                        ):
                            # Act
                            result = await parser.parse_prd_to_tasks(
                                sample_prd, constraints
                            )

        # Assert - verify analyze was called with prompt containing complexity mode
        assert mock_llm_client.analyze.called

        # Check all calls to find the PRD analysis call (first call)
        found_complexity_mode = False
        for call in mock_llm_client.analyze.call_args_list:
            # Get prompt from kwargs or args
            if "prompt" in call.kwargs:
                prompt = call.kwargs["prompt"]
            else:
                prompt = call.args[0] if call.args else ""

            if "COMPLEXITY MODE: prototype" in prompt:
                found_complexity_mode = True
                break

        assert found_complexity_mode, "Complexity mode not found in any analyze() call"
        assert result is not None
