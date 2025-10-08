"""
Unit tests for input parser.

This test module verifies the parse_player_input function that
converts raw user input strings into row/column coordinates.
"""

import pytest

from src.ttt2.input.parser import parse_player_input


class TestParsePlayerInput:
    """Test suite for parse_player_input function."""

    def test_space_separated_input(self):
        """Test parsing space-separated input."""
        result = parse_player_input("1 2")
        assert result == (1, 2)

    def test_comma_separated_input(self):
        """Test parsing comma-separated input."""
        result = parse_player_input("1,2")
        assert result == (1, 2)

    def test_whitespace_trimming(self):
        """Test that whitespace is properly trimmed."""
        result = parse_player_input("  1  2  ")
        assert result == (1, 2)

    def test_empty_input_raises_error(self):
        """Test that empty input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_player_input("")

    def test_wrong_count_raises_error(self):
        """Test that wrong number count raises ValueError."""
        with pytest.raises(ValueError, match="exactly 2 numbers"):
            parse_player_input("1")

        with pytest.raises(ValueError, match="exactly 2 numbers"):
            parse_player_input("1 2 3")

    def test_non_numeric_input_raises_error(self):
        """Test that non-numeric input raises ValueError."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_player_input("a b")

    def test_non_string_input_raises_error(self):
        """Test that non-string input raises TypeError."""
        with pytest.raises(TypeError):
            parse_player_input(123)
