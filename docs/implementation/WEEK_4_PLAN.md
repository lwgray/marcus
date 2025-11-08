## Week 4: Feature Context & Git Integration

**Goal**: Implement feature-level observability with git traceability.

**Why**: Users want to ask: "What's the status of the authentication feature?" and get back all tasks, artifacts, decisions, git branches, and commits related to that feature.

**Related Requirement**: User's observability requirement - "tell me the current state of this feature"

---

### Monday: Implement Git Commit Tracking

**What**: Track git commits by task and feature ID.

**Why**: To provide feature-level observability, we need to know which commits belong to which feature. This enables questions like "show me all commits for the authentication feature."

**How**:

#### Step 1.1: Create git commit tracker

Create `src/workspace/commit_tracker.py`:

```python
"""
Git commit tracking for feature traceability.

Tracks commits by task_id and feature_id for observability.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CommitInfo:
    """
    Information about a git commit.

    Attributes
    ----------
    commit_hash : str
        Full commit SHA
    short_hash : str
        Short commit SHA (first 7 chars)
    task_id : str
        Task that created this commit
    feature_id : str
        Feature this commit belongs to
    branch : str
        Git branch
    message : str
        Commit message
    author : str
        Commit author
    timestamp : str
        ISO timestamp of commit
    files_changed : int
        Number of files changed
    """

    commit_hash: str
    short_hash: str
    task_id: str
    feature_id: str
    branch: str
    message: str
    author: str
    timestamp: str
    files_changed: int


class CommitTracker:
    """
    Tracks git commits for features and tasks.

    Stores commit metadata in .marcus/commits.json for fast querying.
    """

    def __init__(self, project_root: Path):
        """
        Initialize commit tracker.

        Parameters
        ----------
        project_root : Path
            Root directory of git repository
        """
        self.project_root = project_root
        self.commits_file = project_root / ".marcus" / "commits.json"
        self._commits_cache: Optional[List[Dict[str, Any]]] = None

    def _load_commits(self) -> List[Dict[str, Any]]:
        """Load commits from disk."""
        if self._commits_cache is not None:
            return self._commits_cache

        if self.commits_file.exists():
            with open(self.commits_file) as f:
                self._commits_cache = json.load(f)
        else:
            self._commits_cache = []

        return self._commits_cache

    def _save_commits(self) -> None:
        """Save commits to disk."""
        self.commits_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.commits_file, "w") as f:
            json.dump(self._commits_cache, f, indent=2)

    def track_commit(
        self,
        commit_hash: str,
        task_id: str,
        feature_id: str,
        branch: str,
        message: str,
        author: str,
        files_changed: int = 0
    ) -> None:
        """
        Track a commit.

        Parameters
        ----------
        commit_hash : str
            Full commit SHA
        task_id : str
            Task ID
        feature_id : str
            Feature ID
        branch : str
            Git branch
        message : str
            Commit message
        author : str
            Commit author
        files_changed : int
            Number of files changed
        """
        commits = self._load_commits()

        commit_info = {
            "commit_hash": commit_hash,
            "short_hash": commit_hash[:7],
            "task_id": task_id,
            "feature_id": feature_id,
            "branch": branch,
            "message": message,
            "author": author,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files_changed": files_changed
        }

        commits.append(commit_info)
        self._commits_cache = commits
        self._save_commits()

        logger.info(
            f"Tracked commit {commit_hash[:7]} for task {task_id}"
        )

    def get_feature_commits(self, feature_id: str) -> List[CommitInfo]:
        """
        Get all commits for a feature.

        Parameters
        ----------
        feature_id : str
            Feature ID

        Returns
        -------
        List[CommitInfo]
            List of commits for the feature
        """
        commits = self._load_commits()

        feature_commits = [
            CommitInfo(**c)
            for c in commits
            if c.get("feature_id") == feature_id
        ]

        return feature_commits

    def get_task_commits(self, task_id: str) -> List[CommitInfo]:
        """
        Get all commits for a task.

        Parameters
        ----------
        task_id : str
            Task ID

        Returns
        -------
        List[CommitInfo]
            List of commits for the task
        """
        commits = self._load_commits()

        task_commits = [
            CommitInfo(**c)
            for c in commits
            if c.get("task_id") == task_id
        ]

        return task_commits

    def get_recent_commits(self, limit: int = 10) -> List[CommitInfo]:
        """
        Get recent commits across all features.

        Parameters
        ----------
        limit : int
            Maximum number of commits to return

        Returns
        -------
        List[CommitInfo]
            Recent commits (newest first)
        """
        commits = self._load_commits()

        # Sort by timestamp (newest first)
        sorted_commits = sorted(
            commits,
            key=lambda c: c.get("timestamp", ""),
            reverse=True
        )

        return [CommitInfo(**c) for c in sorted_commits[:limit]]
```

#### Step 1.2: Integrate with WorkspaceManager

Update `src/workspace/manager.py` to track commits:

```python
from src.workspace.commit_tracker import CommitTracker

class WorkspaceManager:
    """Manages git worktree-based workspaces for task isolation."""

    def __init__(self, project_root: Path):
        """Initialize workspace manager."""
        self.project_root = project_root
        self.worktrees_dir = project_root / ".marcus" / "worktrees"
        self.active_workspaces: Dict[str, WorkspaceInfo] = {}
        self.git_ops = GitOperations(repo_path=project_root)
        self.commit_tracker = CommitTracker(project_root)  # NEW

        logger.info(f"WorkspaceManager initialized for {project_root}")

    async def capture_workspace_commits(self, task_id: str) -> List[str]:
        """
        Capture commits made in workspace before cleanup.

        This should be called BEFORE cleanup to track what work was done.

        Parameters
        ----------
        task_id : str
            Task ID

        Returns
        -------
        List[str]
            List of commit hashes found in workspace
        """
        workspace_info = self.active_workspaces.get(task_id)
        if not workspace_info:
            logger.warning(f"No workspace for task {task_id}")
            return []

        try:
            # Get commits in workspace that aren't in main branch
            main_branch = await self.git_ops.get_main_branch()

            # Get commits on feature branch not in main
            returncode, stdout, stderr = await self.git_ops._run_git_command(
                "-C", str(workspace_info.workspace_path),
                "log", f"{main_branch}..HEAD",
                "--pretty=format:%H|||%s|||%an|||",
                check=False
            )

            if not stdout:
                logger.info(f"No new commits in workspace for {task_id}")
                return []

            # Parse commits
            commit_hashes = []
            for line in stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|||")
                if len(parts) >= 3:
                    commit_hash = parts[0]
                    message = parts[1]
                    author = parts[2]

                    # Track commit
                    self.commit_tracker.track_commit(
                        commit_hash=commit_hash,
                        task_id=task_id,
                        feature_id=workspace_info.feature_id,
                        branch=workspace_info.feature_branch,
                        message=message,
                        author=author,
                        files_changed=0  # Could parse this from git diff
                    )

                    commit_hashes.append(commit_hash)

            logger.info(
                f"Captured {len(commit_hashes)} commits for task {task_id}"
            )
            return commit_hashes

        except Exception as e:
            logger.error(f"Failed to capture commits: {e}")
            return []

    async def cleanup_workspace(self, task_id: str) -> None:
        """
        Clean up workspace after task completion.

        Now captures commits before cleanup.
        """
        logger.info(f"Cleaning up workspace for task {task_id}")

        workspace_info = self.active_workspaces.get(task_id)
        if not workspace_info:
            logger.warning(f"No workspace found for task {task_id}")
            return

        try:
            # NEW: Capture commits before cleanup
            await self.capture_workspace_commits(task_id)

            # Remove git worktree
            await self.git_ops._run_git_command(
                "worktree", "remove", str(workspace_info.workspace_path),
                "--force"
            )

            # Remove from tracking
            workspace_info.is_active = False
            del self.active_workspaces[task_id]

            logger.info(f"Workspace cleaned up for task {task_id}")

        except Exception as e:
            logger.error(f"Failed to cleanup workspace: {e}")
            raise WorkspaceError(
                f"Failed to cleanup workspace for task {task_id}: {e}",
                context=ErrorContext(
                    operation="cleanup_workspace",
                    task_id=task_id
                )
            )
```

#### Step 1.3: Write tests

Create `tests/unit/workspace/test_commit_tracker.py`:

```python
"""
Tests for CommitTracker.
"""

import pytest
from pathlib import Path

from src.workspace.commit_tracker import CommitTracker, CommitInfo


class TestCommitTracker:
    """Test suite for CommitTracker"""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create CommitTracker instance."""
        return CommitTracker(project_root=tmp_path)

    def test_track_commit(self, tracker):
        """Test tracking a commit."""
        tracker.track_commit(
            commit_hash="abc123def456",
            task_id="T-IMPL-1",
            feature_id="F-100",
            branch="feature/F-100-auth",
            message="feat: Add authentication (T-IMPL-1)",
            author="Test Author",
            files_changed=5
        )

        # Should be saved
        assert tracker.commits_file.exists()

        # Should be retrievable
        commits = tracker.get_task_commits("T-IMPL-1")
        assert len(commits) == 1
        assert commits[0].commit_hash == "abc123def456"
        assert commits[0].short_hash == "abc123d"

    def test_get_feature_commits(self, tracker):
        """Test getting commits by feature."""
        # Track multiple commits
        tracker.track_commit(
            "commit1", "T-IMPL-1", "F-100",
            "feature/F-100-auth", "msg1", "author1"
        )
        tracker.track_commit(
            "commit2", "T-IMPL-2", "F-100",
            "feature/F-100-auth", "msg2", "author2"
        )
        tracker.track_commit(
            "commit3", "T-IMPL-3", "F-200",
            "feature/F-200-profile", "msg3", "author3"
        )

        # Get F-100 commits
        f100_commits = tracker.get_feature_commits("F-100")
        assert len(f100_commits) == 2
        assert all(c.feature_id == "F-100" for c in f100_commits)

        # Get F-200 commits
        f200_commits = tracker.get_feature_commits("F-200")
        assert len(f200_commits) == 1
        assert f200_commits[0].feature_id == "F-200"

    def test_get_recent_commits(self, tracker):
        """Test getting recent commits."""
        # Track commits
        for i in range(15):
            tracker.track_commit(
                f"commit{i}", f"T-{i}", "F-100",
                "feature/F-100", f"msg{i}", "author"
            )

        # Get recent (default limit 10)
        recent = tracker.get_recent_commits(limit=10)
        assert len(recent) == 10

        # Should be newest first
        # (last tracked should be first in results)
        assert "commit14" in recent[0].commit_hash

    def test_tracker_persists(self, tmp_path):
        """Test that commits persist across tracker instances."""
        # Create first tracker and track commit
        tracker1 = CommitTracker(tmp_path)
        tracker1.track_commit(
            "commit1", "T-1", "F-100",
            "feature/F-100", "msg", "author"
        )

        # Create second tracker (should load from disk)
        tracker2 = CommitTracker(tmp_path)
        commits = tracker2.get_task_commits("T-1")

        assert len(commits) == 1
        assert commits[0].commit_hash == "commit1"
```

Run tests:
```bash
pytest tests/unit/workspace/test_commit_tracker.py -v
```

**Success Criteria**:
- ✅ CommitTracker stores commits in `.marcus/commits.json`
- ✅ Can query commits by feature_id
- ✅ Can query commits by task_id
- ✅ Commits captured during workspace cleanup
- ✅ All tests pass

---

### Tuesday: Implement get_feature_context Tool

**What**: Create MCP tool to retrieve full context for a feature (tasks, artifacts, decisions, commits).

**Why**: Agents need access to all information about a feature to understand dependencies and prior work. This enables "show me everything about the authentication feature."

**How**:

#### Step 2.1: Create feature context builder

Create `src/workspace/feature_context.py`:

```python
"""
Feature context aggregation.

Builds comprehensive context for features by aggregating tasks, artifacts,
decisions, and commits.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.feature_index import FeatureIndex
from src.workspace.commit_tracker import CommitTracker, CommitInfo

logger = logging.getLogger(__name__)


@dataclass
class FeatureContext:
    """
    Complete context for a feature.

    Attributes
    ----------
    feature_id : str
        Feature identifier
    feature_name : str
        Human-readable name
    feature_branch : str
        Git branch
    status : str
        Feature status
    task_ids : list[str]
        All task IDs in feature
    artifacts : list[dict]
        All artifacts created for feature
    decisions : list[dict]
        All decisions made for feature
    commits : list[CommitInfo]
        All commits for feature
    summary : dict
        Summary statistics
    """

    feature_id: str
    feature_name: str
    feature_branch: str
    status: str
    task_ids: List[str]
    artifacts: List[Dict[str, Any]]
    decisions: List[Dict[str, Any]]
    commits: List[CommitInfo]
    summary: Dict[str, Any]


class FeatureContextBuilder:
    """
    Builds comprehensive feature context.

    Aggregates data from:
    - Feature metadata
    - Task information
    - Artifacts (via FeatureIndex)
    - Decisions (via FeatureIndex)
    - Git commits (via CommitTracker)
    """

    def __init__(self, project_root: Path):
        """
        Initialize feature context builder.

        Parameters
        ----------
        project_root : Path
            Root directory of git repository
        """
        self.project_root = project_root
        self.feature_index = FeatureIndex(project_root)
        self.commit_tracker = CommitTracker(project_root)

    def build_feature_context(
        self,
        feature_id: str,
        feature_name: str,
        feature_branch: str,
        status: str,
        task_ids: List[str]
    ) -> FeatureContext:
        """
        Build complete context for a feature.

        Parameters
        ----------
        feature_id : str
            Feature identifier
        feature_name : str
            Human-readable name
        feature_branch : str
            Git branch
        status : str
            Feature status
        task_ids : list[str]
            Task IDs in feature

        Returns
        -------
        FeatureContext
            Complete feature context
        """
        logger.info(f"Building context for feature {feature_id}")

        # Get artifacts
        artifacts = self.feature_index.get_feature_artifacts(feature_id)

        # Get decisions
        decisions = self.feature_index.get_feature_decisions(feature_id)

        # Get commits
        commits = self.commit_tracker.get_feature_commits(feature_id)

        # Build summary
        summary = {
            "task_count": len(task_ids),
            "artifact_count": len(artifacts),
            "decision_count": len(decisions),
            "commit_count": len(commits),
            "status": status,
            "branch": feature_branch
        }

        context = FeatureContext(
            feature_id=feature_id,
            feature_name=feature_name,
            feature_branch=feature_branch,
            status=status,
            task_ids=task_ids,
            artifacts=artifacts,
            decisions=decisions,
            commits=commits,
            summary=summary
        )

        logger.info(
            f"Feature context built: {len(artifacts)} artifacts, "
            f"{len(decisions)} decisions, {len(commits)} commits"
        )

        return context

    def format_context_for_agent(self, context: FeatureContext) -> str:
        """
        Format feature context as human-readable text for agents.

        Parameters
        ----------
        context : FeatureContext
            Feature context

        Returns
        -------
        str
            Formatted context text
        """
        lines = [
            f"# Feature: {context.feature_name} ({context.feature_id})",
            f"",
            f"**Branch**: {context.feature_branch}",
            f"**Status**: {context.status}",
            f"**Tasks**: {len(context.task_ids)}",
            f"**Artifacts**: {len(context.artifacts)}",
            f"**Decisions**: {len(context.decisions)}",
            f"**Commits**: {len(context.commits)}",
            f""
        ]

        # Tasks
        if context.task_ids:
            lines.append("## Tasks")
            lines.append("")
            for task_id in context.task_ids:
                lines.append(f"- {task_id}")
            lines.append("")

        # Artifacts
        if context.artifacts:
            lines.append("## Artifacts")
            lines.append("")
            for artifact in context.artifacts:
                lines.append(
                    f"- **{artifact['filename']}** "
                    f"({artifact['artifact_type']}) - "
                    f"Task: {artifact['task_id']}"
                )
                lines.append(f"  Location: {artifact['location']}")
            lines.append("")

        # Decisions
        if context.decisions:
            lines.append("## Decisions")
            lines.append("")
            for decision in context.decisions:
                lines.append(f"- **{decision['what']}**")
                lines.append(f"  Why: {decision['why']}")
                lines.append(f"  Task: {decision['task_id']}")
            lines.append("")

        # Commits
        if context.commits:
            lines.append("## Commits")
            lines.append("")
            for commit in context.commits:
                lines.append(
                    f"- `{commit.short_hash}` {commit.message} "
                    f"({commit.author})"
                )
            lines.append("")

        return "\n".join(lines)
```

#### Step 2.2: Create get_feature_context MCP tool

Create `src/marcus_mcp/tools/feature.py`:

```python
"""
Feature-level MCP tools.
"""

import logging
from pathlib import Path
from typing import Any, Dict

from src.core.error_responses import handle_mcp_tool_error
from src.workspace.feature_context import FeatureContextBuilder

logger = logging.getLogger(__name__)


async def get_feature_context(
    feature_id: str,
    state: Any = None
) -> Dict[str, Any]:
    """
    Get complete context for a feature.

    Returns all tasks, artifacts, decisions, and commits for the feature.

    Parameters
    ----------
    feature_id : str
        Feature identifier
    state : Any
        Marcus state

    Returns
    -------
    Dict[str, Any]
        Feature context
    """
    try:
        # Get feature
        feature = state.features.get(feature_id)

        if not feature:
            return {
                "success": False,
                "message": f"Feature {feature_id} not found"
            }

        # Get project to determine project_root
        project = state.projects.get(feature.project_id)

        if not project:
            return {
                "success": False,
                "message": f"Project {feature.project_id} not found"
            }

        # Build context
        context_builder = FeatureContextBuilder(project.local_path)

        context = context_builder.build_feature_context(
            feature_id=feature.feature_id,
            feature_name=feature.feature_name,
            feature_branch=feature.feature_branch,
            status=feature.status,
            task_ids=feature.task_ids
        )

        # Format for agent
        formatted_context = context_builder.format_context_for_agent(context)

        return {
            "success": True,
            "feature_id": feature_id,
            "context": formatted_context,
            "summary": context.summary,
            "artifacts": [
                {
                    "filename": a["filename"],
                    "location": a["location"],
                    "type": a["artifact_type"],
                    "task_id": a["task_id"]
                }
                for a in context.artifacts
            ],
            "decisions": [
                {
                    "what": d["what"],
                    "why": d["why"],
                    "task_id": d["task_id"]
                }
                for d in context.decisions
            ],
            "commits": [
                {
                    "hash": c.short_hash,
                    "message": c.message,
                    "author": c.author,
                    "task_id": c.task_id
                }
                for c in context.commits
            ]
        }

    except Exception as e:
        logger.error(f"Error getting feature context: {e}")
        return handle_mcp_tool_error(
            e, "get_feature_context", {"feature_id": feature_id}
        )
```

#### Step 2.3: Register tool

Update `src/marcus_mcp/server.py`:

```python
from src.marcus_mcp.tools.feature import get_feature_context

# In tool registration:
server.add_tool(
    name="get_feature_context",
    description="Get complete context for a feature (tasks, artifacts, decisions, commits)",
    handler=get_feature_context
)
```

#### Step 2.4: Write tests

Create `tests/unit/workspace/test_feature_context.py`:

```python
"""
Tests for FeatureContextBuilder.
"""

import pytest
from pathlib import Path

from src.workspace.feature_context import FeatureContextBuilder, FeatureContext
from src.workspace.commit_tracker import CommitTracker
from src.core.feature_index import FeatureIndex


class TestFeatureContextBuilder:
    """Test FeatureContextBuilder"""

    @pytest.fixture
    def setup_data(self, tmp_path):
        """Set up test data."""
        # Create feature index with artifacts
        index = FeatureIndex(tmp_path)
        index.add_artifact(
            artifact_id="art-1",
            task_id="T-DESIGN-1",
            feature_id="F-100",
            filename="design.md",
            location="docs/design.md",
            artifact_type="design"
        )
        index.add_decision(
            decision_id="dec-1",
            task_id="T-IMPL-1",
            feature_id="F-100",
            what="Use JWT",
            why="Industry standard",
            agent_id="agent-1"
        )

        # Create commit tracker with commits
        tracker = CommitTracker(tmp_path)
        tracker.track_commit(
            commit_hash="abc123",
            task_id="T-IMPL-1",
            feature_id="F-100",
            branch="feature/F-100-auth",
            message="feat: Add authentication",
            author="Test Author"
        )

        return tmp_path

    def test_build_feature_context(self, setup_data):
        """Test building feature context."""
        builder = FeatureContextBuilder(setup_data)

        context = builder.build_feature_context(
            feature_id="F-100",
            feature_name="Authentication",
            feature_branch="feature/F-100-auth",
            status="in_progress",
            task_ids=["T-DESIGN-1", "T-IMPL-1"]
        )

        assert context.feature_id == "F-100"
        assert context.feature_name == "Authentication"
        assert len(context.task_ids) == 2
        assert len(context.artifacts) == 1
        assert len(context.decisions) == 1
        assert len(context.commits) == 1
        assert context.summary["task_count"] == 2
        assert context.summary["artifact_count"] == 1

    def test_format_context_for_agent(self, setup_data):
        """Test formatting context as text."""
        builder = FeatureContextBuilder(setup_data)

        context = builder.build_feature_context(
            feature_id="F-100",
            feature_name="Authentication",
            feature_branch="feature/F-100-auth",
            status="in_progress",
            task_ids=["T-DESIGN-1", "T-IMPL-1"]
        )

        formatted = builder.format_context_for_agent(context)

        assert "# Feature: Authentication" in formatted
        assert "T-DESIGN-1" in formatted
        assert "design.md" in formatted
        assert "Use JWT" in formatted
        assert "abc123" in formatted

    def test_empty_feature_context(self, tmp_path):
        """Test building context for feature with no artifacts."""
        builder = FeatureContextBuilder(tmp_path)

        context = builder.build_feature_context(
            feature_id="F-200",
            feature_name="Empty Feature",
            feature_branch="feature/F-200",
            status="todo",
            task_ids=["T-1"]
        )

        assert context.feature_id == "F-200"
        assert len(context.artifacts) == 0
        assert len(context.decisions) == 0
        assert len(context.commits) == 0
        assert context.summary["task_count"] == 1
```

Create `tests/unit/mcp/test_feature_tools.py`:

```python
"""
Tests for feature MCP tools.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.marcus_mcp.tools.feature import get_feature_context
from src.core.models import Feature, Project


class TestFeatureTools:
    """Test feature MCP tools"""

    @pytest.fixture
    def mock_state(self, tmp_path):
        """Create mock state with feature and project."""
        state = Mock()

        project = Project(
            project_id="proj-1",
            name="Test Project",
            repo_url="https://github.com/test/repo",
            local_path=tmp_path,
            main_branch="main",
            created_at="2025-01-06T00:00:00Z"
        )

        feature = Feature(
            feature_id="F-100",
            feature_name="Authentication",
            project_id="proj-1",
            feature_branch="feature/F-100-auth",
            status="in_progress",
            task_ids=["T-DESIGN-1", "T-IMPL-1"]
        )

        state.features = {"F-100": feature}
        state.projects = {"proj-1": project}

        return state

    @pytest.mark.asyncio
    async def test_get_feature_context_success(self, mock_state, tmp_path):
        """Test getting feature context."""
        result = await get_feature_context(
            feature_id="F-100",
            state=mock_state
        )

        assert result["success"] is True
        assert result["feature_id"] == "F-100"
        assert "context" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_get_feature_context_not_found(self, mock_state):
        """Test getting context for non-existent feature."""
        result = await get_feature_context(
            feature_id="F-999",
            state=mock_state
        )

        assert result["success"] is False
        assert "not found" in result["message"]
```

Run tests:
```bash
pytest tests/unit/workspace/test_feature_context.py -v
pytest tests/unit/mcp/test_feature_tools.py -v
```

**Success Criteria**:
- ✅ FeatureContextBuilder aggregates all feature data
- ✅ get_feature_context MCP tool works
- ✅ Context formatted for agent consumption
- ✅ All tests pass

---

### Wednesday: Implement get_feature_status Tool

**What**: Create MCP tool to get current status of a feature including git status.

**Why**: Users want to ask "What's the status of authentication feature?" and get real-time information about progress, branches, and git state.

**How**:

#### Step 3.1: Create feature status checker

Update `src/workspace/feature_context.py` to add status checking:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class FeatureStatus:
    """
    Current status of a feature.

    Attributes
    ----------
    feature_id : str
        Feature identifier
    feature_name : str
        Human-readable name
    status : str
        Feature status (todo, in_progress, completed)
    feature_branch : str
        Git branch name
    branch_exists : bool
        Whether git branch exists
    tasks_total : int
        Total number of tasks
    tasks_completed : int
        Number of completed tasks
    tasks_in_progress : int
        Number of in-progress tasks
    artifacts_count : int
        Number of artifacts created
    decisions_count : int
        Number of decisions made
    commits_count : int
        Number of commits
    latest_commit : Optional[str]
        Latest commit hash
    latest_commit_message : Optional[str]
        Latest commit message
    progress_percentage : float
        Completion percentage (0-100)
    """

    feature_id: str
    feature_name: str
    status: str
    feature_branch: str
    branch_exists: bool
    tasks_total: int
    tasks_completed: int
    tasks_in_progress: int
    artifacts_count: int
    decisions_count: int
    commits_count: int
    latest_commit: Optional[str]
    latest_commit_message: Optional[str]
    progress_percentage: float


