#!/usr/bin/env python3
"""
Script to update imports and method calls after server refactoring.

This script helps update test files and other modules that depend on
the refactored server module.
"""

import re
import sys
from pathlib import Path


def update_server_imports(file_path: Path) -> bool:
    """Update imports in a file to match new server structure."""
    with open(file_path, "r") as f:
        content = f.read()

    original_content = content

    # Map of old attributes to new locations
    replacements = [
        # Methods that moved to initialization module
        (
            r"server\.initialize_kanban\(",
            "await ServerInitializer(server).initialize_kanban(",
        ),
        (
            r"server\._ensure_environment_config\(",
            "ServerInitializer(server)._ensure_environment_config(",
        ),
        # Methods that are now in lifecycle module
        (r"server\.run\(", "await LifecycleManager(server).run_stdio_server("),
        # Module-level imports that need updating
        (
            r"from src\.marcus_mcp\.server import (\w+)",
            r"from src.marcus_mcp.server import \1",
        ),
        # Patching paths
        (r'"src\.marcus_mcp\.server\.stdio_server"', '"mcp.server.stdio.stdio_server"'),
        (
            r'"src\.marcus_mcp\.server\.get_config"',
            '"src.config.config_loader.get_config"',
        ),
        (
            r'"src\.marcus_mcp\.server\.register_marcus_service"',
            '"src.core.service_registry.register_marcus_service"',
        ),
    ]

    for old, new in replacements:
        content = re.sub(old, new, content)

    # Write back if changed
    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)
        return True
    return False


def main() -> None:
    """Execute the main entry point."""
    if len(sys.argv) > 1:
        files = [Path(arg) for arg in sys.argv[1:]]
    else:
        # Default to test files
        files = list(Path("tests/unit/marcus_mcp").glob("test_*.py"))

    for file_path in files:
        if file_path.exists():
            if update_server_imports(file_path):
                print(f"Updated: {file_path}")
            else:
                print(f"No changes: {file_path}")
        else:
            print(f"Not found: {file_path}")


if __name__ == "__main__":
    main()
