## Week 5: Telemetry, Research Logging & CATO Integration

**Goal**: Implement comprehensive telemetry for user journey tracking, research-grade event logging for MAS studies, and integrate with CATO dashboard.

**Why**:
- **Telemetry**: Need to understand where users get stuck to improve UX
- **Research Logging**: Enable researchers to study multi-agent system behavior
- **CATO Integration**: Provide real-time visualization of Marcus activity

**Related Issues**: #30 (Research Instrumentation)

---

### Monday: Enhance Telemetry System

**What**: Extend existing AuditLogger with journey milestones and user flow tracking.

**Why**: Current telemetry logs events, but doesn't track user journeys. We need to identify where users get stuck (e.g., "50% of users fail at project creation").

**How**:

#### Step 1.1: Extend AuditLogger with journey tracking

Update `src/marcus_mcp/audit.py`:

```python
"""
Enhanced audit logging with journey tracking.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class JourneyMilestone:
    """
    A milestone in the user journey.

    Attributes
    ----------
    milestone_id : str
        Unique milestone identifier
    session_id : str
        Session identifier
    milestone_name : str
        Human-readable milestone name
    milestone_type : str
        Type (project_creation, task_assignment, etc.)
    status : str
        Status (started, completed, failed)
    timestamp : str
        ISO timestamp
    duration_seconds : float
        Duration (for completed milestones)
    metadata : dict
        Additional metadata
    """

    milestone_id: str
    session_id: str
    milestone_name: str
    milestone_type: str
    status: str
    timestamp: str
    duration_seconds: float
    metadata: Dict[str, Any]


class AuditLogger:
    """Enhanced audit logger with journey tracking."""

    def __init__(self, log_dir: str = "data/audit_logs"):
        """Initialize audit logger."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.journey_file = self.log_dir / "user_journeys.jsonl"

        # In-memory tracking of active milestones
        self._active_milestones: Dict[str, Dict[str, Any]] = {}

    # ... existing methods (log_event, log_tool_call, etc.) ...

    def start_milestone(
        self,
        session_id: str,
        milestone_name: str,
        milestone_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start tracking a journey milestone.

        Parameters
        ----------
        session_id : str
            Session identifier
        milestone_name : str
            Human-readable milestone name
        milestone_type : str
            Type of milestone
        metadata : dict, optional
            Additional metadata

        Returns
        -------
        str
            Milestone ID
        """
        milestone_id = f"{milestone_type}_{datetime.now(timezone.utc).timestamp()}"

        milestone_data = {
            "milestone_id": milestone_id,
            "session_id": session_id,
            "milestone_name": milestone_name,
            "milestone_type": milestone_type,
            "status": "started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "start_time": datetime.now(timezone.utc).timestamp(),
            "metadata": metadata or {}
        }

        # Store active milestone
        self._active_milestones[milestone_id] = milestone_data

        # Log started event
        self._log_journey_event(milestone_data)

        logger.info(f"Started milestone: {milestone_name} ({milestone_id})")

        return milestone_id

    def complete_milestone(
        self,
        milestone_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark milestone as completed.

        Parameters
        ----------
        milestone_id : str
            Milestone ID (from start_milestone)
        metadata : dict, optional
            Additional completion metadata
        """
        if milestone_id not in self._active_milestones:
            logger.warning(f"Milestone {milestone_id} not found in active milestones")
            return

        milestone_data = self._active_milestones[milestone_id]

        # Calculate duration
        start_time = milestone_data["start_time"]
        end_time = datetime.now(timezone.utc).timestamp()
        duration = end_time - start_time

        # Update milestone
        milestone_data["status"] = "completed"
        milestone_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        milestone_data["duration_seconds"] = duration

        if metadata:
            milestone_data["metadata"].update(metadata)

        # Log completed event
        self._log_journey_event(milestone_data)

        # Remove from active milestones
        del self._active_milestones[milestone_id]

        logger.info(
            f"Completed milestone: {milestone_data['milestone_name']} "
            f"({duration:.2f}s)"
        )

    def fail_milestone(
        self,
        milestone_id: str,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark milestone as failed.

        Parameters
        ----------
        milestone_id : str
            Milestone ID
        error_message : str
            Error message
        metadata : dict, optional
            Additional metadata
        """
        if milestone_id not in self._active_milestones:
            logger.warning(f"Milestone {milestone_id} not found in active milestones")
            return

        milestone_data = self._active_milestones[milestone_id]

        # Calculate duration
        start_time = milestone_data["start_time"]
        end_time = datetime.now(timezone.utc).timestamp()
        duration = end_time - start_time

        # Update milestone
        milestone_data["status"] = "failed"
        milestone_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        milestone_data["duration_seconds"] = duration
        milestone_data["error_message"] = error_message

        if metadata:
            milestone_data["metadata"].update(metadata)

        # Log failed event
        self._log_journey_event(milestone_data)

        # Remove from active milestones
        del self._active_milestones[milestone_id]

        logger.warning(
            f"Failed milestone: {milestone_data['milestone_name']} - {error_message}"
        )

    def _log_journey_event(self, milestone_data: Dict[str, Any]) -> None:
        """Log journey event to file."""
        # Remove start_time (internal use only)
        log_data = milestone_data.copy()
        log_data.pop("start_time", None)

        with open(self.journey_file, "a") as f:
            f.write(json.dumps(log_data) + "\n")

    def get_journey_metrics(
        self,
        milestone_type: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get journey metrics (completion rates, avg durations, etc.).

        Parameters
        ----------
        milestone_type : str, optional
            Filter by milestone type
        hours : int
            Look back this many hours

        Returns
        -------
        dict
            Journey metrics
        """
        if not self.journey_file.exists():
            return {
                "total_milestones": 0,
                "completed": 0,
                "failed": 0,
                "completion_rate": 0.0,
                "avg_duration_seconds": 0.0
            }

        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)

        milestones = []
        with open(self.journey_file) as f:
            for line in f:
                event = json.loads(line)

                # Filter by time
                event_time = datetime.fromisoformat(event["timestamp"]).timestamp()
                if event_time < cutoff_time:
                    continue

                # Filter by type
                if milestone_type and event["milestone_type"] != milestone_type:
                    continue

                milestones.append(event)

        # Calculate metrics
        total = len(milestones)
        completed = sum(1 for m in milestones if m["status"] == "completed")
        failed = sum(1 for m in milestones if m["status"] == "failed")

        completion_rate = (completed / total * 100) if total > 0 else 0.0

        # Average duration (for completed milestones)
        completed_milestones = [m for m in milestones if m["status"] == "completed"]
        avg_duration = 0.0
        if completed_milestones:
            durations = [m["duration_seconds"] for m in completed_milestones]
            avg_duration = sum(durations) / len(durations)

        return {
            "total_milestones": total,
            "completed": completed,
            "failed": failed,
            "completion_rate": completion_rate,
            "avg_duration_seconds": avg_duration,
            "milestone_type": milestone_type
        }
```

#### Step 1.2: Add journey tracking to create_project

Update `src/marcus_mcp/tools/task.py` in `create_project`:

```python
async def create_project(
    description: str,
    project_name: str,
    options: Optional[Dict[str, Any]] = None,
    state: Any = None
) -> Dict[str, Any]:
    """
    Create a complete project from natural language description.

    Now tracks user journey milestone.
    """
    try:
        # Start journey milestone
        session_id = state.session_id if hasattr(state, "session_id") else "unknown"

        milestone_id = state.audit_logger.start_milestone(
            session_id=session_id,
            milestone_name="Project Creation",
            milestone_type="project_creation",
            metadata={"project_name": project_name}
        )

        try:
            # ... existing project creation logic ...

            result = await create_project_internal(description, project_name, options, state)

            if result["success"]:
                # Complete milestone
                state.audit_logger.complete_milestone(
                    milestone_id,
                    metadata={
                        "project_id": result["project_id"],
                        "tasks_created": result.get("tasks_created", 0)
                    }
                )
            else:
                # Fail milestone
                state.audit_logger.fail_milestone(
                    milestone_id,
                    error_message=result.get("message", "Unknown error")
                )

            return result

        except Exception as e:
            # Fail milestone on exception
            state.audit_logger.fail_milestone(
                milestone_id,
                error_message=str(e)
            )
            raise

    except Exception as e:
        logger.error(f"Error in create_project: {e}")
        return handle_mcp_tool_error(e, "create_project", {"project_name": project_name})
```

#### Step 1.3: Add journey tracking to request_next_task

Similarly update `request_next_task` to track task assignment milestone.

#### Step 1.4: Write tests

Create `tests/unit/mcp/test_journey_tracking.py`:

```python
"""
Tests for journey tracking.
"""

import pytest
from pathlib import Path
import time

from src.marcus_mcp.audit import AuditLogger


class TestJourneyTracking:
    """Test journey tracking"""

    @pytest.fixture
    def audit_logger(self, tmp_path):
        """Create audit logger."""
        return AuditLogger(log_dir=str(tmp_path / "audit"))

    def test_start_milestone(self, audit_logger):
        """Test starting a milestone."""
        milestone_id = audit_logger.start_milestone(
            session_id="session-1",
            milestone_name="Create Project",
            milestone_type="project_creation",
            metadata={"project_name": "Test"}
        )

        assert milestone_id is not None
        assert milestone_id in audit_logger._active_milestones

    def test_complete_milestone(self, audit_logger):
        """Test completing a milestone."""
        milestone_id = audit_logger.start_milestone(
            session_id="session-1",
            milestone_name="Create Project",
            milestone_type="project_creation"
        )

        time.sleep(0.1)  # Small delay to measure duration

        audit_logger.complete_milestone(milestone_id)

        # Should be removed from active milestones
        assert milestone_id not in audit_logger._active_milestones

        # Should be logged to file
        assert audit_logger.journey_file.exists()

    def test_fail_milestone(self, audit_logger):
        """Test failing a milestone."""
        milestone_id = audit_logger.start_milestone(
            session_id="session-1",
            milestone_name="Create Project",
            milestone_type="project_creation"
        )

        audit_logger.fail_milestone(
            milestone_id,
            error_message="Project creation failed"
        )

        # Should be removed from active milestones
        assert milestone_id not in audit_logger._active_milestones

    def test_get_journey_metrics(self, audit_logger):
        """Test getting journey metrics."""
        # Complete some milestones
        for i in range(5):
            mid = audit_logger.start_milestone(
                "session-1", f"Task {i}", "task_assignment"
            )
            time.sleep(0.01)
            audit_logger.complete_milestone(mid)

        # Fail some milestones
        for i in range(2):
            mid = audit_logger.start_milestone(
                "session-1", f"Failed {i}", "task_assignment"
            )
            audit_logger.fail_milestone(mid, "Error")

        # Get metrics
        metrics = audit_logger.get_journey_metrics(
            milestone_type="task_assignment"
        )

        assert metrics["total_milestones"] == 7
        assert metrics["completed"] == 5
        assert metrics["failed"] == 2
        assert metrics["completion_rate"] == pytest.approx(71.43, rel=0.1)
        assert metrics["avg_duration_seconds"] > 0
```

Run tests:
```bash
pytest tests/unit/mcp/test_journey_tracking.py -v
```

**Success Criteria**:
- ✅ Journey milestone tracking implemented
- ✅ Metrics calculation (completion rates, durations)
- ✅ Integration with project creation and task assignment
- ✅ All tests pass

---

### Tuesday: Research-Grade Event Logging

**What**: Add specialized event logging for MAS research (decision patterns, agent collaboration, timing analysis).

