"""
Unit tests for causal analyzer.
"""

from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from src.visualization.causal_analyzer import CausalAnalyzer, analyze_why


@pytest.fixture
def sample_snapshot_with_circular_dependency() -> Dict[str, Any]:
    """Create sample snapshot with circular dependency."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_name": "Test Project",
        "diagnostic_report": {
            "issues": [
                {
                    "type": "circular_dependency",
                    "affected_count": 3,
                    "severity": "critical",
                }
            ]
        },
        "early_completions": [],
        "conversation_history": [],
        "task_completion_timeline": [],
    }


@pytest.fixture
def sample_snapshot_with_premature_completion() -> Dict[str, Any]:
    """Create sample snapshot with premature task completion."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_name": "Test Project",
        "diagnostic_report": {"issues": []},
        "early_completions": [
            {
                "task_name": "Deploy to Production",
                "completion_percentage": 60.0,
                "issue": "Completed at 60% progress",
            },
            {
                "task_name": "Mark as Complete",
                "completion_percentage": 55.0,
                "issue": "Completed at 55% progress",
            },
        ],
        "conversation_history": [],
        "task_completion_timeline": [
            {"task_name": "Setup", "timestamp": "2025-10-06T10:00:00"},
            {"task_name": "Build", "timestamp": "2025-10-06T11:00:00"},
            {"task_name": "Deploy to Production", "timestamp": "2025-10-06T12:00:00"},
            {"task_name": "Test", "timestamp": "2025-10-06T13:00:00"},
            {"task_name": "Mark as Complete", "timestamp": "2025-10-06T14:00:00"},
        ],
    }


