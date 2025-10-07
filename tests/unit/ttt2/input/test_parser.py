"""
Unit tests for input parser.

This module tests the parse_player_input function for various input formats.
"""

import pytest

from src.ttt2.input.parser import parse_player_input


@pytest.mark.unit
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

    def test_comma_with_spaces(self):
        """Test parsing comma-separated input with spaces."""
        result = parse_player_input("1 , 2")
        assert result == (1, 2)

    def test_multiple_spaces_between_numbers(self):
        """Test parsing with multiple spaces between numbers."""
        result = parse_player_input("1     2")
        assert result == (1, 2)

    def test_tab_separated_input(self):
        """Test parsing tab-separated input."""
        result = parse_player_input("1\t2")
        assert result == (1, 2)

    def test_mixed_whitespace(self):
        """Test parsing with mixed whitespace."""
        result = parse_player_input("  1 \t 2  ")
        assert result == (1, 2)

    def test_zero_coordinates(self):
        """Test parsing zero coordinates."""
        result = parse_player_input("0 0")
        assert result == (0, 0)

    def test_max_coordinates(self):
        """Test parsing maximum valid coordinates."""
        result = parse_player_input("2 2")
        assert result == (2, 2)

    def test_large_numbers(self):
        """Test parsing large numbers (validation happens elsewhere)."""
        result = parse_player_input("10 20")
        assert result == (10, 20)

    def test_negative_numbers(self):
        """Test parsing negative numbers."""
        result = parse_player_input("-1 -2")
        assert result == (-1, -2)

    def test_empty_input_raises_error(self):
        """Test that empty input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_player_input("")

    def test_whitespace_only_raises_error(self):
        """Test that whitespace-only input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_player_input("   ")

    def test_single_number_raises_error(self):
        """Test that single number raises ValueError."""
        with pytest.raises(ValueError, match="exactly 2 numbers"):
            parse_player_input("1")

    def test_three_numbers_raises_error(self):
        """Test that three numbers raise ValueError."""
        with pytest.raises(ValueError, match="exactly 2 numbers"):
            parse_player_input("1 2 3")

    def test_too_many_numbers_comma_separated(self):
        """Test that too many comma-separated numbers raise ValueError."""
        with pytest.raises(ValueError, match="exactly 2 numbers"):
            parse_player_input("1,2,3")

    def test_non_numeric_input_raises_error(self):
        """Test that non-numeric input raises ValueError."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_player_input("a b")

    def test_partial_numeric_input_raises_error(self):
        """Test that partially numeric input raises ValueError."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_player_input("1 b")

    def test_letters_only_raises_error(self):
        """Test that letters-only input raises ValueError."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_player_input("abc def")

    def test_special_characters_raises_error(self):
        """Test that special characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_player_input("! @")

    def test_mixed_separators_valid(self):
        """Test comma with space is valid (comma takes precedence)."""
        # When there's a comma, it's treated as comma-separated
        # Spaces around parts are trimmed
        result = parse_player_input("1, 2")
        assert result == (1, 2)

    def test_non_string_input_raises_typeerror(self):
        """Test that non-string input raises TypeError."""
        with pytest.raises(TypeError, match="Input must be string"):
            parse_player_input(123)

    def test_none_input_raises_typeerror(self):
        """Test that None input raises TypeError."""
        with pytest.raises(TypeError, match="Input must be string"):
            parse_player_input(None)

    def test_list_input_raises_typeerror(self):
        """Test that list input raises TypeError."""
        with pytest.raises(TypeError, match="Input must be string"):
            parse_player_input([1, 2])

    def test_float_string_input(self):
        """Test that float strings raise ValueError."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_player_input("1.5 2.5")

    def test_decimal_notation(self):
        """Test parsing with decimal notation."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_player_input("1.0 2.0")

    def test_leading_zeros(self):
        """Test parsing numbers with leading zeros."""
        result = parse_player_input("01 02")
        assert result == (1, 2)

    def test_plus_sign_numbers(self):
        """Test parsing numbers with explicit plus sign."""
        result = parse_player_input("+1 +2")
        assert result == (1, 2)

    def test_comma_at_end(self):
        """Test parsing with trailing comma."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_player_input("1 2,")

    def test_comma_at_start(self):
        """Test parsing with leading comma."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_player_input(",1 2")

    def test_double_comma(self):
        """Test parsing with double comma."""
        with pytest.raises(ValueError, match="exactly 2 numbers"):
            parse_player_input("1,,2")

    def test_all_valid_board_positions(self):
        """Test parsing all valid board positions."""
        valid_positions = [
            ("0 0", (0, 0)),
            ("0 1", (0, 1)),
            ("0 2", (0, 2)),
            ("1 0", (1, 0)),
            ("1 1", (1, 1)),
            ("1 2", (1, 2)),
            ("2 0", (2, 0)),
            ("2 1", (2, 1)),
            ("2 2", (2, 2)),
        ]

        for input_str, expected in valid_positions:
            result = parse_player_input(input_str)
            assert result == expected, f"Failed for input: {input_str}"

    def test_comma_format_all_positions(self):
        """Test comma format for all valid positions."""
        for row in range(3):
            for col in range(3):
                input_str = f"{row},{col}"
                result = parse_player_input(input_str)
                assert result == (row, col)
