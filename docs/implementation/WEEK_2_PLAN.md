## Week 2: Workspace Isolation - Phase 1 (Foundation)

**Goal**: Add Feature entity and prepare infrastructure for workspace isolation without breaking existing functionality.

**Why**: Currently, Marcus only tracks tasks. We need to introduce the concept of "Features" (groups of related tasks) so we can later isolate their workspaces and aggregate their context.

**Related Design Doc**: `docs/design/workspace-isolation-and-feature-context.md`

---

### Monday: Add Project and Feature Entities to State

**What**: Add `Project` and `Feature` dataclasses to Marcus state, plus `feature_id` field to Task model.

**Why**:
- **Project**: Represents the repository being worked on
- **Feature**: Groups related tasks (1 design task + N implementation tasks + M test tasks)
- **feature_id on Task**: Links tasks to their parent feature

This creates the hierarchy: Project → Feature → Task

**How**:

#### Step 1.1: Add Project and Feature dataclasses

Create or update `src/core/project.py`:

```python
"""
Project and Feature models for Marcus.

These models represent the hierarchy:
    Project (repository) → Feature (group of tasks) → Task (individual work item)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class Project:
    """
    Represents a software project (repository).

    A project is a single Git repository where all work happens.
    Multiple features can be in progress within a project simultaneously.

    Attributes
    ----------
    project_id : str
        Unique identifier (e.g., "proj-task-api")
    name : str
        Human-readable name (e.g., "Task Management API")
    repo_url : str
        Git repository URL (e.g., "https://github.com/user/task-api")
    local_path : Path
        Local filesystem path to repository
    main_branch : str
        Main branch name (usually "main" or "master")
    created_at : datetime
        When this project was registered with Marcus
    description : Optional[str]
        Project description
    kanban_board_id : Optional[str]
        Associated Kanban board ID
    """
    project_id: str
    name: str
    repo_url: str
    local_path: Path
    main_branch: str
    created_at: datetime
    description: Optional[str] = None
    kanban_board_id: Optional[str] = None


@dataclass
class Feature:
    """
    Represents a feature within a project.

    A feature is a group of related tasks that implement one
    user-facing capability. Typically contains:
    - 1 design task (T-DESIGN-X)
    - N implementation tasks (T-IMPL-X)
    - M test tasks (T-TEST-X)

    Features enable:
    - Workspace isolation (each feature on its own branch)
    - Context aggregation (all artifacts/decisions for a feature)
    - Status tracking ("What's the status of auth?")

    Attributes
    ----------
    feature_id : str
        Unique identifier (e.g., "F-200", "feature-auth")
    feature_name : str
        Human-readable name (e.g., "User Authentication")
    project_id : str
        Parent project ID
    design_task_id : Optional[str]
        ID of the design task for this feature (e.g., "T-DESIGN-1")
    feature_branch : str
        Git branch for this feature (e.g., "feature/F-200-auth")
    status : str
        Feature status: "planning", "in_progress", "completed", "blocked"
    created_at : datetime
        When this feature was created
    completed_at : Optional[datetime]
        When this feature was completed
    description : Optional[str]
        Feature description (from PRD)
    task_ids : list[str]
        IDs of all tasks in this feature
    """
    feature_id: str
    feature_name: str
    project_id: str
    design_task_id: Optional[str]
    feature_branch: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    description: Optional[str] = None
    task_ids: list[str] = field(default_factory=list)

    def add_task(self, task_id: str) -> None:
        """Add a task to this feature."""
        if task_id not in self.task_ids:
            self.task_ids.append(task_id)

    def is_completed(self) -> bool:
        """Check if feature is completed."""
        return self.status == "completed"
```

#### Step 1.2: Add feature_id to Task model

Update `src/core/models.py`:

```python
@dataclass
class Task:
    """
    Represents a work item for an agent.

    ... existing docstring ...
    """
    id: str
    name: str
    description: str
    status: TaskStatus
    priority: Priority
    estimated_hours: float

    # ... existing fields ...

    # NEW: Link to parent feature (optional for backward compatibility)
    feature_id: Optional[str] = None
    project_id: Optional[str] = None

    def __post_init__(self):
        """Validate task after creation."""
        # ... existing validation ...

        # Log if task has no feature (debugging)
        if self.feature_id is None:
            logger.debug(f"Task {self.id} created without feature_id (legacy mode)")
```

**Why optional?**: Existing tasks don't have `feature_id`. Making it optional maintains backward compatibility.

#### Step 1.3: Extend MarcusState to track projects and features

Update `src/marcus_mcp/state.py`:

```python
from src.core.project import Project, Feature

class MarcusState:
    """
    Global state for Marcus MCP server.

    ... existing docstring ...
    """

    def __init__(self):
        # ... existing fields ...

        # NEW: Project and feature tracking
        self.projects: Dict[str, Project] = {}
        self.features: Dict[str, Feature] = {}

    async def register_project(
        self,
        name: str,
        repo_url: str,
        local_path: Path,
        main_branch: str = "main",
        description: Optional[str] = None,
        kanban_board_id: Optional[str] = None
    ) -> str:
        """
        Register a project with Marcus.

        Parameters
        ----------
        name : str
            Project name (e.g., "Task Management API")
        repo_url : str
            Git repository URL
        local_path : Path
            Local path to repository
        main_branch : str
            Main branch name (default: "main")
        description : Optional[str]
            Project description
        kanban_board_id : Optional[str]
            Associated Kanban board ID

        Returns
        -------
        str
            Generated project_id

        Example
        -------
        >>> project_id = await state.register_project(
        ...     name="Task API",
        ...     repo_url="https://github.com/user/task-api",
        ...     local_path=Path("/Users/user/projects/task-api")
        ... )
        >>> print(project_id)
        "proj-task-api"
        """
        # Generate project ID
        project_id = f"proj-{name.lower().replace(' ', '-')}"

        # Create project
        project = Project(
            project_id=project_id,
            name=name,
            repo_url=repo_url,
            local_path=local_path,
            main_branch=main_branch,
            created_at=datetime.now(timezone.utc),
            description=description,
            kanban_board_id=kanban_board_id
        )

        # Store
        self.projects[project_id] = project

        logger.info(f"Registered project: {name} (ID: {project_id})")

        return project_id

    async def create_feature(
        self,
        project_id: str,
        feature_name: str,
        description: Optional[str] = None,
        design_task_id: Optional[str] = None
    ) -> str:
        """
        Create a feature within a project.

        Parameters
        ----------
        project_id : str
            Parent project ID
        feature_name : str
            Feature name (e.g., "User Authentication")
        description : Optional[str]
            Feature description
        design_task_id : Optional[str]
            ID of design task for this feature

        Returns
        -------
        str
            Generated feature_id

        Example
        -------
        >>> feature_id = await state.create_feature(
        ...     project_id="proj-task-api",
        ...     feature_name="User Authentication",
        ...     description="JWT-based authentication system"
        ... )
        >>> print(feature_id)
        "F-200"
        """
        # Validate project exists
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")

        # Generate feature ID (sequential numbering)
        existing_count = len([f for f in self.features.values() if f.project_id == project_id])
        feature_id = f"F-{(existing_count + 1) * 100}"

        # Generate feature branch name
        feature_slug = feature_name.lower().replace(' ', '-')
        feature_branch = f"feature/{feature_id}-{feature_slug}"

        # Create feature
        feature = Feature(
            feature_id=feature_id,
            feature_name=feature_name,
            project_id=project_id,
            design_task_id=design_task_id,
            feature_branch=feature_branch,
            status="planning",
            created_at=datetime.now(timezone.utc),
            description=description
        )

        # Store
        self.features[feature_id] = feature

        logger.info(f"Created feature: {feature_name} (ID: {feature_id}, branch: {feature_branch})")

        return feature_id

    def get_feature_tasks(self, feature_id: str) -> list[Task]:
        """
        Get all tasks for a feature.

        Parameters
        ----------
        feature_id : str
            Feature ID

        Returns
        -------
        list[Task]
            All tasks belonging to this feature

        Example
        -------
        >>> tasks = state.get_feature_tasks("F-200")
        >>> print([t.name for t in tasks])
        ["Design Auth System", "Implement JWT", "Implement Login", "Auth Tests"]
        """
        return [t for t in self.project_tasks if t.feature_id == feature_id]
```

