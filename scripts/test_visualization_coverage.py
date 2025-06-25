#!/usr/bin/env python3
"""Run visualization system tests with detailed coverage reporting.

This module provides a specialized test runner for the PM Agent visualization
system, focusing on achieving and maintaining high test coverage. It runs
pytest with coverage analysis specifically for visualization components and
generates both terminal and HTML coverage reports.

The script supports:
    - Running all visualization tests with coverage analysis
    - Running specific test files with coverage
    - Automatic .coveragerc configuration generation
    - Coverage threshold checking (80% target)
    - Detailed file-by-file coverage reporting
    - HTML coverage report generation

Examples
--------
Run all visualization tests:
    $ python scripts/test_visualization_coverage.py

Run a specific test file:
    $ python scripts/test_visualization_coverage.py tests/unit/visualization/test_ui_server.py

Notes
-----
The script creates coverage reports in multiple formats:
    - Terminal output with missing line numbers
    - HTML report in htmlcov/visualization/
    - JSON report for programmatic analysis
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_tests_with_coverage() -> None:
    """Run all visualization tests with comprehensive coverage reporting.
    
    Executes pytest on the visualization test suite with coverage analysis,
    generates multiple report formats, and checks against the 80% coverage
    target. Creates .coveragerc configuration if it doesn't exist.
    
    The function performs the following steps:
        1. Creates .coveragerc configuration if missing
        2. Runs pytest with coverage on visualization tests
        3. Parses JSON coverage report for analysis
        4. Displays total coverage and per-file breakdown
        5. Checks if 80% coverage target is met
        6. Generates HTML coverage report
    
    Returns
    -------
    None
    
    Side Effects
    ------------
    - Creates .coveragerc file if it doesn't exist
    - Generates coverage reports in multiple formats:
        - coverage-visualization.json
        - htmlcov/visualization/ directory with HTML reports
    - Exits with code 1 if tests fail
    
    Raises
    ------
    SystemExit
        If tests fail or an error occurs during execution.
    """
    print("🧪 Running Visualization System Tests with Coverage...")
    print("=" * 60)
    
    # Test directory
    test_dir = project_root / "tests" / "unit" / "visualization"
    
    # Coverage configuration
    coverage_args = [
        "pytest",
        "-v",
        "--cov=src.visualization",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/visualization",
        "--cov-report=json:coverage-visualization.json",
        "--cov-config=.coveragerc",
        str(test_dir)
    ]
    
    # Create .coveragerc if it doesn't exist
    coveragerc_path = project_root / ".coveragerc"
    if not coveragerc_path.exists():
        print("📝 Creating .coveragerc configuration...")
        coveragerc_content = """[run]
source = src
omit = 
    */tests/*
    */test_*
    */__pycache__/*
    */venv/*
    */visualization-ui/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov/visualization

[json]
output = coverage-visualization.json
pretty_print = True
"""
        with open(coveragerc_path, 'w') as f:
            f.write(coveragerc_content)
    
    # Run tests
    try:
        result = subprocess.run(coverage_args, cwd=project_root)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
            
            # Parse coverage report
            coverage_json = project_root / "coverage-visualization.json"
            if coverage_json.exists():
                import json
                with open(coverage_json) as f:
                    coverage_data = json.load(f)
                
                total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                print(f"\n📊 Total Coverage: {total_coverage:.1f}%")
                
                if total_coverage >= 80:
                    print("🎉 Target coverage of 80% achieved!")
                else:
                    print(f"⚠️  Coverage is below 80% target (need {80 - total_coverage:.1f}% more)")
                
                # Show file-by-file coverage
                print("\n📁 File Coverage:")
                print("-" * 60)
                
                files = coverage_data.get("files", {})
                for file_path, file_data in sorted(files.items()):
                    if "visualization" in file_path:
                        coverage = file_data["summary"]["percent_covered"]
                        missing = file_data["summary"]["missing_lines"]
                        filename = Path(file_path).name
                        
                        status = "✅" if coverage >= 80 else "⚠️"
                        print(f"{status} {filename:<30} {coverage:>6.1f}% ({missing} lines missing)")
            
            print(f"\n📄 HTML report generated at: {project_root}/htmlcov/visualization/index.html")
            
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        sys.exit(1)


def run_specific_test_file(test_file: str) -> None:
    """Run a specific test file with coverage analysis.
    
    Executes pytest on a single test file with coverage reporting for the
    visualization module. This is useful for focused testing during development
    or debugging specific test failures.
    
    Parameters
    ----------
    test_file : str
        Path to the test file to run. Can be relative or absolute.
        
    Returns
    -------
    None
    
    Notes
    -----
    Coverage is still collected for the entire src.visualization module,
    but only the specified test file is executed. This allows you to see
    how a single test file contributes to overall coverage.
    
    Examples
    --------
    >>> run_specific_test_file("tests/unit/visualization/test_ui_server.py")
    🧪 Running tests/unit/visualization/test_ui_server.py with coverage...
    """
    print(f"🧪 Running {test_file} with coverage...")
    
    coverage_args = [
        "pytest",
        "-v",
        "--cov=src.visualization",
        "--cov-report=term-missing",
        test_file
    ]
    
    subprocess.run(coverage_args, cwd=project_root)


def main() -> None:
    """Main entry point for the visualization test coverage script.
    
    Determines whether to run all visualization tests or a specific test file
    based on command-line arguments. If no arguments are provided, runs the
    complete test suite. If a test file path is provided as the first argument,
    runs only that specific test.
    
    Returns
    -------
    None
    
    Command Line Arguments
    ----------------------
    sys.argv[1] : str, optional
        Path to a specific test file to run. If not provided, all visualization
        tests are executed.
        
    Examples
    --------
    Run all tests:
        $ python scripts/test_visualization_coverage.py
        
    Run specific test:
        $ python scripts/test_visualization_coverage.py tests/unit/visualization/test_health_monitor.py
    """
    if len(sys.argv) > 1:
        # Run specific test file
        test_file = sys.argv[1]
        run_specific_test_file(test_file)
    else:
        # Run all visualization tests
        run_tests_with_coverage()


if __name__ == "__main__":
    main()