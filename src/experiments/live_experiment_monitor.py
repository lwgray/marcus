"""
Live Experiment Monitor for Real Marcus Experiments.

This module provides real-time experiment tracking for actual Marcus
operations, monitoring real agents working on real boards and logging
all metrics to MLflow.

Usage
-----
Use the MCP tools to control experiments:
- start_experiment: Begin tracking a real experiment
- end_experiment: Stop tracking and finalize results
- get_experiment_status: Check current experiment status

Example via MCP
---------------
# Start an experiment
start_experiment(
    experiment_name="production-test",
    board_id="abc123",
    project_id="xyz789"
)

# Agents work on real tasks...
# Monitor automatically tracks everything

# End the experiment
end_experiment()
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.experiments import MarcusExperiment

logger = logging.getLogger(__name__)


class LiveExperimentMonitor:
    """
    Monitor and track real Marcus experiments in real-time.

    This class runs in the background during actual Marcus operations,
    tracking agent registrations, task assignments, completions, and
    all other activities, logging everything to MLflow.

    Parameters
    ----------
    experiment_name : str
        Name for the MLflow experiment
    board_id : str
        Board ID to monitor
    project_id : str
        Project ID to monitor
    tracking_interval : int
        How often to log metrics (seconds), default 30
    """

    def __init__(
        self,
        experiment_name: str,
        board_id: str,
        project_id: str,
        tracking_interval: int = 30,
    ):
        """Initialize live experiment monitor."""
        self.experiment_name = experiment_name
        self.board_id = board_id
        self.project_id = project_id
        self.tracking_interval = tracking_interval

        # MLflow experiment
        self.mlflow_experiment = MarcusExperiment(
            experiment_name=experiment_name, tracking_uri="./mlruns"
        )

        # Monitoring state
        self.is_running = False
        self.monitor_task: Optional[asyncio.Task[None]] = None
        self.run_name: Optional[str] = None

        # Tracked metrics
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.task_assignments: Dict[str, str] = {}  # task_id -> agent_id
        self.task_completions: Dict[str, float] = {}  # task_id -> completion_time
        self.blockers_reported = 0
        self.artifacts_created = 0
        self.decisions_logged = 0
        self.context_requests = 0

        logger.info(
            f"Initialized LiveExperimentMonitor for {experiment_name} "
            f"(board: {board_id})"
        )

    async def start(
        self,
        run_name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Start the live experiment monitoring.

        Parameters
        ----------
        run_name : str, optional
            Name for this run (auto-generated if not provided)
        params : Dict[str, Any], optional
            Experiment parameters to log
        tags : Dict[str, str], optional
            Tags to add to the run

        Returns
        -------
        Dict[str, Any]
            Status information including run_id
        """
        if self.is_running:
            return {
                "success": False,
                "error": "Experiment already running",
                "run_id": self.run_name,
            }

        # Generate run name if not provided
        if run_name is None:
            run_name = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.run_name = run_name

        # Prepare default parameters
        if params is None:
            params = {}

        params.update(
            {
                "board_id": self.board_id,
                "project_id": self.project_id,
                "tracking_interval": self.tracking_interval,
                "experiment_type": "live_monitoring",
            }
        )

        # Start MLflow run
        self.mlflow_experiment.start_run(run_name=run_name, params=params, tags=tags)

        # Start background monitoring
        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())

        logger.info(f"Started live experiment: {run_name}")

        return {
            "success": True,
            "run_name": run_name,
            "experiment_name": self.experiment_name,
            "board_id": self.board_id,
            "message": "Live experiment monitoring started",
        }

    async def stop(self) -> Dict[str, Any]:
        """
        Stop the live experiment monitoring.

        Returns
        -------
        Dict[str, Any]
            Final statistics and status
        """
        if not self.is_running:
            return {"success": False, "error": "No experiment currently running"}

        self.is_running = False

        # Cancel monitoring task
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        # Log final metrics
        final_metrics: Dict[str, float] = {
            "total_registered_agents": float(len(self.registered_agents)),
            "total_task_assignments": float(len(self.task_assignments)),
            "total_task_completions": float(len(self.task_completions)),
            "total_blockers": float(self.blockers_reported),
            "total_artifacts": float(self.artifacts_created),
            "total_decisions": float(self.decisions_logged),
            "total_context_requests": float(self.context_requests),
        }

        # Generate summary
        summary = self._generate_summary()

        # End MLflow run
        self.mlflow_experiment.end_run(final_metrics=final_metrics, summary=summary)

        logger.info(f"Stopped live experiment: {self.run_name}")

        return {
            "success": True,
            "run_name": self.run_name,
            "final_metrics": final_metrics,
            "summary": summary,
        }

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        step = 0

        try:
            from src.monitoring.project_monitor import ProjectMonitor

            # Initialize monitoring
            monitor = ProjectMonitor()

            while self.is_running:
                await asyncio.sleep(self.tracking_interval)

                try:
                    # Get current project state
                    state = await monitor.get_project_state()

                    # Log to MLflow
                    self.mlflow_experiment.log_project_state(
                        total_tasks=state.total_tasks,
                        completed_tasks=state.completed_tasks,
                        in_progress_tasks=state.in_progress_tasks,
                        blocked_tasks=state.blocked_tasks,
                        progress_percent=state.progress_percent,
                        velocity=state.team_velocity,
                        step=step,
                    )

                    # Log agent count
                    self.mlflow_experiment.log_metric(
                        "active_agents", len(self.registered_agents), step=step
                    )

                    step += 1

                    logger.debug(
                        f"Logged metrics at step {step}: "
                        f"velocity={state.team_velocity:.2f}, "
                        f"agents={len(self.registered_agents)}"
                    )

                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize monitoring: {e}")

    def record_agent_registration(
        self,
        agent_id: str,
        name: str,
        role: str,
        skills: List[str],
    ) -> None:
        """
        Record an agent registration.

        Parameters
        ----------
        agent_id : str
            Unique agent identifier
        name : str
            Agent name
        role : str
            Agent role
        skills : list
            Agent skills
        """
        self.registered_agents[agent_id] = {
            "name": name,
            "role": role,
            "skills": skills,
            "registered_at": datetime.now().isoformat(),
            "tasks_completed": 0,
        }

        # Log to MLflow
        self.mlflow_experiment.log_param(f"agent_{agent_id}_skills", ",".join(skills))

        logger.info(f"Recorded agent registration: {agent_id} ({name})")

    def record_task_assignment(
        self,
        task_id: str,
        agent_id: str,
    ) -> None:
        """Record a task assignment."""
        self.task_assignments[task_id] = agent_id
        logger.debug(f"Recorded task assignment: {task_id} -> {agent_id}")

    def record_task_completion(
        self,
        task_id: str,
        agent_id: str,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Record a task completion."""
        completion_time = datetime.now().timestamp()
        self.task_completions[task_id] = completion_time

        # Update agent stats
        if agent_id in self.registered_agents:
            self.registered_agents[agent_id]["tasks_completed"] += 1

        # Log to MLflow
        if duration_seconds:
            self.mlflow_experiment.log_task_completion(
                task_id=task_id, duration_seconds=duration_seconds, agent_id=agent_id
            )

        logger.info(f"Recorded task completion: {task_id} by {agent_id}")

    def record_blocker(
        self,
        agent_id: str,
        task_id: str,
        description: str,
        severity: str = "medium",
    ) -> None:
        """Record a blocker."""
        self.blockers_reported += 1

        self.mlflow_experiment.log_blocker(
            agent_id=agent_id,
            task_id=task_id,
            blocker_description=description,
            severity=severity,
        )

        logger.info(f"Recorded blocker: {agent_id} on {task_id}")

    def record_artifact(
        self,
        task_id: str,
        artifact_type: str,
        filename: str,
        description: str = "",
    ) -> None:
        """Record an artifact creation."""
        self.artifacts_created += 1

        self.mlflow_experiment.log_artifact_event(
            task_id=task_id,
            artifact_type=artifact_type,
            filename=filename,
            description=description,
        )

        logger.info(f"Recorded artifact: {filename} ({artifact_type})")

    def record_decision(
        self,
        agent_id: str,
        task_id: str,
        decision: str,
    ) -> None:
        """Record a decision."""
        self.decisions_logged += 1

        self.mlflow_experiment.log_decision(
            agent_id=agent_id, task_id=task_id, decision=decision
        )

        logger.info(f"Recorded decision: {agent_id} on {task_id}")

    def record_context_request(
        self,
        agent_id: str,
        task_id: str,
        context_type: str = "task_context",
    ) -> None:
        """Record a context request."""
        self.context_requests += 1

        self.mlflow_experiment.log_context_request(
            agent_id=agent_id, task_id=task_id, context_type=context_type
        )

        logger.debug(f"Recorded context request: {agent_id} for {task_id}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current experiment status.

        Returns
        -------
        Dict[str, Any]
            Current status and metrics
        """
        return {
            "is_running": self.is_running,
            "run_name": self.run_name,
            "experiment_name": self.experiment_name,
            "board_id": self.board_id,
            "registered_agents": len(self.registered_agents),
            "task_assignments": len(self.task_assignments),
            "task_completions": len(self.task_completions),
            "blockers_reported": self.blockers_reported,
            "artifacts_created": self.artifacts_created,
            "decisions_logged": self.decisions_logged,
            "context_requests": self.context_requests,
        }

    def _generate_summary(self) -> str:
        """Generate experiment summary."""
        duration = (
            (
                datetime.now()
                - datetime.fromisoformat(
                    list(self.registered_agents.values())[0]["registered_at"]
                )
            ).total_seconds()
            if self.registered_agents
            else 0
        )

        summary = f"""
Live Experiment Summary
=======================

Experiment: {self.experiment_name}
Run: {self.run_name}
Board: {self.board_id}
Duration: {duration:.0f} seconds

Agent Metrics:
- Total Registered: {len(self.registered_agents)}
- Active Agents: {len([a for a in self.registered_agents.values() if a['tasks_completed'] > 0])}

Task Metrics:
- Total Assignments: {len(self.task_assignments)}
- Total Completions: {len(self.task_completions)}
- Completion Rate: {len(self.task_completions) / max(len(self.task_assignments), 1) * 100:.1f}%

Condition Metrics:
- Blockers Reported: {self.blockers_reported}
- Artifacts Created: {self.artifacts_created}
- Decisions Logged: {self.decisions_logged}
- Context Requests: {self.context_requests}

Top Agents by Completions:
"""
        # Add top agents
        sorted_agents = sorted(
            self.registered_agents.items(),
            key=lambda x: x[1]["tasks_completed"],
            reverse=True,
        )[:5]

        for agent_id, info in sorted_agents:
            summary += (
                f"- {info['name']} ({agent_id}): {info['tasks_completed']} tasks\n"
            )

        return summary.strip()


# Global instance for MCP tools to use
_active_monitor: Optional[LiveExperimentMonitor] = None


def get_active_monitor() -> Optional[LiveExperimentMonitor]:
    """Get the currently active experiment monitor."""
    return _active_monitor


def set_active_monitor(monitor: Optional[LiveExperimentMonitor]) -> None:
    """Set the active experiment monitor."""
    global _active_monitor
    _active_monitor = monitor
