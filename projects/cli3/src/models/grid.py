"""
Grid data model for tic-tac-toe game.

This module defines the Grid class representing the 3x3 game board.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Grid:
    """
    Immutable representation of a 3x3 tic-tac-toe grid.

    Attributes
    ----------
    board : List[List[Optional[str]]]
        3x3 grid representing the game board.
        None = empty cell, 'X' or 'O' = player marker

    Raises
    ------
    ValueError
        If validation fails in __post_init__
    """

    board: List[List[Optional[str]]] = field(
        default_factory=lambda: [[None, None, None] for _ in range(3)]
    )

    def __post_init__(self) -> None:
        """Validate grid structure."""
        # Validate board structure
        if len(self.board) != 3:
            raise ValueError(f"Board must have 3 rows, got {len(self.board)}")

        for i, row in enumerate(self.board):
            if len(row) != 3:
                raise ValueError(f"Row {i} must have 3 columns, got {len(row)}")

            for j, cell in enumerate(row):
                if cell not in (None, "X", "O"):
                    raise ValueError(f"Invalid cell value at ({i},{j}): {cell}")

    def get_cell(self, row: int, col: int) -> Optional[str]:
        """
        Get the value at a specific cell.

        Parameters
        ----------
        row : int
            Row index (0-2)
        col : int
            Column index (0-2)

        Returns
        -------
        Optional[str]
            Cell value: None, 'X', or 'O'

        Raises
        ------
        IndexError
            If row or col is out of bounds
        """
        if not (0 <= row < 3 and 0 <= col < 3):
            raise IndexError(f"Position ({row}, {col}) is out of bounds")
        return self.board[row][col]

    def is_empty(self) -> bool:
        """
        Check if the grid is completely empty.

        Returns
        -------
        bool
            True if all cells are None
        """
        return all(cell is None for row in self.board for cell in row)

    def is_full(self) -> bool:
        """
        Check if the grid is completely full.

        Returns
        -------
        bool
            True if no cells are None
        """
        return all(cell is not None for row in self.board for cell in row)

    def get_empty_positions(self) -> List[Tuple[int, int]]:
        """
        Get list of all empty cell positions.

        Returns
        -------
        List[Tuple[int, int]]
            List of (row, col) tuples for empty cells
        """
        empty_positions = []
        for row_idx, row in enumerate(self.board):
            for col_idx, cell in enumerate(row):
                if cell is None:
                    empty_positions.append((row_idx, col_idx))
        return empty_positions

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert grid to dictionary for serialization.

        Returns
        -------
        Dict[str, Any]
            Dictionary representation of the grid
        """
        return {"board": self.board}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Grid":
        """
        Create Grid from dictionary.

        Parameters
        ----------
        data : Dict[str, Any]
            Dictionary with 'board' key

        Returns
        -------
        Grid
            New Grid instance
        """
        return cls(board=data["board"])
