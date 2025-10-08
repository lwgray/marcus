"""
Move-related data models.

This module defines data structures for representing player moves
in the tic-tac-toe game.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class MoveInput:
    """
    Represents a validated player move input.

    This dataclass encapsulates a player's move, including the
    coordinates, the player making the move, and a timestamp.
    All coordinates are validated upon creation.

    Attributes
    ----------
    row : int
        Row coordinate (0-2)
    column : int
        Column coordinate (0-2)
    player : Literal['X', 'O']
        Player who made the move
    timestamp : str
        ISO format timestamp of move creation

    Raises
    ------
    ValueError
        If coordinates are out of range or player is invalid

    Examples
    --------
    >>> move = MoveInput(row=1, column=2, player='X')
    >>> move.row
    1
    >>> move.player
    'X'

    >>> # Invalid coordinates raise ValueError
    >>> MoveInput(row=3, column=2, player='X')
    Traceback (most recent call last):
        ...
    ValueError: Row must be 0-2, got 3
    """

    row: int
    column: int
    player: Literal["X", "O"]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self) -> None:
        """Validate coordinates are in range."""
        if not (0 <= self.row <= 2):
            raise ValueError(f"Row must be 0-2, got {self.row}")
        if not (0 <= self.column <= 2):
            raise ValueError(f"Column must be 0-2, got {self.column}")
        if self.player not in ("X", "O"):
            raise ValueError(f"Player must be 'X' or 'O', got {self.player}")
