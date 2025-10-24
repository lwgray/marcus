#!/usr/bin/env python3
"""
LLM-based Project Scoring System.

Uses an LLM to intelligently evaluate code quality, documentation,
architecture, and completeness. Provides both quantitative scores
and qualitative feedback.
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

# Add Marcus src to path
SCRIPT_DIR = Path(__file__).resolve().parent
MARCUS_ROOT = SCRIPT_DIR.parent
if str(MARCUS_ROOT) not in sys.path:
    sys.path.insert(0, str(MARCUS_ROOT))

from src.ai.providers.llm_abstraction import LLMAbstraction  # noqa: E402


class LLMContext:
    """Simple context for LLM calls."""

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens


def extract_json_from_response(response: str) -> str:
    r"""
    Extract JSON from LLM response with markdown or extra text.

    Handles responses like:
    - ```json\n{...}\n```
    - Some text before\n{...}\nSome text after
    - Plain {...}
    """
    # Remove markdown code blocks
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        response = response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        response = response[start:end].strip()

    # Find first { and last }
    first_brace = response.find("{")
    last_brace = response.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        response = response[first_brace : last_brace + 1]

    return response.strip()


@dataclass
class LLMCategoryScore:
    """Score from LLM for a category."""

    category: str
    points_earned: float
    points_possible: float
    percentage: float
    reasoning: str
    strengths: List[str]
    weaknesses: List[str]


@dataclass
class LLMProjectScore:
    """Complete LLM-based scoring."""

    project_name: str
    total_score: float
    total_possible: float
    percentage: float
    categories: List[LLMCategoryScore]
    overall_assessment: str
    recommendations: List[str]


class LLMProjectScorer:
    """LLM-based intelligent project scorer."""

    def __init__(self, project_dir: Path):
        """
        Initialize LLM scorer.

        Parameters
        ----------
        project_dir : Path
            Path to project directory to score
        """
        self.project_dir = project_dir
        self.llm = LLMAbstraction()

        # Collect all relevant files
        self.code_files = self._collect_files([".py"])
        self.doc_files = self._collect_files([".md", ".txt", ".rst"])
        self.config_files = self._collect_files([".json", ".yaml", ".toml", ".env"])

    def _collect_files(self, extensions: List[str]) -> Dict[str, str]:
        """
        Collect files with given extensions.

        Parameters
        ----------
        extensions : List[str]
            File extensions to collect (e.g., [".py", ".md"])

        Returns
        -------
        Dict[str, str]
            Mapping of relative path to file content
        """
        files = {}
        for ext in extensions:
            for f in self.project_dir.rglob(f"*{ext}"):
                # Skip venv, node_modules, etc.
                if any(
                    x in f.parts
                    for x in [".venv", "venv", ".git", "__pycache__", "node_modules"]
                ):
                    continue

                try:
                    relative_path = f.relative_to(self.project_dir)
                    files[str(relative_path)] = f.read_text()
                except Exception:  # nosec B112
                    continue

        return files

    async def score_functionality(self) -> LLMCategoryScore:
        """
        Score Category 1: Functionality using LLM.

        Returns
        -------
        LLMCategoryScore
            Functionality score with reasoning
        """
        prompt = f"""You are evaluating a DateTime API project's FUNCTIONALITY (25 points).  # noqa: E501

PROJECT FILES:
{self._format_files_summary()}

CODE CONTENT:
{self._format_code_files(max_lines=500)}

EVALUATION CRITERIA:
1. Application Runs (10 points)
   - Does the code look like it would run without errors?
   - Are imports correct and dependencies clear?
   - Is there proper entry point (main.py, app.py)?

2. Tests Exist and Pass (10 points)
   - Are there comprehensive test files?
   - Do tests look meaningful (not just stubs)?
   - Test coverage of main functionality?

3. Test Quality (5 points)
   - Are tests well-structured?
   - Do they test edge cases?
   - Good assertions and test data?

Respond in JSON format:
{{
    "score": <0-25>,
    "reasoning": "<2-3 sentence explanation>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>"]
}}

