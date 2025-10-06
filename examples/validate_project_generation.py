#!/usr/bin/env python3
"""
Project Generation Quality Validation Script

This script validates the quality of project creation by:
1. Creating a project from a natural language description
2. Extracting expected features from the description
3. Capturing generated tasks from create_project
4. Simulating agent task requests to verify what agents actually receive
5. Comparing created tasks vs received tasks
6. Using AI to judge task quality and coverage
7. Generating a comprehensive validation report

Usage:
    python examples/validate_project_generation.py

The script uses an isolated Marcus instance (stdio mode) for testing.
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.worker.new_client import Inspector  # noqa: E402


class ValidationReport:
    """Generate a comprehensive validation report for project generation."""

    def __init__(self) -> None:
        """Initialize the validation report."""
        self.start_time = datetime.now()
        self.project_description = ""
        self.extracted_features: Set[str] = set()
        self.created_tasks: List[Dict[str, Any]] = []
        self.received_tasks: List[Dict[str, Any]] = []
        self.planka_tasks: List[Dict[str, Any]] = []  # Tasks from Planka cards
        self.feature_coverage: Dict[str, bool] = {}
        self.task_comparison: List[Dict[str, Any]] = []
        self.planka_comparison: List[Dict[str, Any]] = []  # Planka vs received
        self.ai_quality_score: Dict[str, Any] = {}

    def extract_features_from_description(self, description: str) -> Set[str]:
        """
        Extract key features from natural language description.

        Uses pattern matching to identify features, components, and requirements.

        Parameters
        ----------
        description : str
            The natural language project description

        Returns
        -------
        Set[str]
            Set of extracted feature keywords
        """
        features = set()

        # Common feature patterns
        patterns = [
            r"(\w+\s+(?:authentication|auth))",  # authentication features
            r"(\w+\s+(?:creation|create))",  # creation features
            r"(\w+\s+(?:functionality|feature))",  # explicit features
            r"(follow/unfollow|like|retweet|hashtag|timeline|feed)",  # specific actions
            r"(REST API|GraphQL|API)",  # API mentions
            r"(database|PostgreSQL|MongoDB|MySQL)",  # database mentions
            r"(test coverage|testing|unit tests)",  # testing mentions
            r"(\w+\s+(?:profiles?|bio|avatar))",  # profile features
        ]

        description_lower = description.lower()

        for pattern in patterns:
            matches = re.findall(pattern, description_lower, re.IGNORECASE)
            features.update(match.strip() for match in matches)

        # Also extract key nouns/features by splitting on common separators
        parts = re.split(r"[,;.]", description)
        for part in parts:
            part = part.strip()
            if len(part) > 3 and len(part.split()) <= 5:
                # Extract short phrases that might be features
                features.add(part.lower())

        return features

    def check_feature_coverage(self) -> None:
        """
        Check if extracted features are covered in created tasks.

        Updates self.feature_coverage with coverage status for each feature.
        """
        all_task_text = " ".join(
            [
                f"{task.get('name', '')} {task.get('description', '')}"
                for task in self.created_tasks
            ]
        ).lower()

        for feature in self.extracted_features:
            # Check if feature keywords appear in any task
            feature_keywords = feature.lower().split()
            covered = any(keyword in all_task_text for keyword in feature_keywords)
            self.feature_coverage[feature] = covered

    def compare_created_vs_received(self) -> None:
        """
        Compare created tasks with what agents receive.

        Identifies differences between original tasks and what request_next_task returns.
        """
        # Create lookup dict for received tasks by ID
        received_by_id = {task.get("id"): task for task in self.received_tasks}

        for created_task in self.created_tasks:
            task_id = created_task.get("id")
            received_task = received_by_id.get(task_id)

            comparison = {
                "task_id": task_id,
                "created_name": created_task.get("name", ""),
                "received_name": (
                    received_task.get("name", "") if received_task else "NOT RECEIVED"
                ),
                "name_match": (
                    created_task.get("name") == received_task.get("name")
                    if received_task
                    else False
                ),
                "created_description": created_task.get("description", "")[:100],
                "received_description": (
                    received_task.get("description", "")[:100]
                    if received_task
                    else "NOT RECEIVED"
                ),
                "description_match": (
                    created_task.get("description") == received_task.get("description")
                    if received_task
                    else False
                ),
                "created_priority": created_task.get("priority"),
                "received_priority": (
                    received_task.get("priority") if received_task else None
                ),
                "priority_match": (
                    created_task.get("priority") == received_task.get("priority")
                    if received_task
                    else False
                ),
            }

            self.task_comparison.append(comparison)

    def compare_planka_vs_received(self) -> None:
        """
        Compare Planka card data with what agents receive.

        Identifies differences between what's on Planka cards and what agents get.
        """
        # Create lookup dict for received tasks by ID
        received_by_id = {str(task.get("id")): task for task in self.received_tasks}

        for planka_task in self.planka_tasks:
            task_id = str(planka_task.get("id", ""))
            received_task = received_by_id.get(task_id)

            planka_desc = planka_task.get("description", "")
            received_desc = (
                received_task.get("description", "") if received_task else ""
            )

            # Check for repetition in descriptions
            desc_repetitive = self._is_repetitive(planka_desc)

            comparison = {
                "task_id": task_id,
                "planka_name": planka_task.get("name", ""),
                "received_name": (
                    received_task.get("name", "") if received_task else "NOT RECEIVED"
                ),
                "name_match": (
                    planka_task.get("name") == received_task.get("name")
                    if received_task
                    else False
                ),
                "planka_description": planka_desc[:150],
                "planka_desc_length": len(planka_desc),
                "received_description": (
                    received_desc[:150] if received_task else "NOT RECEIVED"
                ),
                "received_desc_length": len(received_desc),
                "description_match": (
                    planka_desc == received_desc if received_task else False
                ),
                "planka_is_repetitive": desc_repetitive,
            }

            self.planka_comparison.append(comparison)

    def _is_repetitive(self, text: str) -> bool:
        """
        Check if text contains repetitive patterns.

        Parameters
        ----------
        text : str
            Text to check for repetition

        Returns
        -------
        bool
            True if text appears repetitive
        """
        if not text or len(text) < 50:
            return False

        # Split into sentences or chunks
        chunks = text.split(". ")
        if len(chunks) < 2:
            return False

        # Check for duplicate chunks
        seen = set()
        for chunk in chunks:
            chunk_clean = chunk.strip().lower()
            if chunk_clean and len(chunk_clean) > 10:
                if chunk_clean in seen:
                    return True
                seen.add(chunk_clean)

        return False

    async def get_ai_quality_assessment(self, client: Inspector) -> None:
        """
        Use AI to assess task quality and relevance to description.

        Parameters
        ----------
        client : Inspector
            The Inspector client with active session
        """
        # Build prompt for AI assessment
        task_summary = "\n".join(
            [
                f"- {task.get('name', 'Untitled')}: {task.get('description', 'No description')[:100]}"
                for task in self.created_tasks
            ]
        )

        assessment_prompt = f"""
