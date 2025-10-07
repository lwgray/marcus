"""
Unit tests for validation pipeline.

This test module verifies the complete validation pipeline
that orchestrates parsing and all validation stages.
"""

import pytest

from src.ttt2.validation.pipeline import validate_complete_move


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

    def test_invalid_format_fails(self, empty_board):
        """Test that invalid format fails validation."""
        result = validate_complete_move(empty_board, "a b")
        assert result.is_valid is False

    def test_out_of_range_fails(self, empty_board):
        """Test that out of range coordinates fail."""
        result = validate_complete_move(empty_board, "3 2")
        assert result.is_valid is False

    def test_occupied_cell_fails(self, board_with_moves):
        """Test that occupied cell fails validation."""
        result = validate_complete_move(board_with_moves, "1 1")
        assert result.is_valid is False
