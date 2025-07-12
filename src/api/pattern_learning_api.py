"""
API endpoints for pattern learning features - for visualization UI only
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from flask import Blueprint, jsonify, request

from src.core.models import ProjectState, Task, WorkerStatus
from src.integrations.kanban_client import KanbanClient
from src.learning.project_pattern_learner import ProjectPatternLearner
from src.monitoring.project_monitor import ProjectMonitor
from src.quality.project_quality_assessor import ProjectQualityAssessor
from src.recommendations.recommendation_engine import ProjectOutcome

# Create Blueprint
pattern_api = Blueprint("pattern_api", __name__, url_prefix="/api/patterns")

# Initialize components (these would be properly injected in production)
pattern_learner = None
quality_assessor = None
project_monitor = None
kanban_client = None


def init_pattern_api(learner, assessor, monitor, kanban):
    """Initialize the API with required components"""
    global pattern_learner, quality_assessor, project_monitor, kanban_client
    pattern_learner = learner
    quality_assessor = assessor
    project_monitor = monitor
    kanban_client = kanban


@pattern_api.route("/similar-projects", methods=["POST"])
async def get_similar_projects():
    """Find similar projects based on current project context"""
    try:
        data = request.json
        project_context = data.get("project_context", {})
        min_similarity = data.get("min_similarity", 0.7)

        if not pattern_learner:
            return jsonify({"error": "Pattern learning not initialized"}), 500

        # Create a mock pattern from context for similarity matching
        from src.learning.project_pattern_learner import ProjectPattern

        current_pattern = ProjectPattern(
            project_id="current",
            project_name="Current Project",
            outcome=ProjectOutcome(
                successful=True, completion_time_days=0, quality_score=0, cost=0
            ),
            quality_metrics={},
            team_composition={"team_size": project_context.get("team_size", 0)},
            velocity_pattern={"current": project_context.get("velocity", 0)},
            task_patterns={"total_tasks": project_context.get("total_tasks", 0)},
            blocker_patterns={},
            technology_stack=project_context.get("technology_stack", []),
            implementation_patterns={},
            success_factors=[],
            risk_factors=[],
            extracted_at=datetime.now(),
            confidence_score=0.5,
        )

        similar = pattern_learner.find_similar_projects(current_pattern, min_similarity)

        results = []
        for pattern, similarity in similar[:5]:
            results.append(
                {
                    "project_name": pattern.project_name,
                    "similarity_score": similarity,
                    "outcome": {
                        "successful": pattern.outcome.successful,
                        "completion_time_days": pattern.outcome.completion_time_days,
                        "quality_score": pattern.outcome.quality_score,
                    },
                    "key_patterns": {
                        "team_size": pattern.team_composition.get("team_size", 0),
                        "avg_velocity": pattern.velocity_pattern.get("middle", 0),
                        "tech_stack": pattern.technology_stack,
                    },
                }
            )

        return jsonify({"similar_projects": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pattern_api.route("/assess-quality/<board_id>", methods=["GET"])
async def assess_project_quality(board_id: str):
    """Get comprehensive quality assessment for a project"""
    try:
        if not all([quality_assessor, kanban_client]):
            return jsonify({"error": "Quality assessment not initialized"}), 500

        # Get project data
        project_state = (
            await project_monitor.get_project_state() if project_monitor else None
        )
        tasks = await kanban_client.get_all_tasks() if kanban_client else []
        team_members = []  # Would need to get from the system

        # Check for GitHub config
        github_config = None
        if request.args.get("github_owner") and request.args.get("github_repo"):
            github_config = {
                "github_owner": request.args.get("github_owner"),
                "github_repo": request.args.get("github_repo"),
                "project_start_date": request.args.get(
                    "start_date", datetime.now().isoformat()
                ),
            }

        assessment = await quality_assessor.assess_project_quality(
            project_state=project_state,
            tasks=tasks,
            team_members=team_members,
            github_config=github_config,
        )

        return jsonify(
            {
                "assessment": {
                    "project_name": assessment.project_name,
                    "overall_score": assessment.overall_score,
                    "code_quality_score": assessment.code_quality_score,
                    "process_quality_score": assessment.process_quality_score,
                    "delivery_quality_score": assessment.delivery_quality_score,
                    "team_quality_score": assessment.team_quality_score,
                    "quality_insights": assessment.quality_insights,
                    "improvement_areas": assessment.improvement_areas,
                    "success_prediction": assessment.success_prediction,
                }
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pattern_api.route("/recommendations", methods=["POST"])
async def get_pattern_recommendations():
    """Get pattern-based recommendations for current project"""
    try:
        data = request.json
        project_context = data.get("project_context", {})

        if not pattern_learner:
            return jsonify({"error": "Pattern learning not initialized"}), 500

        recommendations = pattern_learner.get_recommendations_from_patterns(
            project_context
        )

        return jsonify({"recommendations": recommendations})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pattern_api.route("/quality-trends", methods=["GET"])
async def get_quality_trends():
    """Get quality trends across projects over time"""
    try:
        days = int(request.args.get("days", 30))
        metric_type = request.args.get("metric_type", "overall")

        if not pattern_learner:
            return jsonify({"error": "Pattern learning not initialized"}), 500

        # Calculate trends from learned patterns
        trends = {
            "period": f"Last {days} days",
            "metric": metric_type,
            "projects_analyzed": len(pattern_learner.learned_patterns),
        }

        # Filter patterns by date
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_patterns = [
            p for p in pattern_learner.learned_patterns if p.extracted_at >= cutoff_date
        ]

        if recent_patterns:
            # Calculate averages
            if metric_type == "overall":
                scores = [p.outcome.quality_score for p in recent_patterns]
            elif metric_type == "code":
                scores = [
                    p.quality_metrics.get("board_quality_score", 0)
                    for p in recent_patterns
                ]
            else:
                scores = [p.outcome.quality_score for p in recent_patterns]

            trends["average_score"] = sum(scores) / len(scores) if scores else 0
            trends["trend_direction"] = (
                "improving" if len(scores) > 1 and scores[-1] > scores[0] else "stable"
            )

        return jsonify({"trends": trends})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pattern_api.route("/patterns", methods=["GET"])
async def list_learned_patterns():
    """List all learned patterns with pagination"""
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))

        if not pattern_learner:
            return jsonify({"error": "Pattern learning not initialized"}), 500

        # Get patterns with pagination
        start = (page - 1) * per_page
        end = start + per_page

        patterns = pattern_learner.learned_patterns[start:end]

        results = []
        for pattern in patterns:
            results.append(
                {
                    "project_id": pattern.project_id,
                    "project_name": pattern.project_name,
                    "extracted_at": pattern.extracted_at.isoformat(),
                    "confidence_score": pattern.confidence_score,
                    "outcome": {
                        "successful": pattern.outcome.successful,
                        "quality_score": pattern.outcome.quality_score,
                        "completion_days": pattern.outcome.completion_time_days,
                    },
                    "team_size": pattern.team_composition.get("team_size", 0),
                    "success_factors": pattern.success_factors[:3],  # Top 3
                    "risk_factors": pattern.risk_factors[:3],  # Top 3
                }
            )

        return jsonify(
            {
                "patterns": results,
                "total": len(pattern_learner.learned_patterns),
                "page": page,
                "per_page": per_page,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pattern_api.route("/export", methods=["GET"])
async def export_patterns():
    """Export all patterns as JSON for analysis"""
    try:
        if not pattern_learner:
            return jsonify({"error": "Pattern learning not initialized"}), 500

        # Convert patterns to exportable format
        export_data = {
            "export_date": datetime.now().isoformat(),
            "total_patterns": len(pattern_learner.learned_patterns),
            "patterns": [],
        }

        for pattern in pattern_learner.learned_patterns:
            # Convert pattern to dict (simplified for export)
            pattern_dict = {
                "project_id": pattern.project_id,
                "project_name": pattern.project_name,
                "outcome": {
                    "successful": pattern.outcome.successful,
                    "quality_score": pattern.outcome.quality_score,
                    "completion_days": pattern.outcome.completion_time_days,
                    "cost": pattern.outcome.cost,
                },
                "metrics": pattern.quality_metrics,
                "team_composition": pattern.team_composition,
                "velocity_pattern": pattern.velocity_pattern,
                "success_factors": pattern.success_factors,
                "risk_factors": pattern.risk_factors,
                "confidence_score": pattern.confidence_score,
                "extracted_at": pattern.extracted_at.isoformat(),
            }
            export_data["patterns"].append(pattern_dict)

        return jsonify(export_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