**Why**: Researchers need detailed data about multi-agent system behavior to study coordination, decision-making, and performance patterns (Issue #30).

**How**:

#### Step 2.1: Create research event logger

Create `src/research/event_logger.py`:

```python
"""
Research-grade event logging for MAS studies.

Captures detailed events for studying multi-agent system behavior.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ResearchEvent:
    """
    A research event.

    Attributes
    ----------
    event_id : str
        Unique event identifier
    event_type : str
        Type (agent_coordination, decision_point, etc.)
    timestamp : str
        ISO timestamp
    session_id : str
        Session identifier
    agent_id : str
        Agent involved (if applicable)
    task_id : str
        Task involved (if applicable)
    feature_id : str
        Feature involved (if applicable)
    event_data : dict
        Event-specific data
    """

    event_id: str
    event_type: str
    timestamp: str
    session_id: str
    agent_id: Optional[str]
    task_id: Optional[str]
    feature_id: Optional[str]
    event_data: Dict[str, Any]


class ResearchEventLogger:
    """
    Research-grade event logger.

    Captures events for studying MAS behavior:
    - Agent coordination patterns
    - Decision-making processes
    - Task assignment strategies
    - Performance metrics
    - Failure patterns
    """

    def __init__(self, log_dir: str = "data/research_logs"):
        """
        Initialize research event logger.

        Parameters
        ----------
        log_dir : str
            Directory for research logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.events_file = self.log_dir / "research_events.jsonl"

    def log_agent_coordination(
        self,
        session_id: str,
        agent_ids: List[str],
        coordination_type: str,
        tasks_involved: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log agent coordination event.

        Examples:
        - Multiple agents working on same feature
        - Agent handoff (one finishes, another picks up)
        - Parallel task execution

        Parameters
        ----------
        session_id : str
            Session ID
        agent_ids : list[str]
            Agents involved
        coordination_type : str
            Type (parallel, sequential, handoff)
        tasks_involved : list[str]
            Tasks being coordinated
        metadata : dict, optional
            Additional metadata
        """
        event = ResearchEvent(
            event_id=self._generate_event_id(),
            event_type="agent_coordination",
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            agent_id=None,  # Multiple agents
            task_id=None,  # Multiple tasks
            feature_id=None,
            event_data={
                "coordination_type": coordination_type,
                "agent_ids": agent_ids,
                "agent_count": len(agent_ids),
                "tasks_involved": tasks_involved,
                "task_count": len(tasks_involved),
                "metadata": metadata or {}
            }
        )

        self._write_event(event)

    def log_decision_point(
        self,
        session_id: str,
        agent_id: str,
        task_id: str,
        decision_type: str,
        options_considered: List[str],
        choice_made: str,
        reasoning: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log agent decision point.

        Captures decision-making process for analysis.

        Parameters
        ----------
        session_id : str
            Session ID
        agent_id : str
            Agent making decision
        task_id : str
            Task context
        decision_type : str
            Type (implementation_approach, tool_selection, etc.)
        options_considered : list[str]
            Options evaluated
        choice_made : str
            Final choice
        reasoning : str
            Why this choice
        confidence : float
            Confidence level (0-1)
        metadata : dict, optional
            Additional metadata
        """
        event = ResearchEvent(
            event_id=self._generate_event_id(),
            event_type="decision_point",
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            agent_id=agent_id,
            task_id=task_id,
            feature_id=None,
            event_data={
                "decision_type": decision_type,
                "options_considered": options_considered,
                "options_count": len(options_considered),
                "choice_made": choice_made,
                "reasoning": reasoning,
                "confidence": confidence,
                "metadata": metadata or {}
            }
        )

        self._write_event(event)

    def log_task_assignment(
        self,
        session_id: str,
        agent_id: str,
        task_id: str,
        feature_id: Optional[str],
        assignment_reason: str,
        agent_workload: int,
        alternative_agents: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log task assignment event.

        Captures why a task was assigned to a specific agent.

        Parameters
        ----------
        session_id : str
            Session ID
        agent_id : str
            Agent assigned
        task_id : str
            Task assigned
        feature_id : str, optional
            Feature context
        assignment_reason : str
            Why this agent
        agent_workload : int
            Current agent workload
        alternative_agents : list[str]
            Other agents considered
        metadata : dict, optional
            Additional metadata
        """
        event = ResearchEvent(
            event_id=self._generate_event_id(),
            event_type="task_assignment",
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            agent_id=agent_id,
            task_id=task_id,
            feature_id=feature_id,
            event_data={
                "assignment_reason": assignment_reason,
                "agent_workload": agent_workload,
                "alternative_agents": alternative_agents,
                "alternative_count": len(alternative_agents),
                "metadata": metadata or {}
            }
        )

        self._write_event(event)

    def log_performance_metric(
        self,
        session_id: str,
        metric_name: str,
        metric_value: float,
        metric_unit: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Log performance metric.

        Examples:
        - Task completion time
        - Agent throughput
        - Context switching frequency

        Parameters
        ----------
        session_id : str
            Session ID
        metric_name : str
            Metric name
        metric_value : float
            Metric value
        metric_unit : str
            Unit (seconds, tasks/hour, etc.)
        context : dict
            Context for metric
        """
        event = ResearchEvent(
            event_id=self._generate_event_id(),
            event_type="performance_metric",
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            agent_id=context.get("agent_id"),
            task_id=context.get("task_id"),
            feature_id=context.get("feature_id"),
            event_data={
                "metric_name": metric_name,
                "metric_value": metric_value,
                "metric_unit": metric_unit,
                "context": context
            }
        )

        self._write_event(event)

    def log_failure_event(
        self,
        session_id: str,
        failure_type: str,
        component: str,
        error_message: str,
        context: Dict[str, Any],
        recovery_attempted: bool,
        recovery_successful: bool
    ) -> None:
        """
        Log failure event.

        Captures failures for reliability analysis.

        Parameters
        ----------
        session_id : str
            Session ID
        failure_type : str
            Type (workspace_creation, git_operation, etc.)
        component : str
            Component that failed
        error_message : str
            Error message
        context : dict
            Failure context
        recovery_attempted : bool
            Whether recovery was attempted
        recovery_successful : bool
            Whether recovery succeeded
        """
        event = ResearchEvent(
            event_id=self._generate_event_id(),
            event_type="failure_event",
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            agent_id=context.get("agent_id"),
            task_id=context.get("task_id"),
            feature_id=context.get("feature_id"),
            event_data={
                "failure_type": failure_type,
                "component": component,
                "error_message": error_message,
                "recovery_attempted": recovery_attempted,
                "recovery_successful": recovery_successful,
                "context": context
            }
        )

        self._write_event(event)

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        return f"evt_{datetime.now(timezone.utc).timestamp()}"

    def _write_event(self, event: ResearchEvent) -> None:
        """Write event to log file."""
        with open(self.events_file, "a") as f:
            f.write(json.dumps(asdict(event)) + "\n")

        logger.debug(f"Logged research event: {event.event_type}")

    def query_events(
        self,
        event_type: Optional[str] = None,
        agent_id: Optional[str] = None,
        hours: int = 24
    ) -> List[ResearchEvent]:
        """
        Query research events.

        Parameters
        ----------
        event_type : str, optional
            Filter by event type
        agent_id : str, optional
            Filter by agent
        hours : int
            Look back this many hours

        Returns
        -------
        list[ResearchEvent]
            Matching events
        """
        if not self.events_file.exists():
            return []

        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)

        events = []
        with open(self.events_file) as f:
            for line in f:
                event_dict = json.loads(line)

                # Filter by time
                event_time = datetime.fromisoformat(event_dict["timestamp"]).timestamp()
                if event_time < cutoff_time:
                    continue

                # Filter by type
                if event_type and event_dict["event_type"] != event_type:
                    continue

                # Filter by agent
                if agent_id and event_dict.get("agent_id") != agent_id:
                    continue

                events.append(ResearchEvent(**event_dict))

        return events
```

#### Step 2.2: Integrate with existing operations

Update `src/marcus_mcp/tools/task.py` to log research events:

```python
from src.research.event_logger import ResearchEventLogger

async def request_next_task(agent_id: str, state: Any) -> Any:
    """Request next task with research logging."""

    # ... existing task finding logic ...

    # Log task assignment event for research
    if hasattr(state, "research_logger"):
        state.research_logger.log_task_assignment(
            session_id=state.session_id,
            agent_id=agent_id,
            task_id=optimal_task.id,
            feature_id=optimal_task.feature_id,
            assignment_reason="Optimal task for agent skills",
            agent_workload=len(state.get_agent_assignments(agent_id)),
            alternative_agents=[a.id for a in state.get_available_agents() if a.id != agent_id]
        )

    # ... rest of function ...
```

#### Step 2.3: Write tests

Create `tests/unit/research/test_event_logger.py`:

```python
"""
Tests for research event logger.
"""

import pytest
from pathlib import Path

from src.research.event_logger import ResearchEventLogger


class TestResearchEventLogger:
    """Test research event logger"""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create research event logger."""
        return ResearchEventLogger(log_dir=str(tmp_path / "research"))

    def test_log_agent_coordination(self, logger):
        """Test logging agent coordination."""
        logger.log_agent_coordination(
            session_id="session-1",
            agent_ids=["agent-1", "agent-2"],
            coordination_type="parallel",
            tasks_involved=["T-1", "T-2"]
        )

        assert logger.events_file.exists()

        # Query events
        events = logger.query_events(event_type="agent_coordination")
        assert len(events) == 1
        assert events[0].event_data["agent_count"] == 2

    def test_log_decision_point(self, logger):
        """Test logging decision point."""
        logger.log_decision_point(
            session_id="session-1",
            agent_id="agent-1",
            task_id="T-1",
            decision_type="implementation_approach",
            options_considered=["REST API", "GraphQL", "gRPC"],
            choice_made="REST API",
            reasoning="Simpler for MVP",
            confidence=0.8
        )

        events = logger.query_events(event_type="decision_point")
        assert len(events) == 1
        assert events[0].event_data["choice_made"] == "REST API"
        assert events[0].event_data["confidence"] == 0.8

    def test_query_events_by_agent(self, logger):
        """Test querying events by agent."""
        # Log events for different agents
        logger.log_task_assignment(
            "session-1", "agent-1", "T-1", "F-100",
            "Best match", 1, ["agent-2"]
        )
        logger.log_task_assignment(
            "session-1", "agent-2", "T-2", "F-100",
            "Available", 0, ["agent-1"]
        )

        # Query agent-1 events
        agent1_events = logger.query_events(agent_id="agent-1")
        assert len(agent1_events) == 1
        assert agent1_events[0].agent_id == "agent-1"
```

Run tests:
```bash
pytest tests/unit/research/test_event_logger.py -v
```

**Success Criteria**:
- ✅ Research event logger implemented
- ✅ Multiple event types (coordination, decisions, performance, failures)
- ✅ Query interface for analysis
- ✅ Integration with task operations
- ✅ All tests pass

---

### **Wednesday: CATO Dashboard Integration API**

**Goal**: Create API endpoints for CATO dashboard to consume Marcus telemetry and state data.

**Background**: CATO (Coordinated Agent Task Observatory) is Marcus's real-time visualization dashboard. It needs access to:
- Current agent states and task assignments
- Project and feature status
- Real-time event stream
- Historical metrics

#### **Step 1: Create CATO API Routes**

Create `src/api/cato_routes.py`:

```python
"""
CATO Dashboard API Routes.

Provides endpoints for CATO to consume Marcus state and telemetry.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.core.error_framework import ErrorContext, MarcusBaseError
from src.marcus_mcp.audit import AuditLogger
from src.research.event_logger import ResearchEventLogger

router = APIRouter(prefix="/api/cato", tags=["cato"])


@router.get("/snapshot")
async def get_system_snapshot() -> Dict[str, Any]:
    """
    Get current system snapshot for CATO network graph.

    Returns complete state of agents, tasks, projects, and features
    for visualization.

    Returns
    -------
    Dict[str, Any]
        System snapshot with nodes (agents, tasks, projects, features)
        and edges (dependencies, assignments, relationships).

    Examples
    --------
    >>> response = await get_system_snapshot()
    >>> print(response["nodes"]["agents"])
    [{"id": "agent-1", "name": "Builder", "status": "active", ...}]
    """
    try:
        from src.state.manager import get_state_manager

        state = get_state_manager()

        # Build nodes
        nodes = {
            "agents": _serialize_agents(state.agents),
            "tasks": _serialize_tasks(state.tasks),
            "projects": _serialize_projects(state.projects),
            "features": _serialize_features(state.features),
        }

        # Build edges
        edges = {
            "task_dependencies": _get_task_dependencies(state.tasks),
            "agent_assignments": _get_agent_assignments(state.agents, state.tasks),
            "feature_tasks": _get_feature_tasks(state.features),
            "project_features": _get_project_features(state.projects, state.features),
        }

        # Get metrics
        metrics = {
            "total_agents": len(state.agents),
            "active_agents": sum(1 for a in state.agents.values() if a.status == "active"),
            "total_tasks": len(state.tasks),
            "completed_tasks": sum(1 for t in state.tasks.values() if t.status == "completed"),
            "total_projects": len(state.projects),
            "total_features": len(state.features),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "success": True,
            "snapshot": {
                "nodes": nodes,
                "edges": edges,
                "metrics": metrics,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate snapshot: {str(e)}",
        )


@router.get("/events/stream")
async def stream_events(
    event_types: Optional[List[str]] = Query(None),
    since: Optional[str] = Query(None),
) -> StreamingResponse:
    """
    Stream real-time events to CATO dashboard.

    Parameters
    ----------
    event_types : Optional[List[str]]
        Filter by event types (e.g., ["task_assigned", "task_completed"]).
    since : Optional[str]
        ISO timestamp - only return events after this time.

    Returns
    -------
    StreamingResponse
        Server-sent events stream.

    Examples
    --------
    Client-side (JavaScript):
    ```javascript
    const eventSource = new EventSource('/api/cato/events/stream');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Event:', data);
    };
    ```
    """
    import asyncio
    import json

    async def event_generator():
        """Generate server-sent events."""
        audit_logger = AuditLogger()
        last_event_time = datetime.fromisoformat(since) if since else None

        while True:
            try:
                # Get recent events
                events = audit_logger.get_recent_events(
                    event_types=event_types,
                    since=last_event_time,
                    limit=50,
                )

                # Send events
                for event in events:
                    yield f"data: {json.dumps(event)}\n\n"
                    last_event_time = datetime.fromisoformat(event["timestamp"])

                # Keep connection alive
                await asyncio.sleep(1)

            except Exception as e:
                # Send error event
                error_event = {
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/metrics/journey")
async def get_journey_metrics(
    milestone_type: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
) -> Dict[str, Any]:
    """
    Get user journey metrics.

    Parameters
    ----------
    milestone_type : Optional[str]
        Filter by milestone type (e.g., "project_creation", "task_assignment").
    hours : int
        Look back period in hours (default: 24, max: 168).

    Returns
    -------
    Dict[str, Any]
        Journey metrics including completion rates, durations, and bottlenecks.

    Examples
    --------
    >>> metrics = await get_journey_metrics(milestone_type="project_creation")
    >>> print(metrics["completion_rate"])
    0.85
    """
    try:
        audit_logger = AuditLogger()
        metrics = audit_logger.get_journey_metrics(
            milestone_type=milestone_type,
            hours=hours,
        )

        return {
            "success": True,
            "metrics": metrics,
            "period_hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get journey metrics: {str(e)}",
        )


@router.get("/metrics/research")
async def get_research_metrics(
    event_type: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
) -> Dict[str, Any]:
    """
    Get research-grade metrics for MAS studies.

    Parameters
    ----------
    event_type : Optional[str]
        Filter by event type.
    agent_id : Optional[str]
        Filter by agent ID.
    hours : int
        Look back period in hours.

    Returns
    -------
    Dict[str, Any]
        Research metrics including agent coordination patterns,
        decision quality, and performance data.

    Examples
    --------
    >>> metrics = await get_research_metrics(event_type="agent_coordination")
    >>> print(metrics["coordination_patterns"])
    {"parallel": 45, "sequential": 23, "handoff": 12}
    """
    try:
        research_logger = ResearchEventLogger()
        events = research_logger.query_events(
            event_type=event_type,
            agent_id=agent_id,
            hours=hours,
        )

        # Aggregate metrics
        metrics = _aggregate_research_metrics(events)

        return {
            "success": True,
            "metrics": metrics,
            "event_count": len(events),
            "period_hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get research metrics: {str(e)}",
        )


@router.get("/agent/{agent_id}")
async def get_agent_detail(agent_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific agent.

    Parameters
    ----------
    agent_id : str
        The agent ID.

    Returns
    -------
    Dict[str, Any]
        Agent details including current task, history, and performance.

    Examples
    --------
    >>> detail = await get_agent_detail("agent-1")
    >>> print(detail["current_task"])
    "T-123"
    """
    try:
        from src.state.manager import get_state_manager

        state = get_state_manager()

        if agent_id not in state.agents:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        agent = state.agents[agent_id]
        research_logger = ResearchEventLogger()

        # Get agent events
        agent_events = research_logger.query_events(agent_id=agent_id, hours=24)

        # Get current task
        current_task = None
        if agent.current_task_id:
            current_task = state.tasks.get(agent.current_task_id)

        # Get task history
        task_history = [
            state.tasks.get(task_id)
            for task_id in agent.task_history[-10:]
            if task_id in state.tasks
        ]

        return {
            "success": True,
            "agent": _serialize_agent(agent),
            "current_task": _serialize_task(current_task) if current_task else None,
            "task_history": [_serialize_task(t) for t in task_history],
            "recent_events": [_serialize_event(e) for e in agent_events[-20:]],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agent detail: {str(e)}",
        )


# Helper functions

def _serialize_agents(agents: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Serialize agents for CATO."""
    return [_serialize_agent(agent) for agent in agents.values()]


def _serialize_agent(agent: Any) -> Dict[str, Any]:
    """Serialize single agent."""
    return {
        "id": agent.agent_id,
        "name": agent.name,
        "role": agent.role,
        "status": agent.status,
        "skills": agent.skills,
        "current_task_id": agent.current_task_id,
        "task_count": len(agent.task_history),
    }


def _serialize_tasks(tasks: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Serialize tasks for CATO."""
    return [_serialize_task(task) for task in tasks.values()]


def _serialize_task(task: Any) -> Dict[str, Any]:
    """Serialize single task."""
    return {
        "id": task.id,
        "name": task.name,
        "status": task.status.value,
        "priority": task.priority.value,
        "assigned_to": task.assigned_to,
        "dependencies": task.dependencies,
        "estimated_hours": task.estimated_hours,
        "feature_id": task.source_context.get("feature_id"),
    }


def _serialize_projects(projects: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Serialize projects for CATO."""
    return [
        {
            "id": project.project_id,
            "name": project.name,
            "status": project.status,
            "task_count": len(project.task_ids),
        }
        for project in projects.values()
    ]


def _serialize_features(features: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Serialize features for CATO."""
    return [
        {
            "id": feature.feature_id,
            "name": feature.name,
            "status": feature.status,
            "task_count": len(feature.task_ids),
            "project_id": feature.project_id,
        }
        for feature in features.values()
    ]


def _serialize_event(event: Any) -> Dict[str, Any]:
    """Serialize research event."""
    return {
        "id": event.event_id,
        "type": event.event_type,
        "timestamp": event.timestamp,
        "agent_id": event.agent_id,
        "task_id": event.task_id,
        "data": event.event_data,
    }


def _get_task_dependencies(tasks: Dict[str, Any]) -> List[Dict[str, str]]:
    """Get task dependency edges."""
    edges = []
    for task in tasks.values():
        for dep_id in task.dependencies:
            edges.append({"from": dep_id, "to": task.id, "type": "dependency"})
    return edges


def _get_agent_assignments(
    agents: Dict[str, Any], tasks: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Get agent-task assignment edges."""
    edges = []
    for task in tasks.values():
        if task.assigned_to:
            edges.append(
                {"from": task.assigned_to, "to": task.id, "type": "assignment"}
            )
    return edges


def _get_feature_tasks(features: Dict[str, Any]) -> List[Dict[str, str]]:
    """Get feature-task edges."""
    edges = []
    for feature in features.values():
        for task_id in feature.task_ids:
            edges.append({"from": feature.feature_id, "to": task_id, "type": "contains"})
    return edges


def _get_project_features(
    projects: Dict[str, Any], features: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Get project-feature edges."""
    edges = []
    for feature in features.values():
        edges.append(
            {"from": feature.project_id, "to": feature.feature_id, "type": "contains"}
        )
    return edges


def _aggregate_research_metrics(events: List[Any]) -> Dict[str, Any]:
    """Aggregate research metrics from events."""
    metrics = {
        "total_events": len(events),
        "event_types": {},
        "coordination_patterns": {"parallel": 0, "sequential": 0, "handoff": 0},
        "decision_quality": {"high_confidence": 0, "medium_confidence": 0, "low_confidence": 0},
        "performance": {"avg_task_completion_time": 0.0, "throughput": 0},
    }

    # Count event types
    for event in events:
        event_type = event.event_type
        metrics["event_types"][event_type] = metrics["event_types"].get(event_type, 0) + 1

        # Aggregate coordination patterns
        if event_type == "agent_coordination":
            coord_type = event.event_data.get("coordination_type", "")
            if coord_type in metrics["coordination_patterns"]:
                metrics["coordination_patterns"][coord_type] += 1

        # Aggregate decision quality
        if event_type == "decision_point":
            confidence = event.event_data.get("confidence", 0.0)
            if confidence >= 0.8:
                metrics["decision_quality"]["high_confidence"] += 1
            elif confidence >= 0.5:
                metrics["decision_quality"]["medium_confidence"] += 1
            else:
                metrics["decision_quality"]["low_confidence"] += 1

        # Aggregate performance
        if event_type == "performance_metric":
            metric_name = event.event_data.get("metric_name", "")
            if metric_name == "task_completion_time":
                metrics["performance"]["avg_task_completion_time"] += event.event_data.get(
                    "metric_value", 0.0
                )
            elif metric_name == "throughput":
                metrics["performance"]["throughput"] += 1

    # Calculate averages
    if metrics["performance"]["avg_task_completion_time"] > 0:
        task_count = metrics["event_types"].get("performance_metric", 1)
        metrics["performance"]["avg_task_completion_time"] /= task_count

    return metrics
```

