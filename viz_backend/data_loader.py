"""
Data Loader for Marcus Visualization Backend.

Reads data from Marcus persistence layer and logs, transforming it
into the format expected by the viz-dashboard frontend.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MarcusDataLoader:
    """
    Load data from Marcus persistence and logs.

    This class provides methods to read Marcus data from various sources
    and transform it into the SimulationData format expected by the
    viz-dashboard frontend.
    """

    def __init__(self, marcus_root: Optional[Path] = None):
        """
        Initialize the data loader.

        Parameters
        ----------
        marcus_root : Optional[Path]
            Path to Marcus root directory. If None, auto-detects from current location.
        """
        if marcus_root is None:
            # Auto-detect Marcus root (viz-backend is in Marcus root)
            self.marcus_root = Path(__file__).parent.parent
        else:
            self.marcus_root = Path(marcus_root)

        self.persistence_dir = self.marcus_root / "data" / "marcus_state"
        self.conversation_logs_dir = self.marcus_root / "logs" / "conversations"
        self.agent_events_dir = self.marcus_root / "logs" / "agent_events"

        logger.info(f"Initialized MarcusDataLoader with root: {self.marcus_root}")

    def load_tasks_from_persistence(
        self, project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Load tasks from persistence layer.

        Parameters
        ----------
        project_id : Optional[str]
            Specific project ID to load tasks for. If None, loads from all projects.

        Returns
        -------
        List[Dict[str, Any]]
            List of tasks in viz-dashboard format
        """
        tasks: List[Dict[str, Any]] = []

        if not self.persistence_dir.exists():
            logger.warning(f"Persistence directory not found: {self.persistence_dir}")
            return tasks

        # Load from projects.json
        projects_file = self.persistence_dir / "projects.json"
        if projects_file.exists():
            try:
                with open(projects_file, "r") as f:
                    projects_data = json.load(f)
                    logger.info(
                        f"Loaded projects data with {len(projects_data)} entries"
                    )
            except Exception as e:
                logger.error(f"Error loading projects.json: {e}")
                return tasks
        else:
            logger.warning(f"Projects file not found: {projects_file}")
            return tasks

        # TODO: Parse tasks from projects_data
        # For now, return empty list - will implement in next commit

        return tasks

    def load_messages_from_logs(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Load conversation messages from Marcus logs.

        Parameters
        ----------
        start_time : Optional[datetime]
            Filter messages after this time
        end_time : Optional[datetime]
            Filter messages before this time

        Returns
        -------
        List[Dict[str, Any]]
            List of messages in viz-dashboard format
        """
        messages: List[Dict[str, Any]] = []

        if not self.conversation_logs_dir.exists():
            logger.warning(
                f"Conversation logs directory not found: {self.conversation_logs_dir}"
            )
            return messages

        # Find all conversation log files (JSONL format)
        log_files = sorted(self.conversation_logs_dir.glob("conversations_*.jsonl"))
        logger.info(f"Found {len(log_files)} conversation log files")

        for log_file in log_files:
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        if not line.strip():
                            continue

                        try:
                            _log_entry = json.loads(line)  # noqa: F841
                            # TODO: Transform _log_entry to viz Message format
                            # Will implement in next commit
                        except json.JSONDecodeError as e:
                            logger.debug(
                                f"Skipping invalid JSON line in {log_file}: {e}"
                            )
                            continue

            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")
                continue

        return messages

    def load_events_from_logs(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Load agent events from Marcus logs.

        Parameters
        ----------
        start_time : Optional[datetime]
            Filter events after this time
        end_time : Optional[datetime]
            Filter events before this time

        Returns
        -------
        List[Dict[str, Any]]
            List of events in viz-dashboard format
        """
        events: List[Dict[str, Any]] = []

        if not self.agent_events_dir.exists():
            logger.warning(f"Agent events directory not found: {self.agent_events_dir}")
            return events

        # Find all agent event log files (JSONL format)
        log_files = sorted(self.agent_events_dir.glob("agent_events_*.jsonl"))
        logger.info(f"Found {len(log_files)} agent event log files")

        for log_file in log_files:
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        if not line.strip():
                            continue

                        try:
                            _event_entry = json.loads(line)  # noqa: F841
                            # TODO: Transform _event_entry to viz Event format
                            # Will implement in next commit
                        except json.JSONDecodeError as e:
                            logger.debug(
                                f"Skipping invalid JSON line in {log_file}: {e}"
                            )
                            continue

            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")
                continue

        return events

    def infer_agents_from_data(
        self, tasks: List[Dict[str, Any]], messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Infer agent information from tasks and messages.

        Parameters
        ----------
        tasks : List[Dict[str, Any]]
            List of tasks
        messages : List[Dict[str, Any]]
            List of messages

        Returns
        -------
        List[Dict[str, Any]]
            List of agents in viz-dashboard format
        """
        agents: List[Dict[str, Any]] = []

        # TODO: Build agent list from:
        # 1. Unique assigned_to values in tasks
        # 2. Message senders/receivers (excluding 'marcus')
        # 3. Calculate metrics (completed tasks, autonomy score)
        # Will implement in next commit

        return agents

    def calculate_metadata(
        self,
        tasks: List[Dict[str, Any]],
        messages: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate simulation metadata.

        Parameters
        ----------
        tasks : List[Dict[str, Any]]
            List of tasks
        messages : List[Dict[str, Any]]
            List of messages
        events : List[Dict[str, Any]]
            List of events

        Returns
        -------
        Dict[str, Any]
            Metadata in viz-dashboard format
        """
        metadata = {
            "project_name": "Unknown Project",
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_duration_hours": 0.0,
        }

        # TODO: Calculate actual metadata from data
        # Will implement in next commit

        return metadata

    def load_all_data(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Load all data and return in SimulationData format.

        Parameters
        ----------
        project_id : Optional[str]
            Specific project to load data for

        Returns
        -------
        Dict[str, Any]
            Complete simulation data in viz-dashboard format
        """
        logger.info(f"Loading all data for project: {project_id or 'all'}")

        # Load all data sources
        tasks = self.load_tasks_from_persistence(project_id)
        messages = self.load_messages_from_logs()
        events = self.load_events_from_logs()
        agents = self.infer_agents_from_data(tasks, messages)
        metadata = self.calculate_metadata(tasks, messages, events)

        simulation_data = {
            "tasks": tasks,
            "agents": agents,
            "messages": messages,
            "events": events,
            "metadata": metadata,
        }

        logger.info(
            f"Loaded: {len(tasks)} tasks, {len(agents)} agents, "
            f"{len(messages)} messages, {len(events)} events"
        )

        return simulation_data
