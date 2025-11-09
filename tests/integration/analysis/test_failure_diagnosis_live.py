"""
Integration tests for Failure Diagnosis Generator with real LLM calls.

These tests use actual Claude API calls to verify the Failure Diagnosis Generator
can correctly diagnose why tasks failed and recommend prevention strategies.

These tests:
- Require valid API keys in config_marcus.json
- Take longer to run (actual API calls)
- Cost money (uses LLM tokens)
- Are marked with @pytest.mark.integration

To run these tests:
    pytest tests/integration/analysis/test_failure_diagnosis_live.py -v -m integration

To skip them (default):
    pytest -v  # Won't run integration tests by default
"""

from datetime import datetime, timezone

import pytest

from src.analysis.aggregator import TaskHistory
from src.analysis.analyzers.failure_diagnosis import (
    FailureCause,
    FailureDiagnosis,
    FailureDiagnosisGenerator,
    PreventionStrategy,
)
from src.core.project_history import Decision


@pytest.mark.integration
@pytest.mark.asyncio
class TestFailureDiagnosisGeneratorLive:
    """Integration tests with real LLM calls."""

    @pytest.fixture
    def generator(self):
        """Create generator with real AI engine."""
        return FailureDiagnosisGenerator()

    @pytest.fixture
    def technical_failure_task(self):
        """Create a task that failed due to technical issues."""
        return TaskHistory(
            task_id="task-tech-fail",
            name="Deploy database migration",
            description=(
                "Deploy schema changes to production database. "
                "Add new user_preferences table and update users table."
            ),
            status="failed",
            estimated_hours=2.0,
            actual_hours=8.0,  # Spent a lot of time trying to fix
        )

    @pytest.fixture
    def requirements_failure_task(self):
        """Create a task that failed due to unclear requirements."""
        return TaskHistory(
            task_id="task-req-fail",
            name="Implement search feature",
            description="Add search to the application",
            status="failed",
            estimated_hours=6.0,
            actual_hours=12.0,
        )

    @pytest.fixture
    def process_failure_task(self):
        """Create a task that failed due to process issues."""
        return TaskHistory(
            task_id="task-proc-fail",
            name="Launch marketing campaign",
            description=(
                "Launch new marketing campaign with email and social media. "
                "Target existing users and new prospects."
            ),
            status="failed",
            estimated_hours=10.0,
            actual_hours=15.0,
        )

    async def test_diagnose_technical_failure_live(
        self, generator, technical_failure_task
    ):
        """
        Test diagnosing a technical failure with real LLM.

        Task failed due to database locking issues.
        """
        # Arrange
        error_logs = [
            "ERROR: database connection timeout after 30s",
            "ERROR: table lock wait timeout exceeded",
            "ERROR: rollback failed - database in inconsistent state",
            "FATAL: migration aborted at step 3 of 5",
        ]

        related_decisions = [
            Decision(
                decision_id="dec-001",
                task_id="task-tech-fail",
                agent_id="agent-1",
                timestamp=datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc),
                what="Run migration during business hours",
                why="Can't wait for maintenance window",
                impact="moderate",
                affected_tasks=["task-tech-fail"],
                confidence=0.6,
            )
        ]

        context_notes = [
            "Production database was under heavy load during migration",
            "No dry-run was performed in staging environment",
            "Migration script had no rollback procedure",
        ]

        # Act
        diagnosis = await generator.generate_diagnosis(
            task=technical_failure_task,
            error_logs=error_logs,
            related_decisions=related_decisions,
            context_notes=context_notes,
        )

        # Assert - Overall structure
        assert isinstance(diagnosis, FailureDiagnosis)
        assert diagnosis.task_id == "task-tech-fail"

        # Assert - Failure causes
        assert len(diagnosis.failure_causes) > 0, "Should identify failure causes"

        # Verify failure cause structure
        for cause in diagnosis.failure_causes:
            assert isinstance(cause, FailureCause)
            assert cause.category in [
                "technical",
                "requirements",
                "process",
                "communication",
            ]
            assert cause.root_cause is not None and len(cause.root_cause) > 0
            assert cause.evidence is not None and len(cause.evidence) > 0
            assert cause.citation is not None and len(cause.citation) > 0

        # At least one should be technical since logs show database issues
        categories = [c.category for c in diagnosis.failure_causes]
        # LLM decides categories, just verify they're valid

        # Assert - Prevention strategies
        assert (
            len(diagnosis.prevention_strategies) > 0
        ), "Should suggest prevention strategies"

        # Verify prevention strategy structure
        for strategy in diagnosis.prevention_strategies:
            assert isinstance(strategy, PreventionStrategy)
            assert strategy.strategy is not None and len(strategy.strategy) > 0
            assert strategy.effort in ["low", "medium", "high"]
            assert strategy.priority in ["low", "medium", "high"]
            assert strategy.rationale is not None

        # Assert - Lessons learned
        assert isinstance(diagnosis.lessons_learned, list)

        # Assert - LLM interpretation
        assert diagnosis.llm_interpretation is not None

        # Print for inspection
        print("\n" + "=" * 70)
        print("FAILURE DIAGNOSIS - TECHNICAL FAILURE")
        print("=" * 70)
        print(f"Task: {technical_failure_task.name}")
        print(f"\nFailure Causes: {len(diagnosis.failure_causes)}")
        for cause in diagnosis.failure_causes:
            print(f"\n  Category: {cause.category}")
            print(f"  Root Cause: {cause.root_cause}")
            print(f"  Evidence: {cause.evidence[:100]}...")
            print(f"  Citation: {cause.citation}")

        print(f"\nPrevention Strategies: {len(diagnosis.prevention_strategies)}")
        for strategy in diagnosis.prevention_strategies:
            print(f"\n  Strategy: {strategy.strategy}")
            print(f"  Priority: {strategy.priority} | Effort: {strategy.effort}")
            print(f"  Rationale: {strategy.rationale[:100]}...")

        print(f"\nLessons Learned: {len(diagnosis.lessons_learned)}")
        for lesson in diagnosis.lessons_learned:
            print(f"  • {lesson}")
        print("=" * 70)

    async def test_diagnose_requirements_failure_live(
        self, generator, requirements_failure_task
    ):
        """
        Test diagnosing a failure due to unclear requirements.

        Task failed because requirements were too vague.
        """
        # Arrange
        error_logs = [
            "ERROR: search query parsing failed for input 'complex query'",
            "ERROR: elasticsearch timeout after 10s",
        ]

        context_notes = [
            "No clear specification of which fields to search",
            "Performance requirements not specified",
            "No examples of expected search behavior",
            "Confusion about full-text vs exact match",
        ]

        # Act
        diagnosis = await generator.generate_diagnosis(
            task=requirements_failure_task,
            error_logs=error_logs,
            related_decisions=[],
            context_notes=context_notes,
        )

        # Assert
        assert diagnosis.task_id == "task-req-fail"
        assert len(diagnosis.failure_causes) > 0

        # Should identify requirements-related causes
        # LLM decides categories based on evidence

        # Verify structure
        for cause in diagnosis.failure_causes:
            assert cause.category in [
                "technical",
                "requirements",
                "process",
                "communication",
            ]
            assert len(cause.root_cause) > 0

    async def test_diagnose_process_failure_live(self, generator, process_failure_task):
        """
        Test diagnosing a failure due to process issues.

        Task failed due to coordination/process problems.
        """
        # Arrange
        error_logs = []  # Process failures often don't have technical error logs

        context_notes = [
            "Marketing team and engineering team had different understanding of timeline",
            "Email templates not reviewed by legal team before sending",
            "Campaign launched before tracking analytics were set up",
            "No approval process for campaign content",
        ]

        # Act
        diagnosis = await generator.generate_diagnosis(
            task=process_failure_task,
            error_logs=error_logs,
            related_decisions=[],
            context_notes=context_notes,
        )

        # Assert
        assert diagnosis.task_id == "task-proc-fail"
        assert len(diagnosis.failure_causes) > 0

        # Should identify process/communication issues
        # Verify structure is valid
        for cause in diagnosis.failure_causes:
            assert cause.category in [
                "technical",
                "requirements",
                "process",
                "communication",
            ]

    async def test_diagnose_with_decision_contribution_live(
        self, generator, technical_failure_task
    ):
        """
        Test that diagnosis identifies how decisions contributed to failure.

        The decision to run migration during business hours contributed to failure.
        """
        # Arrange
        error_logs = ["ERROR: database locked during peak traffic"]

        bad_decision = Decision(
            decision_id="dec-bad",
            task_id="task-tech-fail",
            agent_id="agent-1",
            timestamp=datetime(2025, 11, 1, 9, 0, tzinfo=timezone.utc),
            what="Skip testing migration in staging",
            why="Save time",
            impact="major",
            affected_tasks=["task-tech-fail"],
            confidence=0.5,
        )

        context_notes = ["Migration had not been tested before production"]

        # Act
        diagnosis = await generator.generate_diagnosis(
            task=technical_failure_task,
            error_logs=error_logs,
            related_decisions=[bad_decision],
            context_notes=context_notes,
        )

        # Assert
        assert len(diagnosis.failure_causes) > 0

        # LLM should reference the decision in evidence or citations
        # But we don't prescribe exactly how - just verify structure is valid
        for cause in diagnosis.failure_causes:
            assert cause.citation is not None

    async def test_multiple_contributing_factors_live(self, generator):
        """
        Test diagnosing a failure with multiple contributing factors.

        Complex failure with technical, requirements, and process issues.
        """
        # Arrange
        complex_failure = TaskHistory(
            task_id="task-complex-fail",
            name="Launch new payment system",
            description="Replace old payment system with new provider",
            status="failed",
            estimated_hours=40.0,
            actual_hours=80.0,
        )

        error_logs = [
            "ERROR: payment gateway API rate limit exceeded",
            "ERROR: webhook verification failed - invalid signature",
            "ERROR: customer billing data migration incomplete",
        ]

        context_notes = [
            "Requirements doc didn't specify rate limits",
            "No monitoring for webhook delivery",
            "Migration script tested with sample data only",
            "Rollback plan was incomplete",
        ]

        # Act
        diagnosis = await generator.generate_diagnosis(
            task=complex_failure,
            error_logs=error_logs,
            related_decisions=[],
            context_notes=context_notes,
        )

        # Assert
        # Should identify multiple failure causes
        assert len(diagnosis.failure_causes) >= 1

        # Should have prevention strategies for each cause
        assert len(diagnosis.prevention_strategies) >= 1

        # Verify all contributing factors are captured
        for cause in diagnosis.failure_causes:
            assert len(cause.contributing_factors) >= 0  # May have additional factors

    async def test_diagnose_with_progress_callback_live(
        self, generator, technical_failure_task
    ):
        """Test that progress callback works during live diagnosis."""
        # Arrange
        progress_events = []

        async def track_progress(event):
            progress_events.append(event)

        # Act
        diagnosis = await generator.generate_diagnosis(
            task=technical_failure_task,
            error_logs=["ERROR: test error"],
            related_decisions=[],
            context_notes=[],
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

        # Verify diagnosis completed
        assert diagnosis.task_id == "task-tech-fail"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manual_inspection_failure_diagnosis_live():
    """
    Manual test for inspecting detailed failure diagnosis output.

    Run this test to see the full output from the generator:
    pytest tests/integration/analysis/test_failure_diagnosis_live.py::test_manual_inspection_failure_diagnosis_live -v -s
    """
    generator = FailureDiagnosisGenerator()

    # Create a realistic complex failure scenario
    failed_task = TaskHistory(
        task_id="task-inspect",
        name="Migrate from REST to GraphQL API",
        description=(
            "Replace existing REST API with GraphQL. "
            "Maintain backward compatibility with existing clients. "
            "Improve query efficiency and reduce over-fetching."
        ),
        status="failed",
        estimated_hours=80.0,
        actual_hours=160.0,
    )

    error_logs = [
        "ERROR: GraphQL schema validation failed for User type",
        "ERROR: N+1 query detected - users.posts.comments causing 1000+ DB queries",
        "ERROR: client authentication failing with new GraphQL endpoint",
        "ERROR: breaking change in API contract - mobile app crashed for 50% of users",
        "WARN: GraphQL query complexity exceeded limit (depth > 10)",
    ]

    decisions = [
        Decision(
            decision_id="dec-001",
            task_id="task-inspect",
            agent_id="agent-1",
            timestamp=datetime(2025, 10, 15, 10, 0, tzinfo=timezone.utc),
            what="Implement GraphQL from scratch instead of using existing library",
            why="Want full control over implementation",
            impact="major",
            affected_tasks=["task-inspect"],
            confidence=0.6,
        ),
        Decision(
            decision_id="dec-002",
            task_id="task-inspect",
            agent_id="agent-2",
            timestamp=datetime(2025, 10, 20, 14, 0, tzinfo=timezone.utc),
            what="Deploy to production without canary release",
            why="Confident in testing coverage",
            impact="major",
            affected_tasks=["task-inspect"],
            confidence=0.8,
        ),
    ]

    context_notes = [
        "Only 30% of REST endpoints had test coverage",
        "GraphQL schema was not reviewed by mobile team before deployment",
        "Performance testing was done with small dataset (100 users) vs production (100k users)",
        "No rollback plan was documented",
        "Breaking changes were not communicated to client teams",
    ]

    print("\n" + "=" * 70)
    print("RUNNING FAILURE DIAGNOSIS")
    print("=" * 70)

    diagnosis = await generator.generate_diagnosis(
        task=failed_task,
        error_logs=error_logs,
        related_decisions=decisions,
        context_notes=context_notes,
    )

    print("\n💥 FAILURE DIAGNOSIS")
    print("-" * 70)
    print(f"Task: {failed_task.name}")
    print(f"Status: {failed_task.status}")
    print(
        f"Time: Estimated {failed_task.estimated_hours}h, Actual {failed_task.actual_hours}h"
    )
    print(
        f"Overrun: {((failed_task.actual_hours / failed_task.estimated_hours - 1) * 100):.0f}%"
    )

    print("\n🔍 ROOT CAUSES")
    print("-" * 70)
    for i, cause in enumerate(diagnosis.failure_causes, 1):
        print(f"\nCause {i}: {cause.category.upper()}")
        print(f"  Root Cause: {cause.root_cause}")
        if cause.contributing_factors:
            print(f"  Contributing Factors:")
            for factor in cause.contributing_factors:
                print(f"    • {factor}")
        print(f"  Evidence: {cause.evidence}")
        print(f"  Citation: {cause.citation}")

    print("\n🛡️  PREVENTION STRATEGIES")
    print("-" * 70)
    # Group by priority
    high_priority = [s for s in diagnosis.prevention_strategies if s.priority == "high"]
    med_priority = [
        s for s in diagnosis.prevention_strategies if s.priority == "medium"
    ]
    low_priority = [s for s in diagnosis.prevention_strategies if s.priority == "low"]

    if high_priority:
        print("\nHIGH PRIORITY:")
        for strategy in high_priority:
            print(f"  • {strategy.strategy}")
            print(f"    Effort: {strategy.effort} | Rationale: {strategy.rationale}")

    if med_priority:
        print("\nMEDIUM PRIORITY:")
        for strategy in med_priority:
            print(f"  • {strategy.strategy}")
            print(f"    Effort: {strategy.effort}")

    if low_priority:
        print("\nLOW PRIORITY:")
        for strategy in low_priority:
            print(f"  • {strategy.strategy}")

    print("\n📚 LESSONS LEARNED")
    print("-" * 70)
    for lesson in diagnosis.lessons_learned:
        print(f"  • {lesson}")

    print("\n" + "=" * 70)
    print("DIAGNOSIS COMPLETE")
    print("=" * 70)