#### **Step 2: Register CATO Routes**

Update `src/api/main.py` to include CATO routes:

```python
"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.cato_routes import router as cato_router

app = FastAPI(title="Marcus API", version="0.1.0")

# Enable CORS for CATO dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # CATO dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(cato_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
```

#### **Step 3: Create Unit Tests**

Create `tests/unit/api/test_cato_routes.py`:

```python
"""
Unit tests for CATO API routes.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


class TestCATORoutes:
    """Test CATO API routes"""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_state(self):
        """Create mock state manager."""
        from src.core.models import Agent, Priority, Task, TaskStatus

        # Create mock agents
        agent1 = Agent(
            agent_id="agent-1",
            name="Builder",
            role="developer",
            status="active",
            skills=["python", "api"],
            current_task_id="T-1",
            task_history=["T-1"],
        )

        # Create mock tasks
        task1 = Task(
            id="T-1",
            name="Implement API",
            description="Create API endpoints",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            assigned_to="agent-1",
            dependencies=[],
            estimated_hours=4.0,
            source_context={"feature_id": "F-100"},
        )

        # Create mock state
        state = Mock()
        state.agents = {"agent-1": agent1}
        state.tasks = {"T-1": task1}
        state.projects = {}
        state.features = {}

        return state

    @patch("src.api.cato_routes.get_state_manager")
    def test_get_system_snapshot(self, mock_get_state, client, mock_state):
        """Test getting system snapshot."""
        mock_get_state.return_value = mock_state

        response = client.get("/api/cato/snapshot")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "snapshot" in data
        assert "nodes" in data["snapshot"]
        assert "edges" in data["snapshot"]
        assert "metrics" in data["snapshot"]

        # Check nodes
        nodes = data["snapshot"]["nodes"]
        assert len(nodes["agents"]) == 1
        assert nodes["agents"][0]["id"] == "agent-1"
        assert len(nodes["tasks"]) == 1
        assert nodes["tasks"][0]["id"] == "T-1"

        # Check metrics
        metrics = data["snapshot"]["metrics"]
        assert metrics["total_agents"] == 1
        assert metrics["active_agents"] == 1
        assert metrics["total_tasks"] == 1

    @patch("src.api.cato_routes.AuditLogger")
    def test_get_journey_metrics(self, mock_audit_class, client):
        """Test getting journey metrics."""
        mock_audit = Mock()
        mock_audit.get_journey_metrics.return_value = {
            "total_milestones": 100,
            "completed": 85,
            "failed": 5,
            "in_progress": 10,
            "completion_rate": 0.85,
            "avg_duration_seconds": 45.2,
        }
        mock_audit_class.return_value = mock_audit

        response = client.get("/api/cato/metrics/journey?milestone_type=project_creation")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metrics"]["completion_rate"] == 0.85
        assert data["metrics"]["total_milestones"] == 100

    @patch("src.api.cato_routes.ResearchEventLogger")
    def test_get_research_metrics(self, mock_logger_class, client):
        """Test getting research metrics."""
        from src.research.event_logger import ResearchEvent

        # Create mock events
        events = [
            ResearchEvent(
                event_id="evt-1",
                event_type="agent_coordination",
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id="session-1",
                agent_id="agent-1",
                task_id="T-1",
                feature_id="F-100",
                event_data={"coordination_type": "parallel", "agent_count": 2},
            ),
            ResearchEvent(
                event_id="evt-2",
                event_type="decision_point",
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id="session-1",
                agent_id="agent-1",
                task_id="T-1",
                feature_id="F-100",
                event_data={
                    "decision_type": "implementation",
                    "confidence": 0.9,
                    "choice_made": "REST API",
                },
            ),
        ]

        mock_logger = Mock()
        mock_logger.query_events.return_value = events
        mock_logger_class.return_value = mock_logger

        response = client.get("/api/cato/metrics/research?event_type=agent_coordination")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["event_count"] == 2
        assert "metrics" in data

    @patch("src.api.cato_routes.get_state_manager")
    @patch("src.api.cato_routes.ResearchEventLogger")
    def test_get_agent_detail(
        self, mock_logger_class, mock_get_state, client, mock_state
    ):
        """Test getting agent detail."""
        mock_get_state.return_value = mock_state
        mock_logger = Mock()
        mock_logger.query_events.return_value = []
        mock_logger_class.return_value = mock_logger

        response = client.get("/api/cato/agent/agent-1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["agent"]["id"] == "agent-1"
        assert data["agent"]["name"] == "Builder"
        assert data["current_task"]["id"] == "T-1"

    @patch("src.api.cato_routes.get_state_manager")
    def test_get_agent_detail_not_found(self, mock_get_state, client, mock_state):
        """Test getting agent detail for non-existent agent."""
        mock_get_state.return_value = mock_state

        response = client.get("/api/cato/agent/agent-999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

Run tests:
```bash
pytest tests/unit/api/test_cato_routes.py -v
```

#### **Step 4: Create Integration Tests**

Create `tests/integration/api/test_cato_integration.py`:

```python
"""
Integration tests for CATO API with real state.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.models import Agent, Priority, Task, TaskStatus
from src.state.manager import StateManager


class TestCATOIntegration:
    """Integration tests for CATO API"""

    @pytest.fixture
    def state(self):
        """Create state manager with test data."""
        state = StateManager()

        # Create test agent
        agent = Agent(
            agent_id="test-agent-1",
            name="Test Builder",
            role="developer",
            status="active",
            skills=["python", "testing"],
            current_task_id=None,
            task_history=[],
        )
        state.agents[agent.agent_id] = agent

        # Create test task
        task = Task(
            id="test-task-1",
            name="Test Task",
            description="Integration test task",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            dependencies=[],
            estimated_hours=2.0,
            source_context={},
        )
        state.tasks[task.id] = task

        return state

    @pytest.fixture
    def client(self, state):
        """Create test client with state."""
        # Inject state into app
        from src.api.cato_routes import get_state_manager

        app.dependency_overrides[get_state_manager] = lambda: state

        client = TestClient(app)
        yield client

        # Cleanup
        app.dependency_overrides.clear()

    @pytest.mark.integration
    def test_snapshot_with_real_state(self, client):
        """Test snapshot endpoint with real state."""
        response = client.get("/api/cato/snapshot")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify snapshot contains real data
        snapshot = data["snapshot"]
        assert len(snapshot["nodes"]["agents"]) == 1
        assert snapshot["nodes"]["agents"][0]["id"] == "test-agent-1"
        assert len(snapshot["nodes"]["tasks"]) == 1
        assert snapshot["nodes"]["tasks"][0]["id"] == "test-task-1"

    @pytest.mark.integration
    def test_agent_detail_with_real_state(self, client):
        """Test agent detail endpoint with real state."""
        response = client.get("/api/cato/agent/test-agent-1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["agent"]["id"] == "test-agent-1"
        assert data["agent"]["name"] == "Test Builder"
```

Run integration tests:
```bash
pytest tests/integration/api/test_cato_integration.py -v
```

#### **Step 5: Test Event Streaming**

Create test for SSE (Server-Sent Events):

```python
# Add to tests/integration/api/test_cato_integration.py

@pytest.mark.integration
def test_event_stream(self, client):
    """Test event stream endpoint."""
    # Note: Testing SSE requires special handling
    # This is a basic connectivity test
    response = client.get("/api/cato/events/stream")

    # Should return 200 and start streaming
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
```

**Success Criteria**:
- ✅ CATO API routes created (/snapshot, /events/stream, /metrics/journey, /metrics/research, /agent/{id})
- ✅ CORS enabled for CATO dashboard
- ✅ Server-sent events for real-time updates
- ✅ All unit tests pass
- ✅ Integration tests pass with real state

---

### **Thursday: CATO Real-time Updates**

**Goal**: Implement real-time event broadcasting to CATO dashboard when system state changes.

**Background**: CATO needs to receive updates immediately when:
- Agents are assigned tasks
- Tasks change status
- Features progress
- Errors occur

We'll use a pub-sub pattern to broadcast events.

#### **Step 1: Create Event Broadcaster**

Create `src/events/broadcaster.py`:

```python
"""
Event broadcaster for real-time updates.

Implements pub-sub pattern for broadcasting system events to subscribers
like the CATO dashboard.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from src.core.error_framework import ErrorContext, MarcusBaseError


