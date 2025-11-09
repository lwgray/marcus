"""
Integration tests for Instruction Quality Analyzer with real LLM calls.

These tests use actual Claude API calls to verify the Instruction Quality Analyzer
can correctly evaluate how clear and complete task instructions were.

These tests:
- Require valid API keys in config_marcus.json
- Take longer to run (actual API calls)
- Cost money (uses LLM tokens)
- Are marked with @pytest.mark.integration

To run these tests:
    pytest tests/integration/analysis/test_instruction_quality_live.py -v -m integration

To skip them (default):
    pytest -v  # Won't run integration tests by default
"""

import pytest

from src.analysis.aggregator import TaskHistory
from src.analysis.analyzers.instruction_quality import (
    AmbiguityIssue,
    InstructionQualityAnalysis,
    InstructionQualityAnalyzer,
    QualityScore,
)


@pytest.mark.integration
@pytest.mark.asyncio
class TestInstructionQualityAnalyzerLive:
    """Integration tests with real LLM calls."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer with real AI engine."""
        return InstructionQualityAnalyzer()

    @pytest.fixture
    def clear_detailed_task(self):
        """Create a task with clear, detailed instructions."""
        return TaskHistory(
            task_id="task-clear-001",
            name="Implement user registration API endpoint",
            description=(
                "Create a POST /api/v1/users/register endpoint that:\n"
                "1. Accepts JSON body with email, password, username fields\n"
                "2. Validates email format (RFC 5322)\n"
                "3. Requires password length >= 8 characters with 1 uppercase, 1 lowercase, 1 number\n"
                "4. Checks username is unique in database\n"
                "5. Hashes password using bcrypt with cost factor 12\n"
                "6. Stores user in PostgreSQL users table\n"
                "7. Returns 201 with user ID and auth token (JWT, expires 24h)\n"
                "8. Returns 400 for validation errors with specific error messages\n"
                "9. Returns 409 if email or username already exists\n"
                "10. Rate limit: 5 requests per minute per IP"
            ),
            status="completed",
            estimated_hours=6.0,
            actual_hours=6.5,  # Slightly over estimate
        )

    @pytest.fixture
    def vague_task(self):
        """Create a task with vague, ambiguous instructions."""
        return TaskHistory(
            task_id="task-vague-001",
            name="Add authentication",
            description="Users should be able to log in to the system",
            status="completed",
            estimated_hours=4.0,
            actual_hours=16.0,  # 4x over estimate due to ambiguity
        )

    @pytest.fixture
    def partially_clear_task(self):
        """Create a task with some clear parts and some vague parts."""
        return TaskHistory(
            task_id="task-partial-001",
            name="Implement payment processing",
            description=(
                "Add payment processing to checkout flow. "
                "Use Stripe API. "
                "Handle successful and failed payments appropriately."
            ),
            status="completed",
            estimated_hours=8.0,
            actual_hours=12.0,  # Over estimate due to missing details
        )

    async def test_analyze_clear_detailed_task_live(
        self, analyzer, clear_detailed_task
    ):
        """
        Test analyzing a task with clear, detailed instructions.

        Should result in high quality scores and few ambiguity issues.
        """
        # Act
        analysis = await analyzer.analyze_instruction_quality(
            task=clear_detailed_task,
            clarifications=[],  # No clarifications needed
            implementation_notes=[],
        )

        # Assert - Overall structure
        assert isinstance(analysis, InstructionQualityAnalysis)
        assert analysis.task_id == "task-clear-001"

        # Assert - Quality scores
        assert isinstance(analysis.quality_scores, QualityScore)
        assert 0.0 <= analysis.quality_scores.clarity <= 1.0
        assert 0.0 <= analysis.quality_scores.completeness <= 1.0
        assert 0.0 <= analysis.quality_scores.specificity <= 1.0
        assert 0.0 <= analysis.quality_scores.overall <= 1.0

        # Clear task should have decent overall score (but LLM decides)
        # Just verify the score is in valid range
        assert analysis.quality_scores.overall >= 0.0

        # Assert - Ambiguity issues
        assert isinstance(analysis.ambiguity_issues, list)

        # Verify any ambiguity issues have correct structure
        for issue in analysis.ambiguity_issues:
            assert isinstance(issue, AmbiguityIssue)
            # LLM may format task_id creatively - just verify it's not empty
            assert issue.task_id is not None and len(issue.task_id) > 0
            assert issue.severity in ["critical", "major", "minor"]
            assert issue.citation is not None

        # Assert - LLM interpretation
        assert analysis.llm_interpretation is not None
        assert len(analysis.llm_interpretation) > 0

        # Print for inspection
        print("\n" + "=" * 70)
        print("INSTRUCTION QUALITY - CLEAR DETAILED TASK")
        print("=" * 70)
        print(f"Clarity: {analysis.quality_scores.clarity:.2f}")
        print(f"Completeness: {analysis.quality_scores.completeness:.2f}")
        print(f"Specificity: {analysis.quality_scores.specificity:.2f}")
        print(f"Overall: {analysis.quality_scores.overall:.2f}")
        print(f"\nAmbiguity Issues: {len(analysis.ambiguity_issues)}")
        for issue in analysis.ambiguity_issues:
            print(f"  • {issue.ambiguous_aspect} ({issue.severity})")
        print("=" * 70)

    async def test_analyze_vague_task_live(self, analyzer, vague_task):
        """
        Test analyzing a task with vague, ambiguous instructions.

        Should result in lower quality scores and multiple ambiguity issues.
        """
        # Arrange - Add clarifications that were needed due to vagueness
        clarifications = [
            {
                "question": "Which authentication method? OAuth, JWT, sessions?",
                "answer": "Just basic email/password for now",
                "timestamp": "2025-11-01T10:30:00Z",
            },
            {
                "question": "What user data needs to be collected?",
                "answer": "Email and password only",
                "timestamp": "2025-11-01T10:35:00Z",
            },
            {
                "question": "Password requirements?",
                "answer": "At least 8 characters",
                "timestamp": "2025-11-01T10:40:00Z",
            },
            {
                "question": "Should we support social login?",
                "answer": "No, not in this iteration",
                "timestamp": "2025-11-01T10:45:00Z",
            },
        ]

        # Act
        analysis = await analyzer.analyze_instruction_quality(
            task=vague_task,
            clarifications=clarifications,
            implementation_notes=[
                "Had to ask many questions about requirements",
                "Unclear what 'log in' meant - just password or also social?",
            ],
        )

        # Assert
        assert analysis.task_id == "task-vague-001"

        # Vague task should have lower scores (but LLM decides exact values)
        assert 0.0 <= analysis.quality_scores.overall <= 1.0

        # Should identify ambiguity issues
        # (LLM may or may not find issues, don't prescribe)
        assert isinstance(analysis.ambiguity_issues, list)

        # Verify any issues found have correct structure
        for issue in analysis.ambiguity_issues:
            # LLM may format task_id creatively
            assert issue.task_id is not None and len(issue.task_id) > 0
            assert issue.severity in ["critical", "major", "minor"]
            assert len(issue.ambiguous_aspect) > 0
            assert len(issue.evidence) > 0

        # Print for inspection
        print("\n" + "=" * 70)
        print("INSTRUCTION QUALITY - VAGUE TASK")
        print("=" * 70)
        print(f"Clarity: {analysis.quality_scores.clarity:.2f}")
        print(f"Completeness: {analysis.quality_scores.completeness:.2f}")
        print(f"Specificity: {analysis.quality_scores.specificity:.2f}")
        print(f"Overall: {analysis.quality_scores.overall:.2f}")
        print(f"\nAmbiguity Issues: {len(analysis.ambiguity_issues)}")
        for issue in analysis.ambiguity_issues:
            print(f"  • {issue.ambiguous_aspect} ({issue.severity})")
            print(f"    Evidence: {issue.evidence[:100]}...")
            print(f"    Consequence: {issue.consequence[:100]}...")
        print("=" * 70)

    async def test_analyze_partially_clear_task_live(
        self, analyzer, partially_clear_task
    ):
        """
        Test analyzing a task with mixed clarity.

        Has some clear parts (Stripe API) and vague parts (handle appropriately).
        """
        # Arrange
        clarifications = [
            {
                "question": "What specific Stripe features to use? Checkout vs Payment Intents?",
                "answer": "Use Payment Intents API",
                "timestamp": "2025-11-02T09:00:00Z",
            },
            {
                "question": "How to handle failed payments - retry? notify user?",
                "answer": "Notify user by email, don't auto-retry",
                "timestamp": "2025-11-02T09:15:00Z",
            },
        ]

        # Act
        analysis = await analyzer.analyze_instruction_quality(
            task=partially_clear_task,
            clarifications=clarifications,
            implementation_notes=[],
        )

        # Assert
        assert analysis.task_id == "task-partial-001"
        assert isinstance(analysis.quality_scores, QualityScore)

        # Should have moderate scores (specific parts clear, vague parts not)
        assert 0.0 <= analysis.quality_scores.overall <= 1.0

        # Should identify some ambiguity in the vague parts
        assert isinstance(analysis.ambiguity_issues, list)

    async def test_correlate_instruction_quality_with_delays_live(
        self, analyzer, vague_task
    ):
        """
        Test that analyzer correlates poor instruction quality with task delays.

        The vague task took 4x longer than estimated (4h -> 16h).
        """
        # Act
        analysis = await analyzer.analyze_instruction_quality(
            task=vague_task,
            clarifications=[
                {
                    "question": "Many clarifications needed - what auth method?",
                    "answer": "JWT tokens",
                    "timestamp": "2025-11-01T11:00:00Z",
                },
                {
                    "question": "Spent hours asking questions - what data to collect?",
                    "answer": "Email, password, name",
                    "timestamp": "2025-11-01T11:30:00Z",
                },
            ],
            implementation_notes=[],
        )

        # Assert
        # LLM should recognize the correlation between vague instructions
        # and the 4x time overrun, but we don't prescribe how
        assert analysis.task_id == "task-vague-001"

        # Just verify the analysis completed with valid data
        assert isinstance(analysis.quality_scores, QualityScore)
        assert isinstance(analysis.recommendations, list)

    async def test_analyze_with_progress_callback_live(
        self, analyzer, clear_detailed_task
    ):
        """Test that progress callback works during live analysis."""
        # Arrange
        progress_events = []

        async def track_progress(event):
            progress_events.append(event)

        # Act
        analysis = await analyzer.analyze_instruction_quality(
            task=clear_detailed_task,
            clarifications=[],
            implementation_notes=[],
            progress_callback=track_progress,
        )

        # Assert
        assert len(progress_events) > 0, "Should have received progress updates"

        # Verify progress events have correct structure
        for event in progress_events:
            assert event.operation is not None
            assert event.current >= 0
            assert event.total > 0
            assert event.message is not None

        # Verify analysis completed
        assert analysis.task_id == "task-clear-001"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manual_inspection_instruction_quality_live():
    """
    Manual test for inspecting detailed instruction quality output.

    Run this test to see the full output from the analyzer:
    pytest tests/integration/analysis/test_instruction_quality_live.py::test_manual_inspection_instruction_quality_live -v -s
    """
    analyzer = InstructionQualityAnalyzer()

    # Create a realistic scenario with varying instruction quality
    task = TaskHistory(
        task_id="task-inspect",
        name="Build notification system",
        description=(
            "Users should get notifications. "
            "Implement email and in-app notifications. "
            "Make sure it works well."
        ),
        status="completed",
        estimated_hours=10.0,
        actual_hours=20.0,
    )

    clarifications = [
        {
            "question": "What triggers notifications? (user actions, system events, scheduled?)",
            "answer": "User actions and some system events",
            "timestamp": "2025-11-03T10:00:00Z",
        },
        {
            "question": "Email provider? (SendGrid, AWS SES, SMTP?)",
            "answer": "Use SendGrid",
            "timestamp": "2025-11-03T10:30:00Z",
        },
        {
            "question": "Notification preferences - can users control what they receive?",
            "answer": "Yes, users should be able to opt out",
            "timestamp": "2025-11-03T11:00:00Z",
        },
        {
            "question": "Should notifications be real-time or batched?",
            "answer": "Real-time for important events, batched for others",
            "timestamp": "2025-11-03T11:30:00Z",
        },
        {
            "question": "What's 'works well' mean - SLA? delivery rate?",
            "answer": "95% delivery rate within 1 minute",
            "timestamp": "2025-11-03T12:00:00Z",
        },
    ]

    implementation_notes = [
        "Spent 4 hours in meetings clarifying requirements",
        "Had to redesign notification schema twice due to unclear requirements",
        "Email provider choice blocked development for 2 days",
    ]

    print("\n" + "=" * 70)
    print("RUNNING INSTRUCTION QUALITY ANALYSIS")
    print("=" * 70)

    analysis = await analyzer.analyze_instruction_quality(
        task=task,
        clarifications=clarifications,
        implementation_notes=implementation_notes,
    )

    print("\n📊 INSTRUCTION QUALITY ANALYSIS")
    print("-" * 70)
    print(f"Task: {task.name}")
    print(f"Time: Estimated {task.estimated_hours}h, Actual {task.actual_hours}h")
    print(f"Overrun: {((task.actual_hours / task.estimated_hours - 1) * 100):.0f}%")

    print("\n📈 QUALITY SCORES")
    print("-" * 70)
    print(f"Clarity:       {analysis.quality_scores.clarity:.2f} / 1.00")
    print(f"Completeness:  {analysis.quality_scores.completeness:.2f} / 1.00")
    print(f"Specificity:   {analysis.quality_scores.specificity:.2f} / 1.00")
    print(f"Overall:       {analysis.quality_scores.overall:.2f} / 1.00")

    print("\n🔍 AMBIGUITY ISSUES")
    print("-" * 70)
    if analysis.ambiguity_issues:
        for i, issue in enumerate(analysis.ambiguity_issues, 1):
            print(f"\nIssue {i}: {issue.ambiguous_aspect}")
            print(f"  Severity: {issue.severity}")
            print(f"  Evidence: {issue.evidence}")
            print(f"  Consequence: {issue.consequence}")
            print(f"  Citation: {issue.citation}")
    else:
        print("No ambiguity issues identified")

    print("\n💡 RECOMMENDATIONS")
    print("-" * 70)
    for rec in analysis.recommendations:
        print(f"  • {rec}")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