Be objective and specific. Reference actual code/files in your reasoning."""

        response = await self.llm.analyze(prompt, LLMContext())
        result = json.loads(extract_json_from_response(response))

        return LLMCategoryScore(
            category="Functionality",
            points_earned=result["score"],
            points_possible=25,
            percentage=(result["score"] / 25) * 100,
            reasoning=result["reasoning"],
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
        )

    async def score_code_quality(self) -> LLMCategoryScore:
        """Score Category 2: Code Quality using LLM."""
        prompt = f"""You are evaluating a DateTime API project's CODE QUALITY (20 points).  # noqa: E501

CODE FILES:
{self._format_code_files(max_lines=1000)}

EVALUATION CRITERIA:
1. Documentation (8 points)
   - Are functions/classes properly documented?
   - Clear docstrings with parameters/returns?
   - Helpful comments where needed?

2. Code Complexity (6 points)
   - Is code simple and readable?
   - Appropriate function sizes?
   - Good separation of concerns?

3. Code Organization (6 points)
   - Clean, maintainable structure?
   - Consistent naming conventions?
   - Good error handling patterns?

Respond in JSON format:
{{
    "score": <0-20>,
    "reasoning": "<2-3 sentence explanation>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>"]
}}

Be critical but fair. Reference specific code examples."""

        response = await self.llm.analyze(prompt, LLMContext())
        result = json.loads(extract_json_from_response(response))

        return LLMCategoryScore(
            category="Code Quality",
            points_earned=result["score"],
            points_possible=20,
            percentage=(result["score"] / 20) * 100,
            reasoning=result["reasoning"],
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
        )

    async def score_completeness(self) -> LLMCategoryScore:
        """Score Category 3: Completeness using LLM."""
        prompt = f"""You are evaluating a DateTime API project's COMPLETENESS (20 points).  # noqa: E501

REQUIRED DELIVERABLES:
- API specification document
- Data models for date/time responses
- Two endpoints: GET /api/date and GET /api/time
- Error handling implementation
- Tests for both endpoints

PROJECT FILES:
{self._format_files_summary()}

CODE:
{self._format_code_files(max_lines=500)}

EVALUATION CRITERIA:
1. Required Deliverables (10 points)
   - All 5 deliverables present and complete?
   - Not just stubs or placeholders?

2. No Stubs/Placeholders (5 points)
   - Real implementations vs TODOs?
   - No "pass" or "NotImplemented"?

3. Feature Completeness (5 points)
   - Both endpoints fully implemented?
   - All requirements met?

Respond in JSON format:
{{
    "score": <0-20>,
    "reasoning": "<2-3 sentence explanation>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>"]
}}

List specific missing items if any."""

        response = await self.llm.analyze(prompt, LLMContext())
        result = json.loads(extract_json_from_response(response))

        return LLMCategoryScore(
            category="Completeness",
            points_earned=result["score"],
            points_possible=20,
            percentage=(result["score"] / 20) * 100,
            reasoning=result["reasoning"],
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
        )

    async def score_structure(self) -> LLMCategoryScore:
        """Score Category 4: Project Structure using LLM."""
        prompt = f"""You are evaluating a DateTime API project's STRUCTURE (15 points).

PROJECT STRUCTURE:
{self._format_directory_tree()}

FILES:
{self._format_files_summary()}

EVALUATION CRITERIA:
1. Logical Organization (8 points)
   - Clear separation (models, controllers, tests, docs)?
   - Easy to navigate?
   - Follows best practices?

2. Appropriate File Count (4 points)
   - Not too monolithic (all in one file)?
   - Not over-fragmented (100 tiny files)?
   - 8-15 files is ideal for this project

3. Configuration (3 points)
   - Config separated from code?
   - Dependencies managed (requirements.txt)?

Respond in JSON format:
{{
    "score": <0-15>,
    "reasoning": "<2-3 sentence explanation>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>"]
}}

Compare to industry best practices."""

        response = await self.llm.analyze(prompt, LLMContext())
        result = json.loads(extract_json_from_response(response))

        return LLMCategoryScore(
            category="Project Structure",
            points_earned=result["score"],
            points_possible=15,
            percentage=(result["score"] / 15) * 100,
            reasoning=result["reasoning"],
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
        )

    async def score_documentation(self) -> LLMCategoryScore:
        """Score Category 5: Documentation using LLM."""
        docs_content = "\n\n".join(
            [f"=== {path} ===\n{content}" for path, content in self.doc_files.items()]
        )

        prompt = f"""You are evaluating a DateTime API project's DOCUMENTATION (12 points).  # noqa: E501

