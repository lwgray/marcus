"""
Integration tests for Requirement Divergence Analyzer with real AI.

These tests use actual LLM calls, so they:
- Require valid API keys in config_marcus.json
- Take longer to run (actual API calls)
- Cost money (uses LLM tokens)
- Are marked with @pytest.mark.integration

To run these tests:
    pytest tests/integration/analysis/test_requirement_divergence_live.py -v -m integration

To skip them (default):
    pytest -v  # Won't run integration tests by default
"""

from datetime import datetime, timezone

import pytest

from src.analysis.aggregator import TaskHistory
from src.analysis.analyzers.requirement_divergence import (
    RequirementDivergenceAnalyzer,
)
from src.core.project_history import ArtifactMetadata, Decision


@pytest.mark.integration
class TestRequirementDivergenceWithRealAI:
    """Integration tests using real LLM calls."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer with real AI engine."""
        return RequirementDivergenceAnalyzer()

    @pytest.mark.asyncio
    async def test_detect_critical_divergence_oauth_to_jwt(self, analyzer):
        """
        Test detection of critical divergence: OAuth2 → JWT.

        This is the example from Phase 2 spec where implementation
        fundamentally changed authentication strategy.
        """
        # Arrange - Task required OAuth2
        task = TaskHistory(
            task_id="task-auth-001",
            name="Implement user authentication",
            description=(
                "Implement user login with OAuth2 authentication using GitHub provider. "
                "Users should be redirected to GitHub, authorize the app, and return "
                "with an access token."
            ),
            status="completed",
            estimated_hours=8.0,
            actual_hours=6.0,
        )

        # Decision to use JWT instead
        decision = Decision(
            decision_id="dec-auth-001",
            task_id="task-auth-001",
            agent_id="agent-worker-1",
            timestamp=datetime(2025, 11, 4, 10, 15, tzinfo=timezone.utc),
            what="Use JWT authentication instead of OAuth2",
            why="Simpler to implement, fewer external dependencies",
            impact="major",
            affected_tasks=[],
            confidence=0.8,
        )

        # Artifact showing JWT implementation
        artifact = ArtifactMetadata(
            artifact_id="art-auth-001",
            task_id="task-auth-001",
            agent_id="agent-worker-1",
            timestamp=datetime(2025, 11, 4, 11, 30, tzinfo=timezone.utc),
            artifact_type="code",
            filename="login.py",
            relative_path="src/auth/login.py",
            absolute_path="/project/src/auth/login.py",
            description=(
                "Login endpoint implementation. "
                "Lines 45-67: POST /login endpoint accepting username/password, "
                "returns JWT token. Uses bcrypt for password verification."
            ),
            file_size_bytes=2048,
            sha256_hash="abc123def456",
        )

        # Act
        print("\n" + "=" * 60)
        print("Testing: OAuth2 → JWT divergence detection")
        print("=" * 60)

        analysis = await analyzer.analyze_task(
            task=task,
            decisions=[decision],
            artifacts=[artifact],
        )

        # Assert
        print(f"\nFidelity Score: {analysis.fidelity_score:.2f}")
        print(f"Divergences Found: {len(analysis.divergences)}")

        # Should detect significant divergence (not perfect match)
        assert (
            analysis.fidelity_score < 0.8
        ), f"Should detect significant divergence when OAuth2 → JWT, got {analysis.fidelity_score}"
        assert len(analysis.divergences) > 0, "Should find divergences"

        # Check for major or critical severity
        serious_divs = [
            d for d in analysis.divergences if d.severity in ["critical", "major"]
        ]
        assert (
            len(serious_divs) > 0
        ), f"Should have critical/major divergence, got: {[d.severity for d in analysis.divergences]}"

        # Print details
        print("\n--- DIVERGENCES DETECTED ---")
        for i, div in enumerate(analysis.divergences, 1):
            print(f"\n{i}. [{div.severity.upper()}]")
            print(f"   Required: {div.requirement}")
            print(f"   Got: {div.implementation}")
            print(f"   Impact: {div.impact}")
            print(f"   Citation: {div.citation}")

        print("\n--- RECOMMENDATIONS ---")
        for i, rec in enumerate(analysis.recommendations, 1):
            print(f"{i}. {rec}")

        print("\n--- RAW DATA (for verification) ---")
        print(f"Task: {analysis.raw_data['task_description'][:100]}...")
        print(f"Decisions: {len(analysis.raw_data['decisions'])}")
        print(f"Artifacts: {len(analysis.raw_data['artifacts'])}")

    @pytest.mark.asyncio
    async def test_detect_perfect_match(self, analyzer):
        """
        Test detection of perfect match (no divergence).

        Implementation exactly matches requirements.
        """
        # Arrange - Simple matching implementation
        task = TaskHistory(
            task_id="task-feature-002",
            name="Add logout endpoint",
            description=(
                "Add a POST /logout endpoint that invalidates the user's session token "
                "and returns a 200 OK response."
            ),
            status="completed",
            estimated_hours=2.0,
            actual_hours=2.5,
        )

        # No architectural decisions
        decisions = []

        # Artifact showing exact implementation
        artifact = ArtifactMetadata(
            artifact_id="art-logout-001",
            task_id="task-feature-002",
            agent_id="agent-worker-2",
            timestamp=datetime.now(timezone.utc),
            artifact_type="code",
            filename="logout.py",
            relative_path="src/auth/logout.py",
            absolute_path="/project/src/auth/logout.py",
            description=(
                "Logout endpoint implementation. "
                "Lines 10-20: POST /logout endpoint that invalidates session token "
                "from Authorization header, returns 200 OK."
            ),
            file_size_bytes=512,
            sha256_hash="def789ghi012",
        )

        # Act
        print("\n" + "=" * 60)
        print("Testing: Perfect match detection")
        print("=" * 60)

        analysis = await analyzer.analyze_task(
            task=task,
            decisions=decisions,
            artifacts=[artifact],
        )

        # Assert
        print(f"\nFidelity Score: {analysis.fidelity_score:.2f}")
        print(f"Divergences Found: {len(analysis.divergences)}")

        # Should detect high fidelity
        assert (
            analysis.fidelity_score > 0.8
        ), "Should detect high fidelity for matching implementation"

        # Print details
        if analysis.divergences:
            print("\n--- DIVERGENCES (should be minor or none) ---")
            for div in analysis.divergences:
                print(f"  [{div.severity}] {div.impact}")
        else:
            print("\n✅ No divergences detected - perfect match!")

        print("\n--- RECOMMENDATIONS ---")
        for rec in analysis.recommendations:
            print(f"  - {rec}")

    @pytest.mark.asyncio
    async def test_detect_minor_divergence(self, analyzer):
        """
        Test detection of minor divergence.

        Implementation works but uses different approach.
        """
        # Arrange - Minor deviation
        task = TaskHistory(
            task_id="task-validation-003",
            name="Add email validation",
            description=(
                "Add email validation to the registration form. "
                "Use regex pattern to validate email format."
            ),
            status="completed",
            estimated_hours=1.0,
            actual_hours=1.0,
        )

        # Decision to use different validation
        decision = Decision(
            decision_id="dec-val-001",
            task_id="task-validation-003",
            agent_id="agent-worker-3",
            timestamp=datetime.now(timezone.utc),
            what="Use email-validator library instead of regex",
            why="More robust, handles edge cases better than regex",
            impact="low",
            affected_tasks=[],
            confidence=0.9,
        )

        artifact = ArtifactMetadata(
            artifact_id="art-val-001",
            task_id="task-validation-003",
            agent_id="agent-worker-3",
            timestamp=datetime.now(timezone.utc),
            artifact_type="code",
            filename="validators.py",
            relative_path="src/utils/validators.py",
            absolute_path="/project/src/utils/validators.py",
            description=(
                "Email validation using email-validator library. "
                "Lines 5-10: validate_email() function using validate_email() "
                "from email_validator package."
            ),
            file_size_bytes=256,
            sha256_hash="ghi345jkl678",
        )

        # Act
        print("\n" + "=" * 60)
        print("Testing: Minor divergence detection")
        print("=" * 60)

        analysis = await analyzer.analyze_task(
            task=task,
            decisions=[decision],
            artifacts=[artifact],
        )

        # Assert
        print(f"\nFidelity Score: {analysis.fidelity_score:.2f}")
        print(f"Divergences Found: {len(analysis.divergences)}")

        # Should detect reasonable fidelity (works, just different approach)
        assert (
            0.5 < analysis.fidelity_score < 0.95
        ), "Should detect moderate fidelity for working alternative approach"

        # Print details
        print("\n--- DIVERGENCES ---")
        for div in analysis.divergences:
            print(f"  [{div.severity}] {div.impact}")

        print("\n--- RECOMMENDATIONS ---")
        for rec in analysis.recommendations:
            print(f"  - {rec}")


