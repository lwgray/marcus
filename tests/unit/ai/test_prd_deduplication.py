"""
Unit tests for functional requirement deduplication in AdvancedPRDParser.

Tests the deduplication logic that prevents duplicate tasks from being created
when the AI generates similar requirements with different names.
"""

from unittest.mock import Mock

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser


class TestPRDDeduplication:
    """Test suite for PRD functional requirement deduplication."""

    @pytest.fixture
    def parser(self):
        """Create parser instance with mocked dependencies."""
        mock_llm = Mock()
        mock_dependency_inferer = Mock()
        return AdvancedPRDParser(mock_llm, mock_dependency_inferer)

    def test_duplicate_ids_detected_and_removed(self, parser):
        """Test that requirements with duplicate IDs are detected and removed."""
        # Arrange
        requirements = [
            {"id": "user_auth", "name": "User Authentication"},
            {"id": "product_catalog", "name": "Product Catalog"},
            {"id": "user_auth", "name": "Login System"},  # Duplicate ID!
        ]

        # Act
        deduplicated = parser._deduplicate_functional_requirements(requirements)

        # Assert
        assert len(deduplicated) == 2, "Should remove duplicate ID"
        assert deduplicated[0]["name"] == "User Authentication"
        assert deduplicated[1]["name"] == "Product Catalog"
        # The second "user_auth" should be skipped

    def test_semantically_similar_names_detected(self, parser):
        """Test that semantically similar feature names are detected as duplicates."""
        # Arrange
        requirements = [
            {"id": "user_auth", "name": "User Authentication"},
            {"id": "auth_system", "name": "Authentication System"},  # Similar!
        ]

        # Act
        deduplicated = parser._deduplicate_functional_requirements(requirements)

        # Assert
        assert len(deduplicated) == 1, "Should detect semantic duplicate"
        assert deduplicated[0]["id"] == "user_auth"
        # "Authentication System" normalized to "auth" should match "User Auth" → "auth"

    def test_auth_authorization_normalized(self, parser):
        """Test that 'authentication' and 'authorization' are both normalized to 'auth'."""
        # Arrange
        requirements = [
            {"id": "user_auth", "name": "User Authentication"},
            {"id": "user_authz", "name": "User Authorization"},  # Similar to auth!
        ]

        # Act
        deduplicated = parser._deduplicate_functional_requirements(requirements)

        # Assert
        assert len(deduplicated) == 1, "Should normalize auth/authz to same value"
        assert deduplicated[0]["id"] == "user_auth"

    def test_system_suffix_removed_in_normalization(self, parser):
        """Test that ' system' suffix is removed during normalization."""
        # Arrange
        requirements = [
            {"id": "user_auth", "name": "User Authentication"},
            {"id": "auth_sys", "name": "User Auth System"},  # Same after normalization
        ]

        # Act
        deduplicated = parser._deduplicate_functional_requirements(requirements)

        # Assert
        assert len(deduplicated) == 1, "Should remove ' system' suffix"
        assert deduplicated[0]["id"] == "user_auth"

    def test_multiple_suffixes_removed(self, parser):
        """Test that multiple common suffixes are removed."""
        # Arrange
        requirements = [
            {"id": "product_mgmt", "name": "Product Management"},
            {"id": "product_mgmt_feature", "name": "Product Management Feature"},
            {"id": "product_mgmt_comp", "name": "Product Management Component"},
            {"id": "product_mgmt_svc", "name": "Product Management Service"},
        ]

        # Act
        deduplicated = parser._deduplicate_functional_requirements(requirements)

        # Assert
        # All normalize to "product mgmt" after removing suffixes and normalization
        assert len(deduplicated) == 1, "Should detect all variations as duplicates"
        assert deduplicated[0]["id"] == "product_mgmt"

    def test_unique_requirements_preserved(self, parser):
        """Test that genuinely unique requirements are all preserved."""
        # Arrange
        requirements = [
            {"id": "user_auth", "name": "User Authentication"},
            {"id": "product_catalog", "name": "Product Catalog"},
            {"id": "shopping_cart", "name": "Shopping Cart"},
            {"id": "checkout", "name": "Checkout Process"},
        ]

        # Act
        deduplicated = parser._deduplicate_functional_requirements(requirements)

        # Assert
        assert len(deduplicated) == 4, "Should preserve all unique requirements"
        req_ids = [req["id"] for req in deduplicated]
        assert req_ids == ["user_auth", "product_catalog", "shopping_cart", "checkout"]

    def test_empty_requirements_list(self, parser):
        """Test deduplication with empty list."""
        # Arrange
        requirements = []

        # Act
        deduplicated = parser._deduplicate_functional_requirements(requirements)

        # Assert
        assert deduplicated == [], "Should handle empty list"

    def test_missing_id_or_name_fields(self, parser):
        """Test deduplication handles missing fields gracefully."""
        # Arrange
        requirements = [
            {"id": "user_auth", "name": "User Authentication"},
            {"id": "", "name": "No ID Feature"},  # Empty ID
            {"id": "product_catalog"},  # Missing name
            {"id": "valid_feature", "name": "Valid Feature"},
        ]

        # Act
        deduplicated = parser._deduplicate_functional_requirements(requirements)

        # Assert
        # Should handle gracefully - empty/missing fields won't match duplicates
        assert len(deduplicated) >= 2, "Should preserve valid requirements"
        # Check that requirements with valid IDs are present
        valid_ids = [req["id"] for req in deduplicated if req.get("id")]
        assert "user_auth" in valid_ids
        assert "valid_feature" in valid_ids

    def test_management_normalized_to_mgmt(self, parser):
        """Test that 'management' is normalized to 'mgmt'."""
        # Arrange
        requirements = [
            {"id": "user_mgmt", "name": "User Management"},
            {"id": "user_mgmt_2", "name": "User Mgmt"},  # Already abbreviated
        ]

        # Act
        deduplicated = parser._deduplicate_functional_requirements(requirements)

        # Assert
        assert len(deduplicated) == 1, "Should normalize management/mgmt"
        assert deduplicated[0]["id"] == "user_mgmt"

    def test_real_world_duplicate_scenario(self, parser):
        """Test the real-world scenario from Social Media Platform bug."""
        # Arrange - mimics tasks 77 and 78 from the bug report
        requirements = [
            {
                "id": "content_upload_scalability",
                "name": "Content Upload Scalability",
                "description": "Handle scalable content uploads",
            },
            {
                "id": "user_interface_usability",
                "name": "User Interface Usability",
                "description": "Improve UI usability",
            },
            # These shouldn't be duplicates since they're different domains
        ]

        # Act
        deduplicated = parser._deduplicate_functional_requirements(requirements)

        # Assert
        assert (
            len(deduplicated) == 2
        ), "Different features should not be detected as duplicates"

    def test_case_insensitive_duplicate_detection(self, parser):
        """Test that duplicate detection is case-insensitive."""
        # Arrange
        requirements = [
            {"id": "user_auth", "name": "User Authentication"},
            {"id": "USER_AUTH", "name": "USER AUTHENTICATION"},  # Same but uppercase
        ]

        # Act
        deduplicated = parser._deduplicate_functional_requirements(requirements)

        # Assert
        assert len(deduplicated) == 1, "Should detect case-insensitive duplicates"
        assert deduplicated[0]["id"] == "user_auth"
