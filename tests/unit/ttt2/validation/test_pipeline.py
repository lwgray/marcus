"""
Unit tests for validation pipeline.

This module tests the validate_complete_move function which
orchestrates the full validation workflow.
"""

import pytest

from src.ttt2.validation.pipeline import validate_complete_move
from src.ttt2.validation.results import (
    ERROR_CELL_OCCUPIED,
    ERROR_OUT_OF_RANGE,
)


@pytest.mark.unit
class TestValidateCompleteMove:
    """Test suite for validate_complete_move function."""

    @pytest.fixture
    def empty_board(self):
        """Provide empty board."""
        return [[" " for _ in range(3)] for _ in range(3)]

    @pytest.fixture
    def board_with_moves(self):
        """Provide board with some moves."""
        return [["X", " ", "O"], [" ", "X", " "], ["O", " ", " "]]

    def test_valid_move_passes(self, empty_board):
        """Test that valid move passes all validation."""
        result = validate_complete_move(empty_board, "1 2")
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 2
        assert result.error_message is None
        assert result.error_code is None

    def test_valid_move_comma_separated(self, empty_board):
        """Test valid move with comma separator."""
        result = validate_complete_move(empty_board, "0,1")
        assert result.is_valid is True
        assert result.parsed_row == 0
        assert result.parsed_column == 1

    def test_valid_move_all_positions(self, empty_board):
        """Test valid moves for all board positions."""
        for row in range(3):
            for col in range(3):
                result = validate_complete_move(empty_board, f"{row} {col}")
                assert result.is_valid is True
                assert result.parsed_row == row
                assert result.parsed_column == col

    def test_invalid_format_fails(self, empty_board):
        """Test that invalid format fails validation."""
        result = validate_complete_move(empty_board, "a b")
        assert result.is_valid is False
        assert result.error_code == "INVALID_FORMAT"

    def test_empty_input_fails(self, empty_board):
        """Test that empty input fails validation."""
        result = validate_complete_move(empty_board, "")
        assert result.is_valid is False
        assert result.error_code == "INVALID_FORMAT"

    def test_single_number_fails(self, empty_board):
        """Test that single number fails validation."""
        result = validate_complete_move(empty_board, "1")
        assert result.is_valid is False
        assert result.error_code == "INVALID_FORMAT"

    def test_three_numbers_fails(self, empty_board):
        """Test that three numbers fail validation."""
        result = validate_complete_move(empty_board, "1 2 3")
        assert result.is_valid is False
        assert result.error_code == "INVALID_FORMAT"

    def test_out_of_range_fails(self, empty_board):
        """Test that out of range coordinates fail."""
        result = validate_complete_move(empty_board, "3 2")
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE

    def test_negative_coordinates_fail(self, empty_board):
        """Test that negative coordinates fail."""
        result = validate_complete_move(empty_board, "-1 0")
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE

    def test_occupied_cell_fails(self, board_with_moves):
        """Test that occupied cell fails validation."""
        result = validate_complete_move(board_with_moves, "1 1")
        assert result.is_valid is False
        assert result.error_code == ERROR_CELL_OCCUPIED

    def test_occupied_by_x_fails(self, board_with_moves):
        """Test cell occupied by X fails."""
        result = validate_complete_move(board_with_moves, "0 0")
        assert result.is_valid is False
        assert result.error_code == ERROR_CELL_OCCUPIED

    def test_occupied_by_o_fails(self, board_with_moves):
        """Test cell occupied by O fails."""
        result = validate_complete_move(board_with_moves, "0 2")
        assert result.is_valid is False
        assert result.error_code == ERROR_CELL_OCCUPIED

    def test_valid_empty_cell_on_partial_board(self, board_with_moves):
        """Test valid empty cell on partially filled board."""
        result = validate_complete_move(board_with_moves, "0 1")
        assert result.is_valid is True
        assert result.parsed_row == 0
        assert result.parsed_column == 1

    def test_whitespace_trimmed(self, empty_board):
        """Test that whitespace is properly trimmed."""
        result = validate_complete_move(empty_board, "  1  2  ")
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 2

    def test_validation_order_format_first(self, empty_board):
        """Test that format validation happens before range."""
        # Invalid format should be caught before range check
        result = validate_complete_move(empty_board, "abc")
        assert result.is_valid is False
        assert result.error_code == "INVALID_FORMAT"

    def test_validation_order_range_before_occupancy(self, board_with_moves):
        """Test that range validation happens before occupancy."""
        # Out of range should be caught before occupancy check
        result = validate_complete_move(board_with_moves, "5 5")
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE

    def test_float_input_fails(self, empty_board):
        """Test that float input fails format validation."""
        result = validate_complete_move(empty_board, "1.5 2.5")
        assert result.is_valid is False
        assert result.error_code == "INVALID_FORMAT"

    def test_mixed_valid_invalid(self, empty_board):
        """Test mixed valid number and invalid input."""
        result = validate_complete_move(empty_board, "1 abc")
        assert result.is_valid is False
        assert result.error_code == "INVALID_FORMAT"

    def test_special_characters_fail(self, empty_board):
        """Test that special characters fail validation."""
        result = validate_complete_move(empty_board, "! @")
        assert result.is_valid is False

    def test_all_empty_cells_valid(self, empty_board):
        """Test all cells on empty board are valid."""
        for row in range(3):
            for col in range(3):
                result = validate_complete_move(empty_board, f"{row},{col}")
                assert result.is_valid is True

    def test_sequential_validations(self, empty_board):
        """Test multiple validations in sequence."""
        # First validation
        result1 = validate_complete_move(empty_board, "0 0")
        assert result1.is_valid is True

        # Simulate move
        empty_board[0][0] = "X"

        # Second validation on same position should fail
        result2 = validate_complete_move(empty_board, "0 0")
        assert result2.is_valid is False
        assert result2.error_code == ERROR_CELL_OCCUPIED

    def test_corner_positions(self, empty_board):
        """Test validation for all corner positions."""
        corners = ["0 0", "0 2", "2 0", "2 2"]
        for corner in corners:
            result = validate_complete_move(empty_board, corner)
            assert result.is_valid is True

    def test_center_position(self, empty_board):
        """Test validation for center position."""
        result = validate_complete_move(empty_board, "1 1")
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 1

    def test_edge_positions(self, empty_board):
        """Test validation for edge positions."""
        edges = ["0 1", "1 0", "1 2", "2 1"]
        for edge in edges:
            result = validate_complete_move(empty_board, edge)
            assert result.is_valid is True

    def test_board_full_all_invalid(self):
        """Test that all positions on full board are invalid."""
        full_board = [["X", "O", "X"], ["O", "X", "O"], ["X", "O", "X"]]
        for row in range(3):
            for col in range(3):
                result = validate_complete_move(full_board, f"{row} {col}")
                assert result.is_valid is False
                assert result.error_code == ERROR_CELL_OCCUPIED

    def test_leading_zeros(self, empty_board):
        """Test that leading zeros are handled correctly."""
        result = validate_complete_move(empty_board, "01 02")
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 2

    def test_plus_sign_numbers(self, empty_board):
        """Test that plus signs are handled correctly."""
        result = validate_complete_move(empty_board, "+1 +2")
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 2

    def test_tab_separator(self, empty_board):
        """Test that tab separator works."""
        result = validate_complete_move(empty_board, "1\t2")
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 2

    def test_multiple_spaces(self, empty_board):
        """Test that multiple spaces between numbers work."""
        result = validate_complete_move(empty_board, "1     2")
        assert result.is_valid is True

    def test_comma_with_spaces(self, empty_board):
        """Test comma separator with spaces."""
        result = validate_complete_move(empty_board, "1 , 2")
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 2
