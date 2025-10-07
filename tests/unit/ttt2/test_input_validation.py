"""
Unit tests for Input Validation component.

This module tests the complete input validation pipeline for the
tic-tac-toe game, including parsing, range validation, and occupancy checks.
"""

import pytest

from src.ttt2.board import Board, CellState
from src.ttt2.input.parser import parse_player_input
from src.ttt2.validation.pipeline import validate_complete_move
from src.ttt2.validation.results import (
    ERROR_CELL_OCCUPIED,
    ERROR_EMPTY_INPUT,
    ERROR_INVALID_FORMAT,
    ERROR_OUT_OF_RANGE,
    ValidationResult,
)
from src.ttt2.validation.validators import validate_occupancy, validate_range


@pytest.mark.unit
class TestInputParser:
    """Test suite for input parsing functionality."""

    def test_parse_space_separated_input(self):
        """Test parsing space-separated coordinates."""
        row, col = parse_player_input("1 2")
        assert row == 1
        assert col == 2

    def test_parse_comma_separated_input(self):
        """Test parsing comma-separated coordinates."""
        row, col = parse_player_input("0,2")
        assert row == 0
        assert col == 2

    def test_parse_with_extra_whitespace(self):
        """Test parsing handles extra whitespace correctly."""
        row, col = parse_player_input("  1   2  ")
        assert row == 1
        assert col == 2

    def test_parse_comma_with_spaces(self):
        """Test parsing comma-separated input with spaces."""
        row, col = parse_player_input("1, 2")
        assert row == 1
        assert col == 2

    def test_parse_empty_string_raises_error(self):
        """Test parsing empty string raises ValueError."""
        with pytest.raises(ValueError, match="Input cannot be empty"):
            parse_player_input("")

    def test_parse_whitespace_only_raises_error(self):
        """Test parsing whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="Input cannot be empty"):
            parse_player_input("   ")

    def test_parse_single_number_raises_error(self):
        """Test parsing single number raises ValueError."""
        with pytest.raises(ValueError, match="exactly 2 numbers"):
            parse_player_input("1")

    def test_parse_three_numbers_raises_error(self):
        """Test parsing three numbers raises ValueError."""
        with pytest.raises(ValueError, match="exactly 2 numbers"):
            parse_player_input("1 2 3")

    def test_parse_non_numeric_raises_error(self):
        """Test parsing non-numeric input raises ValueError."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_player_input("a b")

    def test_parse_mixed_alpha_numeric_raises_error(self):
        """Test parsing mixed alphanumeric input raises ValueError."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_player_input("1 x")

    def test_parse_non_string_raises_type_error(self):
        """Test parsing non-string input raises TypeError."""
        with pytest.raises(TypeError, match="Input must be string"):
            parse_player_input(123)


@pytest.mark.unit
class TestRangeValidation:
    """Test suite for coordinate range validation."""

    def test_validate_range_valid_coordinates(self):
        """Test range validation accepts valid coordinates."""
        # All corners
        assert validate_range(0, 0).is_valid is True
        assert validate_range(0, 2).is_valid is True
        assert validate_range(2, 0).is_valid is True
        assert validate_range(2, 2).is_valid is True
        # Center
        assert validate_range(1, 1).is_valid is True

    def test_validate_range_returns_coordinates(self):
        """Test range validation returns parsed coordinates."""
        result = validate_range(1, 2)
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 2

    def test_validate_range_row_too_low(self):
        """Test range validation rejects row < 0."""
        result = validate_range(-1, 1)
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE
        assert "(-1, 1)" in result.error_message

    def test_validate_range_row_too_high(self):
        """Test range validation rejects row > 2."""
        result = validate_range(3, 1)
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE
        assert "(3, 1)" in result.error_message

    def test_validate_range_col_too_low(self):
        """Test range validation rejects column < 0."""
        result = validate_range(1, -1)
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE

    def test_validate_range_col_too_high(self):
        """Test range validation rejects column > 2."""
        result = validate_range(1, 3)
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE

    def test_validate_range_both_invalid(self):
        """Test range validation when both coordinates are invalid."""
        result = validate_range(-1, 3)
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE


@pytest.mark.unit
class TestOccupancyValidation:
    """Test suite for cell occupancy validation."""

    def test_validate_occupancy_empty_cell(self):
        """Test occupancy validation accepts empty cell."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        result = validate_occupancy(board, 1, 1)
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 1

    def test_validate_occupancy_occupied_by_x(self):
        """Test occupancy validation rejects cell occupied by X."""
        board = [[" ", " ", " "], [" ", "X", " "], [" ", " ", " "]]
        result = validate_occupancy(board, 1, 1)
        assert result.is_valid is False
        assert result.error_code == ERROR_CELL_OCCUPIED
        assert "already occupied" in result.error_message

    def test_validate_occupancy_occupied_by_o(self):
        """Test occupancy validation rejects cell occupied by O."""
        board = [[" ", " ", " "], [" ", "O", " "], [" ", " ", " "]]
        result = validate_occupancy(board, 1, 1)
        assert result.is_valid is False
        assert result.error_code == ERROR_CELL_OCCUPIED

    def test_validate_occupancy_all_positions(self):
        """Test occupancy validation for all board positions."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        for row in range(3):
            for col in range(3):
                result = validate_occupancy(board, row, col)
                assert result.is_valid is True


@pytest.mark.unit
class TestValidationResult:
    """Test suite for ValidationResult data structure."""

    def test_validation_result_valid_state(self):
        """Test ValidationResult for valid input."""
        result = ValidationResult(is_valid=True, parsed_row=1, parsed_column=2)
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 2
        assert result.error_message is None
        assert result.error_code is None

    def test_validation_result_invalid_state(self):
        """Test ValidationResult for invalid input."""
        result = ValidationResult(
            is_valid=False,
            error_message="Test error",
            error_code=ERROR_OUT_OF_RANGE,
        )
        assert result.is_valid is False
        assert result.error_message == "Test error"
        assert result.error_code == ERROR_OUT_OF_RANGE
        assert result.parsed_row is None
        assert result.parsed_column is None


@pytest.mark.unit
class TestValidationPipeline:
    """Test suite for complete validation pipeline."""

    def test_pipeline_valid_input_empty_board(self):
        """Test complete pipeline with valid input on empty board."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        result = validate_complete_move(board, "1 2")
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 2

    def test_pipeline_rejects_empty_input(self):
        """Test pipeline rejects empty input."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        result = validate_complete_move(board, "")
        assert result.is_valid is False
        assert result.error_code == "INVALID_FORMAT"

    def test_pipeline_rejects_invalid_format(self):
        """Test pipeline rejects non-numeric input."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        result = validate_complete_move(board, "abc")
        assert result.is_valid is False
        assert result.error_code == "INVALID_FORMAT"

    def test_pipeline_rejects_out_of_range(self):
        """Test pipeline rejects out-of-range coordinates."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        result = validate_complete_move(board, "3 2")
        assert result.is_valid is False
        assert result.error_code == ERROR_OUT_OF_RANGE

    def test_pipeline_rejects_occupied_cell(self):
        """Test pipeline rejects occupied cell."""
        board = [[" ", " ", " "], [" ", "X", " "], [" ", " ", " "]]
        result = validate_complete_move(board, "1 1")
        assert result.is_valid is False
        assert result.error_code == ERROR_CELL_OCCUPIED

    def test_pipeline_validates_all_stages(self):
        """Test pipeline runs all validation stages in order."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]

        # Valid input passes all stages
        result = validate_complete_move(board, "0 0")
        assert result.is_valid is True

        # Invalid format fails at stage 1 (parsing)
        result = validate_complete_move(board, "invalid")
        assert result.error_code == "INVALID_FORMAT"

        # Out of range fails at stage 2 (range)
        result = validate_complete_move(board, "5 5")
        assert result.error_code == ERROR_OUT_OF_RANGE

        # Occupied cell fails at stage 3 (occupancy)
        board[1][1] = "X"
        result = validate_complete_move(board, "1 1")
        assert result.error_code == ERROR_CELL_OCCUPIED