class EventBroadcaster:
    """
    Broadcasts system events to subscribers.

    Uses asyncio queues for async event distribution to multiple subscribers.
    Thread-safe and supports event filtering by type.

    Examples
    --------
    >>> broadcaster = EventBroadcaster()
    >>> await broadcaster.broadcast("task_assigned", {"task_id": "T-1", "agent_id": "agent-1"})
    """

    def __init__(self):
        """Initialize event broadcaster."""
        self._subscribers: Dict[str, asyncio.Queue] = {}
        self._event_types: Dict[str, Set[str]] = {}  # subscriber_id -> event_types
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        subscriber_id: str,
        event_types: Optional[List[str]] = None,
    ) -> asyncio.Queue:
        """
        Subscribe to events.

        Parameters
        ----------
        subscriber_id : str
            Unique identifier for subscriber.
        event_types : Optional[List[str]]
            Filter by event types. If None, receive all events.

        Returns
        -------
        asyncio.Queue
            Queue to receive events from.

        Examples
        --------
        >>> queue = await broadcaster.subscribe("cato-1", ["task_assigned", "task_completed"])
        >>> while True:
        ...     event = await queue.get()
        ...     print(f"Received: {event}")
        """
        async with self._lock:
            queue = asyncio.Queue(maxsize=100)
            self._subscribers[subscriber_id] = queue

            if event_types:
                self._event_types[subscriber_id] = set(event_types)
            else:
                self._event_types[subscriber_id] = set()

            return queue

    async def unsubscribe(self, subscriber_id: str) -> None:
        """
        Unsubscribe from events.

        Parameters
        ----------
        subscriber_id : str
            Subscriber to remove.

        Examples
        --------
        >>> await broadcaster.unsubscribe("cato-1")
        """
        async with self._lock:
            if subscriber_id in self._subscribers:
                del self._subscribers[subscriber_id]
            if subscriber_id in self._event_types:
                del self._event_types[subscriber_id]

    async def broadcast(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Broadcast event to all subscribers.

        Parameters
        ----------
        event_type : str
            Type of event (e.g., "task_assigned", "agent_registered").
        event_data : Dict[str, Any]
            Event payload.
        metadata : Optional[Dict[str, Any]]
            Additional metadata (e.g., priority, source).

        Examples
        --------
        >>> await broadcaster.broadcast(
        ...     "task_assigned",
        ...     {"task_id": "T-1", "agent_id": "agent-1"},
        ...     {"priority": "high"}
        ... )
        """
        event = {
            "event_type": event_type,
            "event_data": event_data,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        async with self._lock:
            # Send to relevant subscribers
            for subscriber_id, queue in self._subscribers.items():
                # Check if subscriber wants this event type
                event_filter = self._event_types.get(subscriber_id, set())
                if event_filter and event_type not in event_filter:
                    continue

                # Try to send (don't block on full queues)
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Log dropped event
                    print(
                        f"Warning: Queue full for subscriber {subscriber_id}, "
                        f"dropped event {event_type}"
                    )

    def get_subscriber_count(self) -> int:
        """Get number of active subscribers."""
        return len(self._subscribers)

    def get_subscribers(self) -> List[str]:
        """Get list of subscriber IDs."""
        return list(self._subscribers.keys())


# Global broadcaster instance
_broadcaster: Optional[EventBroadcaster] = None


def get_broadcaster() -> EventBroadcaster:
    """
    Get global event broadcaster instance.

    Returns
    -------
    EventBroadcaster
        Global broadcaster instance.

    Examples
    --------
    >>> broadcaster = get_broadcaster()
    >>> await broadcaster.broadcast("task_completed", {"task_id": "T-1"})
    """
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = EventBroadcaster()
    return _broadcaster
```

#### **Step 2: Integrate with Task Operations**

Update `src/marcus_mcp/tools/core.py` to broadcast events:

```python
"""Core MCP tools with event broadcasting."""

from src.events.broadcaster import get_broadcaster


async def register_agent(
    agent_id: str,
    name: str,
    role: str,
    skills: List[str] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """Register agent and broadcast event."""
    # Existing registration logic
    agent = Agent(
        agent_id=agent_id,
        name=name,
        role=role,
        skills=skills or [],
        status="active",
        current_task_id=None,
        task_history=[],
    )
    state.agents[agent_id] = agent

    # Broadcast event
    broadcaster = get_broadcaster()
    await broadcaster.broadcast(
        "agent_registered",
        {
            "agent_id": agent_id,
            "name": name,
            "role": role,
            "skills": skills or [],
        },
        {"source": "mcp_tool"},
    )

    return {"success": True, "agent_id": agent_id, "message": f"Agent {name} registered"}


async def request_next_task(
    agent_id: str,
    state: Any = None,
) -> Dict[str, Any]:
    """Request next task and broadcast assignment."""
    # Existing task assignment logic
    task = _find_next_task(agent_id, state)

    if not task:
        return {"success": False, "message": "No tasks available"}

    # Assign task
    task.assigned_to = agent_id
    task.status = TaskStatus.IN_PROGRESS
    agent = state.agents[agent_id]
    agent.current_task_id = task.id

    # Broadcast event
    broadcaster = get_broadcaster()
    await broadcaster.broadcast(
        "task_assigned",
        {
            "task_id": task.id,
            "task_name": task.name,
            "agent_id": agent_id,
            "agent_name": agent.name,
        },
        {"priority": task.priority.value},
    )

    return {
        "success": True,
        "task": {
            "id": task.id,
            "name": task.name,
            "description": task.description,
        },
    }


async def report_task_progress(
    agent_id: str,
    task_id: str,
    status: str,
    progress: int = 0,
    message: str = "",
    state: Any = None,
) -> Dict[str, Any]:
    """Report task progress and broadcast update."""
    # Existing progress reporting logic
    task = state.tasks.get(task_id)
    if not task:
        return {"success": False, "message": f"Task {task_id} not found"}

    old_status = task.status
    task.status = TaskStatus(status)

    # Broadcast event
    broadcaster = get_broadcaster()
    await broadcaster.broadcast(
        "task_progress",
        {
            "task_id": task_id,
            "task_name": task.name,
            "agent_id": agent_id,
            "old_status": old_status.value,
            "new_status": status,
            "progress": progress,
            "message": message,
        },
        {"priority": task.priority.value},
    )

    # If completed, broadcast completion event
    if status == "completed":
        agent = state.agents[agent_id]
        agent.current_task_id = None
        agent.task_history.append(task_id)

        await broadcaster.broadcast(
            "task_completed",
            {
                "task_id": task_id,
                "task_name": task.name,
                "agent_id": agent_id,
                "agent_name": agent.name,
            },
            {"priority": task.priority.value, "duration": task.estimated_hours},
        )

    return {"success": True, "message": f"Progress updated for {task_id}"}
```

#### **Step 3: Update SSE Endpoint**

Update `src/api/cato_routes.py` to use broadcaster:

```python
"""CATO routes with event broadcaster integration."""

from src.events.broadcaster import get_broadcaster


@router.get("/events/stream")
async def stream_events(
    event_types: Optional[List[str]] = Query(None),
) -> StreamingResponse:
    """
    Stream real-time events using event broadcaster.

    Parameters
    ----------
    event_types : Optional[List[str]]
        Filter by event types.

    Returns
    -------
    StreamingResponse
        Server-sent events stream.
    """
    import uuid

    subscriber_id = f"cato-{uuid.uuid4().hex[:8]}"

    async def event_generator():
        """Generate server-sent events from broadcaster."""
        broadcaster = get_broadcaster()

        try:
            # Subscribe to events
            queue = await broadcaster.subscribe(subscriber_id, event_types)

            # Send connection established event
            yield f"data: {json.dumps({'type': 'connected', 'subscriber_id': subscriber_id})}\n\n"

            # Stream events
            while True:
                try:
                    # Wait for event with timeout (for keep-alive)
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"

                except asyncio.TimeoutError:
                    # Send keep-alive
                    yield f": keep-alive\n\n"

        except asyncio.CancelledError:
            # Client disconnected
            await broadcaster.unsubscribe(subscriber_id)
            raise

        except Exception as e:
            # Send error and cleanup
            error_event = {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            await broadcaster.unsubscribe(subscriber_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/events/subscribers")
async def get_subscribers() -> Dict[str, Any]:
    """Get list of active subscribers (for monitoring)."""
    broadcaster = get_broadcaster()

    return {
        "success": True,
        "subscriber_count": broadcaster.get_subscriber_count(),
        "subscribers": broadcaster.get_subscribers(),
    }
```

#### **Step 4: Create Tests**

Create `tests/unit/events/test_broadcaster.py`:

```python
"""
Unit tests for event broadcaster.
"""

import asyncio

import pytest

from src.events.broadcaster import EventBroadcaster


class TestEventBroadcaster:
    """Test event broadcaster"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_subscribe_and_broadcast(self):
        """Test subscribing and receiving events."""
        broadcaster = EventBroadcaster()

        # Subscribe
        queue = await broadcaster.subscribe("sub-1")

        # Broadcast event
        await broadcaster.broadcast(
            "test_event",
            {"message": "Hello"},
        )

        # Receive event
        event = await asyncio.wait_for(queue.get(), timeout=1.0)

        assert event["event_type"] == "test_event"
        assert event["event_data"]["message"] == "Hello"
        assert "timestamp" in event

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_event_filtering(self):
        """Test event type filtering."""
        broadcaster = EventBroadcaster()

        # Subscribe with filter
        queue = await broadcaster.subscribe("sub-1", ["task_assigned"])

        # Broadcast filtered event
        await broadcaster.broadcast("task_assigned", {"task_id": "T-1"})

        # Broadcast unfiltered event
        await broadcaster.broadcast("agent_registered", {"agent_id": "A-1"})

        # Should only receive filtered event
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["event_type"] == "task_assigned"

        # Queue should be empty
        assert queue.empty()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Test broadcasting to multiple subscribers."""
        broadcaster = EventBroadcaster()

        # Subscribe multiple
        queue1 = await broadcaster.subscribe("sub-1")
        queue2 = await broadcaster.subscribe("sub-2")

        # Broadcast
        await broadcaster.broadcast("test_event", {"data": "test"})

        # Both should receive
        event1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        event2 = await asyncio.wait_for(queue2.get(), timeout=1.0)

        assert event1["event_type"] == "test_event"
        assert event2["event_type"] == "test_event"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribing from events."""
        broadcaster = EventBroadcaster()

        # Subscribe
        queue = await broadcaster.subscribe("sub-1")
        assert broadcaster.get_subscriber_count() == 1

        # Unsubscribe
        await broadcaster.unsubscribe("sub-1")
        assert broadcaster.get_subscriber_count() == 0

        # Broadcast (should not crash)
        await broadcaster.broadcast("test_event", {})

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_queue_full_handling(self):
        """Test handling of full queue."""
        broadcaster = EventBroadcaster()

        # Subscribe
        queue = await broadcaster.subscribe("sub-1")

        # Fill queue (maxsize=100)
        for i in range(101):
            await broadcaster.broadcast("test_event", {"index": i})

        # Should have 100 events (1 dropped)
        assert queue.qsize() == 100
```

Run tests:
```bash
pytest tests/unit/events/test_broadcaster.py -v
```

#### **Step 5: Create Integration Test**

Create `tests/integration/e2e/test_realtime_updates.py`:

```python
"""
Integration test for real-time updates to CATO.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.events.broadcaster import get_broadcaster


class TestRealtimeUpdates:
    """Test real-time updates integration"""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_task_assignment_broadcasts_event(self):
        """Test that task assignment triggers broadcast."""
        from src.marcus_mcp.tools.core import register_agent, request_next_task
        from src.state.manager import StateManager

        state = StateManager()
        broadcaster = get_broadcaster()

        # Subscribe to events
        queue = await broadcaster.subscribe("test-sub", ["task_assigned"])

        # Register agent
        await register_agent("agent-1", "Test Agent", "developer", state=state)

        # Create and assign task (simplified)
        from src.core.models import Priority, Task, TaskStatus

        task = Task(
            id="T-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            dependencies=[],
            estimated_hours=2.0,
            source_context={},
        )
        state.tasks[task.id] = task

        # Request task
        await request_next_task("agent-1", state=state)

        # Should receive broadcast
        event = await asyncio.wait_for(queue.get(), timeout=2.0)

        assert event["event_type"] == "task_assigned"
        assert event["event_data"]["task_id"] == "T-1"
        assert event["event_data"]["agent_id"] == "agent-1"

        # Cleanup
        await broadcaster.unsubscribe("test-sub")
```

Run integration test:
```bash
pytest tests/integration/e2e/test_realtime_updates.py -v
```

**Success Criteria**:
- ✅ Event broadcaster implemented with pub-sub pattern
- ✅ Task operations broadcast events (register, assign, progress, complete)
- ✅ SSE endpoint uses broadcaster for real-time streaming
- ✅ Event filtering by type works
- ✅ Multiple subscribers supported
- ✅ All tests pass

---

### **Friday: Week 5 Testing & Documentation**

**Goal**: Comprehensive testing and documentation for Week 5 implementations (telemetry, research logging, CATO integration).

#### **Step 1: Create Feature Documentation**

Create `docs/features/TELEMETRY_SYSTEM.md`:

```markdown
# Telemetry System

## Overview

Marcus's telemetry system provides comprehensive observability for the multi-agent system through three layers:

1. **User Journey Tracking** - Identifies where users get stuck
2. **Research Event Logging** - Captures MAS behavior patterns
3. **CATO Integration** - Real-time visualization

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Actions                              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
                ┌─────────────────────────┐
                │    Marcus MCP Tools     │
                │  (register, assign,     │
                │   progress, complete)   │
                └──────────┬──────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐   ┌──────────────┐  ┌──────────┐
    │ Audit    │   │  Research    │  │  Event   │
    │ Logger   │   │  Event       │  │  Broad   │
    │          │   │  Logger      │  │  caster  │
    └────┬─────┘   └──────┬───────┘  └────┬─────┘
         │                │               │
         │                │               │
         ▼                ▼               ▼
    ┌─────────────────────────────────────────┐
    │          SQLite Event Store             │
    └─────────────────────────────────────────┘
                           │
                           │
                           ▼
                    ┌──────────────┐
                    │     CATO     │
                    │  Dashboard   │
                    └──────────────┘
```

## Components

### 1. Journey Milestone Tracking

**Purpose**: Track user progress through key workflows to identify bottlenecks.

**Key Milestones**:
- `project_creation` - Creating new projects
- `task_assignment` - Assigning tasks to agents
- `feature_implementation` - Implementing features
- `deployment` - Deploying projects

**Usage**:
```python
from src.marcus_mcp.audit import AuditLogger

audit_logger = AuditLogger()

# Start milestone
milestone_id = audit_logger.start_milestone(
    session_id="session-123",
    milestone_name="Create Project",
    milestone_type="project_creation",
    metadata={"project_name": "my-app"}
)

# ... user performs actions ...

# Complete milestone
audit_logger.complete_milestone(
    milestone_id,
    metadata={"project_id": "proj-456", "duration_seconds": 45.2}
)
```

**Metrics**:
```python
metrics = audit_logger.get_journey_metrics(
    milestone_type="project_creation",
    hours=24
)

print(f"Completion rate: {metrics['completion_rate']}")
print(f"Avg duration: {metrics['avg_duration_seconds']}s")
```

### 2. Research Event Logging

**Purpose**: Capture MAS behavior patterns for academic research and system optimization.

**Event Types**:
- `agent_coordination` - How agents work together (parallel, sequential, handoff)
- `decision_point` - Agent decision-making processes
- `task_assignment` - Why tasks are assigned to specific agents
- `performance_metric` - Task completion times, throughput
- `failure_event` - Failures and recovery attempts

**Usage**:
```python
from src.research.event_logger import ResearchEventLogger

research_logger = ResearchEventLogger()

# Log agent coordination
research_logger.log_agent_coordination(
    session_id="session-123",
    agent_ids=["agent-1", "agent-2"],
    coordination_type="parallel",
    tasks_involved=["T-1", "T-2"]
)

# Log decision point
research_logger.log_decision_point(
    session_id="session-123",
    agent_id="agent-1",
    task_id="T-1",
    decision_type="implementation_approach",
    options_considered=["REST API", "GraphQL"],
    choice_made="REST API",
    reasoning="Simpler for MVP",
    confidence=0.8
)

# Query events
events = research_logger.query_events(
    event_type="agent_coordination",
    hours=24
)
```

### 3. CATO Integration

**Purpose**: Real-time visualization of MAS state and behavior.

**Endpoints**:
- `GET /api/cato/snapshot` - Current system state (agents, tasks, dependencies)
- `GET /api/cato/events/stream` - Real-time event stream (SSE)
- `GET /api/cato/metrics/journey` - User journey metrics
- `GET /api/cato/metrics/research` - Research metrics
- `GET /api/cato/agent/{agent_id}` - Agent detail

**Event Stream Usage** (JavaScript):
```javascript
const eventSource = new EventSource('/api/cato/events/stream?event_types=task_assigned,task_completed');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Event:', data);

    if (data.event_type === 'task_assigned') {
        updateAgentStatus(data.event_data.agent_id, 'busy');
    }
};
```

## Data Flow

### Task Assignment Example

1. User calls `request_next_task` via MCP
2. Marcus assigns task to agent
3. Events are generated:
   - **Audit Logger**: Records milestone progress
   - **Research Logger**: Records task assignment with reasoning
   - **Event Broadcaster**: Broadcasts `task_assigned` event
4. CATO receives event via SSE and updates UI

## Performance Considerations

### Event Volume
- Typical load: 10-100 events/second
- Peak load: 1000 events/second (large projects)

### Storage
- Events stored in SQLite with daily rotation
- 30-day retention for audit logs
- 90-day retention for research logs

### Broadcast Queue
- Max queue size: 100 events per subscriber
- Older events dropped if queue full (logged)

## Configuration

```python
# .marcus/config.yaml
telemetry:
  audit_log_dir: ".marcus/logs/audit"
  research_log_dir: ".marcus/logs/research"
  event_retention_days: 30
  research_retention_days: 90
  broadcast_queue_size: 100
```

## Monitoring

### Health Checks
```bash
# Check event broadcaster status
curl http://localhost:8000/api/cato/events/subscribers

# Check journey metrics
curl http://localhost:8000/api/cato/metrics/journey?hours=24

# Check research metrics
curl http://localhost:8000/api/cato/metrics/research?hours=24
```

### Alerts
- Queue full warnings (> 90% capacity)
- High event drop rate (> 1% dropped)
- Slow event processing (> 100ms avg)

## Privacy & Security

### Data Collection
- No PII (personally identifiable information) collected
- Project names and descriptions included (sanitize if needed)
- Agent IDs are UUIDs (not usernames)

### Access Control
- CATO endpoints require authentication (future)
- Research logs stored locally only
- Export requires explicit user action

## Research Use Cases

### 1. Agent Coordination Patterns
```python
events = research_logger.query_events(event_type="agent_coordination", hours=168)

patterns = {}
for event in events:
    coord_type = event.event_data["coordination_type"]
    patterns[coord_type] = patterns.get(coord_type, 0) + 1

print(f"Parallel: {patterns['parallel']}")
print(f"Sequential: {patterns['sequential']}")
print(f"Handoff: {patterns['handoff']}")
```

### 2. Decision Quality Analysis
```python
decisions = research_logger.query_events(event_type="decision_point", hours=168)

high_confidence = sum(1 for d in decisions if d.event_data["confidence"] >= 0.8)
total = len(decisions)

print(f"High confidence decisions: {high_confidence}/{total} ({high_confidence/total*100:.1f}%)")
```

### 3. Task Assignment Efficiency
```python
assignments = research_logger.query_events(event_type="task_assignment", hours=168)

reassignments = sum(1 for a in assignments if len(a.event_data["alternative_agents"]) > 0)
total = len(assignments)

print(f"Optimal assignments: {total - reassignments}/{total}")
```

## Troubleshooting

### Events not appearing in CATO
1. Check broadcaster has subscribers: `curl http://localhost:8000/api/cato/events/subscribers`
2. Check SSE connection is active (browser DevTools → Network)
3. Verify event types match subscription filter

### High event drop rate
1. Increase broadcast queue size in config
2. Reduce event volume (filter less important events)
3. Check CATO processing speed (slow consumers)

### Missing journey metrics
1. Verify milestones are being completed (not just started)
2. Check audit log directory exists and is writable
3. Query with longer time window (`hours=168` for 7 days)

## Future Enhancements

- [ ] Anomaly detection (unusual agent behavior)
- [ ] Predictive analytics (estimate completion times)
- [ ] A/B testing framework (compare coordination strategies)
- [ ] Export to external analytics platforms (Elasticsearch, Grafana)
```

Create `docs/implementation/WEEK_5_SUMMARY.md`:

```markdown
# Week 5 Implementation Summary

## Overview
Week 5 focused on comprehensive telemetry, research-grade event logging, and real-time visualization through CATO integration.

## Completed Work

### Monday: Journey Milestone Tracking
- ✅ Enhanced `AuditLogger` with milestone tracking
- ✅ Implemented `start_milestone()`, `complete_milestone()`, `fail_milestone()`
- ✅ Added `get_journey_metrics()` for completion rates and durations
- ✅ Full test coverage (8 tests, 100% pass rate)

**Key Files**:
- `src/marcus_mcp/audit.py` (enhanced)
- `tests/unit/mcp/test_journey_tracking.py` (new)

### Tuesday: Research Event Logging
- ✅ Created `ResearchEventLogger` for MAS behavior studies
- ✅ Implemented 5 event types (coordination, decisions, assignments, performance, failures)
- ✅ Added query interface for analysis
- ✅ Full test coverage (6 tests, 100% pass rate)

**Key Files**:
- `src/research/event_logger.py` (new)
- `tests/unit/research/test_event_logger.py` (new)

### Wednesday: CATO API Integration
- ✅ Created CATO API routes (`/snapshot`, `/events/stream`, `/metrics/*`, `/agent/*`)
- ✅ Implemented server-sent events for real-time updates
- ✅ Added CORS support for CATO dashboard
- ✅ Full test coverage (7 unit tests, 3 integration tests)

**Key Files**:
- `src/api/cato_routes.py` (new)
- `src/api/main.py` (updated)
- `tests/unit/api/test_cato_routes.py` (new)
- `tests/integration/api/test_cato_integration.py` (new)

### Thursday: Real-time Event Broadcasting
- ✅ Created `EventBroadcaster` with pub-sub pattern
- ✅ Integrated with task operations (register, assign, progress, complete)
- ✅ Updated SSE endpoint to use broadcaster
- ✅ Full test coverage (5 unit tests, 1 integration test)

**Key Files**:
- `src/events/broadcaster.py` (new)
- `src/marcus_mcp/tools/core.py` (updated)
- `tests/unit/events/test_broadcaster.py` (new)
- `tests/integration/e2e/test_realtime_updates.py` (new)

### Friday: Documentation & Testing
- ✅ Created comprehensive telemetry documentation
- ✅ All tests passing (29 new tests, 100% pass rate)
- ✅ Integration tested with CATO dashboard
- ✅ Performance validated (handles 1000 events/sec)

**Key Files**:
- `docs/features/TELEMETRY_SYSTEM.md` (new)
- `docs/implementation/WEEK_5_SUMMARY.md` (this file)

## Metrics

### Code Changes
- **Files added**: 8
- **Files modified**: 3
- **Lines added**: ~2,500
- **Tests added**: 29

### Test Coverage
- **Unit tests**: 26 (100% pass)
- **Integration tests**: 3 (100% pass)
- **Overall coverage**: 95%+

### Performance
- **Event throughput**: 1,000 events/sec
- **SSE latency**: < 10ms
- **Broadcast overhead**: < 1ms per event
- **Storage**: ~1MB per 10,000 events

## Key Features Delivered

1. **User Journey Tracking**
   - Track user progress through workflows
   - Identify bottlenecks (where users get stuck)
   - Calculate completion rates and durations

2. **Research Event Logging**
   - Capture MAS behavior patterns
   - Support academic research
   - Enable system optimization

3. **CATO Integration**
   - Real-time system visualization
   - Network graph of agents, tasks, dependencies
   - Live event stream

4. **Event Broadcasting**
   - Pub-sub pattern for scalability
   - Event filtering by type
   - Multiple subscriber support

## Integration Points

### With Existing Systems
- **MCP Tools**: All tools broadcast events
- **State Manager**: Snapshot API reads current state
- **Audit Logger**: Extended with journey tracking
- **Feature Context**: Journey includes feature progress

### External Systems
- **CATO Dashboard**: SSE connection for real-time updates
- **Research Tools**: Query API for data analysis
- **Monitoring**: Health check endpoints

## Known Issues
None. All tests passing, no known bugs.

## Future Work
- Anomaly detection for unusual agent behavior
- Predictive analytics for completion time estimation
- A/B testing framework for coordination strategies
- Export to external analytics platforms (Elasticsearch, Grafana)

## Migration Notes
No breaking changes. New features are additive.

### To Use Telemetry
1. Journey tracking: Already integrated with existing workflows
2. Research logging: Opt-in via `ResearchEventLogger`
3. CATO: Connect to `/api/cato/events/stream`

### Configuration
Add to `.marcus/config.yaml`:
```yaml
telemetry:
  audit_log_dir: ".marcus/logs/audit"
  research_log_dir: ".marcus/logs/research"
  event_retention_days: 30
  research_retention_days: 90
```

## Team Notes
- All tests must pass before merge
- CATO dashboard tested manually (connects successfully)
- Performance validated with load testing (1000 events/sec sustained)
- Documentation reviewed and approved
```

#### **Step 2: Run Full Test Suite**

```bash
# Run all Week 5 tests
pytest tests/unit/mcp/test_journey_tracking.py \
       tests/unit/research/test_event_logger.py \
       tests/unit/api/test_cato_routes.py \
       tests/unit/events/test_broadcaster.py \
       tests/integration/api/test_cato_integration.py \
       tests/integration/e2e/test_realtime_updates.py \
       -v --cov=src --cov-report=html

# Should show:
# ============================= test session starts ==============================
# collected 29 items
#
# tests/unit/mcp/test_journey_tracking.py::TestJourneyTracking::test_start_milestone PASSED
# tests/unit/mcp/test_journey_tracking.py::TestJourneyTracking::test_complete_milestone PASSED
# ...
# tests/integration/e2e/test_realtime_updates.py::TestRealtimeUpdates::test_task_assignment_broadcasts_event PASSED
#
# ============================== 29 passed in 2.45s ===============================
#
# Coverage: 95%
```

#### **Step 3: Integration Testing with CATO**

Manual testing checklist:

1. **Start Marcus API**:
```bash
uvicorn src.api.main:app --reload --port 8000
```

2. **Test Snapshot Endpoint**:
```bash
curl http://localhost:8000/api/cato/snapshot | jq .
```

Expected output:
```json
{
  "success": true,
  "snapshot": {
    "nodes": {
      "agents": [...],
      "tasks": [...],
      "projects": [...],
      "features": [...]
    },
    "edges": {
      "task_dependencies": [...],
      "agent_assignments": [...],
      "feature_tasks": [...],
      "project_features": [...]
    },
    "metrics": {
      "total_agents": 0,
      "active_agents": 0,
      "total_tasks": 0,
      "completed_tasks": 0
    }
  }
}
```

3. **Test Event Stream**:
```bash
# In terminal 1: Listen to event stream
curl -N http://localhost:8000/api/cato/events/stream

# In terminal 2: Trigger events
python -c "
import asyncio
from src.marcus_mcp.tools.core import register_agent
from src.state.manager import StateManager

async def test():
    state = StateManager()
    await register_agent('test-agent', 'Test', 'developer', state=state)

asyncio.run(test())
"

# Terminal 1 should show:
# data: {"event_type": "agent_registered", "event_data": {"agent_id": "test-agent", ...}, ...}
```

4. **Test Journey Metrics**:
```bash
curl "http://localhost:8000/api/cato/metrics/journey?hours=24" | jq .
```

5. **Test Research Metrics**:
```bash
curl "http://localhost:8000/api/cato/metrics/research?hours=24" | jq .
```

#### **Step 4: Performance Testing**

Create `tests/performance/test_telemetry_performance.py`:

```python
"""
Performance tests for telemetry system.
"""

import asyncio
import time

import pytest

from src.events.broadcaster import EventBroadcaster


class TestTelemetryPerformance:
    """Performance tests for telemetry"""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_broadcast_throughput(self):
        """Test event broadcast throughput."""
        broadcaster = EventBroadcaster()

        # Subscribe
        queue = await broadcaster.subscribe("perf-test")

        # Broadcast 1000 events
        start_time = time.time()

        for i in range(1000):
            await broadcaster.broadcast("test_event", {"index": i})

        end_time = time.time()
        duration = end_time - start_time

        # Calculate throughput
        throughput = 1000 / duration

        print(f"\nThroughput: {throughput:.0f} events/sec")
        assert throughput > 500, f"Throughput too low: {throughput}"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_multiple_subscribers_performance(self):
        """Test performance with multiple subscribers."""
        broadcaster = EventBroadcaster()

        # Subscribe 10 subscribers
        queues = []
        for i in range(10):
            queue = await broadcaster.subscribe(f"sub-{i}")
            queues.append(queue)

        # Broadcast 1000 events
        start_time = time.time()

        for i in range(1000):
            await broadcaster.broadcast("test_event", {"index": i})

        end_time = time.time()
        duration = end_time - start_time

        # Calculate throughput
        throughput = 1000 / duration

        print(f"\nThroughput (10 subscribers): {throughput:.0f} events/sec")
        assert throughput > 200, f"Throughput too low with multiple subscribers: {throughput}"

        # Verify all subscribers received events
        for queue in queues:
            assert queue.qsize() == 1000
```

Run performance tests:
```bash
pytest tests/performance/test_telemetry_performance.py -v -s

# Expected output:
# Throughput: 5000+ events/sec
# Throughput (10 subscribers): 1000+ events/sec
```

#### **Step 5: Update Main Documentation**

Update `README.md` to mention telemetry:

```markdown
# Marcus - Multi-Agent Resource Coordination and Understanding System

...

## Features

...

### Telemetry & Observability
- **User Journey Tracking**: Identify workflow bottlenecks
- **Research Event Logging**: Capture MAS behavior patterns
- **CATO Integration**: Real-time system visualization
- **Event Broadcasting**: Pub-sub for scalable event distribution

See [docs/features/TELEMETRY_SYSTEM.md](docs/features/TELEMETRY_SYSTEM.md) for details.

...
```

**Success Criteria**:
- ✅ Week 5 documentation complete (TELEMETRY_SYSTEM.md, WEEK_5_SUMMARY.md)
- ✅ All 29 tests passing (100% pass rate)
- ✅ Integration tested with CATO dashboard
- ✅ Performance validated (1000+ events/sec)
- ✅ Code coverage > 95%
- ✅ README updated

---
---

## Weekend Extension: Multi-User Telemetry Backend (Saturday-Sunday)

**Goal**: Enable opt-in telemetry collection across multiple Marcus installations to understand how users interact with Marcus globally.

**Why**: The Monday-Friday implementation tracks local usage only. To monitor adoption and identify common pain points across all users, we need a central telemetry backend.

**Privacy First**: All telemetry is opt-in, anonymized, and strips PII before transmission.

---

### Saturday: Central Telemetry Backend Service

**What**: Build a FastAPI service that receives anonymized telemetry from Marcus installations and stores aggregate metrics.

**Why**: Need a central point to collect and aggregate usage data from all users who opt in.

---

#### Step 1: Privacy & Security Guidelines

**File**: `docs/TELEMETRY_PRIVACY.md`

```markdown
# Telemetry Privacy & Security Guidelines

## Overview

Marcus telemetry is **opt-in only** and designed with privacy as the top priority. This document explains what data is collected, how it's anonymized, and what is explicitly excluded.

## What We NEVER Collect

### 🚫 Credentials & Secrets
- API keys (Anthropic, OpenAI, etc.)
- Passwords
- Access tokens
- Database credentials
- SSH keys
- Environment variables (may contain secrets)

### 🚫 Personal Identifiable Information (PII)
- Email addresses
- Real names
- IP addresses (logged but not stored)
- Organization names
- Company names
- Physical addresses
- Phone numbers

### 🚫 Proprietary/Sensitive Content
- Source code content
- File contents
- Task descriptions (may contain business logic)
- Decision reasoning (may contain proprietary info)
- Artifact content (code, docs, etc.)
- Git commit messages (may reveal business info)
- Project descriptions (may reveal business strategy)
- File paths that reveal org structure

### 🚫 System Information That Reveals Identity
- Hostnames with user/company names
- Full file paths with usernames
- MAC addresses
- Device serial numbers

## What We DO Collect (Anonymized)

### ✅ Milestone Metrics (Aggregate Only)
```json
{
  "project_creation": {
    "attempts": 5,
    "completed": 4,
    "failed": 1,
    "avg_duration_seconds": 45.2
  }
}
```

### ✅ Performance Metrics
- Task completion times (no task content)
- Agent coordination patterns (parallel, sequential, handoff)
- Success/failure rates (no error details with PII)
- Error types (sanitized, no stack traces with paths)
- Feature usage counts (e.g., "workspace_isolation used 5 times")

### ✅ System Health (Minimal)
- Marcus version (e.g., "0.1.0")
- Python version (e.g., "3.11")
- OS type only (linux, darwin, win32) - no version details
- Number of agents used (count only)
- Number of tasks completed (count only)

### ✅ Anonymous Identifiers
- Installation ID (random UUID, hashed)
- Session ID (random UUID, hashed)
- No correlation to real identity possible

## Privacy Safeguards

### 1. Hash/Anonymize All Identifiers

```python
import hashlib

def anonymize_id(id_value: str, salt: str) -> str:
    """Hash identifier for privacy."""
    return hashlib.sha256(f"{id_value}{salt}".encode()).hexdigest()[:16]
```

### 2. Sanitize Error Messages

```python
import re

def sanitize_error(error_msg: str) -> str:
    """Remove file paths and PII from error messages."""
    # Remove file paths
    error_msg = re.sub(r'/[^\s]+', '/path/redacted', error_msg)
    error_msg = re.sub(r'C:\\[^\s]+', 'C:\\path\\redacted', error_msg)

    # Remove potential emails
    error_msg = re.sub(r'\S+@\S+\.\S+', 'user@redacted', error_msg)

    # Remove potential hostnames
    error_msg = re.sub(r'host[=:]\S+', 'host=redacted', error_msg, flags=re.IGNORECASE)

    return error_msg
```

### 3. Aggregate Before Sending

Marcus **never sends individual events** immediately. All data is:
1. Collected locally for 24 hours
2. Aggregated into summary statistics
3. Anonymized (remove all PII)
4. Validated (reject if PII detected)
5. Sent as a single batch

```python
# Example: Individual events are aggregated
# Individual events (NOT sent):
# - "User created project 'secret-internal-app'"
# - "User created project 'client-project-acme'"

# Aggregate sent instead:
{
  "project_creation": {
    "attempts": 2,
    "completed": 2,
    "failed": 0,
    "avg_duration_seconds": 43.5
  }
}
```

### 4. Client-Side Validation

Before sending telemetry, Marcus validates that no PII is present:

```python
def validate_no_pii(data: Dict[str, Any]) -> bool:
    """
    Validate that data contains no obvious PII.

    Raises ValueError if potential PII detected.
    """
    import json
    data_str = json.dumps(data)

    # Check for email patterns
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', data_str):
        raise ValueError("Potential email address detected")

    # Check for absolute paths with usernames
    if re.search(r'/home/\w+|/Users/\w+|C:\\Users\\\w+', data_str):
        raise ValueError("File paths with usernames detected")

    # Check for common PII field names
    pii_fields = ['email', 'password', 'api_key', 'token', 'secret', 'credential']
    for field in pii_fields:
        if field in data_str.lower():
            raise ValueError(f"Sensitive field name '{field}' detected")

    return True
```

## Opting In

Telemetry is **disabled by default**. Users must explicitly opt in:

```json
// config_marcus.json
{
  "telemetry": {
    "enabled": false,  // Change to true to opt in
    "endpoint": "https://telemetry.marcus.dev/v1/telemetry/batch",
    "upload_interval_hours": 24
  }
}
```

## Data Retention

- Telemetry data is retained for **1 year**
- After 1 year, data is automatically deleted
- Users can request deletion of their installation's data at any time by contacting support

## Transparency

- This privacy policy is version-controlled alongside the code
- Any changes require a pull request and review
- Users are notified of privacy policy changes via release notes

## Questions?

Contact: privacy@marcus.dev (fictional - replace with real contact)
```

**Test**: Validation functions

```python
# tests/unit/telemetry/test_privacy_validation.py
"""Unit tests for telemetry privacy validation."""

import pytest
from src.telemetry.privacy import validate_no_pii, sanitize_error, anonymize_id

class TestPrivacyValidation:
    """Test privacy validation functions."""

    def test_detects_email_in_data(self):
        """Test email detection in telemetry data."""
        data = {
            "user": "john.doe@company.com",
            "action": "project_created"
        }

        with pytest.raises(ValueError, match="email address"):
            validate_no_pii(data)

    def test_detects_file_paths_in_data(self):
        """Test file path detection."""
        data = {
            "error": "File not found: /Users/john.doe/project/main.py"
        }

        with pytest.raises(ValueError, match="File paths"):
            validate_no_pii(data)

    def test_detects_sensitive_field_names(self):
        """Test sensitive field name detection."""
        data = {
            "api_key": "sk-1234567890"  # pragma: allowlist secret
        }

        with pytest.raises(ValueError, match="api_key"):
            validate_no_pii(data)

    def test_allows_anonymous_data(self):
        """Test anonymous data passes validation."""
        data = {
            "installation_id": "abc123def456",
            "milestones": {
                "project_creation": {
                    "attempts": 5,
                    "completed": 4
                }
            }
        }

        assert validate_no_pii(data) is True

    def test_sanitize_error_removes_paths(self):
        """Test error sanitization removes file paths."""
        error = "File not found: /Users/john/project/main.py"
        sanitized = sanitize_error(error)

        assert "/Users/john" not in sanitized
        assert "/path/redacted" in sanitized

    def test_sanitize_error_removes_emails(self):
        """Test error sanitization removes emails."""
        error = "Authentication failed for user john.doe@company.com"
        sanitized = sanitize_error(error)

        assert "john.doe@company.com" not in sanitized
        assert "user@redacted" in sanitized

    def test_anonymize_id_is_consistent(self):
        """Test ID anonymization is deterministic."""
        id1 = anonymize_id("user-123", "salt")
        id2 = anonymize_id("user-123", "salt")

        assert id1 == id2
        assert len(id1) == 16
        assert id1 != "user-123"

    def test_anonymize_id_different_salt_different_result(self):
        """Test different salts produce different hashes."""
        id1 = anonymize_id("user-123", "salt1")
        id2 = anonymize_id("user-123", "salt2")

        assert id1 != id2
```

---

#### Step 2: Telemetry Backend Service

**File**: `src/telemetry_backend/server.py`

```python
"""
Central telemetry backend service.

Accepts opt-in anonymized telemetry from Marcus installations
and provides aggregate metrics for monitoring user behavior.

Privacy Design:
- All data must pass PII validation before storage
- IP addresses logged but not stored
- Data aggregated before analysis
- 1-year retention policy
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import hashlib
import re
from pathlib import Path
import asyncpg
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Marcus Telemetry Backend",
    description="Opt-in telemetry collection for Marcus usage analytics",
    version="0.1.0"
)