#### Step 1.4: Write tests

Create `tests/unit/core/test_project_feature.py`:

```python
"""
Unit tests for Project and Feature models.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.core.project import Feature, Project
from src.marcus_mcp.state import MarcusState


class TestProject:
    """Test suite for Project model"""

    def test_create_project(self):
        """Test creating a Project."""
        project = Project(
            project_id="proj-test",
            name="Test Project",
            repo_url="https://github.com/test/test",
            local_path=Path("/tmp/test"),
            main_branch="main",
            created_at=datetime.now(timezone.utc)
        )

        assert project.project_id == "proj-test"
        assert project.name == "Test Project"
        assert project.main_branch == "main"


class TestFeature:
    """Test suite for Feature model"""

    def test_create_feature(self):
        """Test creating a Feature."""
        feature = Feature(
            feature_id="F-100",
            feature_name="Test Feature",
            project_id="proj-test",
            design_task_id="T-DESIGN-1",
            feature_branch="feature/F-100-test",
            status="planning",
            created_at=datetime.now(timezone.utc)
        )

        assert feature.feature_id == "F-100"
        assert feature.feature_name == "Test Feature"
        assert feature.status == "planning"
        assert not feature.is_completed()

    def test_add_task_to_feature(self):
        """Test adding tasks to a feature."""
        feature = Feature(
            feature_id="F-100",
            feature_name="Test Feature",
            project_id="proj-test",
            design_task_id=None,
            feature_branch="feature/F-100-test",
            status="planning",
            created_at=datetime.now(timezone.utc)
        )

        feature.add_task("T-DESIGN-1")
        feature.add_task("T-IMPL-1")
        feature.add_task("T-IMPL-2")

        assert len(feature.task_ids) == 3
        assert "T-DESIGN-1" in feature.task_ids

        # Adding duplicate doesn't create duplicate
        feature.add_task("T-IMPL-1")
        assert len(feature.task_ids) == 3


@pytest.mark.asyncio
class TestMarcusStateProjectFeature:
    """Test project and feature management in MarcusState"""

    async def test_register_project(self):
        """Test registering a project with Marcus."""
        state = MarcusState()

        project_id = await state.register_project(
            name="Task API",
            repo_url="https://github.com/test/task-api",
            local_path=Path("/tmp/task-api")
        )

        assert project_id == "proj-task-api"
        assert project_id in state.projects

        project = state.projects[project_id]
        assert project.name == "Task API"
        assert project.main_branch == "main"

    async def test_create_feature(self):
        """Test creating a feature."""
        state = MarcusState()

        # Register project first
        project_id = await state.register_project(
            name="Task API",
            repo_url="https://github.com/test/task-api",
            local_path=Path("/tmp/task-api")
        )

        # Create feature
        feature_id = await state.create_feature(
            project_id=project_id,
            feature_name="User Authentication",
            description="JWT auth system"
        )

        assert feature_id == "F-100"  # First feature
        assert feature_id in state.features

        feature = state.features[feature_id]
        assert feature.feature_name == "User Authentication"
        assert feature.project_id == project_id
        assert feature.feature_branch == "feature/F-100-user-authentication"
        assert feature.status == "planning"

    async def test_create_multiple_features(self):
        """Test creating multiple features in a project."""
        state = MarcusState()

        project_id = await state.register_project(
            name="Task API",
            repo_url="https://github.com/test/task-api",
            local_path=Path("/tmp/task-api")
        )

        # Create multiple features
        feature_id_1 = await state.create_feature(
            project_id=project_id,
            feature_name="Authentication"
        )
        feature_id_2 = await state.create_feature(
            project_id=project_id,
            feature_name="Task Management"
        )

        assert feature_id_1 == "F-100"
        assert feature_id_2 == "F-200"

    async def test_get_feature_tasks(self):
        """Test retrieving all tasks for a feature."""
        from src.core.models import Task, TaskStatus, Priority

        state = MarcusState()

        # Add some tasks with feature_id
        task1 = Task(
            id="T-DESIGN-1",
            name="Design Auth",
            description="Design auth system",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=4.0,
            feature_id="F-100"
        )
        task2 = Task(
            id="T-IMPL-1",
            name="Implement JWT",
            description="Implement JWT tokens",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=8.0,
            feature_id="F-100"
        )
        task3 = Task(
            id="T-IMPL-2",
            name="Implement Login",
            description="Implement login endpoint",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=6.0,
            feature_id="F-200"  # Different feature
        )

        state.project_tasks = [task1, task2, task3]

        # Get tasks for F-100
        f100_tasks = state.get_feature_tasks("F-100")

        assert len(f100_tasks) == 2
        assert task1 in f100_tasks
        assert task2 in f100_tasks
        assert task3 not in f100_tasks
```

Run tests:
```bash
pytest tests/unit/core/test_project_feature.py -v
```

**Success Criteria**:
- ✅ Project and Feature dataclasses created
- ✅ `feature_id` added to Task model
- ✅ MarcusState tracks projects and features
- ✅ All tests pass
- ✅ Backward compatible (existing code still works)

---

### Tuesday: Extend Artifact and Decision Logging with Feature ID