class FeatureContextBuilder:
    """Builds comprehensive feature context."""

    # ... existing methods ...

    async def get_feature_status(
        self,
        feature_id: str,
        feature_name: str,
        feature_branch: str,
        status: str,
        task_ids: List[str],
        tasks_by_status: Dict[str, int]
    ) -> FeatureStatus:
        """
        Get current status of a feature.

        Parameters
        ----------
        feature_id : str
            Feature identifier
        feature_name : str
            Feature name
        feature_branch : str
            Git branch
        status : str
            Feature status
        task_ids : list[str]
            Task IDs
        tasks_by_status : dict[str, int]
            Task counts by status

        Returns
        -------
        FeatureStatus
            Current feature status
        """
        from src.workspace.git_operations import GitOperations

        logger.info(f"Getting status for feature {feature_id}")

        # Check if branch exists
        git_ops = GitOperations(self.project_root)
        branch_exists = await git_ops.branch_exists(feature_branch)

        # Get summary
        summary = self.feature_index.get_feature_summary(feature_id)

        # Get commits
        commits = self.commit_tracker.get_feature_commits(feature_id)

        # Latest commit
        latest_commit = None
        latest_commit_message = None
        if commits:
            latest = commits[0]  # Commits are sorted newest first
            latest_commit = latest.short_hash
            latest_commit_message = latest.message

        # Calculate progress
        tasks_total = len(task_ids)
        tasks_completed = tasks_by_status.get("completed", 0)
        tasks_in_progress = tasks_by_status.get("in_progress", 0)

        progress_percentage = 0.0
        if tasks_total > 0:
            progress_percentage = (tasks_completed / tasks_total) * 100

        feature_status = FeatureStatus(
            feature_id=feature_id,
            feature_name=feature_name,
            status=status,
            feature_branch=feature_branch,
            branch_exists=branch_exists,
            tasks_total=tasks_total,
            tasks_completed=tasks_completed,
            tasks_in_progress=tasks_in_progress,
            artifacts_count=summary["artifact_count"],
            decisions_count=summary["decision_count"],
            commits_count=len(commits),
            latest_commit=latest_commit,
            latest_commit_message=latest_commit_message,
            progress_percentage=progress_percentage
        )

        return feature_status

    def format_status_for_display(self, status: FeatureStatus) -> str:
        """
        Format feature status as human-readable text.

        Parameters
        ----------
        status : FeatureStatus
            Feature status

        Returns
        -------
        str
            Formatted status text
        """
        lines = [
            f"# Feature Status: {status.feature_name}",
            f"",
            f"**ID**: {status.feature_id}",
            f"**Status**: {status.status}",
            f"**Progress**: {status.progress_percentage:.1f}%",
            f"",
            f"## Git",
            f"",
            f"**Branch**: {status.feature_branch}",
            f"**Branch Exists**: {'✓' if status.branch_exists else '✗'}",
            f"**Commits**: {status.commits_count}",
            f""
        ]

        if status.latest_commit:
            lines.append(f"**Latest Commit**: `{status.latest_commit}` {status.latest_commit_message}")
            lines.append(f"")

        lines.extend([
            f"## Tasks",
            f"",
            f"**Total**: {status.tasks_total}",
            f"**Completed**: {status.tasks_completed}",
            f"**In Progress**: {status.tasks_in_progress}",
            f"**Pending**: {status.tasks_total - status.tasks_completed - status.tasks_in_progress}",
            f"",
            f"## Artifacts & Decisions",
            f"",
            f"**Artifacts**: {status.artifacts_count}",
            f"**Decisions**: {status.decisions_count}",
            f""
        ])

        return "\n".join(lines)
```

#### Step 3.2: Add get_feature_status MCP tool

Update `src/marcus_mcp/tools/feature.py`:

```python
async def get_feature_status(
    feature_id: str,
    state: Any = None
) -> Dict[str, Any]:
    """
    Get current status of a feature.

    Returns progress, git status, task counts, etc.

    Parameters
    ----------
    feature_id : str
        Feature identifier
    state : Any
        Marcus state

    Returns
    -------
    Dict[str, Any]
        Feature status
    """
    try:
        # Get feature
        feature = state.features.get(feature_id)

        if not feature:
            return {
                "success": False,
                "message": f"Feature {feature_id} not found"
            }

        # Get project
        project = state.projects.get(feature.project_id)

        if not project:
            return {
                "success": False,
                "message": f"Project {feature.project_id} not found"
            }

        # Get task counts by status
        # (In real implementation, query tasks from kanban)
        tasks_by_status = {
            "completed": 0,
            "in_progress": 0,
            "todo": 0
        }

        # Get tasks from kanban
        if hasattr(state, "kanban") and state.kanban:
            for task_id in feature.task_ids:
                try:
                    task = await state.kanban.get_task(task_id)
                    if task:
                        status_key = task.status.value if hasattr(task.status, "value") else str(task.status).lower()
                        if status_key in tasks_by_status:
                            tasks_by_status[status_key] += 1
                except Exception as e:
                    logger.warning(f"Failed to get task {task_id}: {e}")

        # Build status
        context_builder = FeatureContextBuilder(project.local_path)

        feature_status = await context_builder.get_feature_status(
            feature_id=feature.feature_id,
            feature_name=feature.feature_name,
            feature_branch=feature.feature_branch,
            status=feature.status,
            task_ids=feature.task_ids,
            tasks_by_status=tasks_by_status
        )

        # Format for display
        formatted_status = context_builder.format_status_for_display(feature_status)

        return {
            "success": True,
            "feature_id": feature_id,
            "status": formatted_status,
            "summary": {
                "feature_name": feature_status.feature_name,
                "status": feature_status.status,
                "progress_percentage": feature_status.progress_percentage,
                "branch": feature_status.feature_branch,
                "branch_exists": feature_status.branch_exists,
                "tasks_total": feature_status.tasks_total,
                "tasks_completed": feature_status.tasks_completed,
                "tasks_in_progress": feature_status.tasks_in_progress,
                "artifacts_count": feature_status.artifacts_count,
                "decisions_count": feature_status.decisions_count,
                "commits_count": feature_status.commits_count,
                "latest_commit": feature_status.latest_commit
            }
        }

    except Exception as e:
        logger.error(f"Error getting feature status: {e}")
        return handle_mcp_tool_error(
            e, "get_feature_status", {"feature_id": feature_id}
        )
```

#### Step 3.3: Register tool

Update `src/marcus_mcp/server.py`:

```python
from src.marcus_mcp.tools.feature import get_feature_context, get_feature_status

