"""
Display Board Component for Tic-Tac-Toe Game.

This module provides the Board class, CellState enum, and utility functions
for managing and displaying the 3x3 tic-tac-toe game board.
"""

import sys
from enum import Enum
from typing import List, Tuple


class CellState(Enum):
    """
    Enumeration for tic-tac-toe cell states.

    Attributes
    ----------
    EMPTY : str
        Represents an unoccupied cell (value: " ")
    X : str
        Represents a cell occupied by player X (value: "X")
    O : str
        Represents a cell occupied by player O (value: "O")
    """

    EMPTY = " "
    X = "X"
    O = "O"  # noqa: E741  # 'O' is standard tic-tac-toe symbol


def position_to_coords(position: int) -> Tuple[int, int]:
    """
    Convert a position number (1-9) to board coordinates.

    Parameters
    ----------
    position : int
        Position number (1-9)

    Returns
    -------
    Tuple[int, int]
        (row, col) where both are 0-2

    Raises
    ------
    ValueError
        If position is not in range 1-9

    Examples
    --------
    >>> position_to_coords(1)
    (0, 0)
    >>> position_to_coords(5)
    (1, 1)
    >>> position_to_coords(9)
    (2, 2)
    """
    if not (1 <= position <= 9):
        raise ValueError(f"Position must be between 1 and 9, got {position}")

    row = (position - 1) // 3
    col = (position - 1) % 3
    return (row, col)


def coords_to_position(row: int, col: int) -> int:
    """
    Convert board coordinates to a position number (1-9).

    Parameters
    ----------
    row : int
        Row index (0-2)
    col : int
        Column index (0-2)

    Returns
    -------
    int
        Position number (1-9)

    Raises
    ------
    ValueError
        If row or col is out of bounds

    Examples
    --------
    >>> coords_to_position(0, 0)
    1
    >>> coords_to_position(1, 1)
    5
    >>> coords_to_position(2, 2)
    9
    """
    if not (0 <= row <= 2 and 0 <= col <= 2):
        raise ValueError(f"Invalid coordinates: ({row}, {col})")

    return row * 3 + col + 1


