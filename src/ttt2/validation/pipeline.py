"""
Complete validation pipeline.

This module provides the main validation function that orchestrates
all validation stages for player move input.
"""

from typing import List

from src.ttt2.input.parser import parse_player_input
from src.ttt2.validation.results import ValidationResult
from src.ttt2.validation.validators import validate_occupancy, validate_range


def validate_complete_move(
    board: List[List[str]], input_string: str
) -> ValidationResult:
    """
    Run complete validation pipeline on raw input.

    Pipeline stages:
    1. Parse input string
    2. Validate range (0-2)
    3. Validate occupancy

    Parameters
    ----------
    board : list[list[str]]
        Current game board
    input_string : str
        Raw input from player

    Returns
    -------
    ValidationResult
        Complete validation result from all stages

    Examples
    --------
    >>> board = [[' ', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']]
    >>> result = validate_complete_move(board, "1 2")
    >>> result.is_valid
    True
    >>> result.parsed_row
    1
    >>> result.parsed_column
    2

    >>> result = validate_complete_move(board, "3 2")
    >>> result.is_valid
    False
    >>> result.error_code
    'OUT_OF_RANGE'
    """
    # Stage 1: Parse input
    try:
        row, col = parse_player_input(input_string)
    except (ValueError, TypeError) as e:
        return ValidationResult(
            is_valid=False, error_message=str(e), error_code="INVALID_FORMAT"
        )

    # Stage 2: Validate range
    range_result = validate_range(row, col)
    if not range_result.is_valid:
        return range_result

    # Stage 3: Validate occupancy
    occupancy_result = validate_occupancy(board, row, col)
    return occupancy_result
