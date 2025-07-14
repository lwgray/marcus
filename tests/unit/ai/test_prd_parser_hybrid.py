"""
Unit tests for PRD parser hybrid approach with standardized template
"""

import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import (
    AdvancedPRDParser,
    PRDAnalysis,
    ProjectConstraints,
)


class TestPRDParserHybridApproach:
    """Test PRD parser handles both standardized and legacy formats"""

    @pytest.fixture
    def parser(self):
        """Create parser with mocked dependencies"""
        with patch("src.ai.advanced.prd.advanced_parser.LLMAbstraction"):
            with patch("src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"):
                return AdvancedPRDParser()

    @pytest.fixture
    def mock_constraints(self):
        """Create mock project constraints"""
        return ProjectConstraints(team_size=2)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_break_down_epic_with_standardized_format(
        self, parser, mock_constraints
    ):
        """Test epic breakdown with standardized template format"""
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
        )

        # Standardized format from template
        req = {
            "id": "crud_operations",
            "name": "CRUD Operations",
            "description": "Create, Read, Update, Delete operations for todos",
            "priority": "high",
        }

        tasks = await parser._break_down_epic(req, analysis, mock_constraints)

        assert len(tasks) == 3
        assert tasks[0]["id"] == "task_crud_operations_design"
        assert tasks[0]["name"] == "Design CRUD Operations"
        assert tasks[1]["id"] == "task_crud_operations_implement"
        assert tasks[2]["id"] == "task_crud_operations_test"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_break_down_epic_logs_deviation_from_template(
        self, parser, mock_constraints, caplog
    ):
        """Test that deviations from template are logged"""
        analysis = PRDAnalysis(
            functional_requirements=[{"feature": "User Auth"}],
            non_functional_requirements=[],
            technical_constraints=[],
            business_objectives=[],
            user_personas=[],
            success_metrics=[],
            implementation_approach="agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.8,
        )

        # Legacy format (missing 'id' and 'name' fields)
        req = {"feature": "User Auth", "description": "JWT authentication"}

        with caplog.at_level(logging.WARNING):
            tasks = await parser._break_down_epic(req, analysis, mock_constraints)

        # Check that warnings were logged
        assert "AI deviated from template format" in caplog.text
        assert "Expected 'name' field" in caplog.text
        assert "Expected 'id' field" in caplog.text

        # Should still generate correct tasks
        assert len(tasks) == 3
        assert "task_user_auth_design" in tasks[0]["id"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_nfr_tasks_with_standardized_format(
        self, parser, mock_constraints
    ):
        """Test NFR task creation with standardized template format"""
        nfrs = [
            {
                "id": "performance",
                "name": "Performance",
                "description": "Handle 100 requests per second",
                "category": "performance",
            },
            {
                "id": "security",
                "name": "Security",
                "description": "JWT token authentication",
                "category": "security",
            },
        ]

        tasks = await parser._create_nfr_tasks(nfrs, mock_constraints)

        assert len(tasks) == 2
        assert tasks[0]["id"] == "nfr_task_performance"
        assert tasks[0]["name"] == "Implement Performance"
        assert tasks[1]["id"] == "nfr_task_security"
        assert tasks[1]["name"] == "Implement Security"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_nfr_tasks_fallback_with_logging(
        self, parser, mock_constraints, caplog
    ):
        """Test NFR creation falls back and logs when template not followed"""
        nfrs = [
            {"requirement": "Scalability", "target": "1000 users"},
            {"description": "Data Privacy"},
        ]

        with caplog.at_level(logging.WARNING):
            tasks = await parser._create_nfr_tasks(nfrs, mock_constraints)

        # Check warnings were logged
        assert "NFR deviated from template format" in caplog.text

        # Should still create tasks correctly
        assert len(tasks) == 2
        assert tasks[0]["id"] == "nfr_task_scalability"
        assert tasks[1]["id"] == "nfr_task_data_privacy"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_task_hierarchy_mixed_formats(
        self, parser, mock_constraints, caplog
    ):
        """Test hierarchy generation with mix of standardized and legacy formats"""
        analysis = PRDAnalysis(
            functional_requirements=[
                # Standardized format
                {
                    "id": "crud_operations",
                    "name": "CRUD Operations",
                    "description": "CRUD for todos",
                    "priority": "high",
                },
                # Legacy format with 'feature'
                {"feature": "User Authentication"},
                # Legacy format with 'description'
                {"description": "Data Validation"},
                # Empty requirement to test ultimate fallback
                {},
            ],
            non_functional_requirements=[
                {"id": "performance", "name": "Performance"},
                {"requirement": "Security"},  # Legacy format
            ],
            technical_constraints=[],
            business_objectives=[],
            user_personas=[],
            success_metrics=[],
            implementation_approach="agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.8,
        )

        with caplog.at_level(logging.DEBUG):
            hierarchy = await parser._generate_task_hierarchy(
                analysis, mock_constraints
            )

        # Check that fallback IDs were logged
        assert "Generated fallback ID" in caplog.text

        # Should have correct epic IDs
        assert "epic_crud_operations" in hierarchy  # Standardized
        assert "epic_user_authentication" in hierarchy  # Fallback from feature
        assert "epic_data_validation" in hierarchy  # Fallback from description
        # Note: Empty requirements are filtered out, not converted to fallback epics

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_prd_implementation_approach_handling(self, parser):
        """Test that implementationApproach is handled correctly"""
        # Mock the JSON parser to return our standardized format
        with patch("src.utils.json_parser.parse_ai_json_response") as mock_parse:
            mock_parse.return_value = {
                "functionalRequirements": [],
                "nonFunctionalRequirements": [],
                "technicalConstraints": [],
                "businessObjectives": [],
                "userPersonas": [],
                "successMetrics": [],
                "implementationApproach": "iterative",  # Standardized field name
                "complexityAssessment": {"technical": "medium"},
                "riskFactors": [],
                "confidence": 0.9,
            }

            with patch.object(
                parser.llm_client, "analyze", new_callable=AsyncMock
            ) as mock_analyze:
                mock_analyze.return_value = '{"test": "data"}'

                result = await parser._analyze_prd_deeply("Test PRD")

                assert result.implementation_approach == "iterative"
                assert result.confidence == 0.9
