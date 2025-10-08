"""
Input handling and prompts.

This module provides functions for displaying prompts and
capturing user input in the tic-tac-toe game.
"""

import sys


def get_raw_input(
    player: str,
    prompt_template: str = "Player {player}'s turn\nEnter your move (row column): ",
) -> str:
    """
    Display prompt and capture raw user input.

    Parameters
    ----------
    player : str
        Current player identifier ('X' or 'O')
    prompt_template : str
        Template for input prompt (can include {player})

    Returns
    -------
    str
        Raw input string from user

    Raises
    ------
    KeyboardInterrupt
        If user presses Ctrl+C (allowed to propagate)
    EOFError
        If input stream is closed

    Examples
    --------
    >>> # In interactive session
    >>> get_raw_input('X')  # doctest: +SKIP
    Player X's turn
    Enter your move (row column): 1 2
    '1 2'
    """
    prompt = prompt_template.format(player=player)

    try:
        return input(prompt)
    except EOFError:
        print("\nInput stream closed. Exiting game.")
        sys.exit(0)
