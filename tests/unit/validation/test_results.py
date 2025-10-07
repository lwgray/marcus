"""
Unit tests for ValidationResult.

This test module verifies the ValidationResult dataclass used for
representing input validation outcomes.
"""

import pytest

from src.ttt2.validation.results import ERROR_OUT_OF_RANGE, ValidationResult


class TestValidationResult:
    """Test suite for ValidationResult dataclass."""

    def test_valid_result_creation(self):
        """Test creating a valid ValidationResult."""
        result = ValidationResult(is_valid=True, parsed_row=1, parsed_column=2)

        assert result.is_valid is True
        assert result.error_message is None
        assert result.error_code is None
        assert result.parsed_row == 1
        assert result.parsed_column == 2

    def test_invalid_result_creation(self):
        """Test creating an invalid ValidationResult."""
        result = ValidationResult(
            is_valid=False, error_message="Out of range", error_code=ERROR_OUT_OF_RANGE
        )

        assert result.is_valid is False
        assert result.error_message == "Out of range"
        assert result.error_code == ERROR_OUT_OF_RANGE
        assert result.parsed_row is None
        assert result.parsed_column is None
