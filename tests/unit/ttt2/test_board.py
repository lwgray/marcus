"""
Unit tests for the Display Board component.

This module tests the Board class, CellState enum, and utility functions
for the tic-tac-toe game board.
"""

import pytest

from src.ttt2.board import Board, CellState, coords_to_position, position_to_coords


class TestCellState:
    """Test suite for CellState enum."""

    def test_cell_state_values(self):
        """Test that CellState enum has correct values."""
        assert CellState.EMPTY.value == " "
        assert CellState.X.value == "X"
        assert CellState.O.value == "O"

    def test_cell_state_members(self):
        """Test that CellState has exactly three members."""
        assert len(CellState) == 3
        assert CellState.EMPTY in CellState
        assert CellState.X in CellState
        assert CellState.O in CellState


class TestUtilityFunctions:
    """Test suite for position conversion utility functions."""

    def test_position_to_coords_valid(self):
        """Test position_to_coords with valid positions 1-9."""
        # Top row
        assert position_to_coords(1) == (0, 0)
        assert position_to_coords(2) == (0, 1)
        assert position_to_coords(3) == (0, 2)
        # Middle row
        assert position_to_coords(4) == (1, 0)
        assert position_to_coords(5) == (1, 1)
        assert position_to_coords(6) == (1, 2)
        # Bottom row
        assert position_to_coords(7) == (2, 0)
        assert position_to_coords(8) == (2, 1)
        assert position_to_coords(9) == (2, 2)

    def test_position_to_coords_invalid_low(self):
        """Test position_to_coords raises ValueError for position < 1."""
        with pytest.raises(ValueError, match="Position must be between 1 and 9"):
            position_to_coords(0)
        with pytest.raises(ValueError, match="Position must be between 1 and 9"):
            position_to_coords(-1)

    def test_position_to_coords_invalid_high(self):
        """Test position_to_coords raises ValueError for position > 9."""
        with pytest.raises(ValueError, match="Position must be between 1 and 9"):
            position_to_coords(10)
        with pytest.raises(ValueError, match="Position must be between 1 and 9"):
            position_to_coords(100)

    def test_coords_to_position_valid(self):
        """Test coords_to_position with valid coordinates."""
        # Top row
        assert coords_to_position(0, 0) == 1
        assert coords_to_position(0, 1) == 2
        assert coords_to_position(0, 2) == 3
        # Middle row
        assert coords_to_position(1, 0) == 4
        assert coords_to_position(1, 1) == 5
        assert coords_to_position(1, 2) == 6
        # Bottom row
        assert coords_to_position(2, 0) == 7
        assert coords_to_position(2, 1) == 8
        assert coords_to_position(2, 2) == 9

    def test_coords_to_position_invalid_row(self):
        """Test coords_to_position raises ValueError for invalid row."""
        with pytest.raises(ValueError, match="Invalid coordinates"):
            coords_to_position(-1, 0)
        with pytest.raises(ValueError, match="Invalid coordinates"):
            coords_to_position(3, 0)

    def test_coords_to_position_invalid_col(self):
        """Test coords_to_position raises ValueError for invalid column."""
        with pytest.raises(ValueError, match="Invalid coordinates"):
            coords_to_position(0, -1)
        with pytest.raises(ValueError, match="Invalid coordinates"):
            coords_to_position(0, 3)

    def test_position_coords_round_trip(self):
        """Test that converting position to coords and back gives same position."""
        for position in range(1, 10):
            row, col = position_to_coords(position)
            result = coords_to_position(row, col)
            assert result == position


class TestBoardInitialization:
    """Test suite for Board initialization."""

    def test_board_initializes_empty(self):
        """Test that Board initializes with all cells empty."""
        board = Board()
        for row in range(3):
            for col in range(3):
                assert board.get_cell(row, col) == CellState.EMPTY

    def test_board_state_is_3x3(self):
        """Test that Board state is a 3x3 grid."""
        board = Board()
        state = board.get_state()
        assert len(state) == 3
        for row in state:
            assert len(row) == 3


class TestBoardCellAccess:
    """Test suite for Board cell access methods."""

    def test_get_cell_valid_coordinates(self):
        """Test get_cell with valid coordinates."""
        board = Board()
        # All cells should be empty initially
        for row in range(3):
            for col in range(3):
                cell = board.get_cell(row, col)
                assert cell == CellState.EMPTY

    def test_get_cell_invalid_row(self):
        """Test get_cell raises ValueError for invalid row."""
        board = Board()
        with pytest.raises(ValueError, match="Invalid coordinates"):
            board.get_cell(-1, 0)
        with pytest.raises(ValueError, match="Invalid coordinates"):
            board.get_cell(3, 0)

    def test_get_cell_invalid_col(self):
        """Test get_cell raises ValueError for invalid column."""
        board = Board()
        with pytest.raises(ValueError, match="Invalid coordinates"):
            board.get_cell(0, -1)
        with pytest.raises(ValueError, match="Invalid coordinates"):
            board.get_cell(0, 3)

    def test_set_cell_empty_to_x(self):
        """Test setting an empty cell to X."""
        board = Board()
        success = board.set_cell(0, 0, CellState.X)
        assert success is True
        assert board.get_cell(0, 0) == CellState.X

    def test_set_cell_empty_to_o(self):
        """Test setting an empty cell to O."""
        board = Board()
        success = board.set_cell(1, 1, CellState.O)
        assert success is True
        assert board.get_cell(1, 1) == CellState.O

    def test_set_cell_occupied_returns_false(self):
        """Test that setting an occupied cell returns False."""
        board = Board()
        board.set_cell(0, 0, CellState.X)
        # Try to overwrite with O
        success = board.set_cell(0, 0, CellState.O)
        assert success is False
        # Cell should still be X
        assert board.get_cell(0, 0) == CellState.X

    def test_set_cell_invalid_coordinates(self):
        """Test set_cell raises ValueError for invalid coordinates."""
        board = Board()
        with pytest.raises(ValueError, match="Invalid coordinates"):
            board.set_cell(-1, 0, CellState.X)
        with pytest.raises(ValueError, match="Invalid coordinates"):
            board.set_cell(0, 3, CellState.X)

    def test_is_cell_empty_true(self):
        """Test is_cell_empty returns True for empty cell."""
        board = Board()
        assert board.is_cell_empty(0, 0) is True

    def test_is_cell_empty_false(self):
        """Test is_cell_empty returns False for occupied cell."""
        board = Board()
        board.set_cell(0, 0, CellState.X)
        assert board.is_cell_empty(0, 0) is False

    def test_is_cell_empty_invalid_coordinates(self):
        """Test is_cell_empty raises ValueError for invalid coordinates."""
        board = Board()
        with pytest.raises(ValueError, match="Invalid coordinates"):
            board.is_cell_empty(-1, 0)