@pytest.mark.integration
class TestRequirementDivergenceProgressReporting:
    """Test progress reporting during analysis."""

    @pytest.mark.asyncio
    async def test_progress_reporting_during_analysis(self):
        """Test that progress events are emitted during analysis."""
        # Arrange
        analyzer = RequirementDivergenceAnalyzer()

        progress_events = []

        async def progress_callback(event):
            progress_events.append(event)
            print(f"\r{event.message} ({event.current}/{event.total or '?'})", end="")

        task = TaskHistory(
            task_id="task-test",
            name="Test task",
            description="Build a simple feature",
            status="completed",
            estimated_hours=2.0,
            actual_hours=2.0,
        )

        # Act
        print("\n" + "=" * 60)
        print("Testing: Progress reporting")
        print("=" * 60)

        await analyzer.analyze_task(
            task=task,
            decisions=[],
            artifacts=[],
            progress_callback=progress_callback,
        )

        # Assert
        print(f"\n\nProgress events captured: {len(progress_events)}")
        assert len(progress_events) > 0, "Should emit progress events"

        # Print progress timeline
        print("\n--- PROGRESS TIMELINE ---")
        for event in progress_events:
            percentage = (
                f"{event.current / event.total * 100:.0f}%" if event.total else "N/A"
            )
            print(
                f"  {event.timestamp.strftime('%H:%M:%S.%f')[:-3]} "
                f"[{percentage:>4}] {event.message}"
            )