**What**: Add `feature_id` parameter to `log_artifact()` and `log_decision()` tools so artifacts/decisions can be linked to features.

**Why**: Later, when we implement `get_feature_context()`, we need to aggregate all artifacts and decisions for a feature. We need to store the feature association now.

**How**:

#### Step 2.1: Add feature_id to log_artifact

Update `src/marcus_mcp/tools/attachment.py`:

```python
async def log_artifact(
    task_id: str,
    filename: str,
    content: str,
    artifact_type: str,
    project_root: str,
    description: str = "",
    location: Optional[str] = None,
    feature_id: Optional[str] = None,  # ⭐ NEW
    state: Any = None,
) -> Dict[str, Any]:
    """
    Store an artifact with prescriptive location management.

    ... existing docstring ...

    Parameters
    ----------
    ... existing parameters ...
    feature_id : Optional[str], optional
        Feature ID this artifact belongs to (for feature-level aggregation)

    ... rest of docstring ...
    """
    try:
        # ... existing validation ...

        # Determine storage location
        if location:
            # User specified custom location
            relative_path = location
        elif artifact_type in ARTIFACT_PATHS:
            # Use predefined location
            relative_path = ARTIFACT_PATHS[artifact_type]
        else:
            # Unknown type -> fallback to docs/artifacts/
            relative_path = "docs/artifacts"

        # Create full path
        artifact_dir = project_root_path / relative_path
        artifact_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = artifact_dir / filename

        # Write artifact
        async with aiofiles.open(artifact_path, "w") as f:
            await f.write(content)

        # Create artifact record
        artifact_record = {
            "artifact_id": f"art-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "task_id": task_id,
            "filename": filename,
            "location": str(artifact_path.relative_to(project_root_path)),
            "artifact_type": artifact_type,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": getattr(state, "current_agent_id", "unknown"),
            "storage_type": "filesystem"
        }

        # ⭐ NEW: Include feature_id if provided
        if feature_id:
            artifact_record["feature_id"] = feature_id
            logger.info(f"Artifact linked to feature {feature_id}")

        # Store in state (in-memory)
        if state and hasattr(state, "task_artifacts"):
            if task_id not in state.task_artifacts:
                state.task_artifacts[task_id] = []
            state.task_artifacts[task_id].append(artifact_record)

        # ⭐ NEW: Also store in feature artifacts if feature_id provided
        if state and feature_id and hasattr(state, "feature_artifacts"):
            if feature_id not in state.feature_artifacts:
                state.feature_artifacts[feature_id] = []
            state.feature_artifacts[feature_id].append(artifact_record)

        # Persist to artifact index
        await _persist_artifact_index(project_root_path, artifact_record)

        return {
            "success": True,
            "artifact_id": artifact_record["artifact_id"],
            "location": str(artifact_path),
            "storage_type": "filesystem",
            "message": f"Artifact stored at {artifact_path}"
        }

    except Exception as e:
        logger.error(f"Error storing artifact: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {"task_id": task_id, "filename": filename}
        }


async def _persist_artifact_index(
    project_root: Path,
    artifact_record: Dict[str, Any]
) -> None:
    """
    Persist artifact to .marcus/artifact_index.json.

    This creates a searchable index of all artifacts in the project.
    """
    index_dir = project_root / ".marcus"
    index_dir.mkdir(parents=True, exist_ok=True)

    index_file = index_dir / "artifact_index.json"

    # Load existing index
    if index_file.exists():
        async with aiofiles.open(index_file, "r") as f:
            content = await f.read()
            index = json.loads(content)
    else:
        index = {"artifacts": []}

    # Add new artifact
    index["artifacts"].append(artifact_record)

    # Save index
    async with aiofiles.open(index_file, "w") as f:
        await f.write(json.dumps(index, indent=2))
```

#### Step 2.2: Add feature_id to log_decision

Update `src/marcus_mcp/tools/context.py`:

```python
async def log_decision(
    agent_id: str,
    task_id: str,
    decision: str,
    feature_id: Optional[str] = None,  # ⭐ NEW
    state: Any = None
) -> Dict[str, Any]:
    """
    Log an architectural decision made during task implementation.

    ... existing docstring ...

    Parameters
    ----------
    ... existing parameters ...
    feature_id : Optional[str], optional
        Feature ID this decision belongs to

    ... rest of docstring ...
    """
    try:
        # Check if Context system is available
        if not hasattr(state, "context") or not state.context:
            return {"success": False, "error": "Context system not enabled"}

        # Parse decision from natural language
        parts = decision.split(".", 2)

        what = decision  # Default to full decision
        why = "Not specified"
        impact = "May affect dependent tasks"

        # Try to parse structured format
        if len(parts) >= 1 and "because" in parts[0]:
            what_parts = parts[0].split("because", 1)
            what = what_parts[0].strip()
            if len(what_parts) > 1:
                why = what_parts[1].strip()

        if len(parts) >= 2 and any(
            word in parts[1].lower() for word in ["affect", "impact", "require"]
        ):
            impact = parts[1].strip()

        # Log the decision
        logged_decision = await state.context.log_decision(
            agent_id=agent_id,
            task_id=task_id,
            what=what,
            why=why,
            impact=impact
        )

        # ⭐ NEW: Add feature_id to decision record
        if feature_id:
            logged_decision.feature_id = feature_id
            logger.info(f"Decision linked to feature {feature_id}")

        # Add comment to task if kanban is available
        if state.kanban_client:
            try:
                comment = f"🏗️ ARCHITECTURAL DECISION by {agent_id}\n"
                comment += f"Decision: {what}\n"
                comment += f"Reasoning: {why}\n"
                comment += f"Impact: {impact}"

                if feature_id:
                    comment += f"\n\nFeature: {feature_id}"

                await state.kanban_client.add_comment(task_id, comment)
            except Exception as e:
                logger.warning(f"Failed to add kanban comment for decision: {e}")

        # ⭐ NEW: Also store in feature decisions if feature_id provided
        if state and feature_id and hasattr(state, "feature_decisions"):
            if feature_id not in state.feature_decisions:
                state.feature_decisions[feature_id] = []
            state.feature_decisions[feature_id].append({
                "decision_id": logged_decision.decision_id,
                "agent_id": agent_id,
                "task_id": task_id,
                "what": what,
                "why": why,
                "impact": impact,
                "created_at": logged_decision.created_at.isoformat()
            })

        return {
            "success": True,
            "decision_id": logged_decision.decision_id,
            "message": "Decision logged and cross-referenced to dependent tasks"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
```

#### Step 2.3: Add feature artifact/decision storage to state

Update `src/marcus_mcp/state.py`:

```python
class MarcusState:
    """
    Global state for Marcus MCP server.
    """

    def __init__(self):
        # ... existing fields ...

        # Project and feature tracking
        self.projects: Dict[str, Project] = {}
        self.features: Dict[str, Feature] = {}

        # ⭐ NEW: Feature-level artifact/decision storage
        self.feature_artifacts: Dict[str, List[Dict[str, Any]]] = {}
        self.feature_decisions: Dict[str, List[Dict[str, Any]]] = {}
```

#### Step 2.4: Write tests

Add to `tests/unit/mcp/test_artifact_feature_tracking.py`:

```python
"""
Unit tests for feature-aware artifact and decision logging.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from src.marcus_mcp.tools.attachment import log_artifact
from src.marcus_mcp.tools.context import log_decision


@pytest.mark.asyncio
async def test_log_artifact_with_feature_id(tmp_path):
    """Test logging artifact with feature_id."""
    # Setup
    project_root = tmp_path / "test-project"
    project_root.mkdir()

    state = Mock()
    state.task_artifacts = {}
    state.feature_artifacts = {}
    state.current_agent_id = "test-agent"

    # Log artifact with feature_id
    result = await log_artifact(
        task_id="T-IMPL-1",
        filename="auth-design.md",
        content="# Auth Design\n\nUsing JWT tokens...",
        artifact_type="design",
        project_root=str(project_root),
        description="Authentication system design",
        feature_id="F-100",  # ⭐ Feature ID
        state=state
    )

    # Verify
    assert result["success"] is True

    # Should be in task artifacts
    assert "T-IMPL-1" in state.task_artifacts
    task_artifact = state.task_artifacts["T-IMPL-1"][0]
    assert task_artifact["feature_id"] == "F-100"

    # Should also be in feature artifacts
    assert "F-100" in state.feature_artifacts
    feature_artifact = state.feature_artifacts["F-100"][0]
    assert feature_artifact["task_id"] == "T-IMPL-1"
    assert feature_artifact["filename"] == "auth-design.md"


@pytest.mark.asyncio
async def test_log_artifact_without_feature_id(tmp_path):
    """Test logging artifact without feature_id (backward compatibility)."""
    project_root = tmp_path / "test-project"
    project_root.mkdir()

    state = Mock()
    state.task_artifacts = {}
    state.feature_artifacts = {}
    state.current_agent_id = "test-agent"

    # Log artifact WITHOUT feature_id
    result = await log_artifact(
        task_id="T-IMPL-1",
        filename="test.md",
        content="Test content",
        artifact_type="design",
        project_root=str(project_root),
        state=state
    )

    # Should still work
    assert result["success"] is True

    # Should be in task artifacts
    assert "T-IMPL-1" in state.task_artifacts
    task_artifact = state.task_artifacts["T-IMPL-1"][0]
    assert "feature_id" not in task_artifact

    # Should NOT be in feature artifacts
    assert len(state.feature_artifacts) == 0


@pytest.mark.asyncio
async def test_log_decision_with_feature_id():
    """Test logging decision with feature_id."""
    # Setup
    state = Mock()
    state.context = Mock()
    state.feature_decisions = {}

    logged_decision = Mock()
    logged_decision.decision_id = "dec-123"
    logged_decision.created_at = Mock()
    logged_decision.created_at.isoformat = Mock(return_value="2025-01-06T12:00:00Z")

    state.context.log_decision = AsyncMock(return_value=logged_decision)
    state.kanban_client = None  # Skip kanban for this test

    # Log decision with feature_id
    result = await log_decision(
        agent_id="agent-1",
        task_id="T-IMPL-1",
        decision="Using JWT tokens because they are stateless. This affects all auth endpoints.",
        feature_id="F-100",  # ⭐ Feature ID
        state=state
    )

    # Verify
    assert result["success"] is True

    # Should be in feature decisions
    assert "F-100" in state.feature_decisions
    feature_decision = state.feature_decisions["F-100"][0]
    assert feature_decision["task_id"] == "T-IMPL-1"
    assert "JWT" in feature_decision["what"]


@pytest.mark.asyncio
async def test_artifact_index_includes_feature_id(tmp_path):
    """Test that artifact index file includes feature_id."""
    project_root = tmp_path / "test-project"
    project_root.mkdir()

    state = Mock()
    state.task_artifacts = {}
    state.feature_artifacts = {}
    state.current_agent_id = "test-agent"

    # Log artifact
    await log_artifact(
        task_id="T-IMPL-1",
        filename="test.md",
        content="Test",
        artifact_type="design",
        project_root=str(project_root),
        feature_id="F-100",
        state=state
    )

    # Check artifact index file
    index_file = project_root / ".marcus" / "artifact_index.json"
    assert index_file.exists()

    import json
    with open(index_file) as f:
        index = json.load(f)

    assert len(index["artifacts"]) == 1
    artifact = index["artifacts"][0]
    assert artifact["feature_id"] == "F-100"
    assert artifact["task_id"] == "T-IMPL-1"
```

Run tests:
```bash
pytest tests/unit/mcp/test_artifact_feature_tracking.py -v
```

**Success Criteria**:
- ✅ `log_artifact` accepts `feature_id` parameter
- ✅ `log_decision` accepts `feature_id` parameter
- ✅ Artifacts/decisions stored in feature collections
- ✅ Artifact index includes `feature_id`
- ✅ Backward compatible (works without `feature_id`)
- ✅ All tests pass

---

### Wednesday: Artifact and Decision Indexing by Feature

**What**: Implement efficient querying of artifacts and decisions by feature ID.

**Why**: When we implement `get_feature_context()` next week, we need to quickly retrieve all artifacts and decisions for a feature without scanning every task.

**How**:

#### Step 3.1: Create artifact/decision query functions

Create `src/core/feature_index.py`:

