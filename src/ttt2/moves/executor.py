"""
Move execution logic.

This module provides functions for creating and executing
validated moves on the game board.
"""

from copy import deepcopy
from typing import List, Literal

from src.ttt2.moves.models import MoveInput


def create_move(row: int, col: int, player: Literal["X", "O"]) -> MoveInput:
    """
    Create MoveInput from coordinates.

    Parameters
    ----------
    row : int
        Row coordinate (0-2)
    col : int
        Column coordinate (0-2)
    player : str
        Player identifier ('X' or 'O')

    Returns
    -------
    MoveInput
        Validated move object with timestamp

    Examples
    --------
    >>> move = create_move(1, 2, 'X')
    >>> move.row
    1
    >>> move.column
    2
    >>> move.player
    'X'
    """
    return MoveInput(row=row, column=col, player=player)


def execute_move(board: List[List[str]], move: MoveInput) -> List[List[str]]:
    """
    Apply a validated move to the board.

    This function creates a new board with the move applied,
    following the immutable pattern to avoid side effects.

    Parameters
    ----------
    board : list[list[str]]
        Current game board
    move : MoveInput
        Validated move to execute

    Returns
    -------
    list[list[str]]
        Updated board state (new copy, original unchanged)

    Raises
    ------
    ValueError
        If position is already occupied

    Examples
    --------
    >>> board = [[' ', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']]
    >>> move = MoveInput(row=1, column=2, player='X')
    >>> new_board = execute_move(board, move)
    >>> new_board[1][2]
    'X'
    >>> board[1][2]  # Original unchanged
    ' '
    """
    # Create new board (immutable pattern)
    new_board = deepcopy(board)

    # Check occupancy (defensive programming)
    if new_board[move.row][move.column] != " ":
        raise ValueError(f"Position ({move.row}, {move.column}) is already occupied")

    # Apply move
    new_board[move.row][move.column] = move.player

    return new_board
