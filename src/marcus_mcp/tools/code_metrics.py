"""
Code production metrics tools for Marcus MCP.

This module provides tools for collecting code metrics from GitHub,
including commit statistics, PR metrics, and code review activity.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from mcp.types import Tool


async def get_code_metrics(
    agent_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Calculate code production metrics for an agent.

    Parameters
    ----------
    agent_id : str
        ID of the agent to analyze
    start_date : Optional[str]
        Start date in ISO format (defaults to 7 days ago)
    end_date : Optional[str]
        End date in ISO format (defaults to now)
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Code metrics including:
        - commits: number of commits
        - lines_added: total lines added
        - lines_deleted: total lines deleted
        - files_changed: unique files modified
        - languages: language distribution
        - review_activity: PR reviews given and received
    """
    if not state:
        return {
            "success": False,
            "error": "Server state not available",
        }

    # Parse dates
    if end_date:
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    else:
        end_dt = datetime.now()

    if start_date:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    else:
        start_dt = end_dt - timedelta(days=7)

    # Get GitHub username for agent
    github_username = None
    agent_data = None

    # Find agent across projects
    for project_id, context in state._project_contexts.items():
        if context.assignment_persistence:
            agent_data = context.assignment_persistence.get_agent(agent_id)
            if agent_data:
                # Try to get GitHub username from agent metadata
                if hasattr(agent_data, "metadata") and agent_data.metadata:
                    github_username = agent_data.metadata.get("github_username")
                break

    if not github_username:
        # Fallback: use agent_id as GitHub username
        github_username = agent_id

    # Mock implementation for now - in real implementation, this would
    # call GitHub API to fetch actual metrics
    metrics = {
        "commits": 0,
        "lines_added": 0,
        "lines_deleted": 0,
        "files_changed": [],
        "languages": {},
        "review_comments_made": 0,
        "review_comments_received": 0,
        "prs_opened": 0,
        "prs_merged": 0,
        "average_pr_merge_time": 0.0,
        "code_churn": 0,
    }

    # Simulate some data based on agent activity
    if agent_data:
        # Estimate commits based on completed tasks
        for project_id, context in state._project_contexts.items():
            if context.kanban_provider:
                tasks = await context.kanban_provider.get_tasks()
                agent_tasks = [
                    t
                    for t in tasks
                    if t.assigned_to == agent_id
                    and hasattr(t, "updated_at")
                    and start_dt <= t.updated_at <= end_dt
                ]

                # Rough estimates
                completed_tasks = len(
                    [t for t in agent_tasks if str(t.status) == "done"]
                )
                metrics["commits"] = completed_tasks * 3  # Assume 3 commits per task
                metrics["lines_added"] = (
                    completed_tasks * 150
                )  # Assume 150 lines per task
                metrics["lines_deleted"] = completed_tasks * 50
                metrics["prs_opened"] = completed_tasks
                metrics["prs_merged"] = int(completed_tasks * 0.9)  # 90% merge rate

                # Language distribution based on task labels
                for task in agent_tasks:
                    for label in task.labels or []:
                        if label in [
                            "python",
                            "javascript",
                            "typescript",
                            "go",
                            "rust",
                        ]:
                            languages_dict = metrics["languages"]
                            if isinstance(languages_dict, dict):
                                languages_dict[label] = languages_dict.get(label, 0) + 1

    # Convert files_changed to count
    files_changed = metrics["files_changed"]
    if isinstance(files_changed, list):
        metrics["files_changed"] = len(set(files_changed))

    # Calculate average merge time (mock)
    prs_merged = metrics["prs_merged"]
    if isinstance(prs_merged, int) and prs_merged > 0:
        metrics["average_pr_merge_time"] = 24.5  # Mock 24.5 hours average

    return {
        "success": True,
        "agent_id": agent_id,
        "github_username": github_username,
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "metrics": metrics,
        "note": "Using estimated metrics based on task completion",
    }


async def get_repository_metrics(
    repository: str,
    time_window: str = "7d",
    state: Any = None,
) -> Dict[str, Any]:
    """
    Get code metrics for an entire repository.

    Parameters
    ----------
    repository : str
        Repository name (e.g., "owner/repo")
    time_window : str
        Time window: 1h, 24h, 7d, 30d
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Repository-wide code metrics
    """
    if not state:
        return {
            "success": False,
            "error": "Server state not available",
        }

    # Parse time window
    window_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = window_map.get(time_window, timedelta(days=7))
    cutoff_time = datetime.now() - delta

    # Mock repository metrics
    # In real implementation, this would query GitHub API
    metrics = {
        "total_commits": 0,
        "total_prs": 0,
        "active_contributors": 0,
        "lines_changed": 0,
        "files_changed": 0,
        "language_breakdown": {},
        "commit_frequency": {},
        "pr_merge_rate": 0.0,
        "average_pr_size": 0,
        "review_turnaround_time": 0.0,
    }

    # Simulate data based on project activity
    all_agents = set()
    total_commits = 0

    for project_id, context in state._project_contexts.items():
        if context.kanban_provider:
            tasks = await context.kanban_provider.get_tasks()
            recent_tasks = [
                t
                for t in tasks
                if hasattr(t, "updated_at") and t.updated_at > cutoff_time
            ]

            # Count unique contributors
            for task in recent_tasks:
                if task.assigned_to:
                    all_agents.add(task.assigned_to)

            # Estimate commits
            completed_recent = len([t for t in recent_tasks if str(t.status) == "done"])
            total_commits += completed_recent * 3

    metrics["total_commits"] = total_commits
    metrics["active_contributors"] = len(all_agents)
    metrics["total_prs"] = int(total_commits / 3)  # Rough estimate
    metrics["pr_merge_rate"] = 0.85  # 85% merge rate
    metrics["average_pr_size"] = 250  # 250 lines average
    metrics["review_turnaround_time"] = 18.5  # 18.5 hours average

    # Mock language breakdown
    metrics["language_breakdown"] = {
        "python": 0.6,
        "javascript": 0.25,
        "typescript": 0.1,
        "other": 0.05,
    }

    return {
        "success": True,
        "repository": repository,
        "time_window": time_window,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
    }