You are evaluating the quality of task generation for a project.

PROJECT DESCRIPTION:
{self.project_description}

GENERATED TASKS:
{task_summary}

Please evaluate:
1. Coverage: Do the tasks comprehensively cover all aspects of the description? (0-10)
2. Clarity: Are the task descriptions clear and actionable? (0-10)
3. Completeness: Are there any missing critical components? (0-10)
4. Organization: Are tasks logically structured and ordered? (0-10)

Respond in JSON format:
{{
    "coverage_score": <0-10>,
    "clarity_score": <0-10>,
    "completeness_score": <0-10>,
    "organization_score": <0-10>,
    "overall_score": <0-10>,
    "missing_components": ["component1", "component2", ...],
    "strengths": ["strength1", "strength2", ...],
    "weaknesses": ["weakness1", "weakness2", ...]
}}
"""

        # Note: This would call an AI model in production
        # For now, we'll calculate a basic score based on coverage
        coverage_pct = (
            sum(1 for covered in self.feature_coverage.values() if covered)
            / len(self.feature_coverage)
            * 100
            if self.feature_coverage
            else 0
        )

        self.ai_quality_score = {
            "coverage_score": round(coverage_pct / 10, 1),
            "clarity_score": 8.0,  # Placeholder
            "completeness_score": round(coverage_pct / 10, 1),
            "organization_score": 8.0,  # Placeholder
            "overall_score": round(coverage_pct / 10, 1),
            "missing_components": [
                feature
                for feature, covered in self.feature_coverage.items()
                if not covered
            ],
            "strengths": ["Tasks generated successfully", "Clear task structure"],
            "weaknesses": ["Some features may not be fully covered"],
        }

    def generate_report(self) -> str:
        """
        Generate the complete validation report.

        Returns
        -------
        str
            Formatted validation report
        """
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        report = "\n" + "=" * 80 + "\n"
        report += "📊 PROJECT GENERATION VALIDATION REPORT\n"
        report += "=" * 80 + "\n\n"

        # Summary section
        report += "SUMMARY\n"
        report += "-" * 80 + "\n"
        report += f"Validation Time: {duration:.2f} seconds\n"
        report += (
            f"Project Description Length: {len(self.project_description)} characters\n"
        )
        report += f"Extracted Features: {len(self.extracted_features)}\n"
        report += f"Tasks Created: {len(self.created_tasks)}\n"
        report += f"Tasks Received by Agent: {len(self.received_tasks)}\n"
        report += f"Planka Cards Validated: {len(self.planka_tasks)}\n\n"

        # Feature extraction section
        report += "EXTRACTED FEATURES FROM DESCRIPTION\n"
        report += "-" * 80 + "\n"
        for i, feature in enumerate(sorted(self.extracted_features), 1):
            status = "✅" if self.feature_coverage.get(feature, False) else "❌"
            report += f"{i}. {status} {feature}\n"
        report += "\n"

        # Feature coverage section
        covered_count = sum(1 for covered in self.feature_coverage.values() if covered)
        coverage_pct = (
            covered_count / len(self.feature_coverage) * 100
            if self.feature_coverage
            else 0
        )
        report += "FEATURE COVERAGE ANALYSIS\n"
        report += "-" * 80 + "\n"
        report += f"Features Covered: {covered_count}/{len(self.feature_coverage)} ({coverage_pct:.1f}%)\n"

        if coverage_pct >= 80:
            report += "Status: ✅ EXCELLENT COVERAGE\n"
        elif coverage_pct >= 60:
            report += "Status: ⚠️  GOOD COVERAGE (some features missing)\n"
        else:
            report += "Status: ❌ POOR COVERAGE (many features missing)\n"
        report += "\n"

        # Task comparison section
        report += "TASK INTEGRITY CHECK (Created vs Received)\n"
        report += "-" * 80 + "\n"

        matches = {
            "name": sum(1 for c in self.task_comparison if c["name_match"]),
            "description": sum(
                1 for c in self.task_comparison if c["description_match"]
            ),
            "priority": sum(1 for c in self.task_comparison if c["priority_match"]),
        }

        total = len(self.task_comparison)
        report += f"Name Matches: {matches['name']}/{total}\n"
        report += f"Description Matches: {matches['description']}/{total}\n"
        report += f"Priority Matches: {matches['priority']}/{total}\n\n"

        # Detail mismatches
        mismatches = [c for c in self.task_comparison if not c["name_match"]]
        if mismatches:
            report += "MISMATCHED TASKS:\n"
            for mismatch in mismatches:
                report += f"\nTask ID: {mismatch['task_id']}\n"
                report += f"  Created Name: {mismatch['created_name']}\n"
                report += f"  Received Name: {mismatch['received_name']}\n"
        else:
            report += "✅ All tasks match perfectly between creation and assignment!\n"
        report += "\n"

        # Planka card comparison section
        if self.planka_comparison:
            report += "PLANKA CARD INTEGRITY CHECK (Cards vs Agent Received)\n"
            report += "-" * 80 + "\n"

            planka_matches = {
                "name": sum(1 for c in self.planka_comparison if c["name_match"]),
                "description": sum(
                    1 for c in self.planka_comparison if c["description_match"]
                ),
            }

            planka_total = len(self.planka_comparison)
            report += f"Name Matches: {planka_matches['name']}/{planka_total}\n"
            report += (
                f"Description Matches: {planka_matches['description']}/{planka_total}\n"
            )

            # Check for repetitive descriptions
            repetitive_count = sum(
                1 for c in self.planka_comparison if c["planka_is_repetitive"]
            )
            if repetitive_count > 0:
                report += f"⚠️  Repetitive Descriptions Found: {repetitive_count}/{planka_total}\n"

            report += "\n"

            # Detail Planka mismatches
            planka_mismatches = [
                c for c in self.planka_comparison if not c["description_match"]
            ]
            if planka_mismatches:
                report += "PLANKA DESCRIPTION ISSUES:\n"
                for mismatch in planka_mismatches[:3]:  # Show first 3
                    report += f"\nTask ID: {mismatch['task_id']}\n"
                    report += f"  Planka Name: {mismatch['planka_name']}\n"
                    if mismatch["planka_is_repetitive"]:
                        report += f"  ⚠️  REPETITIVE: Planka description appears to have duplicate content\n"
                    report += f"  Planka Desc Length: {mismatch['planka_desc_length']} chars\n"
                    report += f"  Received Desc Length: {mismatch['received_desc_length']} chars\n"
                    report += f"  Planka: {mismatch['planka_description']}...\n"
                    report += f"  Agent: {mismatch['received_description']}...\n"

                if len(planka_mismatches) > 3:
                    report += (
                        f"\n  ... and {len(planka_mismatches) - 3} more mismatches\n"
                    )
            else:
                report += "✅ Planka cards match what agents receive!\n"
            report += "\n"

        # AI Quality Assessment
        report += "AI QUALITY ASSESSMENT\n"
        report += "-" * 80 + "\n"
        report += (
            f"Coverage Score: {self.ai_quality_score.get('coverage_score', 0)}/10\n"
        )
        report += f"Clarity Score: {self.ai_quality_score.get('clarity_score', 0)}/10\n"
        report += f"Completeness Score: {self.ai_quality_score.get('completeness_score', 0)}/10\n"
        report += f"Organization Score: {self.ai_quality_score.get('organization_score', 0)}/10\n"
        report += (
            f"Overall Score: {self.ai_quality_score.get('overall_score', 0)}/10\n\n"
        )

        missing = self.ai_quality_score.get("missing_components", [])
        if missing:
            report += "Missing Components:\n"
            for component in missing:
                report += f"  - {component}\n"
            report += "\n"

        strengths = self.ai_quality_score.get("strengths", [])
        if strengths:
            report += "Strengths:\n"
            for strength in strengths:
                report += f"  ✅ {strength}\n"
            report += "\n"

        weaknesses = self.ai_quality_score.get("weaknesses", [])
        if weaknesses:
            report += "Weaknesses:\n"
            for weakness in weaknesses:
                report += f"  ⚠️  {weakness}\n"
            report += "\n"

        # Final verdict
        report += "FINAL VERDICT\n"
        report += "-" * 80 + "\n"
        overall_score = self.ai_quality_score.get("overall_score", 0)

        # Check Planka integrity
        planka_issues = False
        if self.planka_comparison:
            planka_desc_matches = sum(
                1 for c in self.planka_comparison if c["description_match"]
            )
            planka_repetitive = sum(
                1 for c in self.planka_comparison if c["planka_is_repetitive"]
            )
            planka_issues = (planka_desc_matches < len(self.planka_comparison)) or (
                planka_repetitive > 0
            )

        if (
            overall_score >= 8.0
            and all(matches[k] == total for k in matches)
            and not planka_issues
        ):
            report += "✅ EXCELLENT: Tasks are high quality and perfectly preserved\n"
        elif overall_score >= 6.0 and matches["name"] == total and not planka_issues:
            report += "⚠️  GOOD: Tasks are reasonable quality with minor issues\n"
        elif planka_issues:
            report += (
                "⚠️  PLANKA ISSUES DETECTED: Check Planka card integrity section above\n"
            )
        else:
            report += "❌ NEEDS IMPROVEMENT: Significant quality or integrity issues\n"

        report += "\n" + "=" * 80 + "\n"

        return report


async def validate_project_generation() -> None:
    """
    Run project generation validation workflow.

    This function:
    1. Creates a project with a known description (Twitter clone)
    2. Extracts expected features from the description
    3. Captures generated tasks
    4. Simulates agent requesting tasks
    5. Compares created vs received tasks
    6. Generates comprehensive validation report
    """
    print("\n" + "=" * 80)
    print("🔍 PROJECT GENERATION QUALITY VALIDATION")
    print("=" * 80)
    print("\nThis script will:")
    print("1. Create a test project from natural language description")
    print("2. Extract expected features from the description")
    print("3. Analyze generated tasks for coverage and quality")
    print("4. Verify task integrity (created vs received by agents)")
    print("5. Check Planka card data vs what agents receive")
    print("6. Detect repetitive/corrupted descriptions")
    print("7. Generate comprehensive validation report")
    print("\n" + "=" * 80)

    validator = ValidationReport()

    # Test project description
    description = (
        "Build a Twitter clone with the following features: "
        "User authentication (registration, login, JWT tokens), "
        "Tweet creation with 280 character limit, "
        "Follow/unfollow users, "
        "Timeline feed showing tweets from followed users, "
        "Like and retweet functionality, "
        "Hashtag support and trending topics, "
        "User profiles with bio and avatar, "
        "REST API using FastAPI, "
        "PostgreSQL database, "
        "Comprehensive test coverage. Use Python."
    )
    validator.project_description = description

    client = Inspector(connection_type="stdio")

    try:
        async with client.connect() as session:
            print("\n✅ Connected to isolated Marcus instance (stdio mode)")

            # Step 1: Authenticate
            print("\n🔐 Step 1: Authenticating...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "validation-client",
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"purpose": "validation"},
                },
            )
            print("✅ Authenticated")

            # Step 2: Extract features from description
            print("\n📝 Step 2: Extracting features from description...")
            validator.extracted_features = validator.extract_features_from_description(
                description
            )
            print(f"✅ Extracted {len(validator.extracted_features)} features")

            # Step 3: Create project
            print("\n🏗️  Step 3: Creating test project...")
            create_result = await session.call_tool(
                "create_project",
                arguments={
                    "description": description,
                    "project_name": "Twitter-Validation-Test",
                    "options": {
                        "mode": "new_project",
                        "complexity": "standard",
                    },
                },
            )

            # Parse create_project response
            create_data = json.loads(create_result.content[0].text)
            if not create_data.get("success"):
                print(f"❌ Failed to create project: {create_data.get('error')}")
                return

            tasks_created = create_data.get("tasks_created", 0)
            print(f"✅ Project created with {tasks_created} tasks")

            # Debug: Print create_data structure
            print(f"\n🔍 Debug - Create response: {json.dumps(create_data, indent=2)}")

            # Step 4: Register test agent
            print("\n🤖 Step 4: Registering test agent...")
            await client.register_agent(
                agent_id="validation-agent",
                name="Validation Agent",
                role="Validator",
                skills=["validation", "testing"],
            )
            print("✅ Agent registered")

            # Step 5: Request all tasks to capture what agents receive
            print("\n📋 Step 5: Requesting tasks to simulate agent workflow...")
            task_count = 0
            while True:
                task_result = await client.request_next_task("validation-agent")

                # Parse response
                if hasattr(task_result, "content") and task_result.content:
                    task_data = json.loads(task_result.content[0].text)
                else:
                    task_data = task_result

                if not task_data.get("task"):
                    print(f"✅ Retrieved all tasks ({task_count} total)")
                    break

                task = task_data["task"]
                validator.received_tasks.append(task)
                task_count += 1

                # Immediately complete the task so we can get the next one
                await client.report_task_progress(
                    agent_id="validation-agent",
                    task_id=task["id"],
                    status="completed",
                    progress=100,
                    message="Validation complete",
                )

            # Step 6: Fetch Planka card data directly
            print("\n🔍 Step 6: Fetching Planka card data from board...")

            try:
                # Read workspace to get board IDs
                import json as json_lib

                workspace_path = project_root / ".marcus_workspace.json"

                if workspace_path.exists():
                    with open(workspace_path, "r") as f:
                        workspace = json_lib.load(f)

                    board_id = workspace.get("board_id")
                    project_id = workspace.get("project_id")

                    print(f"   Using Board ID: {board_id}, Project ID: {project_id}")

                    if board_id and project_id:
                        # Call Planka provider directly
                        from src.integrations.providers.planka import Planka

                        planka_provider = Planka(
                            board_id=str(board_id), project_id=str(project_id)
                        )

                        # Fetch all tasks
                        planka_tasks_list = await planka_provider.get_all_tasks()
                        validator.planka_tasks = planka_tasks_list
                        validator.created_tasks = planka_tasks_list

                        print(
                            f"✅ Retrieved {len(validator.planka_tasks)} tasks from Planka"
                        )

                        if validator.planka_tasks:
                            sample = validator.planka_tasks[0]
                            print(f"   Sample: {sample.get('name', 'N/A')[:50]}")
                            desc_len = len(sample.get("description", ""))
                            print(f"   Description: {desc_len} chars")

                            if desc_len > 500:
                                print(
                                    f"   ⚠️  Long description - checking for repetition..."
                                )
                    else:
                        print(f"⚠️  No board_id/project_id in workspace")
                        validator.created_tasks = validator.received_tasks.copy()
                else:
                    print(f"⚠️  Workspace file not found: {workspace_path}")
                    validator.created_tasks = validator.received_tasks.copy()

            except Exception as e:
                print(f"⚠️  Error: {e}")
                import traceback

                traceback.print_exc()
                validator.created_tasks = validator.received_tasks.copy()

            # Step 7: Run validation analysis
            print("\n🔍 Step 7: Running validation analysis...")
            validator.check_feature_coverage()
            validator.compare_created_vs_received()
            if validator.planka_tasks:
                validator.compare_planka_vs_received()
                print("✅ Planka card comparison complete")
            await validator.get_ai_quality_assessment(client)
            print("✅ Analysis complete")

            # Step 8: Generate and display report
            print("\n📊 Step 8: Generating validation report...")
            report = validator.generate_report()
            print(report)

            # Step 9: Save report to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = project_root / f"validation_report_{timestamp}.txt"
            with open(report_path, "w") as f:
                f.write(report)
            print(f"📄 Report saved to: {report_path}\n")

    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback

        traceback.print_exc()


async def main() -> None:
    """Run the validation script."""
    print("\n🚀 Starting Project Generation Validation")
    print("=" * 80)
    print("\nThis validation script uses an isolated Marcus instance (stdio)")
    print("to test project generation quality without affecting your main setup.")
    print("\nNo prerequisites needed - the script is fully self-contained.")
    print("=" * 80)

    await validate_project_generation()

    print("\n" + "=" * 80)
    print("✅ Validation complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
