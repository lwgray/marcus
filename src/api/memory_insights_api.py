"""
Memory Insights API

Provides endpoints for visualizing the Memory system's learning and predictions,
including agent profiles, task patterns, and prediction accuracy.
"""

import asyncio
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from src.api.async_wrapper import async_route
from src.api.marcus_server_singleton import get_marcus_server

# Create blueprint
memory_api = Blueprint("memory_api", __name__, url_prefix="/api/memory")


@memory_api.route("/health", methods=["GET"])
def health():
    """Health check for memory API."""
    return jsonify({"status": "healthy", "service": "memory-insights-api"})


@memory_api.route("/stats", methods=["GET"])
@async_route
async def get_memory_stats():
    """
    Get overall memory system statistics.

    Returns counts and summaries of all memory tiers.
    """
    try:
        server = await get_marcus_server()

        if not server.memory:
            return (
                jsonify(
                    {
                        "error": "Memory system not enabled",
                        "hint": "Enable 'memory' in features configuration",
                    }
                ),
                503,
            )

        stats = server.memory.get_memory_stats()

        # Add derived statistics
        stats["insights"] = {
            "total_learning_instances": stats["episodic_memory"]["total_outcomes"],
            "unique_agents": len(stats["semantic_memory"]["agent_profiles"]),
            "pattern_types": len(stats["semantic_memory"]["task_patterns"]),
            "active_tasks": stats["working_memory"]["active_tasks"],
        }

        return jsonify(stats)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@memory_api.route("/agents", methods=["GET"])
