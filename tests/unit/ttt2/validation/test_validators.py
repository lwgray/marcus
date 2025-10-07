"""
Unit tests for validation functions.

This module tests validate_range and validate_occupancy functions.
"""

import pytest

from src.ttt2.validation.results import ERROR_CELL_OCCUPIED, ERROR_OUT_OF_RANGE
from src.ttt2.validation.validators import validate_occupancy, validate_range


@pytest.mark.unit
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
        assert result.error_message is None
        assert result.error_code is None

    @pytest.mark.parametrize(
        "row,col", [(3, 2), (-1, 1), (2, 5), (-1, -1), (10, 10), (0, 3), (3, 0)]
    )
    def test_invalid_coordinates(self, row, col):
        """Test that invalid coordinates fail validation."""
        result = validate_range(row, col)
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE
        assert f"({row}, {col})" in result.error_message
        assert result.parsed_row is None
        assert result.parsed_column is None

    def test_row_zero_col_zero(self):
        """Test top-left corner (0, 0)."""
        result = validate_range(0, 0)
        assert result.is_valid is True
        assert result.parsed_row == 0
        assert result.parsed_column == 0

    def test_row_two_col_two(self):
        """Test bottom-right corner (2, 2)."""
        result = validate_range(2, 2)
        assert result.is_valid is True
        assert result.parsed_row == 2
        assert result.parsed_column == 2

    def test_all_valid_positions(self):
        """Test all 9 valid board positions."""
        for row in range(3):
            for col in range(3):
                result = validate_range(row, col)
                assert result.is_valid is True
                assert result.parsed_row == row
                assert result.parsed_column == col

    def test_row_negative_col_valid(self):
        """Test negative row with valid column."""
        result = validate_range(-1, 1)
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE

    def test_row_valid_col_negative(self):
        """Test valid row with negative column."""
        result = validate_range(1, -1)
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE

    def test_row_too_high(self):
        """Test row > 2."""
        result = validate_range(3, 1)
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE

    def test_col_too_high(self):
        """Test column > 2."""
        result = validate_range(1, 3)
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE

    def test_both_coordinates_too_high(self):
        """Test both row and column > 2."""
        result = validate_range(5, 5)
        assert result.is_valid is False
        assert "(5, 5)" in result.error_message

    def test_both_coordinates_negative(self):
        """Test both row and column negative."""
        result = validate_range(-2, -3)
        assert result.is_valid is False
        assert "(-2, -3)" in result.error_message

    def test_error_message_contains_hint(self):
        """Test that error message contains helpful hint."""
        result = validate_range(5, 5)
        assert result.is_valid is False
        # Check for hint in error message
        assert "0 and 2" in result.error_message or "0 to 2" in result.error_message


