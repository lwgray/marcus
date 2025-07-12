"""Project monitoring and health tracking system.

This module implements comprehensive project monitoring capabilities including
real-time health tracking, risk assessment, performance metrics collection,
and automated alerting for the Marcus system.

Classes
-------
ProjectMonitor
    Core monitoring system that provides continuous project health tracking,
    AI-powered risk analysis, and automated issue detection.

Key Features
------------
- Continuous monitoring loop with configurable intervals
- Real-time project state tracking and metrics collection
- AI-powered project health analysis and risk assessment
- Automated detection of stalled tasks, capacity issues, and bottlenecks
- Historical data tracking for trend analysis
- Integration with MCP Kanban system for task data

Examples
--------
Basic monitoring setup:

>>> import asyncio
>>> from src.monitoring.project_monitor import ProjectMonitor
>>>
>>> async def main():
...     monitor = ProjectMonitor()
...
...     # Start continuous monitoring
...     await monitor.start_monitoring()
>>>
>>> asyncio.run(main())

Manual project state check:

>>> monitor = ProjectMonitor()
>>> state = await monitor.get_project_state()
>>> print(f"Progress: {state.progress_percent}%")
>>> print(f"Risk Level: {state.risk_level}")
>>> print(f"Velocity: {state.team_velocity} tasks/week")

Risk and blocker management:

>>> # Get current risks
>>> risks = monitor.get_current_risks()
>>> for risk in risks:
...     print(f"{risk.risk_type}: {risk.description}")
>>>
>>> # Record a blocker
>>> blocker = await monitor.record_blocker(
...     agent_id="agent-123",
...     task_id="task-456",
...     description="Database connection failed"
... )
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.config.settings import Settings
from src.core.models import (
    BlockerReport,
    ProjectRisk,
    ProjectState,
    RiskLevel,
    Task,
    TaskStatus,
)
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.integrations.github_mcp_interface import GitHubMCPInterface
from src.integrations.kanban_client import KanbanClient
from src.learning.project_pattern_learner import ProjectPatternLearner
from src.quality.project_quality_assessor import ProjectQualityAssessor
from src.recommendations.recommendation_engine import ProjectOutcome


class ProjectMonitor:
    """Continuous monitoring system for project health and performance tracking.

    The ProjectMonitor class provides comprehensive project oversight through
    real-time monitoring, AI-powered analysis, and automated issue detection.
    It integrates with the MCP Kanban system to track project progress and
    identifies potential risks before they impact project timelines.

    Attributes
    ----------
    settings : Settings
        Configuration settings for the monitoring system
    kanban_client : KanbanClient
        Client for interacting with the MCP Kanban board
    ai_engine : AIAnalysisEngine
        AI engine for project health analysis and risk assessment
    current_state : Optional[ProjectState]
        Current project state with metrics and health indicators
    blockers : List[BlockerReport]
        List of reported blockers across all tasks
    risks : List[ProjectRisk]
        List of identified project risks with mitigation strategies
    historical_data : List[Dict]
        Historical metrics data for trend analysis
    check_interval : int
        Interval in seconds between monitoring checks (default: 900s/15min)
    is_monitoring : bool
        Flag indicating if continuous monitoring is active

    Methods
    -------
    start_monitoring()
        Start the continuous monitoring loop
    stop_monitoring()
        Stop the continuous monitoring loop
    get_project_state()
        Get current project state with latest metrics
    record_blocker(agent_id, task_id, description)
        Record a new blocker report
    get_current_risks()
        Get list of current project risks
    get_active_blockers()
        Get list of unresolved blockers

    Examples
    --------
    Initialize and start monitoring:

    >>> monitor = ProjectMonitor()
    >>> await monitor.start_monitoring()

    Get project health status:

    >>> state = await monitor.get_project_state()
    >>> print(f"Progress: {state.progress_percent}%")
    >>> print(f"Risk: {state.risk_level.value}")

    Record a blocker:

    >>> blocker = await monitor.record_blocker(
    ...     agent_id="agent-001",
    ...     task_id="task-123",
    ...     description="API endpoint not responding"
    ... )
    """

    def __init__(self) -> None:
        self.settings = Settings()
        self.kanban_client = KanbanClient()
        self.ai_engine = AIAnalysisEngine()

        # Pattern learning and quality assessment
        self.pattern_learner = ProjectPatternLearner(ai_engine=self.ai_engine)
        self.quality_assessor = ProjectQualityAssessor(ai_engine=self.ai_engine)

        # Connect pattern learner to recommendation engine
        from src.recommendations.recommendation_engine import (
            PipelineRecommendationEngine,
        )

        self.recommendation_engine = PipelineRecommendationEngine(
            pattern_learner=self.pattern_learner
        )

        # State tracking
        self.current_state: Optional[ProjectState] = None
        self.blockers: List[BlockerReport] = []
        self.risks: List[ProjectRisk] = []
        self.historical_data: List[Dict] = []

        # Monitoring configuration
        self.check_interval = self.settings.get(
            "monitoring_interval", 900
        )  # 15 minutes
        self.is_monitoring = False

    async def start_monitoring(self) -> None:
        """Start the continuous monitoring loop.

        Initiates the main monitoring loop that continuously collects project
        data, analyzes health metrics, checks for issues, and records historical
        data at regular intervals defined by check_interval.

        The monitoring loop performs the following operations:
        1. Collect current project data from the kanban board
        2. Analyze project health using AI engine
        3. Check for various issues (stalled tasks, capacity problems, etc.)
        4. Record metrics for historical tracking

        The loop continues until stop_monitoring() is called or an unrecoverable
        error occurs. Individual monitoring cycles that encounter errors will log
        the error and continue with the next cycle.

        Raises
        ------
        Exception
            If there are critical errors in the monitoring setup that prevent
            the loop from starting

        Examples
        --------
        >>> monitor = ProjectMonitor()
        >>> await monitor.start_monitoring()  # Runs indefinitely

        Run monitoring for a specific duration:

        >>> import asyncio
        >>> monitor = ProjectMonitor()
        >>>
        >>> # Start monitoring in background
        >>> monitor_task = asyncio.create_task(monitor.start_monitoring())
        >>>
        >>> # Do other work...
        >>> await asyncio.sleep(3600)  # Run for 1 hour
        >>>
        >>> # Stop monitoring
        >>> await monitor.stop_monitoring()
        >>> await monitor_task

        Notes
        -----
        The monitoring interval can be configured via the 'monitoring_interval'
        setting. Default is 900 seconds (15 minutes). Shorter intervals provide
        more responsive monitoring but increase system load.
        """
        self.is_monitoring = True

        while self.is_monitoring:
            try:
                # Collect project data
                await self._collect_project_data()

                # Analyze project health
                await self._analyze_project_health()

                # Check for issues
                await self._check_for_issues()

                # Check for project completion
                await self._check_for_project_completion()

                # Store historical data
                self._record_metrics()

            except Exception as e:
                print(f"Error in monitoring loop: {e}")

            # Wait before next check
            await asyncio.sleep(self.check_interval)

    async def stop_monitoring(self) -> None:
        """Stop the continuous monitoring loop.

        Gracefully stops the monitoring loop by setting the is_monitoring flag
        to False. The current monitoring cycle will complete before the loop exits.

        Examples
        --------
        >>> monitor = ProjectMonitor()
        >>> # Start monitoring in background
        >>> monitor_task = asyncio.create_task(monitor.start_monitoring())
        >>>
        >>> # Stop monitoring after some time
        >>> await monitor.stop_monitoring()
        >>> await monitor_task  # Wait for loop to exit
        """
        self.is_monitoring = False

    async def get_project_state(self) -> ProjectState:
        """Get current project state with latest metrics.

        Retrieves the current project state including progress metrics, task
        counts, velocity data, and risk assessment. If no current state exists,
        it will collect fresh data from the kanban board.

        Returns
        -------
        ProjectState
            Current project state containing:
            - board_id: Kanban board identifier
            - project_name: Name of the project
            - total_tasks: Total number of tasks
            - completed_tasks: Number of completed tasks
            - in_progress_tasks: Number of tasks in progress
            - blocked_tasks: Number of blocked tasks
            - progress_percent: Overall progress percentage
            - overdue_tasks: List of overdue tasks
            - team_velocity: Tasks completed per week
            - risk_level: Overall project risk level
            - last_updated: Timestamp of last update

        Examples
        --------
        >>> monitor = ProjectMonitor()
        >>> state = await monitor.get_project_state()
        >>> print(f"Project: {state.project_name}")
        >>> print(f"Progress: {state.progress_percent:.1f}%")
        >>> print(f"Velocity: {state.team_velocity} tasks/week")
        >>> print(f"Risk Level: {state.risk_level.value}")

        Check for overdue tasks:

        >>> state = await monitor.get_project_state()
        >>> if state.overdue_tasks:
        ...     print(f"Warning: {len(state.overdue_tasks)} overdue tasks")
        ...     for task in state.overdue_tasks:
        ...         print(f"  - {task.name} (due: {task.due_date})")
        """
        if not self.current_state:
            await self._collect_project_data()
        return self.current_state

    async def _collect_project_data(self) -> None:
        """Collect comprehensive project data from kanban board.

        Gathers current project metrics including task counts, progress,
        velocity calculations, and risk assessment. Updates the current_state
        attribute with fresh data from the kanban board.

        The method performs the following data collection:
        1. Retrieves board summary and all tasks from kanban system
        2. Calculates task distribution across status categories
        3. Identifies overdue tasks based on due dates
        4. Computes progress percentage and team velocity
        5. Assesses overall project risk level
        6. Updates the current_state with collected metrics

        Raises
        ------
        Exception
            If there are errors communicating with the kanban board or
            processing the retrieved data

        Notes
        -----
        This method is called automatically by the monitoring loop and when
        get_project_state() is called with no existing state. It integrates
        with the MCP Kanban client to retrieve real-time project data.
        """
        # Get board summary
        summary = await self.kanban_client.get_board_summary()

        # Get all tasks
        all_tasks = await self._get_all_tasks()

        # Calculate metrics
        total_tasks = len(all_tasks)
        completed_tasks = len([t for t in all_tasks if t.status == TaskStatus.DONE])
        in_progress_tasks = len(
            [t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]
        )
        blocked_tasks = len([t for t in all_tasks if t.status == TaskStatus.BLOCKED])

        # Find overdue tasks
        overdue_tasks = []
        now = datetime.now()
        for task in all_tasks:
            if task.due_date and task.due_date < now and task.status != TaskStatus.DONE:
                overdue_tasks.append(task)

        # Calculate progress
        progress_percent = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )

        # Calculate velocity (tasks completed per week)
        velocity = await self._calculate_velocity(all_tasks)

        # Determine velocity trend
        velocity_trend = self._calculate_velocity_trend(velocity)

        # Determine risk level and score
        risk_level = self._assess_risk_level(
            progress_percent, len(overdue_tasks), blocked_tasks, velocity
        )
        risk_score = self._calculate_risk_score(
            progress_percent, len(overdue_tasks), blocked_tasks, velocity
        )

        # Calculate projected completion date
        projected_completion = self._calculate_projected_completion(
            completed_tasks, total_tasks, velocity
        )

        # Update current state
        self.current_state = ProjectState(
            board_id=self.kanban_client.board_id or "unknown",
            project_name=summary.get("name", "Unknown Project"),
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            in_progress_tasks=in_progress_tasks,
            blocked_tasks=blocked_tasks,
            progress_percent=progress_percent,
            overdue_tasks=overdue_tasks,
            team_velocity=velocity,
            velocity_trend=velocity_trend,
            risk_level=risk_level,
            risk_score=risk_score,
            projected_completion_date=projected_completion,
            last_updated=datetime.now(),
        )

    async def _get_all_tasks(self) -> List[Task]:
        """Get all tasks from all kanban board columns.

        Retrieves tasks from all standard kanban columns (TODO, IN PROGRESS,
        BLOCKED, DONE) and converts them to Task objects for analysis.

        Returns
        -------
        List[Task]
            List of all tasks across all board columns, with each task
            containing status, timing, and metadata information

        Raises
        ------
        Exception
            If there are errors retrieving tasks from the kanban board
            or converting card data to Task objects

        Notes
        -----
        This method directly interfaces with the MCP Kanban system using
        the mcp_kanban_card_manager tool to retrieve card data from each
        column, then converts the cards to standardized Task objects.
        """
        all_tasks = []

        columns = ["TODO", "IN PROGRESS", "BLOCKED", "DONE"]
        for column in columns:
            cards = await self.kanban_client._call_tool(
                "mcp_kanban_card_manager",
                {
                    "action": "get_all",
                    "boardId": self.kanban_client.board_id,
                    "columnName": column,
                },
            )

            for card in cards:
                task = self.kanban_client._card_to_task(card)
                all_tasks.append(task)

        return all_tasks

    async def _calculate_velocity(self, tasks: List[Task]) -> float:
        """Calculate team velocity as tasks completed per week.

        Analyzes the provided tasks to determine how many were completed
        in the last 7 days, providing a measure of team productivity.

        Parameters
        ----------
        tasks : List[Task]
            List of all project tasks to analyze for velocity calculation

        Returns
        -------
        float
            Number of tasks completed in the last week, representing
            the team's current velocity

        Examples
        --------
        >>> tasks = await monitor._get_all_tasks()
        >>> velocity = await monitor._calculate_velocity(tasks)
        >>> print(f"Team velocity: {velocity} tasks/week")

        Notes
        -----
        Velocity is calculated by counting tasks with status DONE that have
        an updated_at timestamp within the last 7 days. This provides a
        rolling window of team productivity that can be used for planning
        and capacity assessment.
        """
        one_week_ago = datetime.now() - timedelta(days=7)

        completed_this_week = [
            t
            for t in tasks
            if t.status == TaskStatus.DONE and t.updated_at > one_week_ago
        ]

        return len(completed_this_week)

    def _assess_risk_level(
        self, progress: float, overdue_count: int, blocked_count: int, velocity: float
    ) -> RiskLevel:
        """Assess overall project risk level based on key metrics.

        Evaluates multiple project health indicators to determine the
        overall risk level using a scoring system that considers progress,
        overdue tasks, blocked tasks, and team velocity.

        Parameters
        ----------
        progress : float
            Project progress as a percentage (0-100)
        overdue_count : int
            Number of tasks that are past their due date
        blocked_count : int
            Number of tasks currently in blocked status
        velocity : float
            Team velocity (tasks completed per week)

        Returns
        -------
        RiskLevel
            Assessed risk level (LOW, MEDIUM, HIGH, or CRITICAL)

        Examples
        --------
        >>> risk = monitor._assess_risk_level(
        ...     progress=75.0,
        ...     overdue_count=2,
        ...     blocked_count=1,
        ...     velocity=8.0
        ... )
        >>> print(f"Risk Level: {risk.value}")  # e.g., "LOW"

        Risk scoring breakdown:

        >>> # High risk scenario
        >>> risk = monitor._assess_risk_level(
        ...     progress=15.0,      # Low progress: +2 points
        ...     overdue_count=8,    # Many overdue: +3 points
        ...     blocked_count=5,    # Many blocked: +2 points
        ...     velocity=1.0        # Low velocity: +2 points
        ... )  # Total: 9 points = CRITICAL

        Notes
        -----
        Risk scoring system:
        - Progress < 25%: +2 points, < 50%: +1 point
        - Overdue tasks: >5: +3, >2: +2, >0: +1 point
        - Blocked tasks: >3: +2, >0: +1 point
        - Velocity: <2: +2, <5: +1 point

        Risk levels by total score:
        - 0-1 points: LOW risk
        - 2-3 points: MEDIUM risk
        - 4-5 points: HIGH risk
        - 6+ points: CRITICAL risk
        """
        risk_score = 0

        # Progress-based risk
        if progress < 25:
            risk_score += 2
        elif progress < 50:
            risk_score += 1

        # Overdue tasks risk
        if overdue_count > 5:
            risk_score += 3
        elif overdue_count > 2:
            risk_score += 2
        elif overdue_count > 0:
            risk_score += 1

        # Blocked tasks risk
        if blocked_count > 3:
            risk_score += 2
        elif blocked_count > 0:
            risk_score += 1

        # Velocity risk
        if velocity < 2:
            risk_score += 2
        elif velocity < 5:
            risk_score += 1

        # Map score to risk level
        if risk_score >= 6:
            return RiskLevel.CRITICAL
        elif risk_score >= 4:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    async def _analyze_project_health(self) -> None:
        """Perform AI-powered project health analysis.

        Uses the AI analysis engine to perform deep analysis of project
        health, identifying potential risks and generating mitigation
        strategies based on current state and historical trends.

        The analysis considers:
        1. Current project state and metrics
        2. Recent activity patterns from historical data
        3. Team status and capacity information
        4. Trend analysis for predictive insights

        Updates the risks attribute with identified project risks including
        type classification, severity assessment, and recommended mitigation
        strategies.

        Raises
        ------
        Exception
            If there are errors communicating with the AI analysis engine
            or processing the analysis results

        Notes
        -----
        This method requires a valid current_state to perform analysis.
        If no current state exists, the analysis is skipped. The AI engine
        analyzes up to the last 10 historical data points for trend analysis.
        """
        if not self.current_state:
            return

        # Get recent activities from historical data
        recent_activities = self.historical_data[-10:] if self.historical_data else []

        # Get team status (simplified for now)
        team_status = []  # Would be populated from agent status tracking

        # Get AI analysis
        analysis = await self.ai_engine.analyze_project_health(
            self.current_state, recent_activities, team_status
        )

        # Extract risks from analysis
        self.risks = []
        for risk_data in analysis.get("risk_factors", []):
            risk = ProjectRisk(
                risk_type=risk_data["type"],
                description=risk_data["description"],
                severity=self._map_severity(risk_data["severity"]),
                probability=0.5,  # Default probability
                impact=risk_data.get("impact", "Medium"),
                mitigation_strategy=risk_data.get("mitigation", "Monitor closely"),
                identified_at=datetime.now(),
            )
            self.risks.append(risk)

    async def _check_for_issues(self) -> None:
        """Check for various project issues and potential problems.

        Performs automated detection of common project issues including
        stalled tasks, capacity problems, and dependency bottlenecks.
        Identified issues are added to the risks list for tracking.

        Issue detection includes:
        1. Stalled tasks that haven't progressed within threshold time
        2. Capacity issues from too many concurrent in-progress tasks
        3. Dependency bottlenecks where blocked tasks affect multiple others

        Raises
        ------
        Exception
            If there are errors retrieving task data or analyzing issues

        Notes
        -----
        This method requires a valid current_state to perform issue detection.
        Detection thresholds can be configured via settings (e.g.,
        stall_threshold_hours for identifying stalled tasks).
        """
        if not self.current_state:
            return

        # Check for stalled tasks
        await self._check_stalled_tasks()

        # Check for capacity issues
        await self._check_capacity_issues()

        # Check for dependency bottlenecks
        await self._check_dependency_bottlenecks()

    async def _check_stalled_tasks(self) -> None:
        """Identify tasks that haven't progressed within threshold time.

        Analyzes in-progress tasks to find those that haven't been updated
        recently, indicating potential stalls or blockers. Creates risk
        entries for tasks that exceed the stall threshold.

        The stall threshold is configurable via the 'stall_threshold_hours'
        setting (default: 24 hours). Tasks in progress longer than this
        threshold without updates are flagged as stalled.

        Raises
        ------
        Exception
            If there are errors retrieving task data or calculating time
            differences

        Notes
        -----
        Stalled tasks are added to the risks list with type 'stalled_task'
        and MEDIUM severity. The risk description includes the task name
        and duration since last update.
        """
        tasks = await self._get_all_tasks()

        stall_threshold = timedelta(
            hours=self.settings.get("stall_threshold_hours", 24)
        )
        now = datetime.now()

        for task in tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                if now - task.updated_at > stall_threshold:
                    # Task is stalled, create a risk
                    risk = ProjectRisk(
                        risk_type="stalled_task",
                        description=f"Task '{task.name}' has been in progress for over {stall_threshold.total_seconds()/3600} hours",
                        severity=RiskLevel.MEDIUM,
                        probability=1.0,
                        impact="Delays project timeline",
                        mitigation_strategy="Check in with assigned agent",
                        identified_at=now,
                    )
                    self.risks.append(risk)

    async def _check_capacity_issues(self) -> None:
        """Check if team capacity is being exceeded.

        Analyzes the current workload distribution to identify potential
        capacity issues where too many tasks are in progress simultaneously,
        which can lead to reduced productivity and quality issues.

        Creates a HIGH severity risk if more than 10 tasks (configurable
        threshold) are in progress concurrently, suggesting potential team
        overload and recommending task prioritization.

        Raises
        ------
        Exception
            If there are errors retrieving or analyzing task data

        Notes
        -----
        The capacity threshold (currently 10 concurrent tasks) should be
        made configurable in future versions. This check provides early
        warning of team overload before it impacts project delivery.
        """
        # This would integrate with agent status tracking
        # For now, we'll check task distribution

        tasks = await self._get_all_tasks()
        in_progress = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]

        if len(in_progress) > 10:  # Configurable threshold
            risk = ProjectRisk(
                risk_type="capacity",
                description="Too many tasks in progress simultaneously",
                severity=RiskLevel.HIGH,
                probability=0.8,
                impact="Team burnout and quality issues",
                mitigation_strategy="Prioritize and defer lower priority tasks",
                identified_at=datetime.now(),
            )
            self.risks.append(risk)

    async def _check_dependency_bottlenecks(self) -> None:
        """Identify dependency chains causing project bottlenecks.

        Analyzes blocked tasks to find those that are preventing multiple
        other tasks from proceeding, creating dependency bottlenecks that
        can significantly impact project timelines.

        For each blocked task, checks how many dependent tasks are waiting.
        If a blocked task has more than 2 dependents, it's flagged as a
        HIGH severity risk requiring immediate attention.

        Raises
        ------
        Exception
            If there are errors retrieving task dependency information
            or analyzing dependency chains

        Notes
        -----
        This method relies on the kanban client's get_dependent_tasks()
        method to identify task dependencies. Dependency bottlenecks are
        critical as they can cascade delays across multiple work streams.
        """
        tasks = await self._get_all_tasks()

        # Find blocked tasks with many dependents
        for task in tasks:
            if task.status == TaskStatus.BLOCKED:
                dependents = await self.kanban_client.get_dependent_tasks(task.id)
                if len(dependents) > 2:
                    risk = ProjectRisk(
                        risk_type="dependency",
                        description=f"Task '{task.name}' is blocking {len(dependents)} other tasks",
                        severity=RiskLevel.HIGH,
                        probability=1.0,
                        impact="Multiple tasks cannot proceed",
                        mitigation_strategy="Prioritize unblocking this task",
                        identified_at=datetime.now(),
                    )
                    self.risks.append(risk)

    def _record_metrics(self) -> None:
        """Record current metrics for historical tracking and trend analysis.

        Captures a snapshot of current project metrics and adds it to the
        historical data for trend analysis and reporting. Maintains a
        rolling window of the last 100 metric snapshots.

        Recorded metrics include:
        - Timestamp of measurement
        - Project progress percentage
        - Team velocity (tasks/week)
        - Number of blocked tasks
        - Overall risk level
        - Total and completed task counts

        The historical data enables trend analysis, velocity tracking,
        and identification of patterns in project health over time.

        Notes
        -----
        Historical data is stored in memory and limited to the last 100
        entries to prevent excessive memory usage. For persistent storage,
        consider extending this method to write to a database or file.
        """
        if self.current_state:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "progress": self.current_state.progress_percent,
                "velocity": self.current_state.team_velocity,
                "blocked_tasks": self.current_state.blocked_tasks,
                "risk_level": self.current_state.risk_level.value,
                "total_tasks": self.current_state.total_tasks,
                "completed_tasks": self.current_state.completed_tasks,
            }

            self.historical_data.append(metrics)

            # Keep only last 100 entries
            if len(self.historical_data) > 100:
                self.historical_data = self.historical_data[-100:]

    async def record_blocker(
        self, agent_id: str, task_id: str, description: str
    ) -> BlockerReport:
        """Record a new blocker report from an agent.

        Creates a new blocker report when an agent encounters an issue
        that prevents task progress. The blocker is tracked for resolution
        and included in project health assessments.

        Parameters
        ----------
        agent_id : str
            Unique identifier of the agent reporting the blocker
        task_id : str
            Unique identifier of the blocked task
        description : str
            Detailed description of the blocking issue

        Returns
        -------
        BlockerReport
            Created blocker report containing:
            - task_id: ID of the blocked task
            - reporter_id: ID of the reporting agent
            - description: Description of the blocking issue
            - severity: Risk level of the blocker (default: MEDIUM)
            - reported_at: Timestamp when blocker was reported
            - resolved: Resolution status (default: False)

        Examples
        --------
        >>> blocker = await monitor.record_blocker(
        ...     agent_id="agent-backend-001",
        ...     task_id="task-user-auth-123",
        ...     description="Database connection timeout after 30 seconds"
        ... )
        >>> print(f"Blocker recorded: {blocker.task_id}")

        Record multiple related blockers:

        >>> blockers = []
        >>> for task_id in failing_tasks:
        ...     blocker = await monitor.record_blocker(
        ...         agent_id="agent-001",
        ...         task_id=task_id,
        ...         description="External API rate limit exceeded"
        ...     )
        ...     blockers.append(blocker)

        Notes
        -----
        Blockers are automatically assigned MEDIUM severity. For more precise
        severity assessment, consider extending this method to accept severity
        as a parameter or implement automatic severity classification based
        on the description content.
        """
        blocker = BlockerReport(
            task_id=task_id,
            reporter_id=agent_id,
            description=description,
            severity=RiskLevel.MEDIUM,
            reported_at=datetime.now(),
        )

        self.blockers.append(blocker)
        return blocker

    def _map_severity(self, severity_str: str) -> RiskLevel:
        """Map string severity to RiskLevel enum.

        Converts string-based severity levels from external sources
        (like AI analysis results) to the standardized RiskLevel enum.

        Parameters
        ----------
        severity_str : str
            String representation of severity level (case-insensitive).
            Valid values: "low", "medium", "high", "critical"

        Returns
        -------
        RiskLevel
            Corresponding RiskLevel enum value. Returns MEDIUM for
            unrecognized severity strings as a safe default.

        Examples
        --------
        >>> risk_level = monitor._map_severity("high")
        >>> print(risk_level)  # RiskLevel.HIGH

        >>> risk_level = monitor._map_severity("CRITICAL")
        >>> print(risk_level)  # RiskLevel.CRITICAL

        >>> risk_level = monitor._map_severity("unknown")
        >>> print(risk_level)  # RiskLevel.MEDIUM (default)
        """
        mapping = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }
        return mapping.get(severity_str.lower(), RiskLevel.MEDIUM)

    def get_current_risks(self) -> List[ProjectRisk]:
        """Get current project risks identified by monitoring and analysis.

        Returns the list of all currently identified project risks,
        including those from AI analysis, automated issue detection,
        and manual risk assessments.

        Returns
        -------
        List[ProjectRisk]
            List of current project risks, each containing:
            - risk_type: Category of risk (e.g., 'stalled_task', 'capacity')
            - description: Detailed description of the risk
            - severity: Risk severity level (LOW, MEDIUM, HIGH, CRITICAL)
            - probability: Likelihood of risk occurrence (0.0-1.0)
            - impact: Description of potential impact
            - mitigation_strategy: Recommended mitigation approach
            - identified_at: Timestamp when risk was identified

        Examples
        --------
        >>> risks = monitor.get_current_risks()
        >>> print(f"Total risks: {len(risks)}")
        >>>
        >>> # Filter by severity
        >>> critical_risks = [
        ...     risk for risk in risks
        ...     if risk.severity == RiskLevel.CRITICAL
        ... ]
        >>>
        >>> # Display risk summary
        >>> for risk in risks:
        ...     print(f"{risk.risk_type}: {risk.description}")
        ...     print(f"  Severity: {risk.severity.value}")
        ...     print(f"  Mitigation: {risk.mitigation_strategy}")
        """
        return self.risks

    def get_active_blockers(self) -> List[BlockerReport]:
        """Get active (unresolved) blocker reports.

        Returns all blocker reports that have not yet been resolved,
        providing visibility into current impediments affecting project
        progress.

        Returns
        -------
        List[BlockerReport]
            List of unresolved blocker reports, each containing:
            - task_id: ID of the blocked task
            - reporter_id: ID of the agent that reported the blocker
            - description: Description of the blocking issue
            - severity: Severity level of the blocker
            - reported_at: When the blocker was first reported
            - resolved: Resolution status (False for active blockers)

        Examples
        --------
        >>> blockers = monitor.get_active_blockers()
        >>> print(f"Active blockers: {len(blockers)}")
        >>>
        >>> # Group by task
        >>> from collections import defaultdict
        >>> by_task = defaultdict(list)
        >>> for blocker in blockers:
        ...     by_task[blocker.task_id].append(blocker)
        >>>
        >>> # Display blocker summary
        >>> for blocker in blockers:
        ...     print(f"Task {blocker.task_id}: {blocker.description}")
        ...     print(f"  Reported by: {blocker.reporter_id}")
        ...     print(f"  Severity: {blocker.severity.value}")
        ...     print(f"  Age: {datetime.now() - blocker.reported_at}")

        Notes
        -----
        Active blockers represent ongoing impediments that require attention.
        Regular review of active blockers helps identify patterns and
        prioritize resolution efforts.
        """
        return [b for b in self.blockers if not b.resolved]

    def _calculate_velocity_trend(self, current_velocity: float) -> str:
        """Calculate velocity trend based on historical data.

        Parameters
        ----------
        current_velocity : float
            Current team velocity in tasks per week

        Returns
        -------
        str
            Velocity trend: "increasing", "stable", or "decreasing"
        """
        if len(self.historical_data) < 3:
            return "stable"

        # Get last 3 velocity measurements
        recent_velocities = [
            data.get("velocity", 0) for data in self.historical_data[-3:]
        ]

        if not recent_velocities:
            return "stable"

        avg_recent = sum(recent_velocities) / len(recent_velocities)

        # Determine trend
        if current_velocity > avg_recent * 1.1:
            return "increasing"
        elif current_velocity < avg_recent * 0.9:
            return "decreasing"
        else:
            return "stable"

    def _calculate_risk_score(
        self, progress: float, overdue_count: int, blocked_count: int, velocity: float
    ) -> float:
        """Calculate numeric risk score (0-1).

        Parameters
        ----------
        progress : float
            Project progress percentage
        overdue_count : int
            Number of overdue tasks
        blocked_count : int
            Number of blocked tasks
        velocity : float
            Team velocity

        Returns
        -------
        float
            Risk score between 0 (low risk) and 1 (high risk)
        """
        risk_score = 0.0

        # Progress-based risk (0-0.3)
        if progress < 25:
            risk_score += 0.3
        elif progress < 50:
            risk_score += 0.15

        # Overdue tasks risk (0-0.3)
        if overdue_count > 5:
            risk_score += 0.3
        elif overdue_count > 2:
            risk_score += 0.2
        elif overdue_count > 0:
            risk_score += 0.1

        # Blocked tasks risk (0-0.2)
        if blocked_count > 3:
            risk_score += 0.2
        elif blocked_count > 0:
            risk_score += 0.1

        # Velocity risk (0-0.2)
        if velocity < 2:
            risk_score += 0.2
        elif velocity < 5:
            risk_score += 0.1

        return min(risk_score, 1.0)

    def _calculate_projected_completion(
        self, completed_tasks: int, total_tasks: int, velocity: float
    ) -> Optional[datetime]:
        """Calculate projected completion date based on velocity.

        Parameters
        ----------
        completed_tasks : int
            Number of completed tasks
        total_tasks : int
            Total number of tasks
        velocity : float
            Tasks completed per week

        Returns
        -------
        Optional[datetime]
            Projected completion date, or None if cannot be calculated
        """
        if velocity <= 0 or total_tasks <= completed_tasks:
            return None

        remaining_tasks = total_tasks - completed_tasks
        weeks_to_complete = remaining_tasks / velocity

        return datetime.now() + timedelta(weeks=weeks_to_complete)

    async def _check_for_project_completion(self) -> None:
        """Check if project has reached completion criteria.

        Triggers pattern learning and quality assessment when:
        - Progress >= 95%
        - No tasks in progress
        - Less than 5% of tasks are blocked
        """
        if not self.current_state:
            return

        # Check completion criteria
        completion_threshold = self.settings.get(
            "pattern_learning.completion_threshold", 95
        )

        if (
            self.current_state.progress_percent >= completion_threshold
            and self.current_state.in_progress_tasks == 0
            and (
                self.current_state.blocked_tasks / self.current_state.total_tasks < 0.05
                if self.current_state.total_tasks > 0
                else True
            )
        ):
            # Check if we've already processed this completion
            if hasattr(self, "_last_completion_check"):
                if (datetime.now() - self._last_completion_check).days < 1:
                    return

            self._last_completion_check = datetime.now()

            # Trigger completion learning
            await self._handle_project_completion()

    async def _handle_project_completion(self) -> None:
        """Handle project completion by triggering learning and assessment."""
        print(f"🎉 Project '{self.current_state.project_name}' appears to be complete!")
        print(f"   Progress: {self.current_state.progress_percent:.1f}%")
        print(
            f"   Completed Tasks: {self.current_state.completed_tasks}/{self.current_state.total_tasks}"
        )

        # Get configuration
        config = self.settings.get("quality_assessment", {})
        github_owner = config.get("github_owner")
        github_repo = config.get("github_repo")

        # Create project outcome based on current state
        project_duration = self._calculate_project_duration()

        # Run quality assessment first to determine success
        all_tasks = await self._get_all_tasks()

        # Get team members (would need to be tracked or passed in)
        team_members = []  # This would come from agent tracking

        github_config = (
            {
                "github_owner": github_owner,
                "github_repo": github_repo,
                "project_start_date": config.get("project_start_date", ""),
            }
            if github_owner and github_repo
            else None
        )

        # Pass GitHub MCP interface if available
        if hasattr(self.kanban_client, "mcp_caller") and github_config:
            github_interface = GitHubMCPInterface(self.kanban_client.mcp_caller)
            self.quality_assessor.github_mcp = github_interface

        assessment = await self.quality_assessor.assess_project_quality(
            project_state=self.current_state,
            tasks=all_tasks,
            team_members=team_members,
            github_config=github_config,
        )

        # Create outcome based on assessment
        outcome = ProjectOutcome(
            successful=assessment.is_successful,
            completion_time_days=project_duration,
            quality_score=assessment.overall_score,
            cost=self._estimate_project_cost(project_duration, len(team_members)),
            failure_reasons=(
                [] if assessment.is_successful else assessment.improvement_areas[:3]
            ),
        )

        # Run pattern learning
        pattern = await self.pattern_learner.learn_from_project(
            project_state=self.current_state,
            tasks=all_tasks,
            team_members=team_members,
            outcome=outcome,
            github_owner=github_owner,
            github_repo=github_repo,
        )

        # Log results
        print(f"\n📊 Quality Assessment Complete:")
        print(f"   Overall Score: {assessment.overall_score:.1%}")
        print(f"   Success: {'✅ Yes' if assessment.is_successful else '❌ No'}")
        print(f"   Confidence: {assessment.success_confidence:.1%}")
        print(f"\n📈 Key Insights:")
        for insight in assessment.quality_insights[:3]:
            print(f"   • {insight}")
        print(f"\n🎯 Improvement Areas:")
        for area in assessment.improvement_areas[:3]:
            print(f"   • {area}")
        print(f"\n🧠 Pattern Learning Complete:")
        print(f"   Confidence Score: {pattern.confidence_score:.1%}")
        print(f"   Patterns in Database: {len(self.pattern_learner.learned_patterns)}")

    def _calculate_project_duration(self) -> int:
        """Calculate project duration in days from historical data."""
        if not self.historical_data:
            return 30  # Default estimate

        # Find first entry
        first_entry = self.historical_data[0]
        first_date = datetime.fromisoformat(first_entry["timestamp"])

        return (datetime.now() - first_date).days

    def _estimate_project_cost(self, duration_days: int, team_size: int) -> float:
        """Estimate project cost based on duration and team size."""
        # Simple cost model: $1000/day per team member
        daily_rate = self.settings.get("cost_estimation.daily_rate", 1000)
        return (
            duration_days * team_size * daily_rate
            if team_size > 0
            else duration_days * daily_rate * 3
        )

    async def trigger_project_completion_learning(
        self,
        team_members: List[Any],
        outcome: ProjectOutcome,
        github_owner: Optional[str] = None,
        github_repo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Trigger pattern learning and quality assessment when a project completes.

        This method should be called when a project reaches completion to:
        1. Extract patterns from the completed project
        2. Run comprehensive quality assessment
        3. Store insights for future projects

        Parameters
        ----------
        team_members : List[Any]
            List of team members who worked on the project
        outcome : ProjectOutcome
            The actual outcome of the project
        github_owner : Optional[str]
            GitHub repository owner for code analysis
        github_repo : Optional[str]
            GitHub repository name for code analysis

        Returns
        -------
        Dict[str, Any]
            Results containing pattern extraction and quality assessment

        Examples
        --------
        >>> outcome = ProjectOutcome(
        ...     successful=True,
        ...     completion_time_days=35,
        ...     quality_score=0.85,
        ...     cost=50000
        ... )
        >>> results = await monitor.trigger_project_completion_learning(
        ...     team_members, outcome, "owner", "repo"
        ... )
        >>> print(f"Quality Grade: {results['quality_assessment']['grade']}")

        Notes
        -----
        This method integrates pattern learning with quality assessment to
        provide comprehensive insights that help improve future projects.
        """
        if not self.current_state:
            await self._collect_project_data()

        # Get all tasks for analysis
        all_tasks = await self._get_all_tasks()

        # Run pattern learning
        pattern = await self.pattern_learner.learn_from_project(
            project_state=self.current_state,
            tasks=all_tasks,
            team_members=team_members,
            outcome=outcome,
            github_owner=github_owner,
            github_repo=github_repo,
        )

        # Run quality assessment
        github_config = (
            {
                "github_owner": github_owner,
                "github_repo": github_repo,
                "project_start_date": self.settings.get(
                    "quality_assessment.project_start_date", ""
                ),
            }
            if github_owner and github_repo
            else None
        )

        assessment = await self.quality_assessor.assess_project_quality(
            project_state=self.current_state,
            tasks=all_tasks,
            team_members=team_members,
            github_config=github_config,
        )

        # Log completion event with insights
        print(f"✅ Project '{self.current_state.project_name}' completed:")
        print(f"   - Quality Score: {assessment.overall_score:.1%}")
        print(f"   - Pattern Confidence: {pattern.confidence_score:.1%}")
        print(f"   - Key Success Factors: {', '.join(pattern.success_factors[:3])}")

        return {
            "pattern_learning": {
                "success": True,
                "confidence_score": pattern.confidence_score,
                "success_factors": pattern.success_factors,
                "risk_factors": pattern.risk_factors,
                "patterns_learned": len(self.pattern_learner.learned_patterns),
            },
            "quality_assessment": {
                "score": assessment.overall_score,
                "is_successful": assessment.is_successful,
                "insights": assessment.quality_insights,
                "improvements": assessment.improvement_areas,
                "code_quality_score": assessment.code_quality_score,
                "process_quality_score": assessment.process_quality_score,
                "delivery_quality_score": assessment.delivery_quality_score,
                "team_quality_score": assessment.team_quality_score,
            },
        }

    async def get_pattern_based_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get recommendations based on learned patterns for the current project.

        Returns
        -------
        List[Dict[str, Any]]
            List of recommendations with type, message, confidence, and impact

        Examples
        --------
        >>> recommendations = await monitor.get_pattern_based_recommendations()
        >>> for rec in recommendations:
        ...     print(f"{rec['message']} (confidence: {rec['confidence']:.0%})")
        """
        if not self.current_state:
            await self._collect_project_data()

        # Build project context
        all_tasks = await self._get_all_tasks()

        project_context = {
            "total_tasks": self.current_state.total_tasks,
            "progress": self.current_state.progress_percent,
            "velocity": self.current_state.team_velocity,
            "risk_level": self.current_state.risk_level.value,
            "team_size": 3,  # Would need to track actual team size
            "blocked_tasks": self.current_state.blocked_tasks,
        }

        # Get recommendations from recommendation engine
        recommendations = self.recommendation_engine.get_pattern_based_recommendations(
            project_context
        )

        # Convert to dict format
        rec_dicts = []
        for rec in recommendations:
            rec_dict = {
                "type": rec.type,
                "message": rec.message,
                "confidence": rec.confidence,
                "impact": rec.impact,
            }
            if rec.supporting_data:
                rec_dict["supporting_data"] = rec.supporting_data
            rec_dicts.append(rec_dict)

        return rec_dicts