@pytest.mark.unit
class TestInputValidationIntegration:
    """Integration tests for input validation with Board class."""

    def test_validation_with_board_class(self):
        """Test validation integrates correctly with Board class."""
        board = Board()
        # Convert Board to list format for validation
        board_list = [[cell.value for cell in row] for row in board.get_state()]

        # Valid empty cell
        result = validate_complete_move(board_list, "0 0")
        assert result.is_valid is True

        # Set cell and verify validation detects occupancy
        board.set_cell(0, 0, CellState.X)
        board_list = [[cell.value for cell in row] for row in board.get_state()]
        result = validate_complete_move(board_list, "0 0")
        assert result.is_valid is False
        assert result.error_code == ERROR_CELL_OCCUPIED

    def test_validation_edge_cases(self):
        """Test validation handles edge cases correctly."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]

        # Boundary coordinates
        assert validate_complete_move(board, "0 0").is_valid is True
        assert validate_complete_move(board, "2 2").is_valid is True

        # Just outside boundaries
        assert validate_complete_move(board, "-1 0").is_valid is False
        assert validate_complete_move(board, "0 3").is_valid is False

    def test_validation_error_messages_are_descriptive(self):
        """Test validation error messages are user-friendly."""
        board = [[" ", " ", " "], [" ", "X", " "], [" ", " ", " "]]

        # Out of range
        result = validate_complete_move(board, "5 5")
        assert result.is_valid is False
        assert "between 0 and 2" in result.error_message

        # Occupied
        result = validate_complete_move(board, "1 1")
        assert result.is_valid is False
        assert "already occupied" in result.error_message

        # Invalid format
        result = validate_complete_move(board, "not-numbers")
        assert result.is_valid is False


@pytest.mark.unit
class TestValidationPerformance:
    """Test suite for validation performance requirements."""

    def test_validation_completes_quickly(self):
        """Test validation meets <1ms performance target."""
        import time

        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]

        # Warm up
        for _ in range(10):
            validate_complete_move(board, "1 1")

        # Time 100 validations
        start = time.perf_counter()
        for _ in range(100):
            validate_complete_move(board, "1 1")
        end = time.perf_counter()

        avg_time_ms = ((end - start) / 100) * 1000
        assert avg_time_ms < 1.0, f"Validation took {avg_time_ms:.3f}ms, target is <1ms"
