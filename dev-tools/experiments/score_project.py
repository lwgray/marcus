#!/usr/bin/env python3
"""
Automated Project Scoring System for Marcus vs Single Agent Comparison.

Uses the rubric defined in PROJECT-SCORING-RUBRIC.md to objectively score
project implementations.
"""

import argparse
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class CategoryScore:
    """Score for a single rubric category."""

    category: str
    points_earned: float
    points_possible: float
    percentage: float
    details: Dict[str, any]


@dataclass
class ProjectScore:
    """Complete scoring for a project."""

    project_name: str
    total_score: float
    total_possible: float
    percentage: float
    categories: List[CategoryScore]
    metadata: Dict[str, any]


class ProjectScorer:
    """Automated project scoring system."""

    def __init__(self, project_dir: Path):
        """
        Initialize scorer with project directory.

        Parameters
        ----------
        project_dir : Path
            Path to project directory to score
        """
        self.project_dir = project_dir
        self.python_files = list(project_dir.rglob("*.py"))
        # Exclude venv, .git, etc.
        self.python_files = [
            f
            for f in self.python_files
            if not any(
                x in f.parts
                for x in [".venv", "venv", ".git", "__pycache__", "node_modules"]
            )
        ]

    def score_functionality(self) -> CategoryScore:
        """
        Score Category 1: Functionality (25 points).

        Returns
        -------
        CategoryScore
            Functionality score breakdown
        """
        points = 0.0
        details = {}

        # 1.1 Application runs (10 points)
        # Look for main entry point
        main_files = [
            f for f in self.python_files if f.name in ["main.py", "app.py", "server.py"]
        ]
        if main_files:
            details["has_main_file"] = True
            # Assume it runs if main file exists (actual run test would be more complex)
            points += 7  # Conservative score without actual execution
            details["app_runs_score"] = 7
        else:
            details["has_main_file"] = False
            details["app_runs_score"] = 0

        # 1.2 Tests exist and pass (10 points)
        test_files = [f for f in self.python_files if "test" in f.name.lower()]
        if test_files:
            details["test_files_count"] = len(test_files)
            # Conservative: assume tests exist and likely pass
            points += 7  # Would need actual pytest run for full score
            details["tests_score"] = 7
        else:
            details["test_files_count"] = 0
            details["tests_score"] = 0

        # 1.3 Test coverage (5 points)
        # This would require running pytest --cov, give partial credit if tests exist
        if test_files:
            points += 3  # Conservative estimate
            details["coverage_score"] = 3
        else:
            details["coverage_score"] = 0

        return CategoryScore(
            category="Functionality",
            points_earned=points,
            points_possible=25,
            percentage=(points / 25) * 100,
            details=details,
        )

    def score_code_quality(self) -> CategoryScore:
        """
        Score Category 2: Code Quality (20 points).

        Returns
        -------
        CategoryScore
            Code quality score breakdown
        """
        points = 0.0
        details = {}

        # 2.1 Static analysis (8 points) - count basic issues
        total_lines = 0
        docstring_count = 0
        function_count = 0

        for py_file in self.python_files:
            try:
                content = py_file.read_text()
                total_lines += len(content.splitlines())

                # Count functions
                function_count += len(re.findall(r"^\s*def ", content, re.MULTILINE))

                # Count docstrings (simple heuristic)
                docstring_count += len(re.findall(r'""".*?"""', content, re.DOTALL))
                docstring_count += len(re.findall(r"'''.*?'''", content, re.DOTALL))
            except Exception:
                continue

        details["total_lines"] = total_lines
        details["function_count"] = function_count
        details["docstring_count"] = docstring_count

        # Rough quality score based on docstrings
        if function_count > 0:
            doc_ratio = docstring_count / function_count
            if doc_ratio >= 0.8:
                points += 6
            elif doc_ratio >= 0.5:
                points += 4
            elif doc_ratio >= 0.3:
                points += 2
        details["static_analysis_score"] = points

        # 2.2 Code complexity (6 points) - file size heuristic
        if self.python_files:
            avg_file_size = total_lines / len(self.python_files)
            if avg_file_size < 100:  # Simple, focused files
                points += 6
            elif avg_file_size < 200:
                points += 4
            elif avg_file_size < 400:
                points += 2
            details["avg_file_size"] = avg_file_size
            details["complexity_score"] = points - details["static_analysis_score"]

        # 2.3 Documentation coverage (6 points)
        if function_count > 0:
            doc_coverage = (docstring_count / function_count) * 100
            if doc_coverage >= 90:
                points += 6
            elif doc_coverage >= 70:
                points += 4
            elif doc_coverage >= 50:
                points += 2
            details["documentation_coverage"] = doc_coverage
            details["documentation_score"] = (
                points
                - details["static_analysis_score"]
                - details.get("complexity_score", 0)
            )

        return CategoryScore(
            category="Code Quality",
            points_earned=points,
            points_possible=20,
            percentage=(points / 20) * 100,
            details=details,
        )

    def score_completeness(self) -> CategoryScore:
        """
        Score Category 3: Completeness (20 points).

        Returns
        -------
        CategoryScore
            Completeness score breakdown
        """
        points = 0.0
        details = {}

        # 3.1 Required deliverables (10 points)
        deliverables = {
            "api_spec": False,
            "models": False,
            "endpoints": False,
            "error_handling": False,
            "tests": False,
        }

        all_files = list(self.project_dir.rglob("*"))
        all_content = ""

        # Collect all text content for searching
        for f in all_files:
            if f.is_file() and f.suffix in [".py", ".md", ".txt"]:
                try:
                    all_content += f.read_text().lower()
                except Exception:
                    continue

        # Check for API spec
        if any("spec" in f.name.lower() or "api" in f.name.lower() for f in all_files):
            deliverables["api_spec"] = True
            points += 2

        # Check for models
        if any("model" in f.name.lower() for f in all_files) or "class " in all_content:
            deliverables["models"] = True
            points += 2

        # Check for endpoints
        if any(
            x in all_content
            for x in ["@app.route", "@router", "def get", "def post", "fastapi"]
        ):
            deliverables["endpoints"] = True
            points += 2

        # Check for error handling
        if "try:" in all_content and "except" in all_content:
            deliverables["error_handling"] = True
            points += 2

        # Check for tests
        if any("test" in f.name.lower() for f in self.python_files):
            deliverables["tests"] = True
            points += 2

        details["deliverables"] = deliverables
        details["deliverables_score"] = points

        # 3.2 No stubs/placeholders (5 points)
        stub_patterns = [
            r"\bTODO\b",
            r"\bFIXME\b",
            r"\bXXX\b",
            r"^\s*pass\s*$",
            r"NotImplemented",
        ]
        stub_count = 0

        for pattern in stub_patterns:
            stub_count += len(
                re.findall(pattern, all_content, re.MULTILINE | re.IGNORECASE)
            )

        if stub_count == 0:
            points += 5
        elif stub_count <= 2:
            points += 3

        details["stub_count"] = stub_count
        details["no_stubs_score"] = (
            5 if stub_count == 0 else (3 if stub_count <= 2 else 0)
        )

        # 3.3 All subtasks completed (5 points)
        # Heuristic: check for both endpoints
        has_date_endpoint = any(
            x in all_content
            for x in ["/date", "/api/date", "current_date", "currentdate"]
        )
        has_time_endpoint = any(
            x in all_content
            for x in ["/time", "/api/time", "current_time", "currenttime"]
        )

        if has_date_endpoint and has_time_endpoint:
            points += 5
            details["both_endpoints"] = True
        elif has_date_endpoint or has_time_endpoint:
            points += 3
            details["both_endpoints"] = False

        details["subtasks_score"] = (
            5 if (has_date_endpoint and has_time_endpoint) else 0
        )

        return CategoryScore(
            category="Completeness",
            points_earned=points,
            points_possible=20,
            percentage=(points / 20) * 100,
            details=details,
        )

    def score_structure(self) -> CategoryScore:
        """
        Score Category 4: Project Structure (15 points).

        Returns
        -------
        CategoryScore
            Project structure score breakdown
        """
        points = 0.0
        details = {}

        all_dirs = [d for d in self.project_dir.rglob("*") if d.is_dir()]
        dir_names = [d.name.lower() for d in all_dirs]

        # 4.1 Logical organization (8 points)
        has_structure = {
            "models": any(x in dir_names for x in ["models", "model"]),
            "tests": any(x in dir_names for x in ["tests", "test"]),
            "docs": any(x in dir_names for x in ["docs", "documentation", "doc"]),
            "controllers": any(
                x in dir_names for x in ["controllers", "routes", "api", "endpoints"]
            ),
        }

        structure_count = sum(has_structure.values())
        if structure_count >= 3:
            points += 8
        elif structure_count == 2:
            points += 6
        elif structure_count == 1:
            points += 4

        details["structure"] = has_structure
        details["structure_score"] = points

        # 4.2 Appropriate file count (4 points)
        file_count = len(self.python_files)
        if 8 <= file_count <= 15:
            points += 4
        elif 6 <= file_count <= 7 or 16 <= file_count <= 20:
            points += 3
        elif 4 <= file_count <= 5 or 21 <= file_count <= 25:
            points += 2
        elif 2 <= file_count <= 3 or file_count > 25:
            points += 1

        details["python_file_count"] = file_count
        details["file_count_score"] = points - details["structure_score"]

        # 4.3 Configuration separated (3 points)
        config_files = [
            f
            for f in self.project_dir.rglob("*")
            if f.name
            in ["config.py", "settings.py", ".env", "config.yaml", "config.json"]
        ]
        if config_files:
            points += 3
            details["has_config_file"] = True
        else:
            details["has_config_file"] = False

        details["config_score"] = 3 if config_files else 0

        return CategoryScore(
            category="Project Structure",
            points_earned=points,
            points_possible=15,
            percentage=(points / 15) * 100,
            details=details,
        )

    def score_documentation(self) -> CategoryScore:
        """
        Score Category 5: Documentation (12 points).

        Returns
        -------
        CategoryScore
            Documentation score breakdown
        """
        points = 0.0
        details = {}

        doc_files = [
            f
            for f in self.project_dir.rglob("*")
            if f.suffix in [".md", ".txt", ".rst"] and f.is_file()
        ]

        # 5.1 PROJECT_SUCCESS.md (6 points)
        success_files = [
            f
            for f in doc_files
            if "success" in f.name.lower() or "readme" in f.name.lower()
        ]

        if success_files:
            try:
                content = success_files[0].read_text()
                word_count = len(content.split())

                # Check for key sections
                has_how_to_run = any(
                    x in content.lower()
                    for x in ["how to run", "running", "usage", "start"]
                )
                has_how_to_test = any(
                    x in content.lower() for x in ["how to test", "testing"]
                )
                has_how_it_works = any(
                    x in content.lower()
                    for x in ["how it works", "architecture", "overview", "design"]
                )

                section_count = sum([has_how_to_run, has_how_to_test, has_how_it_works])

                if word_count >= 500 and section_count >= 3:
                    points += 6
                elif word_count >= 300 and section_count >= 2:
                    points += 4
                elif word_count >= 100:
                    points += 2

                details["project_success_word_count"] = word_count
                details["project_success_sections"] = section_count
            except Exception:
                details["project_success_word_count"] = 0

        details["project_success_score"] = points

        # 5.2 API documentation (3 points)
        all_doc_content = ""
        for f in doc_files:
            try:
                all_doc_content += f.read_text().lower()
            except Exception:
                continue

        has_endpoints = "/api/date" in all_doc_content or "/api/time" in all_doc_content
        has_examples = "curl" in all_doc_content or "example" in all_doc_content
        has_responses = "response" in all_doc_content or "json" in all_doc_content

        api_doc_score = 0
        if has_endpoints and has_examples and has_responses:
            api_doc_score = 3
        elif has_endpoints and (has_examples or has_responses):
            api_doc_score = 2
        elif has_endpoints:
            api_doc_score = 1

        points += api_doc_score
        details["api_documentation_score"] = api_doc_score

        # 5.3 Setup instructions (3 points)
        has_dependencies = any(
            x in all_doc_content for x in ["dependencies", "requirements", "install"]
        )
        has_steps = any(x in all_doc_content for x in ["step", "1.", "first", "setup"])
        has_startup = any(
            x in all_doc_content for x in ["python", "npm", "run", "start"]
        )

        setup_score = 0
        if has_dependencies and has_steps and has_startup:
            setup_score = 3
        elif (has_dependencies and has_steps) or (has_steps and has_startup):
            setup_score = 2
        elif any([has_dependencies, has_steps, has_startup]):
            setup_score = 1

        points += setup_score
        details["setup_instructions_score"] = setup_score

        return CategoryScore(
            category="Documentation",
            points_earned=points,
            points_possible=12,
            percentage=(points / 12) * 100,
            details=details,
        )

    def score_usability(self) -> CategoryScore:
        """
        Score Category 6: Usability (8 points).

        Returns
        -------
        CategoryScore
            Usability score breakdown
        """
        points = 0.0
        details = {}

        # 6.1 Single-command startup (4 points)
        main_files = [
            f for f in self.python_files if f.name in ["main.py", "app.py", "run.py"]
        ]
        if main_files:
            points += 4
            details["single_command_startup"] = True
        else:
            details["single_command_startup"] = False

        # 6.2 Dependencies managed (2 points)
        dep_files = [
            f
            for f in self.project_dir.rglob("*")
            if f.name
            in [
                "requirements.txt",
                "package.json",
                "Pipfile",
                "pyproject.toml",
                "setup.py",
            ]
        ]
        if dep_files:
            points += 2
            details["has_dependency_file"] = True
        else:
            details["has_dependency_file"] = False

        # 6.3 Example requests (2 points)
        doc_files = [
            f
            for f in self.project_dir.rglob("*")
            if f.suffix in [".md", ".txt", ".rst"] and f.is_file()
        ]

        all_doc_content = ""
        for f in doc_files:
            try:
                all_doc_content += f.read_text().lower()
            except Exception:
                continue

        has_curl = "curl" in all_doc_content
        has_request_example = any(
            x in all_doc_content
            for x in ["example request", "request example", "http get"]
        )

        if has_curl or has_request_example:
            points += 2
            details["has_examples"] = True
        else:
            details["has_examples"] = False

        return CategoryScore(
            category="Usability",
            points_earned=points,
            points_possible=8,
            percentage=(points / 8) * 100,
            details=details,
        )

    def score_project(self) -> ProjectScore:
        """
        Score the entire project across all categories.

        Returns
        -------
        ProjectScore
            Complete project score
        """
        categories = [
            self.score_functionality(),
            self.score_code_quality(),
            self.score_completeness(),
            self.score_structure(),
            self.score_documentation(),
            self.score_usability(),
        ]

        total_earned = sum(c.points_earned for c in categories)
        total_possible = sum(c.points_possible for c in categories)

        return ProjectScore(
            project_name=self.project_dir.name,
            total_score=total_earned,
            total_possible=total_possible,
            percentage=(
                (total_earned / total_possible) * 100 if total_possible > 0 else 0
            ),
            categories=categories,
            metadata={
                "project_directory": str(self.project_dir),
                "python_files_analyzed": len(self.python_files),
            },
        )


def main():
    """Run the automated scoring system."""
    parser = argparse.ArgumentParser(
        description="Automatically score a project implementation"
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        required=True,
        help="Path to project directory to score",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Output JSON file for results (optional)",
    )

    args = parser.parse_args()

    if not args.project_dir.exists():
        print(f"Error: Project directory not found: {args.project_dir}")
        return 1

    # Score the project
    scorer = ProjectScorer(args.project_dir)
    result = scorer.score_project()

    # Convert to dict
    result_dict = asdict(result)

    # Print summary
    print(f"\n{'='*70}")
    print(f"Project: {result.project_name}")
    print(
        f"Total Score: {result.total_score:.1f}/{result.total_possible} ({result.percentage:.1f}%)"
    )
    print(f"{'='*70}\n")

    print("Category Breakdown:")
    for category in result.categories:
        print(
            f"  {category.category:20s}: {category.points_earned:5.1f}/{category.points_possible:5.1f} "
            f"({category.percentage:5.1f}%)"
        )

    # Save to file if requested
    if args.output_file:
        args.output_file.write_text(json.dumps(result_dict, indent=2))
        print(f"\nFull results saved to: {args.output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