DOCUMENTATION FILES:
{docs_content if docs_content else "No documentation files found."}

EVALUATION CRITERIA:
1. PROJECT_SUCCESS.md (6 points)
   - How to run the application?
   - How to test it?
   - How it works (architecture)?
   - Comprehensive and clear?

2. API Documentation (3 points)
   - Both endpoints documented?
   - Request/response examples?
   - Error cases explained?

3. Setup Instructions (3 points)
   - Can someone follow them from zero?
   - Dependencies listed?
   - Troubleshooting included?

Respond in JSON format:
{{
    "score": <0-12>,
    "reasoning": "<2-3 sentence explanation>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>"]
}}

Judge: could a new developer use this documentation successfully?"""

        response = await self.llm.analyze(prompt, LLMContext())
        result = json.loads(extract_json_from_response(response))

        return LLMCategoryScore(
            category="Documentation",
            points_earned=result["score"],
            points_possible=12,
            percentage=(result["score"] / 12) * 100,
            reasoning=result["reasoning"],
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
        )

    async def score_usability(self) -> LLMCategoryScore:
        """Score Category 6: Usability using LLM."""
        prompt = f"""You are evaluating a DateTime API project's USABILITY (8 points).

PROJECT FILES:
{self._format_files_summary()}

MAIN CODE:
{self._format_code_files(max_lines=300)}

DOCUMENTATION:
{self._format_doc_files(max_lines=200)}

EVALUATION CRITERIA:
1. Single-Command Startup (4 points)
   - Can you run with "python main.py" or similar?
   - Clear and simple?

2. Dependencies Managed (2 points)
   - requirements.txt or similar?
   - Easy to install?

3. Example Requests (2 points)
   - Curl commands or similar provided?
   - Easy to test both endpoints?

Respond in JSON format:
{{
    "score": <0-8>,
    "reasoning": "<2-3 sentence explanation>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>"]
}}

Focus on developer experience."""

        response = await self.llm.analyze(prompt, LLMContext())
        result = json.loads(extract_json_from_response(response))

        return LLMCategoryScore(
            category="Usability",
            points_earned=result["score"],
            points_possible=8,
            percentage=(result["score"] / 8) * 100,
            reasoning=result["reasoning"],
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
        )

    async def generate_overall_assessment(
        self, categories: List[LLMCategoryScore]
    ) -> tuple[str, List[str]]:
        """
        Generate overall assessment and recommendations.

        Parameters
        ----------
        categories : List[LLMCategoryScore]
            Scored categories

        Returns
        -------
        tuple[str, List[str]]
            Overall assessment text and list of recommendations
        """
        scores_summary = "\n".join(
            [
                f"- {cat.category}: {cat.points_earned}/{cat.points_possible} "
                f"({cat.percentage:.0f}%) - {cat.reasoning}"
                for cat in categories
            ]
        )

        prompt = f"""You scored a DateTime API project across 6 categories:

{scores_summary}

Total: {sum(c.points_earned for c in categories)}/100

Based on these scores, provide:
1. A 2-3 sentence overall assessment of the project quality
2. Top 3-5 specific recommendations for improvement

Respond in JSON format:
{{
    "overall_assessment": "<your assessment>",
    "recommendations": ["<rec 1>", "<rec 2>", "<rec 3>"]
}}