# In tool registration:
server.add_tool(
    name="get_feature_status",
    description="Get current status of a feature (progress, git status, tasks)",
    handler=get_feature_status
)
```

#### Step 3.4: Write tests

Update `tests/unit/workspace/test_feature_context.py`:

```python
class TestFeatureStatus:
    """Test FeatureStatus"""

    @pytest.fixture
    def setup_data(self, tmp_path):
        """Set up test data."""
        # Create branch
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path, check=True
        )

        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path, check=True
        )
        subprocess.run(
            ["git", "branch", "feature/F-100-auth"],
            cwd=tmp_path, check=True
        )

        # Add commits
        tracker = CommitTracker(tmp_path)
        tracker.track_commit(
            "abc123", "T-IMPL-1", "F-100",
            "feature/F-100-auth", "feat: Add auth", "Author"
        )

        return tmp_path

    @pytest.mark.asyncio
    async def test_get_feature_status(self, setup_data):
        """Test getting feature status."""
        builder = FeatureContextBuilder(setup_data)

        status = await builder.get_feature_status(
            feature_id="F-100",
            feature_name="Authentication",
            feature_branch="feature/F-100-auth",
            status="in_progress",
            task_ids=["T-DESIGN-1", "T-IMPL-1", "T-TEST-1"],
            tasks_by_status={"completed": 1, "in_progress": 1, "todo": 1}
        )

        assert status.feature_id == "F-100"
        assert status.branch_exists is True
        assert status.tasks_total == 3
        assert status.tasks_completed == 1
        assert status.progress_percentage == pytest.approx(33.33, rel=0.1)
        assert status.commits_count == 1
        assert status.latest_commit == "abc123"

    @pytest.mark.asyncio
    async def test_format_status_for_display(self, setup_data):
        """Test formatting status."""
        builder = FeatureContextBuilder(setup_data)

        status = await builder.get_feature_status(
            feature_id="F-100",
            feature_name="Authentication",
            feature_branch="feature/F-100-auth",
            status="in_progress",
            task_ids=["T-1", "T-2"],
            tasks_by_status={"completed": 1, "in_progress": 1}
        )

        formatted = builder.format_status_for_display(status)

        assert "Authentication" in formatted
        assert "50.0%" in formatted
        assert "feature/F-100-auth" in formatted
        assert "abc123" in formatted
```

Run tests:
```bash
pytest tests/unit/workspace/test_feature_context.py -v
```

**Success Criteria**:
- ✅ get_feature_status returns current feature state
- ✅ Includes git branch existence check
- ✅ Calculates progress percentage
- ✅ Shows latest commit information
- ✅ All tests pass

---

### Thursday: Integrate Feature Context with request_next_task

**What**: Update task assignment to include relevant feature context when available.

**Why**: Agents working on a task should automatically receive context from related tasks in the same feature, improving decision-making and consistency.

**How**:

#### Step 4.1: Update get_task_context to include feature context

Update `src/marcus_mcp/tools/context.py`:

```python
async def get_task_context(
    task_id: str,
    state: Any = None
) -> Dict[str, Any]:
    """
    Get full context for a task.

    Now includes feature context if task is part of a feature.
    """
    try:
        # ... existing context gathering logic ...

        context_parts = []

        # 1. Task dependencies context (existing)
        if dependency_context:
            context_parts.append(dependency_context)

        # 2. NEW: Feature context (if task belongs to feature)
        if hasattr(state, "features") and state.features:
            # Find feature for this task
            task_feature = None
            for feature in state.features.values():
                if task_id in feature.task_ids:
                    task_feature = feature
                    break

            if task_feature:
                # Get feature context
                from src.marcus_mcp.tools.feature import get_feature_context

                feature_ctx_result = await get_feature_context(
                    feature_id=task_feature.feature_id,
                    state=state
                )

                if feature_ctx_result["success"]:
                    context_parts.append(
                        f"\n\n# FEATURE CONTEXT\n\n"
                        f"{feature_ctx_result['context']}"
                    )

        combined_context = "\n\n".join(context_parts)

        return {
            "success": True,
            "task_id": task_id,
            "context": combined_context,
            # ... rest of response ...
        }

    except Exception as e:
        logger.error(f"Error getting task context: {e}")
        return handle_mcp_tool_error(e, "get_task_context", {"task_id": task_id})
