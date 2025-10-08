"""
Unit tests for move executor.

This test module verifies the move creation and execution functions
that apply validated moves to the game board.
"""

import pytest

from src.ttt2.moves.executor import create_move, execute_move
from src.ttt2.moves.models import MoveInput


class TestCreateMove:
    """Test suite for create_move function."""

    def test_create_valid_move(self):
        """Test creating a valid move."""
        move = create_move(1, 2, "X")
        assert isinstance(move, MoveInput)
        assert move.row == 1
        assert move.column == 2
        assert move.player == "X"


class TestExecuteMove:
    """Test suite for execute_move function."""

    @pytest.fixture
    def empty_board(self):
        """Provide empty board."""
        return [[" " for _ in range(3)] for _ in range(3)]

    def test_execute_move_updates_board(self, empty_board):
        """Test that executing move updates board correctly."""
        move = MoveInput(row=1, column=2, player="X")
        new_board = execute_move(empty_board, move)

        assert new_board[1][2] == "X"
        assert empty_board[1][2] == " "  # Original unchanged

    def test_execute_move_on_occupied_raises_error(self, empty_board):
        """Test that executing move on occupied cell raises error."""
        empty_board[1][1] = "O"
        move = MoveInput(row=1, column=1, player="X")

        with pytest.raises(ValueError, match="occupied"):
            execute_move(empty_board, move)
