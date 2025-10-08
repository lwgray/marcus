"""
Unit tests for ValidationResult.

This module tests the ValidationResult dataclass and error code constants.
"""

import pytest

from src.ttt2.validation.results import (
    ERROR_CELL_OCCUPIED,
    ERROR_EMPTY_INPUT,
    ERROR_INVALID_FORMAT,
    ERROR_OUT_OF_RANGE,
    ERROR_WRONG_COUNT,
    ValidationResult,
)


@pytest.mark.unit
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

    def test_empty_input_error_code(self):
        """Test creating result with EMPTY_INPUT error code."""
        result = ValidationResult(
            is_valid=False, error_message="Empty input", error_code=ERROR_EMPTY_INPUT
        )

        assert result.is_valid is False
        assert result.error_code == ERROR_EMPTY_INPUT

    def test_invalid_format_error_code(self):
        """Test creating result with INVALID_FORMAT error code."""
        result = ValidationResult(
            is_valid=False,
            error_message="Invalid format",
            error_code=ERROR_INVALID_FORMAT,
        )

        assert result.is_valid is False
        assert result.error_code == ERROR_INVALID_FORMAT

    def test_cell_occupied_error_code(self):
        """Test creating result with CELL_OCCUPIED error code."""
        result = ValidationResult(
            is_valid=False,
            error_message="Cell occupied",
            error_code=ERROR_CELL_OCCUPIED,
        )

        assert result.is_valid is False
        assert result.error_code == ERROR_CELL_OCCUPIED

    def test_wrong_count_error_code(self):
        """Test creating result with WRONG_COUNT error code."""
        result = ValidationResult(
            is_valid=False, error_message="Wrong count", error_code=ERROR_WRONG_COUNT
        )

        assert result.is_valid is False
        assert result.error_code == ERROR_WRONG_COUNT

    def test_partial_valid_result(self):
        """Test creating valid result with only row set."""
        result = ValidationResult(is_valid=True, parsed_row=0, parsed_column=None)

        assert result.is_valid is True
        assert result.parsed_row == 0
        assert result.parsed_column is None

    def test_error_constants_are_strings(self):
        """Test that all error constants are strings."""
        assert isinstance(ERROR_EMPTY_INPUT, str)
        assert isinstance(ERROR_INVALID_FORMAT, str)
        assert isinstance(ERROR_OUT_OF_RANGE, str)
        assert isinstance(ERROR_CELL_OCCUPIED, str)
        assert isinstance(ERROR_WRONG_COUNT, str)

    def test_error_constants_are_unique(self):
        """Test that all error constants have unique values."""
        error_codes = {
            ERROR_EMPTY_INPUT,
            ERROR_INVALID_FORMAT,
            ERROR_OUT_OF_RANGE,
            ERROR_CELL_OCCUPIED,
            ERROR_WRONG_COUNT,
        }
        # All 5 constants should be unique
        assert len(error_codes) == 5