# Utility function for manual testing
async def manual_test():
    """
    Manual test function you can run directly.

    Run this with:
        python -c "import asyncio; from tests.integration.analysis.test_requirement_divergence_live import manual_test; asyncio.run(manual_test())"
    """
    print("=" * 70)
    print("MANUAL TEST: Requirement Divergence Analyzer")
    print("=" * 70)

    analyzer = RequirementDivergenceAnalyzer()

    # Create a test scenario
    task = TaskHistory(
        task_id="manual-test-001",
        name="Implement password reset",
        description=(
            "Implement password reset functionality. "
            "User enters email, receives reset link via email, "
            "can set new password using the link."
        ),
        status="completed",
        estimated_hours=4.0,
        actual_hours=6.0,
    )

    decision = Decision(
        decision_id="manual-dec-001",
        task_id="manual-test-001",
        agent_id="test-agent",
        timestamp=datetime.now(timezone.utc),
        what="Skip email sending, just generate reset token",
        why="Email service not configured yet",
        impact="major",
        affected_tasks=[],
        confidence=0.6,
    )

    artifact = ArtifactMetadata(
        artifact_id="manual-art-001",
        task_id="manual-test-001",
        agent_id="test-agent",
        timestamp=datetime.now(timezone.utc),
        artifact_type="code",
        filename="password_reset.py",
        relative_path="src/auth/password_reset.py",
        absolute_path="/project/src/auth/password_reset.py",
        description=(
            "Password reset implementation. "
            "Generates reset token and stores in database. "
            "Email sending is TODO."
        ),
        file_size_bytes=1024,
        sha256_hash="test123",
    )

    # Progress callback
    async def print_progress(event):
        print(f"  [{event.current}/{event.total or '?'}] {event.message}")

    print("\nRunning analysis...")
    analysis = await analyzer.analyze_task(
        task=task,
        decisions=[decision],
        artifacts=[artifact],
        progress_callback=print_progress,
    )

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\nFidelity Score: {analysis.fidelity_score:.2%}")
    print(f"Divergences: {len(analysis.divergences)}")

    for i, div in enumerate(analysis.divergences, 1):
        print(f"\n{i}. [{div.severity.upper()}]")
        print(f"   Required: {div.requirement}")
        print(f"   Got: {div.implementation}")
        print(f"   Impact: {div.impact}")

    print("\nRecommendations:")
    for i, rec in enumerate(analysis.recommendations, 1):
        print(f"{i}. {rec}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(manual_test())
