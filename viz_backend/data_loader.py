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

        # Parse tasks from projects_data
        for project_key, project_info in projects_data.items():
            # Filter by project_id if specified
            if project_id and project_key != project_id:
                continue

            project_name = project_info.get("name", "Unknown Project")
            project_tasks = project_info.get("tasks", {})

            for task_id, task_data in project_tasks.items():
                try:
                    # Transform Marcus Task to viz format
                    # Use timezone-aware datetime for defaults
                    from datetime import timezone

                    now = datetime.now(timezone.utc).isoformat()

                    viz_task = {
                        "id": task_id,
                        "name": task_data.get("name", "Untitled Task"),
                        "description": task_data.get("description", ""),
                        "status": task_data.get("status", "todo"),
                        "priority": task_data.get("priority", "medium"),
                        "assigned_to": task_data.get("assigned_to"),
                        "created_at": task_data.get("created_at", now),
                        "updated_at": task_data.get("updated_at", now),
                        "due_date": task_data.get("due_date"),
                        "estimated_hours": task_data.get("estimated_hours", 0.0),
                        "actual_hours": task_data.get("actual_hours", 0.0),
                        "dependencies": task_data.get("dependencies", []),
                        "labels": task_data.get("labels", []),
                        "project_id": project_key,
                        "project_name": project_name,
                        "is_subtask": task_data.get("is_subtask", False),
                        "parent_task_id": task_data.get("parent_task_id"),
                        "subtask_index": task_data.get("subtask_index"),
                        "progress": self._calculate_progress(task_data),
                    }
                    tasks.append(viz_task)
                except Exception as e:
                    logger.error(f"Error parsing task {task_id}: {e}")
                    continue

        logger.info(f"Loaded {len(tasks)} tasks from persistence")
        return tasks

    def _calculate_progress(self, task_data: Dict[str, Any]) -> int:
        """
        Calculate task progress percentage.

        Parameters
        ----------
        task_data : Dict[str, Any]
            Task data from persistence

        Returns
        -------
        int
            Progress percentage (0-100)
        """
        status = task_data.get("status", "todo")
        if status == "done":
            return 100
        elif status == "in_progress":
            # Try to calculate from actual vs estimated hours
            estimated = task_data.get("estimated_hours", 0.0)
            actual = task_data.get("actual_hours", 0.0)
            if estimated > 0:
                return min(int((actual / estimated) * 100), 90)
            return 50  # Default for in_progress
        elif status == "blocked":
            return 0
        else:  # todo
            return 0

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
        message_id_counter = 0

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
                            log_entry = json.loads(line)

                            # Extract timestamp - it's at top level
                            timestamp_str = log_entry.get("timestamp")
                            if not timestamp_str:
                                continue

                            # Parse timestamp for filtering
                            try:
                                msg_time = datetime.fromisoformat(
                                    timestamp_str.replace("Z", "+00:00")
                                )
                                if start_time and msg_time < start_time:
                                    continue
                                if end_time and msg_time > end_time:
                                    continue
                            except Exception:
                                pass  # Keep message if timestamp parsing fails

                            # Data is at top level, not nested
                            conversation_type = log_entry.get("conversation_type", "")

                            # Map conversation types to viz message types
                            message_type = self._map_conversation_type(
                                conversation_type, log_entry
                            )

                            # Extract from/to
                            from_id = log_entry.get(
                                "worker_id", log_entry.get("from", "marcus")
                            )
                            to_id = log_entry.get("to", "marcus")
                            if conversation_type == "pm_to_worker":
                                from_id = "marcus"
                                to_id = log_entry.get("worker_id", "unknown")

                            # Extract message content from various fields
                            message_text = (
                                log_entry.get("message", "")
                                or log_entry.get("decision", "")
                                or log_entry.get("content", "")
                                or log_entry.get("action", "")
                            )

                            # Extract task_id from various locations
                            task_id = log_entry.get("task_id")
                            if not task_id and "data" in log_entry:
                                task_id = log_entry.get("data", {}).get("task_id")

                            # Build metadata
                            metadata = {}
                            if "progress" in log_entry:
                                metadata["progress"] = log_entry["progress"]
                            if "blocking" in log_entry:
                                metadata["blocking"] = log_entry["blocking"]
                            if "response_time" in log_entry:
                                metadata["response_time"] = log_entry["response_time"]
                            if "confidence_score" in log_entry:
                                metadata["confidence"] = log_entry["confidence_score"]

                            # Create viz message
                            viz_message = {
                                "id": f"msg-{message_id_counter}",
                                "timestamp": timestamp_str,
                                "from": from_id,
                                "to": to_id,
                                "task_id": task_id,
                                "message": message_text,
                                "type": message_type,
                                "parent_message_id": None,  # Could be enhanced
                                "metadata": metadata,
                            }
                            messages.append(viz_message)
                            message_id_counter += 1

                        except json.JSONDecodeError as e:
                            logger.debug(
                                f"Skipping invalid JSON line in {log_file}: {e}"
                            )
                            continue

            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")
                continue

        logger.info(f"Loaded {len(messages)} messages from logs")
        return messages

    def _map_conversation_type(
        self, conversation_type: str, event_data: Dict[str, Any]
    ) -> str:
        """
        Map Marcus conversation types to viz message types.

        Parameters
        ----------
        conversation_type : str
            Marcus conversation type
        event_data : Dict[str, Any]
            Event data for additional context

        Returns
        -------
        str
            Viz message type
        """
        # Check for specific patterns in message content
        message = event_data.get("message", "").lower()

        if "blocker" in message or "blocked" in message:
            return "blocker"
        elif "?" in message or "question" in conversation_type:
            return "question"
        elif conversation_type == "decision":
            return "instruction"
        elif "progress" in event_data or "progress" in message:
            return "status_update"
        elif conversation_type == "worker_to_pm":
            if "completed" in message or "done" in message:
                return "status_update"
            return "answer"
        elif conversation_type == "pm_to_worker":
            if "assign" in message:
                return "task_assignment"
            return "instruction"
        else:
            return "status_update"

    def load_agent_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        Load agent profiles from assignment persistence and experiments.

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Dictionary mapping agent_id to agent profile data
        """
        agents_data: Dict[str, Dict[str, Any]] = {}

        # Try to load from experiment monitoring data (most complete)
        mlruns_dir = self.marcus_root / "mlruns"
        if mlruns_dir.exists():
            # Find most recent experiment with agent data
            try:
                for exp_dir in sorted(mlruns_dir.iterdir(), reverse=True):
                    if not exp_dir.is_dir() or exp_dir.name == ".trash":
                        continue

                    for run_dir in sorted(exp_dir.iterdir(), reverse=True):
                        if not run_dir.is_dir():
                            continue

                        # Check for agent artifacts
                        artifacts_dir = run_dir / "artifacts"
                        if artifacts_dir.exists():
                            agent_file = artifacts_dir / "agents.json"
                            if agent_file.exists():
                                with open(agent_file, "r") as f:
                                    exp_agents = json.load(f)
                                    for agent_id, agent_info in exp_agents.items():
                                        agents_data[agent_id] = agent_info
                                break
                    if agents_data:
                        break
            except Exception as e:
                logger.debug(f"Could not load agents from mlruns: {e}")

        # Fallback: infer from assignments
        assignments_dir = self.marcus_root / "data" / "assignments"
        if assignments_dir.exists() and not agents_data:
            assignments_file = assignments_dir / "assignments.json"
            if assignments_file.exists():
                try:
                    with open(assignments_file, "r") as f:
                        assignments = json.load(f)
                        for agent_id, assignment_info in assignments.items():
                            if agent_id not in agents_data:
                                agents_data[agent_id] = {
                                    "id": agent_id,
                                    "name": agent_id.replace("_", " ").title(),
                                    "role": "Worker",
                                    "skills": [],
                                }
                except Exception as e:
                    logger.debug(f"Could not load agents from assignments: {e}")

        logger.info(f"Loaded {len(agents_data)} agent profiles")
        return agents_data

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
        event_id_counter = 0

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
                            event_entry = json.loads(line)

                            # Extract timestamp
                            timestamp_str = event_entry.get("timestamp")
                            if not timestamp_str:
                                continue

                            # Parse timestamp for filtering
                            try:
                                event_time = datetime.fromisoformat(
                                    timestamp_str.replace("Z", "+00:00")
                                )
                                if start_time and event_time < start_time:
                                    continue
                                if end_time and event_time > end_time:
                                    continue
                            except Exception:  # nosec B112
                                pass  # Keep event if timestamp parsing fails

                            # Extract event data
                            event_type = event_entry.get("event_type", "unknown")
                            event_data = event_entry.get("data", {})

                            # Extract agent_id and task_id
                            agent_id = event_data.get("worker_id") or event_data.get(
                                "agent_id"
                            )
                            task_id = event_data.get("task_id")

                            # Create viz event
                            viz_event = {
                                "id": f"event-{event_id_counter}",
                                "timestamp": timestamp_str,
                                "event_type": event_type,
                                "agent_id": agent_id,
                                "task_id": task_id,
                                "data": event_data,
                            }
                            events.append(viz_event)
                            event_id_counter += 1

                        except json.JSONDecodeError as e:
                            logger.debug(
                                f"Skipping invalid JSON line in {log_file}: {e}"
                            )
                            continue

            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")
                continue

        logger.info(f"Loaded {len(events)} events from logs")
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
        # Load agent profiles first
        agent_profiles = self.load_agent_profiles()

        # Collect unique agent IDs from tasks and messages
        agent_ids = set()
        for task in tasks:
            if task.get("assigned_to"):
                agent_ids.add(task["assigned_to"])

        for message in messages:
            from_id = message.get("from")
            to_id = message.get("to")
            if from_id and from_id != "marcus":
                agent_ids.add(from_id)
            if to_id and to_id != "marcus":
                agent_ids.add(to_id)

        # Build agent list with metrics
        agents: List[Dict[str, Any]] = []
        for agent_id in agent_ids:
            # Get profile if exists
            profile = agent_profiles.get(agent_id, {})

            # Calculate metrics from tasks
            agent_tasks = [t for t in tasks if t.get("assigned_to") == agent_id]
            completed_tasks = [t for t in agent_tasks if t.get("status") == "done"]
            current_tasks = [
                t["id"] for t in agent_tasks if t.get("status") == "in_progress"
            ]

            # Calculate autonomy from messages
            agent_messages = [m for m in messages if m.get("from") == agent_id]
            questions = [
                m for m in agent_messages if m.get("type") in ["question", "blocker"]
            ]
            autonomy_score = 1.0 - min(len(questions) / max(len(agent_tasks), 1), 0.5)

            # Build viz agent
            viz_agent = {
                "id": agent_id,
                "name": profile.get("name", agent_id.replace("_", " ").title()),
                "role": profile.get("role", "Worker"),
                "skills": profile.get("skills", []),
                "current_tasks": current_tasks,
                "completed_tasks_count": len(completed_tasks),
                "capacity": profile.get("capacity", 40),
                "performance_score": profile.get("performance_score", 1.0),
                "autonomy_score": round(autonomy_score, 2),
            }
            agents.append(viz_agent)

        logger.info(f"Inferred {len(agents)} agents from data")
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
        # Determine project name from tasks
        project_name = "Marcus Project"
        if tasks:
            project_name = tasks[0].get("project_name", "Marcus Project")

        # Calculate time boundaries
        all_timestamps = []

        # Collect timestamps from all sources
        for task in tasks:
            if task.get("created_at"):
                all_timestamps.append(task["created_at"])
            if task.get("updated_at"):
                all_timestamps.append(task["updated_at"])

        for message in messages:
            if message.get("timestamp"):
                all_timestamps.append(message["timestamp"])

        for event in events:
            if event.get("timestamp"):
                all_timestamps.append(event["timestamp"])

        # Parse timestamps and find boundaries
        parsed_times = []
        for ts_str in all_timestamps:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                parsed_times.append(ts)
            except Exception:  # nosec B112
                continue  # Skip invalid timestamps

        if parsed_times:
            start_time = min(parsed_times)
            end_time = max(parsed_times)
            duration = end_time - start_time
            total_duration_minutes = int(duration.total_seconds() / 60)
        else:
            # Use timezone-aware datetime
            from datetime import timezone

            start_time = datetime.now(timezone.utc)
            end_time = datetime.now(timezone.utc)
            total_duration_minutes = 0

        # Calculate max concurrent tasks (parallelization level)
        task_times = []
        for task in tasks:
            try:
                created = datetime.fromisoformat(
                    task["created_at"].replace("Z", "+00:00")
                )
                updated = datetime.fromisoformat(
                    task["updated_at"].replace("Z", "+00:00")
                )
                task_times.append((created, updated))
            except Exception:  # nosec B112
                continue  # Skip tasks with invalid timestamps

        max_concurrent = 0
        if task_times:
            time_points = set()
            for start, end in task_times:
                time_points.add(start)
                time_points.add(end)

            for time_point in sorted(time_points):
                concurrent = sum(
                    1 for start, end in task_times if start <= time_point <= end
                )
                max_concurrent = max(max_concurrent, concurrent)

        metadata = {
            "project_name": project_name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_duration_minutes": total_duration_minutes,
            "parallelization_level": max_concurrent,
        }

        logger.info(
            f"Calculated metadata: {total_duration_minutes}min, "
            f"{max_concurrent} max concurrent"
        )
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
