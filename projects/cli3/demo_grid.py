"""Demo script to visualize the 3x3 grid implementation."""

from src.models.grid import Grid
from src.ui.grid_renderer import GridRenderer


def main():
    """Demonstrate the grid rendering."""
    print("=" * 50)
    print("CLI3 Tic-Tac-Toe - 3x3 Grid Demo")
    print("=" * 50)
    print()

    # Empty grid
    print("1. Empty Grid:")
    empty_grid = Grid()
    renderer = GridRenderer()
    print(renderer.render(empty_grid))
    print()

    # Empty grid with position numbers
    print("2. Empty Grid with Position Numbers (1-9):")
    renderer_with_positions = GridRenderer(show_positions=True)
    print(renderer_with_positions.render(empty_grid))
    print()

    # Grid with some moves
    print("3. Grid with Some Moves:")
    board_with_moves = [["X", None, "O"], [None, "X", None], ["O", None, None]]
    grid_with_moves = Grid(board=board_with_moves)
    print(renderer.render(grid_with_moves))
    print()

    # Grid with some moves and position numbers
    print("4. Grid with Moves and Position Numbers:")
    print(renderer_with_positions.render(grid_with_moves))
    print()

    # Full grid
    print("5. Full Grid (Game Over):")
    full_board = [["X", "O", "X"], ["O", "X", "O"], ["X", "O", "X"]]
    full_grid = Grid(board=full_board)
    print(renderer.render(full_grid))
    print()

    # Grid with labels
    print("6. Grid with Row/Column Labels:")
    print(renderer.render_with_labels(grid_with_moves))
    print()

    # Grid with header
    print("7. Grid with Header:")
    print(renderer.render_with_header(grid_with_moves, header="Current Player: X"))
    print()


if __name__ == "__main__":
    main()
