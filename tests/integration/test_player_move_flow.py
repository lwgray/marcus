"""
Integration tests for complete player move flow.

This test module verifies the end-to-end player move workflow
from input to validation to board update.
"""

from unittest.mock import patch

import pytest

from src.ttt2.game.controller import get_player_move


class TestGetPlayerMove:
    """Integration tests for get_player_move."""

    @pytest.fixture
    def empty_board(self):
        """Provide empty board."""
        return [[" " for _ in range(3)] for _ in range(3)]

    def test_valid_input_on_first_try(self, empty_board):
        """Test successful move on first attempt."""
        with patch("builtins.input", return_value="1 2"):
            row, col = get_player_move(empty_board, "X")
            assert (row, col) == (1, 2)

    def test_retry_after_invalid_format(self, empty_board):
        """Test retry after invalid format."""
        with patch("builtins.input", side_effect=["a b", "1 2"]):
            row, col = get_player_move(empty_board, "X")
            assert (row, col) == (1, 2)

    def test_retry_after_occupied_cell(self, empty_board):
        """Test retry after attempting occupied cell."""
        empty_board[1][1] = "X"
        with patch("builtins.input", side_effect=["1 1", "0 0"]):
            row, col = get_player_move(empty_board, "O")
            assert (row, col) == (0, 0)

    def test_max_retries_exceeded(self, empty_board):
        """Test that max_retries raises ValueError when exceeded."""
        with patch("builtins.input", side_effect=["a b", "c d", "e f"]):
            with pytest.raises(ValueError, match="Maximum retries"):
                get_player_move(empty_board, "X", max_retries=2)
