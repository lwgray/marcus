"""
Integration tests for PostProjectAnalyzer with real LLM calls.

These tests use actual Claude API calls to verify the complete end-to-end
workflow of the PostProjectAnalyzer orchestrator coordinating all four
Phase 2 analyzers.

These tests:
- Require valid API keys in config_marcus.json
- Take longer to run (actual API calls)
- Cost money (uses LLM tokens)
- Are marked with @pytest.mark.integration

To run these tests:
    pytest tests/integration/analysis/test_post_project_analyzer_live.py -v -m integration

To skip them (default):
    pytest -v  # Won't run integration tests by default
"""

from datetime import datetime, timezone

import pytest

from src.analysis.aggregator import TaskHistory
from src.analysis.post_project_analyzer import (
    AnalysisScope,
    PostProjectAnalyzer,
)
from src.core.project_history import Decision


@pytest.mark.integration
@pytest.mark.asyncio
class TestPostProjectAnalyzerLive:
    """Integration tests with real LLM calls."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer with real AI engine."""
        return PostProjectAnalyzer()

    @pytest.fixture
    def realistic_project_tasks(self):
        """Create realistic project tasks with clear divergence patterns."""
        return [
            TaskHistory(
                task_id="task-001",
                name="Implement user authentication",
                description=(
                    "Build authentication system using OAuth2 with Google provider. "
                    "Users should be able to sign in with their Google account. "
                    "Store user profile in PostgreSQL database."
                ),
                status="completed",
                estimated_hours=8.0,
                actual_hours=16.0,  # Took much longer
            ),
            TaskHistory(
                task_id="task-002",
                name="Create user dashboard",
                description=(
                    "Build a dashboard showing user's recent activity. "
                    "Display last 10 actions in a table with timestamps. "
                    "Include pagination for older items."
                ),
                status="completed",
                estimated_hours=4.0,
                actual_hours=4.5,
            ),
            TaskHistory(
                task_id="task-003",
                name="Implement data export",
                description=(
                    "Allow users to export their data in CSV format. "
                    "Include all user actions with timestamps. "
                    "Send download link via email."
                ),
                status="failed",
                estimated_hours=6.0,
                actual_hours=10.0,
            ),
        ]

    @pytest.fixture
    def realistic_project_decisions(self):
        """Create realistic project decisions."""
        return [
            Decision(
                decision_id="dec-001",
                task_id="task-001",
                agent_id="agent-1",
                timestamp=datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc),
                what="Use JWT tokens instead of OAuth2 sessions",
                why=(
                    "JWT tokens are stateless and easier to scale. "
                    "We can avoid session storage in database."
                ),
                impact="major",
                affected_tasks=["task-001", "task-002"],
                confidence=0.8,
            ),
            Decision(
                decision_id="dec-002",
                task_id="task-002",
                agent_id="agent-1",
                timestamp=datetime(2025, 11, 2, 14, 0, tzinfo=timezone.utc),
                what="Use React for frontend instead of vanilla JS",
                why="Better component reusability and state management",
                impact="moderate",
                affected_tasks=["task-002"],
                confidence=0.9,
            ),
            Decision(
                decision_id="dec-003",
                task_id="task-003",
                agent_id="agent-2",
                timestamp=datetime(2025, 11, 3, 9, 0, tzinfo=timezone.utc),
                what="Generate CSV in-memory instead of using temp files",
                why="Simpler implementation, no cleanup needed",
                impact="minor",
                affected_tasks=["task-003"],
                confidence=0.7,
            ),
        ]

    async def test_complete_project_analysis_live(
        self, analyzer, realistic_project_tasks, realistic_project_decisions
    ):
        """
        Test complete post-project analysis with real LLM.

        This is the main integration test that verifies the entire
        PostProjectAnalyzer workflow with actual Claude API calls.
        """
        # Act
        analysis = await analyzer.analyze_project(
            project_id="test-project-001",
            tasks=realistic_project_tasks,
            decisions=realistic_project_decisions,
        )

        # Assert - Overall structure
        assert analysis.project_id == "test-project-001"
        assert analysis.summary is not None
        assert len(analysis.summary) > 0

        # Assert - Requirement divergence analysis
        assert len(analysis.requirement_divergences) == 3  # One per task

        # Should detect divergence in task-001 (OAuth2 -> JWT)
        task_001_analysis = next(
            (d for d in analysis.requirement_divergences if d.task_id == "task-001"),
            None,
        )
        assert task_001_analysis is not None
        assert (
            task_001_analysis.fidelity_score < 1.0
        ), "Should detect divergence from OAuth2 to JWT"
        assert (
            len(task_001_analysis.divergences) > 0
        ), "Should find specific divergences"

        # Verify divergence has proper structure
        divergence = task_001_analysis.divergences[0]
        assert divergence.requirement is not None
        assert divergence.implementation is not None
        assert divergence.severity in ["minor", "major", "critical"]
        assert divergence.citation is not None
        # Citation should reference either task or decision
        assert (
            "task" in divergence.citation.lower()
            or "dec" in divergence.citation.lower()
        )

        # Assert - Decision impact analysis
        assert len(analysis.decision_impacts) == 3  # One per decision

        # Check decision dec-001 which affects multiple tasks
        dec_001_analysis = next(
            (d for d in analysis.decision_impacts if d.decision_id == "dec-001"),
            None,
        )
        assert dec_001_analysis is not None
        assert len(dec_001_analysis.impact_chains) > 0

        # Verify impact chain structure
        chain = dec_001_analysis.impact_chains[0]
        # LLM may format decision ID creatively - just verify it's not empty
        assert chain.decision_id is not None and len(chain.decision_id) > 0
        assert chain.decision_summary is not None
        assert chain.citation is not None

        # Assert - Instruction quality analysis
        assert len(analysis.instruction_quality_issues) == 3  # One per task

        # Task-001 took 2x longer than estimated - quality score should reflect this
        task_001_quality = next(
            (q for q in analysis.instruction_quality_issues if q.task_id == "task-001"),
            None,
        )
        assert task_001_quality is not None
        assert 0.0 <= task_001_quality.quality_scores.overall <= 1.0

        # Verify quality scores structure
        scores = task_001_quality.quality_scores
        assert 0.0 <= scores.clarity <= 1.0
        assert 0.0 <= scores.completeness <= 1.0
        assert 0.0 <= scores.specificity <= 1.0

        # Assert - Failure diagnosis (only for failed tasks)
        assert len(analysis.failure_diagnoses) == 1  # Only task-003 failed

        failure = analysis.failure_diagnoses[0]
        assert failure.task_id == "task-003"
        assert len(failure.failure_causes) > 0, "Should identify failure causes"
        assert len(failure.prevention_strategies) > 0, "Should suggest prevention"

        # Verify failure cause structure
        cause = failure.failure_causes[0]
        assert cause.category in [
            "technical",
            "requirements",
            "process",
            "communication",
        ]
        assert cause.root_cause is not None
        assert cause.citation is not None

        # Assert - Metadata
        assert analysis.metadata["tasks_analyzed"] == 3
        assert analysis.metadata["decisions_analyzed"] == 3
        assert analysis.metadata["failed_tasks"] == 1

        # Print summary for manual inspection
        print("\n" + "=" * 70)
        print("POST-PROJECT ANALYSIS SUMMARY")
        print("=" * 70)
        print(analysis.summary)
        print("=" * 70)

    async def test_selective_analysis_requirement_only_live(
        self, analyzer, realistic_project_tasks, realistic_project_decisions
    ):
        """Test running only requirement divergence analysis with real LLM."""
        # Arrange
        scope = AnalysisScope(
            requirement_divergence=True,
            decision_impact=False,
            instruction_quality=False,
            failure_diagnosis=False,
        )

        # Act
        analysis = await analyzer.analyze_project(
            project_id="test-project-002",
            tasks=realistic_project_tasks,
            decisions=realistic_project_decisions,
            scope=scope,
        )

        # Assert
        assert len(analysis.requirement_divergences) == 3
        assert len(analysis.decision_impacts) == 0
        assert len(analysis.instruction_quality_issues) == 0
        assert len(analysis.failure_diagnoses) == 0

        # Verify requirement divergence actually ran
        task_001_analysis = next(
            (d for d in analysis.requirement_divergences if d.task_id == "task-001"),
            None,
        )
        assert task_001_analysis is not None
        assert task_001_analysis.fidelity_score >= 0.0

    async def test_analysis_with_progress_tracking_live(
        self, analyzer, realistic_project_tasks, realistic_project_decisions
    ):
        """Test that progress callbacks work during live analysis."""
        # Arrange
        progress_events = []

        async def track_progress(event):
            progress_events.append(event)
            print(
                f"\nProgress: {event.operation} - {event.message} ({event.current}/{event.total})"
            )

        # Act
        analysis = await analyzer.analyze_project(
            project_id="test-project-003",
            tasks=realistic_project_tasks[:2],  # Use fewer tasks for speed
            decisions=realistic_project_decisions[:2],
            progress_callback=track_progress,
        )

        # Assert
        assert len(progress_events) > 0, "Should have received progress updates"

        # Verify progress events have correct structure
        # Events can come from both orchestrator and individual analyzers
        valid_operations = [
            "requirement_divergence",
            "decision_impact",
            "instruction_quality",
            "failure_diagnosis",
            # AI engine also emits these detailed operation names
            "analyze_requirement_divergence",
            "analyze_decision_impact",
            "analyze_instruction_quality",
            "analyze_failure_diagnosis",
        ]
        for event in progress_events:
            assert (
                event.operation in valid_operations
            ), f"Unexpected operation: {event.operation}"
            assert event.current >= 0  # Can be 0 when starting
            assert event.total > 0
            assert event.current <= event.total
            assert event.message is not None

        # Verify analysis completed successfully
        assert analysis.project_id == "test-project-003"

    async def test_analysis_handles_edge_case_minimal_data_live(self, analyzer):
        """Test analysis with minimal data - single simple task."""
        # Arrange
        minimal_task = [
            TaskHistory(
                task_id="task-simple",
                name="Fix typo",
                description="Fix typo in homepage title",
                status="completed",
                estimated_hours=0.5,
                actual_hours=0.5,
            )
        ]

        # Act
        analysis = await analyzer.analyze_project(
            project_id="test-project-minimal",
            tasks=minimal_task,
            decisions=[],
        )

        # Assert
        assert len(analysis.requirement_divergences) == 1
        assert len(analysis.decision_impacts) == 0
        assert len(analysis.instruction_quality_issues) == 1
        assert len(analysis.failure_diagnoses) == 0

        # Verify analysis returned valid data
        simple_analysis = analysis.requirement_divergences[0]
        # Don't assume LLM's interpretation - it may find issues we don't expect
        # Just verify the score is valid (0.0 to 1.0)
        assert (
            0.0 <= simple_analysis.fidelity_score <= 1.0
        ), "Fidelity score should be between 0.0 and 1.0"
        # Verify structure is correct
        assert simple_analysis.task_id == "task-simple"
        assert isinstance(simple_analysis.divergences, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manual_inspection_live():
    """
    Manual test for inspecting detailed analysis output.

    Run this test to see the full output from all analyzers:
    pytest tests/integration/analysis/test_post_project_analyzer_live.py::test_manual_inspection_live -v -s
    """
    analyzer = PostProjectAnalyzer()

    # Create a realistic failed project scenario
    tasks = [
        TaskHistory(
            task_id="task-auth",
            name="Implement authentication",
            description=(
                "Build OAuth2 authentication with Google and GitHub providers. "
                "Store user sessions in Redis. Support remember me functionality."
            ),
            status="completed",
            estimated_hours=10.0,
            actual_hours=25.0,  # Significant overrun
        ),
        TaskHistory(
            task_id="task-api",
            name="Build REST API",
            description=(
                "Create RESTful API endpoints for user management. "
                "Support CRUD operations. Include pagination and filtering."
            ),
            status="failed",
            estimated_hours=8.0,
            actual_hours=15.0,
        ),
    ]

    decisions = [
        Decision(
            decision_id="dec-jwt",
            task_id="task-auth",
            agent_id="agent-1",
            timestamp=datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc),
            what="Use JWT tokens instead of Redis sessions",
            why="Stateless tokens are more scalable",
            impact="major",
            affected_tasks=["task-auth", "task-api"],
            confidence=0.7,
        ),
    ]

    print("\n" + "=" * 70)
    print("RUNNING COMPLETE POST-PROJECT ANALYSIS")
    print("=" * 70)

    analysis = await analyzer.analyze_project(
        project_id="manual-inspection",
        tasks=tasks,
        decisions=decisions,
    )

    # Print detailed results
    print("\n📊 EXECUTIVE SUMMARY")
    print("-" * 70)
    print(analysis.summary)

    print("\n🔍 REQUIREMENT DIVERGENCE ANALYSIS")
    print("-" * 70)
    for div_analysis in analysis.requirement_divergences:
        print(f"\nTask: {div_analysis.task_id}")
        print(f"Fidelity Score: {div_analysis.fidelity_score:.2f}")
        print(f"Divergences Found: {len(div_analysis.divergences)}")
        for div in div_analysis.divergences:
            print(
                f"  • {div.severity.upper()}: {div.requirement} → {div.implementation}"
            )
            print(f"    Citation: {div.citation}")

    print("\n🎯 DECISION IMPACT ANALYSIS")
    print("-" * 70)
    for impact in analysis.decision_impacts:
        print(f"\nDecision: {impact.decision_id}")
        print(f"Impact Chains: {len(impact.impact_chains)}")
        for chain in impact.impact_chains:
            print(f"  • {chain.decision_summary}")
            print(f"    Direct impacts: {chain.direct_impacts}")
            print(f"    Indirect impacts: {chain.indirect_impacts}")
        print(f"Unexpected Impacts: {len(impact.unexpected_impacts)}")

    print("\n📝 INSTRUCTION QUALITY ANALYSIS")
    print("-" * 70)
    for quality in analysis.instruction_quality_issues:
        print(f"\nTask: {quality.task_id}")
        print(f"Overall Quality: {quality.quality_scores.overall:.2f}")
        print(f"  Clarity: {quality.quality_scores.clarity:.2f}")
        print(f"  Completeness: {quality.quality_scores.completeness:.2f}")
        print(f"  Specificity: {quality.quality_scores.specificity:.2f}")
        print(f"Ambiguities Found: {len(quality.ambiguity_issues)}")

    print("\n❌ FAILURE DIAGNOSIS")
    print("-" * 70)
    for diagnosis in analysis.failure_diagnoses:
        print(f"\nFailed Task: {diagnosis.task_id}")
        print(f"Root Causes: {len(diagnosis.failure_causes)}")
        for cause in diagnosis.failure_causes:
            print(f"  • {cause.category.upper()}: {cause.root_cause}")
            print(f"    Evidence: {cause.evidence}")
        print(f"\nPrevention Strategies: {len(diagnosis.prevention_strategies)}")
        for strategy in diagnosis.prevention_strategies:
            print(f"  • [{strategy.priority.upper()}] {strategy.strategy}")
            print(f"    Rationale: {strategy.rationale}")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
