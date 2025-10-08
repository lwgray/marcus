"""
High-level game control functions.

This module provides the main game controller functions that
orchestrate the complete player move workflow.
"""

from typing import List, Optional, Tuple

from src.ttt2.input.handler import get_raw_input
from src.ttt2.validation.pipeline import validate_complete_move


def get_player_move(
    board: List[List[str]], player: str, max_retries: Optional[int] = None
) -> Tuple[int, int]:
    """
    Get validated move from player with retry loop.

    This function handles the complete player move workflow:
    1. Prompt for input
    2. Validate input (format, range, occupancy)
    3. Retry on errors with helpful messages
    4. Return valid coordinates

    Parameters
    ----------
    board : list[list[str]]
        Current game board
    player : str
        Current player ('X' or 'O')
    max_retries : int | None
        Maximum retry attempts (None = infinite)

    Returns
    -------
    tuple[int, int]
        Valid (row, column) coordinates

    Raises
    ------
    KeyboardInterrupt
        If user exits with Ctrl+C

    Examples
    --------
    >>> board = [[' ', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']]
    >>> # In interactive session
    >>> get_player_move(board, 'X')  # doctest: +SKIP
    Player X's turn
    Enter your move (row column): 1 2
    (1, 2)
    """
    attempts = 0

    while True:
        # Get input
        raw_input = get_raw_input(player)

        # Validate
        result = validate_complete_move(board, raw_input)

        if result.is_valid:
            # Type check: if is_valid is True, parsed values are guaranteed non-None
            if result.parsed_row is None or result.parsed_column is None:
                raise RuntimeError("Validation succeeded but coordinates are None")
            return result.parsed_row, result.parsed_column
        else:
            # Show error and retry
            print(f"Error: {result.error_message}\n")
            attempts += 1

            if max_retries is not None and attempts >= max_retries:
                raise ValueError(f"Maximum retries ({max_retries}) exceeded")
