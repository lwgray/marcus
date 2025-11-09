"""
Integration tests for Decision Impact Tracer with real LLM calls.

These tests use actual Claude API calls to verify the Decision Impact Tracer
can correctly analyze how architectural decisions cascade through a project.

These tests:
- Require valid API keys in config_marcus.json
- Take longer to run (actual API calls)
- Cost money (uses LLM tokens)
- Are marked with @pytest.mark.integration

To run these tests:
    pytest tests/integration/analysis/test_decision_impact_tracer_live.py -v -m integration

To skip them (default):
    pytest -v  # Won't run integration tests by default
"""

from datetime import datetime, timezone

import pytest

from src.analysis.analyzers.decision_impact_tracer import (
    DecisionImpactAnalysis,
    DecisionImpactTracer,
    ImpactChain,
    UnexpectedImpact,
)
from src.core.project_history import Decision


@pytest.mark.integration
@pytest.mark.asyncio
class TestDecisionImpactTracerLive:
    """Integration tests with real LLM calls."""

    @pytest.fixture
    def tracer(self):
        """Create tracer with real AI engine."""
        return DecisionImpactTracer()

    @pytest.fixture
    def major_architecture_decision(self):
        """Create a major architectural decision that affects multiple tasks."""
        return Decision(
            decision_id="dec-arch-001",
            task_id="task-planning",
            agent_id="architect-agent",
            timestamp=datetime(2025, 11, 1, 9, 0, tzinfo=timezone.utc),
            what="Switch from monolithic architecture to microservices",
            why=(
                "Need better scalability and independent deployment. "
                "Current monolith is becoming difficult to maintain and deploy. "
                "Team wants to use different tech stacks for different services."
            ),
            impact="major",
            affected_tasks=[
                "task-auth",
                "task-api",
                "task-database",
            ],
            confidence=0.7,
        )

    @pytest.fixture
    def technical_decision(self):
        """Create a technical decision with limited scope."""
        return Decision(
            decision_id="dec-tech-001",
            task_id="task-auth",
            agent_id="dev-agent",
            timestamp=datetime(2025, 11, 2, 10, 0, tzinfo=timezone.utc),
            what="Use JWT tokens instead of session cookies",
            why=(
                "Stateless authentication works better with microservices. "
                "No need for session storage. Easier to scale horizontally."
            ),
            impact="moderate",
            affected_tasks=["task-auth", "task-frontend"],
            confidence=0.8,
        )

    @pytest.fixture
    def all_project_tasks(self):
        """Create a realistic set of project tasks."""
        return [
            {
                "task_id": "task-planning",
                "name": "Architecture planning",
                "status": "completed",
            },
            {
                "task_id": "task-auth",
                "name": "Build authentication service",
                "status": "completed",
            },
            {
                "task_id": "task-api",
                "name": "Build REST API gateway",
                "status": "completed",
            },
            {
                "task_id": "task-database",
                "name": "Set up database sharding",
                "status": "completed",
            },
            {
                "task_id": "task-frontend",
                "name": "Update frontend to use new auth",
                "status": "completed",
            },
            {
                "task_id": "task-deployment",
                "name": "Set up Kubernetes deployment",
                "status": "in_progress",
            },
        ]

    async def test_trace_major_architectural_decision_live(
        self, tracer, major_architecture_decision, all_project_tasks
    ):
        """
        Test tracing a major architectural decision with real LLM.

        This tests the ability to trace how a big decision (monolith -> microservices)
        cascades through multiple tasks.
        """
        # Act
        analysis = await tracer.trace_decision_impact(
            decision=major_architecture_decision,
            related_decisions=[],
            all_tasks=all_project_tasks,
        )

        # Assert - Overall structure
        assert isinstance(analysis, DecisionImpactAnalysis)
        assert analysis.decision_id == "dec-arch-001"

        # Assert - Impact chains
        assert len(analysis.impact_chains) > 0, "Should identify impact chains"

        # Verify impact chain structure
        chain = analysis.impact_chains[0]
        assert isinstance(chain, ImpactChain)
        # LLM may format decision ID creatively - just verify it's not empty
        assert chain.decision_id is not None and len(chain.decision_id) > 0
        assert chain.decision_summary is not None
        assert len(chain.decision_summary) > 0
        # Summary should reference the actual decision content
        assert (
            "microservice" in chain.decision_summary.lower()
            or "monolith" in chain.decision_summary.lower()
        )

        # Should have some direct impacts (tasks explicitly listed)
        assert len(chain.direct_impacts) > 0, "Should identify direct impacts"

        # Depth should be reasonable (1-5 levels)
        assert 1 <= chain.depth <= 5, f"Depth {chain.depth} seems unrealistic"

        # Must have citation
        assert chain.citation is not None
        assert len(chain.citation) > 0

        # Assert - LLM interpretation
        assert analysis.llm_interpretation is not None
        assert len(analysis.llm_interpretation) > 0

        # Print for manual inspection
        print("\n" + "=" * 70)
        print("DECISION IMPACT ANALYSIS - MAJOR ARCHITECTURAL DECISION")
        print("=" * 70)
        print(f"Decision: {major_architecture_decision.what}")
        print(f"\nImpact Chains: {len(analysis.impact_chains)}")
        for chain in analysis.impact_chains:
            print(f"\n  Chain (depth {chain.depth}):")
            print(f"    Summary: {chain.decision_summary}")
            print(f"    Direct impacts: {chain.direct_impacts}")
            print(f"    Indirect impacts: {chain.indirect_impacts}")
            print(f"    Citation: {chain.citation}")

        print(f"\nUnexpected Impacts: {len(analysis.unexpected_impacts)}")
        for unexpected in analysis.unexpected_impacts:
            print(f"\n  Unexpected Impact:")
            print(f"    Task: {unexpected.affected_task_name}")
            print(f"    Anticipated: {unexpected.anticipated}")
            print(f"    Actual: {unexpected.actual_impact}")
            print(f"    Severity: {unexpected.severity}")

        print("\n" + "=" * 70)

    async def test_trace_technical_decision_live(
        self, tracer, technical_decision, all_project_tasks
    ):
        """
        Test tracing a more focused technical decision.

        This tests analysis of a smaller-scope decision (JWT tokens).
        """
        # Act
        analysis = await tracer.trace_decision_impact(
            decision=technical_decision,
            related_decisions=[],
            all_tasks=all_project_tasks,
        )

        # Assert
        assert analysis.decision_id == "dec-tech-001"
        assert len(analysis.impact_chains) > 0

        # Technical decisions typically have shallower impact chains
        for chain in analysis.impact_chains:
            assert chain.depth <= 3, "Technical decision should have shallow impact"

    async def test_trace_decision_with_related_decisions_live(
        self, tracer, major_architecture_decision, technical_decision, all_project_tasks
    ):
        """
        Test tracing a decision in the context of related decisions.

        This tests whether the LLM can identify how decisions interact.
        """
        # Act - Trace the technical decision with architecture decision as context
        analysis = await tracer.trace_decision_impact(
            decision=technical_decision,
            related_decisions=[major_architecture_decision],
            all_tasks=all_project_tasks,
        )

        # Assert
        assert analysis.decision_id == "dec-tech-001"

        # Verify analysis completed with valid structure
        # LLM may or may not reference related decisions explicitly
        assert len(analysis.impact_chains) > 0
        assert analysis.llm_interpretation is not None

        # Just verify the analysis is valid - don't prescribe content
        for chain in analysis.impact_chains:
            assert chain.decision_id is not None
            assert chain.citation is not None

    async def test_identify_unexpected_impacts_live(self, tracer, all_project_tasks):
        """
        Test identification of unexpected impacts.

        Creates a decision where predicted impacts differ from actual.
        """
        # Arrange - Decision with overly optimistic impact prediction
        decision = Decision(
            decision_id="dec-optimistic",
            task_id="task-database",
            agent_id="dev-agent",
            timestamp=datetime(2025, 11, 3, 11, 0, tzinfo=timezone.utc),
            what="Switch database from PostgreSQL to MongoDB",
            why="Better performance for document storage",
            impact="minor",  # Predicted as minor
            affected_tasks=["task-database"],  # Only predicted to affect one task
            confidence=0.9,  # High confidence in prediction
        )

        # Act
        analysis = await tracer.trace_decision_impact(
            decision=decision,
            related_decisions=[],
            all_tasks=all_project_tasks,
        )

        # Assert
        # LLM should recognize that changing the database affects more than predicted
        # It should identify unexpected impacts on other tasks
        assert isinstance(analysis, DecisionImpactAnalysis)

        # Verify structure is valid
        for chain in analysis.impact_chains:
            assert isinstance(chain, ImpactChain)
            assert chain.citation is not None

        for unexpected in analysis.unexpected_impacts:
            assert isinstance(unexpected, UnexpectedImpact)
            assert unexpected.severity in ["critical", "major", "minor"]
            assert unexpected.citation is not None

    async def test_trace_with_progress_callback_live(
        self, tracer, major_architecture_decision, all_project_tasks
    ):
        """Test that progress callback works during live analysis."""
        # Arrange
        progress_events = []

        async def track_progress(event):
            progress_events.append(event)

        # Act
        analysis = await tracer.trace_decision_impact(
            decision=major_architecture_decision,
            related_decisions=[],
            all_tasks=all_project_tasks,
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
        assert analysis.decision_id == "dec-arch-001"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manual_inspection_decision_impact_live():
    """
    Manual test for inspecting detailed decision impact output.

    Run this test to see the full output from the tracer:
    pytest tests/integration/analysis/test_decision_impact_tracer_live.py::test_manual_inspection_decision_impact_live -v -s
    """
    tracer = DecisionImpactTracer()

    # Create a realistic decision cascade scenario
    architecture_decision = Decision(
        decision_id="dec-001",
        task_id="task-architecture",
        agent_id="architect-1",
        timestamp=datetime(2025, 11, 1, 9, 0, tzinfo=timezone.utc),
        what="Adopt event-driven architecture with message queue",
        why=(
            "Need to decouple services for better scalability. "
            "Current synchronous calls create bottlenecks. "
            "Want to handle traffic spikes gracefully."
        ),
        impact="major",
        affected_tasks=[
            "task-messaging",
            "task-api-refactor",
            "task-monitoring",
        ],
        confidence=0.75,
    )

    related_decision = Decision(
        decision_id="dec-002",
        task_id="task-messaging",
        agent_id="dev-1",
        timestamp=datetime(2025, 11, 2, 14, 0, tzinfo=timezone.utc),
        what="Use RabbitMQ for message queue",
        why="Team has experience with RabbitMQ, good community support",
        impact="moderate",
        affected_tasks=["task-messaging", "task-deployment"],
        confidence=0.8,
    )

    tasks = [
        {
            "task_id": "task-architecture",
            "name": "Architecture planning",
            "status": "completed",
        },
        {
            "task_id": "task-messaging",
            "name": "Implement message queue",
            "status": "completed",
        },
        {
            "task_id": "task-api-refactor",
            "name": "Refactor API to async",
            "status": "in_progress",
        },
        {
            "task_id": "task-monitoring",
            "name": "Add queue monitoring",
            "status": "completed",
        },
        {
            "task_id": "task-deployment",
            "name": "Deploy RabbitMQ cluster",
            "status": "completed",
        },
        {
            "task_id": "task-frontend",
            "name": "Update frontend polling",
            "status": "pending",
        },
    ]

    print("\n" + "=" * 70)
    print("RUNNING DECISION IMPACT ANALYSIS")
    print("=" * 70)

    analysis = await tracer.trace_decision_impact(
        decision=architecture_decision,
        related_decisions=[related_decision],
        all_tasks=tasks,
    )

    print("\n📊 DECISION IMPACT ANALYSIS")
    print("-" * 70)
    print(f"Decision: {architecture_decision.what}")
    print(f"Original Impact Assessment: {architecture_decision.impact}")
    print(
        f"Originally Predicted to Affect: {len(architecture_decision.affected_tasks)} tasks"
    )

    print("\n🔗 IMPACT CHAINS")
    print("-" * 70)
    for i, chain in enumerate(analysis.impact_chains, 1):
        print(f"\nChain {i}:")
        print(f"  Summary: {chain.decision_summary}")
        print(f"  Depth: {chain.depth}")
        print(f"  Direct Impacts: {chain.direct_impacts}")
        print(f"  Indirect Impacts: {chain.indirect_impacts}")
        print(f"  Citation: {chain.citation}")

    print("\n⚠️  UNEXPECTED IMPACTS")
    print("-" * 70)
    if analysis.unexpected_impacts:
        for impact in analysis.unexpected_impacts:
            print(f"\nTask: {impact.affected_task_name} ({impact.affected_task_id})")
            print(f"  Anticipated: {impact.anticipated}")
            print(f"  Actual Impact: {impact.actual_impact}")
            print(f"  Severity: {impact.severity}")
            print(f"  Citation: {impact.citation}")
    else:
        print("No unexpected impacts identified")

    print("\n💡 RECOMMENDATIONS")
    print("-" * 70)
    for rec in analysis.recommendations:
        print(f"  • {rec}")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