@async_route
async def get_agent_profiles():
    """
    Get all agent profiles with their learning history.

    Query params:
        - sort_by: Field to sort by (success_rate, total_tasks, accuracy)
        - limit: Number of agents to return
    """
    try:
        server = await get_marcus_server()

        if not server.memory:
            return jsonify({"error": "Memory system not enabled"}), 503

        # Get sorting preferences
        sort_by = request.args.get("sort_by", "total_tasks")
        limit = int(request.args.get("limit", "50"))

        # Get all agent profiles
        profiles = []
        for agent_id, profile in server.memory.semantic["agent_profiles"].items():
            profile_data = {
                "agent_id": agent_id,
                "total_tasks": profile.total_tasks,
                "successful_tasks": profile.successful_tasks,
                "failed_tasks": profile.failed_tasks,
                "blocked_tasks": profile.blocked_tasks,
                "success_rate": profile.success_rate,
                "blockage_rate": profile.blockage_rate,
                "average_estimation_accuracy": profile.average_estimation_accuracy,
                "skill_success_rates": profile.skill_success_rates,
                "common_blockers": _format_blockers(profile.common_blockers),
                "performance_trend": _calculate_performance_trend(
                    agent_id, server.memory
                ),
            }
            profiles.append(profile_data)

        # Sort profiles
        if sort_by == "success_rate":
            profiles.sort(key=lambda x: x["success_rate"], reverse=True)
        elif sort_by == "accuracy":
            profiles.sort(key=lambda x: x["average_estimation_accuracy"], reverse=True)
        else:
            profiles.sort(key=lambda x: x["total_tasks"], reverse=True)

        return jsonify({"profiles": profiles[:limit], "total": len(profiles)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@memory_api.route("/agents/<agent_id>/history", methods=["GET"])
@async_route
async def get_agent_history(agent_id: str):
    """Get detailed task history for a specific agent."""
    try:
        server = await get_marcus_server()

        if not server.memory:
            return jsonify({"error": "Memory system not enabled"}), 503

        # Get agent's task outcomes
        outcomes = [
            outcome
            for outcome in server.memory.episodic["outcomes"]
            if outcome.agent_id == agent_id
        ]

        # Format outcomes
        history = []
        for outcome in outcomes:
            history.append(
                {
                    "task_id": outcome.task_id,
                    "task_name": outcome.task_name,
                    "estimated_hours": outcome.estimated_hours,
                    "actual_hours": outcome.actual_hours,
                    "estimation_accuracy": outcome.estimation_accuracy,
                    "success": outcome.success,
                    "blockers": outcome.blockers,
                    "started_at": outcome.started_at.isoformat()
                    if outcome.started_at
                    else None,
                    "completed_at": outcome.completed_at.isoformat()
                    if outcome.completed_at
                    else None,
                }
            )

        # Calculate statistics
        if history:
            accuracies = [
                h["estimation_accuracy"]
                for h in history
                if h["estimation_accuracy"] > 0
            ]
            success_count = len([h for h in history if h["success"]])

            stats = {
                "total_tasks": len(history),
                "success_rate": success_count / len(history),
                "average_accuracy": statistics.mean(accuracies) if accuracies else 0,
                "accuracy_std_dev": statistics.stdev(accuracies)
                if len(accuracies) > 1
                else 0,
                "total_hours": sum(h["actual_hours"] for h in history),
                "recent_trend": _calculate_recent_trend(history),
            }
        else:
            stats = {
                "total_tasks": 0,
                "success_rate": 0,
                "average_accuracy": 0,
                "accuracy_std_dev": 0,
                "total_hours": 0,
                "recent_trend": "no_data",
            }

        return jsonify({"agent_id": agent_id, "history": history, "statistics": stats})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@memory_api.route("/patterns", methods=["GET"])
@async_route
async def get_task_patterns():
    """Get learned task patterns."""
    try:
        server = await get_marcus_server()

        if not server.memory:
            return jsonify({"error": "Memory system not enabled"}), 503

        patterns = []
        for pattern_key, pattern in server.memory.semantic["task_patterns"].items():
            patterns.append(
                {
                    "pattern_id": pattern_key,
                    "pattern_type": pattern.pattern_type,
                    "task_labels": pattern.task_labels,
                    "average_duration": pattern.average_duration,
                    "success_rate": pattern.success_rate,
                    "common_blockers": pattern.common_blockers,
                    "prerequisites": pattern.prerequisites,
                    "best_agents": pattern.best_agents[:5],  # Top 5
                }
            )

        return jsonify({"patterns": patterns, "total": len(patterns)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@memory_api.route("/predictions/<agent_id>/<task_id>", methods=["GET"])
@async_route
async def get_task_prediction(agent_id: str, task_id: str):
    """Get prediction for a specific agent-task combination."""
    try:
        server = await get_marcus_server()

        if not server.memory:
            return jsonify({"error": "Memory system not enabled"}), 503

        # Find the task
        task = None
        for t in server.project_tasks:
            if t.id == task_id:
                task = t
                break

        if not task:
            return jsonify({"error": f"Task {task_id} not found"}), 404

        # Get predictions (try enhanced version if available)
        if hasattr(server.memory, "predict_task_outcome_v2"):
            from src.core.memory_advanced import MemoryAdvanced

            enhanced_memory = MemoryAdvanced(
                events=server.memory.events, persistence=server.memory.persistence
            )
            # Copy state from regular memory
            enhanced_memory.episodic = server.memory.episodic
            enhanced_memory.semantic = server.memory.semantic

            predictions = await enhanced_memory.predict_task_outcome_v2(agent_id, task)
        else:
            predictions = await server.memory.predict_task_outcome(agent_id, task)

        # Find similar past tasks
        similar_outcomes = await server.memory.find_similar_outcomes(task, limit=5)

        return jsonify(
            {
                "agent_id": agent_id,
                "task": {
                    "id": task.id,
                    "name": task.name,
                    "estimated_hours": task.estimated_hours,
                    "labels": task.labels,
                },
                "predictions": predictions,
                "similar_tasks": [
                    {
                        "task_name": outcome.task_name,
                        "agent_id": outcome.agent_id,
                        "success": outcome.success,
                        "actual_hours": outcome.actual_hours,
                        "estimation_accuracy": outcome.estimation_accuracy,
                    }
                    for outcome in similar_outcomes
                ],
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@memory_api.route("/learning-curve", methods=["GET"])
@async_route
async def get_learning_curve():
    """
    Get system-wide learning curve data.

    Shows how prediction accuracy improves over time.
    """
    try:
        server = await get_marcus_server()

        if not server.memory:
            return jsonify({"error": "Memory system not enabled"}), 503

        # Group outcomes by week
        weekly_data = {}

        for outcome in server.memory.episodic["outcomes"]:
            if outcome.completed_at:
                week = outcome.completed_at.isocalendar()[:2]  # (year, week)
                week_key = f"{week[0]}-W{week[1]:02d}"

                if week_key not in weekly_data:
                    weekly_data[week_key] = {
                        "accuracies": [],
                        "success_count": 0,
                        "total_count": 0,
                    }

                weekly_data[week_key]["accuracies"].append(outcome.estimation_accuracy)
                weekly_data[week_key]["total_count"] += 1
                if outcome.success:
                    weekly_data[week_key]["success_count"] += 1

        # Calculate weekly metrics
        learning_curve = []
        for week, data in sorted(weekly_data.items()):
            accuracies = [a for a in data["accuracies"] if a > 0]
            learning_curve.append(
                {
                    "week": week,
                    "average_accuracy": statistics.mean(accuracies)
                    if accuracies
                    else 0,
                    "success_rate": data["success_count"] / data["total_count"],
                    "task_count": data["total_count"],
                }
            )

        return jsonify(
            {"learning_curve": learning_curve, "total_weeks": len(learning_curve)}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@memory_api.route("/insights/blockers", methods=["GET"])
@async_route
async def get_blocker_insights():
    """Get insights about common blockers."""
    try:
        server = await get_marcus_server()

        if not server.memory:
            return jsonify({"error": "Memory system not enabled"}), 503

        # Aggregate all blockers
        blocker_counts = {}
        blocker_impacts = {}

        for outcome in server.memory.episodic["outcomes"]:
            for blocker in outcome.blockers:
                if blocker not in blocker_counts:
                    blocker_counts[blocker] = 0
                    blocker_impacts[blocker] = []

                blocker_counts[blocker] += 1
                # Impact is measured as hours lost
                blocker_impacts[blocker].append(
                    outcome.actual_hours - outcome.estimated_hours
                )

        # Format blocker insights
        insights = []
        for blocker, count in blocker_counts.items():
            avg_impact = (
                statistics.mean(blocker_impacts[blocker])
                if blocker_impacts[blocker]
                else 0
            )
            insights.append(
                {
                    "blocker": blocker,
                    "occurrences": count,
                    "average_delay_hours": avg_impact,
                    "total_impact_hours": sum(blocker_impacts[blocker]),
                    "affected_agents": _get_affected_agents(blocker, server.memory),
                }
            )

        # Sort by impact
        insights.sort(key=lambda x: x["total_impact_hours"], reverse=True)

        return jsonify(
            {
                "blocker_insights": insights[:20],  # Top 20
                "total_unique_blockers": len(blocker_counts),
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Helper functions


def _format_blockers(blockers: Dict[str, int]) -> List[Dict[str, Any]]:
    """Format blocker dictionary for API response."""
    formatted = []
    for blocker, count in sorted(blockers.items(), key=lambda x: x[1], reverse=True):
        formatted.append({"description": blocker, "occurrences": count})
    return formatted[:5]  # Top 5


def _calculate_performance_trend(agent_id: str, memory) -> str:
    """Calculate recent performance trend for an agent."""
    recent_outcomes = [
        o
        for o in memory.episodic["outcomes"]
        if o.agent_id == agent_id and o.completed_at
    ]

    if len(recent_outcomes) < 5:
        return "insufficient_data"

    # Sort by completion date
    recent_outcomes.sort(key=lambda x: x.completed_at)

    # Compare first half vs second half success rate
    mid = len(recent_outcomes) // 2
    first_half = recent_outcomes[:mid]
    second_half = recent_outcomes[mid:]

    first_success_rate = sum(1 for o in first_half if o.success) / len(first_half)
    second_success_rate = sum(1 for o in second_half if o.success) / len(second_half)

    if second_success_rate > first_success_rate + 0.1:
        return "improving"
    elif second_success_rate < first_success_rate - 0.1:
        return "declining"
    else:
        return "stable"


def _calculate_recent_trend(history: List[Dict[str, Any]]) -> str:
    """Calculate trend from task history."""
    if len(history) < 3:
        return "insufficient_data"

    # Get last 10 tasks
    recent = history[-10:]

    # Calculate success rate trend
    if len(recent) >= 5:
        first_half = recent[: len(recent) // 2]
        second_half = recent[len(recent) // 2 :]

        first_success = sum(1 for h in first_half if h["success"]) / len(first_half)
        second_success = sum(1 for h in second_half if h["success"]) / len(second_half)

        if second_success > first_success + 0.15:
            return "strongly_improving"
        elif second_success > first_success:
            return "improving"
        elif second_success < first_success - 0.15:
            return "declining"
        else:
            return "stable"

    return "stable"


def _get_affected_agents(blocker: str, memory) -> List[str]:
    """Get list of agents affected by a specific blocker."""
    affected = set()

    for outcome in memory.episodic["outcomes"]:
        if blocker in outcome.blockers:
            affected.add(outcome.agent_id)

    return list(affected)
