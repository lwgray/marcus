"""
Project Quality Assessor

Comprehensive quality assessment system that analyzes completed projects
using multiple data sources including GitHub, task metrics, and AI analysis.
"""

import json
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from src.core.models import ProjectState, Task, TaskStatus, WorkerStatus
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.integrations.github_mcp_interface import GitHubMCPInterface
from src.quality.board_quality_validator import BoardQualityValidator


class TaskQualityMetrics(TypedDict):
    """Typed dictionary for task quality metrics."""
    total_tasks: int
    completed_tasks: int
    completion_rate: float
    board_quality_score: float
    description_quality: float
    acceptance_criteria_quality: float
    blocked_task_rate: float
    avg_task_size: float
    task_size_variance: float


class TeamQualityMetrics(TypedDict):
    """Typed dictionary for team quality metrics."""
    team_size: int
    avg_tasks_per_member: float
    skill_diversity: int
    workload_balance: float
    collaboration_index: float
    member_performance: Dict[str, Dict[str, Any]]


class DeliveryQualityMetrics(TypedDict):
    """Typed dictionary for delivery quality metrics."""
    progress_percent: float
    velocity_trend: str
    on_time_delivery_rate: float
    late_task_rate: float
    risk_score: float
    projected_completion_days: int


class GitHubDataCollection(TypedDict):
    """Typed dictionary for GitHub data collection."""
    commits: List[Dict[str, Any]]
    pull_requests: List[Dict[str, Any]]
    issues: List[Dict[str, Any]]
    reviews: List[Dict[str, Any]]


class AIAssessmentResult(TypedDict):
    """Typed dictionary for AI assessment results."""
    insights: List[str]
    recommendations: List[str]
    overall_assessment: str
    strengths: List[str]
    weaknesses: List[str]


class SuccessDetermination(TypedDict):
    """Typed dictionary for success determination results."""
    is_successful: bool
    confidence: float
    reasoning: str
    criteria_met: int
    total_criteria: int


@dataclass
class CodeQualityMetrics:
    """Metrics extracted from GitHub repository analysis."""

    test_coverage: float = 0.0
    code_review_coverage: float = 0.0
    avg_pr_size: float = 0.0
    merge_conflict_rate: float = 0.0
    commit_frequency: float = 0.0
    documentation_coverage: float = 0.0
    linting_score: float = 0.0
    security_issues: int = 0
    performance_issues: int = 0
    maintainability_index: float = 0.0


@dataclass
class ProcessQualityMetrics:
    """Metrics related to development process quality."""

    pr_approval_rate: float = 0.0
    avg_review_time_hours: float = 0.0
    ci_success_rate: float = 0.0
    deployment_frequency: float = 0.0
    rollback_rate: float = 0.0
    issue_resolution_time: float = 0.0
    collaboration_score: float = 0.0
    planning_accuracy: float = 0.0


@dataclass
class ProjectQualityAssessment:
    """Complete quality assessment for a project."""

    project_id: str
    project_name: str
    assessment_date: datetime
    overall_score: float

    # Component scores (0-1)
    code_quality_score: float
    process_quality_score: float
    delivery_quality_score: float
    team_quality_score: float

    # Detailed metrics
    code_metrics: CodeQualityMetrics
    process_metrics: ProcessQualityMetrics

    # AI analysis
    ai_assessment: Dict[str, Any]
    quality_insights: List[str]
    improvement_areas: List[str]

    # Success determination
    is_successful: bool
    success_confidence: float
    success_reasoning: str

    # Raw data
    github_data: Dict[str, Any] = field(default_factory=dict)
    task_data: Dict[str, Any] = field(default_factory=dict)


