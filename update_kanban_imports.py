#!/usr/bin/env python3
"""
Script to update imports from MCPKanbanClientSimplified to SimpleMCPKanbanClient.

This script updates all Python files that import MCPKanbanClientSimplified
to use SimpleMCPKanbanClient instead, as part of the code consolidation effort.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def find_files_with_import(pattern: str, directory: str = ".") -> List[Path]:
    """
    Find all Python files containing the specified import pattern.
    
    Parameters
    ----------
    pattern : str
        Import pattern to search for
    directory : str
        Directory to search in
        
    Returns
    -------
    List[Path]
        List of file paths containing the pattern
    """
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".py"):
                filepath = Path(root) / filename
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if pattern in content:
                            files.append(filepath)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    return files


def update_imports_in_file(file_path: Path, replacements: List[Tuple[str, str]]) -> bool:
    """
    Update imports in a single file.
    
    Parameters
    ----------
    file_path : Path
        Path to the file to update
    replacements : List[Tuple[str, str]]
        List of (old, new) replacement tuples
        
    Returns
    -------
    bool
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = False
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                modified = True
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            return True
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
    return False


def main():
    """Main function to update kanban client imports."""
    # Define replacements
    replacements = [
        # Import statements
        ("from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient",
         "from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient"),
        ("from mcp_kanban_client_simple import SimpleMCPKanbanClient",
         "from mcp_kanban_client_simple import SimpleMCPKanbanClient"),
        ("import mcp_kanban_client_simple",
         "import mcp_kanban_client_simple"),
        
        # Class name replacements
        ("SimpleMCPKanbanClient(", "SimpleMCPKanbanClient("),
        ("SimpleMCPKanbanClient.", "SimpleMCPKanbanClient."),
        ("SimpleMCPKanbanClient)", "SimpleMCPKanbanClient)"),
        ("SimpleMCPKanbanClient as", "SimpleMCPKanbanClient as"),
        (": SimpleMCPKanbanClient", ": SimpleMCPKanbanClient"),
        ("= SimpleMCPKanbanClient", "= SimpleMCPKanbanClient"),
    ]
    
    # Find all files with the old import
    files = find_files_with_import("MCPKanbanClientSimplified", ".")
    
    if not files:
        print("No files found with MCPKanbanClientSimplified imports")
        return
    
    print(f"Found {len(files)} files with MCPKanbanClientSimplified imports:")
    for file in files:
        print(f"  - {file}")
    
    # Update each file
    updated_count = 0
    for file_path in files:
        if update_imports_in_file(file_path, replacements):
            updated_count += 1
    
    print(f"\nUpdated {updated_count} files")
    
    # Show what to do next
    print("\nNext steps:")
    print("1. Delete src/integrations/mcp_kanban_client_simplified.py")
    print("2. Run tests to ensure nothing is broken")
    print("3. Commit the changes")


if __name__ == "__main__":
    main()