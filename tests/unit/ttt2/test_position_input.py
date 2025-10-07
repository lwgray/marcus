"""
Unit tests for position-based input validation.

This module tests the position-based input system (1-9) for the
tic-tac-toe game, which provides a simpler interface than coordinates.
"""

import pytest

from src.ttt2.validation.position_validator import (
    parse_position_input,
    validate_position_input,
)


@pytest.mark.unit
class TestPositionInputParsing:
    """Test suite for position-based input parsing (1-9)."""

    def test_parse_position_valid_range(self):
        """Test parsing positions 1-9."""
        for position in range(1, 10):
            row, col = parse_position_input(str(position))
            assert 0 <= row <= 2
            assert 0 <= col <= 2

    def test_parse_position_1(self):
        """Test position 1 maps to (0, 0)."""
        row, col = parse_position_input("1")
        assert row == 0
        assert col == 0

    def test_parse_position_5(self):
        """Test position 5 maps to (1, 1) - center."""
        row, col = parse_position_input("5")
        assert row == 1
        assert col == 1

    def test_parse_position_9(self):
        """Test position 9 maps to (2, 2)."""
        row, col = parse_position_input("9")
        assert row == 2
        assert col == 2

    def test_parse_position_with_whitespace(self):
        """Test parsing handles whitespace correctly."""
        row, col = parse_position_input("  5  ")
        assert row == 1
        assert col == 1

    def test_parse_position_zero_raises_error(self):
        """Test position 0 is invalid."""
        with pytest.raises(ValueError, match="between 1 and 9"):
            parse_position_input("0")

    def test_parse_position_ten_raises_error(self):
        """Test position 10 is invalid."""
        with pytest.raises(ValueError, match="between 1 and 9"):
            parse_position_input("10")

    def test_parse_position_negative_raises_error(self):
        """Test negative position is invalid."""
        with pytest.raises(ValueError, match="between 1 and 9"):
            parse_position_input("-1")

    def test_parse_position_empty_raises_error(self):
        """Test empty input raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_position_input("")

    def test_parse_position_non_numeric_raises_error(self):
        """Test non-numeric input raises error."""
        with pytest.raises(ValueError, match="must be a number"):
            parse_position_input("abc")

    def test_parse_position_float_raises_error(self):
        """Test decimal input raises error."""
        with pytest.raises(ValueError, match="must be a whole number"):
            parse_position_input("1.5")

    def test_parse_position_multiple_numbers_raises_error(self):
        """Test multiple numbers raise error."""
        with pytest.raises(ValueError, match="single position"):
            parse_position_input("1 2")


@pytest.mark.unit
class TestPositionValidationPipeline:
    """Test suite for complete position-based validation."""

    def test_validate_position_valid_empty_cell(self):
        """Test validation accepts valid position on empty cell."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        result = validate_position_input(board, "5")
        assert result.is_valid is True
        assert result.parsed_row == 1
        assert result.parsed_column == 1

    def test_validate_position_all_valid_positions(self):
        """Test validation accepts all valid positions 1-9."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        for position in range(1, 10):
            result = validate_position_input(board, str(position))
            assert result.is_valid is True

    def test_validate_position_occupied_cell(self):
        """Test validation rejects occupied cell."""
        board = [[" ", " ", " "], [" ", "X", " "], [" ", " ", " "]]
        result = validate_position_input(board, "5")  # Center
        assert result.is_valid is False
        assert (
            "already occupied" in result.error_message
            or "taken" in result.error_message
        )

    def test_validate_position_out_of_range(self):
        """Test validation rejects out-of-range position."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        result = validate_position_input(board, "10")
        assert result.is_valid is False

    def test_validate_position_invalid_format(self):
        """Test validation rejects invalid format."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        result = validate_position_input(board, "abc")
        assert result.is_valid is False


@pytest.mark.unit
class TestPositionErrorMessages:
    """Test suite for position-based error message formatting."""

    def test_error_has_emoji_format(self):
        """Test error messages use emoji format."""
        board = [[" ", " ", " "], [" ", "X", " "], [" ", " ", " "]]
        result = validate_position_input(board, "5")
        assert result.is_valid is False
        # Should have error indicator and tip
        error_msg = result.error_message
        assert "❌" in error_msg or "Error" in error_msg
        assert "💡" in error_msg or "Tip" in error_msg or "choose" in error_msg.lower()

    def test_error_out_of_range_descriptive(self):
        """Test out of range error is descriptive."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        result = validate_position_input(board, "10")
        assert result.is_valid is False
        assert "1" in result.error_message and "9" in result.error_message

    def test_error_invalid_format_helpful(self):
        """Test invalid format error provides helpful guidance."""
        board = [[" ", " ", " "], [" ", " ", " "], [" ", " ", " "]]
        result = validate_position_input(board, "abc")
        assert result.is_valid is False
        assert result.error_message  # Non-empty message


@pytest.mark.unit
class TestPositionToCoordinateMapping:
    """Test suite verifying position-to-coordinate mapping."""

    def test_position_mapping_layout(self):
        """
        Test position mapping matches expected board layout.

        Board positions:
         1 | 2 | 3
        -----------
         4 | 5 | 6
        -----------
         7 | 8 | 9
        """
        expected = {
            1: (0, 0),
            2: (0, 1),
            3: (0, 2),
            4: (1, 0),
            5: (1, 1),
            6: (1, 2),
            7: (2, 0),
            8: (2, 1),
            9: (2, 2),
        }

        for position, (expected_row, expected_col) in expected.items():
            row, col = parse_position_input(str(position))
            assert (
                row == expected_row and col == expected_col
            ), f"Position {position} should map to ({expected_row}, {expected_col}), got ({row}, {col})"