class ProjectQualityAssessor:
    """
    Comprehensive quality assessment for completed projects.

    Integrates multiple data sources to provide a holistic view of project quality,
    including code quality, process adherence, team performance, and delivery metrics.
    """

    def __init__(
        self,
        ai_engine: Optional[AIAnalysisEngine] = None,
        github_mcp: Optional[GitHubMCPInterface] = None,
        board_validator: Optional[BoardQualityValidator] = None,
    ) -> None:
        """
        Initialize the quality assessor.

        Parameters
        ----------
        ai_engine : Optional[AIAnalysisEngine]
            AI engine for quality analysis
        github_mcp : Optional[GitHubMCPInterface]
            GitHub MCP interface for repository analysis
        board_validator : Optional[BoardQualityValidator]
            Board quality validator for task quality
        """
        self.ai_engine = ai_engine or AIAnalysisEngine()
        self.github_mcp = github_mcp
        self.board_validator = board_validator or BoardQualityValidator()

    async def assess_project_quality(
        self,
        project_state: ProjectState,
        tasks: List[Task],
        team_members: List[WorkerStatus],
        github_config: Optional[Dict[str, str]] = None,
    ) -> ProjectQualityAssessment:
        """
        Perform comprehensive quality assessment on a completed project.

        Parameters
        ----------
        project_state : ProjectState
            Final state of the project
        tasks : List[Task]
            All tasks from the project
        team_members : List[WorkerStatus]
            Team members who worked on the project
        github_config : Optional[Dict[str, str]]
            GitHub configuration with owner, repo, and date range

        Returns
        -------
        ProjectQualityAssessment
            Complete quality assessment with scores and insights
        """
        # Collect all quality data
        task_metrics = self._analyze_task_quality(tasks)
        team_metrics = self._analyze_team_quality(tasks, team_members)
        delivery_metrics = self._analyze_delivery_quality(project_state, tasks)

        # GitHub analysis if available
        code_metrics = CodeQualityMetrics()
        process_metrics = ProcessQualityMetrics()
        github_data: Dict[str, Any] = {}

        if self.github_mcp and github_config:
            try:
                github_data_collection = await self._collect_github_data(github_config)
                github_data = dict(github_data_collection)
                code_metrics = await self._analyze_code_quality(github_data)
                process_metrics = await self._analyze_process_quality(github_data)
            except Exception as e:
                # Continue without GitHub data
                print(f"GitHub analysis failed: {e}", file=sys.stderr)

        # Calculate component scores
        code_score = self._calculate_code_quality_score(code_metrics)
        process_score = self._calculate_process_quality_score(process_metrics)
        delivery_score = self._calculate_delivery_quality_score(delivery_metrics)
        team_score = self._calculate_team_quality_score(team_metrics)

        # Overall score (weighted average)
        overall_score = (
            code_score * 0.3
            + process_score * 0.2
            + delivery_score * 0.3
            + team_score * 0.2
        )

        # AI assessment
        ai_assessment = await self._perform_ai_assessment(
            project_state, code_metrics, process_metrics, task_metrics, team_metrics
        )

        # Determine success
        success_determination = self._determine_project_success(
            overall_score, delivery_metrics, ai_assessment
        )

        # Extract insights
        quality_insights = self._extract_quality_insights(
            code_metrics, process_metrics, delivery_metrics, team_metrics, ai_assessment
        )

        improvement_areas = self._identify_improvement_areas(
            code_score, process_score, delivery_score, team_score, ai_assessment
        )

        return ProjectQualityAssessment(
            project_id=project_state.board_id,
            project_name=project_state.project_name,
            assessment_date=datetime.now(),
            overall_score=overall_score,
            code_quality_score=code_score,
            process_quality_score=process_score,
            delivery_quality_score=delivery_score,
            team_quality_score=team_score,
            code_metrics=code_metrics,
            process_metrics=process_metrics,
            ai_assessment=dict(ai_assessment),
            quality_insights=quality_insights,
            improvement_areas=improvement_areas,
            is_successful=success_determination["is_successful"],
            success_confidence=success_determination["confidence"],
            success_reasoning=success_determination["reasoning"],
            github_data=github_data,
            task_data={
                "task_metrics": task_metrics,
                "team_metrics": team_metrics,
                "delivery_metrics": delivery_metrics,
            },
        )

    def _analyze_task_quality(self, tasks: List[Task]) -> TaskQualityMetrics:
        """Analyze quality metrics from tasks."""
        completed_tasks = [t for t in tasks if t.status == TaskStatus.DONE]

        # Board quality validation
        quality_report = self.board_validator.validate_board(tasks)

        metrics = {
            "total_tasks": len(tasks),
            "completed_tasks": len(completed_tasks),
            "completion_rate": len(completed_tasks) / len(tasks) if tasks else 0,
            "board_quality_score": quality_report.score,
            "description_quality": quality_report.metrics.get(
                "description_coverage", 0
            ),
            "acceptance_criteria_quality": quality_report.metrics.get(
                "acceptance_criteria", 0
            ),
            "blocked_task_rate": (
                len([t for t in tasks if t.status == TaskStatus.BLOCKED]) / len(tasks)
                if tasks
                else 0
            ),
            "avg_task_size": (
                statistics.mean([t.estimated_hours for t in tasks if t.estimated_hours])
                if any(t.estimated_hours for t in tasks)
                else 0
            ),
            "task_size_variance": (
                statistics.stdev(
                    [t.estimated_hours for t in tasks if t.estimated_hours]
                )
                if sum(1 for t in tasks if t.estimated_hours) > 1
                else 0
            ),
        }

        return TaskQualityMetrics(
            total_tasks=metrics["total_tasks"],
            completed_tasks=metrics["completed_tasks"],
            completion_rate=metrics["completion_rate"],
            board_quality_score=metrics["board_quality_score"],
            description_quality=metrics["description_quality"],
            acceptance_criteria_quality=metrics["acceptance_criteria_quality"],
            blocked_task_rate=metrics["blocked_task_rate"],
            avg_task_size=metrics["avg_task_size"],
            task_size_variance=metrics["task_size_variance"]
        )

    def _analyze_team_quality(
        self, tasks: List[Task], team_members: List[WorkerStatus]
    ) -> TeamQualityMetrics:
        """Analyze team performance quality."""
        metrics: Dict[str, Any] = {
            "team_size": len(team_members),
            "avg_tasks_per_member": (
                len(tasks) / len(team_members) if team_members else 0
            ),
            "skill_diversity": len(
                set(skill for member in team_members for skill in member.skills)
            ),
            "workload_balance": self._calculate_workload_balance(tasks, team_members),
            "collaboration_index": self._calculate_collaboration_index(
                tasks, team_members
            ),
        }

        # Per-member metrics
        member_performance: Dict[str, Any] = {}
        for member in team_members:
            member_tasks = [t for t in tasks if t.assigned_to == member.worker_id]
            completed = [t for t in member_tasks if t.status == TaskStatus.DONE]

            member_performance[member.worker_id] = {
                "completion_rate": (
                    len(completed) / len(member_tasks) if member_tasks else 0
                ),
                "task_count": len(member_tasks),
                "performance_score": member.performance_score,
            }

        metrics["member_performance"] = member_performance

        return TeamQualityMetrics(
            team_size=metrics["team_size"],
            avg_tasks_per_member=metrics["avg_tasks_per_member"],
            skill_diversity=metrics["skill_diversity"],
            workload_balance=metrics["workload_balance"],
            collaboration_index=metrics["collaboration_index"],
            member_performance=metrics["member_performance"]
        )

    def _analyze_delivery_quality(
        self, project_state: ProjectState, tasks: List[Task]
    ) -> DeliveryQualityMetrics:
        """Analyze delivery and timeline quality."""
        completed_tasks = [t for t in tasks if t.status == TaskStatus.DONE]

        # Calculate on-time delivery
        on_time_tasks = 0
        late_tasks = 0

        for task in completed_tasks:
            if task.due_date and task.updated_at:
                if task.updated_at <= task.due_date:
                    on_time_tasks += 1
                else:
                    late_tasks += 1

        total_with_due_dates = on_time_tasks + late_tasks

        metrics = {
            "progress_percent": project_state.progress_percent,
            "velocity_trend": getattr(project_state, "velocity_trend", "stable"),
            "on_time_delivery_rate": (
                on_time_tasks / total_with_due_dates
                if total_with_due_dates > 0
                else 1.0
            ),
            "late_task_rate": (
                late_tasks / total_with_due_dates if total_with_due_dates > 0 else 0.0
            ),
            "risk_score": getattr(project_state, "risk_score", 0.5),
            "projected_completion_days": (
                (projected_completion_date - datetime.now()).days
                if (
                    projected_completion_date := getattr(
                        project_state, "projected_completion_date", None
                    )
                )
                else 0
            ),
        }

        return DeliveryQualityMetrics(
            progress_percent=float(metrics["progress_percent"]),
            velocity_trend=str(metrics["velocity_trend"]),
            on_time_delivery_rate=float(metrics["on_time_delivery_rate"]),
            late_task_rate=float(metrics["late_task_rate"]),
            risk_score=float(metrics["risk_score"]),
            projected_completion_days=int(metrics["projected_completion_days"])
        )

    async def _collect_github_data(self, config: Dict[str, str]) -> GitHubDataCollection:
        """Collect data from GitHub repository."""
        if not self.github_mcp:
            return GitHubDataCollection(
                commits=[],
                pull_requests=[],
                issues=[],
                reviews=[]
            )

        owner = config.get("github_owner", "")
        repo = config.get("github_repo", "")
        start_date = config.get("project_start_date", "")

        data: GitHubDataCollection = {
            "commits": [],
            "pull_requests": [],
            "issues": [],
            "reviews": [],
        }

        try:
            # Get commits
            commits_result = await self.github_mcp.list_commits(
                owner=owner,
                repo=repo,
                since=start_date,
            )
            data["commits"] = commits_result.get("commits", [])

            # Get pull requests
            prs_result = await self.github_mcp.search_issues(
                query=f"repo:{owner}/{repo} is:pr created:>={start_date}",
            )
            data["pull_requests"] = prs_result.get("items", [])

            # Get issues
            issues_result = await self.github_mcp.search_issues(
                query=f"repo:{owner}/{repo} is:issue created:>={start_date}",
            )
            data["issues"] = issues_result.get("items", [])

            # Get PR reviews for each PR
            for pr in data["pull_requests"][:10]:  # Limit to avoid rate limits
                reviews_result = await self.github_mcp.list_pr_reviews(
                    owner=owner,
                    repo=repo,
                    pr_number=pr["number"],
                )
                data["reviews"].extend(reviews_result.get("reviews", []))

        except Exception as e:
            print(f"Error collecting GitHub data: {e}", file=sys.stderr)

        return data

    async def _analyze_code_quality(
        self, github_data: Dict[str, Any]
    ) -> CodeQualityMetrics:
        """Analyze code quality from GitHub data."""
        metrics = CodeQualityMetrics()

        commits = github_data.get("commits", [])
        prs = github_data.get("pull_requests", [])
        reviews = github_data.get("reviews", [])

        # Commit frequency (commits per week)
        if commits:
            first_commit_date = datetime.fromisoformat(
                commits[-1]["commit"]["author"]["date"].replace("Z", "+00:00")
            )
            last_commit_date = datetime.fromisoformat(
                commits[0]["commit"]["author"]["date"].replace("Z", "+00:00")
            )
            weeks = max((last_commit_date - first_commit_date).days / 7, 1)
            metrics.commit_frequency = len(commits) / weeks

        # Code review coverage
        reviewed_prs = len(set(r["pull_request_url"].split("/")[-1] for r in reviews))
        metrics.code_review_coverage = reviewed_prs / len(prs) if prs else 0

        # Average PR size (simplified - would need file changes data)
        metrics.avg_pr_size = 100  # Placeholder

        # Test coverage (would need CI/CD integration)
        metrics.test_coverage = 0.75  # Placeholder

        # Documentation (check for README updates)
        doc_commits = [
            c
            for c in commits
            if any(
                "readme" in msg.lower() or "doc" in msg.lower()
                for msg in [c["commit"]["message"]]
            )
        ]
        metrics.documentation_coverage = (
            len(doc_commits) / len(commits) if commits else 0
        )

        # Linting score (would need CI/CD data)
        metrics.linting_score = 0.85  # Placeholder

        # Maintainability index
        metrics.maintainability_index = (
            metrics.test_coverage * 0.3
            + metrics.documentation_coverage * 0.2
            + metrics.linting_score * 0.2
            + metrics.code_review_coverage * 0.3
        )

        return metrics

    async def _analyze_process_quality(
        self, github_data: Dict[str, Any]
    ) -> ProcessQualityMetrics:
        """Analyze development process quality from GitHub data."""
        metrics = ProcessQualityMetrics()

        prs = github_data.get("pull_requests", [])
        reviews = github_data.get("reviews", [])
        issues = github_data.get("issues", [])

        # PR approval rate
        approved_reviews = [r for r in reviews if r.get("state") == "APPROVED"]
        metrics.pr_approval_rate = (
            len(approved_reviews) / len(reviews) if reviews else 1.0
        )

        # Average review time
        review_times = []
        for pr in prs:
            if pr.get("merged_at") and pr.get("created_at"):
                created = datetime.fromisoformat(
                    pr["created_at"].replace("Z", "+00:00")
                )
                merged = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
                review_times.append((merged - created).total_seconds() / 3600)

        metrics.avg_review_time_hours = (
            statistics.mean(review_times) if review_times else 0
        )

        # CI success rate (would need CI/CD data)
        metrics.ci_success_rate = 0.9  # Placeholder

        # Issue resolution time
        closed_issues = [i for i in issues if i.get("closed_at")]
        resolution_times = []

        for issue in closed_issues:
            created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
            closed = datetime.fromisoformat(issue["closed_at"].replace("Z", "+00:00"))
            resolution_times.append((closed - created).days)

        metrics.issue_resolution_time = (
            statistics.mean(resolution_times) if resolution_times else 0
        )

        # Collaboration score (based on PR participation)
        unique_reviewers = len(set(r.get("user", {}).get("login", "") for r in reviews))
        unique_pr_authors = len(set(pr.get("user", {}).get("login", "") for pr in prs))

        if unique_pr_authors > 0:
            metrics.collaboration_score = min(unique_reviewers / unique_pr_authors, 1.0)

        return metrics

    def _calculate_code_quality_score(self, metrics: CodeQualityMetrics) -> float:
        """Calculate overall code quality score (0-1)."""
        scores = [
            metrics.test_coverage,
            metrics.code_review_coverage,
            min(metrics.commit_frequency / 20, 1.0),  # Normalize to 20 commits/week
            metrics.documentation_coverage,
            metrics.linting_score,
            metrics.maintainability_index,
            1.0 - min(metrics.security_issues / 10, 1.0),  # Penalize security issues
            1.0 - min(metrics.merge_conflict_rate, 1.0),
        ]

        return statistics.mean([s for s in scores if s > 0])

    def _calculate_process_quality_score(self, metrics: ProcessQualityMetrics) -> float:
        """Calculate overall process quality score (0-1)."""
        scores = [
            metrics.pr_approval_rate,
            1.0 - min(metrics.avg_review_time_hours / 48, 1.0),  # Normalize to 48 hours
            metrics.ci_success_rate,
            min(metrics.deployment_frequency / 5, 1.0),  # Normalize to 5 deploys/week
            1.0 - metrics.rollback_rate,
            1.0 - min(metrics.issue_resolution_time / 7, 1.0),  # Normalize to 7 days
            metrics.collaboration_score,
            metrics.planning_accuracy,
        ]

        return statistics.mean([s for s in scores if s > 0])

    def _calculate_delivery_quality_score(self, metrics: DeliveryQualityMetrics) -> float:
        """Calculate delivery quality score (0-1)."""
        scores = [
            metrics["progress_percent"] / 100,
            metrics["on_time_delivery_rate"],
            1.0 - metrics["late_task_rate"],
            1.0 - min(metrics["risk_score"], 1.0),
        ]

        # Velocity trend contribution
        velocity_trend = metrics["velocity_trend"]
        if velocity_trend == "increasing":
            scores.append(1.0)
        elif velocity_trend == "stable":
            scores.append(0.8)
        else:
            scores.append(0.5)

        return float(statistics.mean(scores))

    def _calculate_team_quality_score(self, metrics: TeamQualityMetrics) -> float:
        """Calculate team quality score (0-1)."""
        scores = [
            metrics["workload_balance"],
            min(metrics["skill_diversity"] / 10, 1.0),  # Normalize to 10 skills
            metrics["collaboration_index"],
        ]

        # Add member performance scores
        member_perf = metrics["member_performance"]
        if member_perf:
            avg_completion = statistics.mean(
                [m["completion_rate"] for m in member_perf.values()]
            )
            scores.append(avg_completion)

        return float(statistics.mean(scores))

    async def _perform_ai_assessment(
        self,
        project_state: ProjectState,
        code_metrics: CodeQualityMetrics,
        process_metrics: ProcessQualityMetrics,
        task_metrics: TaskQualityMetrics,
        team_metrics: TeamQualityMetrics,
    ) -> AIAssessmentResult:
        """Use AI to provide qualitative assessment."""
        if not self.ai_engine.client:
            return AIAssessmentResult(
                insights=[],
                recommendations=[],
                overall_assessment="unknown",
                strengths=[],
                weaknesses=[]
            )

        prompt = f"""Analyze this completed project and provide quality assessment:

Project: {project_state.project_name}
Progress: {project_state.progress_percent}%

Code Quality:
- Test Coverage: {code_metrics.test_coverage:.1%}
- Code Review Coverage: {code_metrics.code_review_coverage:.1%}
- Documentation: {code_metrics.documentation_coverage:.1%}
- Maintainability: {code_metrics.maintainability_index:.2f}

Process Quality:
- PR Approval Rate: {process_metrics.pr_approval_rate:.1%}
- Avg Review Time: {process_metrics.avg_review_time_hours:.1f} hours
- CI Success Rate: {process_metrics.ci_success_rate:.1%}

Task Quality:
- Completion Rate: {task_metrics.get('completion_rate', 0):.1%}
- Board Quality: {task_metrics.get('board_quality_score', 0):.2f}
- Blocked Task Rate: {task_metrics.get('blocked_task_rate', 0):.1%}

Team Performance:
- Team Size: {team_metrics.get('team_size', 0)}
- Workload Balance: {team_metrics.get('workload_balance', 0):.2f}
- Collaboration Index: {team_metrics.get('collaboration_index', 0):.2f}

Provide:
1. Key quality insights (3-5 points)
2. Specific recommendations for improvement (3-5 points)
3. Overall quality assessment (excellent/good/fair/poor)

Return JSON:
{{
    "insights": ["insight1", "insight2", ...],
    "recommendations": ["rec1", "rec2", ...],
    "overall_assessment": "good",
    "strengths": ["strength1", "strength2", ...],
    "weaknesses": ["weakness1", "weakness2", ...]
}}"""

        try:
            response = await self.ai_engine._call_claude(prompt)
            result = json.loads(response)
            return AIAssessmentResult(
                insights=result.get("insights", []),
                recommendations=result.get("recommendations", []),
                overall_assessment=result.get("overall_assessment", "unknown"),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", [])
            ) if isinstance(result, dict) else AIAssessmentResult(
                insights=[],
                recommendations=[],
                overall_assessment="unknown",
                strengths=[],
                weaknesses=[]
            )
        except Exception:
            return AIAssessmentResult(
                insights=["Unable to perform AI assessment"],
                recommendations=[],
                overall_assessment="unknown",
                strengths=[],
                weaknesses=[]
            )

    def _determine_project_success(
        self,
        overall_score: float,
        delivery_metrics: DeliveryQualityMetrics,
        ai_assessment: AIAssessmentResult,
    ) -> SuccessDetermination:
        """Determine if project was successful."""
        # Success criteria
        criteria = {
            "quality_threshold": overall_score >= 0.7,
            "completion_threshold": delivery_metrics.get("progress_percent", 0) >= 95,
            "on_time_delivery": delivery_metrics.get("on_time_delivery_rate", 0) >= 0.8,
            "low_risk": delivery_metrics.get("risk_score", 1.0) < 0.3,
            "ai_assessment": ai_assessment.get("overall_assessment")
            in ["excellent", "good"],
        }

        # Count met criteria
        met_criteria = sum(criteria.values())
        total_criteria = len(criteria)

        # Determine success
        is_successful = met_criteria >= 3  # At least 3 out of 5 criteria
        confidence = met_criteria / total_criteria

        # Generate reasoning
        reasoning_parts = []
        if criteria["quality_threshold"]:
            reasoning_parts.append(
                f"Quality score {overall_score:.1%} exceeds threshold"
            )
        if criteria["completion_threshold"]:
            reasoning_parts.append(
                f"Project {delivery_metrics.get('progress_percent', 0)}% complete"
            )
        if criteria["on_time_delivery"]:
            reasoning_parts.append("Strong on-time delivery performance")
        if not criteria["low_risk"]:
            reasoning_parts.append("Some risk factors present")

        reasoning = (
            ". ".join(reasoning_parts)
            if reasoning_parts
            else "Based on overall metrics"
        )

        return SuccessDetermination(
            is_successful=is_successful,
            confidence=confidence,
            reasoning=reasoning,
            criteria_met=met_criteria,
            total_criteria=total_criteria
        )

    def _extract_quality_insights(
        self,
        code_metrics: CodeQualityMetrics,
        process_metrics: ProcessQualityMetrics,
        delivery_metrics: DeliveryQualityMetrics,
        team_metrics: TeamQualityMetrics,
        ai_assessment: AIAssessmentResult,
    ) -> List[str]:
        """Extract key quality insights."""
        insights = []

        # Code quality insights
        if code_metrics.test_coverage > 0.8:
            insights.append("Excellent test coverage ensures code reliability")
        elif code_metrics.test_coverage < 0.5:
            insights.append("Low test coverage poses quality risks")

        if code_metrics.code_review_coverage > 0.9:
            insights.append("Comprehensive code review process in place")

        # Process insights
        if process_metrics.avg_review_time_hours < 24:
            insights.append("Fast code review turnaround enhances velocity")
        elif process_metrics.avg_review_time_hours > 72:
            insights.append("Slow code reviews may be impacting delivery")

        # Delivery insights
        if delivery_metrics.get("on_time_delivery_rate", 0) > 0.9:
            insights.append("Exceptional on-time delivery performance")

        # Team insights
        if team_metrics.get("workload_balance", 0) > 0.8:
            insights.append("Well-balanced workload across team members")

        # Add AI insights
        insights.extend(ai_assessment.get("insights", [])[:3])

        return insights[:5]  # Limit to 5 insights

    def _identify_improvement_areas(
        self,
        code_score: float,
        process_score: float,
        delivery_score: float,
        team_score: float,
        ai_assessment: AIAssessmentResult,
    ) -> List[str]:
        """Identify areas for improvement."""
        areas = []

        # Score-based improvements
        scores = {
            "code quality": code_score,
            "development process": process_score,
            "delivery performance": delivery_score,
            "team collaboration": team_score,
        }

        # Find lowest scoring areas
        for area, score in sorted(scores.items(), key=lambda x: x[1]):
            if score < 0.7:
                areas.append(f"Improve {area} (current score: {score:.1%})")

        # Add AI recommendations
        areas.extend(ai_assessment.get("recommendations", [])[:3])

        return areas[:5]  # Limit to 5 areas

    def _calculate_workload_balance(
        self, tasks: List[Task], team_members: List[WorkerStatus]
    ) -> float:
        """Calculate how evenly work is distributed."""
        if len(team_members) < 2:
            return 1.0

        # Count tasks per member
        task_counts = {}
        for member in team_members:
            member_tasks = [t for t in tasks if t.assigned_to == member.worker_id]
            task_counts[member.worker_id] = len(member_tasks)

        if not task_counts:
            return 0.0

        # Calculate coefficient of variation (lower is better)
        mean_tasks = statistics.mean(task_counts.values())
        if mean_tasks == 0:
            return 1.0

        std_dev = statistics.stdev(task_counts.values()) if len(task_counts) > 1 else 0
        cv = std_dev / mean_tasks

        # Convert to 0-1 score (1 is perfectly balanced)
        return max(0, 1 - cv)

    def _calculate_collaboration_index(
        self, tasks: List[Task], team_members: List[WorkerStatus]
    ) -> float:
        """Calculate team collaboration index."""
        if len(team_members) < 2:
            return 0.0

        # Simple heuristic: tasks with multiple assignees or handoffs
        # In reality, would track task reassignments and dependencies
        collaborative_indicators = 0.0

        for task in tasks:
            # Check for collaboration labels
            if task.labels:
                if any(
                    "collab" in label.lower() or "pair" in label.lower()
                    for label in task.labels
                ):
                    collaborative_indicators += 1
                elif any("review" in label.lower() for label in task.labels):
                    collaborative_indicators += 0.5

        # Normalize by total tasks and team size
        max_collaboration = (
            len(tasks) * 0.3
        )  # Assume 30% of tasks could be collaborative

        return (
            min(collaborative_indicators / max_collaboration, 1.0)
            if max_collaboration > 0
            else 0.0
        )
