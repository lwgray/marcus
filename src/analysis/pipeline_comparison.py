"""
Pipeline Comparison Engine - Compare multiple pipeline executions.

This module enables comparison of multiple project creations to identify
patterns, best practices, and optimization opportunities.
"""

import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from src.visualization.shared_pipeline_events import SharedPipelineEvents


@dataclass
class ComparisonReport:
    """Comprehensive comparison report for multiple flows."""

    flow_summaries: List[Dict[str, Any]]
    common_patterns: Dict[str, Any]
    unique_decisions: List[Dict[str, Any]]
    performance_comparison: Dict[str, Any]
    quality_comparison: Dict[str, Any]
    task_breakdown_analysis: Dict[str, Any]
    recommendations: List[str]


class PipelineComparator:
    """Compare multiple pipeline flows to identify patterns and best practices."""

    def __init__(self) -> None:
        """Initialize the pipeline comparator."""
        self.shared_events = SharedPipelineEvents()

    def compare_multiple_flows(self, flow_ids: List[str]) -> ComparisonReport:
        """
        Compare multiple pipeline flows.

        Parameters
        ----------
        flow_ids : List[str]
            List of flow IDs to compare

        Returns
        -------
        ComparisonReport
            Comprehensive comparison report
        """
        # Load all flows
        flows = []
        for flow_id in flow_ids:
            flow_data = self._load_flow_with_metadata(flow_id)
            if flow_data:
                flows.append(flow_data)

        if len(flows) < 2:
            raise ValueError("Need at least 2 flows to compare")

        # Perform comparisons
        report = ComparisonReport(
            flow_summaries=self._create_flow_summaries(flows),
            common_patterns=self._find_common_patterns(flows),
            unique_decisions=self._find_unique_decisions(flows),
            performance_comparison=self._compare_performance(flows),
            quality_comparison=self._compare_quality(flows),
            task_breakdown_analysis=self._analyze_task_patterns(flows),
            recommendations=self._generate_recommendations(flows),
        )

        return report

    def _load_flow_with_metadata(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Load flow with all metadata and metrics."""
        events = self.shared_events.get_events()

        if not events:
            return None

        # Get flow info
        flow_data = self.shared_events._read_events()
        flow_info = flow_data["flows"].get(flow_id, {})

        # Extract comprehensive metadata
        metadata = {
            "flow_id": flow_id,
            "project_name": flow_info.get("project_name", "Unknown"),
            "started_at": flow_info.get("started_at"),
            "completed_at": flow_info.get("completed_at"),
            "events": events,
            "metrics": self._extract_flow_metrics(events),
            "decisions": self._extract_decisions(events),
            "requirements": self._extract_requirements(events),
            "tasks": self._extract_tasks(events),
        }

        return metadata

    def _extract_flow_metrics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract key metrics from flow events."""
        metrics = {
            "total_duration_ms": 0,
            "ai_analysis_duration": 0,
            "task_generation_duration": 0,
            "total_cost": 0,
            "token_usage": 0,
            "task_count": 0,
            "requirement_count": 0,
            "decision_count": 0,
            "quality_score": 0,
            "complexity_score": 0,
            "confidence_avg": 0,
        }

        confidence_scores = []

        for event in events:
            event_type = event.get("event_type", "")
            data = event.get("data", {})

            if event_type == "pipeline_completed":
                metrics["total_duration_ms"] = data.get("total_duration_ms", 0)
            elif event_type == "ai_prd_analysis":
                metrics["ai_analysis_duration"] = event.get("duration_ms", 0)
                metrics["requirement_count"] = len(
                    data.get("extracted_requirements", [])
                )
                if "confidence" in data:
                    confidence_scores.append(data["confidence"])
            elif event_type == "tasks_generated":
                metrics["task_generation_duration"] = event.get("duration_ms", 0)
                metrics["task_count"] = data.get("task_count", 0)
                metrics["complexity_score"] = data.get("complexity_score", 0)
            elif event_type == "performance_metrics":
                metrics["token_usage"] += data.get("token_usage", 0)
                metrics["total_cost"] += data.get("cost_estimate", 0)
            elif event_type == "quality_metrics":
                metrics["quality_score"] = data.get("overall_quality_score", 0)
            elif event_type == "decision_point":
                metrics["decision_count"] += 1
                if "confidence" in data:
                    confidence_scores.append(data["confidence"])

        if confidence_scores:
            metrics["confidence_avg"] = statistics.mean(confidence_scores)

        return metrics

    def _extract_decisions(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract all decisions from events."""
        decisions = []

        for event in events:
            if event.get("event_type") == "decision_point":
                data = event.get("data", {})
                decisions.append(
                    {
                        "stage": event.get("stage"),
                        "decision": data.get("decision"),
                        "confidence": data.get("confidence"),
                        "alternatives": data.get("alternatives_considered", []),
                    }
                )

        return decisions

    def _extract_requirements(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract requirements from AI analysis."""
        for event in events:
            if event.get("event_type") == "ai_prd_analysis":
                data = event.get("data", {})
                requirements = data.get("extracted_requirements", [])
                # Ensure we return the correct type
                if isinstance(requirements, list):
                    return requirements
        return []

    def _extract_tasks(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract generated tasks."""
        tasks = []

        for event in events:
            if event.get("event_type") == "task_created":
                data = event.get("data", {})
                tasks.append({"id": data.get("task_id"), "name": data.get("task_name")})

        return tasks

    def _create_flow_summaries(
        self, flows: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create summary for each flow."""
        summaries = []

        for flow in flows:
            metrics = flow["metrics"]
            summary = {
                "flow_id": flow["flow_id"],
                "project_name": flow["project_name"],
                "duration_seconds": metrics["total_duration_ms"] / 1000,
                "cost": metrics["total_cost"],
                "task_count": metrics["task_count"],
                "quality_score": metrics["quality_score"],
                "complexity": metrics["complexity_score"],
                "confidence": metrics["confidence_avg"],
            }
            summaries.append(summary)

        return summaries

    def _find_common_patterns(self, flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify patterns common across flows."""
        patterns: Dict[str, Any] = {
            "decision_patterns": defaultdict(list),
            "requirement_patterns": defaultdict(int),
            "task_name_patterns": Counter(),
            "complexity_correlation": [],
        }

        for flow in flows:
            # Decision patterns
            for decision in flow["decisions"]:
                decision_dict = decision if isinstance(decision, dict) else {}
                stage = decision_dict.get("stage", "")
                decision_text = str(decision_dict.get("decision", ""))[:30]
                key = f"{stage}:{decision_text}"
                confidence = decision_dict.get("confidence", 0)
                if isinstance(confidence, (int, float)):
                    patterns["decision_patterns"][key].append(confidence)

            # Requirement patterns
            for req in flow["requirements"]:
                req_dict = req if isinstance(req, dict) else {}
                req_type = req_dict.get("category", "unknown")
                patterns["requirement_patterns"][req_type] += 1

            # Task patterns
            for task in flow["tasks"]:
                task_dict = task if isinstance(task, dict) else {}
                task_name = task_dict.get("name", "")
                if isinstance(task_name, str):
                    # Extract common words from task names
                    words = task_name.lower().split()
                    for word in words:
                        if len(word) > 3:  # Skip short words
                            patterns["task_name_patterns"][word] += 1

            # Complexity correlation
            patterns["complexity_correlation"].append(
                {
                    "task_count": flow["metrics"]["task_count"],
                    "complexity": flow["metrics"]["complexity_score"],
                }
            )

        # Process patterns - cast to proper types for mypy
        decision_patterns = patterns["decision_patterns"]
        task_name_patterns = patterns["task_name_patterns"]
        requirement_patterns = patterns["requirement_patterns"]

        processed_patterns = {
            "common_decisions": [
                {
                    "decision": key,
                    "frequency": len(confidences),
                    "avg_confidence": statistics.mean(confidences),
                }
                for key, confidences in decision_patterns.items()
                if len(confidences) > len(flows) / 2  # Common if in >50% of flows
            ],
            "requirement_distribution": dict(requirement_patterns),
            "common_task_words": task_name_patterns.most_common(10),
            "complexity_trend": self._analyze_complexity_trend(
                patterns["complexity_correlation"]
            ),
        }

        return processed_patterns

    def _analyze_complexity_trend(
        self, correlations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze relationship between task count and complexity."""
        if not correlations:
            return {}

        task_counts = [c["task_count"] for c in correlations]
        complexities = [c["complexity"] for c in correlations]

        # Simple correlation analysis
        avg_ratio = statistics.mean(
            c["complexity"] / c["task_count"] if c["task_count"] > 0 else 0
            for c in correlations
        )

        return {
            "avg_tasks": statistics.mean(task_counts),
            "avg_complexity": statistics.mean(complexities),
            "complexity_per_task": avg_ratio,
        }

    def _find_unique_decisions(
        self, flows: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find decisions unique to specific flows."""
        # Count decision occurrences
        decision_counts = defaultdict(list)

        for flow in flows:
            for decision in flow["decisions"]:
                key = f"{decision['stage']}:{decision['decision']}"
                decision_counts[key].append(
                    {
                        "flow_id": flow["flow_id"],
                        "project_name": flow["project_name"],
                        "confidence": decision["confidence"],
                    }
                )

        # Find unique decisions (only in one flow)
        unique_decisions = []
        for decision_key, occurrences in decision_counts.items():
            if len(occurrences) == 1:
                stage, decision = decision_key.split(":", 1)
                unique_decisions.append(
                    {
                        "flow_id": occurrences[0]["flow_id"],
                        "project_name": occurrences[0]["project_name"],
                        "stage": stage,
                        "decision": decision,
                        "confidence": occurrences[0]["confidence"],
                    }
                )

        return unique_decisions

    def _compare_performance(self, flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare performance metrics across flows."""
        performance = {
            "duration": {
                "min": float("inf"),
                "max": 0,
                "avg": 0,
                "best_flow": None,
                "worst_flow": None,
            },
            "cost": {
                "min": float("inf"),
                "max": 0,
                "avg": 0,
                "best_flow": None,
                "worst_flow": None,
            },
            "token_efficiency": {
                "best_ratio": float("inf"),
                "worst_ratio": 0,
                "best_flow": None,
                "worst_flow": None,
            },
        }

        durations = []
        costs = []

        for flow in flows:
            metrics = flow["metrics"]
            duration = metrics["total_duration_ms"]
            cost = metrics["total_cost"]

            # Duration tracking
            durations.append(duration)
            if duration < performance["duration"]["min"]:
                performance["duration"]["min"] = duration
                performance["duration"]["best_flow"] = flow["project_name"]
            if duration > performance["duration"]["max"]:
                performance["duration"]["max"] = duration
                performance["duration"]["worst_flow"] = flow["project_name"]

            # Cost tracking
            costs.append(cost)
            if cost < performance["cost"]["min"]:
                performance["cost"]["min"] = cost
                performance["cost"]["best_flow"] = flow["project_name"]
            if cost > performance["cost"]["max"]:
                performance["cost"]["max"] = cost
                performance["cost"]["worst_flow"] = flow["project_name"]

            # Token efficiency (tokens per task)
            if metrics["task_count"] > 0:
                ratio = metrics["token_usage"] / metrics["task_count"]
                if ratio < performance["token_efficiency"]["best_ratio"]:
                    performance["token_efficiency"]["best_ratio"] = ratio
                    performance["token_efficiency"]["best_flow"] = flow["project_name"]
                if ratio > performance["token_efficiency"]["worst_ratio"]:
                    performance["token_efficiency"]["worst_ratio"] = ratio
                    performance["token_efficiency"]["worst_flow"] = flow["project_name"]

        performance["duration"]["avg"] = statistics.mean(durations)
        performance["cost"]["avg"] = statistics.mean(costs)

        return performance

    def _compare_quality(self, flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare quality metrics across flows."""
        quality_scores = []
        confidence_scores = []
        missing_considerations: Dict[str, int] = defaultdict(int)

        for flow in flows:
            quality_scores.append(flow["metrics"]["quality_score"])
            confidence_scores.append(flow["metrics"]["confidence_avg"])

            # Check for quality issues
            for event in flow["events"]:
                if event.get("event_type") == "quality_metrics":
                    for missing in event.get("data", {}).get(
                        "missing_considerations", []
                    ):
                        missing_considerations[missing] += 1

        return {
            "quality_scores": {
                "min": min(quality_scores),
                "max": max(quality_scores),
                "avg": statistics.mean(quality_scores),
                "std_dev": (
                    statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0
                ),
            },
            "confidence_scores": {
                "min": min(confidence_scores),
                "max": max(confidence_scores),
                "avg": statistics.mean(confidence_scores),
            },
            "common_missing_considerations": [
                {"consideration": k, "frequency": v}
                for k, v in sorted(
                    missing_considerations.items(), key=lambda x: x[1], reverse=True
                )[:5]
            ],
        }

    def _analyze_task_patterns(self, flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze task breakdown patterns."""
        task_counts = []
        task_categories: Dict[str, int] = defaultdict(int)

        for flow in flows:
            task_counts.append(flow["metrics"]["task_count"])

            # Categorize tasks
            for task in flow["tasks"]:
                name_lower = task["name"].lower()
                if any(word in name_lower for word in ["test", "testing", "qa"]):
                    task_categories["testing"] += 1
                elif any(
                    word in name_lower for word in ["doc", "documentation", "readme"]
                ):
                    task_categories["documentation"] += 1
                elif any(
                    word in name_lower for word in ["design", "architect", "plan"]
                ):
                    task_categories["design"] += 1
                elif any(
                    word in name_lower
                    for word in ["implement", "build", "create", "develop"]
                ):
                    task_categories["implementation"] += 1
                elif any(
                    word in name_lower for word in ["deploy", "ci", "cd", "devops"]
                ):
                    task_categories["deployment"] += 1
                else:
                    task_categories["other"] += 1

        return {
            "task_count_stats": {
                "min": min(task_counts),
                "max": max(task_counts),
                "avg": statistics.mean(task_counts),
                "median": statistics.median(task_counts),
            },
            "task_categories": dict(task_categories),
            "category_percentages": (
                {
                    cat: (count / sum(task_categories.values()) * 100)
                    for cat, count in task_categories.items()
                }
                if task_categories
                else {}
            ),
        }

    def _generate_recommendations(self, flows: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on comparison."""
        recommendations = []

        # Performance recommendations
        perf = self._compare_performance(flows)
        if perf["cost"]["max"] > perf["cost"]["avg"] * 1.5:
            recommendations.append(
                f"Consider optimizing costs - highest cost "
                f"(${perf['cost']['max']:.2f}) "
                f"is 50% above average (${perf['cost']['avg']:.2f})"
            )

        # Quality recommendations
        quality = self._compare_quality(flows)
        if quality["quality_scores"]["min"] < 0.6:
            recommendations.append(
                "Some flows have low quality scores (<60%). "
                "Review task generation and requirement coverage."
            )

        # Common missing considerations
        if quality["common_missing_considerations"]:
            most_common = quality["common_missing_considerations"][0]
            recommendations.append(
                f"'{most_common['consideration']}' is missing in "
                f"{most_common['frequency']} flows - "
                "consider making it standard"
            )

        # Task patterns
        task_analysis = self._analyze_task_patterns(flows)
        if task_analysis["category_percentages"].get("testing", 0) < 15:
            recommendations.append(
                "Testing tasks represent <15% of total tasks. "
                "Consider increasing test coverage."
            )

        return recommendations

    def export_comparison_report(
        self, report: ComparisonReport, format: str = "json"
    ) -> str:
        """
        Export comparison report in specified format.

        Parameters
        ----------
        report : ComparisonReport
            The comparison report to export
        format : str
            Export format (json, html, markdown)

        Returns
        -------
        str
            Formatted report
        """
        if format == "json":
            import json

            return json.dumps(asdict(report), indent=2, default=str)
        elif format == "markdown":
            return self._format_markdown_report(report)
        elif format == "html":
            return self._format_html_report(report)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_markdown_report(self, report: ComparisonReport) -> str:
        """Format report as markdown."""
        md = "# Pipeline Comparison Report\n\n"

        # Flow summaries
        md += "## Flow Summaries\n\n"
        md += "| Project | Duration (s) | Cost | Tasks | Quality | Complexity |\n"
        md += "|---------|-------------|------|-------|---------|------------|\n"

        for summary in report.flow_summaries:
            md += f"| {summary['project_name']} "
            md += f"| {summary['duration_seconds']:.1f} "
            md += f"| ${summary['cost']:.2f} "
            md += f"| {summary['task_count']} "
            md += f"| {summary['quality_score'] * 100:.0f}% "
            md += f"| {summary['complexity']:.2f} |\n"

        # Common patterns
        md += "\n## Common Patterns\n\n"
        for decision in report.common_patterns.get("common_decisions", []):
            md += f"- **{decision['decision']}**: "
            md += f"Found in {decision['frequency']} flows "
            md += f"(avg confidence: {decision['avg_confidence'] * 100:.0f}%)\n"

        # Recommendations
        md += "\n## Recommendations\n\n"
        for rec in report.recommendations:
            md += f"- {rec}\n"

        return md

    def _format_html_report(self, report: ComparisonReport) -> str:
        """Format report as HTML."""
        # Simple HTML template - in production, use proper templating
        html = """
        <html>
        <head>
            <title>Pipeline Comparison Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; }
                th, td {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }
                th { background-color: #f2f2f2; }
                .recommendation {
                    background-color: #fff3cd;
                    padding: 10px;
                    margin: 10px 0;
                }
            </style>
        </head>
        <body>
            <h1>Pipeline Comparison Report</h1>
        """

        # Add content similar to markdown
        # (abbreviated for space)

        html += "</body></html>"
        return html
