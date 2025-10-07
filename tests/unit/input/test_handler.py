"""
Unit tests for input handler.

This test module verifies the get_raw_input function that
displays prompts and captures user input.
"""

from unittest.mock import patch

import pytest

from src.ttt2.input.handler import get_raw_input


class TestGetRawInput:
    """Test suite for get_raw_input function."""

    def test_get_input_with_default_prompt(self):
        """Test getting input with default prompt."""
        with patch("builtins.input", return_value="1 2"):
            result = get_raw_input("X")
            assert result == "1 2"

    def test_get_input_with_custom_prompt(self):
        """Test getting input with custom prompt."""
        with patch("builtins.input", return_value="0 0"):
            result = get_raw_input("O", "Your move, {player}: ")
            assert result == "0 0"

    def test_keyboard_interrupt_propagates(self):
        """Test that KeyboardInterrupt is allowed to propagate."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                get_raw_input("X")

    def test_eof_error_exits_gracefully(self):
        """Test that EOFError causes graceful exit."""
        with patch("builtins.input", side_effect=EOFError):
            with pytest.raises(SystemExit):
                get_raw_input("X")