# CORS for Cato dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://cato.marcus.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None


class TelemetryBatch(BaseModel):
    """
    Anonymized telemetry batch from a Marcus installation.

    All PII must be removed before sending. Server validates
    data for PII patterns before storage.
    """
    installation_id: str = Field(
        ...,
        description="Hashed installation ID (anonymous)",
        regex=r'^[a-f0-9]{16}$'
    )
    marcus_version: str = Field(..., description="Marcus version (e.g., '0.1.0')")
    python_version: str = Field(..., description="Python version (e.g., '3.11')")
    os_type: str = Field(..., description="OS type (linux, darwin, win32)")
    period_start: str = Field(..., description="Batch period start (ISO UTC)")
    period_end: str = Field(..., description="Batch period end (ISO UTC)")

    # Aggregate milestone metrics
    milestones: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Milestone metrics by type",
        example={
            "project_creation": {
                "attempts": 5,
                "completed": 4,
                "failed": 1,
                "avg_duration_seconds": 45.2
            }
        }
    )

    # Aggregate feature usage
    feature_usage: Dict[str, int] = Field(
        default_factory=dict,
        description="Feature usage counts",
        example={
            "workspace_isolation": 10,
            "feature_context": 8
        }
    )

    # Error statistics (sanitized)
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Sanitized error statistics",
        example=[
            {
                "error_type": "KanbanIntegrationError",
                "count": 2,
                "contexts": ["task_assignment", "project_creation"]
            }
        ]
    )

    @validator('installation_id')
    def validate_installation_id(cls, v):
        """Ensure installation ID is properly anonymized."""
        if not re.match(r'^[a-f0-9]{16}$', v):
            raise ValueError("installation_id must be a 16-character hex hash")
        return v


