"""
Unit tests for Grid data model.

This module tests the Grid class representing the 3x3 tic-tac-toe board.
"""

import pytest

from src.models.grid import Grid


class TestGridCreation:
    """Test suite for Grid creation and initialization."""

    def test_create_empty_grid(self):
        """Test creating an empty 3x3 grid."""
        # Arrange & Act
        grid = Grid()

        # Assert
        assert grid.board is not None
        assert len(grid.board) == 3
        assert all(len(row) == 3 for row in grid.board)
        assert all(cell is None for row in grid.board for cell in row)

    def test_create_grid_with_initial_state(self):
        """Test creating a grid with initial board state."""
        # Arrange
        initial_board = [["X", None, "O"], [None, "X", None], ["O", None, None]]

        # Act
        grid = Grid(board=initial_board)

        # Assert
        assert grid.board == initial_board
        assert grid.board[0][0] == "X"
        assert grid.board[0][2] == "O"
        assert grid.board[1][1] == "X"


class TestGridValidation:
    """Test suite for Grid validation."""

    def test_invalid_board_size_rows(self):
        """Test that grid rejects invalid number of rows."""
        # Arrange
        invalid_board = [["X", None, "O"], [None, "X", None]]

        # Act & Assert
        with pytest.raises(ValueError, match="Board must have 3 rows"):
            Grid(board=invalid_board)

    def test_invalid_board_size_columns(self):
        """Test that grid rejects invalid number of columns."""
        # Arrange
        invalid_board = [["X", None], [None, "X", None], ["O", None, None]]

        # Act & Assert
        with pytest.raises(ValueError, match="Row .* must have 3 columns"):
            Grid(board=invalid_board)

    def test_invalid_cell_value(self):
        """Test that grid rejects invalid cell values."""
        # Arrange
        invalid_board = [["X", None, "O"], [None, "Y", None], ["O", None, None]]

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid cell value"):
            Grid(board=invalid_board)


class TestGridProperties:
    """Test suite for Grid properties."""

    def test_is_empty_on_new_grid(self):
        """Test that new grid is empty."""
        # Arrange & Act
        grid = Grid()

        # Assert
        assert grid.is_empty() is True

    def test_is_full_on_complete_grid(self):
        """Test that completed grid is full."""
        # Arrange
        full_board = [["X", "O", "X"], ["O", "X", "O"], ["X", "O", "X"]]

        # Act
        grid = Grid(board=full_board)

        # Assert
        assert grid.is_full() is True

    def test_get_cell_value(self):
        """Test getting cell value at position."""
        # Arrange
        board = [["X", None, "O"], [None, "X", None], ["O", None, None]]
        grid = Grid(board=board)

        # Act & Assert
        assert grid.get_cell(0, 0) == "X"
        assert grid.get_cell(0, 1) is None
        assert grid.get_cell(0, 2) == "O"
        assert grid.get_cell(1, 1) == "X"

    def test_get_empty_positions(self):
        """Test getting list of empty positions."""
        # Arrange
        board = [["X", None, "O"], [None, "X", None], ["O", None, None]]
        grid = Grid(board=board)

        # Act
        empty_positions = grid.get_empty_positions()

        # Assert
        assert len(empty_positions) == 5
        assert (0, 1) in empty_positions
        assert (1, 0) in empty_positions
        assert (1, 2) in empty_positions
        assert (2, 1) in empty_positions
        assert (2, 2) in empty_positions
