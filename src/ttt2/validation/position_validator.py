"""
Position-based input validation for tic-tac-toe.

This module provides validation for position-based input (1-9) as an
alternative to coordinate-based input (row, column). This is more
intuitive for players.

Board layout:
 1 | 2 | 3
-----------
 4 | 5 | 6
-----------
 7 | 8 | 9
"""

from typing import List, Tuple

from src.ttt2.validation.results import ERROR_CELL_OCCUPIED, ValidationResult


def parse_position_input(input_string: str) -> Tuple[int, int]:
    """
    Parse position input (1-9) into row and column coordinates.

    Parameters
    ----------
    input_string : str
        Position number as string (1-9)

    Returns
    -------
    tuple[int, int]
        Tuple of (row, column) coordinates (0-2, 0-2)

    Raises
    ------
    ValueError
        If position is not a valid number between 1-9

    Examples
    --------
    >>> parse_position_input("1")
    (0, 0)
    >>> parse_position_input("5")
    (1, 1)
    >>> parse_position_input("9")
    (2, 2)
    """
    # Strip whitespace
    input_string = input_string.strip()

    # Check for empty input
    if not input_string:
        raise ValueError(
            "❌ Error: Input cannot be empty.\n"
            "💡 Tip: Enter a number from 1-9 to choose your position."
        )

    # Check for multiple values
    if " " in input_string or "," in input_string:
        raise ValueError(
            "❌ Error: Please enter a single position number.\n"
            "💡 Tip: Use numbers 1-9 (e.g., '5' for center)."
        )

    # Try to parse as number
    try:
        # Check for decimal point
        if "." in input_string:
            raise ValueError(
                "❌ Error: Position must be a whole number (1-9).\n"
                "💡 Tip: Use integers like 1, 2, 3, not decimals like 1.5."
            )

        position = int(input_string)
    except ValueError as e:
        if "whole number" in str(e):
            raise
        raise ValueError(
            "❌ Error: Input must be a number.\n"
            "💡 Tip: Enter a digit from 1-9 "
            "(e.g., '1' for top-left, '9' for bottom-right)."
        )

    # Validate range
    if not (1 <= position <= 9):
        raise ValueError(
            f"❌ Error: Position must be between 1 and 9, got {position}.\n"
            "💡 Tip: Choose a number from 1 (top-left) to 9 (bottom-right)."
        )

    # Convert position to coordinates
    # Position 1-9 maps to grid:
    #  1 | 2 | 3
    # -----------
    #  4 | 5 | 6
    # -----------
    #  7 | 8 | 9
    row = (position - 1) // 3
    col = (position - 1) % 3

    return (row, col)


def validate_position_input(
    board: List[List[str]], input_string: str
) -> ValidationResult:
    """
    Validate position-based input (1-9) with complete pipeline.

    Pipeline stages:
    1. Parse position string to coordinates
    2. Validate cell is not occupied

    Parameters
    ----------
    board : list[list[str]]
        Current game board (3x3 grid)
    input_string : str
        Position input from player (1-9)

    Returns
    -------
    ValidationResult
        Complete validation result from all stages

    Examples
    --------
    >>> board = [[' ', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']]
    >>> result = validate_position_input(board, "5")
    >>> result.is_valid
    True
    >>> result.parsed_row
    1
    >>> result.parsed_column
    1

    >>> board[1][1] = 'X'
    >>> result = validate_position_input(board, "5")
    >>> result.is_valid
    False
    """
    # Stage 1: Parse position to coordinates
    try:
        row, col = parse_position_input(input_string)
    except ValueError as e:
        return ValidationResult(
            is_valid=False, error_message=str(e), error_code="INVALID_FORMAT"
        )

    # Stage 2: Validate cell is empty
    if board[row][col] != " ":
        # Calculate position for error message
        position = row * 3 + col + 1
        return ValidationResult(
            is_valid=False,
            error_message=(
                f"❌ Error: Position {position} is already taken.\n"
                "💡 Tip: Choose an empty position (shown as a number on the board)."
            ),
            error_code=ERROR_CELL_OCCUPIED,
        )

    return ValidationResult(is_valid=True, parsed_row=row, parsed_column=col)
