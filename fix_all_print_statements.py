#!/usr/bin/env python3
"""
Fix all print statements in Marcus codebase to prevent MCP protocol corruption.

This script finds and replaces all print() statements with either:
1. logger calls (preferred)
2. print(..., file=sys.stderr) for startup messages
"""

import os
import re
import sys
from pathlib import Path


def fix_print_statements(file_path: Path) -> bool:
    """Fix print statements in a single file."""

    with open(file_path, "r") as f:
        content = f.read()

    original_content = content

    # Skip test files and this script
    if "test_" in file_path.name or file_path.name == "fix_all_print_statements.py":
        return False

    # Check if file has logger
    has_logger = "logger = logging.getLogger" in content
    needs_logging_import = False

    # Pattern to match print statements (excluding those already with file=)
    print_pattern = r"^(\s*)print\((.*?)\)(?!\s*#\s*nosec)"

    lines = content.split("\n")
    modified = False

    for i, line in enumerate(lines):
        # Skip lines that already have file=sys.stderr
        if "file=sys.stderr" in line:
            continue

        # Skip commented lines
        if line.strip().startswith("#"):
            continue

        # Skip lines in docstrings (rough check)
        if ">>> print" in line or "... print" in line:
            continue

        match = re.match(print_pattern, line)
        if match:
            indent = match.group(1)
            print_content = match.group(2)

            # Determine the type of message
            if any(
                word in print_content.lower()
                for word in ["error", "failed", "exception"]
            ):
                if has_logger or needs_logging_import:
                    lines[i] = f"{indent}logger.error({print_content})"
                    needs_logging_import = True
                    modified = True
                else:
                    lines[i] = f"{indent}print({print_content}, file=sys.stderr)"
                    modified = True
            elif any(word in print_content.lower() for word in ["warning", "warn"]):
                if has_logger or needs_logging_import:
                    lines[i] = f"{indent}logger.warning({print_content})"
                    needs_logging_import = True
                    modified = True
                else:
                    lines[i] = f"{indent}print({print_content}, file=sys.stderr)"
                    modified = True
            elif any(word in print_content.lower() for word in ["debug", "trace"]):
                if has_logger or needs_logging_import:
                    lines[i] = f"{indent}logger.debug({print_content})"
                    needs_logging_import = True
                    modified = True
                else:
                    lines[i] = f"{indent}print({print_content}, file=sys.stderr)"
                    modified = True
            else:
                # For info/general messages
                if has_logger or needs_logging_import:
                    lines[i] = f"{indent}logger.info({print_content})"
                    needs_logging_import = True
                    modified = True
                else:
                    lines[i] = f"{indent}print({print_content}, file=sys.stderr)"
                    modified = True

    if modified:
        content = "\n".join(lines)

        # Add logging import if needed
        if needs_logging_import and not has_logger:
            # Find where to insert the import
            import_lines = []
            other_lines = []
            in_imports = False

            for line in content.split("\n"):
                if line.startswith("import ") or line.startswith("from "):
                    in_imports = True
                    import_lines.append(line)
                elif in_imports and line.strip() == "":
                    import_lines.append(line)
                else:
                    if in_imports:
                        # Add logging import
                        import_lines.append("import logging")
                        import_lines.append("")
                        import_lines.append("logger = logging.getLogger(__name__)")
                        in_imports = False
                    other_lines.append(line)

            content = "\n".join(import_lines + other_lines)

        # Write back
        with open(file_path, "w") as f:
            f.write(content)

        print(f"Fixed {file_path}")
        return True

    return False


def main():
    """Fix all print statements in the Marcus source code."""

    src_dir = Path("/Users/lwgray/dev/marcus/src")

    fixed_count = 0

    # Files to fix based on our search
    problem_files = [
        "config/settings.py",
        "integrations/providers/github_kanban.py",
        "integrations/providers/planka.py",
        "integrations/providers/linear_kanban.py",
        "integrations/providers/planka_kanban.py",
        "integrations/kanban_client.py",
        "integrations/label_helper.py",
        "integrations/ai_analysis_engine.py",
        "core/code_analyzer.py",
        "core/workspace.py",
        "quality/project_quality_assessor.py",
        "marcus_mcp/agent_server.py",
    ]

    for file_path in problem_files:
        full_path = src_dir / file_path
        if full_path.exists():
            if fix_print_statements(full_path):
                fixed_count += 1
        else:
            print(f"File not found: {full_path}", file=sys.stderr)

    print(f"\nFixed {fixed_count} files", file=sys.stderr)

    # Also scan for any other files we might have missed
    print("\nScanning for additional files with print statements...", file=sys.stderr)

    for py_file in src_dir.rglob("*.py"):
        if py_file.name.startswith("test_"):
            continue

        with open(py_file, "r") as f:
            content = f.read()

        if "print(" in content and "file=sys.stderr" not in content:
            # Check if it's not already in our list
            relative_path = py_file.relative_to(src_dir)
            if str(relative_path) not in problem_files:
                print(
                    f"Found additional file with print statements: {relative_path}",
                    file=sys.stderr,
                )


if __name__ == "__main__":
    main()
