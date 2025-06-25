#!/usr/bin/env python3
"""Test runner script for PM Agent.

This module provides a comprehensive test runner for the PM Agent project,
supporting different test types (unit, integration, kanban-specific), coverage
reporting, and various pytest options. It acts as a wrapper around pytest with
project-specific configurations and conveniences.

The test runner supports:
    - Running all tests or specific test categories
    - Coverage reporting with HTML and terminal output
    - Verbose mode for detailed test output
    - Running specific test files
    - Automatic pytest installation if missing

Examples
--------
Run all tests:
    $ python scripts/run_tests.py

Run only unit tests with coverage:
    $ python scripts/run_tests.py --type unit --coverage

Run a specific test file:
    $ python scripts/run_tests.py --file tests/unit/test_project_manager.py

Run quick tests (unit only, stop on first failure):
    $ python scripts/run_tests.py --type quick

Notes
-----
The script automatically installs pytest if it's not available, ensuring
a smooth developer experience.
"""

import sys
import subprocess
import argparse
from typing import List, Optional


def run_command(cmd: List[str]) -> int:
    """Run a command and display its output.
    
    Executes a command using subprocess.run, displaying the command being run
    and its output in real-time. This provides transparency about what the
    test runner is doing.
    
    Parameters
    ----------
    cmd : List[str]
        The command and its arguments to execute, as a list of strings.
        
    Returns
    -------
    int
        The return code from the executed command. 0 indicates success,
        non-zero indicates failure.
        
    Examples
    --------
    >>> exit_code = run_command(["python", "-m", "pytest", "-v"])
    >>> if exit_code == 0:
    ...     print("Tests passed!")
    """
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def main() -> int:
    """Main entry point for the test runner.
    
    Parses command-line arguments and runs pytest with the appropriate
    configuration based on user options. Handles test type selection,
    coverage reporting, verbosity levels, and specific file execution.
    
    Returns
    -------
    int
        Exit code from pytest execution. 0 indicates all tests passed,
        non-zero indicates test failures or errors.
        
    Notes
    -----
    The function performs the following steps:
        1. Parse command-line arguments
        2. Build pytest command with appropriate options
        3. Check for pytest installation (install if missing)
        4. Execute tests
        5. Display results and coverage report if applicable
        
    Available test types:
        - all: Run all tests (default)
        - unit: Run only unit tests
        - integration: Run only integration tests
        - kanban: Run kanban-specific integration tests
        - quick: Run unit tests with stop-on-first-failure
    """
    parser = argparse.ArgumentParser(description="Run PM Agent tests")
    parser.add_argument(
        "--type",
        choices=["all", "unit", "integration", "kanban", "quick"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--file",
        help="Run specific test file"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing"])
    
    # Select tests based on type
    if args.file:
        cmd.append(args.file)
    elif args.type == "unit":
        cmd.extend(["-m", "unit", "tests/unit/"])
    elif args.type == "integration":
        cmd.extend(["-m", "integration", "tests/integration/"])
    elif args.type == "kanban":
        cmd.extend(["-m", "kanban", "tests/integration/"])
    elif args.type == "quick":
        # Quick tests - only unit tests
        cmd.extend(["-m", "unit", "tests/unit/", "-x"])  # -x stops on first failure
    else:
        # Run all tests
        cmd.append("tests/")
    
    # Additional pytest options
    cmd.extend(["-s"])  # Don't capture output
    
    print("🧪 PM Agent Test Runner")
    print("=" * 60)
    
    # Check if pytest is installed
    try:
        subprocess.run(["python", "-m", "pytest", "--version"], 
                      capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ pytest not installed. Installing test dependencies...")
        run_command(["pip", "install", "-r", "requirements.txt"])
    
    # Run the tests
    exit_code = run_command(cmd)
    
    if args.coverage and exit_code == 0:
        print("\n📊 Coverage report generated in htmlcov/index.html")
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())