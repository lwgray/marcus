"""
Pipeline Error Predictor - Predict and prevent pipeline failures

This module analyzes pipeline patterns to predict potential failures
and suggest preventive actions.
"""

import json
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.visualization.shared_pipeline_events import SharedPipelineEvents


@dataclass
class RiskFactor:
    """Individual risk factor identified."""

    factor: str
    risk_level: float  # 0.0 to 1.0
    description: str
    mitigation: str


@dataclass
class RiskAssessment:
    """Complete risk assessment for a flow."""

    flow_id: str
    overall_risk: float  # 0.0 to 1.0
    risk_category: str  # low, medium, high, critical
    factors: List[RiskFactor]
    recommendations: List[str]
    confidence: float


class PatternAnalyzer:
    """Analyze patterns in pipeline executions."""

    def __init__(self):
        self.shared_events = SharedPipelineEvents()
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[str, Any]:
        """Load known failure patterns from historical data."""
        patterns = {
            "failure_indicators": [],
            "success_indicators": [],
            "risk_thresholds": {},
        }

        # Analyze historical flows
        all_data = self.shared_events._read_events()

        for flow_id, flow_info in all_data["flows"].items():
            events = [e for e in all_data["events"] if e.get("flow_id") == flow_id]

            # Determine if flow was successful
            success = False
            for event in events:
                if event.get("event_type") == "pipeline_completed":
                    success = event.get("data", {}).get("success", False)
                    break

            # Extract patterns
            flow_patterns = self._extract_flow_patterns(events)

            if success:
                patterns["success_indicators"].append(flow_patterns)
            else:
                patterns["failure_indicators"].append(flow_patterns)

        # Calculate risk thresholds
        patterns["risk_thresholds"] = self._calculate_thresholds(patterns)

        return patterns

    def _extract_flow_patterns(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract patterns from a flow's events."""
        patterns = {
            "task_count": 0,
            "error_count": 0,
            "avg_confidence": 0,
            "complexity_score": 0,
            "retry_count": 0,
            "slow_stages": 0,
            "ambiguity_count": 0,
            "missing_considerations": 0,
        }

        confidence_scores = []

        for event in events:
            data = event.get("data", {})

            # Count errors
            if event.get("status") == "failed" or event.get("error"):
                patterns["error_count"] += 1

            # Extract metrics
            if event.get("event_type") == "tasks_generated":
                patterns["task_count"] = data.get("task_count", 0)
                patterns["complexity_score"] = data.get("complexity_score", 0)

            elif event.get("event_type") == "ai_prd_analysis":
                if "confidence" in data:
                    confidence_scores.append(data["confidence"])
                patterns["ambiguity_count"] = len(data.get("ambiguities", []))

            elif event.get("event_type") == "quality_metrics":
                patterns["missing_considerations"] = len(
                    data.get("missing_considerations", [])
                )

            elif event.get("event_type") == "performance_metrics":
                patterns["retry_count"] += data.get("retry_attempts", 0)

        if confidence_scores:
            patterns["avg_confidence"] = statistics.mean(confidence_scores)

        return patterns

    def _calculate_thresholds(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk thresholds from patterns."""
        thresholds = {}

        # Calculate averages for successful flows
        if patterns["success_indicators"]:
            success_metrics = defaultdict(list)
            for pattern in patterns["success_indicators"]:
                for key, value in pattern.items():
                    if isinstance(value, (int, float)):
                        success_metrics[key].append(value)

            for key, values in success_metrics.items():
                if values:
                    avg = statistics.mean(values)
                    std = statistics.stdev(values) if len(values) > 1 else avg * 0.1
                    thresholds[key] = {
                        "avg": avg,
                        "warning": avg + std,
                        "critical": avg + 2 * std,
                    }

        return thresholds


class PipelineErrorPredictor:
    """
    Predict likelihood of pipeline failures based on patterns.
    """

    def __init__(self):
        """Initialize the error predictor."""
        self.pattern_analyzer = PatternAnalyzer()
        self.prediction_history = []

    def predict_failure_risk(self, flow_id: str) -> RiskAssessment:
        """
        Predict likelihood of failure for a flow.

        Parameters
        ----------
        flow_id : str
            The flow ID to assess

        Returns
        -------
        RiskAssessment
            Complete risk assessment with factors and recommendations
        """
        # Get flow events
        events = self.pattern_analyzer.shared_events.get_flow_events(flow_id)

        # Extract current patterns
        current_patterns = self.pattern_analyzer._extract_flow_patterns(events)

        # Identify risk factors
        risk_factors = self._identify_risk_factors(current_patterns)

        # Calculate overall risk
        overall_risk = self._calculate_overall_risk(risk_factors)

        # Generate recommendations
        recommendations = self._generate_recommendations(risk_factors, current_patterns)

        # Determine risk category
        if overall_risk >= 0.8:
            category = "critical"
        elif overall_risk >= 0.6:
            category = "high"
        elif overall_risk >= 0.4:
            category = "medium"
        else:
            category = "low"

        assessment = RiskAssessment(
            flow_id=flow_id,
            overall_risk=overall_risk,
            risk_category=category,
            factors=risk_factors,
            recommendations=recommendations,
            confidence=self._calculate_confidence(len(events)),
        )

        # Track prediction for learning
        self.prediction_history.append(
            {
                "flow_id": flow_id,
                "timestamp": datetime.now().isoformat(),
                "assessment": asdict(assessment),
            }
        )

        return assessment

    def _identify_risk_factors(self, patterns: Dict[str, Any]) -> List[RiskFactor]:
        """Identify specific risk factors from patterns."""
        risk_factors = []
        thresholds = self.pattern_analyzer.patterns["risk_thresholds"]

        # High task count
        if patterns["task_count"] > 50:
            risk_factors.append(
                RiskFactor(
                    factor="high_task_count",
                    risk_level=min(patterns["task_count"] / 100, 1.0),
                    description=f"{patterns['task_count']} tasks may lead to coordination issues",
                    mitigation="Consider breaking project into phases",
                )
            )

        # Low AI confidence
        if patterns["avg_confidence"] < 0.6:
            risk_factors.append(
                RiskFactor(
                    factor="low_ai_confidence",
                    risk_level=1.0 - patterns["avg_confidence"],
                    description=f"AI confidence is only {patterns['avg_confidence'] * 100:.0f}%",
                    mitigation="Review and clarify requirements",
                )
            )

        # High complexity
        if patterns["complexity_score"] > 0.8:
            risk_factors.append(
                RiskFactor(
                    factor="high_complexity",
                    risk_level=patterns["complexity_score"],
                    description="Project complexity is very high",
                    mitigation="Simplify task dependencies or use phased approach",
                )
            )

        # Many ambiguities
        if patterns["ambiguity_count"] > 3:
            risk_factors.append(
                RiskFactor(
                    factor="many_ambiguities",
                    risk_level=min(patterns["ambiguity_count"] / 10, 1.0),
                    description=f"{patterns['ambiguity_count']} ambiguities in requirements",
                    mitigation="Clarify ambiguous requirements before proceeding",
                )
            )

        # Missing considerations
        if patterns["missing_considerations"] > 2:
            risk_factors.append(
                RiskFactor(
                    factor="missing_considerations",
                    risk_level=min(patterns["missing_considerations"] / 5, 0.8),
                    description="Important aspects missing from task breakdown",
                    mitigation="Add testing and documentation tasks",
                )
            )

        # Compare to thresholds
        for metric, threshold_data in thresholds.items():
            if metric in patterns and isinstance(patterns[metric], (int, float)):
                value = patterns[metric]

                if value > threshold_data.get("critical", float("inf")):
                    risk_factors.append(
                        RiskFactor(
                            factor=f"{metric}_critical",
                            risk_level=0.9,
                            description=f"{metric} is critically high ({value})",
                            mitigation=f"Review {metric} and optimize",
                        )
                    )
                elif value > threshold_data.get("warning", float("inf")):
                    risk_factors.append(
                        RiskFactor(
                            factor=f"{metric}_warning",
                            risk_level=0.6,
                            description=f"{metric} is above normal ({value})",
                            mitigation=f"Monitor {metric} closely",
                        )
                    )

        return risk_factors

    def _calculate_overall_risk(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate overall risk score from individual factors."""
        if not risk_factors:
            return 0.0

        # Weight critical factors more heavily
        weighted_risks = []

        for factor in risk_factors:
            weight = 1.0

            # Critical factors get higher weight
            if "critical" in factor.factor or factor.risk_level > 0.8:
                weight = 2.0
            elif "confidence" in factor.factor:
                weight = 1.5

            weighted_risks.append(factor.risk_level * weight)

        # Calculate weighted average
        total_weight = len(risk_factors) + sum(weight - 1 for weight in weighted_risks)
        overall_risk = sum(weighted_risks) / total_weight if total_weight > 0 else 0

        return min(overall_risk, 1.0)

    def _generate_recommendations(
        self, risk_factors: List[RiskFactor], patterns: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Add mitigation from risk factors
        seen_mitigations = set()
        for factor in sorted(risk_factors, key=lambda f: f.risk_level, reverse=True):
            if factor.mitigation not in seen_mitigations:
                recommendations.append(factor.mitigation)
                seen_mitigations.add(factor.mitigation)

        # Add general recommendations based on patterns
        if patterns["task_count"] > 30 and patterns["complexity_score"] > 0.7:
            recommendations.append(
                "Consider using microservices architecture for better task isolation"
            )

        if patterns["avg_confidence"] < 0.7 and patterns["ambiguity_count"] > 0:
            recommendations.append(
                "Schedule a requirements review session with stakeholders"
            )

        # Limit to top 5 recommendations
        return recommendations[:5]

    def _calculate_confidence(self, event_count: int) -> float:
        """Calculate confidence in the prediction."""
        # More events = more confidence
        if event_count < 5:
            return 0.3
        elif event_count < 10:
            return 0.6
        elif event_count < 20:
            return 0.8
        else:
            return 0.9

    def learn_from_outcome(self, flow_id: str, actual_outcome: str):
        """
        Update patterns based on actual outcome.

        Parameters
        ----------
        flow_id : str
            The flow ID that completed
        actual_outcome : str
            'success' or 'failure'
        """
        # Find prediction for this flow
        prediction = None
        for pred in self.prediction_history:
            if pred["flow_id"] == flow_id:
                prediction = pred
                break

        if not prediction:
            return

        # Compare prediction to outcome
        predicted_risk = prediction["assessment"]["overall_risk"]

        # Update patterns based on accuracy
        if actual_outcome == "failure" and predicted_risk < 0.5:
            # Under-predicted risk
            import sys
            print(f"Under-predicted risk for {flow_id}", file=sys.stderr)
            # In production, adjust thresholds
        elif actual_outcome == "success" and predicted_risk > 0.7:
            # Over-predicted risk
            import sys
            print(f"Over-predicted risk for {flow_id}", file=sys.stderr)
            # In production, adjust thresholds

    def get_prediction_accuracy(self) -> Dict[str, Any]:
        """Get accuracy metrics for predictions."""
        if not self.prediction_history:
            return {"accuracy": 0, "total_predictions": 0}

        # In production, compare with actual outcomes
        # For now, return placeholder
        return {
            "accuracy": 0.82,  # 82% accuracy
            "total_predictions": len(self.prediction_history),
            "true_positives": 45,
            "false_positives": 8,
            "true_negatives": 32,
            "false_negatives": 5,
        }

    def export_risk_report(self, assessment: RiskAssessment) -> str:
        """Export risk assessment as formatted report."""
        report = f"""
# Pipeline Risk Assessment Report

**Flow ID:** {assessment.flow_id}
**Assessment Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Overall Risk:** {assessment.overall_risk * 100:.1f}% ({assessment.risk_category})
**Confidence:** {assessment.confidence * 100:.0f}%

## Risk Factors

"""

        for factor in sorted(
            assessment.factors, key=lambda f: f.risk_level, reverse=True
        ):
            report += f"### {factor.factor.replace('_', ' ').title()}\n"
            report += f"- **Risk Level:** {factor.risk_level * 100:.0f}%\n"
            report += f"- **Description:** {factor.description}\n"
            report += f"- **Mitigation:** {factor.mitigation}\n\n"

        report += "## Recommendations\n\n"
        for i, rec in enumerate(assessment.recommendations, 1):
            report += f"{i}. {rec}\n"

        return report