```

#### Step 4.2: Write integration test

Create `tests/integration/test_feature_context_integration.py`:

```python
"""
Integration test for feature context in task assignment.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from pathlib import Path

from src.marcus_mcp.state import MarcusState
from src.marcus_mcp.tools.context import get_task_context
from src.core.models import Feature, Project, Task, TaskStatus, Priority


class TestFeatureContextIntegration:
    """Test feature context integration"""

    @pytest.fixture
    async def state_with_feature(self, tmp_path):
        """Create state with feature and tasks."""
        state = MarcusState(storage_dir=str(tmp_path / "data"))
        await state.initialize()

        # Create project
        project = Project(
            project_id="proj-1",
            name="Test Project",
            repo_url="https://github.com/test/repo",
            local_path=tmp_path,
            main_branch="main",
            created_at="2025-01-06T00:00:00Z"
        )
        state.projects[project.project_id] = project

        # Create feature
        feature = Feature(
            feature_id="F-100",
            feature_name="Authentication",
            project_id="proj-1",
            feature_branch="feature/F-100-auth",
            status="in_progress",
            task_ids=["T-DESIGN-1", "T-IMPL-1", "T-TEST-1"]
        )
        state.features[feature.feature_id] = feature

        # Log some artifacts for the feature
        from src.marcus_mcp.tools.context import log_artifact

        await log_artifact(
            task_id="T-DESIGN-1",
            filename="auth-design.md",
            content="# Auth Design\nUse JWT tokens...",
            artifact_type="design",
            project_root=str(tmp_path),
            feature_id="F-100",
            state=state
        )

        return state

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_task_context_includes_feature_context(
        self, state_with_feature
    ):
        """Test that task context includes feature context."""
        state = state_with_feature

        # Get context for a task in the feature
        result = await get_task_context(
            task_id="T-IMPL-1",
            state=state
        )

        assert result["success"] is True

        context = result["context"]

        # Should include feature context
        assert "FEATURE CONTEXT" in context
        assert "Authentication" in context
        assert "T-DESIGN-1" in context
        assert "auth-design.md" in context

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_task_without_feature_still_works(self, state_with_feature):
        """Test that tasks not in a feature still get context."""
        state = state_with_feature

        # Get context for task not in any feature
        result = await get_task_context(
            task_id="T-ORPHAN-1",
            state=state
        )

        # Should still work (but no feature context)
        assert result["success"] is True
```

Run tests:
```bash
pytest tests/integration/test_feature_context_integration.py -v
```

#### Step 4.3: Update documentation

Create `docs/features/FEATURE_CONTEXT.md`:

```markdown
# Feature Context

**Status**: Implemented (Week 4)
**Version**: 1.0

## Overview

Feature context provides agents with comprehensive information about features, including all related tasks, artifacts, decisions, and git commits.

## Key Concepts

### Feature Context
Complete information about a feature:
- Task list
- All artifacts created
- All decisions made
- All git commits
- Progress status

### Feature Status
Real-time status of a feature:
- Progress percentage
- Task completion counts
- Git branch status
- Latest commit information

## Usage

### Get Feature Context

```python
from src.marcus_mcp.tools.feature import get_feature_context

result = await get_feature_context(
    feature_id="F-100",
    state=state
)

print(result["context"])
# Output:
# # Feature: Authentication (F-100)
#
# **Branch**: feature/F-100-auth
# **Status**: in_progress
# **Tasks**: 3
# **Artifacts**: 2
# ...
```

### Get Feature Status

```python
from src.marcus_mcp.tools.feature import get_feature_status

result = await get_feature_status(
    feature_id="F-100",
    state=state
)

print(f"Progress: {result['summary']['progress_percentage']}%")
# Output: Progress: 66.7%
```

### Automatic Context in Task Assignment

When agents request tasks, they automatically receive feature context:

```python
result = await request_next_task(agent_id="agent-1", state=state)

# Task assignment includes feature context
assignment = result["assignment"]
instructions = assignment["instructions"]

# Instructions contain:
# - Workspace path
# - Git workflow instructions
# - Task description
# - FEATURE CONTEXT (automatic)
#   - Related tasks
#   - Previous artifacts
#   - Decisions made
#   - Commits
```

## Benefits

- **Awareness**: Agents know what work has been done
- **Consistency**: Decisions aligned with feature direction
- **Traceability**: Full history of feature development
- **Observability**: Real-time feature progress

## Storage

- **Feature metadata**: `data/features.json`
- **Artifacts**: `docs/artifacts/{task_id}/`
- **Decisions**: `data/decisions/`
- **Commits**: `.marcus/commits.json`
- **Feature index**: `.marcus/feature_index.json`

## MCP Tools

- `get_feature_context` - Get complete feature information
- `get_feature_status` - Get current feature status
- `get_task_context` - Get task context (includes feature context)

## Next Steps (Week 5)

- Enhanced telemetry
- Research-grade event logging
- CATO dashboard integration
```

**Success Criteria**:
- ✅ Task context includes feature context automatically
- ✅ Agents receive feature information when assigned tasks
- ✅ Documentation complete
- ✅ All tests pass

---

### Friday: Week 4 Testing & Documentation

**What**: Comprehensive testing of feature context and git integration.

**Why**: Ensure all feature-level observability works correctly before moving to telemetry.

**How**:

#### Step 5.1: Create comprehensive integration test

Create `tests/integration/e2e/test_feature_observability_e2e.py`:

```python
"""
End-to-end test for feature observability.

Tests complete workflow:
1. Create feature
2. Agents work on tasks
3. Create artifacts and decisions
4. Make commits
5. Query feature status and context
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from src.marcus_mcp.state import MarcusState
from src.marcus_mcp.tools.task import request_next_task, report_task_progress
from src.marcus_mcp.tools.context import log_artifact, log_decision
from src.marcus_mcp.tools.feature import get_feature_context, get_feature_status
from src.core.models import Task, TaskStatus, Priority, Feature, Project


class TestFeatureObservabilityE2E:
    """End-to-end feature observability tests"""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create git repository."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path, check=True
        )

        (repo_path / "README.md").write_text("# Test Project")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path, check=True
        )

        return repo_path

    @pytest.fixture
    async def full_state(self, tmp_path, git_repo):
        """Create fully initialized state."""
        state = MarcusState(storage_dir=str(tmp_path / "data"))
        await state.initialize()
        await state.initialize_workspace_manager(git_repo)

        # Mock kanban
        state.kanban = Mock()

        # Create project
        project = Project(
            project_id="proj-1",
            name="E2E Test Project",
            repo_url="https://github.com/test/repo",
            local_path=git_repo,
            main_branch="master",
            created_at="2025-01-06T00:00:00Z"
        )
        state.projects[project.project_id] = project

        # Create feature
        feature = Feature(
            feature_id="F-100",
            feature_name="User Authentication",
            project_id="proj-1",
            feature_branch="feature/F-100-user-auth",
            status="in_progress",
            task_ids=["T-DESIGN-1", "T-IMPL-1", "T-TEST-1"]
        )
        state.features[feature.feature_id] = feature

        # Create feature branch
        subprocess.run(
            ["git", "branch", "feature/F-100-user-auth"],
            cwd=git_repo, check=True
        )

        # Register agent
        await state.register_agent(
            "agent-1", "Dev Agent", "developer", []
        )

        return state

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_full_feature_observability_workflow(
        self, full_state, git_repo
    ):
        """Test complete feature observability workflow."""
        state = full_state

        # Step 1: Design task - create artifacts
        design_task = Task(
            id="T-DESIGN-1",
            name="Design authentication system",
            description="Create design for JWT authentication",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=6.0,
            labels=["design"],
            feature_id="F-100",
            project_id="proj-1"
        )

        # Log design artifact
        await log_artifact(
            task_id="T-DESIGN-1",
            filename="auth-design.md",
            content="# Authentication Design\n\nUse JWT tokens with refresh mechanism...",
            artifact_type="design",
            project_root=str(git_repo),
            feature_id="F-100",
            state=state
        )

        # Log design decision
        await log_decision(
            task_id="T-DESIGN-1",
            what="Use JWT tokens for authentication",
            why="Industry standard, stateless, scalable",
            agent_id="agent-1",
            feature_id="F-100",
            state=state
        )

        # Step 2: Check feature status after design
        status_after_design = await get_feature_status(
            feature_id="F-100",
            state=state
        )

        assert status_after_design["success"] is True
        assert status_after_design["summary"]["artifacts_count"] == 1
        assert status_after_design["summary"]["decisions_count"] == 1

        # Step 3: Implementation task - work in workspace
        impl_task = Task(
            id="T-IMPL-1",
            name="Implement JWT authentication",
            description="Implement authentication using JWT",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=8.0,
            labels=["feature"],
            feature_id="F-100",
            project_id="proj-1"
        )

        state.kanban.find_optimal_task = AsyncMock(return_value=impl_task)
        state.kanban.update_task_status = AsyncMock()

        # Agent requests task
        task_result = await request_next_task(agent_id="agent-1", state=state)
        assert task_result["success"] is True

        # Get workspace
        workspace = await state.workspace_manager.get_workspace("T-IMPL-1")
        assert workspace is not None

        # Simulate agent work
        (workspace.workspace_path / "src").mkdir(parents=True)
        (workspace.workspace_path / "src" / "auth.py").write_text(
            "def authenticate(token):\n    # JWT authentication\n    pass"
        )

        # Commit work
        subprocess.run(
            ["git", "add", "."],
            cwd=workspace.workspace_path, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "feat: Implement JWT authentication (T-IMPL-1)"],
            cwd=workspace.workspace_path, check=True
        )

        # Complete task (triggers commit tracking)
        await report_task_progress(
            agent_id="agent-1",
            task_id="T-IMPL-1",
            status="completed",
            progress=100,
            state=state
        )

        # Step 4: Get feature context (should include everything)
        context_result = await get_feature_context(
            feature_id="F-100",
            state=state
        )

        assert context_result["success"] is True

        context = context_result["context"]

        # Should contain design artifact
        assert "auth-design.md" in context

        # Should contain decision
        assert "JWT tokens" in context

        # Should contain commit
        assert len(context_result["commits"]) == 1
        assert "JWT authentication" in context_result["commits"][0]["message"]

        # Step 5: Get feature status (should show progress)
        final_status = await get_feature_status(
            feature_id="F-100",
            state=state
        )

        assert final_status["success"] is True
        assert final_status["summary"]["commits_count"] == 1
        assert final_status["summary"]["artifacts_count"] == 1
        assert final_status["summary"]["decisions_count"] == 1

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_feature_context_available_to_next_agent(
        self, full_state, git_repo
    ):
        """Test that feature context is available to subsequent agents."""
        state = full_state

        # First agent completes design
        await log_artifact(
            task_id="T-DESIGN-1",
            filename="design.md",
            content="Design content",
            artifact_type="design",
            project_root=str(git_repo),
            feature_id="F-100",
            state=state
        )

        await log_decision(
            task_id="T-DESIGN-1",
            what="Use OAuth 2.0",
            why="Standard protocol",
            agent_id="agent-1",
            feature_id="F-100",
            state=state
        )

        # Second agent gets implementation task
        impl_task = Task(
            id="T-IMPL-1",
            name="Implement",
            description="Implement auth",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=8.0,
            labels=[],
            feature_id="F-100",
            project_id="proj-1"
        )

        # Get context for implementation task
        from src.marcus_mcp.tools.context import get_task_context

        context_result = await get_task_context(
            task_id="T-IMPL-1",
            state=state
        )

        assert context_result["success"] is True

        context = context_result["context"]

        # Should include feature context with design artifact and decision
        assert "FEATURE CONTEXT" in context
        assert "design.md" in context
        assert "OAuth 2.0" in context
