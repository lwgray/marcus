#!/usr/bin/env python3
"""
Script to update imports after removing prefixes and suffixes from file names.

This script updates all Python files that import the renamed modules.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def find_files_with_import(pattern: str, directory: str = ".") -> List[Path]:
    """Find all Python files containing the specified import pattern."""
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".py"):
                filepath = Path(root) / filename
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        if pattern in content:
                            files.append(filepath)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    return files


def update_imports_in_file(
    file_path: Path, replacements: List[Tuple[str, str]]
) -> bool:
    """Update imports in a single file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        modified = False
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                modified = True

        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Updated: {file_path}")
            return True
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
    return False


def main():
    """Main function to update all imports after file renames."""

    # Define all the replacements needed
    replacements = [
        # Kanban client changes
        (
            "from src.integrations.kanban_client import",
            "from src.integrations.kanban_client import",
        ),
        ("from src.integrations.kanban_client", "from src.integrations.kanban_client"),
        (
            "import src.integrations.kanban_client",
            "import src.integrations.kanban_client",
        ),
        ("kanban_client", "kanban_client"),
        # Natural language tools changes
        (
            "from src.integrations.nlp_tools import",
            "from src.integrations.nlp_tools import",
        ),
        ("from src.integrations.nlp_tools", "from src.integrations.nlp_tools"),
        ("import src.integrations.nlp_tools", "import src.integrations.nlp_tools"),
        ("nlp_tools", "nlp_tools"),
        # Planka provider changes
        (
            "from src.integrations.providers.planka_simple import",
            "from src.integrations.providers.planka_simple import",
        ),
        (
            "from src.integrations.providers.planka_simple",
            "from src.integrations.providers.planka_simple",
        ),
        (
            "import src.integrations.providers.planka_simple",
            "import src.integrations.providers.planka_simple",
        ),
        ("planka_simple", "planka_simple"),
        ("PlankaSimple", "PlankaSimple"),
        # Class name updates
        ("KanbanClient", "KanbanClient"),
    ]

    print("Updating imports after file renames...")
    print("=" * 60)

    # Find all Python files
    python_files = []
    for root, _, filenames in os.walk("."):
        for filename in filenames:
            if filename.endswith(".py"):
                python_files.append(Path(root) / filename)

    print(f"Found {len(python_files)} Python files to check")

    # Update each file
    updated_count = 0
    for file_path in python_files:
        if update_imports_in_file(file_path, replacements):
            updated_count += 1

    print(f"\nUpdated {updated_count} files")

    # Show what was done
    print("\nFiles renamed:")
    print("- kanban_client.py → kanban_client.py")
    print("- nlp_tools.py → nlp_tools.py")
    print("- planka_simple.py → planka_simple.py")

    print("\nClass names updated:")
    print("- KanbanClient → KanbanClient")
    print("- PlankaSimple → PlankaSimple")


if __name__ == "__main__":
    main()