def validate_no_pii(data: Dict[str, Any]) -> None:
    """
    Validate that data contains no obvious PII.

    Parameters
    ----------
    data : Dict[str, Any]
        Data to validate

    Raises
    ------
    ValueError
        If potential PII detected
    """
    import json
    data_str = json.dumps(data)

    # Check for email patterns
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', data_str):
        raise ValueError("Potential email address detected in telemetry data")

    # Check for absolute paths with usernames
    if re.search(r'/home/\w+|/Users/\w+|C:\\Users\\\w+', data_str):
        raise ValueError("Absolute file paths with usernames detected in telemetry data")

    # Check for common PII field names
    pii_fields = ['email', 'password', 'api_key', 'token', 'secret', 'credential', 'name']
    for field in pii_fields:
        # Use word boundaries to avoid false positives
        pattern = rf'\b{field}\b'
        if re.search(pattern, data_str, re.IGNORECASE):
            raise ValueError(f"Sensitive field name '{field}' detected in telemetry data")


@app.on_event("startup")
async def startup():
    """Initialize database connection pool."""
    global db_pool

    # TODO: Load from environment variables
    db_pool = await asyncpg.create_pool(
        host="localhost",
        port=5432,
        user="telemetry_user",
        password="telemetry_pass",  # pragma: allowlist secret
        database="marcus_telemetry",
        min_size=2,
        max_size=10
    )

    logger.info("Telemetry backend started")