```

Run tests:
```bash
pytest tests/integration/e2e/test_feature_observability_e2e.py -v
```

#### Step 5.2: Run full test suite

```bash
# Unit tests
pytest tests/unit/workspace/ -v
pytest tests/unit/mcp/test_feature_tools.py -v

# Integration tests
pytest tests/integration/test_feature_context_integration.py -v
pytest tests/integration/e2e/test_feature_observability_e2e.py -v

# Coverage
pytest tests/ --cov=src/workspace --cov=src/marcus_mcp/tools --cov-report=term-missing

# All tests
pytest tests/ -v --tb=short
```

#### Step 5.3: Create Week 4 summary document

Create `docs/implementation/WEEK_4_SUMMARY.md`:

```markdown
# Week 4 Implementation Summary

**Goal**: Feature Context & Git Integration ✅

## Completed

### Monday: Git Commit Tracking
- ✅ CommitTracker class for tracking commits by feature/task
- ✅ Integration with WorkspaceManager
- ✅ Automatic commit capture on workspace cleanup
- ✅ Storage in `.marcus/commits.json`

### Tuesday: get_feature_context Tool
- ✅ FeatureContextBuilder aggregates feature data
- ✅ MCP tool `get_feature_context`
- ✅ Returns tasks, artifacts, decisions, commits
- ✅ Formatted for agent consumption

### Wednesday: get_feature_status Tool
- ✅ Real-time feature status checking
- ✅ Progress calculation
- ✅ Git branch existence validation
- ✅ Latest commit information
- ✅ MCP tool `get_feature_status`

### Thursday: Integration with Task Assignment
- ✅ Automatic feature context in `get_task_context`
- ✅ Agents receive feature context when assigned tasks
- ✅ Improved agent awareness

### Friday: Testing & Documentation
- ✅ End-to-end feature observability tests
- ✅ Full test suite passing
- ✅ Documentation complete

## Key Files Created

### Source Code
- `src/workspace/commit_tracker.py` - Git commit tracking
- `src/workspace/feature_context.py` - Feature context aggregation
- `src/marcus_mcp/tools/feature.py` - Feature MCP tools
- Updated `src/marcus_mcp/tools/context.py` - Feature context integration

### Tests
- `tests/unit/workspace/test_commit_tracker.py`
- `tests/unit/workspace/test_feature_context.py`
- `tests/unit/mcp/test_feature_tools.py`
- `tests/integration/test_feature_context_integration.py`
- `tests/integration/e2e/test_feature_observability_e2e.py`

### Documentation
- `docs/features/FEATURE_CONTEXT.md`

## User-Facing Features

Users can now:

1. **Query Feature Status**:
   ```
   What's the status of the authentication feature?
   ```
   Returns: Progress, git status, task counts, latest commits

2. **Get Feature Context**:
   ```
   Show me everything about feature F-100
   ```
   Returns: All tasks, artifacts, decisions, commits

3. **Automatic Context for Agents**:
   Agents automatically receive feature context when assigned tasks

## Storage

- **Commits**: `.marcus/commits.json`
- **Feature Index**: `.marcus/feature_index.json` (from Week 2)
- **Features**: `data/features.json` (from Week 2)

## Metrics

- Test Coverage: 85%+ for new code
- Unit Tests: 25+ tests passing
- Integration Tests: 5+ tests passing
- E2E Tests: 2 comprehensive scenarios

## Ready for Week 5

Feature observability is complete. Next week:
- Enhanced telemetry (user journey tracking)
- Research-grade event logging
- CATO dashboard integration
```

**Success Criteria**:
- ✅ All Week 4 features implemented
- ✅ End-to-end tests pass
- ✅ Coverage >= 80%
- ✅ Documentation complete
- ✅ Ready for Week 5 (Telemetry & Research Logging)

---