class TestBoardState:
    """Test suite for Board state management."""

    def test_get_state_returns_copy(self):
        """Test that get_state returns a copy, not the original."""
        board = Board()
        board.set_cell(0, 0, CellState.X)
        state = board.get_state()
        # Modify the copy
        state[0][0] = CellState.O
        # Original should be unchanged
        assert board.get_cell(0, 0) == CellState.X

    def test_is_full_empty_board(self):
        """Test is_full returns False for empty board."""
        board = Board()
        assert board.is_full() is False

    def test_is_full_partial_board(self):
        """Test is_full returns False for partially filled board."""
        board = Board()
        board.set_cell(0, 0, CellState.X)
        board.set_cell(1, 1, CellState.O)
        assert board.is_full() is False

    def test_is_full_complete_board(self):
        """Test is_full returns True when all cells are occupied."""
        board = Board()
        # Fill all cells
        positions = [
            (0, 0, CellState.X),
            (0, 1, CellState.O),
            (0, 2, CellState.X),
            (1, 0, CellState.O),
            (1, 1, CellState.X),
            (1, 2, CellState.O),
            (2, 0, CellState.X),
            (2, 1, CellState.O),
            (2, 2, CellState.X),
        ]
        for row, col, state in positions:
            board.set_cell(row, col, state)
        assert board.is_full() is True

    def test_reset_clears_board(self):
        """Test reset clears all cells."""
        board = Board()
        # Fill some cells
        board.set_cell(0, 0, CellState.X)
        board.set_cell(1, 1, CellState.O)
        board.set_cell(2, 2, CellState.X)
        # Reset
        board.reset()
        # All cells should be empty
        for row in range(3):
            for col in range(3):
                assert board.get_cell(row, col) == CellState.EMPTY


class TestBoardRendering:
    """Test suite for Board rendering functionality."""

    def test_render_empty_board(self):
        """Test rendering an empty board shows position numbers."""
        board = Board()
        rendered = board.render()
        # Should contain position numbers 1-9
        for i in range(1, 10):
            assert str(i) in rendered
        # Should contain box-drawing characters
        assert "│" in rendered or "|" in rendered
        assert "─" in rendered or "-" in rendered

    def test_render_with_x_move(self):
        """Test rendering board with X move."""
        board = Board()
        board.set_cell(0, 0, CellState.X)
        rendered = board.render()
        assert "X" in rendered
        # Position 1 should not appear (replaced by X)
        lines = rendered.split("\n")
        # First cell should have X, not 1
        assert " X " in lines[0]

    def test_render_with_multiple_moves(self):
        """Test rendering board with multiple moves."""
        board = Board()
        board.set_cell(0, 0, CellState.X)
        board.set_cell(1, 1, CellState.O)
        board.set_cell(0, 2, CellState.X)
        rendered = board.render()
        assert "X" in rendered
        assert "O" in rendered
        # Check specific positions are shown for empty cells
        assert "2" in rendered  # Position 2 should still be visible
        assert "4" in rendered  # Position 4 should still be visible

    def test_display_runs_without_error(self):
        """Test that display() method runs without error."""
        board = Board()
        # Should not raise any exception
        board.display()

    def test_render_structure(self):
        """Test that rendered board has correct structure."""
        board = Board()
        rendered = board.render()
        lines = rendered.split("\n")
        # Should have 5 lines (3 rows + 2 separators)
        assert len(lines) == 5
        # Lines 1, 3, 5 should be board rows
        # Lines 2, 4 should be separators


@pytest.mark.unit
class TestBoardEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_set_cell_with_type_error(self):
        """Test set_cell with invalid type raises TypeError."""
        board = Board()
        with pytest.raises(TypeError):
            board.set_cell(0, 0, "X")  # Should use CellState.X

    def test_multiple_moves_same_position(self):
        """Test multiple attempts to set the same position."""
        board = Board()
        # First move succeeds
        assert board.set_cell(0, 0, CellState.X) is True
        # Second move fails
        assert board.set_cell(0, 0, CellState.O) is False
        # Third move also fails
        assert board.set_cell(0, 0, CellState.X) is False
        # Cell should still have original value
        assert board.get_cell(0, 0) == CellState.X