@app.on_event("shutdown")
async def shutdown():
    """Close database connection pool."""
    if db_pool:
        await db_pool.close()

    logger.info("Telemetry backend stopped")


@app.post("/v1/telemetry/batch")
async def receive_telemetry_batch(
    batch: TelemetryBatch,
    request: Request
) -> Dict[str, Any]:
    """
    Receive anonymized telemetry batch.

    IP address is logged for rate limiting but NOT stored.

    Parameters
    ----------
    batch : TelemetryBatch
        Anonymized telemetry data
    request : Request
        HTTP request (for IP logging only)

    Returns
    -------
    Dict[str, Any]
        Success confirmation

    Raises
    ------
    HTTPException
        If validation fails or PII detected

    Examples
    --------
    >>> import httpx
    >>> async with httpx.AsyncClient() as client:
    ...     response = await client.post(
    ...         "http://localhost:8001/v1/telemetry/batch",
    ...         json={
    ...             "installation_id": "abc123def4567890",
    ...             "marcus_version": "0.1.0",
    ...             "python_version": "3.11",
    ...             "os_type": "darwin",
    ...             "period_start": "2025-01-10T00:00:00Z",
    ...             "period_end": "2025-01-11T00:00:00Z",
    ...             "milestones": {
    ...                 "project_creation": {
    ...                     "attempts": 5,
    ...                     "completed": 4,
    ...                     "failed": 1,
    ...                     "avg_duration_seconds": 45.2
    ...                 }
    ...             }
    ...         }
    ...     )
    >>> response.json()
    {"success": True, "message": "Telemetry received"}
    """
    try:
        # Log IP for rate limiting (not stored)
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"Received telemetry from {client_ip} (not stored)")

        # Validate no PII
        validate_no_pii(batch.dict())

        # Store in database
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO telemetry_batches
                (installation_id, marcus_version, python_version, os_type,
                 period_start, period_end, milestones, feature_usage, errors, received_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                batch.installation_id,
                batch.marcus_version,
                batch.python_version,
                batch.os_type,
                batch.period_start,
                batch.period_end,
                batch.milestones,
                batch.feature_usage,
                batch.errors,
                datetime.now(timezone.utc)
            )

        logger.info(f"Telemetry stored for installation {batch.installation_id[:8]}...")

        return {
            "success": True,
            "message": "Telemetry received",
            "received_at": datetime.now(timezone.utc).isoformat()
        }

    except ValueError as e:
        # PII validation failed
        logger.warning(f"Telemetry rejected due to PII: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Telemetry validation failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to store telemetry: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store telemetry: {str(e)}"
        )


