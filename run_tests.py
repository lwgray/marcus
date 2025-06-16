#!/usr/bin/env python3
"""
Test runner script for PM Agent
Provides various test running options
"""

import sys
import subprocess
import argparse


def run_command(cmd):
    """Run a command and print output"""
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def main():
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