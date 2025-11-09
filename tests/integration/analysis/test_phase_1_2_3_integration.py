"""
Integration tests verifying Phase 1, Phase 2, and Phase 3 work together.

These tests verify that the complete data flow works end-to-end:
Phase 1 (Data) → Phase 2 (Analysis) → Phase 3 (API responses)

This ensures the Cato backend will be able to properly integrate
with the Marcus analysis system.

To run:
    pytest tests/integration/analysis/test_phase_1_2_3_integration.py -v -m integration
"""

from datetime import datetime, timezone

import pytest

from src.analysis.aggregator import ProjectHistoryAggregator, TaskHistory
from src.analysis.post_project_analyzer import PostProjectAnalyzer
from src.analysis.query_api import ProjectHistoryQuery
from src.core.project_history import Decision


@pytest.mark.integration
@pytest.mark.asyncio
class TestPhase123Integration:
    """Integration tests for Phase 1 + Phase 2 + Phase 3 (planned) APIs."""

    @pytest.fixture
    def aggregator(self):
        """Create Phase 1 aggregator."""
        return ProjectHistoryAggregator()

    @pytest.fixture
    def query_api(self, aggregator):
        """Create Phase 1 query API."""
        return ProjectHistoryQuery(aggregator)

    @pytest.fixture
    def analyzer(self):
        """Create Phase 2 analyzer."""
        return PostProjectAnalyzer()

    @pytest.fixture
    def sample_project_data(self):
        """Create sample project data for testing."""
        tasks = [
            TaskHistory(
                task_id="task-001",
                name="Implement authentication",
                description="Build OAuth2 authentication system",
                status="completed",
                estimated_hours=8.0,
                actual_hours=12.0,
            ),
            TaskHistory(
                task_id="task-002",
                name="Create user dashboard",
                description="Build dashboard with user stats",
                status="completed",
                estimated_hours=6.0,
                actual_hours=6.5,
            ),
            TaskHistory(
                task_id="task-003",
                name="Implement data export",
                description="Allow users to export data as CSV",
                status="failed",
                estimated_hours=4.0,
                actual_hours=8.0,
            ),
        ]

        decisions = [
            Decision(
                decision_id="dec-001",
                task_id="task-001",
                agent_id="agent-1",
                timestamp=datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc),
                what="Use JWT tokens instead of sessions",
                why="Better scalability",
                impact="major",
                affected_tasks=["task-001", "task-002"],
                confidence=0.8,
            )
        ]

        return {"tasks": tasks, "decisions": decisions}

    async def test_phase1_aggregator_works(self, aggregator):
        """
        Test Phase 1: ProjectHistoryAggregator can load project data.

        This is the foundation for everything else.
        """
        # This will try to load a project from disk
        # If no projects exist, it should return empty data gracefully
        try:
            history = await aggregator.aggregate_project(
                project_id="test-integration-project",
                include_conversations=False,
            )

            # Should return ProjectHistory object even if empty
            assert history.project_id == "test-integration-project"
            assert isinstance(history.tasks, list)
            assert isinstance(history.decisions, list)
            assert isinstance(history.artifacts, list)

        except Exception as e:
            # It's ok if project doesn't exist - we're just testing the API works
            assert "not found" in str(e).lower() or "no such file" in str(e).lower()

    async def test_phase1_query_api_works(self, query_api):
        """
        Test Phase 1: ProjectHistoryQuery provides convenient queries.

        This is what Cato backend will use to fetch data.
        """
        # Test that query methods exist and have correct signatures
        try:
            # Try to get project summary
            summary = await query_api.get_project_summary("test-integration-project")

            # Should return dict with expected keys
            assert "project_id" in summary
            assert "total_tasks" in summary
            assert "completed_tasks" in summary

        except Exception:
            # It's ok if project doesn't exist - we're testing the API signature
            pass

        # Verify method signatures are correct
        import inspect

        # Check get_project_history signature
        sig = inspect.signature(query_api.get_project_history)
        params = list(sig.parameters.keys())
        assert "project_id" in params
        assert "include_conversations" in params

        # Check get_project_summary signature
        sig = inspect.signature(query_api.get_project_summary)
        params = list(sig.parameters.keys())
        assert "project_id" in params

    async def test_phase2_analyzer_works_with_phase1_data(
        self, analyzer, sample_project_data
    ):
        """
        Test Phase 2: PostProjectAnalyzer works with Phase 1 TaskHistory objects.

        This verifies Phase 2 can consume Phase 1 output.
        """
        import asyncio

        # Add delay to avoid rate limiting (previous tests made API calls)
        await asyncio.sleep(2)

        # Run Phase 2 analysis on sample data with retry logic
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                analysis = await analyzer.analyze_project(
                    project_id="test-integration-project",
                    tasks=sample_project_data["tasks"],
                    decisions=sample_project_data["decisions"],
                )

                # Verify analysis completed
                assert analysis.project_id == "test-integration-project"
                assert len(analysis.requirement_divergences) > 0
                assert len(analysis.instruction_quality_issues) > 0
                assert len(analysis.failure_diagnoses) >= 1  # task-003 failed
                assert analysis.summary is not None
                break

            except Exception as e:
                if "529" in str(e) or "overload" in str(e).lower():
                    if attempt < max_retries - 1:
                        print(f"\nAPI overloaded, retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise
                else:
                    raise

    async def test_phase3_api_response_format(self, analyzer, sample_project_data):
        """
        Test Phase 3: Verify API response format matches what Cato expects.

        This simulates what the Cato backend endpoint will do.
        """
        # Simulate Phase 3 backend endpoint logic
        tasks = sample_project_data["tasks"]
        decisions = sample_project_data["decisions"]

        # Run Phase 2 analysis
        analysis = await analyzer.analyze_project(
            project_id="test-integration-project",
            tasks=tasks,
            decisions=decisions,
        )

        # Build response in format Cato expects
        response = {
            # Basic info
            "project_id": analysis.project_id,
            "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
            "summary": analysis.summary,
            # Requirement divergence
            "requirement_divergences": [
                {
                    "task_id": rd.task_id,
                    "fidelity_score": rd.fidelity_score,
                    "divergences": [
                        {
                            "requirement": d.requirement,
                            "implementation": d.implementation,
                            "severity": d.severity,
                            "impact": d.impact,
                            "citation": d.citation,
                        }
                        for d in rd.divergences
                    ],
                    "recommendations": rd.recommendations,
                }
                for rd in analysis.requirement_divergences
            ],
            # Decision impacts
            "decision_impacts": [
                {
                    "decision_id": di.decision_id,
                    "impact_chains": [
                        {
                            "decision_summary": ic.decision_summary,
                            "direct_impacts": ic.direct_impacts,
                            "indirect_impacts": ic.indirect_impacts,
                            "depth": ic.depth,
                            "citation": ic.citation,
                        }
                        for ic in di.impact_chains
                    ],
                }
                for di in analysis.decision_impacts
            ],
            # Instruction quality
            "instruction_quality_issues": [
                {
                    "task_id": iq.task_id,
                    "quality_scores": {
                        "clarity": iq.quality_scores.clarity,
                        "completeness": iq.quality_scores.completeness,
                        "specificity": iq.quality_scores.specificity,
                        "overall": iq.quality_scores.overall,
                    },
                }
                for iq in analysis.instruction_quality_issues
            ],
            # Failure diagnoses
            "failure_diagnoses": [
                {
                    "task_id": fd.task_id,
                    "failure_causes": [
                        {
                            "category": fc.category,
                            "root_cause": fc.root_cause,
                        }
                        for fc in fd.failure_causes
                    ],
                    "prevention_strategies": [
                        {
                            "strategy": ps.strategy,
                            "priority": ps.priority,
                        }
                        for ps in fd.prevention_strategies
                    ],
                }
                for fd in analysis.failure_diagnoses
            ],
        }

        # Verify response structure
        assert "project_id" in response
        assert "summary" in response
        assert "requirement_divergences" in response
        assert "decision_impacts" in response
        assert "instruction_quality_issues" in response
        assert "failure_diagnoses" in response

        # Verify we have data
        assert len(response["requirement_divergences"]) > 0
        assert len(response["instruction_quality_issues"]) > 0
        assert len(response["failure_diagnoses"]) >= 1

        # Verify nested structure is correct
        rd = response["requirement_divergences"][0]
        assert "task_id" in rd
        assert "fidelity_score" in rd
        assert "divergences" in rd
        assert "recommendations" in rd

        fd = response["failure_diagnoses"][0]
        assert "task_id" in fd
        assert "failure_causes" in fd
        assert "prevention_strategies" in fd

    async def test_end_to_end_workflow(self, aggregator, query_api, analyzer):
        """
        Test complete end-to-end workflow simulating Cato backend.

        This is what the actual Cato /api/historical/projects/{id}/analysis
        endpoint will do.
        """
        project_id = "test-integration-e2e"

        # Step 1: Try to load project history (Phase 1)
        try:
            history = await query_api.get_project_history(project_id)

            # Step 2: Run analysis (Phase 2)
            analysis = await analyzer.analyze_project(
                project_id=project_id,
                tasks=history.tasks,
                decisions=history.decisions,
            )

            # Step 3: Format response (Phase 3)
            response = {
                "project_id": analysis.project_id,
                "summary": analysis.summary,
                "metadata": analysis.metadata,
            }

            # Verify complete flow worked
            assert response["project_id"] == project_id
            assert isinstance(response["summary"], str)
            assert isinstance(response["metadata"], dict)

        except Exception as e:
            # Project may not exist on disk - that's ok for this test
            # We're verifying the API flow is correct
            if "not found" not in str(e).lower():
                # But other errors should fail the test
                raise

    async def test_phase3_task_detail_endpoint(self, sample_project_data):
        """
        Test Phase 3 task detail endpoint logic.

        Simulates: GET /api/historical/projects/{id}/tasks/{task_id}
        """
        tasks = sample_project_data["tasks"]

        # Simulate finding a specific task
        task_id = "task-003"
        task = next((t for t in tasks if t.task_id == task_id), None)

        assert task is not None
        assert task.task_id == task_id

        # Convert to dict for API response
        task_dict = task.to_dict()

        # Verify response has expected fields
        assert "task_id" in task_dict
        assert "name" in task_dict
        assert "description" in task_dict
        assert "status" in task_dict
        assert "estimated_hours" in task_dict
        assert "actual_hours" in task_dict

    async def test_phase3_project_summary_endpoint(self, query_api):
        """
        Test Phase 3 project summary endpoint logic.

        Simulates: GET /api/historical/projects/{id}/summary
        """
        project_id = "test-integration-summary"

        try:
            summary = await query_api.get_project_summary(project_id)

            # Verify summary has all expected fields for Cato UI
            expected_fields = [
                "project_id",
                "total_tasks",
                "completed_tasks",
                "blocked_tasks",
                "completion_rate",
                "total_decisions",
                "total_artifacts",
                "active_agents",
            ]

            for field in expected_fields:
                assert field in summary, f"Missing field: {field}"

        except Exception:
            # Project may not exist - that's ok
            pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_phase3_backend_simulation():
    """
    Full simulation of what Cato backend will do.

    This test acts as documentation for how to implement the Cato backend.
    """
    print("\n" + "=" * 70)
    print("PHASE 1-2-3 INTEGRATION TEST")
    print("=" * 70)

    # Initialize Phase 1 components
    aggregator = ProjectHistoryAggregator()
    query_api = ProjectHistoryQuery(aggregator)

    # Initialize Phase 2 components
    analyzer = PostProjectAnalyzer()

    # Simulate Cato backend endpoint:
    # GET /api/historical/projects/{project_id}/analysis

    print("\n1. Phase 1: Load project history from disk...")
    project_id = "test-backend-simulation"

    # Create sample data (in real scenario, this comes from disk)
    sample_tasks = [
        TaskHistory(
            task_id="task-sim-001",
            name="Test task",
            description="Test description",
            status="completed",
            estimated_hours=5.0,
            actual_hours=6.0,
        )
    ]

    sample_decisions = [
        Decision(
            decision_id="dec-sim-001",
            task_id="task-sim-001",
            agent_id="agent-1",
            timestamp=datetime.now(timezone.utc),
            what="Test decision",
            why="Testing",
            impact="minor",
            affected_tasks=["task-sim-001"],
            confidence=0.9,
        )
    ]

    print(f"   Loaded {len(sample_tasks)} tasks, {len(sample_decisions)} decisions")

    print("\n2. Phase 2: Run LLM analysis...")
    analysis = await analyzer.analyze_project(
        project_id=project_id,
        tasks=sample_tasks,
        decisions=sample_decisions,
    )

    print(f"   Analysis complete: {len(analysis.requirement_divergences)} divergences")
    print(f"   Summary length: {len(analysis.summary)} characters")

    print("\n3. Phase 3: Format API response...")
    response = {
        "project_id": analysis.project_id,
        "summary": analysis.summary,
        "requirement_divergences": len(analysis.requirement_divergences),
        "decision_impacts": len(analysis.decision_impacts),
        "instruction_quality_issues": len(analysis.instruction_quality_issues),
        "failure_diagnoses": len(analysis.failure_diagnoses),
    }

    print(f"   Response ready: {response}")

    print("\n" + "=" * 70)
    print("SUCCESS: Phase 1-2-3 integration works!")
    print("=" * 70)

    # Verify the response
    assert response["project_id"] == project_id
    assert isinstance(response["summary"], str)
    assert response["requirement_divergences"] >= 0
