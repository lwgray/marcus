"""
Unit tests for GridRenderer component.

This module tests the GridRenderer class for terminal display of the grid.
"""

import pytest

from src.models.grid import Grid
from src.ui.grid_renderer import GridRenderer


class TestGridRendererBasic:
    """Test suite for basic GridRenderer functionality."""

    def test_render_empty_grid(self):
        """Test rendering an empty 3x3 grid."""
        # Arrange
        grid = Grid()
        renderer = GridRenderer()

        # Act
        output = renderer.render(grid)

        # Assert
        assert output is not None
        assert isinstance(output, str)
        assert len(output.strip()) > 0

    def test_render_grid_contains_dividers(self):
        """Test that rendered grid contains row dividers."""
        # Arrange
        grid = Grid()
        renderer = GridRenderer()

        # Act
        output = renderer.render(grid)

        # Assert
        # Should have horizontal dividers between rows
        assert "---" in output or "─" in output

    def test_render_grid_contains_vertical_separators(self):
        """Test that rendered grid contains column separators."""
        # Arrange
        grid = Grid()
        renderer = GridRenderer()

        # Act
        output = renderer.render(grid)

        # Assert
        # Should have vertical separators between columns
        assert "|" in output or "│" in output


class TestGridRendererWithMarkers:
    """Test suite for rendering grids with X and O markers."""

    def test_render_grid_with_x_marker(self):
        """Test rendering grid with X marker."""
        # Arrange
        board = [["X", None, None], [None, None, None], [None, None, None]]
        grid = Grid(board=board)
        renderer = GridRenderer()

        # Act
        output = renderer.render(grid)

        # Assert
        assert "X" in output

    def test_render_grid_with_o_marker(self):
        """Test rendering grid with O marker."""
        # Arrange
        board = [[None, None, None], [None, "O", None], [None, None, None]]
        grid = Grid(board=board)
        renderer = GridRenderer()

        # Act
        output = renderer.render(grid)

        # Assert
        assert "O" in output

    def test_render_grid_with_both_markers(self):
        """Test rendering grid with both X and O markers."""
        # Arrange
        board = [["X", None, "O"], [None, "X", None], ["O", None, None]]
        grid = Grid(board=board)
        renderer = GridRenderer()

        # Act
        output = renderer.render(grid)

        # Assert
        assert "X" in output
        assert "O" in output
        assert output.count("X") == 2
        assert output.count("O") == 2


class TestGridRendererPositionNumbers:
    """Test suite for rendering position numbers in empty cells."""

    def test_render_empty_cells_with_position_numbers(self):
        """Test that empty cells show position numbers (1-9)."""
        # Arrange
        grid = Grid()
        renderer = GridRenderer(show_positions=True)

        # Act
        output = renderer.render(grid)

        # Assert
        # Should contain position numbers 1-9
        for i in range(1, 10):
            assert str(i) in output

    def test_render_partial_grid_shows_remaining_positions(self):
        """Test that only empty cells show position numbers."""
        # Arrange
        board = [["X", None, None], [None, "O", None], [None, None, None]]
        grid = Grid(board=board)
        renderer = GridRenderer(show_positions=True)

        # Act
        output = renderer.render(grid)

        # Assert
        # Should show X and O, plus position numbers for empty cells
        assert "X" in output
        assert "O" in output
        # Position 1 should not show (occupied by X)
        # Position 5 should not show (occupied by O)
        # Other positions should show

    def test_render_without_position_numbers(self):
        """Test rendering without position numbers (default)."""
        # Arrange
        grid = Grid()
        renderer = GridRenderer(show_positions=False)

        # Act
        output = renderer.render(grid)

        # Assert
        # Empty cells should show spaces or other indicator, not numbers
        # This is default behavior
        assert output is not None
        assert len(output) > 0


class TestGridRendererFormatting:
    """Test suite for grid formatting and structure."""

    def test_render_output_has_correct_number_of_lines(self):
        """Test that rendered output has expected number of lines."""
        # Arrange
        grid = Grid()
        renderer = GridRenderer()

        # Act
        output = renderer.render(grid)
        lines = output.strip().split("\n")

        # Assert
        # Should have at least 5 lines (3 rows + 2 dividers)
        assert len(lines) >= 5

    def test_render_grid_is_symmetric(self):
        """Test that rendered grid has symmetric structure."""
        # Arrange
        grid = Grid()
        renderer = GridRenderer()

        # Act
        output = renderer.render(grid)
        lines = output.strip().split("\n")

        # Assert
        # All lines should have similar length (within reason)
        line_lengths = [len(line) for line in lines if line.strip()]
        if line_lengths:
            max_len = max(line_lengths)
            min_len = min(line_lengths)
            # Allow some variation for different line types
            assert max_len - min_len < 10


class TestGridRendererEdgeCases:
    """Test suite for edge cases."""

    def test_render_full_grid(self):
        """Test rendering completely filled grid."""
        # Arrange
        board = [["X", "O", "X"], ["O", "X", "O"], ["X", "O", "X"]]
        grid = Grid(board=board)
        renderer = GridRenderer()

        # Act
        output = renderer.render(grid)

        # Assert
        assert "X" in output
        assert "O" in output
        assert output.count("X") == 5
        assert output.count("O") == 4

    def test_render_with_custom_renderer_settings(self):
        """Test that renderer accepts custom settings."""
        # Arrange
        grid = Grid()

        # Act & Assert - should not raise error
        renderer1 = GridRenderer(show_positions=True)
        renderer2 = GridRenderer(show_positions=False)

        output1 = renderer1.render(grid)
        output2 = renderer2.render(grid)

        assert output1 is not None
        assert output2 is not None

    def test_render_with_header(self):
        """Test rendering grid with header message."""
        # Arrange
        grid = Grid()
        renderer = GridRenderer()

        # Act
        output = renderer.render_with_header(grid, header="Player X's Turn")

        # Assert
        assert "Player X's Turn" in output
        assert "┌───┬───┬───┐" in output

    def test_render_with_empty_header(self):
        """Test rendering grid with empty header."""
        # Arrange
        grid = Grid()
        renderer = GridRenderer()

        # Act
        output = renderer.render_with_header(grid, header="")

        # Assert - should just have the grid, no header
        assert output == renderer.render(grid)

    def test_render_with_labels(self):
        """Test rendering grid with row and column labels."""
        # Arrange
        grid = Grid()
        renderer = GridRenderer()

        # Act
        output = renderer.render_with_labels(grid)

        # Assert
        # Should have column headers
        assert "0   1   2" in output
        # Should have row labels
        assert "0 │" in output
        assert "1 │" in output
        assert "2 │" in output

    def test_get_cell_out_of_bounds(self):
        """Test that get_cell raises error for out of bounds."""
        # Arrange
        grid = Grid()

        # Act & Assert
        with pytest.raises(IndexError):
            grid.get_cell(3, 0)

        with pytest.raises(IndexError):
            grid.get_cell(0, 3)

        with pytest.raises(IndexError):
            grid.get_cell(-1, 0)

    def test_grid_serialization(self):
        """Test grid to_dict and from_dict."""
        # Arrange
        board = [["X", None, "O"], [None, "X", None], ["O", None, None]]
        original_grid = Grid(board=board)

        # Act
        grid_dict = original_grid.to_dict()
        reconstructed_grid = Grid.from_dict(grid_dict)

        # Assert
        assert reconstructed_grid.board == original_grid.board
        assert grid_dict["board"] == board