@app.get("/v1/metrics/aggregate")
async def get_aggregate_metrics(
    hours: int = 24,
    marcus_version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get aggregate metrics across all installations.

    Used by Cato dashboard to show global usage statistics.

    Parameters
    ----------
    hours : int
        Look back period in hours (default: 24)
    marcus_version : str, optional
        Filter by Marcus version

    Returns
    -------
    Dict[str, Any]
        Aggregate metrics including:
        - active_installations: Number of unique installations reporting
        - milestone_metrics: Aggregated milestone statistics
        - feature_adoption: Feature usage across installations

    Examples
    --------
    >>> metrics = await get_aggregate_metrics(hours=24)
    >>> print(metrics["active_installations"])
    42
    >>> print(metrics["milestone_metrics"]["project_creation"]["success_rate"])
    0.85
    """
    try:
        async with db_pool.acquire() as conn:
            # Get total installations reporting
            installations = await conn.fetchval("""
                SELECT COUNT(DISTINCT installation_id)
                FROM telemetry_batches
                WHERE received_at > NOW() - INTERVAL '%s hours'
            """ % hours)

            # Get milestone aggregates
            milestones = await conn.fetch("""
                SELECT
                    milestone_type,
                    SUM((value->>'attempts')::int) as total_attempts,
                    SUM((value->>'completed')::int) as total_completed,
                    SUM((value->>'failed')::int) as total_failed,
                    AVG((value->>'avg_duration_seconds')::float) as avg_duration
                FROM (
                    SELECT
                        key as milestone_type,
                        value
                    FROM telemetry_batches, jsonb_each(milestones)
                    WHERE received_at > NOW() - INTERVAL '%s hours'
                ) AS milestone_data
                GROUP BY milestone_type
            """ % hours)

            milestone_metrics = {}
            for row in milestones:
                total_attempts = row['total_attempts'] or 0
                total_completed = row['total_completed'] or 0
                milestone_metrics[row['milestone_type']] = {
                    "total_attempts": total_attempts,
                    "total_completed": total_completed,
                    "total_failed": row['total_failed'] or 0,
                    "avg_duration_seconds": float(row['avg_duration']) if row['avg_duration'] else 0,
                    "success_rate": total_completed / total_attempts if total_attempts > 0 else 0
                }

            return {
                "success": True,
                "period_hours": hours,
                "active_installations": installations,
                "milestone_metrics": milestone_metrics,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

    except Exception as e:
        logger.error(f"Failed to get aggregate metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get aggregate metrics: {str(e)}"
        )


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns
    -------
    Dict[str, str]
        Status message
    """
    return {"status": "healthy", "service": "marcus-telemetry"}


@app.get("/v1/privacy")
async def get_privacy_policy() -> Dict[str, Any]:
    """
    Get privacy policy details.

    Returns
    -------
    Dict[str, Any]
        Privacy policy summary
    """
    return {
        "opt_in": True,
        "data_collected": [
            "Aggregate milestone completion rates",
            "Feature usage counts",
            "Sanitized error types",
            "System metadata (OS, versions)"
        ],
        "data_not_collected": [
            "Source code or file contents",
            "Personal information (names, emails, IP addresses)",
            "API keys or credentials",
            "Task descriptions or project details"
        ],
        "retention_days": 365,
        "anonymization": "All identifiers are hashed before transmission",
        "full_policy_url": "https://marcus.dev/privacy"
    }
```

**Database Schema**: `src/telemetry_backend/schema.sql`

```sql
-- Telemetry backend database schema

CREATE TABLE IF NOT EXISTS telemetry_batches (
    id SERIAL PRIMARY KEY,
    installation_id VARCHAR(16) NOT NULL,  -- Hashed, anonymous (16-char hex)
    marcus_version VARCHAR(20) NOT NULL,
    python_version VARCHAR(20) NOT NULL,
    os_type VARCHAR(20) NOT NULL,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    milestones JSONB NOT NULL,  -- Aggregate milestone metrics
    feature_usage JSONB NOT NULL DEFAULT '{}',  -- Feature usage counts
    errors JSONB NOT NULL DEFAULT '[]',  -- Sanitized error statistics
    received_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_os_type CHECK (os_type IN ('linux', 'darwin', 'win32')),
    CONSTRAINT valid_installation_id CHECK (installation_id ~ '^[a-f0-9]{16}$')
);

-- Indexes for queries
CREATE INDEX idx_installation_id ON telemetry_batches(installation_id);
CREATE INDEX idx_received_at ON telemetry_batches(received_at);
CREATE INDEX idx_marcus_version ON telemetry_batches(marcus_version);
CREATE INDEX idx_period ON telemetry_batches(period_start, period_end);

-- GIN index for JSONB queries
CREATE INDEX idx_milestones ON telemetry_batches USING GIN (milestones);
CREATE INDEX idx_feature_usage ON telemetry_batches USING GIN (feature_usage);

-- Retention policy: Automatically delete data older than 1 year
-- Run this as a daily cron job
-- DELETE FROM telemetry_batches WHERE received_at < NOW() - INTERVAL '365 days';

-- View for quick stats
CREATE OR REPLACE VIEW installation_stats AS
SELECT
    DATE(received_at) as report_date,
    COUNT(DISTINCT installation_id) as unique_installations,
    marcus_version,
    os_type,
    COUNT(*) as total_batches
FROM telemetry_batches
GROUP BY DATE(received_at), marcus_version, os_type
ORDER BY report_date DESC;
```

**Tests**: `tests/unit/telemetry_backend/test_backend_server.py`

```python
"""Unit tests for telemetry backend server."""

import pytest
from fastapi.testclient import TestClient
from src.telemetry_backend.server import app, validate_no_pii

client = TestClient(app)


class TestTelemetryBackend:
    """Test telemetry backend API."""

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_privacy_policy_endpoint(self):
        """Test privacy policy is accessible."""
        response = client.get("/v1/privacy")

        assert response.status_code == 200
        data = response.json()
        assert data["opt_in"] is True
        assert "data_collected" in data
        assert "data_not_collected" in data

    def test_receive_valid_telemetry_batch(self):
        """Test receiving valid anonymized telemetry."""
        batch = {
            "installation_id": "abc123def4567890",
            "marcus_version": "0.1.0",
            "python_version": "3.11",
            "os_type": "darwin",
            "period_start": "2025-01-10T00:00:00Z",
            "period_end": "2025-01-11T00:00:00Z",
            "milestones": {
                "project_creation": {
                    "attempts": 5,
                    "completed": 4,
                    "failed": 1,
                    "avg_duration_seconds": 45.2
                }
            }
        }

        response = client.post("/v1/telemetry/batch", json=batch)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_reject_telemetry_with_email(self):
        """Test telemetry with email is rejected."""
        batch = {
            "installation_id": "abc123def4567890",
            "marcus_version": "0.1.0",
            "python_version": "3.11",
            "os_type": "darwin",
            "period_start": "2025-01-10T00:00:00Z",
            "period_end": "2025-01-11T00:00:00Z",
            "milestones": {
                "project_creation": {
                    "user": "john.doe@company.com",  # PII!
                    "attempts": 5
                }
            }
        }

        response = client.post("/v1/telemetry/batch", json=batch)

        assert response.status_code == 400
        assert "email address" in response.json()["detail"].lower()

    def test_reject_telemetry_with_file_paths(self):
        """Test telemetry with file paths is rejected."""
        batch = {
            "installation_id": "abc123def4567890",
            "marcus_version": "0.1.0",
            "python_version": "3.11",
            "os_type": "darwin",
            "period_start": "2025-01-10T00:00:00Z",
            "period_end": "2025-01-11T00:00:00Z",
            "milestones": {},
            "errors": [
                {
                    "error": "File not found: /Users/john/project/main.py"  # PII!
                }
            ]
        }

        response = client.post("/v1/telemetry/batch", json=batch)

        assert response.status_code == 400
        assert "file paths" in response.json()["detail"].lower()


class TestPrivacyValidation:
    """Test privacy validation functions."""

    def test_validate_detects_email(self):
        """Test email detection."""
        data = {"user": "john.doe@company.com"}

        with pytest.raises(ValueError, match="email"):
            validate_no_pii(data)

    def test_validate_detects_file_paths(self):
        """Test file path detection."""
        data = {"path": "/Users/john/project/main.py"}

        with pytest.raises(ValueError, match="file paths"):
            validate_no_pii(data)

    def test_validate_detects_sensitive_fields(self):
        """Test sensitive field detection."""
        data = {"api_key": "sk-1234567890"}  # pragma: allowlist secret

        with pytest.raises(ValueError, match="api_key"):
            validate_no_pii(data)

    def test_validate_allows_anonymous_data(self):
        """Test anonymous data passes."""
        data = {
            "installation_id": "abc123def456",
            "milestones": {
                "project_creation": {
                    "attempts": 5,
                    "completed": 4
                }
            }
        }

        # Should not raise
        validate_no_pii(data)
```

Run backend tests:
```bash
pytest tests/unit/telemetry_backend/test_backend_server.py -v
pytest tests/unit/telemetry/test_privacy_validation.py -v
```

---

### Sunday: Marcus Client Integration + Cato Visualization

**What**: Add telemetry uploader to Marcus that batches and sends anonymized data to the backend (opt-in only).

---

#### Step 1: Telemetry Client Uploader

**File**: `src/telemetry/uploader.py`

```python
"""
Telemetry uploader for Marcus.

Batches local telemetry data, anonymizes it, and uploads to central backend.
Only runs if user has opted in via config.
"""

import asyncio
import hashlib
import logging
import platform
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
from src.marcus_mcp.audit import AuditLogger
from src.telemetry.privacy import validate_no_pii, sanitize_error

logger = logging.getLogger(__name__)


class TelemetryUploader:
    """
    Uploads anonymized telemetry to central backend.

    Only runs if user has opted in via config.
    Batches data over 24 hours before uploading.
    Validates data for PII before transmission.

    Parameters
    ----------
    config : Dict[str, Any]
        Marcus configuration with telemetry settings

    Attributes
    ----------
    enabled : bool
        Whether telemetry is enabled
    endpoint : str
        Backend endpoint URL
    installation_id : str
        Anonymous installation identifier
    last_upload : datetime, optional
        Last successful upload timestamp

    Examples
    --------
    >>> config = {
    ...     "telemetry": {
    ...         "enabled": True,
    ...         "endpoint": "https://telemetry.marcus.dev/v1/telemetry/batch"
    ...     }
    ... }
    >>> uploader = TelemetryUploader(config)
    >>> await uploader.upload_if_due(audit_logger)
    True
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize telemetry uploader.

        Parameters
        ----------
        config : Dict[str, Any]
            Marcus configuration
        """
        telemetry_config = config.get("telemetry", {})

        self.enabled = telemetry_config.get("enabled", False)
        self.endpoint = telemetry_config.get(
            "endpoint",
            "https://telemetry.marcus.dev/v1/telemetry/batch"
        )
        self.upload_interval_hours = telemetry_config.get("upload_interval_hours", 24)

        self.installation_id = self._get_or_create_installation_id()
        self.last_upload = None

    def _get_or_create_installation_id(self) -> str:
        """
        Get or create anonymized installation ID.

        Generates a random UUID on first run, hashes it for privacy,
        and stores it locally for future uploads.

        Returns
        -------
        str
            16-character hex hash (anonymized)
        """
        id_file = Path.home() / ".marcus" / "installation_id"

        if id_file.exists():
            return id_file.read_text().strip()

        # Generate new anonymous ID
        random_uuid = str(uuid.uuid4())
        installation_id = hashlib.sha256(random_uuid.encode()).hexdigest()[:16]

        # Store for future use
        id_file.parent.mkdir(parents=True, exist_ok=True)
        id_file.write_text(installation_id)

        logger.info(f"Created anonymous installation ID: {installation_id[:8]}...")

        return installation_id

    async def upload_if_due(self, audit_logger: AuditLogger) -> bool:
        """
        Upload telemetry batch if interval has passed.

        Checks if upload_interval_hours have passed since last upload.
        If due, aggregates local data, anonymizes, and uploads.

        Parameters
        ----------
        audit_logger : AuditLogger
            Audit logger with local telemetry data

        Returns
        -------
        bool
            True if uploaded successfully, False if skipped or failed

        Examples
        --------
        >>> uploader = TelemetryUploader(config)
        >>> success = await uploader.upload_if_due(audit_logger)
        >>> if success:
        ...     print("Telemetry uploaded")
        """
        if not self.enabled:
            logger.debug("Telemetry disabled, skipping upload")
            return False

        # Check if interval has passed
        now = datetime.now(timezone.utc)
        if self.last_upload:
            hours_since_upload = (now - self.last_upload).total_seconds() / 3600
            if hours_since_upload < self.upload_interval_hours:
                logger.debug(f"Upload not due yet ({hours_since_upload:.1f}h < {self.upload_interval_hours}h)")
                return False

        # Prepare batch
        try:
            batch = self._prepare_batch(audit_logger, now)

            # Validate no PII
            validate_no_pii(batch)

            # Upload
            await self._upload_batch(batch)

            self.last_upload = now
            logger.info("Telemetry uploaded successfully")
            return True

        except ValueError as e:
            logger.error(f"Telemetry failed PII validation: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to upload telemetry: {e}")
            return False

    def _prepare_batch(
        self,
        audit_logger: AuditLogger,
        now: datetime
    ) -> Dict[str, Any]:
        """
        Prepare anonymized telemetry batch from local data.

        Aggregates milestone metrics from the last upload_interval_hours.
        All PII is removed before inclusion.

        Parameters
        ----------
        audit_logger : AuditLogger
            Local audit logger
        now : datetime
            Current timestamp

        Returns
        -------
        Dict[str, Any]
            Anonymized telemetry batch
        """
        # Calculate period
        period_start = now - timedelta(hours=self.upload_interval_hours)

        # Aggregate milestone metrics
        milestone_types = ["project_creation", "task_assignment", "feature_implementation"]
        milestone_metrics = {}

        for milestone_type in milestone_types:
            try:
                metrics = audit_logger.get_journey_metrics(
                    milestone_type=milestone_type,
                    hours=self.upload_interval_hours
                )

                milestone_metrics[milestone_type] = {
                    "attempts": metrics.get("total_milestones", 0),
                    "completed": metrics.get("completed_milestones", 0),
                    "failed": metrics.get("failed_milestones", 0),
                    "avg_duration_seconds": metrics.get("avg_duration_seconds", 0)
                }
            except Exception as e:
                logger.warning(f"Failed to get metrics for {milestone_type}: {e}")

        # TODO: Track feature usage counts
        feature_usage = {}

        # TODO: Aggregate and sanitize errors
        errors = []

        # Prepare batch
        batch = {
            "installation_id": self.installation_id,
            "marcus_version": self._get_marcus_version(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            "os_type": platform.system().lower(),
            "period_start": period_start.isoformat(),
            "period_end": now.isoformat(),
            "milestones": milestone_metrics,
            "feature_usage": feature_usage,
            "errors": errors
        }

        return batch

    def _get_marcus_version(self) -> str:
        """Get Marcus version string."""
        try:
            from src import __version__
            return __version__
        except ImportError:
            return "0.1.0"  # Default

    async def _upload_batch(self, batch: Dict[str, Any]) -> None:
        """
        Upload batch to telemetry backend.

        Parameters
        ----------
        batch : Dict[str, Any]
            Telemetry batch

        Raises
        ------
        httpx.HTTPError
            If upload fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.endpoint,
                json=batch,
                timeout=10.0
            )
            response.raise_for_status()
```

**Update Marcus Config**: `config_marcus.example.json`

```json
{
  "telemetry": {
    "enabled": false,
    "endpoint": "https://telemetry.marcus.dev/v1/telemetry/batch",
    "upload_interval_hours": 24
  }
}
```

**Integrate with Marcus**: Update `src/marcus_mcp/server.py` to periodically upload

```python
# In MarcusServer.__init__()
from src.telemetry.uploader import TelemetryUploader

self.telemetry_uploader = TelemetryUploader(self.config)

# Add background task
async def telemetry_upload_loop():
    """Background task to upload telemetry."""
    while True:
        try:
            await self.telemetry_uploader.upload_if_due(self.audit_logger)
        except Exception as e:
            logger.warning(f"Telemetry upload error: {e}")

        # Check every hour
        await asyncio.sleep(3600)

asyncio.create_task(telemetry_upload_loop())
```

---

#### Step 2: Cato Dashboard Integration

**File**: `dashboard/src/components/GlobalMetrics.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import './GlobalMetrics.css';

interface AggregateMetrics {
  success: boolean;
  period_hours: number;
  active_installations: number;
  milestone_metrics: {
    [key: string]: {
      total_attempts: number;
      total_completed: number;
      total_failed: number;
      avg_duration_seconds: number;
      success_rate: number;
    };
  };
  generated_at: string;
}

export const GlobalMetrics: React.FC = () => {
  const [metrics, setMetrics] = useState<AggregateMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGlobalMetrics();

    // Refresh every 5 minutes
    const interval = setInterval(fetchGlobalMetrics, 300000);
    return () => clearInterval(interval);
  }, []);

  const fetchGlobalMetrics = async () => {
    try {
      const response = await fetch(
        'https://telemetry.marcus.dev/v1/metrics/aggregate?hours=24'
      );

      if (!response.ok) {
        throw new Error('Failed to fetch global metrics');
      }

      const data = await response.json();
      setMetrics(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="global-metrics loading">Loading global metrics...</div>;
  }

  if (error) {
    return <div className="global-metrics error">Error: {error}</div>;
  }

  if (!metrics) {
    return <div className="global-metrics">No data available</div>;
  }

  const projectCreation = metrics.milestone_metrics.project_creation || {};

  return (
    <div className="global-metrics">
      <h2>Global Marcus Usage (Last 24 Hours)</h2>

      <div className="metric-cards">
        <div className="metric-card highlight">
          <h3>Active Installations</h3>
          <p className="metric-value">{metrics.active_installations}</p>
          <p className="metric-subtitle">unique users reporting</p>
        </div>

        <div className="metric-card">
          <h3>Project Creation</h3>
          <p className="metric-value">
            {(projectCreation.success_rate * 100).toFixed(1)}%
          </p>
          <p className="metric-subtitle">success rate</p>
          <div className="metric-details">
            <span>{projectCreation.total_completed} completed</span>
            <span>{projectCreation.total_failed} failed</span>
          </div>
        </div>

        <div className="metric-card">
          <h3>Avg Duration</h3>
          <p className="metric-value">
            {projectCreation.avg_duration_seconds?.toFixed(1)}s
          </p>
          <p className="metric-subtitle">to create project</p>
        </div>
      </div>

      <div className="milestone-breakdown">
        <h3>All Milestones</h3>
        <table>
          <thead>
            <tr>
              <th>Milestone</th>
              <th>Attempts</th>
              <th>Success Rate</th>
              <th>Avg Duration</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(metrics.milestone_metrics).map(([type, data]) => (
              <tr key={type}>
                <td>{type.replace(/_/g, ' ')}</td>
                <td>{data.total_attempts}</td>
                <td>{(data.success_rate * 100).toFixed(1)}%</td>
                <td>{data.avg_duration_seconds.toFixed(1)}s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="privacy-note">
        All metrics are anonymized and aggregated. No personal information is collected.{' '}
        <a href="https://marcus.dev/privacy" target="_blank" rel="noopener noreferrer">
          Privacy Policy
        </a>
      </p>
    </div>
  );
};
```

**Add to Cato navigation**: Update `dashboard/src/App.tsx`

```typescript
// Add new tab in historical mode
{mode === 'historical' && (
  <div className="layer-tabs">
    {/* ... existing tabs ... */}
    <button
      className={currentLayer === 'global_metrics' ? 'active' : ''}
      onClick={() => setCurrentLayer('global_metrics')}
    >
      🌍 Global Metrics
    </button>
  </div>
)}

// Render component
{mode === 'historical' && currentLayer === 'global_metrics' && (
  <GlobalMetrics />
)}
```

---

#### Step 3: Documentation & Testing

**Update**: `docs/features/TELEMETRY_SYSTEM.md` (add section)

```markdown
## Multi-User Telemetry (Opt-In)

Marcus can optionally send anonymized usage metrics to a central backend to help improve the system.

### Opting In

Telemetry is **disabled by default**. To opt in, update your config:

```json
{
  "telemetry": {
    "enabled": true,
    "endpoint": "https://telemetry.marcus.dev/v1/telemetry/batch",
    "upload_interval_hours": 24
  }
}
```

### What's Collected

Only **aggregated, anonymized metrics** are sent:
- Milestone completion rates (no project names)
- Feature usage counts (no source code)
- Error types (no file paths or PII)
- System metadata (OS type, Marcus version)

See [TELEMETRY_PRIVACY.md](../TELEMETRY_PRIVACY.md) for complete details.

### What's NOT Collected

Marcus **never** collects:
- Source code or file contents
- API keys or credentials
- Personal information (names, emails)
- Task descriptions or project details

### Viewing Global Metrics

If you opt in, you can view aggregate metrics in the Cato dashboard:
1. Open Cato dashboard
2. Switch to "Historical" mode
3. Click "Global Metrics" tab
4. See how Marcus is being used globally

### Disabling Telemetry

Set `"enabled": false` in your config and restart Marcus.
```

**Tests**: `tests/unit/telemetry/test_uploader.py`

```python
"""Unit tests for telemetry uploader."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from src.telemetry.uploader import TelemetryUploader

class TestTelemetryUploader:
    """Test telemetry uploader."""

    @pytest.fixture
    def config_enabled(self):
        """Config with telemetry enabled."""
        return {
            "telemetry": {
                "enabled": True,
                "endpoint": "http://localhost:8001/v1/telemetry/batch",
                "upload_interval_hours": 24
            }
        }

    @pytest.fixture
    def config_disabled(self):
        """Config with telemetry disabled."""
        return {
            "telemetry": {
                "enabled": False
            }
        }

    def test_initialization_with_enabled_telemetry(self, config_enabled):
        """Test uploader initializes correctly when enabled."""
        uploader = TelemetryUploader(config_enabled)

        assert uploader.enabled is True
        assert uploader.endpoint == "http://localhost:8001/v1/telemetry/batch"
        assert uploader.upload_interval_hours == 24
        assert len(uploader.installation_id) == 16

    def test_initialization_with_disabled_telemetry(self, config_disabled):
        """Test uploader initializes correctly when disabled."""
        uploader = TelemetryUploader(config_disabled)

        assert uploader.enabled is False

    @pytest.mark.asyncio
    async def test_upload_skipped_when_disabled(self, config_disabled):
        """Test upload is skipped when telemetry disabled."""
        uploader = TelemetryUploader(config_disabled)
        audit_logger = Mock()

        result = await uploader.upload_if_due(audit_logger)

        assert result is False

    @pytest.mark.asyncio
    async def test_upload_skipped_when_not_due(self, config_enabled):
        """Test upload is skipped when interval hasn't passed."""
        uploader = TelemetryUploader(config_enabled)
        audit_logger = Mock()

        # Set last upload to 1 hour ago
        uploader.last_upload = datetime.now(timezone.utc) - timedelta(hours=1)

        result = await uploader.upload_if_due(audit_logger)

        assert result is False

    @pytest.mark.asyncio
    @patch('src.telemetry.uploader.httpx.AsyncClient')
    async def test_upload_succeeds_when_due(self, mock_client, config_enabled):
        """Test upload succeeds when interval has passed."""
        uploader = TelemetryUploader(config_enabled)

        # Mock audit logger
        audit_logger = Mock()
        audit_logger.get_journey_metrics = Mock(return_value={
            "total_milestones": 5,
            "completed_milestones": 4,
            "failed_milestones": 1,
            "avg_duration_seconds": 45.2
        })

        # Mock HTTP client
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        # No last upload (first time)
        result = await uploader.upload_if_due(audit_logger)

        assert result is True
        assert uploader.last_upload is not None

    def test_installation_id_is_consistent(self, config_enabled, tmp_path):
        """Test installation ID is consistent across instances."""
        with patch('pathlib.Path.home', return_value=tmp_path):
            uploader1 = TelemetryUploader(config_enabled)
            id1 = uploader1.installation_id

            uploader2 = TelemetryUploader(config_enabled)
            id2 = uploader2.installation_id

            assert id1 == id2
```

Run tests:
```bash
pytest tests/unit/telemetry/test_uploader.py -v
pytest tests/unit/telemetry_backend/test_backend_server.py -v
```

---

### Weekend Summary

**Saturday**: Telemetry Backend
- ✅ Privacy guidelines documented
- ✅ Backend service with PII validation
- ✅ PostgreSQL schema with indexes
- ✅ Aggregate metrics API
- ✅ Tests passing

**Sunday**: Client Integration
- ✅ Telemetry uploader in Marcus
- ✅ Background upload task
- ✅ Cato global metrics dashboard
- ✅ Documentation updated
- ✅ Tests passing

**Total New Files**: 6
**Total Lines Added**: ~1,500
**Tests Added**: 15

---

## Week 5 Complete (Extended)

**Monday-Friday**: Local telemetry, research logging, CATO integration
**Saturday-Sunday**: Multi-user telemetry backend (opt-in)

**Success Criteria (Extended)**:
- ✅ All Week 5 Monday-Friday deliverables (29 tests)
- ✅ Privacy guidelines documented
- ✅ Telemetry backend service deployed
- ✅ Marcus client uploader integrated
- ✅ Cato global metrics dashboard working
- ✅ All privacy validations passing
- ✅ Opt-in only (default: disabled)
- ✅ 15 additional tests passing

**Total Week 5 (including weekend)**:
- Files added: 14
- Tests added: 44
- Test coverage: 95%+

---

**Congratulations!** Week 5 is now complete with both local telemetry (Monday-Friday) and optional multi-user telemetry backend (Saturday-Sunday). 🎉
