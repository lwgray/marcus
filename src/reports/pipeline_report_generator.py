"""
Pipeline Report Generator - Generate comprehensive reports for analysis

This module generates detailed reports from pipeline executions for
offline analysis, team reviews, and documentation.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from src.analysis.pipeline_comparison import PipelineComparator
from src.visualization.shared_pipeline_events import SharedPipelineEvents


class PipelineReportGenerator:
    """
    Generate comprehensive reports from pipeline executions.
    """

    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize report generator.

        Parameters
        ----------
        template_dir : Optional[str]
            Directory containing report templates
        """
        self.shared_events = SharedPipelineEvents()
        self.comparator = PipelineComparator()

        # Setup Jinja2 environment
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            self.template_dir = Path(__file__).parent / "templates"

        # Create templates directory if it doesn't exist
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Initialize template environment with autoescape for security
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)), autoescape=True
        )

        # Create default templates if they don't exist
        self._create_default_templates()

    def _create_default_templates(self):
        """Create default report templates."""
        # HTML report template
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ flow.project_name }} - Pipeline Analysis Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .report-header {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        h1 {
            color: #2c3e50;
            margin: 0;
        }
        .meta-info {
            color: #7f8c8d;
            margin-top: 10px;
        }
        .section {
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            text-align: center;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }
        .metric-label {
            color: #7f8c8d;
            margin-top: 5px;
        }
        .decision-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
        }
        .confidence-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            margin-left: 10px;
        }
        .confidence-high { background: #d4edda; color: #155724; }
        .confidence-medium { background: #fff3cd; color: #856404; }
        .confidence-low { background: #f8d7da; color: #721c24; }
        .timeline {
            position: relative;
            padding: 20px 0;
        }
        .timeline-item {
            position: relative;
            padding-left: 40px;
            margin-bottom: 20px;
        }
        .timeline-item::before {
            content: '';
            position: absolute;
            left: 10px;
            top: 5px;
            width: 10px;
            height: 10px;
            background: #007bff;
            border-radius: 50%;
        }
        .timeline-item::after {
            content: '';
            position: absolute;
            left: 14px;
            top: 15px;
            width: 2px;
            height: calc(100% + 10px);
            background: #e9ecef;
        }
        .timeline-item:last-child::after {
            display: none;
        }
        .recommendation {
            background: #e7f3ff;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
        }
        .chart-container {
            margin: 20px 0;
            height: 300px;
        }
        @media print {
            body { background: white; }
            .section { box-shadow: none; border: 1px solid #ddd; }
        }
    </style>
</head>
<body>
    <div class="report-header">
        <h1>{{ flow.project_name }} - Pipeline Analysis Report</h1>
        <div class="meta-info">
            Generated: {{ generation_date }}<br>
            Flow ID: {{ flow.flow_id }}<br>
            Duration: {{ (flow.metrics.total_duration_ms / 1000) | round(1) }}s
        </div>
    </div>

    <!-- Executive Summary -->
    <div class="section">
        <h2>Executive Summary</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{{ flow.metrics.task_count }}</div>
                <div class="metric-label">Total Tasks</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${{ flow.metrics.total_cost | round(2) }}</div>
                <div class="metric-label">Total Cost</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ (flow.metrics.quality_score * 100) | round(0) }}%</div>
                <div class="metric-label">Quality Score</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ (flow.metrics.confidence_avg * 100) | round(0) }}%</div>
                <div class="metric-label">Avg Confidence</div>
            </div>
        </div>
    </div>

    <!-- Key Decisions -->
    <div class="section">
        <h2>Key Decisions</h2>
        {% for decision in insights.key_decisions %}
        <div class="decision-item">
            <strong>{{ decision.decision }}</strong>
            {% set conf_class = 'high' if decision.confidence > 0.8 else ('medium' if decision.confidence > 0.6 else 'low') %}
            <span class="confidence-badge confidence-{{ conf_class }}">
                {{ (decision.confidence * 100) | round(0) }}% confidence
            </span>
            <p>{{ decision.rationale }}</p>
            {% if decision.alternatives %}
            <details>
                <summary>Alternatives Considered</summary>
                <ul>
                {% for alt in decision.alternatives %}
                    <li>{{ alt.option }} (Score: {{ alt.score }})</li>
                {% endfor %}
                </ul>
            </details>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <!-- Timeline -->
    <div class="section">
        <h2>Pipeline Timeline</h2>
        <div class="timeline">
            {% for event in insights.timeline %}
            <div class="timeline-item">
                <strong>{{ event.stage }}</strong>: {{ event.summary }}<br>
                <small>{{ event.relative_time }}ms</small>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Requirements Coverage -->
    <div class="section">
        <h2>Requirements Analysis</h2>
        <table>
            <thead>
                <tr>
                    <th>Requirement</th>
                    <th>Confidence</th>
                    <th>Coverage</th>
                </tr>
            </thead>
            <tbody>
                {% for req in insights.requirements %}
                <tr>
                    <td>{{ req.requirement }}</td>
                    <td>{{ (req.confidence * 100) | round(0) }}%</td>
                    <td>{{ req.task_count }} tasks</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- Recommendations -->
    <div class="section">
        <h2>Recommendations</h2>
        {% for rec in recommendations %}
        <div class="recommendation">
            {{ rec }}
        </div>
        {% endfor %}
    </div>

    <!-- Performance Details -->
    <div class="section">
        <h2>Performance Analysis</h2>
        <table>
            <thead>
                <tr>
                    <th>Stage</th>
                    <th>Duration (ms)</th>
                    <th>Cost</th>
                    <th>Tokens</th>
                </tr>
            </thead>
            <tbody>
                {% for stage in insights.stage_performance %}
                <tr>
                    <td>{{ stage.name }}</td>
                    <td>{{ stage.duration_ms }}</td>
                    <td>${{ stage.cost | round(3) }}</td>
                    <td>{{ stage.tokens }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <script>
        // Add any interactive features here
        document.querySelectorAll('details').forEach(detail => {
            detail.addEventListener('toggle', function() {
                // Could add analytics tracking here
            });
        });
    </script>
</body>
</html>
"""

        # Executive summary template
        exec_summary_template = """
# Executive Summary: {{ project_name }}

**Generated:** {{ generation_date }}
**Flow ID:** {{ flow_id }}

## Key Metrics
- **Total Tasks:** {{ total_tasks }}
- **Estimated Hours:** {{ estimated_hours }}
- **Total Cost:** ${{ total_cost }}
- **Quality Score:** {{ quality_score }}%

## Key Decisions
{% for decision in key_decisions %}
1. {{ decision.decision }} ({{ decision.confidence }}% confidence)
   - Rationale: {{ decision.rationale }}
{% endfor %}

## Identified Risks
{% for risk in risks_identified %}
- {{ risk.description }} ({{ risk.severity }})
  - Mitigation: {{ risk.mitigation }}
{% endfor %}

## Recommendations
{% for rec in recommendations %}
- {{ rec }}
{% endfor %}
"""

        # Save templates
        (self.template_dir / "full_report.html").write_text(html_template)
        (self.template_dir / "executive_summary.md").write_text(exec_summary_template)

    def generate_html_report(self, flow_id: str) -> str:
        """
        Generate HTML report for a flow.

        Parameters
        ----------
        flow_id : str
            The flow ID to generate report for

        Returns
        -------
        str
            HTML report content
        """
        flow = self._load_complete_flow(flow_id)
        insights = self._gather_insights(flow)
        recommendations = self._generate_recommendations(flow)

        template = self.env.get_template("full_report.html")
        return template.render(
            flow=flow,
            insights=insights,
            recommendations=recommendations,
            generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def generate_pdf_report(
        self, flow_id: str, output_path: Optional[str] = None
    ) -> bytes:
        """
        Generate PDF report for a flow.

        Parameters
        ----------
        flow_id : str
            The flow ID to generate report for
        output_path : Optional[str]
            Path to save PDF file

        Returns
        -------
        bytes
            PDF content
        """
        html = self.generate_html_report(flow_id)

        # Note: PDF generation requires additional dependencies
        # In production, use libraries like weasyprint or pdfkit
        # For now, return a placeholder

        if output_path:
            # Save HTML as alternative
            Path(output_path).with_suffix(".html").write_text(html)

        return b"PDF generation requires additional dependencies"

    def generate_executive_summary(self, flow_id: str) -> Dict[str, Any]:
        """
        Generate executive summary for stakeholders.

        Parameters
        ----------
        flow_id : str
            The flow ID to summarize

        Returns
        -------
        Dict[str, Any]
            Executive summary data
        """
        flow = self._load_complete_flow(flow_id)

        # Extract key information
        key_decisions = self._extract_key_decisions(flow)
        risks = self._summarize_risks(flow)
        recommendations = self._top_recommendations(flow)

        summary = {
            "project_name": flow["project_name"],
            "flow_id": flow_id,
            "generation_date": datetime.now().isoformat(),
            "total_tasks": flow["metrics"]["task_count"],
            "estimated_hours": sum(
                event.get("data", {}).get("effort_estimates", {}).values()
                for event in flow["events"]
                if event.get("event_type") == "tasks_generated"
            ),
            "total_cost": flow["metrics"]["total_cost"],
            "quality_score": int(flow["metrics"]["quality_score"] * 100),
            "key_decisions": key_decisions,
            "risks_identified": risks,
            "recommendations": recommendations,
        }

        return summary

    def generate_markdown_summary(self, flow_id: str) -> str:
        """Generate markdown executive summary."""
        summary_data = self.generate_executive_summary(flow_id)
        template = self.env.get_template("executive_summary.md")
        return template.render(**summary_data)

    def _load_complete_flow(self, flow_id: str) -> Dict[str, Any]:
        """Load complete flow data with all metadata."""
        events = self.shared_events.get_flow_events(flow_id)
        flow_data = self.shared_events._read_events()
        flow_info = flow_data["flows"].get(flow_id, {})

        # Use comparator's extraction methods
        flow = {
            "flow_id": flow_id,
            "project_name": flow_info.get("project_name", "Unknown"),
            "events": events,
            "metrics": self.comparator._extract_flow_metrics(events),
            "decisions": self.comparator._extract_decisions(events),
            "requirements": self.comparator._extract_requirements(events),
            "tasks": self.comparator._extract_tasks(events),
        }

        return flow

    def _gather_insights(self, flow: Dict[str, Any]) -> Dict[str, Any]:
        """Gather insights from flow data."""
        insights = {
            "timeline": self._create_timeline(flow["events"]),
            "key_decisions": self._extract_key_decisions(flow),
            "requirements": self._analyze_requirements(flow),
            "stage_performance": self._analyze_stage_performance(flow["events"]),
        }

        return insights

    def _create_timeline(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create timeline from events."""
        timeline = []

        if not events:
            return timeline

        start_time = datetime.fromisoformat(events[0].get("timestamp", ""))

        for event in events:
            event_time = datetime.fromisoformat(event.get("timestamp", ""))
            relative_ms = int((event_time - start_time).total_seconds() * 1000)

            timeline.append(
                {
                    "stage": event.get("stage", "Unknown"),
                    "event_type": event.get("event_type", ""),
                    "summary": self._get_event_summary(event),
                    "relative_time": relative_ms,
                }
            )

        return timeline

    def _get_event_summary(self, event: Dict[str, Any]) -> str:
        """Generate concise event summary."""
        event_type = event.get("event_type", "")
        data = event.get("data", {})

        summaries = {
            "ai_prd_analysis": f"AI Analysis ({data.get('confidence', 0) * 100:.0f}% confidence)",
            "tasks_generated": f"Generated {data.get('task_count', 0)} tasks",
            "decision_point": f"Decision: {data.get('decision', 'Unknown')[:50]}",
            "quality_metrics": f"Quality Score: {data.get('overall_quality_score', 0) * 100:.0f}%",
        }

        return summaries.get(event_type, event_type.replace("_", " ").title())

    def _extract_key_decisions(self, flow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract the most important decisions."""
        # Get all decisions sorted by confidence
        decisions = sorted(
            flow["decisions"], key=lambda d: d.get("confidence", 0), reverse=True
        )

        # Return top 5 decisions
        return decisions[:5]

    def _summarize_risks(self, flow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Summarize identified risks."""
        risks = []

        for event in flow["events"]:
            if event.get("event_type") == "tasks_generated":
                risk_factors = event.get("data", {}).get("risk_factors", [])
                for risk in risk_factors:
                    risks.append(
                        {
                            "description": risk.get(
                                "description", risk.get("risk", "")
                            ),
                            "severity": (
                                "High" if "high" in str(risk).lower() else "Medium"
                            ),
                            "mitigation": risk.get("mitigation", "Review and monitor"),
                        }
                    )

        return risks[:5]  # Top 5 risks

    def _generate_recommendations(self, flow: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on flow analysis."""
        recommendations = []

        metrics = flow["metrics"]

        # Quality recommendations
        if metrics["quality_score"] < 0.7:
            recommendations.append(
                "Quality score is below 70%. Consider reviewing task coverage "
                "and adding missing test/documentation tasks."
            )

        # Complexity recommendations
        if metrics["complexity_score"] > 0.8:
            recommendations.append(
                "High complexity detected. Consider breaking the project into "
                "phases or simplifying task dependencies."
            )

        # Cost recommendations
        if metrics["total_cost"] > 1.0:
            recommendations.append(
                f"Cost is ${metrics['total_cost']:.2f}. Consider using GPT-3.5 "
                "for non-critical analysis to reduce costs."
            )

        # Confidence recommendations
        if metrics["confidence_avg"] < 0.7:
            recommendations.append(
                "Average confidence is low. Review and clarify project requirements "
                "for better AI understanding."
            )

        # Check for missing testing
        has_testing = any("test" in task["name"].lower() for task in flow["tasks"])
        if not has_testing:
            recommendations.append(
                "No testing tasks detected. Add explicit testing tasks "
                "to ensure quality."
            )

        return recommendations

    def _top_recommendations(self, flow: Dict[str, Any]) -> List[str]:
        """Get top 3 recommendations for executive summary."""
        all_recommendations = self._generate_recommendations(flow)
        return all_recommendations[:3]

    def _analyze_requirements(self, flow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze requirement coverage."""
        requirements = flow["requirements"]

        # Count tasks per requirement
        req_coverage = {}
        for event in flow["events"]:
            if event.get("event_type") == "tasks_generated":
                # This is simplified - in production, track actual mapping
                for req in requirements:
                    req_coverage[req.get("requirement", "")] = flow["metrics"][
                        "task_count"
                    ] // len(requirements)

        # Enhance requirements with coverage
        for req in requirements:
            req["task_count"] = req_coverage.get(req.get("requirement", ""), 0)

        return requirements

    def _analyze_stage_performance(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze performance by pipeline stage."""
        stage_metrics = {}

        for event in events:
            stage = event.get("stage", "unknown")
            if stage not in stage_metrics:
                stage_metrics[stage] = {
                    "name": stage,
                    "duration_ms": 0,
                    "cost": 0,
                    "tokens": 0,
                }

            # Accumulate metrics
            if "duration_ms" in event:
                stage_metrics[stage]["duration_ms"] += event["duration_ms"]

            if event.get("event_type") == "performance_metrics":
                data = event.get("data", {})
                stage_metrics[stage]["cost"] += data.get("cost_estimate", 0)
                stage_metrics[stage]["tokens"] += data.get("token_usage", 0)

        return list(stage_metrics.values())

    def batch_generate_reports(self, flow_ids: List[str], output_dir: str):
        """
        Generate reports for multiple flows.

        Parameters
        ----------
        flow_ids : List[str]
            List of flow IDs to generate reports for
        output_dir : str
            Directory to save reports
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for flow_id in flow_ids:
            try:
                # Generate HTML report
                html = self.generate_html_report(flow_id)
                html_path = output_path / f"report_{flow_id}.html"
                html_path.write_text(html)

                # Generate markdown summary
                md = self.generate_markdown_summary(flow_id)
                md_path = output_path / f"summary_{flow_id}.md"
                md_path.write_text(md)

                print(f"Generated reports for {flow_id}", file=sys.stderr)

            except Exception as e:
                print(f"Error generating report for {flow_id}: {e}", file=sys.stderr)
