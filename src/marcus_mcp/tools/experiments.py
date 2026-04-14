"""
MCP Tools for Live Experiment Tracking.

These tools allow starting, stopping, and monitoring real Marcus experiments
with automatic MLflow tracking of all metrics.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.experiments.live_experiment_monitor import (
    LiveExperimentMonitor,
    get_active_monitor,
    set_active_monitor,
)

logger = logging.getLogger(__name__)


async def start_experiment(
    experiment_name: str,
    board_id: Optional[str] = None,
    project_id: Optional[str] = None,
    run_name: Optional[str] = None,
    tracking_interval: int = 30,
    params: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Start a live experiment with MLflow tracking.

    This tool initiates real-time monitoring of Marcus operations,
    automatically tracking all agent registrations, task assignments,
    completions, blockers, artifacts, decisions, and context requests.
    All metrics are logged to MLflow for analysis and comparison.

    Parameters
    ----------
    experiment_name : str
        Name for the MLflow experiment
    board_id : str, optional
        Board ID to monitor. If not provided, uses the currently selected
        project's board.
    project_id : str, optional
        Project ID to monitor. If not provided, uses the currently selected
        project.
    run_name : str, optional
        Name for this specific run (auto-generated if not provided)
    tracking_interval : int, optional
        How often to log metrics in seconds (default: 30)
    params : Dict[str, Any], optional
        Additional experiment parameters to log
    tags : Dict[str, str], optional
        Tags to add to the MLflow run
    state : Any, optional
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Status information including success, run_name, and experiment details

    Examples
    --------
    >>> # Use currently selected project
    >>> result = await start_experiment(
    ...     experiment_name="production-test",
    ...     params={"num_agents": 50, "complexity": "enterprise"}
    ... )

    >>> # Or specify explicit IDs
    >>> result = await start_experiment(
    ...     experiment_name="production-test",
    ...     board_id="1234567890",
    ...     project_id="0987654321",
    ...     params={"num_agents": 50, "complexity": "enterprise"}
    ... )
    >>> print(result["message"])
    'Live experiment monitoring started'

    Notes
    -----
    - Only one experiment can run at a time
    - Automatically tracks agent registrations via register_agent tool
    - Tracks task progress via report_task_progress tool
    - Tracks blockers via report_blocker tool
    - Logs velocity and project state every tracking_interval seconds
    """
    # Check if experiment already running
    existing_monitor = get_active_monitor()
    if existing_monitor and existing_monitor.is_running:
        return {
            "success": False,
            "error": "An experiment is already running",
            "current_experiment": existing_monitor.experiment_name,
            "current_run": existing_monitor.run_name,
        }

    # Get board_id and project_id from active project if not provided
    if not board_id or not project_id:
        if not state:
            return {
                "success": False,
                "error": "board_id and project_id required when state is not available",
            }

        try:
            active_project = await state.project_registry.get_active_project()
            if not active_project:
                return {
                    "success": False,
                    "error": (
                        "No active project selected. Use select_project "
                        "first or provide board_id and project_id."
                    ),
                }

            # Get board_id and project_id from active project
            if not project_id:
                project_id = active_project.provider_config.get("project_id")
            if not board_id:
                board_id = active_project.provider_config.get("board_id")

            if not board_id or not project_id:
                return {
                    "success": False,
                    "error": (
                        "Active project missing board_id or project_id "
                        f"in config: {active_project.provider_config}"
                    ),
                }

            logger.info(
                f"Using active project: {active_project.name} "
                f"(project_id={project_id}, board_id={board_id})"
            )

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get active project: {str(e)}",
            }

    try:
        # Create new monitor with kanban client for
        # deterministic completion detection
        kanban = (
            state.kanban_client if state and hasattr(state, "kanban_client") else None
        )
        monitor = LiveExperimentMonitor(
            experiment_name=experiment_name,
            board_id=board_id,
            project_id=project_id,
            tracking_interval=tracking_interval,
            kanban_client=kanban,
        )

        # Store run directory on monitor so end_experiment can
        # write experiment_complete.json to the right place
        if state and hasattr(state, "kanban_client") and state.kanban_client:
            ws = None
            if hasattr(state.kanban_client, "_load_workspace_state"):
                ws = state.kanban_client._load_workspace_state()
            if ws and ws.get("project_root"):
                monitor.run_dir = Path(ws["project_root"]).parent
                logger.info(f"Monitor run_dir set to {monitor.run_dir}")

        # Start monitoring
        result = await monitor.start(run_name=run_name, params=params, tags=tags)

        if result["success"]:
            # Set as active monitor
            set_active_monitor(monitor)
            logger.info(
                f"Started live experiment: {experiment_name} "
                f"(run: {result['run_name']})"
            )

        return result

    except Exception as e:
        logger.error(f"Failed to start experiment: {e}")
        return {"success": False, "error": str(e)}


async def end_experiment() -> Dict[str, Any]:
    """
    Stop the currently running experiment.

    Stops the live monitoring, logs final metrics to MLflow,
    and generates a summary report.

    Returns
    -------
    Dict[str, Any]
        Final statistics and summary including:
        - total_registered_agents
        - total_task_completions
        - total_blockers
        - total_artifacts
        - total_decisions
        - summary text

    Examples
    --------
    >>> result = await end_experiment()
    >>> print(result["final_metrics"]["total_registered_agents"])
    50

    Notes
    -----
    - Automatically called when Marcus server shuts down
    - Generates a detailed summary of the experiment
    - All data is saved to MLflow for later analysis
    """
    monitor = get_active_monitor()

    if monitor is None:
        return {"success": False, "error": "No experiment is currently running"}

    try:
        # Grab run_dir before clearing the monitor
        run_dir = getattr(monitor, "run_dir", None)

        result = await monitor.stop()

        # Clear active monitor
        set_active_monitor(None)

        logger.info(f"Stopped experiment: {result['run_name']}")

        # Write experiment_complete.json so Posidonius auto-advance
        # can detect that this run is finished.
        if run_dir:
            _write_completion_signal(result, run_dir)

        return result

    except Exception as e:
        logger.error(f"Failed to stop experiment: {e}")
        return {"success": False, "error": str(e)}


