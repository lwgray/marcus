"""Live demonstration with REAL LLM validation (no mocking).

This script uses the actual AI to validate broken code.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from src.ai.validation.work_analyzer import WorkAnalyzer


async def demo_real_llm_validation() -> None:
    """Demonstrate validation with REAL LLM (no mocking)."""
    print("=" * 70)
    print("REAL LLM VALIDATION: Will the AI catch the broken code?")
    print("=" * 70)
    print()

    # Create a task with completion criteria
    print("📋 Task: 'Implement user registration'")
    task = Mock()
    task.id = "demo-task-456"
    task.name = "Implement user registration"
    task.description = "Create user registration with email validation"
    task.type = "implementation"
    task.completion_criteria = [
        "Form includes email, password, confirm password fields",
        "Email validation implemented",
        "Password strength validation implemented",
        "Passwords match validation implemented",
    ]
    task.dependencies = []

    for i, criterion in enumerate(task.completion_criteria, 1):
        print(f"  {i}. {criterion}")
    print()

    # Create temporary project with BROKEN code
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"🗂️  Temporary project: {tmpdir}")
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()

        # Write INCOMPLETE code with TODOs
        broken_code = """/**
 * User Registration Module - INCOMPLETE!
 */

function validateEmail(email) {
    // TODO: implement proper email validation
    return true;  // STUB - always returns true!
}

// Missing: validatePassword() function
// Missing: passwordsMatch() function
"""
        registration_file = src_dir / "registration.js"
        registration_file.write_text(broken_code)

        print("📝 Broken code created with:")
        print("   ✗ TODO comment in validateEmail")
        print("   ✗ Stub implementation (returns hardcoded true)")
        print("   ✗ Missing validatePassword() function")
        print("   ✗ Missing passwordsMatch() function")
        print()

        # Set up mock state
        mock_state = Mock()
        mock_state.task_artifacts = {}
        mock_state.workspace_manager = Mock()
        mock_state.workspace_manager.project_config = Mock()
        mock_state.workspace_manager.project_config.main_workspace = tmpdir
        mock_state.kanban_client = Mock()
        mock_state.kanban_client._load_workspace_state.return_value = None

        # Mock get_task_context (only mock this, not the AI!)
        with patch(
            "src.ai.validation.work_analyzer.get_task_context",
            new_callable=AsyncMock,
        ) as mock_context:
            mock_context.return_value = {
                "success": True,
                "context": {"decisions": []},
            }

            # Run validation with REAL LLM (no mocking _validate_with_ai!)
            print("🤖 Calling REAL LLM to validate the code...")
            print("    (This will use actual AI, not mocked responses)")
            print()

            analyzer = WorkAnalyzer()

            # NO MOCKING - Let the real LLM validate!
            result = await analyzer.validate_implementation_task(task, mock_state)

            # Display results
            print("=" * 70)
            print("REAL LLM VALIDATION RESULTS")
            print("=" * 70)
            print()
            print(f"Passed: {result.passed}")
            print(f"Issues found: {len(result.issues)}")
            print()

            if result.issues:
                print("🚨 ISSUES DETECTED BY REAL LLM:")
                print()
                for i, issue in enumerate(result.issues, 1):
                    print(f"{i}. {issue.issue}")
                    print(f"   Severity: {issue.severity.value}")
                    print(f"   Evidence: {issue.evidence}")
                    print(f"   Fix: {issue.remediation}")
                    print()
            else:
                print("✅ No issues found")

            print("=" * 70)
            print()
            if not result.passed:
                print("✅ SUCCESS: Real LLM caught the broken code!")
            else:
                print("❌ FAILURE: Real LLM did not catch the issues")


if __name__ == "__main__":
    asyncio.run(demo_real_llm_validation())
