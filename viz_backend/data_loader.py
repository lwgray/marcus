"""
Data Loader for Marcus Visualization Backend.

Reads data from Marcus persistence layer and logs, transforming it
into the format expected by the viz-dashboard frontend.
"""

import json
import logging
from datetime import datetime, timezone
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

        # Load project metadata from projects.json
        projects_file = self.persistence_dir / "projects.json"
        projects_data = {}
        project_timeframes = {}
        if projects_file.exists():
            try:
                with open(projects_file, "r") as f:
                    projects_data = json.load(f)
                    logger.info(
                        f"Loaded projects data with {len(projects_data)} entries"
                    )

                    # Build project timeframes for heuristic filtering
                    for proj_key, proj_info in projects_data.items():
                        if proj_key != "active_project" and isinstance(proj_info, dict):
                            if "id" in proj_info:
                                proj_id = proj_info["id"]
                                created = proj_info.get("created_at")
                                last_used = proj_info.get("last_used", created)
                                if created and last_used:
                                    project_timeframes[proj_id] = {
                                        "start": created,
                                        "end": last_used,
                                        "name": proj_info.get("name", "Unknown"),
                                    }
            except Exception as e:
                logger.error(f"Error loading projects.json: {e}")
        else:
            logger.warning(f"Projects file not found: {projects_file}")

        # Load tasks from subtasks.json (where Marcus actually stores tasks)
        subtasks_file = self.persistence_dir / "subtasks.json"
        all_subtasks = {}
        if subtasks_file.exists():
            try:
                with open(subtasks_file, "r") as f:
                    subtasks_data = json.load(f)
                    all_subtasks = subtasks_data.get("subtasks", {})
                    logger.info(
                        f"Loaded {len(all_subtasks)} subtasks from subtasks.json"
                    )
            except Exception as e:
                logger.error(f"Error loading subtasks.json: {e}")
        else:
            logger.warning(f"Subtasks file not found: {subtasks_file}")

        # Parse tasks from subtasks
        for task_id, task_data in all_subtasks.items():

            try:
                # Get parent task ID
                parent_task_id = task_data.get("parent_task_id", "")

                # Match task to project by parent_task_id
                task_project_id = "unknown"
                task_project_name = "Unknown Project"

                if parent_task_id and project_timeframes:
                    # First, try to match to a known project by board/project ID
                    for proj_id, timeframe in project_timeframes.items():
                        # Get the board_id and project_id from projects_data
                        proj_data = projects_data.get(proj_id, {})
                        config = proj_data.get("provider_config", {})
                        board_id = str(config.get("board_id", ""))
                        kanban_project_id = str(config.get("project_id", ""))

                        # Check if parent_task_id starts with board or project prefix
                        if (board_id and parent_task_id.startswith(board_id[:8])) or (
                            kanban_project_id
                            and parent_task_id.startswith(kanban_project_id[:8])
                        ):
                            task_project_id = proj_id  # Use Marcus UUID
                            task_project_name = timeframe["name"]
                            break
                    else:
                        # No match to known project - use inferred
                        board_prefix = parent_task_id[:8]
                        task_project_id = f"inferred_{board_prefix}"
                        task_project_name = f"Legacy Project {board_prefix}"

                # Use timezone-aware datetime for defaults
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
                    "project_id": task_project_id,
                    "project_name": task_project_name,
                    "is_subtask": True,
                    "parent_task_id": parent_task_id,
                    "subtask_index": task_data.get("order", 0),
                    "progress": self._calculate_progress(task_data),
                }

                # Filter by project_id if specified
                if project_id is None or task_project_id == project_id:
                    tasks.append(viz_task)
            except Exception as e:
                logger.error(f"Error parsing task {task_id}: {e}")
                continue

        logger.info(f"Loaded {len(tasks)} tasks from persistence")

        # Enrich with actual timing data from marcus.db and agent_events
        tasks = self.enrich_tasks_with_timing(tasks)

        # Filter out tasks that don't have valid timing (incomplete/future tasks)
        # These are tasks with updated_at far in the future or actual_hours = 0
        # Keep only tasks that have completed or are within the project timeline
        filtered_tasks = []
        for task in tasks:
            # Keep tasks that have actual work done
            if task.get("actual_hours", 0.0) > 0:
                filtered_tasks.append(task)
            # Or tasks that are completed/done
            elif task.get("status") in ["done", "completed"]:
                filtered_tasks.append(task)

        removed_count = len(tasks) - len(filtered_tasks)
        logger.info(
            f"Filtered to {len(filtered_tasks)} completed/active tasks "
            f"(removed {removed_count} incomplete)"
        )
        return filtered_tasks

    def load_parent_tasks_from_persistence(
        self, project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Load parent tasks with aggregated subtask data.

        Groups subtasks by parent_task_id and creates parent task entries
        with aggregated progress, timing, and dependencies.

        Parameters
        ----------
        project_id : Optional[str]
            Specific project ID to load tasks for. If None, loads from all projects.

        Returns
        -------
        List[Dict[str, Any]]
            List of parent tasks with aggregated subtask data
        """
        # First load all subtasks
        subtasks = self.load_tasks_from_persistence(project_id=project_id)

        # Group by parent_task_id
        from collections import defaultdict

        parent_groups = defaultdict(list)

        for subtask in subtasks:
            parent_id = subtask.get("parent_task_id")
            if parent_id:
                parent_groups[parent_id].append(subtask)

        # Create parent task entries
        parent_tasks = []

        for parent_id, children in parent_groups.items():
            # Aggregate data from children
            total_estimated = sum(c.get("estimated_hours", 0.0) for c in children)
            total_actual = sum(c.get("actual_hours", 0.0) for c in children)

            # Calculate overall status
            statuses = [c.get("status") for c in children]
            if all(s == "done" for s in statuses):
                overall_status = "done"
            elif any(s == "blocked" for s in statuses):
                overall_status = "blocked"
            elif any(s == "in_progress" for s in statuses):
                overall_status = "in_progress"
            else:
                overall_status = "todo"

            # Calculate overall progress
            if total_estimated > 0:
                progress = int((total_actual / total_estimated) * 100)
            else:
                done_count = sum(1 for s in statuses if s == "done")
                progress = int((done_count / len(children)) * 100) if children else 0

            # Get earliest start and latest end
            start_times: List[str] = [
                str(c.get("created_at")) for c in children if c.get("created_at")
            ]
            # Only use updated_at from completed tasks or tasks with actual hours
            end_times: List[str] = [
                str(c.get("updated_at"))
                for c in children
                if c.get("updated_at")
                and (
                    c.get("status") in ["done", "completed"]
                    or c.get("actual_hours", 0.0) > 0
                )
            ]

            created_at: Optional[str] = min(start_times) if start_times else None
            updated_at: Optional[str] = max(end_times) if end_times else None

            # Collect unique dependencies from all subtasks
            all_dependencies = set()
            for child in children:
                all_dependencies.update(child.get("dependencies", []))

            # Get project info from first child
            project_id_val = children[0].get("project_id") if children else "unknown"
            project_name = (
                children[0].get("project_name") if children else "Unknown Project"
            )

            # Create parent task name (use a pattern or first subtask's parent info)
            # Try to infer parent name from subtask pattern
            parent_name = f"Parent Task {parent_id}"
            if children:
                # Try to extract common prefix from subtask names
                first_name = children[0].get("name", "")
                # Remove common suffixes like "Integrate and validate", "Design", etc.
                for prefix in ["Design ", "Implement ", "Test ", "Integrate "]:
                    if first_name.startswith(prefix):
                        parent_name = (
                            first_name.split(prefix)[1]
                            if " " in first_name
                            else first_name
                        )
                        break

            parent_task = {
                "id": parent_id,
                "name": parent_name,
                "description": f"Parent task with {len(children)} subtasks",
                "status": overall_status,
                "priority": (
                    children[0].get("priority", "medium") if children else "medium"
                ),
                "assigned_to": None,  # Parent tasks aren't assigned
                "created_at": created_at,
                "updated_at": updated_at,
                "estimated_hours": total_estimated,
                "actual_hours": total_actual,
                "dependencies": list(all_dependencies),
                "labels": [],
                "project_id": project_id_val,
                "project_name": project_name,
                "is_parent": True,
                "subtask_count": len(children),
                "subtasks": [c["id"] for c in children],  # Reference to children
                "progress": progress,
            }

            parent_tasks.append(parent_task)

        logger.info(
            f"Created {len(parent_tasks)} parent tasks from {len(subtasks)} subtasks"
        )
        return parent_tasks

    def get_projects_list(self) -> List[Dict[str, Any]]:
        """
        Get list of all projects with metadata.

        Also includes inferred projects from parent_task_ids that don't match
        any project in projects.json (legacy/archived projects).

        Returns
        -------
        List[Dict[str, Any]]
            List of projects with id, name, last_used
        """
        projects: List[Dict[str, Any]] = []
        known_parent_ids = set()

        projects_file = self.persistence_dir / "projects.json"
        if not projects_file.exists():
            return projects

        try:
            with open(projects_file, "r") as f:
                projects_data = json.load(f)

            # Add known projects from projects.json
            for project_key, project_info in projects_data.items():
                # Skip special keys
                if project_key == "active_project" or not isinstance(
                    project_info, dict
                ):
                    continue
                if "id" not in project_info:
                    continue

                projects.append(
                    {
                        "id": project_info.get("id"),
                        "name": project_info.get("name", "Unnamed Project"),
                        "last_used": project_info.get("last_used"),
                        "created_at": project_info.get("created_at"),
                        "provider": project_info.get("provider", "unknown"),
                        "is_inferred": False,
                    }
                )

                # Track known parent task IDs from provider config
                config = project_info.get("provider_config", {})
                if "board_id" in config:
                    known_parent_ids.add(str(config["board_id"]))
                if "project_id" in config:
                    known_parent_ids.add(str(config["project_id"]))

            # Infer additional projects from tasks that don't match any known project
            subtasks_file = self.persistence_dir / "subtasks.json"
            if subtasks_file.exists():
                with open(subtasks_file, "r") as f:
                    subtasks_data = json.load(f)
                    all_subtasks = subtasks_data.get("subtasks", {})

                # Group tasks by parent_task_id prefix
                # (first 7-8 digits likely indicate board)
                from collections import defaultdict

                parent_groups = defaultdict(list)

                for task_id, task_data in all_subtasks.items():
                    parent_id = task_data.get("parent_task_id", "")
                    if parent_id:
                        # Use first 8 digits as board identifier
                        board_prefix = parent_id[:8]
                        parent_groups[board_prefix].append(task_data)

                # Create inferred projects for groups with tasks
                for board_prefix, tasks in parent_groups.items():
                    # Skip if this matches a known project
                    if any(pid.startswith(board_prefix) for pid in known_parent_ids):
                        continue

                    # Create virtual project
                    # Use the oldest and newest task timestamps
                    task_times = [
                        t.get("created_at") for t in tasks if t.get("created_at")
                    ]
                    if task_times:
                        oldest = min(task_times)
                        newest = max(task_times)

                        projects.append(
                            {
                                "id": f"inferred_{board_prefix}",
                                "name": f"Legacy Project {board_prefix}",
                                "last_used": newest,
                                "created_at": oldest,
                                "provider": "inferred",
                                "is_inferred": True,
                                "task_count": len(tasks),
                                "board_prefix": board_prefix,
                            }
                        )

            # Sort by last_used descending (most recent first)
            projects.sort(
                key=lambda p: p.get("last_used") or p.get("created_at") or "",
                reverse=True,
            )

            inferred_count = sum(1 for p in projects if p.get("is_inferred"))
            logger.info(
                f"Found {len(projects)} projects " f"({inferred_count} inferred)"
            )
            return projects
        except Exception as e:
            logger.error(f"Error loading projects list: {e}")
            return []

    def get_active_project_id(self) -> Optional[str]:
        """
        Get the currently active project ID.

        Returns
        -------
        Optional[str]
            Active project ID or None
        """
        projects_file = self.persistence_dir / "projects.json"
        if not projects_file.exists():
            return None

        try:
            with open(projects_file, "r") as f:
                projects_data = json.load(f)

            active = projects_data.get("active_project", {})
            project_id = active.get("project_id")
            return str(project_id) if project_id is not None else None
        except Exception as e:
            logger.error(f"Error getting active project: {e}")
            return None

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

        # Calculate time boundaries using task assignment/completion events
        # This gives the actual project execution timeline
        import sqlite3

        db_path = self.marcus_root / "data" / "marcus.db"
        start_time = None
        end_time = None
        total_duration_minutes = 0

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get first task start (from task_completed events which have started_at)
            cursor.execute(
                """
                SELECT MIN(json_extract(data, '$.data.started_at'))
                FROM persistence
                WHERE collection = 'events'
                  AND json_extract(data, '$.event_type') = 'task_completed'
                  AND json_extract(data, '$.data.started_at') IS NOT NULL
            """
            )
            first_start = cursor.fetchone()[0]

            # Get last task completion
            cursor.execute(
                """
                SELECT MAX(json_extract(data, '$.data.completed_at'))
                FROM persistence
                WHERE collection = 'events'
                  AND json_extract(data, '$.event_type') = 'task_completed'
                  AND json_extract(data, '$.data.completed_at') IS NOT NULL
            """
            )
            last_completion = cursor.fetchone()[0]

            conn.close()

            if first_start and last_completion:
                start_time = datetime.fromisoformat(first_start.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(
                    last_completion.replace("Z", "+00:00")
                )

                # Make timezone-aware if naive
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)

                duration = end_time - start_time
                total_duration_minutes = int(duration.total_seconds() / 60)
        except Exception as e:
            logger.warning(
                f"Could not load timeline from events: {e}, "
                f"falling back to task timestamps"
            )

            # Fallback: use task timestamps
            all_timestamps = []
            for task in tasks:
                if task.get("created_at"):
                    all_timestamps.append(task["created_at"])
                if task.get("updated_at"):
                    status = task.get("status", "")
                    actual_hours = task.get("actual_hours", 0.0)
                    if status in ["done", "completed"] or actual_hours > 0:
                        all_timestamps.append(task["updated_at"])

            parsed_times = []
            for ts_str in all_timestamps:
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    parsed_times.append(ts)
                except Exception:  # nosec B112
                    continue

            if parsed_times:
                start_time = min(parsed_times)
                end_time = max(parsed_times)
                duration = end_time - start_time
                total_duration_minutes = int(duration.total_seconds() / 60)

        if not start_time or not end_time:
            # Final fallback
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
                # Make timezone-aware if naive
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
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

    def load_all_data(
        self, project_id: Optional[str] = None, view: str = "subtasks"
    ) -> Dict[str, Any]:
        """
        Load all data and return in SimulationData format.

        Parameters
        ----------
        project_id : Optional[str]
            Specific project to load data for
        view : str
            View mode: 'subtasks' (default) or 'parents'

        Returns
        -------
        Dict[str, Any]
            Complete simulation data in viz-dashboard format
        """
        logger.info(
            f"Loading all data for project: {project_id or 'all'}, view: {view}"
        )

        # Load all data sources
        if view == "parents":
            tasks = self.load_parent_tasks_from_persistence(project_id)
        else:
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

    def load_task_outcomes_from_db(self) -> Dict[str, Dict[str, Any]]:
        """
        Load task outcomes from marcus.db (Memory system).

        Returns actual task durations and completion data.

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Dictionary mapping task_id to outcome data with actual_hours, etc.
        """
        import sqlite3

        db_path = self.marcus_root / "data" / "marcus.db"
        if not db_path.exists():
            logger.warning(f"marcus.db not found at {db_path}")
            return {}

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Query task_outcomes from persistence table
            cursor.execute(
                """
                SELECT key, data FROM persistence
                WHERE collection = 'task_outcomes'
            """
            )

            outcomes = {}
            for row in cursor.fetchall():
                task_id, data_json = row
                data = json.loads(data_json)

                # Extract key fields
                outcomes[task_id] = {
                    "task_id": task_id,
                    "task_name": data.get("task_name"),
                    "actual_hours": data.get("actual_hours", 0.0),
                    "estimated_hours": data.get("estimated_hours", 0.0),
                    "created_at": data.get("created_at"),
                    "completed_at": data.get("completed_at"),
                    "status": "done",  # Outcomes are for completed tasks
                }

            conn.close()
            logger.info(f"Loaded {len(outcomes)} task outcomes from marcus.db")
            return outcomes

        except Exception as e:
            logger.error(f"Error loading task outcomes from db: {e}")
            return {}

    def load_task_timing_from_agent_events(self) -> Dict[str, Dict[str, Any]]:
        """
        Load task start/end times from events in marcus.db.

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Dictionary mapping task_id to timing data with
            start_time, end_time, duration
        """
        import sqlite3

        timings: Dict[str, Any] = {}
        db_path = self.marcus_root / "data" / "marcus.db"

        if not db_path.exists():
            logger.warning(f"marcus.db not found at {db_path}")
            return timings

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get task_completed events which contain started_at and completed_at
            cursor.execute(
                """
                SELECT data FROM persistence
                WHERE collection = 'events'
                  AND json_extract(data, '$.event_type') = 'task_completed'
            """
            )

            for row in cursor.fetchall():
                try:
                    event = json.loads(row[0])
                    event_data = event.get("data", {})

                    task_id = event_data.get("task_id")
                    started_at = event_data.get(
                        "started_at"
                    )  # e.g., "2025-10-20T13:59:26.935749"
                    completed_at = event_data.get(
                        "completed_at"
                    )  # e.g., "2025-10-20T14:27:52.738785"
                    task_name = event_data.get("task_name")

                    if task_id and started_at and completed_at:
                        # Ensure timestamps have timezone info for
                        # JavaScript compatibility
                        # Marcus events store timestamps without timezone,
                        # so add UTC
                        start_with_tz = (
                            started_at
                            if started_at.endswith(("Z", "+00:00"))
                            else started_at + "+00:00"
                        )
                        end_with_tz = (
                            completed_at
                            if completed_at.endswith(("Z", "+00:00"))
                            else completed_at + "+00:00"
                        )

                        timings[task_id] = {
                            "start_time": start_with_tz,
                            "end_time": end_with_tz,
                            "task_name": task_name,
                        }

                        # Calculate duration
                        try:
                            start = datetime.fromisoformat(
                                start_with_tz.replace("Z", "+00:00")
                            )
                            end = datetime.fromisoformat(
                                end_with_tz.replace("Z", "+00:00")
                            )
                            duration_seconds = (end - start).total_seconds()
                            timings[task_id]["duration_seconds"] = duration_seconds
                            timings[task_id]["duration_minutes"] = duration_seconds / 60
                            timings[task_id]["duration_hours"] = duration_seconds / 3600
                        except Exception as e:
                            logger.warning(
                                f"Error calculating duration for {task_id}: {e}"
                            )

                except json.JSONDecodeError as e:
                    logger.warning(f"Error parsing event JSON: {e}")
                    continue

            conn.close()
            logger.info(f"Loaded timing for {len(timings)} tasks from marcus.db events")
            if timings:
                # Log first timing for debugging
                first_task_id = list(timings.keys())[0]
                logger.info(
                    f"Example timing: {first_task_id} -> {timings[first_task_id]}"
                )
            return timings

        except Exception as e:
            logger.error(f"Error loading task timing from marcus.db events: {e}")
            return {}

    def enrich_tasks_with_timing(
        self, tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich task data with actual timing from marcus.db and agent_events.

        Parameters
        ----------
        tasks : List[Dict[str, Any]]
            Tasks from subtasks.json

        Returns
        -------
        List[Dict[str, Any]]
            Tasks enriched with actual start/end times and durations
        """
        # Load timing data
        outcomes = self.load_task_outcomes_from_db()
        timings = self.load_task_timing_from_agent_events()

        logger.info(
            f"Enriching {len(tasks)} tasks with {len(outcomes)} outcomes "
            f"and {len(timings)} timings"
        )

        # Enrich each task
        enriched_count = 0
        for task in tasks:
            task_id = task["id"]

            # Add outcome data if available (try exact match first, then prefix match)
            if task_id in outcomes:
                outcome = outcomes[task_id]
                task["actual_hours"] = outcome["actual_hours"]
                if outcome["completed_at"]:
                    task["updated_at"] = outcome["completed_at"]
            else:
                # Try prefix match (task IDs in marcus.db have agent suffix)
                for outcome_id, outcome in outcomes.items():
                    if outcome_id.startswith(task_id + "_"):
                        task["actual_hours"] = outcome["actual_hours"]
                        if outcome["completed_at"]:
                            task["updated_at"] = outcome["completed_at"]
                        break

            # Add timing data if available (try exact match first, then prefix match)
            if task_id in timings:
                timing = timings[task_id]
                if "start_time" in timing:
                    task["created_at"] = timing[
                        "start_time"
                    ]  # Override with actual start
                if "end_time" in timing:
                    task["updated_at"] = timing["end_time"]  # Set actual end time
                if "duration_hours" in timing:
                    task["actual_hours"] = timing["duration_hours"]
                enriched_count += 1
            else:
                # Try prefix match
                for timing_id, timing in timings.items():
                    if timing_id.startswith(task_id + "_"):
                        if "start_time" in timing:
                            task["created_at"] = timing["start_time"]
                        if "end_time" in timing:
                            task["updated_at"] = timing["end_time"]
                        if "duration_hours" in timing:
                            task["actual_hours"] = timing["duration_hours"]
                        enriched_count += 1
                        break

        logger.info(f"Enriched {enriched_count}/{len(tasks)} tasks with timing data")
        return tasks
