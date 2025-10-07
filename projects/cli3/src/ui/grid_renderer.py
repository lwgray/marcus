"""
GridRenderer component for terminal display.

This module provides the GridRenderer class for displaying the 3x3 grid
in the terminal with proper formatting.
"""

from typing import Optional

from src.models.grid import Grid


class GridRenderer:
    """
    Renders a 3x3 tic-tac-toe grid for terminal display.

    Attributes
    ----------
    show_positions : bool
        Whether to show position numbers (1-9) in empty cells

    Examples
    --------
    >>> grid = Grid()
    >>> renderer = GridRenderer(show_positions=True)
    >>> print(renderer.render(grid))
    """

    def __init__(self, show_positions: bool = False):
        """
        Initialize the GridRenderer.

        Parameters
        ----------
        show_positions : bool, default=False
            Whether to show position numbers in empty cells
        """
        self.show_positions = show_positions

    def render(self, grid: Grid) -> str:
        """
        Render the grid as a formatted string.

        Parameters
        ----------
        grid : Grid
            The grid to render

        Returns
        -------
        str
            Formatted string representation of the grid

        Examples
        --------
        >>> grid = Grid()
        >>> renderer = GridRenderer()
        >>> output = renderer.render(grid)
        """
        lines = []

        # Top border
        lines.append("┌───┬───┬───┐")

        # Render each row
        for row_idx in range(3):
            row_content = self._render_row(grid, row_idx)
            lines.append(row_content)

            # Add divider between rows (but not after last row)
            if row_idx < 2:
                lines.append("├───┼───┼───┤")

        # Bottom border
        lines.append("└───┴───┴───┘")

        return "\n".join(lines)

    def _render_row(self, grid: Grid, row_idx: int) -> str:
        """
        Render a single row of the grid.

        Parameters
        ----------
        grid : Grid
            The grid being rendered
        row_idx : int
            The row index (0-2)

        Returns
        -------
        str
            Formatted row string
        """
        cells = []
        for col_idx in range(3):
            cell_value = grid.get_cell(row_idx, col_idx)
            cell_display = self._format_cell(cell_value, row_idx, col_idx)
            cells.append(cell_display)

        return f"│ {cells[0]} │ {cells[1]} │ {cells[2]} │"

    def _format_cell(
        self, cell_value: Optional[str], row_idx: int, col_idx: int
    ) -> str:
        """
        Format a single cell for display.

        Parameters
        ----------
        cell_value : Optional[str]
            The cell value (None, 'X', or 'O')
        row_idx : int
            Row index (0-2)
        col_idx : int
            Column index (0-2)

        Returns
        -------
        str
            Formatted cell string (single character)
        """
        if cell_value == "X":
            return "X"
        elif cell_value == "O":
            return "O"
        elif self.show_positions:
            # Calculate position number (1-9)
            position = row_idx * 3 + col_idx + 1
            return str(position)
        else:
            return " "

    def render_with_header(self, grid: Grid, header: str = "") -> str:
        """
        Render grid with an optional header message.

        Parameters
        ----------
        grid : Grid
            The grid to render
        header : str, default=""
            Header message to display above the grid

        Returns
        -------
        str
            Grid with header
        """
        output_lines = []

        if header:
            output_lines.append(header)
            output_lines.append("")

        output_lines.append(self.render(grid))

        return "\n".join(output_lines)

    def render_with_labels(self, grid: Grid) -> str:
        """
        Render grid with row and column labels.

        Parameters
        ----------
        grid : Grid
            The grid to render

        Returns
        -------
        str
            Grid with labels
        """
        lines = []

        # Column headers
        lines.append("    0   1   2")
        lines.append("  ┌───┬───┬───┐")

        # Render each row with row label
        for row_idx in range(3):
            row_content = self._render_row(grid, row_idx)
            lines.append(f"{row_idx} {row_content}")

            # Add divider between rows
            if row_idx < 2:
                lines.append("  ├───┼───┼───┤")

        # Bottom border
        lines.append("  └───┴───┴───┘")

        return "\n".join(lines)
