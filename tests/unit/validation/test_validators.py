"""
Unit tests for validation functions.

This test module verifies the individual validation functions
for range checking and occupancy checking.
"""

import pytest

from src.ttt2.validation.results import ERROR_CELL_OCCUPIED, ERROR_OUT_OF_RANGE
from src.ttt2.validation.validators import validate_occupancy, validate_range


class TestValidateRange:
    """Test suite for validate_range function."""

    @pytest.mark.parametrize(
        "row,col",
        [
            (0, 0),
            (1, 1),
            (2, 2),  # Corners and center
            (0, 1),
            (1, 0),
            (1, 2),
            (2, 1),  # Edges
        ],
    )
    def test_valid_coordinates(self, row, col):
        """Test that valid coordinates pass validation."""
        result = validate_range(row, col)
        assert result.is_valid is True
        assert result.parsed_row == row
        assert result.parsed_column == col

    @pytest.mark.parametrize("row,col", [(3, 2), (-1, 1), (2, 5), (-1, -1), (10, 10)])
    def test_invalid_coordinates(self, row, col):
        """Test that invalid coordinates fail validation."""
        result = validate_range(row, col)
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE
        assert f"({row}, {col})" in result.error_message


class TestValidateOccupancy:
    """Test suite for validate_occupancy function."""

    def test_empty_cell_is_valid(self):
        """Test that empty cell passes validation."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        result = validate_occupancy(board, 1, 1)
        assert result.is_valid is True

    def test_occupied_cell_is_invalid(self):
        """Test that occupied cell fails validation."""
        board = [[" ", " ", " "], [" ", "X", " "], [" ", " ", " "]]
        result = validate_occupancy(board, 1, 1)
        assert result.is_valid is False
        assert result.error_code == ERROR_CELL_OCCUPIED
        assert "occupied" in result.error_message.lower()
