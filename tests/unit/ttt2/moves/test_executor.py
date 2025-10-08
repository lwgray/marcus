"""
Unit tests for move executor.

This module tests the create_move and execute_move functions.
"""

from datetime import datetime

import pytest

from src.ttt2.moves.executor import create_move, execute_move
from src.ttt2.moves.models import MoveInput


@pytest.mark.unit
class TestCreateMove:
    """Test suite for create_move function."""

    def test_create_valid_move_x(self):
        """Test creating a valid move for player X."""
        move = create_move(1, 2, "X")
        assert isinstance(move, MoveInput)
        assert move.row == 1
        assert move.column == 2
        assert move.player == "X"
        assert isinstance(move.timestamp, str)

    def test_create_valid_move_o(self):
        """Test creating a valid move for player O."""
        move = create_move(0, 0, "O")
        assert isinstance(move, MoveInput)
        assert move.row == 0
        assert move.column == 0
        assert move.player == "O"

    def test_create_move_all_positions(self):
        """Test creating moves at all valid positions."""
        for row in range(3):
            for col in range(3):
                move = create_move(row, col, "X")
                assert move.row == row
                assert move.column == col

    def test_create_move_has_timestamp(self):
        """Test that created move has a timestamp."""
        before = datetime.now()
        move = create_move(1, 1, "X")
        after = datetime.now()

        timestamp = datetime.fromisoformat(move.timestamp)
        assert before <= timestamp <= after

    def test_create_move_invalid_row_raises_error(self):
        """Test that invalid row raises ValueError."""
        with pytest.raises(ValueError, match="Row must be 0-2"):
            create_move(3, 2, "X")

    def test_create_move_invalid_col_raises_error(self):
        """Test that invalid column raises ValueError."""
        with pytest.raises(ValueError, match="Column must be 0-2"):
            create_move(1, 5, "X")

    def test_create_move_invalid_player_raises_error(self):
        """Test that invalid player raises ValueError."""
        with pytest.raises(ValueError, match="Player must be"):
            create_move(1, 2, "Z")

    def test_create_move_corner_positions(self):
        """Test creating moves at corner positions."""
        corners = [(0, 0), (0, 2), (2, 0), (2, 2)]
        for row, col in corners:
            move = create_move(row, col, "X")
            assert move.row == row
            assert move.column == col

    def test_create_move_center(self):
        """Test creating move at center position."""
        move = create_move(1, 1, "O")
        assert move.row == 1
        assert move.column == 1


