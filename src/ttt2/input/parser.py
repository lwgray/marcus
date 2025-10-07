"""
Input parsing utilities.

This module provides functions for parsing raw player input strings
into structured coordinates for the tic-tac-toe game.
"""

from typing import Tuple


def parse_player_input(input_string: str) -> Tuple[int, int]:
    """
    Parse player input string into row and column coordinates.

    Supports both space-separated and comma-separated formats:
    - "1 2" -> (1, 2)
    - "1,2" -> (1, 2)
    - "  1  2  " -> (1, 2)  (whitespace trimmed)

    Parameters
    ----------
    input_string : str
        Raw input from player

    Returns
    -------
    tuple[int, int]
        Tuple of (row, column) coordinates

    Raises
    ------
    ValueError
        If input format is invalid
    TypeError
        If input is not a string

    Examples
    --------
    >>> parse_player_input("1 2")
    (1, 2)
    >>> parse_player_input("0,0")
    (0, 0)
    """
    if not isinstance(input_string, str):
        raise TypeError(f"Input must be string, got {type(input_string)}")

    # Strip whitespace
    input_string = input_string.strip()

    # Check for empty input
    if not input_string:
        raise ValueError(
            "Input cannot be empty. Please enter row and column (e.g., '1 2')"
        )

    # Parse based on separator
    if "," in input_string:
        parts = input_string.split(",")
    else:
        parts = input_string.split()

    # Validate count
    if len(parts) != 2:
        raise ValueError("Please enter exactly 2 numbers (row and column)")

    # Convert to integers
    try:
        row = int(parts[0].strip())
        col = int(parts[1].strip())
    except ValueError:
        raise ValueError(
            "Invalid format. Please enter two numbers separated by space (e.g., '1 2')"
        )

    return row, col
