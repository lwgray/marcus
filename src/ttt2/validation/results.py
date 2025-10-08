"""
Validation result data structures.

This module defines the data structures used to represent the results
of input validation operations in the tic-tac-toe game.
"""

from dataclasses import dataclass
from typing import Optional

# Error code constants
ERROR_EMPTY_INPUT = "EMPTY_INPUT"
ERROR_INVALID_FORMAT = "INVALID_FORMAT"
ERROR_OUT_OF_RANGE = "OUT_OF_RANGE"
ERROR_CELL_OCCUPIED = "CELL_OCCUPIED"
ERROR_WRONG_COUNT = "WRONG_COUNT"


@dataclass
class ValidationResult:
    """
    Result of input validation attempt.

    This dataclass encapsulates the outcome of validating user input,
    including whether the validation passed, any error information,
    and the parsed coordinates if validation succeeded.

    Attributes
    ----------
    is_valid : bool
        Whether validation passed
    error_message : str | None
        Human-readable error message if validation failed
    error_code : str | None
        Machine-readable error code for programmatic handling
    parsed_row : int | None
        Validated row coordinate (only if valid)
    parsed_column : int | None
        Validated column coordinate (only if valid)

    Examples
    --------
    >>> # Valid result
    >>> result = ValidationResult(is_valid=True, parsed_row=1, parsed_column=2)
    >>> result.is_valid
    True

    >>> # Invalid result
    >>> result = ValidationResult(
    ...     is_valid=False,
    ...     error_message="Out of range",
    ...     error_code=ERROR_OUT_OF_RANGE
    ... )
    >>> result.is_valid
    False
    """

    is_valid: bool
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    parsed_row: Optional[int] = None
    parsed_column: Optional[int] = None