```python
"""
Feature-level artifact and decision indexing.

Provides efficient querying of artifacts and decisions by feature ID.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class FeatureIndex:
    """
    Index for querying artifacts and decisions by feature.

    This class provides fast lookups for:
    - All artifacts in a feature
    - All decisions in a feature
    - Cross-feature queries

    Data is stored in .marcus/feature_index.json
    """

    def __init__(self, project_root: Path):
        """
        Initialize feature index.

        Parameters
        ----------
        project_root : Path
            Root directory of the project
        """
        self.project_root = project_root
        self.index_dir = project_root / ".marcus"
        self.index_file = self.index_dir / "feature_index.json"
        self._cache: Optional[Dict[str, Any]] = None

    def _load_index(self) -> Dict[str, Any]:
        """Load index from disk or create empty."""
        if self._cache is not None:
            return self._cache

        if self.index_file.exists():
            with open(self.index_file) as f:
                self._cache = json.load(f)
        else:
            self._cache = {
                "features": {},
                "artifacts": [],
                "decisions": []
            }

        return self._cache

    def _save_index(self) -> None:
        """Save index to disk."""
        self.index_dir.mkdir(parents=True, exist_ok=True)

        with open(self.index_file, "w") as f:
            json.dump(self._cache, f, indent=2)

    def add_artifact(
        self,
        artifact_id: str,
        task_id: str,
        feature_id: str,
        filename: str,
        location: str,
        artifact_type: str
    ) -> None:
        """
        Add artifact to feature index.

        Parameters
        ----------
        artifact_id : str
            Unique artifact ID
        task_id : str
            Task that created this artifact
        feature_id : str
            Feature this artifact belongs to
        filename : str
            Artifact filename
        location : str
            Filesystem location
        artifact_type : str
            Type of artifact (design, api, implementation, etc.)
        """
        index = self._load_index()

        # Add to artifacts list
        index["artifacts"].append({
            "artifact_id": artifact_id,
            "task_id": task_id,
            "feature_id": feature_id,
            "filename": filename,
            "location": location,
            "artifact_type": artifact_type
        })

        # Update feature entry
        if feature_id not in index["features"]:
            index["features"][feature_id] = {
                "artifact_ids": [],
                "decision_ids": [],
                "task_ids": set()
            }

        index["features"][feature_id]["artifact_ids"].append(artifact_id)
        index["features"][feature_id]["task_ids"].add(task_id)

        # Convert set to list for JSON serialization
        index["features"][feature_id]["task_ids"] = list(
            index["features"][feature_id]["task_ids"]
        )

        self._save_index()

    def add_decision(
        self,
        decision_id: str,
        task_id: str,
        feature_id: str,
        what: str,
        why: str,
        agent_id: str
    ) -> None:
        """
        Add decision to feature index.

        Parameters
        ----------
        decision_id : str
            Unique decision ID
        task_id : str
            Task that made this decision
        feature_id : str
            Feature this decision belongs to
        what : str
            What was decided
        why : str
            Why it was decided
        agent_id : str
            Agent who made the decision
        """
        index = self._load_index()

        # Add to decisions list
        index["decisions"].append({
            "decision_id": decision_id,
            "task_id": task_id,
            "feature_id": feature_id,
            "what": what,
            "why": why,
            "agent_id": agent_id
        })

        # Update feature entry
        if feature_id not in index["features"]:
            index["features"][feature_id] = {
                "artifact_ids": [],
                "decision_ids": [],
                "task_ids": set()
            }

        index["features"][feature_id]["decision_ids"].append(decision_id)
        index["features"][feature_id]["task_ids"].add(task_id)

        # Convert set to list for JSON serialization
        index["features"][feature_id]["task_ids"] = list(
            index["features"][feature_id]["task_ids"]
        )

        self._save_index()

    def get_feature_artifacts(self, feature_id: str) -> List[Dict[str, Any]]:
        """
        Get all artifacts for a feature.

        Parameters
        ----------
        feature_id : str
            Feature ID to query

        Returns
        -------
        List[Dict[str, Any]]
            All artifacts belonging to this feature

        Example
        -------
        >>> index = FeatureIndex(Path("/project"))
        >>> artifacts = index.get_feature_artifacts("F-100")
        >>> print([a["filename"] for a in artifacts])
        ["auth-design.md", "jwt-implementation.py", "auth-tests.py"]
        """
        index = self._load_index()

        if feature_id not in index["features"]:
            return []

        artifact_ids = index["features"][feature_id]["artifact_ids"]

        # Retrieve full artifact records
        return [
            a for a in index["artifacts"]
            if a["artifact_id"] in artifact_ids
        ]

    def get_feature_decisions(self, feature_id: str) -> List[Dict[str, Any]]:
        """
        Get all decisions for a feature.

        Parameters
        ----------
        feature_id : str
            Feature ID to query

        Returns
        -------
        List[Dict[str, Any]]
            All decisions made for this feature
        """
        index = self._load_index()

        if feature_id not in index["features"]:
            return []

        decision_ids = index["features"][feature_id]["decision_ids"]

        # Retrieve full decision records
        return [
            d for d in index["decisions"]
            if d["decision_id"] in decision_ids
        ]

    def get_feature_summary(self, feature_id: str) -> Dict[str, Any]:
        """
        Get summary of feature contents.

        Parameters
        ----------
        feature_id : str
            Feature ID to query

        Returns
        -------
        Dict[str, Any]
            Summary including artifact count, decision count, task IDs
        """
        index = self._load_index()

        if feature_id not in index["features"]:
            return {
                "feature_id": feature_id,
                "exists": False,
                "artifact_count": 0,
                "decision_count": 0,
                "task_count": 0
            }

        feature_data = index["features"][feature_id]

        return {
            "feature_id": feature_id,
            "exists": True,
            "artifact_count": len(feature_data["artifact_ids"]),
            "decision_count": len(feature_data["decision_ids"]),
            "task_count": len(feature_data["task_ids"]),
            "task_ids": feature_data["task_ids"]
        }
```

#### Step 3.2: Integrate with log_artifact and log_decision

Update `src/marcus_mcp/tools/attachment.py`:

```python
from src.core.feature_index import FeatureIndex

async def log_artifact(
    task_id: str,
    filename: str,
    content: str,
    artifact_type: str,
    project_root: str,
    description: str = "",
    location: Optional[str] = None,
    feature_id: Optional[str] = None,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Store an artifact with prescriptive location management.

    ... existing code ...
    """
    try:
        # ... existing artifact storage code ...

        # ⭐ NEW: Update feature index if feature_id provided
        if feature_id:
            feature_index = FeatureIndex(project_root_path)
            feature_index.add_artifact(
                artifact_id=artifact_record["artifact_id"],
                task_id=task_id,
                feature_id=feature_id,
                filename=filename,
                location=artifact_record["location"],
                artifact_type=artifact_type
            )

        return {
            "success": True,
            "artifact_id": artifact_record["artifact_id"],
            "location": str(artifact_path),
            "storage_type": "filesystem",
            "message": f"Artifact stored at {artifact_path}"
        }

    except Exception as e:
        # ... error handling ...
```

Similarly update `log_decision` in `src/marcus_mcp/tools/context.py`.

#### Step 3.3: Write tests

Create `tests/unit/core/test_feature_index.py`:

```python
"""
Unit tests for FeatureIndex.
"""

import json
from pathlib import Path

import pytest

from src.core.feature_index import FeatureIndex


class TestFeatureIndex:
    """Test suite for FeatureIndex"""

    def test_create_feature_index(self, tmp_path):
        """Test creating a feature index."""
        index = FeatureIndex(tmp_path)

        # Index file doesn't exist yet
        assert not index.index_file.exists()

        # Loading creates empty structure
        data = index._load_index()
        assert "features" in data
        assert "artifacts" in data
        assert "decisions" in data

    def test_add_artifact_to_index(self, tmp_path):
        """Test adding an artifact to the index."""
        index = FeatureIndex(tmp_path)

        index.add_artifact(
            artifact_id="art-001",
            task_id="T-IMPL-1",
            feature_id="F-100",
            filename="auth-design.md",
            location="docs/design/auth-design.md",
            artifact_type="design"
        )

        # Index file should exist now
        assert index.index_file.exists()

        # Should be queryable
        artifacts = index.get_feature_artifacts("F-100")
        assert len(artifacts) == 1
        assert artifacts[0]["artifact_id"] == "art-001"
        assert artifacts[0]["filename"] == "auth-design.md"

    def test_add_multiple_artifacts_to_feature(self, tmp_path):
        """Test adding multiple artifacts to same feature."""
        index = FeatureIndex(tmp_path)

        index.add_artifact(
            artifact_id="art-001",
            task_id="T-DESIGN-1",
            feature_id="F-100",
            filename="design.md",
            location="docs/design/design.md",
            artifact_type="design"
        )

        index.add_artifact(
            artifact_id="art-002",
            task_id="T-IMPL-1",
            feature_id="F-100",
            filename="implementation.py",
            location="src/auth/implementation.py",
            artifact_type="implementation"
        )

        # Should have both artifacts
        artifacts = index.get_feature_artifacts("F-100")
        assert len(artifacts) == 2
        filenames = [a["filename"] for a in artifacts]
        assert "design.md" in filenames
        assert "implementation.py" in filenames

    def test_add_decision_to_index(self, tmp_path):
        """Test adding a decision to the index."""
        index = FeatureIndex(tmp_path)

        index.add_decision(
            decision_id="dec-001",
            task_id="T-IMPL-1",
            feature_id="F-100",
            what="Use JWT tokens",
            why="Stateless and scalable",
            agent_id="agent-1"
        )

        # Should be queryable
        decisions = index.get_feature_decisions("F-100")
        assert len(decisions) == 1
        assert decisions[0]["decision_id"] == "dec-001"
        assert "JWT" in decisions[0]["what"]

    def test_get_feature_summary(self, tmp_path):
        """Test getting feature summary."""
        index = FeatureIndex(tmp_path)

        # Add artifacts and decisions
        index.add_artifact(
            artifact_id="art-001",
            task_id="T-DESIGN-1",
            feature_id="F-100",
            filename="design.md",
            location="docs/design.md",
            artifact_type="design"
        )

        index.add_artifact(
            artifact_id="art-002",
            task_id="T-IMPL-1",
            feature_id="F-100",
            filename="impl.py",
            location="src/impl.py",
            artifact_type="implementation"
        )

        index.add_decision(
            decision_id="dec-001",
            task_id="T-IMPL-1",
            feature_id="F-100",
            what="Decision 1",
            why="Reason 1",
            agent_id="agent-1"
        )

        # Get summary
        summary = index.get_feature_summary("F-100")

        assert summary["exists"] is True
        assert summary["artifact_count"] == 2
        assert summary["decision_count"] == 1
        assert summary["task_count"] == 2
        assert set(summary["task_ids"]) == {"T-DESIGN-1", "T-IMPL-1"}

    def test_query_nonexistent_feature(self, tmp_path):
        """Test querying a feature that doesn't exist."""
        index = FeatureIndex(tmp_path)

        artifacts = index.get_feature_artifacts("F-999")
        decisions = index.get_feature_decisions("F-999")
        summary = index.get_feature_summary("F-999")

        assert artifacts == []
        assert decisions == []
        assert summary["exists"] is False
        assert summary["artifact_count"] == 0

    def test_index_persists_across_instances(self, tmp_path):
        """Test that index persists when creating new instance."""
        # Create first instance and add data
        index1 = FeatureIndex(tmp_path)
        index1.add_artifact(
            artifact_id="art-001",
            task_id="T-IMPL-1",
            feature_id="F-100",
            filename="test.md",
            location="docs/test.md",
            artifact_type="design"
        )

        # Create second instance (should load from disk)
        index2 = FeatureIndex(tmp_path)
        artifacts = index2.get_feature_artifacts("F-100")

        # Should have the artifact
        assert len(artifacts) == 1
        assert artifacts[0]["artifact_id"] == "art-001"
```

Run tests:
```bash
pytest tests/unit/core/test_feature_index.py -v
```

**Success Criteria**:
- ✅ FeatureIndex class created
- ✅ Efficient querying by feature ID
- ✅ Persists to .marcus/feature_index.json
- ✅ Integrated with log_artifact and log_decision
- ✅ All tests pass

---

### Thursday: Create WorkspaceManager Skeleton

**What**: Build the basic structure for WorkspaceManager that will handle git worktree-based task workspaces.

**Why**: Next week we'll implement the full workspace isolation logic. Today we create the skeleton with the interface that other code will use, allowing us to test integration points before building complex git logic.

**How**:

#### Step 4.1: Create workspace module

```bash
mkdir -p src/workspace
touch src/workspace/__init__.py
touch src/workspace/manager.py
```

#### Step 4.2: Define WorkspaceManager interface

Create `src/workspace/manager.py`:

```python
"""
Workspace manager for git worktree-based task isolation.

Provides safe, isolated workspaces for parallel task execution.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from src.core.models import Task

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceInfo:
    """
    Information about a task workspace.

    Attributes
    ----------
    task_id : str
        Task identifier
    feature_id : str
        Feature identifier
    workspace_path : Path
        Absolute path to worktree workspace
    feature_branch : str
        Git branch for the feature (e.g., "feature/F-200-auth")
    is_active : bool
        Whether workspace is currently in use
    created_at : str
        ISO timestamp of creation
    """

    task_id: str
    feature_id: str
    workspace_path: Path
    feature_branch: str
    is_active: bool
    created_at: str


class WorkspaceManager:
    """
    Manages git worktree-based workspaces for task isolation.

    Each task gets its own workspace (git worktree) on the feature branch.
    This prevents file conflicts when multiple agents work in parallel.

    Features:
    - Automatic feature branch creation
    - Git worktree management
    - Workspace cleanup
    - Conflict prevention

    Example
    -------
    >>> manager = WorkspaceManager(project_root=Path("/path/to/repo"))
    >>> workspace = await manager.create_workspace(task, feature)
    >>> # Agent works in workspace.workspace_path
    >>> await manager.cleanup_workspace(task.id)
    """

    def __init__(self, project_root: Path):
        """
        Initialize workspace manager.

        Parameters
        ----------
        project_root : Path
            Root directory of the git repository
        """
        self.project_root = project_root
        self.worktrees_dir = project_root / ".marcus" / "worktrees"
        self.active_workspaces: Dict[str, WorkspaceInfo] = {}

        logger.info(f"WorkspaceManager initialized for {project_root}")

    async def create_workspace(
        self, task: Task, feature_branch: str
    ) -> WorkspaceInfo:
        """
        Create isolated workspace for a task.

        This will:
        1. Create feature branch if it doesn't exist
        2. Create git worktree for the task
        3. Track the workspace as active

        Parameters
        ----------
        task : Task
            Task that needs a workspace
        feature_branch : str
            Feature branch name (e.g., "feature/F-200-auth")

        Returns
        -------
        WorkspaceInfo
            Information about the created workspace

        Raises
        ------
        WorkspaceError
            If workspace creation fails
        """
        # Implementation will be added next week
        logger.info(
            f"create_workspace called for task {task.id} "
            f"on branch {feature_branch}"
        )
        raise NotImplementedError("Will be implemented in Week 3")

    async def cleanup_workspace(self, task_id: str) -> None:
        """
        Clean up workspace after task completion.

        This will:
        1. Remove the git worktree
        2. Clean up metadata
        3. Mark workspace as inactive

        Parameters
        ----------
        task_id : str
            Task whose workspace should be cleaned up

        Raises
        ------
        WorkspaceError
            If cleanup fails
        """
        # Implementation will be added next week
        logger.info(f"cleanup_workspace called for task {task_id}")
        raise NotImplementedError("Will be implemented in Week 3")

    async def get_workspace(self, task_id: str) -> Optional[WorkspaceInfo]:
        """
        Get workspace information for a task.

        Parameters
        ----------
        task_id : str
            Task identifier

        Returns
        -------
        Optional[WorkspaceInfo]
            Workspace info if exists, None otherwise
        """
        return self.active_workspaces.get(task_id)

    async def list_active_workspaces(self) -> list[WorkspaceInfo]:
        """
        List all active workspaces.

        Returns
        -------
        list[WorkspaceInfo]
            List of active workspace information
        """
        return list(self.active_workspaces.values())


class WorkspaceError(Exception):
    """Raised when workspace operations fail."""

    pass
```

#### Step 4.3: Add WorkspaceManager to State

Update `src/marcus_mcp/state.py` to include WorkspaceManager:

```python
from src.workspace.manager import WorkspaceManager

class MarcusState:
    def __init__(self, storage_dir: str = "data"):
        # ... existing initialization ...

        # Add workspace manager (if in workspace isolation mode)
        self.workspace_manager: Optional[WorkspaceManager] = None

    async def initialize_workspace_manager(
        self, project_root: Path
    ) -> None:
        """
        Initialize workspace manager for a project.

        Parameters
        ----------
        project_root : Path
            Root directory of the git repository
        """
        from src.workspace.manager import WorkspaceManager

        self.workspace_manager = WorkspaceManager(project_root)
        logger.info(f"Workspace manager initialized for {project_root}")
```

#### Step 4.4: Write skeleton tests

Create `tests/unit/workspace/test_manager_skeleton.py`:

```python
"""
Tests for WorkspaceManager skeleton.

Tests the interface, not the implementation (which comes next week).
"""

import pytest
from pathlib import Path
from datetime import datetime

from src.workspace.manager import WorkspaceManager, WorkspaceInfo, WorkspaceError
from src.core.models import Task, TaskStatus, Priority


class TestWorkspaceManagerSkeleton:
    """Test WorkspaceManager interface"""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create WorkspaceManager instance."""
        return WorkspaceManager(project_root=tmp_path)

    @pytest.fixture
    def sample_task(self):
        """Create sample task."""
        return Task(
            id="T-IMPL-1",
            name="Implement authentication",
            description="Add JWT authentication",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=8.0,
            labels=["feature", "auth"],
            feature_id="F-200"
        )

    def test_manager_initialization(self, tmp_path):
        """Test that WorkspaceManager initializes."""
        manager = WorkspaceManager(project_root=tmp_path)

        assert manager.project_root == tmp_path
        assert manager.worktrees_dir == tmp_path / ".marcus" / "worktrees"
        assert manager.active_workspaces == {}

    @pytest.mark.asyncio
    async def test_create_workspace_not_implemented(
        self, manager, sample_task
    ):
        """Test that create_workspace raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await manager.create_workspace(
                task=sample_task,
                feature_branch="feature/F-200-auth"
            )

    @pytest.mark.asyncio
    async def test_cleanup_workspace_not_implemented(self, manager):
        """Test that cleanup_workspace raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await manager.cleanup_workspace(task_id="T-IMPL-1")

    @pytest.mark.asyncio
    async def test_get_workspace_returns_none_when_empty(self, manager):
        """Test that get_workspace returns None when no workspace."""
        result = await manager.get_workspace(task_id="T-IMPL-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_active_workspaces_empty(self, manager):
        """Test that list_active_workspaces returns empty list."""
        workspaces = await manager.list_active_workspaces()
        assert workspaces == []

    def test_workspace_info_dataclass(self):
        """Test WorkspaceInfo dataclass."""
        info = WorkspaceInfo(
            task_id="T-IMPL-1",
            feature_id="F-200",
            workspace_path=Path("/tmp/workspace"),
            feature_branch="feature/F-200-auth",
            is_active=True,
            created_at="2025-01-06T10:00:00Z"
        )

        assert info.task_id == "T-IMPL-1"
        assert info.feature_id == "F-200"
        assert info.is_active is True
```

Run tests:
```bash
pytest tests/unit/workspace/test_manager_skeleton.py -v
```

**Success Criteria**:
- ✅ WorkspaceManager skeleton created with clear interface
- ✅ WorkspaceInfo dataclass defined
- ✅ Integration point in State added
- ✅ Tests verify interface (not implementation)
- ✅ All tests pass

---

### Friday: Week 2 Integration & Testing

**What**: Integrate Week 2 components, write integration tests, and prepare for Week 3.

**Why**: Before building complex workspace logic next week, we need to ensure that Project, Feature, and artifact tracking all work together correctly.

**How**:

#### Step 5.1: Create integration test

Create `tests/integration/test_feature_tracking_integration.py`:

```python
"""
Integration test for Week 2 feature tracking components.

Tests that Project, Feature, artifact logging, and indexing work together.
"""

import pytest
from datetime import datetime
from pathlib import Path

from src.marcus_mcp.state import MarcusState
from src.core.models import Task, TaskStatus, Priority, Project, Feature
from src.core.feature_index import FeatureIndex


class TestFeatureTrackingIntegration:
    """Integration tests for feature tracking"""

    @pytest.fixture
    async def state_with_project(self, tmp_path):
        """Create state with a project."""
        state = MarcusState(storage_dir=str(tmp_path / "data"))
        await state.initialize()

        # Create project
        project = Project(
            project_id="proj-001",
            name="Test Project",
            repo_url="https://github.com/test/repo",
            local_path=tmp_path / "repo",
            main_branch="main",
            created_at=datetime.now().isoformat()
        )
        state.projects[project.project_id] = project

        return state

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_feature_workflow(self, state_with_project, tmp_path):
        """Test complete workflow: project → feature → tasks → artifacts."""
        state = state_with_project

        # Step 1: Create feature
        feature = Feature(
            feature_id="F-100",
            feature_name="Authentication",
            project_id="proj-001",
            feature_branch="feature/F-100-auth",
            status="in_progress",
            task_ids=[]
        )
        state.features[feature.feature_id] = feature

        # Step 2: Create tasks for feature
        design_task = Task(
            id="T-DESIGN-1",
            name="Design authentication",
            description="Design JWT authentication",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=6.0,
            labels=["design", "auth"],
            feature_id="F-100",
            project_id="proj-001"
        )

        impl_task = Task(
            id="T-IMPL-1",
            name="Implement authentication",
            description="Implement JWT authentication",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=8.0,
            labels=["feature", "auth"],
            feature_id="F-100",
            project_id="proj-001"
        )

        feature.task_ids = [design_task.id, impl_task.id]

        # Step 3: Log artifacts for tasks
        from src.marcus_mcp.tools.context import log_artifact

        artifact1_result = await log_artifact(
            task_id=design_task.id,
            filename="auth-design.md",
            content="# Authentication Design\n\nUse JWT...",
            artifact_type="design",
            project_root=str(tmp_path / "repo"),
            feature_id="F-100",
            state=state
        )

        artifact2_result = await log_artifact(
            task_id=impl_task.id,
            filename="auth.py",
            content="def authenticate(token): ...",
            artifact_type="implementation",
            project_root=str(tmp_path / "repo"),
            feature_id="F-100",
            state=state
        )

        # Step 4: Query feature index
        index = FeatureIndex(tmp_path / "repo")

        feature_artifacts = index.get_feature_artifacts("F-100")
        assert len(feature_artifacts) == 2

        feature_summary = index.get_feature_summary("F-100")
        assert feature_summary["artifact_count"] == 2
        assert feature_summary["task_count"] == 2
        assert set(feature_summary["task_ids"]) == {
            "T-DESIGN-1",
            "T-IMPL-1"
        }

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_feature_without_artifacts_queryable(
        self, state_with_project, tmp_path
    ):
        """Test that features without artifacts still queryable."""
        state = state_with_project

        # Create feature with no artifacts
        feature = Feature(
            feature_id="F-200",
            feature_name="Empty Feature",
            project_id="proj-001",
            feature_branch="feature/F-200-empty",
            status="todo",
            task_ids=["T-TEST-1"]
        )
        state.features[feature.feature_id] = feature

        # Query should work (but return empty)
        index = FeatureIndex(tmp_path / "repo")
        artifacts = index.get_feature_artifacts("F-200")
        summary = index.get_feature_summary("F-200")

        assert artifacts == []
        assert summary["exists"] is False  # No index entry yet

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_backward_compatibility_no_feature_id(
        self, state_with_project, tmp_path
    ):
        """Test that artifacts without feature_id still work."""
        state = state_with_project

        # Log artifact without feature_id (legacy path)
        from src.marcus_mcp.tools.context import log_artifact

        result = await log_artifact(
            task_id="T-LEGACY-1",
            filename="legacy.md",
            content="Legacy content",
            artifact_type="design",
            project_root=str(tmp_path / "repo"),
            state=state
            # Note: no feature_id parameter
        )

        assert result["success"] is True
        # Should still create artifact file
        assert Path(result["artifact"]["location"]).exists()
```

Run integration tests:
```bash
pytest tests/integration/test_feature_tracking_integration.py -v
```

#### Step 5.2: Update documentation

Create `docs/features/FEATURE_TRACKING.md`:

```markdown
# Feature Tracking

**Status**: Implemented (Week 2)
**Version**: 1.0

## Overview

Marcus now supports grouping tasks into **features** for better organization and traceability.

## Key Concepts

### Feature
A feature groups related tasks:
- 1 design task
- N implementation tasks
- M test tasks

Each feature gets its own git branch (e.g., `feature/F-200-auth`).

### Project
A project represents a git repository that Marcus manages.

### Feature Index
Fast lookup of artifacts and decisions by feature ID.

## Usage

### Creating a Feature

```python
from src.core.models import Feature

feature = Feature(
    feature_id="F-100",
    feature_name="Authentication",
    project_id="proj-001",
    feature_branch="feature/F-100-auth",
    status="in_progress",
    task_ids=["T-DESIGN-1", "T-IMPL-1"]
)

state.features[feature.feature_id] = feature
```

### Logging Artifacts with Feature ID

```python
from src.marcus_mcp.tools.context import log_artifact

result = await log_artifact(
    task_id="T-IMPL-1",
    filename="auth.py",
    content="...",
    artifact_type="implementation",
    project_root="/path/to/repo",
    feature_id="F-100",  # <-- Link to feature
    state=state
)
```

### Querying Feature Artifacts

```python
from src.core.feature_index import FeatureIndex

index = FeatureIndex(project_root)

# Get all artifacts for feature
artifacts = index.get_feature_artifacts("F-100")

# Get feature summary
summary = index.get_feature_summary("F-100")
print(f"Feature has {summary['artifact_count']} artifacts")
print(f"Feature has {summary['decision_count']} decisions")
```

## Storage

- **Projects**: `data/projects.json`
- **Features**: `data/features.json`
- **Artifacts**: `docs/artifacts/{task_id}/`
- **Feature Index**: `.marcus/feature_index.json`

## Next Steps (Week 3)

- Implement WorkspaceManager (git worktree creation)
- Automatic feature branch creation
- Workspace cleanup on task completion
```

#### Step 5.3: Run full test suite

```bash
# Unit tests
pytest tests/unit/core/test_project_feature_models.py -v
pytest tests/unit/mcp/test_artifact_feature_tracking.py -v
pytest tests/unit/core/test_feature_index.py -v
pytest tests/unit/workspace/test_manager_skeleton.py -v

# Integration tests
pytest tests/integration/test_feature_tracking_integration.py -v

# Check coverage
pytest tests/unit/ tests/integration/ --cov=src --cov-report=term-missing
```

**Success Criteria**:
- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ Coverage >= 80% for new code
- ✅ Documentation complete
- ✅ Ready to start Week 3 (WorkspaceManager implementation)

---