def _write_completion_signal(result: Dict[str, Any], run_dir: Path) -> None:
    """Write experiment_complete.json to the run directory.

    Posidonius polls for this file to detect when a run is done
    and can advance to the next run. The run_dir is stored on the
    monitor object at start_experiment time from the kanban client's
    workspace state.

    Parameters
    ----------
    result : Dict[str, Any]
        The result from monitor.stop() with final metrics.
    run_dir : Path
        The experiment run directory containing project_info.json.
    """
    try:
        completion_file = run_dir / "experiment_complete.json"
        completion_data = {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "run_name": result.get("run_name"),
            "final_metrics": result.get("final_metrics", {}),
            "success": result.get("success", True),
        }

        with open(completion_file, "w") as f:
            json.dump(completion_data, f, indent=2)

        logger.info(f"Wrote experiment_complete.json to {completion_file}")

    except Exception as e:
        logger.warning(f"Failed to write experiment_complete.json: {e}")


async def get_experiment_status() -> Dict[str, Any]:
    """
    Get the status of the current experiment.

    Returns current run metadata and project task counts. Use this to
    decide when to stop polling: when ``is_running`` is false, the
    experiment is over and Marcus has finalized results.

    Returns
    -------
    Dict[str, Any]
        Status payload. Top-level fields:

        Run metadata:
            - is_running (bool): True while the experiment is active.
              Flips to False when Marcus auto-ends the experiment
              (all tasks done) or end_experiment is called explicitly.
              **This is the canonical "should I stop?" signal.**
            - run_name (str): MLflow run identifier.
            - experiment_name (str): Experiment identifier.
            - registered_agents (int): Number of worker agents
              currently registered with Marcus.

        Project task counts (kanban truth, sourced from the backend):
            - total_tasks (int): Total tasks in the project.
            - completed_tasks (int): Tasks marked DONE on the board.
            - in_progress_tasks (int): Tasks currently being worked on.
            - backlog_tasks (int): Tasks not yet started.
            - blocked_tasks (int): Tasks blocked on dependencies.

        Use these for completion math::

            percent = round(100 * completed_tasks / total_tasks, 1)
            project_done = (
                completed_tasks == total_tasks
                and in_progress_tasks == 0
            )

        Marcus uses the same formula internally to decide when to flip
        ``is_running`` to false, so reading ``is_running`` is equivalent
        to evaluating the formula yourself — and is the recommended path
        for agents.

        Observability counters (running event tallies for MLflow):
            - task_assignments (int): Number of times tasks were ever
              assigned to agents during this run (grows with each
              recovery/reassignment).
            - task_completions (int): Number of completion events the
              monitor has observed during this run.
            - blockers_reported (int)
            - artifacts_created (int)
            - decisions_logged (int)
            - context_requests (int)

        These counters track *events seen by the monitor*, not project
        totals. They feed MLflow metrics and dashboards. For project
        completion math, use the kanban truth fields above.

    Examples
    --------
    Polling loop until the experiment ends::

        while True:
            status = await get_experiment_status()
            if not status["is_running"]:
                print("EXPERIMENT COMPLETE")
                break
            done = status["completed_tasks"]
            total = status["total_tasks"]
            percent = round(100 * done / total, 1) if total else 0.0
            print(f"Project: {done}/{total} ({percent}%)")
            await asyncio.sleep(120)
    """
    monitor = get_active_monitor()

    if monitor is None:
        return {"is_running": False, "message": "No experiment is currently running"}

    return await monitor.get_status()


# Tool metadata for MCP registration
EXPERIMENT_TOOLS = {
    "start_experiment": {
        "function": start_experiment,
        "description": "Start a live experiment with MLflow tracking",
        "parameters": {
            "type": "object",
            "properties": {
                "experiment_name": {
                    "type": "string",
                    "description": "Name for the MLflow experiment",
                },
                "board_id": {
                    "type": "string",
                    "description": (
                        "Board ID to monitor (optional, uses active "
                        "project if not provided)"
                    ),
                },
                "project_id": {
                    "type": "string",
                    "description": (
                        "Project ID to monitor (optional, uses active "
                        "project if not provided)"
                    ),
                },
                "run_name": {
                    "type": "string",
                    "description": "Name for this run (optional)",
                },
                "tracking_interval": {
                    "type": "integer",
                    "description": "Metrics logging interval in seconds",
                    "default": 30,
                },
                "params": {
                    "type": "object",
                    "description": "Additional experiment parameters",
                },
                "tags": {"type": "object", "description": "Tags for the MLflow run"},
            },
            "required": ["experiment_name"],
        },
    },
    "end_experiment": {
        "function": end_experiment,
        "description": "Stop the current experiment and finalize results",
        "parameters": {"type": "object", "properties": {}},
    },
    "get_experiment_status": {
        "function": get_experiment_status,
        "description": "Get the status of the current experiment",
        "parameters": {"type": "object", "properties": {}},
    },
}