class Board:
    """
    Manages the tic-tac-toe board state and display.

    The Board class provides methods for initializing, manipulating, and
    rendering the 3x3 game board. It maintains the board state internally
    and provides validation for all operations.

    Attributes
    ----------
    _board : List[List[CellState]]
        3x3 grid representing the board state (private)
    _box_drawing_enabled : bool
        Whether UTF-8 box-drawing characters are supported
    """

    def __init__(self) -> None:
        """Initialize a new empty 3x3 board."""
        self._board: List[List[CellState]] = [
            [CellState.EMPTY for _ in range(3)] for _ in range(3)
        ]
        self._box_drawing_enabled = self._supports_box_drawing()

    def _supports_box_drawing(self) -> bool:
        """
        Check if terminal supports UTF-8 box-drawing characters.

        Returns
        -------
        bool
            True if UTF-8 is supported, False otherwise
        """
        try:
            encoding = sys.stdout.encoding
            if encoding:
                return encoding.lower() in ["utf-8", "utf8"]
            return False
        except (AttributeError, Exception):
            return False

    def _validate_coords(self, row: int, col: int) -> None:
        """
        Validate that coordinates are within bounds.

        Parameters
        ----------
        row : int
            Row index
        col : int
            Column index

        Raises
        ------
        ValueError
            If row or col is out of bounds (not 0-2)
        """
        if not (0 <= row <= 2 and 0 <= col <= 2):
            raise ValueError(f"Invalid coordinates: ({row}, {col})")

    def get_cell(self, row: int, col: int) -> CellState:
        """
        Get the state of a specific cell.

        Parameters
        ----------
        row : int
            Row index (0-2)
        col : int
            Column index (0-2)

        Returns
        -------
        CellState
            Current state of the cell

        Raises
        ------
        ValueError
            If row or col is out of bounds

        Examples
        --------
        >>> board = Board()
        >>> board.get_cell(0, 0)
        <CellState.EMPTY: ' '>
        """
        self._validate_coords(row, col)
        return self._board[row][col]

    def set_cell(self, row: int, col: int, state: CellState) -> bool:
        """
        Set the state of a specific cell.

        Parameters
        ----------
        row : int
            Row index (0-2)
        col : int
            Column index (0-2)
        state : CellState
            New cell state (typically X or O)

        Returns
        -------
        bool
            True if cell was successfully set, False if cell was already occupied

        Raises
        ------
        ValueError
            If row or col is out of bounds
        TypeError
            If state is not a CellState enum

        Examples
        --------
        >>> board = Board()
        >>> board.set_cell(0, 0, CellState.X)
        True
        >>> board.set_cell(0, 0, CellState.O)
        False
        """
        self._validate_coords(row, col)

        if not isinstance(state, CellState):
            raise TypeError(f"State must be a CellState enum, got {type(state)}")

        if self._board[row][col] != CellState.EMPTY:
            return False

        self._board[row][col] = state
        return True

    def is_cell_empty(self, row: int, col: int) -> bool:
        """
        Check if a specific cell is available for a move.

        Parameters
        ----------
        row : int
            Row index (0-2)
        col : int
            Column index (0-2)

        Returns
        -------
        bool
            True if cell is empty, False otherwise

        Raises
        ------
        ValueError
            If row or col is out of bounds

        Examples
        --------
        >>> board = Board()
        >>> board.is_cell_empty(0, 0)
        True
        >>> board.set_cell(0, 0, CellState.X)
        True
        >>> board.is_cell_empty(0, 0)
        False
        """
        self._validate_coords(row, col)
        return self._board[row][col] == CellState.EMPTY

    def get_state(self) -> List[List[CellState]]:
        """
        Return a deep copy of the current board state.

        This method returns a copy to prevent external modification of
        the internal board state.

        Returns
        -------
        List[List[CellState]]
            3x3 nested list representing board state

        Examples
        --------
        >>> board = Board()
        >>> state = board.get_state()
        >>> len(state)
        3
        >>> len(state[0])
        3
        """
        return [row[:] for row in self._board]

    def is_full(self) -> bool:
        """
        Check if the board has no empty cells remaining.

        Returns
        -------
        bool
            True if all cells are occupied, False otherwise

        Examples
        --------
        >>> board = Board()
        >>> board.is_full()
        False
        """
        for row in self._board:
            for cell in row:
                if cell == CellState.EMPTY:
                    return False
        return True

    def reset(self) -> None:
        """
        Clear all cells and reset the board to initial empty state.

        Examples
        --------
        >>> board = Board()
        >>> board.set_cell(0, 0, CellState.X)
        True
        >>> board.reset()
        >>> board.get_cell(0, 0)
        <CellState.EMPTY: ' '>
        """
        self._board = [[CellState.EMPTY for _ in range(3)] for _ in range(3)]

    def render(self) -> str:
        """
        Generate the ASCII representation of the board as a string.

        For empty cells, displays position numbers (1-9).
        For occupied cells, displays player symbols (X or O).
        Uses box-drawing characters if supported, ASCII otherwise.

        Returns
        -------
        str
            Formatted board string with newlines

        Examples
        --------
        >>> board = Board()
        >>> print(board.render())
         1 │ 2 │ 3
        ───┼───┼───
         4 │ 5 │ 6
        ───┼───┼───
         7 │ 8 │ 9
        """
        lines = []

        # Choose separators based on terminal support
        if self._box_drawing_enabled:
            vertical_sep = "│"
            horizontal_sep = "───┼───┼───"
        else:
            vertical_sep = "|"
            horizontal_sep = "---|---|---"

        for row_idx, row in enumerate(self._board):
            # Build cell display
            cells = []
            for col_idx, cell in enumerate(row):
                if cell == CellState.EMPTY:
                    # Show position number
                    position = row_idx * 3 + col_idx + 1
                    cells.append(f" {position} ")
                else:
                    # Show player symbol
                    cells.append(f" {cell.value} ")

            # Add row with vertical separators
            lines.append(vertical_sep.join(cells))

            # Add horizontal separator (except after last row)
            if row_idx < 2:
                lines.append(horizontal_sep)

        return "\n".join(lines)

    def display(self) -> None:
        """
        Print the current board state to the console.

        Uses the render() method to generate the board representation
        and prints it to stdout.

        Examples
        --------
        >>> board = Board()
        >>> board.display()
         1 │ 2 │ 3
        ───┼───┼───
         4 │ 5 │ 6
        ───┼───┼───
         7 │ 8 │ 9
        """
        print(self.render())