@pytest.mark.unit
class TestExecuteMove:
    """Test suite for execute_move function."""

    @pytest.fixture
    def empty_board(self):
        """Provide empty board."""
        return [[" " for _ in range(3)] for _ in range(3)]

    @pytest.fixture
    def partial_board(self):
        """Provide board with some moves."""
        return [["X", " ", "O"], [" ", "X", " "], ["O", " ", " "]]

    def test_execute_move_updates_board(self, empty_board):
        """Test that executing move updates board correctly."""
        move = MoveInput(row=1, column=2, player="X")
        new_board = execute_move(empty_board, move)

        assert new_board[1][2] == "X"
        # Original board should be unchanged
        assert empty_board[1][2] == " "

    def test_execute_move_player_o(self, empty_board):
        """Test executing move for player O."""
        move = MoveInput(row=0, column=0, player="O")
        new_board = execute_move(empty_board, move)

        assert new_board[0][0] == "O"
        assert empty_board[0][0] == " "

    def test_execute_move_immutability(self, empty_board):
        """Test that execute_move doesn't modify original board."""
        original_copy = [row[:] for row in empty_board]
        move = MoveInput(row=1, column=1, player="X")

        new_board = execute_move(empty_board, move)

        # Original should be unchanged
        assert empty_board == original_copy
        # New board should have the move
        assert new_board[1][1] == "X"

    def test_execute_move_all_positions(self, empty_board):
        """Test executing moves at all positions."""
        for row in range(3):
            for col in range(3):
                fresh_board = [[" " for _ in range(3)] for _ in range(3)]
                move = MoveInput(row=row, column=col, player="X")
                new_board = execute_move(fresh_board, move)
                assert new_board[row][col] == "X"

    def test_execute_move_on_occupied_raises_error(self, partial_board):
        """Test that executing move on occupied cell raises error."""
        move = MoveInput(row=1, column=1, player="O")  # Position has 'X'

        with pytest.raises(ValueError, match="occupied"):
            execute_move(partial_board, move)

    def test_execute_move_occupied_by_x(self, partial_board):
        """Test error when trying to overwrite X."""
        move = MoveInput(row=0, column=0, player="O")  # Has 'X'

        with pytest.raises(ValueError, match="Position \\(0, 0\\) is already occupied"):
            execute_move(partial_board, move)

    def test_execute_move_occupied_by_o(self, partial_board):
        """Test error when trying to overwrite O."""
        move = MoveInput(row=0, column=2, player="X")  # Has 'O'

        with pytest.raises(ValueError, match="occupied"):
            execute_move(partial_board, move)

    def test_execute_multiple_moves_sequentially(self, empty_board):
        """Test executing multiple moves in sequence."""
        move1 = MoveInput(row=0, column=0, player="X")
        board1 = execute_move(empty_board, move1)

        move2 = MoveInput(row=1, column=1, player="O")
        board2 = execute_move(board1, move2)

        move3 = MoveInput(row=2, column=2, player="X")
        board3 = execute_move(board2, move3)

        # Check all moves are present
        assert board3[0][0] == "X"
        assert board3[1][1] == "O"
        assert board3[2][2] == "X"

        # Original board unchanged
        assert empty_board[0][0] == " "
        assert empty_board[1][1] == " "
        assert empty_board[2][2] == " "

    def test_execute_move_corner_positions(self, empty_board):
        """Test executing moves at all corners."""
        corners = [
            (0, 0, "X"),
            (0, 2, "O"),
            (2, 0, "X"),
            (2, 2, "O"),
        ]

        current_board = empty_board
        for row, col, player in corners:
            move = MoveInput(row=row, column=col, player=player)
            current_board = execute_move(current_board, move)
            assert current_board[row][col] == player

    def test_execute_move_preserves_other_cells(self, partial_board):
        """Test that executing move doesn't affect other cells."""
        move = MoveInput(row=0, column=1, player="X")  # Empty cell
        new_board = execute_move(partial_board, move)

        # New cell should have move
        assert new_board[0][1] == "X"

        # Other cells should be unchanged
        assert new_board[0][0] == "X"
        assert new_board[0][2] == "O"
        assert new_board[1][1] == "X"
        assert new_board[2][0] == "O"

    def test_execute_move_returns_new_list(self, empty_board):
        """Test that execute_move returns a new list object."""
        move = MoveInput(row=0, column=0, player="X")
        new_board = execute_move(empty_board, move)

        # Should be different objects
        assert new_board is not empty_board
        assert new_board[0] is not empty_board[0]

    def test_execute_move_deep_copy(self, empty_board):
        """Test that board is deeply copied."""
        move = MoveInput(row=1, column=1, player="X")
        new_board = execute_move(empty_board, move)

        # Modify new board's row
        new_board[0][0] = "O"

        # Original should be unaffected
        assert empty_board[0][0] == " "

    def test_execute_move_with_lowercase_occupied(self):
        """Test error when cell has lowercase marker."""
        board = [[" ", " ", " "], [" ", "x", " "], [" ", " ", " "]]
        move = MoveInput(row=1, column=1, player="O")

        with pytest.raises(ValueError, match="occupied"):
            execute_move(board, move)

    def test_execute_move_alternating_players(self, empty_board):
        """Test alternating X and O moves."""
        board = empty_board
        players = ["X", "O", "X", "O", "X"]
        positions = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)]

        for (row, col), player in zip(positions, players):
            move = MoveInput(row=row, column=col, player=player)
            board = execute_move(board, move)
            assert board[row][col] == player

    def test_execute_move_center_then_corners(self, empty_board):
        """Test specific game sequence."""
        # X takes center
        move1 = MoveInput(row=1, column=1, player="X")
        board = execute_move(empty_board, move1)

        # O takes corner
        move2 = MoveInput(row=0, column=0, player="O")
        board = execute_move(board, move2)

        # X takes opposite corner
        move3 = MoveInput(row=2, column=2, player="X")
        board = execute_move(board, move3)

        assert board[1][1] == "X"
        assert board[0][0] == "O"
        assert board[2][2] == "X"
