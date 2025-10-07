"""
Demo script for the Display Board component.

This script demonstrates the functionality of the Board class,
showing various board states and operations.
"""

from board import Board, CellState, position_to_coords


def main() -> None:
    """Run the display board demo."""
    print("=" * 50)
    print("Tic-Tac-Toe Display Board Demo")
    print("=" * 50)
    print()

    # Create a new board
    board = Board()
    print("Initial empty board:")
    board.display()
    print()

    # Make some moves using position numbers
    print("Player X moves to position 5 (center):")
    row, col = position_to_coords(5)
    board.set_cell(row, col, CellState.X)
    board.display()
    print()

    print("Player O moves to position 1 (top-left):")
    row, col = position_to_coords(1)
    board.set_cell(row, col, CellState.O)
    board.display()
    print()

    print("Player X moves to position 3 (top-right):")
    row, col = position_to_coords(3)
    board.set_cell(row, col, CellState.X)
    board.display()
    print()

    print("Player O moves to position 9 (bottom-right):")
    row, col = position_to_coords(9)
    board.set_cell(row, col, CellState.O)
    board.display()
    print()

    print("Player X moves to position 7 (bottom-left):")
    row, col = position_to_coords(7)
    board.set_cell(row, col, CellState.X)
    board.display()
    print()

    # Demonstrate validation
    print("Attempting to move to position 5 (already occupied):")
    success = board.set_cell(1, 1, CellState.O)
    if not success:
        print("Move rejected - cell already occupied!")
    print()

    # Show board state
    print("Board state analysis:")
    print(f"  Board is full: {board.is_full()}")
    print(f"  Position 2 is empty: {board.is_cell_empty(0, 1)}")
    print(f"  Position 5 is empty: {board.is_cell_empty(1, 1)}")
    print()

    # Reset and show new game
    print("Resetting board for new game:")
    board.reset()
    board.display()
    print()

    print("=" * 50)
    print("Demo complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