@pytest.fixture
def sample_snapshot_with_assignment_deadlock() -> Dict[str, Any]:
    """Create sample snapshot with assignment deadlock."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_name": "Test Project",
        "diagnostic_report": {"issues": []},
        "early_completions": [],
        "conversation_history": [
            {"type": "agent_request_task", "timestamp": "2025-10-06T10:00:00"},
            {"type": "no_task_available", "timestamp": "2025-10-06T10:01:00"},
            {"type": "agent_request_task", "timestamp": "2025-10-06T10:02:00"},
            {"type": "no_task_available", "timestamp": "2025-10-06T10:03:00"},
            {"type": "agent_request_task", "timestamp": "2025-10-06T10:04:00"},
            {"type": "no_task_available", "timestamp": "2025-10-06T10:05:00"},
            {"type": "agent_request_task", "timestamp": "2025-10-06T10:06:00"},
            {"type": "no_task_available", "timestamp": "2025-10-06T10:07:00"},
            {"type": "agent_request_task", "timestamp": "2025-10-06T10:08:00"},
            {"type": "no_task_available", "timestamp": "2025-10-06T10:09:00"},
        ],
        "task_completion_timeline": [],
    }


class TestCausalAnalyzer:
    """Test suite for CausalAnalyzer."""

    def test_find_root_causes_circular_dependency(
        self, sample_snapshot_with_circular_dependency
    ):
        """Test finding root causes identifies circular dependencies."""
        analyzer = CausalAnalyzer(sample_snapshot_with_circular_dependency)
        root_causes = analyzer._find_root_causes()

        # Should find circular dependency
        circular_cause = next(
            (c for c in root_causes if c["type"] == "circular_dependency"), None
        )
        assert circular_cause is not None
        assert circular_cause["severity"] == "critical"
        assert circular_cause["affected_tasks"] == 3
        assert "cycle" in circular_cause["explanation"].lower()
        assert "why" in circular_cause
        assert "impact" in circular_cause

    def test_find_root_causes_premature_completion(
        self, sample_snapshot_with_premature_completion
    ):
        """Test finding root causes identifies premature completions."""
        analyzer = CausalAnalyzer(sample_snapshot_with_premature_completion)
        root_causes = analyzer._find_root_causes()

        # Should find premature completion
        premature_cause = next(
            (c for c in root_causes if c["type"] == "premature_completion"), None
        )
        assert premature_cause is not None
        assert premature_cause["severity"] == "high"
        assert premature_cause["affected_tasks"] == 2
        assert "Deploy to Production" in premature_cause["explanation"]
        assert "why" in premature_cause
        assert "impact" in premature_cause

    def test_find_root_causes_assignment_deadlock(
        self, sample_snapshot_with_assignment_deadlock
    ):
        """Test finding root causes identifies assignment deadlocks."""
        analyzer = CausalAnalyzer(sample_snapshot_with_assignment_deadlock)
        root_causes = analyzer._find_root_causes()

        # Should find assignment deadlock (5+ no_task events)
        deadlock_cause = next(
            (c for c in root_causes if c["type"] == "assignment_deadlock"), None
        )
        assert deadlock_cause is not None
        assert deadlock_cause["severity"] == "critical"
        assert "no progress possible" in deadlock_cause["impact"].lower()
        assert "why" in deadlock_cause

    def test_build_causal_chains_circular_dependency(
        self, sample_snapshot_with_circular_dependency
    ):
        """Test building causal chains for circular dependency."""
        analyzer = CausalAnalyzer(sample_snapshot_with_circular_dependency)
        chains = analyzer._build_causal_chains()

        # Should have at least one chain
        assert len(chains) > 0

        # Find circular dependency chain
        circular_chain = next(
            (c for c in chains if "circular" in c["root_cause"].lower()), None
        )
        assert circular_chain is not None
        assert "chain" in circular_chain
        assert len(circular_chain["chain"]) >= 4  # Multi-step chain
        assert circular_chain["final_impact"] is not None

        # Each step should have event and why
        for step in circular_chain["chain"]:
            assert "event" in step
            assert "why" in step

    def test_build_causal_chains_premature_completion(
        self, sample_snapshot_with_premature_completion
    ):
        """Test building causal chains for premature completion."""
        analyzer = CausalAnalyzer(sample_snapshot_with_premature_completion)
        chains = analyzer._build_causal_chains()

        # Should have premature completion chain
        premature_chain = next(
            (c for c in chains if "final tasks completed" in c["root_cause"].lower()),
            None,
        )
        assert premature_chain is not None
        assert len(premature_chain["chain"]) >= 4
        assert "confusion" in premature_chain["chain"][-1]["event"].lower()

    def test_find_intervention_points(self, sample_snapshot_with_premature_completion):
        """Test finding intervention points."""
        analyzer = CausalAnalyzer(sample_snapshot_with_premature_completion)
        interventions = analyzer._find_intervention_points()

        # Should find intervention opportunities
        assert len(interventions) > 0

        # Each intervention should have required fields
        for intervention in interventions:
            assert "timing" in intervention
            assert "trigger" in intervention
            assert "action" in intervention
            assert "prevention" in intervention
            assert "window" in intervention

    def test_find_intervention_points_for_early_completion(
        self, sample_snapshot_with_premature_completion
    ):
        """Test finding intervention points catches early completions."""
        analyzer = CausalAnalyzer(sample_snapshot_with_premature_completion)
        interventions = analyzer._find_intervention_points()

        # Should have intervention for "Deploy to Production" completed early
        deploy_intervention = next(
            (
                i
                for i in interventions
                if "Deploy to Production" in i.get("trigger", "")
            ),
            None,
        )
        assert deploy_intervention is not None
        assert "dependencies" in deploy_intervention["action"].lower()

    def test_analyze_human_decisions(self, sample_snapshot_with_premature_completion):
        """Test analyzing human decisions."""
        analyzer = CausalAnalyzer(sample_snapshot_with_premature_completion)
        decisions = analyzer._analyze_human_decisions()

        # Should find decisions about premature completion
        assert len(decisions) > 0

        premature_decision = next(
            (d for d in decisions if "premature" in d["decision"].lower()), None
        )
        assert premature_decision is not None
        assert "when" in premature_decision
        assert "impact" in premature_decision
        assert "why_problematic" in premature_decision
        assert "alternative" in premature_decision
        assert premature_decision["severity"] in ["low", "medium", "high", "critical"]

    def test_build_narrative(self, sample_snapshot_with_premature_completion):
        """Test building narrative."""
        analyzer = CausalAnalyzer(sample_snapshot_with_premature_completion)
        narrative = analyzer._build_narrative()

        # Should be a non-empty string
        assert isinstance(narrative, str)
        assert len(narrative) > 100

        # Should contain key sections
        assert "ROOT CAUSE ANALYSIS" in narrative
        assert "HOW IT UNFOLDED" in narrative
        assert "WHERE WE COULD HAVE INTERVENED" in narrative
        assert "BOTTOM LINE" in narrative

        # Should mention project name
        assert "Test Project" in narrative

    def test_analyze_complete_workflow(self, sample_snapshot_with_premature_completion):
        """Test complete analysis workflow."""
        analyzer = CausalAnalyzer(sample_snapshot_with_premature_completion)
        analysis = analyzer.analyze()

        # Should have all required sections
        assert "root_causes" in analysis
        assert "causal_chains" in analysis
        assert "intervention_points" in analysis
        assert "human_decisions" in analysis
        assert "narrative" in analysis

        # All sections should be populated
        assert len(analysis["root_causes"]) > 0
        assert len(analysis["causal_chains"]) > 0
        assert len(analysis["intervention_points"]) > 0
        assert len(analysis["human_decisions"]) > 0
        assert len(analysis["narrative"]) > 100

    def test_analyze_why_function(self, sample_snapshot_with_premature_completion):
        """Test the analyze_why convenience function."""
        analysis = analyze_why(sample_snapshot_with_premature_completion)

        # Should return same structure as analyzer.analyze()
        assert "root_causes" in analysis
        assert "causal_chains" in analysis
        assert "intervention_points" in analysis
        assert "human_decisions" in analysis
        assert "narrative" in analysis

    def test_empty_snapshot(self):
        """Test analyzer handles empty snapshot gracefully."""
        empty_snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_name": "Empty Project",
            "diagnostic_report": {"issues": []},
            "early_completions": [],
            "conversation_history": [],
            "task_completion_timeline": [],
        }

        analyzer = CausalAnalyzer(empty_snapshot)
        analysis = analyzer.analyze()

        # Should not crash, but have empty lists
        assert analysis["root_causes"] == []
        assert len(analysis["narrative"]) > 0  # Still builds a narrative

    def test_multiple_root_causes(self):
        """Test analyzer identifies multiple root causes."""
        complex_snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_name": "Complex Project",
            "diagnostic_report": {
                "issues": [
                    {"type": "circular_dependency", "affected_count": 3},
                    {"type": "bottleneck", "affected_count": 5},
                    {"type": "missing_dependency", "affected_count": 2},
                ]
            },
            "early_completions": [
                {
                    "task_name": "Final Task",
                    "completion_percentage": 50.0,
                    "issue": "Too early",
                }
            ],
            "conversation_history": [
                {"type": "no_task_available"} for _ in range(6)
            ],  # 6 no_task events
            "task_completion_timeline": [],
        }

        analyzer = CausalAnalyzer(complex_snapshot)
        root_causes = analyzer._find_root_causes()

        # Should find multiple root causes
        assert len(root_causes) >= 4  # At least 4 different types of issues
        cause_types = [c["type"] for c in root_causes]
        assert "circular_dependency" in cause_types
        assert "critical_bottleneck" in cause_types
        assert "premature_completion" in cause_types
        assert "assignment_deadlock" in cause_types
