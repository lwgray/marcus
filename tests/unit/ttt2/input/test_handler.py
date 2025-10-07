"""
Unit tests for input handler.

This module tests the get_raw_input function.
"""

from unittest.mock import patch

import pytest

from src.ttt2.input.handler import get_raw_input


@pytest.mark.unit
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

    def test_prompt_formatting_with_player_x(self):
        """Test that player X is formatted into prompt."""
        with patch("builtins.input", return_value="1 1") as mock_input:
            get_raw_input("X")
            # Check the prompt was called with formatted string
            call_args = mock_input.call_args[0][0]
            assert "X" in call_args

    def test_prompt_formatting_with_player_o(self):
        """Test that player O is formatted into prompt."""
        with patch("builtins.input", return_value="2 2") as mock_input:
            get_raw_input("O")
            call_args = mock_input.call_args[0][0]
            assert "O" in call_args

    def test_returns_exact_input(self):
        """Test that function returns exactly what user types."""
        test_inputs = ["1 2", "0,0", "  1  2  ", "abc", ""]
        for test_input in test_inputs:
            with patch("builtins.input", return_value=test_input):
                result = get_raw_input("X")
                assert result == test_input

    def test_whitespace_not_trimmed(self):
        """Test that whitespace in input is preserved."""
        with patch("builtins.input", return_value="  1  2  "):
            result = get_raw_input("X")
            assert result == "  1  2  "

    def test_empty_string_returned(self):
        """Test that empty string can be returned."""
        with patch("builtins.input", return_value=""):
            result = get_raw_input("X")
            assert result == ""

    def test_custom_prompt_template_formatting(self):
        """Test custom prompt template with placeholder."""
        custom_template = "Player {player}, enter move: "
        with patch("builtins.input", return_value="1 1") as mock_input:
            get_raw_input("X", custom_template)
            assert mock_input.call_args[0][0] == "Player X, enter move: "

    def test_multiline_input_not_supported(self):
        """Test that only first line of input is returned."""
        with patch("builtins.input", return_value="1 2"):
            result = get_raw_input("X")
            assert "\n" not in result
