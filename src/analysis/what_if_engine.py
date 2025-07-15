"""
What-If Analysis Engine - Explore alternative pipeline execution paths

This module enables users to modify parameters and see how different choices
would affect the outcome, learning optimal approaches through experimentation.
"""

import copy
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.visualization.pipeline_conversation_bridge import PipelineConversationBridge
from src.visualization.shared_pipeline_events import (
    PipelineStage,
    SharedPipelineVisualizer,
)


@dataclass
class PipelineModification:
    """Represents a modification to pipeline parameters."""

    parameter: str
    original_value: Any
    new_value: Any
    description: str


@dataclass
class ComparisonResult:
    """Results of comparing two pipeline flows."""

    task_count_diff: int
    cost_diff: float
    complexity_diff: float
    quality_diff: float
    duration_diff: int
    decision_differences: List[Dict[str, Any]]
    improvement_summary: str


class WhatIfAnalysisEngine:
    """
    Engine for exploring alternative pipeline execution paths.

    Allows users to modify parameters and simulate how changes
    would affect the pipeline outcome.
    """

    def __init__(self, original_flow_id: str):
        """
        Initialize what-if analysis for a specific flow.

        Parameters
        ----------
        original_flow_id : str
            The original pipeline flow ID to analyze
        """
        self.original_flow_id = original_flow_id
        self.shared_events = SharedPipelineVisualizer()
        self.original_flow = self._load_flow(original_flow_id)
        self.variations = []

    def _load_flow(self, flow_id: str) -> Dict[str, Any]:
        """Load complete flow data including all events."""
        events = self.shared_events.shared_events.get_flow_events(flow_id)

        # Extract flow metadata
        flow_data = {
            "flow_id": flow_id,
            "events": events,
            "metrics": self._extract_metrics(events),
            "decisions": self._extract_decisions(events),
            "parameters": self._extract_parameters(events),
        }

        return flow_data

    def _extract_metrics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract key metrics from flow events."""
        metrics = {
            "total_duration_ms": 0,
            "total_cost": 0,
            "task_count": 0,
            "complexity_score": 0,
            "quality_score": 0,
            "token_usage": 0,
        }

        for event in events:
            data = event.get("data", {})

            # Extract metrics based on event type
            if event.get("event_type") == "pipeline_completed":
                metrics["total_duration_ms"] = data.get("total_duration_ms", 0)
            elif event.get("event_type") == "tasks_generated":
                metrics["task_count"] = data.get("task_count", 0)
                metrics["complexity_score"] = data.get("complexity_score", 0)
            elif event.get("event_type") == "quality_metrics":
                metrics["quality_score"] = data.get("overall_quality_score", 0)
            elif event.get("event_type") == "performance_metrics":
                metrics["token_usage"] += data.get("token_usage", 0)
                metrics["total_cost"] += data.get("cost_estimate", 0)

        return metrics

    def _extract_decisions(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract all decision points from flow."""
        decisions = []

        for event in events:
            if event.get("event_type") == "decision_point":
                decisions.append(
                    {
                        "timestamp": event.get("timestamp"),
                        "stage": event.get("stage"),
                        "decision": event.get("data", {}).get("decision"),
                        "confidence": event.get("data", {}).get("confidence"),
                        "alternatives": event.get("data", {}).get(
                            "alternatives_considered", []
                        ),
                    }
                )

        return decisions

    def _extract_parameters(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract configurable parameters from flow."""
        parameters = {
            "team_size": 3,
            "ai_model": "gpt-4",
            "generation_strategy": "requirement_based",
            "confidence_threshold": 0.7,
            "max_task_complexity": 1.0,
            "include_testing_tasks": True,
            "include_documentation_tasks": True,
        }

        # Extract from events
        for event in events:
            data = event.get("data", {})

            if event.get("event_type") == "create_project_request":
                options = data.get("options", {})
                if "team_size" in options:
                    parameters["team_size"] = options["team_size"]

            elif event.get("event_type") == "ai_prd_analysis":
                ai_metrics = data.get("ai_metrics", {})
                if "model" in ai_metrics:
                    parameters["ai_model"] = ai_metrics["model"]

        return parameters

    async def simulate_variation(
        self, modifications: List[PipelineModification]
    ) -> Dict[str, Any]:
        """
        Simulate pipeline with modified parameters.

        Parameters
        ----------
        modifications : List[PipelineModification]
            List of parameter modifications to apply

        Returns
        -------
        Dict[str, Any]
            Simulated flow with comparison data
        """
        # Create new flow ID for variation
        variation_flow_id = str(uuid.uuid4())

        # Clone original parameters
        modified_params = copy.deepcopy(self.original_flow["parameters"])

        # Apply modifications
        for mod in modifications:
            modified_params[mod.parameter] = mod.new_value

        # Simulate the flow based on modifications
        simulated_flow = await self._simulate_flow(
            variation_flow_id, modified_params, modifications
        )

        # Store variation for later analysis
        self.variations.append(
            {
                "variation_id": variation_flow_id,
                "modifications": modifications,
                "simulated_flow": simulated_flow,
                "comparison": self.compare_flows(self.original_flow, simulated_flow),
            }
        )

        return simulated_flow

    async def _simulate_flow(
        self,
        flow_id: str,
        parameters: Dict[str, Any],
        modifications: List[PipelineModification],
    ) -> Dict[str, Any]:
        """Simulate a pipeline flow with given parameters."""
        # This is a simplified simulation - in production, you'd re-run
        # the actual pipeline with modified parameters

        simulated_events = []
        simulated_metrics = copy.deepcopy(self.original_flow["metrics"])

        # Simulate impact of modifications
        for mod in modifications:
            if mod.parameter == "team_size":
                # More team members = potentially more parallel tasks
                if mod.new_value > mod.original_value:
                    simulated_metrics["task_count"] = int(
                        simulated_metrics["task_count"] * 1.2
                    )
                    simulated_metrics["complexity_score"] *= 1.1
                else:
                    simulated_metrics["task_count"] = int(
                        simulated_metrics["task_count"] * 0.9
                    )
                    simulated_metrics["complexity_score"] *= 0.95

            elif mod.parameter == "ai_model":
                # Different models have different costs and quality
                if mod.new_value == "gpt-3.5":
                    simulated_metrics["total_cost"] *= 0.1  # Much cheaper
                    simulated_metrics["quality_score"] *= 0.85  # Slightly lower quality
                    simulated_metrics["total_duration_ms"] *= 0.7  # Faster
                elif mod.new_value == "claude":
                    simulated_metrics["total_cost"] *= 1.2
                    simulated_metrics["quality_score"] *= 1.05

            elif mod.parameter == "generation_strategy":
                if mod.new_value == "minimal":
                    simulated_metrics["task_count"] = int(
                        simulated_metrics["task_count"] * 0.6
                    )
                    simulated_metrics["complexity_score"] *= 0.7
                elif mod.new_value == "detailed":
                    simulated_metrics["task_count"] = int(
                        simulated_metrics["task_count"] * 1.5
                    )
                    simulated_metrics["complexity_score"] *= 1.3

            elif mod.parameter == "include_testing_tasks":
                if mod.new_value and not mod.original_value:
                    simulated_metrics["task_count"] += int(
                        simulated_metrics["task_count"] * 0.3
                    )
                    simulated_metrics["quality_score"] = min(
                        1.0, simulated_metrics["quality_score"] * 1.2
                    )

        # Create simulated flow
        return {
            "flow_id": flow_id,
            "events": simulated_events,
            "metrics": simulated_metrics,
            "decisions": self._simulate_decisions(parameters),
            "parameters": parameters,
            "is_simulation": True,
        }

    def _simulate_decisions(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simulate decision points based on parameters."""
        decisions = []

        # Simulate architecture decision based on team size
        if parameters["team_size"] > 5:
            decisions.append(
                {
                    "decision": "Use microservices architecture",
                    "confidence": 0.85,
                    "reasoning": f"Large team of {parameters['team_size']} benefits from service isolation",
                }
            )
        else:
            decisions.append(
                {
                    "decision": "Use monolithic architecture",
                    "confidence": 0.9,
                    "reasoning": f"Small team of {parameters['team_size']} benefits from simplicity",
                }
            )

        return decisions

    def compare_flows(
        self, flow_a: Dict[str, Any], flow_b: Dict[str, Any]
    ) -> ComparisonResult:
        """
        Compare two pipeline flows.

        Parameters
        ----------
        flow_a : Dict[str, Any]
            First flow (typically original)
        flow_b : Dict[str, Any]
            Second flow (typically variation)

        Returns
        -------
        ComparisonResult
            Detailed comparison between the flows
        """
        metrics_a = flow_a["metrics"]
        metrics_b = flow_b["metrics"]

        # Calculate differences
        task_diff = metrics_b["task_count"] - metrics_a["task_count"]
        cost_diff = metrics_b["total_cost"] - metrics_a["total_cost"]
        complexity_diff = metrics_b["complexity_score"] - metrics_a["complexity_score"]
        quality_diff = metrics_b["quality_score"] - metrics_a["quality_score"]
        duration_diff = metrics_b["total_duration_ms"] - metrics_a["total_duration_ms"]

        # Compare decisions
        decision_diffs = self._compare_decisions(
            flow_a["decisions"], flow_b["decisions"]
        )

        # Generate improvement summary
        improvements = []
        if quality_diff > 0:
            improvements.append(f"Quality improved by {quality_diff * 100:.1f}%")
        if cost_diff < 0:
            improvements.append(f"Cost reduced by ${-cost_diff:.2f}")
        if duration_diff < 0:
            improvements.append(f"Time saved: {-duration_diff / 1000:.1f}s")

        improvement_summary = (
            " | ".join(improvements) if improvements else "No significant improvements"
        )

        return ComparisonResult(
            task_count_diff=task_diff,
            cost_diff=cost_diff,
            complexity_diff=complexity_diff,
            quality_diff=quality_diff,
            duration_diff=duration_diff,
            decision_differences=decision_diffs,
            improvement_summary=improvement_summary,
        )

    def _compare_decisions(
        self, decisions_a: List[Dict[str, Any]], decisions_b: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Compare decision points between flows."""
        differences = []

        # Simple comparison - in production, use more sophisticated matching
        for i, dec_b in enumerate(decisions_b):
            if i < len(decisions_a):
                dec_a = decisions_a[i]
                if dec_a["decision"] != dec_b["decision"]:
                    differences.append(
                        {
                            "original": dec_a["decision"],
                            "variation": dec_b["decision"],
                            "confidence_change": dec_b["confidence"]
                            - dec_a["confidence"],
                        }
                    )
            else:
                differences.append(
                    {
                        "original": None,
                        "variation": dec_b["decision"],
                        "confidence_change": dec_b["confidence"],
                    }
                )

        return differences

    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """
        Generate optimization suggestions based on variations.

        Returns
        -------
        List[Dict[str, Any]]
            List of suggested optimizations with expected impact
        """
        suggestions = []

        # Analyze all variations to find best performing
        best_quality = self.original_flow["metrics"]["quality_score"]
        best_cost = self.original_flow["metrics"]["total_cost"]
        best_speed = self.original_flow["metrics"]["total_duration_ms"]

        for variation in self.variations:
            metrics = variation["simulated_flow"]["metrics"]
            comparison = variation["comparison"]

            # Quality improvement
            if metrics["quality_score"] > best_quality:
                suggestions.append(
                    {
                        "type": "quality",
                        "modifications": variation["modifications"],
                        "impact": f"Improve quality by {comparison.quality_diff * 100:.1f}%",
                        "trade_offs": self._identify_tradeoffs(comparison),
                    }
                )

            # Cost reduction
            if metrics["total_cost"] < best_cost and comparison.quality_diff >= -0.05:
                suggestions.append(
                    {
                        "type": "cost",
                        "modifications": variation["modifications"],
                        "impact": f"Reduce cost by ${-comparison.cost_diff:.2f}",
                        "trade_offs": self._identify_tradeoffs(comparison),
                    }
                )

        return suggestions

    def _identify_tradeoffs(self, comparison: ComparisonResult) -> List[str]:
        """Identify trade-offs in a comparison."""
        tradeoffs = []

        if comparison.quality_diff < 0:
            tradeoffs.append(
                f"Quality reduced by {-comparison.quality_diff * 100:.1f}%"
            )
        if comparison.cost_diff > 0:
            tradeoffs.append(f"Cost increased by ${comparison.cost_diff:.2f}")
        if comparison.complexity_diff > 0:
            tradeoffs.append(
                f"Complexity increased by {comparison.complexity_diff * 100:.1f}%"
            )

        return tradeoffs

    def export_analysis_results(self) -> Dict[str, Any]:
        """Export complete what-if analysis results."""
        return {
            "original_flow_id": self.original_flow_id,
            "original_metrics": self.original_flow["metrics"],
            "variations_tested": len(self.variations),
            "variations": [
                {
                    "variation_id": v["variation_id"],
                    "modifications": [asdict(m) for m in v["modifications"]],
                    "metrics": v["simulated_flow"]["metrics"],
                    "comparison": asdict(v["comparison"]),
                }
                for v in self.variations
            ],
            "optimization_suggestions": self.get_optimization_suggestions(),
            "analysis_timestamp": datetime.now().isoformat(),
        }
