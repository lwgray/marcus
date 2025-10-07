"""
Unit tests for MoveInput model.

This test module verifies the MoveInput dataclass used for
representing validated player moves.
"""

import pytest

from src.ttt2.moves.models import MoveInput


class TestMoveInput:
    """Test suite for MoveInput dataclass."""

    def test_valid_move_creation(self):
        """Test creating valid MoveInput."""
        move = MoveInput(row=1, column=2, player="X")

        assert move.row == 1
        assert move.column == 2
        assert move.player == "X"
        assert isinstance(move.timestamp, str)

    def test_invalid_row_raises_error(self):
        """Test that invalid row raises ValueError."""
        with pytest.raises(ValueError, match="Row must be 0-2"):
            MoveInput(row=3, column=2, player="X")

    def test_invalid_column_raises_error(self):
        """Test that invalid column raises ValueError."""
        with pytest.raises(ValueError, match="Column must be 0-2"):
            MoveInput(row=1, column=5, player="X")

    def test_invalid_player_raises_error(self):
        """Test that invalid player raises ValueError."""
        with pytest.raises(ValueError, match="Player must be"):
            MoveInput(row=1, column=2, player="Z")
