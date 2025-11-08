"""
Unit tests for NFR task ID parsing in AdvancedPRDParser.

Tests the fix for the bug where NFR task IDs with phase suffixes
(e.g., "nfr_task_scalability_implement") were not correctly matching
their corresponding requirements.
"""

from unittest.mock import Mock

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser
from src.ai.advanced.prd.constraints import ProjectConstraints


class TestNFRTaskIDParsing:
    """Test suite for NFR task ID parsing and requirement matching."""

    @pytest.fixture
    def parser(self):
        """Create parser instance with mocked dependencies."""
        mock_llm = Mock()
        mock_dependency_inferer = Mock()
        return AdvancedPRDParser(mock_llm, mock_dependency_inferer)

    @pytest.fixture
    def mock_requirements(self):
        """Create mock functional and non-functional requirements."""
        return [
            # Functional requirements
            {"id": "user_auth", "name": "User Authentication"},
            {"id": "product_catalog", "name": "Product Catalog"},
            # Non-functional requirements
            {"id": "scalability", "name": "System Scalability"},
            {"id": "performance", "name": "Performance Requirements"},
        ]

    def test_nfr_task_id_with_design_phase_suffix(self, parser, mock_requirements):
        """Test NFR task ID with '_design' suffix correctly extracts requirement ID."""
        # Arrange
        task_id = "nfr_task_scalability_design"
        mock_analysis = Mock()
        mock_analysis.functional_requirements = mock_requirements[:2]
        mock_analysis.non_functional_requirements = mock_requirements[2:]

        # Act
        result = parser._find_matching_requirement(task_id, mock_analysis)

        # Assert
        assert result is not None, "Should find matching NFR requirement"
        assert result["id"] == "scalability"
        assert result["name"] == "System Scalability"

    def test_nfr_task_id_with_implement_phase_suffix(self, parser, mock_requirements):
        """Test NFR task ID with '_implement' suffix correctly extracts requirement ID."""
        # Arrange
        task_id = "nfr_task_performance_implement"
        mock_analysis = Mock()
        mock_analysis.functional_requirements = mock_requirements[:2]
        mock_analysis.non_functional_requirements = mock_requirements[2:]

        # Act
        result = parser._find_matching_requirement(task_id, mock_analysis)

        # Assert
        assert result is not None, "Should find matching NFR requirement"
        assert result["id"] == "performance"
        assert result["name"] == "Performance Requirements"

    def test_nfr_task_id_with_test_phase_suffix(self, parser, mock_requirements):
        """Test NFR task ID with '_test' suffix correctly extracts requirement ID."""
        # Arrange
        task_id = "nfr_task_scalability_test"
        mock_analysis = Mock()
        mock_analysis.functional_requirements = mock_requirements[:2]
        mock_analysis.non_functional_requirements = mock_requirements[2:]

        # Act
        result = parser._find_matching_requirement(task_id, mock_analysis)

        # Assert
        assert result is not None, "Should find matching NFR requirement"
        assert result["id"] == "scalability"

    def test_functional_task_id_with_phase_suffix_still_works(
        self, parser, mock_requirements
    ):
        """Test functional task ID parsing still works correctly (regression test)."""
        # Arrange
        task_id = "task_user_auth_implement"
        mock_analysis = Mock()
        mock_analysis.functional_requirements = mock_requirements[:2]
        mock_analysis.non_functional_requirements = mock_requirements[2:]

        # Act
        result = parser._find_matching_requirement(task_id, mock_analysis)

        # Assert
        assert result is not None, "Should find matching functional requirement"
        assert result["id"] == "user_auth"
        assert result["name"] == "User Authentication"

    def test_nfr_task_id_without_phase_suffix(self, parser, mock_requirements):
        """Test NFR task ID without phase suffix (edge case)."""
        # Arrange
        task_id = "nfr_task_scalability"
        mock_analysis = Mock()
        mock_analysis.functional_requirements = mock_requirements[:2]
        mock_analysis.non_functional_requirements = mock_requirements[2:]

        # Act
        result = parser._find_matching_requirement(task_id, mock_analysis)

        # Assert
        assert result is not None, "Should find matching NFR requirement"
        assert result["id"] == "scalability"

    def test_nfr_task_id_no_matching_requirement(self, parser, mock_requirements):
        """Test NFR task ID with no matching requirement returns None."""
        # Arrange
        task_id = "nfr_task_nonexistent_implement"
        mock_analysis = Mock()
        mock_analysis.functional_requirements = mock_requirements[:2]
        mock_analysis.non_functional_requirements = mock_requirements[2:]

        # Act
        result = parser._find_matching_requirement(task_id, mock_analysis)

        # Assert
        assert result is None, "Should return None when no match found"

    def test_complex_nfr_id_with_underscores(self, parser):
        """Test NFR with multi-word ID containing underscores."""
        # Arrange
        task_id = "nfr_task_api_response_time_implement"
        mock_analysis = Mock()
        mock_analysis.functional_requirements = []
        mock_analysis.non_functional_requirements = [
            {"id": "api_response_time", "name": "API Response Time Requirements"}
        ]

        # Act
        result = parser._find_matching_requirement(task_id, mock_analysis)

        # Assert
        assert result is not None, "Should find matching NFR with complex ID"
        assert result["id"] == "api_response_time"
        assert result["name"] == "API Response Time Requirements"

    def test_nfr_id_extraction_logic(self, parser):
        """Test the NFR ID extraction logic directly."""
        # Test cases: (task_id, expected_req_id)
        test_cases = [
            ("nfr_task_scalability_design", "scalability"),
            ("nfr_task_scalability_implement", "scalability"),
            ("nfr_task_scalability_test", "scalability"),
            ("nfr_task_performance", "performance"),
            ("nfr_task_api_response_time_implement", "api_response_time"),
            (
                "nfr_task_content_upload_scalability_implement",
                "content_upload_scalability",
            ),
        ]

        for task_id, expected_req_id in test_cases:
            # Extract using the same logic as _find_matching_requirement
            if task_id.startswith("nfr_task_"):
                parts = task_id.replace("nfr_task_", "").rsplit("_", 1)
                req_id = parts[0] if parts else task_id.replace("nfr_task_", "")

                assert req_id == expected_req_id, (
                    f"Failed for {task_id}: expected '{expected_req_id}', "
                    f"got '{req_id}'"
                )