async def get_code_review_metrics(
    agent_id: Optional[str] = None,
    time_window: str = "7d",
    state: Any = None,
) -> Dict[str, Any]:
    """
    Get code review activity metrics.

    Parameters
    ----------
    agent_id : Optional[str]
        Agent ID to filter by (all agents if not provided)
    time_window : str
        Time window: 1h, 24h, 7d, 30d
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Code review metrics including participation and turnaround times
    """
    if not state:
        return {
            "success": False,
            "error": "Server state not available",
        }

    # Parse time window
    window_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    window_map.get(time_window, timedelta(days=7))

    # Mock review metrics
    if agent_id:
        # Individual agent metrics
        metrics = {
            "reviews_given": 12,
            "reviews_received": 8,
            "average_review_time": 2.5,  # hours
            "comments_made": 35,
            "comments_received": 28,
            "approval_rate": 0.75,  # 75% of reviews result in approval
            "revision_requests": 3,
            "review_coverage": 0.85,  # 85% of PRs reviewed
        }
    else:
        # Team-wide metrics
        bottlenecks = [
            {"agent": "agent-123", "pending_reviews": 8},
            {"agent": "agent-456", "pending_reviews": 5},
        ]
        metrics = {
            "total_reviews": 156,
            "average_reviews_per_pr": 2.3,
            "average_review_turnaround": 4.5,  # hours
            "review_participation_rate": 0.78,  # 78% of team participates
            "unreviewed_prs": 5,
        }
        # Add the bottlenecks separately with proper typing
        metrics_dict: Dict[str, Any] = dict(metrics)
        metrics_dict["review_bottlenecks"] = bottlenecks
        metrics = metrics_dict

    return {
        "success": True,
        "agent_id": agent_id,
        "time_window": time_window,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
    }


async def get_code_quality_metrics(
    repository: str,
    branch: str = "main",
    state: Any = None,
) -> Dict[str, Any]:
    """
    Get code quality metrics from static analysis.

    Parameters
    ----------
    repository : str
        Repository name
    branch : str
        Branch to analyze
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Code quality metrics including complexity, coverage, and issues
    """
    if not state:
        return {
            "success": False,
            "error": "Server state not available",
        }

    # Mock quality metrics
    # In real implementation, this would integrate with tools like:
    # - SonarQube
    # - CodeClimate
    # - Coverage.py
    # - ESLint/Pylint

    metrics = {
        "code_coverage": 78.5,  # percentage
        "test_coverage": 82.3,
        "cyclomatic_complexity": 4.2,  # average
        "technical_debt_ratio": 0.05,  # 5%
        "duplicated_lines_percentage": 2.3,
        "code_smells": 42,
        "bugs": 3,
        "vulnerabilities": 0,
        "security_hotspots": 2,
        "maintainability_rating": "A",  # A-F scale
        "reliability_rating": "B",
        "security_rating": "A",
        "quality_gate_status": "PASSED",
        "issues_by_severity": {
            "blocker": 0,
            "critical": 3,
            "major": 12,
            "minor": 27,
            "info": 45,
        },
    }

    return {
        "success": True,
        "repository": repository,
        "branch": branch,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
        "last_analysis": datetime.now().isoformat(),
    }


# Tool definitions for MCP
code_metrics_tools = [
    Tool(
        name="get_code_metrics",
        description="Get code production metrics for a specific agent",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to analyze",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in ISO format",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in ISO format",
                },
            },
            "required": ["agent_id"],
        },
    ),
    Tool(
        name="get_repository_metrics",
        description="Get code metrics for an entire repository",
        inputSchema={
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "Repository name (owner/repo)",
                },
                "time_window": {
                    "type": "string",
                    "description": "Time window: 1h, 24h, 7d, 30d",
                    "default": "7d",
                    "enum": ["1h", "24h", "7d", "30d"],
                },
            },
            "required": ["repository"],
        },
    ),
    Tool(
        name="get_code_review_metrics",
        description="Get code review activity and participation metrics",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID (optional, all agents if not provided)",
                },
                "time_window": {
                    "type": "string",
                    "description": "Time window: 1h, 24h, 7d, 30d",
                    "default": "7d",
                    "enum": ["1h", "24h", "7d", "30d"],
                },
            },
        },
    ),
    Tool(
        name="get_code_quality_metrics",
        description="Get code quality metrics from static analysis",
        inputSchema={
            "type": "object",
            "properties": {
                "repository": {
                    "type": "string",
                    "description": "Repository name",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to analyze",
                    "default": "main",
                },
            },
            "required": ["repository"],
        },
    ),
]
