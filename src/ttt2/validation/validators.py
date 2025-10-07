"""
Individual validation functions.

This module provides validation functions for checking move
coordinates and board state in the tic-tac-toe game.
"""

from typing import List

from src.ttt2.validation.results import (
    ERROR_CELL_OCCUPIED,
    ERROR_OUT_OF_RANGE,
    ValidationResult,
)


def validate_range(row: int, col: int) -> ValidationResult:
    """
    Validate that coordinates are within board bounds (0-2).

    Parameters
    ----------
    row : int
        Row coordinate to validate
    col : int
        Column coordinate to validate

    Returns
    -------
    ValidationResult
        Validation result with error message if invalid

    Examples
    --------
    >>> result = validate_range(1, 2)
    >>> result.is_valid
    True

    >>> result = validate_range(3, 2)
    >>> result.is_valid
    False
    >>> result.error_code
    'OUT_OF_RANGE'
    """
    if not (0 <= row <= 2 and 0 <= col <= 2):
        return ValidationResult(
            is_valid=False,
            error_message=(
                f"Numbers must be between 0 and 2. You entered: ({row}, {col})"
            ),
            error_code=ERROR_OUT_OF_RANGE,
        )

    return ValidationResult(is_valid=True, parsed_row=row, parsed_column=col)


def validate_occupancy(board: List[List[str]], row: int, col: int) -> ValidationResult:
    """
    Validate that the specified position is empty.

    Parameters
    ----------
    board : list[list[str]]
        Current game board (3x3 grid)
    row : int
        Row coordinate (0-2)
    col : int
        Column coordinate (0-2)

    Returns
    -------
    ValidationResult
        Validation result indicating if position is empty

    Examples
    --------
    >>> board = [[' ', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']]
    >>> result = validate_occupancy(board, 1, 1)
    >>> result.is_valid
    True

    >>> board[1][1] = 'X'
    >>> result = validate_occupancy(board, 1, 1)
    >>> result.is_valid
    False
    >>> result.error_code
    'CELL_OCCUPIED'
    """
    if board[row][col] != " ":
        return ValidationResult(
            is_valid=False,
            error_message=(
                f"Position ({row}, {col}) is already occupied. "
                "Please choose another."
            ),
            error_code=ERROR_CELL_OCCUPIED,
        )

    return ValidationResult(is_valid=True, parsed_row=row, parsed_column=col)
