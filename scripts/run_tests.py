#!/usr/bin/env python3
"""
Test runner script for Marcus project.

This script provides a convenient interface to run different types of tests
with proper configuration and reporting.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> int:
    """
    Run a command and return its exit code.

    Parameters
    ----------
    cmd : List[str]
        Command and arguments to run
    cwd : Optional[Path]
        Working directory for the command

    Returns
    -------
    int
        Exit code from the command
    """
    if cwd is None:
        cwd = get_project_root()

    print(f"Running: {' '.join(cmd)}")
    print(f"Working directory: {cwd}")

    try:
        result = subprocess.run(cmd, cwd=cwd, check=False)
        return result.returncode
    except FileNotFoundError as e:
        print(f"Error: Command not found: {e}")
        return 1
    except Exception as e:
        print(f"Error running command: {e}")
        return 1


def build_pytest_command(
    test_type: Optional[str] = None,
    coverage: bool = False,
    verbose: bool = False,
    parallel: Optional[str] = None,
    specific_path: Optional[str] = None,
    markers: Optional[List[str]] = None,
) -> List[str]:
    """
    Build pytest command with specified options.

    Parameters
    ----------
    test_type : Optional[str]
        Type of tests to run ('unit', 'integration', 'performance')
    coverage : bool
        Whether to include coverage reporting
    verbose : bool
        Whether to run in verbose mode
    parallel : Optional[str]
        Number of parallel workers ('auto' or specific number)
    specific_path : Optional[str]
        Specific test path to run
    markers : Optional[List[str]]
        Pytest markers to include

    Returns
    -------
    List[str]
        Complete pytest command
    """
    cmd = ["pytest"]

    # Add test path based on type
    if specific_path:
        cmd.append(specific_path)
    elif test_type == "unit":
        cmd.append("tests/unit/")
    elif test_type == "integration":
        cmd.append("tests/integration/")
    elif test_type == "performance":
        cmd.append("tests/performance/")
    elif test_type == "future":
        cmd.append("tests/future_features/")
    else:
        # Default to all tests
        cmd.append("tests/")

    # Add markers (only if explicitly provided, not based on test_type)
    if markers:
        for marker in markers:
            cmd.extend(["-m", marker])

    # Add coverage options
    if coverage:
        cmd.extend(
            [
                "--cov=src",
                "--cov-branch",
                "--cov-report=term-missing:skip-covered",
                "--cov-report=html",
                "--cov-report=xml",
                "--cov-fail-under=80",
            ]
        )

    # Add verbosity
    if verbose:
        cmd.append("-v")

    # Add parallel execution
    if parallel:
        cmd.extend(["-n", parallel])

    # Add common options
    cmd.extend(["--strict-markers", "--tb=short"])

    return cmd


def validate_test_type(test_type: str) -> bool:
    """
    Validate that the test type is supported.

    Parameters
    ----------
    test_type : str
        The test type to validate

    Returns
    -------
    bool
        True if valid, False otherwise
    """
    valid_types = {"unit", "integration", "performance", "future"}
    return test_type in valid_types


def check_environment() -> bool:
    """
    Check if the environment is properly set up for testing.

    Returns
    -------
    bool
        True if environment is ready, False otherwise
    """
    project_root = get_project_root()

    # Check if pytest is available
    try:
        subprocess.run(["pytest", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: pytest is not installed or not in PATH")
        return False

    # Check if test directory exists
    test_dir = project_root / "tests"
    if not test_dir.exists():
        print(f"Error: Test directory not found: {test_dir}")
        return False

    # Check if source directory exists
    src_dir = project_root / "src"
    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}")
        return False

    return True


def main(args: Optional[Sequence[str]] = None) -> int:
    """
    Main entry point for the test runner.

    Parameters
    ----------
    args : Optional[Sequence[str]]
        Command line arguments (for testing)

    Returns
    -------
    int
        Exit code
    """
    parser = argparse.ArgumentParser(
        description="Run Marcus tests with various options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all tests
  %(prog)s --type unit              # Run only unit tests
  %(prog)s --type integration       # Run only integration tests
  %(prog)s --coverage               # Run with coverage reporting
  %(prog)s -v                       # Run with verbose output
  %(prog)s -n auto                  # Run with parallel execution
  %(prog)s --path tests/unit/core/  # Run specific test directory
        """,
    )

    parser.add_argument(
        "--type",
        "-t",
        choices=["unit", "integration", "performance", "future"],
        help="Type of tests to run",
    )

    parser.add_argument(
        "--coverage", "-c", action="store_true", help="Run with coverage reporting"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Run with verbose output"
    )

    parser.add_argument(
        "--parallel",
        "-n",
        metavar="WORKERS",
        help="Number of parallel workers (use 'auto' for automatic)",
    )

    parser.add_argument("--path", "-p", help="Specific test path to run")

    parser.add_argument(
        "--marker",
        "-m",
        action="append",
        help="Pytest marker to include (can be used multiple times)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show command that would be run without executing it",
    )

    # Parse arguments
    parsed_args = parser.parse_args(args)

    # Validate test type if provided
    if parsed_args.type and not validate_test_type(parsed_args.type):
        print(f"Error: Invalid test type '{parsed_args.type}'")
        return 1

    # Check environment
    if not check_environment():
        return 1

    # Build pytest command
    cmd = build_pytest_command(
        test_type=parsed_args.type,
        coverage=parsed_args.coverage,
        verbose=parsed_args.verbose,
        parallel=parsed_args.parallel,
        specific_path=parsed_args.path,
        markers=parsed_args.marker,
    )

    # Show command if dry run
    if parsed_args.dry_run:
        print("Would run:")
        print(" ".join(cmd))
        return 0

    # Run the tests
    return run_command(cmd)


if __name__ == "__main__":
    sys.exit(main())