@pytest.mark.unit
class TestValidateOccupancy:
    """Test suite for validate_occupancy function."""

    @pytest.fixture
    def empty_board(self):
        """Provide empty board."""
        return [[" " for _ in range(3)] for _ in range(3)]

    @pytest.fixture
    def partial_board(self):
        """Provide board with some moves."""
        return [["X", " ", "O"], [" ", "X", " "], ["O", " ", " "]]

    @pytest.fixture
    def full_board(self):
        """Provide completely filled board."""
        return [["X", "O", "X"], ["O", "X", "O"], ["X", "O", "X"]]

    def test_empty_cell_is_valid(self, empty_board):
        """Test that empty cell passes validation."""
        result = validate_occupancy(empty_board, 1, 1)
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 1
        assert result.error_message is None
        assert result.error_code is None

    def test_all_empty_cells_valid(self, empty_board):
        """Test all cells on empty board are valid."""
        for row in range(3):
            for col in range(3):
                result = validate_occupancy(empty_board, row, col)
                assert result.is_valid is True

    def test_occupied_cell_with_x(self, partial_board):
        """Test that cell occupied by X fails validation."""
        result = validate_occupancy(partial_board, 1, 1)  # Has 'X'
        assert result.is_valid is False
        assert result.error_code == ERROR_CELL_OCCUPIED
        assert "occupied" in result.error_message.lower()

    def test_occupied_cell_with_o(self, partial_board):
        """Test that cell occupied by O fails validation."""
        result = validate_occupancy(partial_board, 0, 2)  # Has 'O'
        assert result.is_valid is False
        assert result.error_code == ERROR_CELL_OCCUPIED

    def test_empty_cell_on_partial_board(self, partial_board):
        """Test that empty cell on partially filled board is valid."""
        result = validate_occupancy(partial_board, 0, 1)  # Empty
        assert result.is_valid is True
        assert result.parsed_row == 0
        assert result.parsed_column == 1

    def test_all_cells_occupied(self, full_board):
        """Test that all cells on full board fail validation."""
        for row in range(3):
            for col in range(3):
                result = validate_occupancy(full_board, row, col)
                assert result.is_valid is False
                assert result.error_code == ERROR_CELL_OCCUPIED

    def test_error_message_includes_coordinates(self, partial_board):
        """Test that error message includes the coordinates."""
        result = validate_occupancy(partial_board, 1, 1)
        assert result.is_valid is False
        assert "(1, 1)" in result.error_message

    def test_corner_cells_empty(self, empty_board):
        """Test all corner cells when empty."""
        corners = [(0, 0), (0, 2), (2, 0), (2, 2)]
        for row, col in corners:
            result = validate_occupancy(empty_board, row, col)
            assert result.is_valid is True

    def test_corner_cells_occupied(self, partial_board):
        """Test corner cells when occupied."""
        # Top-left has X
        result = validate_occupancy(partial_board, 0, 0)
        assert result.is_valid is False

        # Top-right has O
        result = validate_occupancy(partial_board, 0, 2)
        assert result.is_valid is False

        # Bottom-left has O
        result = validate_occupancy(partial_board, 2, 0)
        assert result.is_valid is False

    def test_center_cell_occupied(self, partial_board):
        """Test center cell when occupied."""
        result = validate_occupancy(partial_board, 1, 1)
        assert result.is_valid is False
        assert result.error_code == ERROR_CELL_OCCUPIED

    def test_board_modification_does_not_affect_result(self, empty_board):
        """Test that modifying board after validation doesn't affect result."""
        result = validate_occupancy(empty_board, 0, 0)
        assert result.is_valid is True

        # Modify board
        empty_board[0][0] = "X"

        # Result should still be valid (it's a snapshot)
        assert result.is_valid is True

    def test_lowercase_x_is_occupied(self):
        """Test that lowercase 'x' is considered occupied."""
        board = [[" ", " ", " "], [" ", "x", " "], [" ", " ", " "]]
        result = validate_occupancy(board, 1, 1)
        assert result.is_valid is False

    def test_lowercase_o_is_occupied(self):
        """Test that lowercase 'o' is considered occupied."""
        board = [[" ", " ", " "], [" ", "o", " "], [" ", " ", " "]]
        result = validate_occupancy(board, 1, 1)
        assert result.is_valid is False

    def test_any_non_space_is_occupied(self):
        """Test that any non-space character is considered occupied."""
        non_space_chars = ["X", "O", "x", "o", ".", "#", "1", "-"]
        for char in non_space_chars:
            board = [[" ", " ", " "], [" ", char, " "], [" ", " ", " "]]
            result = validate_occupancy(board, 1, 1)
            assert result.is_valid is False, f"Failed for character: {char}"

    def test_space_is_empty(self):
        """Test that space character is considered empty."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        result = validate_occupancy(board, 1, 1)
        assert result.is_valid is True

    def test_multiple_spaces_is_occupied(self):
        """Test that multiple spaces are considered occupied."""
        board = [[" ", " ", " "], [" ", "  ", " "], [" ", " ", " "]]
        result = validate_occupancy(board, 1, 1)
        # Multiple spaces should be considered occupied
        assert result.is_valid is False

    def test_error_message_contains_hint(self, partial_board):
        """Test that error message contains helpful hint."""
        result = validate_occupancy(partial_board, 1, 1)
        assert result.is_valid is False
        # Check for hint in error message
        assert (
            "empty" in result.error_message.lower()
            or "choose" in result.error_message.lower()
        )