Be constructive and actionable."""

        response = await self.llm.analyze(prompt, LLMContext())
        result = json.loads(extract_json_from_response(response))

        return result["overall_assessment"], result["recommendations"]

    async def score_project(self) -> LLMProjectScore:
        """
        Score the entire project using LLM evaluation.

        Returns
        -------
        LLMProjectScore
            Complete LLM-based scoring with qualitative feedback
        """
        print("Scoring with LLM (this may take 1-2 minutes)...")

        # Score each category
        categories = [
            await self.score_functionality(),
            await self.score_code_quality(),
            await self.score_completeness(),
            await self.score_structure(),
            await self.score_documentation(),
            await self.score_usability(),
        ]

        total_earned = sum(c.points_earned for c in categories)
        total_possible = sum(c.points_possible for c in categories)

        # Generate overall assessment
        assessment, recommendations = await self.generate_overall_assessment(categories)

        return LLMProjectScore(
            project_name=self.project_dir.name,
            total_score=total_earned,
            total_possible=total_possible,
            percentage=(
                (total_earned / total_possible) * 100 if total_possible > 0 else 0
            ),
            categories=categories,
            overall_assessment=assessment,
            recommendations=recommendations,
        )

    def _format_files_summary(self) -> str:
        """Format summary of all files."""
        lines = ["Python Files:"]
        for path in sorted(self.code_files.keys()):
            lines.append(f"  - {path}")

        lines.append("\nDocumentation Files:")
        for path in sorted(self.doc_files.keys()):
            lines.append(f"  - {path}")

        lines.append("\nConfiguration Files:")
        for path in sorted(self.config_files.keys()):
            lines.append(f"  - {path}")

        return "\n".join(lines)

    def _format_directory_tree(self) -> str:
        """Format directory tree structure."""
        all_files = (
            list(self.code_files.keys())
            + list(self.doc_files.keys())
            + list(self.config_files.keys())
        )

        tree_lines = []
        for path in sorted(all_files):
            parts = Path(path).parts
            indent = "  " * (len(parts) - 1)
            tree_lines.append(f"{indent}{parts[-1]}")

        return "\n".join(tree_lines)

    def _format_code_files(self, max_lines: int = 500) -> str:
        """Format code files with line limit."""
        lines: List[str] = []
        total_lines = 0

        for path, content in sorted(self.code_files.items()):
            if total_lines >= max_lines:
                lines.append(
                    f"\n... ({len(self.code_files) - len(lines)} more files) ..."
                )
                break

            lines.append(f"\n=== {path} ===")
            file_lines = content.splitlines()
            remaining = max_lines - total_lines

            if len(file_lines) <= remaining:
                lines.append(content)
                total_lines += len(file_lines)
            else:
                lines.append("\n".join(file_lines[:remaining]))
                lines.append(f"... (truncated, {len(file_lines)} total lines) ...")
                total_lines += remaining

        return "\n".join(lines)

    def _format_doc_files(self, max_lines: int = 200) -> str:
        """Format documentation files with line limit."""
        lines: List[str] = []
        total_lines = 0

        for path, content in sorted(self.doc_files.items()):
            if total_lines >= max_lines:
                lines.append(
                    f"\n... ({len(self.doc_files) - len(lines)} more files) ..."
                )
                break

            lines.append(f"\n=== {path} ===")
            file_lines = content.splitlines()
            remaining = max_lines - total_lines

            if len(file_lines) <= remaining:
                lines.append(content)
                total_lines += len(file_lines)
            else:
                lines.append("\n".join(file_lines[:remaining]))
                total_lines += remaining

        return "\n".join(lines)


async def main() -> int:
    """Run the LLM-based scoring system."""
    parser = argparse.ArgumentParser(
        description="Score a project using LLM-based intelligent evaluation"
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
    scorer = LLMProjectScorer(args.project_dir)
    result = await scorer.score_project()

    # Convert to dict
    result_dict = asdict(result)

    # Print summary
    print(f"\n{'='*70}")
    print("LLM-Based Scoring Results")
    print(f"Project: {result.project_name}")
    print(
        f"Total Score: {result.total_score:.1f}/{result.total_possible} "
        f"({result.percentage:.1f}%)"
    )
    print(f"{'='*70}\n")

    print("Overall Assessment:")
    print(f"  {result.overall_assessment}\n")

    print("Category Breakdown:")
    for category in result.categories:
        print(
            f"\n  {category.category}: {category.points_earned:.1f}/"
            f"{category.points_possible} ({category.percentage:.0f}%)"
        )
        print(f"    Reasoning: {category.reasoning}")
        if category.strengths:
            print(f"    Strengths: {', '.join(category.strengths)}")
        if category.weaknesses:
            print(f"    Weaknesses: {', '.join(category.weaknesses)}")

    print("\nRecommendations:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")

    # Save to file if requested
    if args.output_file:
        args.output_file.write_text(json.dumps(result_dict, indent=2))
        print(f"\nFull results saved to: {args.output_file}")

    return 0


if __name__ == "__main__":
    import asyncio

    exit(asyncio.run(main()))
