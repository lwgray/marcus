## Week 3: Workspace Isolation - Phase 2 (Implementation)

**Goal**: Implement full git worktree-based workspace isolation for parallel task execution.

**Why**: Multiple agents working in the same directory causes file conflicts. Workspace isolation gives each task its own workspace (git worktree) on the feature branch.

**Related Design**: `docs/design/workspace-isolation-and-feature-context.md`

---

### Monday: Implement Feature Branch Creation

**What**: Add git operations for creating and managing feature branches.

**Why**: Before we can create worktrees, we need feature branches. Each feature gets one branch (e.g., `feature/F-200-auth`) that all tasks in that feature use.

**How**:

#### Step 1.1: Create git operations module

Create `src/workspace/git_operations.py`:

```python
"""
Git operations for workspace management.

Provides safe git operations with error handling.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from src.core.error_framework import GitOperationError, ErrorContext

logger = logging.getLogger(__name__)


class GitOperations:
    """
    Safe git operations for workspace management.

    All operations use asyncio subprocess for non-blocking execution.
    """

    def __init__(self, repo_path: Path):
        """
        Initialize git operations.

        Parameters
        ----------
        repo_path : Path
            Path to git repository
        """
        self.repo_path = repo_path

    async def _run_git_command(
        self, *args: str, check: bool = True
    ) -> tuple[int, str, str]:
        """
        Run git command asynchronously.

        Parameters
        ----------
        *args : str
            Git command arguments
        check : bool
            Whether to raise on non-zero exit

        Returns
        -------
        tuple[int, str, str]
            Exit code, stdout, stderr

        Raises
        ------
        GitOperationError
            If command fails and check=True
        """
        cmd = ["git", "-C", str(self.repo_path)] + list(args)

        logger.debug(f"Running git command: {' '.join(cmd)}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout_bytes, stderr_bytes = await proc.communicate()
            stdout = stdout_bytes.decode("utf-8").strip()
            stderr = stderr_bytes.decode("utf-8").strip()

            if check and proc.returncode != 0:
                raise GitOperationError(
                    operation=" ".join(args),
                    repo_path=str(self.repo_path),
                    git_error=stderr,
                    context=ErrorContext(operation="git_command")
                )

            return proc.returncode, stdout, stderr

        except FileNotFoundError:
            raise GitOperationError(
                operation=" ".join(args),
                repo_path=str(self.repo_path),
                git_error="git command not found",
                context=ErrorContext(operation="git_command")
            )

    async def branch_exists(self, branch_name: str) -> bool:
        """
        Check if branch exists (local or remote).

        Parameters
        ----------
        branch_name : str
            Branch name to check

        Returns
        -------
        bool
            True if branch exists
        """
        # Check local branches
        returncode, stdout, _ = await self._run_git_command(
            "branch", "--list", branch_name, check=False
        )

        if stdout:
            return True

        # Check remote branches
        returncode, stdout, _ = await self._run_git_command(
            "branch", "-r", "--list", f"origin/{branch_name}", check=False
        )

        return bool(stdout)

    async def get_current_branch(self) -> str:
        """
        Get current branch name.

        Returns
        -------
        str
            Current branch name

        Raises
        ------
        GitOperationError
            If unable to determine branch
        """
        _, stdout, _ = await self._run_git_command(
            "branch", "--show-current"
        )

        return stdout

    async def create_branch(
        self, branch_name: str, start_point: str = "HEAD"
    ) -> None:
        """
        Create a new branch.

        Parameters
        ----------
        branch_name : str
            Name of branch to create
        start_point : str
            Starting point (default: HEAD)

        Raises
        ------
        GitOperationError
            If branch creation fails
        """
        logger.info(f"Creating branch {branch_name} from {start_point}")

        await self._run_git_command(
            "branch", branch_name, start_point
        )

    async def create_feature_branch(
        self, feature_id: str, feature_name: str, base_branch: str = "main"
    ) -> str:
        """
        Create feature branch if it doesn't exist.

        Branch naming: feature/{feature_id}-{slug}
        Example: feature/F-200-auth

        Parameters
        ----------
        feature_id : str
            Feature identifier (e.g., "F-200")
        feature_name : str
            Human-readable feature name
        base_branch : str
            Base branch to branch from (default: "main")

        Returns
        -------
        str
            Feature branch name

        Raises
        ------
        GitOperationError
            If branch creation fails
        """
        # Create branch slug from feature name
        slug = feature_name.lower().replace(" ", "-")[:30]
        branch_name = f"feature/{feature_id}-{slug}"

        # Check if branch already exists
        if await self.branch_exists(branch_name):
            logger.info(f"Feature branch {branch_name} already exists")
            return branch_name

        # Ensure we're on base branch
        current = await self.get_current_branch()
        if current != base_branch:
            logger.warning(
                f"Not on {base_branch}, currently on {current}. "
                "Creating branch anyway."
            )

        # Create branch
        await self.create_branch(branch_name, base_branch)

        logger.info(f"Created feature branch: {branch_name}")
        return branch_name

    async def get_main_branch(self) -> str:
        """
        Detect main branch name (main or master).

        Returns
        -------
        str
            Main branch name

        Raises
        ------
        GitOperationError
            If unable to determine main branch
        """
        # Check for 'main'
        if await self.branch_exists("main"):
            return "main"

        # Check for 'master'
        if await self.branch_exists("master"):
            return "master"

        # Try to get default branch from remote
        _, stdout, _ = await self._run_git_command(
            "symbolic-ref", "refs/remotes/origin/HEAD", check=False
        )

        if stdout:
            # Extract branch name from refs/remotes/origin/main
            parts = stdout.split("/")
            return parts[-1] if parts else "main"

        # Default to 'main'
        return "main"
```

#### Step 1.2: Write tests for git operations

Create `tests/unit/workspace/test_git_operations.py`:

```python
"""
Tests for GitOperations.

Uses real git repository (created in tmp_path) for integration-style testing.
"""

import pytest
from pathlib import Path
import subprocess

from src.workspace.git_operations import GitOperations
from src.core.error_framework import GitOperationError


class TestGitOperations:
    """Test suite for GitOperations"""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a real git repository for testing."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"], cwd=repo_path, check=True,
            capture_output=True
        )

        # Configure git
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path, check=True
        )

        # Create initial commit
        (repo_path / "README.md").write_text("# Test Repo")
        subprocess.run(
            ["git", "add", "README.md"], cwd=repo_path, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path, check=True
        )

        return repo_path

    @pytest.fixture
    def git_ops(self, git_repo):
        """Create GitOperations instance."""
        return GitOperations(repo_path=git_repo)

    @pytest.mark.asyncio
    async def test_get_current_branch(self, git_ops, git_repo):
        """Test getting current branch name."""
        # Default branch should be 'master' or 'main'
        branch = await git_ops.get_current_branch()
        assert branch in ["master", "main"]

    @pytest.mark.asyncio
    async def test_branch_exists(self, git_ops):
        """Test checking if branch exists."""
        # Main/master should exist
        exists_main = await git_ops.branch_exists("main")
        exists_master = await git_ops.branch_exists("master")

        assert exists_main or exists_master

        # Non-existent branch
        exists_fake = await git_ops.branch_exists("nonexistent-branch")
        assert not exists_fake

    @pytest.mark.asyncio
    async def test_create_branch(self, git_ops):
        """Test creating a branch."""
        await git_ops.create_branch("test-branch")

        # Should exist now
        exists = await git_ops.branch_exists("test-branch")
        assert exists

    @pytest.mark.asyncio
    async def test_create_feature_branch(self, git_ops):
        """Test creating feature branch."""
        branch_name = await git_ops.create_feature_branch(
            feature_id="F-100",
            feature_name="Authentication System",
            base_branch=await git_ops.get_current_branch()
        )

        assert branch_name == "feature/F-100-authentication-system"

        # Should exist
        exists = await git_ops.branch_exists(branch_name)
        assert exists

    @pytest.mark.asyncio
    async def test_create_feature_branch_idempotent(self, git_ops):
        """Test that creating same feature branch twice is idempotent."""
        main_branch = await git_ops.get_current_branch()

        branch1 = await git_ops.create_feature_branch(
            feature_id="F-200",
            feature_name="User Profile",
            base_branch=main_branch
        )

        # Create again
        branch2 = await git_ops.create_feature_branch(
            feature_id="F-200",
            feature_name="User Profile",
            base_branch=main_branch
        )

        assert branch1 == branch2

    @pytest.mark.asyncio
    async def test_get_main_branch(self, git_ops):
        """Test detecting main branch."""
        main_branch = await git_ops.get_main_branch()
        assert main_branch in ["main", "master"]

    @pytest.mark.asyncio
    async def test_git_command_error_handling(self, tmp_path):
        """Test error handling for invalid git commands."""
        # Use non-git directory
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()

        git_ops = GitOperations(repo_path=non_repo)

        with pytest.raises(GitOperationError):
            await git_ops.get_current_branch()
```

Run tests:
```bash
pytest tests/unit/workspace/test_git_operations.py -v
```

**Success Criteria**:
- ✅ GitOperations class created with async git commands
- ✅ Feature branch creation works
- ✅ Branch existence checking works
- ✅ Error handling with GitOperationError
- ✅ All tests pass

---

### Tuesday: Implement Worktree Creation

**What**: Implement `create_workspace()` in WorkspaceManager to create git worktrees.

**Why**: Git worktrees allow multiple working directories for the same repository. Each task gets its own worktree on the feature branch.

**How**:

#### Step 2.1: Update WorkspaceManager with worktree logic

Update `src/workspace/manager.py`:

```python
"""
Workspace manager for git worktree-based task isolation.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from src.core.error_framework import WorkspaceError, ErrorContext
from src.core.models import Task
from src.workspace.git_operations import GitOperations

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceInfo:
    """Information about a task workspace."""
    task_id: str
    feature_id: str
    workspace_path: Path
    feature_branch: str
    is_active: bool
    created_at: str


class WorkspaceManager:
    """Manages git worktree-based workspaces for task isolation."""

    def __init__(self, project_root: Path):
        """Initialize workspace manager."""
        self.project_root = project_root
        self.worktrees_dir = project_root / ".marcus" / "worktrees"
        self.active_workspaces: Dict[str, WorkspaceInfo] = {}
        self.git_ops = GitOperations(repo_path=project_root)

        logger.info(f"WorkspaceManager initialized for {project_root}")

    async def create_workspace(
        self, task: Task, feature_branch: str
    ) -> WorkspaceInfo:
        """
        Create isolated workspace for a task.

        Creates git worktree at .marcus/worktrees/{task_id}/

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
        logger.info(
            f"Creating workspace for task {task.id} "
            f"on branch {feature_branch}"
        )

        # Check if workspace already exists
        if task.id in self.active_workspaces:
            logger.warning(f"Workspace for {task.id} already exists")
            return self.active_workspaces[task.id]

        try:
            # Ensure feature branch exists
            if not await self.git_ops.branch_exists(feature_branch):
                main_branch = await self.git_ops.get_main_branch()
                await self.git_ops.create_branch(feature_branch, main_branch)

            # Create worktree directory
            workspace_path = self.worktrees_dir / task.id
            workspace_path.parent.mkdir(parents=True, exist_ok=True)

            # Create git worktree
            await self.git_ops._run_git_command(
                "worktree", "add", str(workspace_path), feature_branch
            )

            # Create workspace info
            workspace_info = WorkspaceInfo(
                task_id=task.id,
                feature_id=task.feature_id or "unknown",
                workspace_path=workspace_path,
                feature_branch=feature_branch,
                is_active=True,
                created_at=datetime.now(timezone.utc).isoformat()
            )

            # Track workspace
            self.active_workspaces[task.id] = workspace_info

            logger.info(f"Workspace created at {workspace_path}")
            return workspace_info

        except Exception as e:
            logger.error(f"Failed to create workspace: {e}")
            raise WorkspaceError(
                f"Failed to create workspace for task {task.id}: {e}",
                context=ErrorContext(
                    operation="create_workspace",
                    task_id=task.id,
                    feature_branch=feature_branch
                )
            )

    async def cleanup_workspace(self, task_id: str) -> None:
        """
        Clean up workspace after task completion.

        Removes git worktree and metadata.

        Parameters
        ----------
        task_id : str
            Task whose workspace should be cleaned up

        Raises
        ------
        WorkspaceError
            If cleanup fails
        """
        logger.info(f"Cleaning up workspace for task {task_id}")

        workspace_info = self.active_workspaces.get(task_id)
        if not workspace_info:
            logger.warning(f"No workspace found for task {task_id}")
            return

        try:
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

    async def get_workspace(self, task_id: str) -> Optional[WorkspaceInfo]:
        """Get workspace information for a task."""
        return self.active_workspaces.get(task_id)

    async def list_active_workspaces(self) -> list[WorkspaceInfo]:
        """List all active workspaces."""
        return list(self.active_workspaces.values())
```

#### Step 2.2: Update error framework

Add WorkspaceError if not already defined. Update `src/core/error_framework.py`:

```python
class WorkspaceError(MarcusBaseError):
    """Raised when workspace operations fail."""

    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            error_code="WORKSPACE_ERROR",
            user_message=message,
            technical_details=message,
            context=context
        )
```

#### Step 2.3: Write tests

Update `tests/unit/workspace/test_manager_skeleton.py` → `tests/unit/workspace/test_manager.py`:

```python
"""
Tests for WorkspaceManager.

Uses real git repository for testing worktree operations.
"""

import pytest
import subprocess
from pathlib import Path
from datetime import datetime

from src.workspace.manager import WorkspaceManager, WorkspaceInfo, WorkspaceError
from src.core.models import Task, TaskStatus, Priority


class TestWorkspaceManager:
    """Test WorkspaceManager worktree operations"""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a real git repository."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path, check=True
        )

        # Initial commit
        (repo_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path, check=True
        )

        # Create feature branch
        subprocess.run(
            ["git", "branch", "feature/F-100-test"],
            cwd=repo_path, check=True
        )

        return repo_path

    @pytest.fixture
    def manager(self, git_repo):
        """Create WorkspaceManager."""
        return WorkspaceManager(project_root=git_repo)

    @pytest.fixture
    def sample_task(self):
        """Create sample task."""
        return Task(
            id="T-IMPL-1",
            name="Implement feature",
            description="Implement the feature",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=8.0,
            labels=["feature"],
            feature_id="F-100"
        )

    @pytest.mark.asyncio
    async def test_create_workspace(self, manager, sample_task, git_repo):
        """Test creating a workspace."""
        workspace = await manager.create_workspace(
            task=sample_task,
            feature_branch="feature/F-100-test"
        )

        assert workspace.task_id == sample_task.id
        assert workspace.feature_id == "F-100"
        assert workspace.is_active is True
        assert workspace.workspace_path.exists()

        # Worktree should be on correct branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=workspace.workspace_path,
            capture_output=True,
            text=True
        )
        assert result.stdout.strip() == "feature/F-100-test"

    @pytest.mark.asyncio
    async def test_create_workspace_idempotent(
        self, manager, sample_task
    ):
        """Test creating same workspace twice."""
        workspace1 = await manager.create_workspace(
            task=sample_task,
            feature_branch="feature/F-100-test"
        )

        workspace2 = await manager.create_workspace(
            task=sample_task,
            feature_branch="feature/F-100-test"
        )

        assert workspace1.workspace_path == workspace2.workspace_path

    @pytest.mark.asyncio
    async def test_cleanup_workspace(self, manager, sample_task):
        """Test cleaning up workspace."""
        # Create workspace
        workspace = await manager.create_workspace(
            task=sample_task,
            feature_branch="feature/F-100-test"
        )

        workspace_path = workspace.workspace_path
        assert workspace_path.exists()

        # Cleanup
        await manager.cleanup_workspace(sample_task.id)

        # Should be removed
        assert not workspace_path.exists()
        assert sample_task.id not in manager.active_workspaces

    @pytest.mark.asyncio
    async def test_list_active_workspaces(self, manager):
        """Test listing active workspaces."""
        task1 = Task(
            id="T-1", name="Task 1", description="", status=TaskStatus.TODO,
            priority=Priority.HIGH, estimated_hours=8.0, labels=[],
            feature_id="F-100"
        )
        task2 = Task(
            id="T-2", name="Task 2", description="", status=TaskStatus.TODO,
            priority=Priority.HIGH, estimated_hours=8.0, labels=[],
            feature_id="F-100"
        )

        await manager.create_workspace(task1, "feature/F-100-test")
        await manager.create_workspace(task2, "feature/F-100-test")

        workspaces = await manager.list_active_workspaces()
        assert len(workspaces) == 2

    @pytest.mark.asyncio
    async def test_get_workspace(self, manager, sample_task):
        """Test getting workspace info."""
        await manager.create_workspace(
            task=sample_task,
            feature_branch="feature/F-100-test"
        )

        workspace = await manager.get_workspace(sample_task.id)
        assert workspace is not None
        assert workspace.task_id == sample_task.id
```

Run tests:
```bash
pytest tests/unit/workspace/test_manager.py -v
```

**Success Criteria**:
- ✅ `create_workspace()` creates git worktrees
- ✅ `cleanup_workspace()` removes worktrees
- ✅ Workspaces tracked in `active_workspaces`
- ✅ Idempotent operations (safe to call twice)
- ✅ All tests pass

---

### Wednesday: Integrate Workspace Manager with request_next_task

**What**: Update `request_next_task` to create workspaces and provide workspace path in instructions.

**Why**: Agents need to know where to work. The instructions must tell them: "Work in this directory: `/path/to/workspace`".

**How**:

#### Step 3.1: Update request_next_task to use WorkspaceManager

Update `src/marcus_mcp/tools/task.py` in the `request_next_task` function:

```python
async def request_next_task(agent_id: str, state: Any) -> Any:
    """
    Request next optimal task assignment for agent.

    Now includes workspace creation for task isolation.
    """
    try:
        # ... existing task finding logic ...

        optimal_task = await find_optimal_task_for_agent(agent_id, state)

        if not optimal_task:
            return {
                "success": False,
                "message": "No available tasks at this time"
            }

        # NEW: Create workspace if workspace manager enabled
        workspace_path = None
        feature_branch = None

        if state.workspace_manager and optimal_task.feature_id:
            try:
                # Get feature to determine branch
                feature = state.features.get(optimal_task.feature_id)

                if feature:
                    # Create workspace
                    workspace_info = await state.workspace_manager.create_workspace(
                        task=optimal_task,
                        feature_branch=feature.feature_branch
                    )

                    workspace_path = str(workspace_info.workspace_path)
                    feature_branch = feature.feature_branch

                    logger.info(
                        f"Created workspace for task {optimal_task.id} "
                        f"at {workspace_path}"
                    )

            except Exception as e:
                logger.error(f"Failed to create workspace: {e}")
                # Continue without workspace (fallback to main directory)

        # ... existing context building ...

        context_data = await state.context.get_context(
            optimal_task.id, dependency_ids
        )

        # Build instructions (now includes workspace path)
        instructions = build_tiered_instructions(
            base_instructions=get_base_instructions(),
            task=optimal_task,
            context_data=context_data,
            dependency_awareness=True,
            predictions=predictions,
            workspace_path=workspace_path,  # NEW
            feature_branch=feature_branch   # NEW
        )

        # ... rest of function ...

    except Exception as e:
        logger.error(f"Error in request_next_task: {e}")
        return handle_mcp_tool_error(e, "request_next_task", {"agent_id": agent_id})
```

#### Step 3.2: Update build_tiered_instructions

Update the `build_tiered_instructions` helper function in `src/marcus_mcp/tools/task.py`:

```python
def build_tiered_instructions(
    base_instructions: str,
    task: Task,
    context_data: Optional[Dict[str, Any]],
    dependency_awareness: bool,
    predictions: Optional[Dict[str, Any]] = None,
    workspace_path: Optional[str] = None,  # NEW
    feature_branch: Optional[str] = None    # NEW
) -> str:
    """
    Build tiered instructions for task execution.

    Now includes mandatory workspace and git workflow instructions.
    """
    parts = [base_instructions]

    # MANDATORY: Workspace and Git Instructions (if available)
    if workspace_path and feature_branch:
        git_instructions = f"""
# WORKSPACE AND GIT WORKFLOW (MANDATORY)

You MUST work in this isolated workspace:
```
{workspace_path}
```

This workspace is on the feature branch: `{feature_branch}`

## Git Workflow Rules:

1. **Change Directory First**:
   ```bash
   cd {workspace_path}
   ```

2. **All Work Must Be in Workspace**:
   - Read files from workspace: `{workspace_path}/src/...`
   - Write files to workspace: `{workspace_path}/src/...`
   - Run commands in workspace: `cd {workspace_path} && pytest`

3. **Commit Your Work**:
   - When task is complete, commit changes:
     ```bash
     cd {workspace_path}
     git add .
     git commit -m "feat: {task.name} ({task.id})"
     ```
   - Include task ID in commit message for traceability

4. **Push to Feature Branch**:
   ```bash
   git push origin {feature_branch}
   ```

5. **Do NOT**:
   - Work in the main repository directory
   - Switch branches (you're already on the correct branch)
   - Merge or rebase (that happens later)

Your workspace is isolated - other agents can work simultaneously without conflicts.
"""
        parts.append(git_instructions)

    # Task details
    parts.append(f"\n# TASK DETAILS\n\n{task.description}")

    # Context from dependencies
    if context_data and context_data.get("dependency_context"):
        parts.append(
            f"\n# CONTEXT FROM DEPENDENCIES\n\n"
            f"{context_data['dependency_context']}"
        )

    # Predictions (if available)
    if predictions:
        parts.append(f"\n# PREDICTIONS\n\n{format_predictions(predictions)}")

    return "\n".join(parts)
```

#### Step 3.3: Write tests

Create `tests/integration/test_workspace_integration.py`:

```python
"""
Integration test for workspace creation in request_next_task.
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from src.marcus_mcp.state import MarcusState
from src.marcus_mcp.tools.task import request_next_task
from src.core.models import Task, TaskStatus, Priority, Feature, Project
from src.workspace.manager import WorkspaceManager


class TestWorkspaceIntegration:
    """Test workspace integration with request_next_task"""

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
            ["git", "config", "user.name", "Test"],
            cwd=repo_path, check=True
        )

        (repo_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo_path, check=True
        )

        return repo_path

    @pytest.fixture
    async def state_with_workspace_manager(self, tmp_path, git_repo):
        """Create state with workspace manager."""
        state = MarcusState(storage_dir=str(tmp_path / "data"))
        await state.initialize()

        # Initialize workspace manager
        await state.initialize_workspace_manager(git_repo)

        # Create project
        project = Project(
            project_id="proj-1",
            name="Test Project",
            repo_url="https://github.com/test/repo",
            local_path=git_repo,
            main_branch="master",
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
            task_ids=["T-IMPL-1"]
        )
        state.features[feature.feature_id] = feature

        # Create feature branch
        subprocess.run(
            ["git", "branch", "feature/F-100-auth"],
            cwd=git_repo, check=True
        )

        return state

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_request_next_task_creates_workspace(
        self, state_with_workspace_manager, git_repo
    ):
        """Test that request_next_task creates workspace."""
        state = state_with_workspace_manager

        # Create task
        task = Task(
            id="T-IMPL-1",
            name="Implement auth",
            description="Add authentication",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=8.0,
            labels=["feature"],
            feature_id="F-100",
            project_id="proj-1"
        )

        # Add to kanban (mock)
        state.kanban = Mock()
        state.kanban.find_optimal_task = AsyncMock(return_value=task)
        state.kanban.update_task_status = AsyncMock()

        # Register agent
        await state.register_agent("agent-1", "Test Agent", "developer", [])

        # Request task
        result = await request_next_task(agent_id="agent-1", state=state)

        # Should succeed
        assert result["success"] is True

        # Should create workspace
        workspace = await state.workspace_manager.get_workspace("T-IMPL-1")
        assert workspace is not None
        assert workspace.workspace_path.exists()

        # Instructions should include workspace path
        assert str(workspace.workspace_path) in result["assignment"]["instructions"]
        assert "feature/F-100-auth" in result["assignment"]["instructions"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workspace_path_in_instructions(
        self, state_with_workspace_manager
    ):
        """Test that instructions contain workspace path."""
        state = state_with_workspace_manager

        # ... setup task and agent ...

        result = await request_next_task(agent_id="agent-1", state=state)

        instructions = result["assignment"]["instructions"]

        # Must contain workspace path
        assert "cd " in instructions
        assert "WORKSPACE AND GIT WORKFLOW" in instructions
        assert "feature/F-100-auth" in instructions
        assert "git commit" in instructions
```

Run tests:
```bash
pytest tests/integration/test_workspace_integration.py -v
```

**Success Criteria**:
- ✅ `request_next_task` creates workspace for tasks
- ✅ Instructions include workspace path
- ✅ Git workflow instructions are mandatory
- ✅ Multiple agents can work simultaneously
- ✅ All tests pass

---

### Thursday: Implement Workspace Cleanup

**What**: Add automatic workspace cleanup when tasks complete.

**Why**: Worktrees should be cleaned up after task completion to save disk space and keep the repository clean.

**How**:

#### Step 4.1: Add cleanup hook to task completion

Update `src/marcus_mcp/tools/task.py` in `report_task_progress`:

```python
async def report_task_progress(
    agent_id: str,
    task_id: str,
    status: str,
    progress: int = 0,
    message: str = "",
    state: Any = None
) -> Any:
    """
    Report progress on a task.

    Now includes automatic workspace cleanup on completion.
    """
    try:
        # ... existing progress reporting logic ...

        # Update task status
        await state.kanban.update_task_status(task_id, status)

        # NEW: Cleanup workspace if task completed
        if status.lower() in ["completed", "done"] and state.workspace_manager:
            try:
                await state.workspace_manager.cleanup_workspace(task_id)
                logger.info(f"Cleaned up workspace for completed task {task_id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup workspace: {e}")
                # Don't fail the whole operation if cleanup fails

        return {
            "success": True,
            "message": f"Progress reported for task {task_id}",
            "status": status,
            "progress": progress
        }

    except Exception as e:
        logger.error(f"Error reporting task progress: {e}")
        return handle_mcp_tool_error(
            e, "report_task_progress",
            {"agent_id": agent_id, "task_id": task_id}
        )
```

#### Step 4.2: Add cleanup command for stuck workspaces

Add new MCP tool `cleanup_workspace` in `src/marcus_mcp/tools/workspace.py`:

```python
"""
Workspace management MCP tools.
"""

import logging
from typing import Any, Dict

from src.core.error_responses import handle_mcp_tool_error

logger = logging.getLogger(__name__)


async def cleanup_workspace(
    task_id: str,
    force: bool = False,
    state: Any = None
) -> Dict[str, Any]:
    """
    Manually cleanup a workspace.

    Use this to clean up stuck or abandoned workspaces.

    Parameters
    ----------
    task_id : str
        Task ID whose workspace to cleanup
    force : bool
        Force cleanup even if task is still active
    state : Any
        Marcus state

    Returns
    -------
    Dict[str, Any]
        Result of cleanup operation
    """
    try:
        if not state.workspace_manager:
            return {
                "success": False,
                "message": "Workspace manager not enabled"
            }

        workspace = await state.workspace_manager.get_workspace(task_id)

        if not workspace:
            return {
                "success": False,
                "message": f"No workspace found for task {task_id}"
            }

        if workspace.is_active and not force:
            return {
                "success": False,
                "message": (
                    f"Workspace for {task_id} is still active. "
                    "Use force=True to cleanup anyway."
                )
            }

        # Cleanup
        await state.workspace_manager.cleanup_workspace(task_id)

        return {
            "success": True,
            "message": f"Workspace cleaned up for task {task_id}",
            "workspace_path": str(workspace.workspace_path)
        }

    except Exception as e:
        logger.error(f"Error cleaning up workspace: {e}")
        return handle_mcp_tool_error(
            e, "cleanup_workspace", {"task_id": task_id}
        )


async def list_workspaces(state: Any) -> Dict[str, Any]:
    """
    List all active workspaces.

    Returns
    -------
    Dict[str, Any]
        List of active workspaces
    """
    try:
        if not state.workspace_manager:
            return {
                "success": False,
                "message": "Workspace manager not enabled"
            }

        workspaces = await state.workspace_manager.list_active_workspaces()

        return {
            "success": True,
            "workspaces": [
                {
                    "task_id": ws.task_id,
                    "feature_id": ws.feature_id,
                    "workspace_path": str(ws.workspace_path),
                    "feature_branch": ws.feature_branch,
                    "created_at": ws.created_at
                }
                for ws in workspaces
            ],
            "count": len(workspaces)
        }

    except Exception as e:
        logger.error(f"Error listing workspaces: {e}")
        return handle_mcp_tool_error(e, "list_workspaces", {})
```

#### Step 4.3: Register new tools in server

Update `src/marcus_mcp/server.py` to register new tools:

```python
from src.marcus_mcp.tools.workspace import cleanup_workspace, list_workspaces

# In the tool registration section:
server.add_tool(
    name="cleanup_workspace",
    description="Manually cleanup a task workspace",
    handler=cleanup_workspace
)

server.add_tool(
    name="list_workspaces",
    description="List all active workspaces",
    handler=list_workspaces
)
```

#### Step 4.4: Write tests

Create `tests/unit/mcp/test_workspace_tools.py`:

```python
"""
Tests for workspace MCP tools.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from pathlib import Path

from src.marcus_mcp.tools.workspace import cleanup_workspace, list_workspaces
from src.workspace.manager import WorkspaceInfo


class TestWorkspaceTools:
    """Test workspace MCP tools"""

    @pytest.fixture
    def mock_state(self):
        """Create mock state with workspace manager."""
        state = Mock()
        state.workspace_manager = Mock()
        return state

    @pytest.mark.asyncio
    async def test_cleanup_workspace_success(self, mock_state):
        """Test successful workspace cleanup."""
        workspace_info = WorkspaceInfo(
            task_id="T-1",
            feature_id="F-100",
            workspace_path=Path("/tmp/workspace"),
            feature_branch="feature/F-100-test",
            is_active=False,
            created_at="2025-01-06T00:00:00Z"
        )

        mock_state.workspace_manager.get_workspace = AsyncMock(
            return_value=workspace_info
        )
        mock_state.workspace_manager.cleanup_workspace = AsyncMock()

        result = await cleanup_workspace(
            task_id="T-1",
            force=False,
            state=mock_state
        )

        assert result["success"] is True
        mock_state.workspace_manager.cleanup_workspace.assert_called_once_with("T-1")

    @pytest.mark.asyncio
    async def test_cleanup_workspace_not_found(self, mock_state):
        """Test cleanup when workspace doesn't exist."""
        mock_state.workspace_manager.get_workspace = AsyncMock(return_value=None)

        result = await cleanup_workspace(
            task_id="T-999",
            force=False,
            state=mock_state
        )

        assert result["success"] is False
        assert "No workspace found" in result["message"]

    @pytest.mark.asyncio
    async def test_cleanup_active_workspace_requires_force(self, mock_state):
        """Test that cleaning active workspace requires force flag."""
        workspace_info = WorkspaceInfo(
            task_id="T-1",
            feature_id="F-100",
            workspace_path=Path("/tmp/workspace"),
            feature_branch="feature/F-100-test",
            is_active=True,  # Still active
            created_at="2025-01-06T00:00:00Z"
        )

        mock_state.workspace_manager.get_workspace = AsyncMock(
            return_value=workspace_info
        )

        result = await cleanup_workspace(
            task_id="T-1",
            force=False,
            state=mock_state
        )

        assert result["success"] is False
        assert "still active" in result["message"]

    @pytest.mark.asyncio
    async def test_list_workspaces(self, mock_state):
        """Test listing workspaces."""
        workspaces = [
            WorkspaceInfo(
                task_id="T-1",
                feature_id="F-100",
                workspace_path=Path("/tmp/ws1"),
                feature_branch="feature/F-100",
                is_active=True,
                created_at="2025-01-06T00:00:00Z"
            ),
            WorkspaceInfo(
                task_id="T-2",
                feature_id="F-100",
                workspace_path=Path("/tmp/ws2"),
                feature_branch="feature/F-100",
                is_active=True,
                created_at="2025-01-06T00:00:00Z"
            )
        ]

        mock_state.workspace_manager.list_active_workspaces = AsyncMock(
            return_value=workspaces
        )

        result = await list_workspaces(state=mock_state)

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["workspaces"]) == 2
```

Run tests:
```bash
pytest tests/unit/mcp/test_workspace_tools.py -v
```

**Success Criteria**:
- ✅ Automatic cleanup on task completion
- ✅ Manual cleanup tool (`cleanup_workspace`)
- ✅ List workspaces tool (`list_workspaces`)
- ✅ Safety checks (don't cleanup active workspaces without force)
- ✅ All tests pass

---

### Friday: Week 3 Testing & Documentation

**What**: End-to-end testing of workspace isolation and documentation.

**Why**: Verify that the full workspace isolation workflow works correctly before moving to feature context next week.

**How**:

#### Step 5.1: Write end-to-end test

Create `tests/integration/e2e/test_workspace_e2e.py`:

```python
"""
End-to-end test for workspace isolation.

Simulates full workflow:
1. Agent requests task
2. Workspace created
3. Agent works in workspace
4. Agent reports completion
5. Workspace cleaned up
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from src.marcus_mcp.state import MarcusState
from src.marcus_mcp.tools.task import request_next_task, report_task_progress
from src.core.models import Task, TaskStatus, Priority, Feature, Project


class TestWorkspaceE2E:
    """End-to-end workspace isolation tests"""

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
            ["git", "config", "user.name", "Test"],
            cwd=repo_path, check=True
        )

        (repo_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
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
            feature_name="Authentication",
            project_id="proj-1",
            feature_branch="feature/F-100-auth",
            status="in_progress",
            task_ids=["T-IMPL-1"]
        )
        state.features[feature.feature_id] = feature

        # Create feature branch
        subprocess.run(
            ["git", "branch", "feature/F-100-auth"],
            cwd=git_repo, check=True
        )

        # Register agent
        await state.register_agent(
            "agent-1", "Test Agent", "developer", []
        )

        return state

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_full_workspace_lifecycle(self, full_state, git_repo):
        """Test complete workspace lifecycle."""
        state = full_state

        # Create task
        task = Task(
            id="T-IMPL-1",
            name="Implement auth",
            description="Add authentication",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=8.0,
            labels=["feature"],
            feature_id="F-100",
            project_id="proj-1"
        )

        # Mock kanban to return our task
        state.kanban.find_optimal_task = AsyncMock(return_value=task)
        state.kanban.update_task_status = AsyncMock()

        # Step 1: Agent requests task
        request_result = await request_next_task(
            agent_id="agent-1", state=state
        )

        assert request_result["success"] is True

        # Step 2: Workspace should be created
        workspace = await state.workspace_manager.get_workspace("T-IMPL-1")
        assert workspace is not None
        assert workspace.workspace_path.exists()

        workspace_path = workspace.workspace_path

        # Step 3: Simulate agent working (create a file)
        (workspace_path / "auth.py").write_text("def authenticate(): pass")

        # Verify file exists in workspace
        assert (workspace_path / "auth.py").exists()

        # Step 4: Agent reports completion
        completion_result = await report_task_progress(
            agent_id="agent-1",
            task_id="T-IMPL-1",
            status="completed",
            progress=100,
            message="Implementation complete",
            state=state
        )

        assert completion_result["success"] is True

        # Step 5: Workspace should be cleaned up
        assert "T-IMPL-1" not in state.workspace_manager.active_workspaces

        # Workspace directory should be removed
        assert not workspace_path.exists()

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_parallel_workspace_isolation(self, full_state, git_repo):
        """Test that multiple agents can work in parallel."""
        state = full_state

        # Create two tasks
        task1 = Task(
            id="T-IMPL-1",
            name="Task 1",
            description="First task",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=8.0,
            labels=[],
            feature_id="F-100",
            project_id="proj-1"
        )

        task2 = Task(
            id="T-IMPL-2",
            name="Task 2",
            description="Second task",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=8.0,
            labels=[],
            feature_id="F-100",
            project_id="proj-1"
        )

        # Register second agent
        await state.register_agent(
            "agent-2", "Agent 2", "developer", []
        )

        # Mock kanban to return different tasks
        state.kanban.find_optimal_task = AsyncMock(
            side_effect=[task1, task2]
        )
        state.kanban.update_task_status = AsyncMock()

        # Both agents request tasks
        result1 = await request_next_task(agent_id="agent-1", state=state)
        result2 = await request_next_task(agent_id="agent-2", state=state)

        assert result1["success"] is True
        assert result2["success"] is True

        # Should have two workspaces
        ws1 = await state.workspace_manager.get_workspace("T-IMPL-1")
        ws2 = await state.workspace_manager.get_workspace("T-IMPL-2")

        assert ws1 is not None
        assert ws2 is not None

        # Workspaces should be different
        assert ws1.workspace_path != ws2.workspace_path

        # Both workspaces should exist
        assert ws1.workspace_path.exists()
        assert ws2.workspace_path.exists()

        # Agents can write to their own workspaces without conflicts
        (ws1.workspace_path / "file1.py").write_text("agent 1 work")
        (ws2.workspace_path / "file2.py").write_text("agent 2 work")

        assert (ws1.workspace_path / "file1.py").exists()
        assert (ws2.workspace_path / "file2.py").exists()

        # file1.py should NOT exist in workspace 2
        assert not (ws2.workspace_path / "file1.py").exists()
```

Run end-to-end tests:
```bash
pytest tests/integration/e2e/test_workspace_e2e.py -v
```

#### Step 5.2: Update documentation

Create `docs/features/WORKSPACE_ISOLATION.md`:

```markdown
# Workspace Isolation

**Status**: Implemented (Week 3)
**Version**: 1.0

## Overview

Marcus uses **git worktrees** to provide isolated workspaces for each task. This prevents file conflicts when multiple agents work in parallel.

## Architecture

```
project-root/
├── .marcus/
│   └── worktrees/
│       ├── T-IMPL-1/          # Workspace for task 1
│       │   ├── src/
│       │   └── ...
│       └── T-IMPL-2/          # Workspace for task 2
│           ├── src/
│           └── ...
├── src/                       # Main repository
└── docs/
```

Each workspace is a **git worktree** on the feature branch.

## How It Works

### 1. Agent Requests Task

```python
result = await request_next_task(agent_id="agent-1", state=state)
```

### 2. Workspace Created

- Creates git worktree at `.marcus/worktrees/{task_id}/`
- Worktree is on the feature branch (e.g., `feature/F-200-auth`)
- Workspace path included in instructions

### 3. Agent Works in Workspace

Agent receives instructions:

```
# WORKSPACE AND GIT WORKFLOW

You MUST work in this isolated workspace:
/path/to/repo/.marcus/worktrees/T-IMPL-1/

cd /path/to/repo/.marcus/worktrees/T-IMPL-1/
# All work happens here
```

### 4. Agent Commits Work

```bash
cd /path/to/repo/.marcus/worktrees/T-IMPL-1/
git add .
git commit -m "feat: Implement authentication (T-IMPL-1)"
git push origin feature/F-200-auth
```

### 5. Workspace Cleaned Up

When task completes:

```python
await report_task_progress(
    agent_id="agent-1",
    task_id="T-IMPL-1",
    status="completed"
)
# Workspace automatically cleaned up
```

## Benefits

- **No Conflicts**: Each agent works in isolated directory
- **Parallel Execution**: Multiple agents can work simultaneously
- **Git Integration**: Each workspace is on correct feature branch
- **Automatic Cleanup**: Workspaces removed after task completion

## Manual Workspace Management

### List Active Workspaces

```python
result = await list_workspaces(state=state)
print(f"Active workspaces: {result['count']}")
```

### Cleanup Stuck Workspace

```python
result = await cleanup_workspace(
    task_id="T-IMPL-1",
    force=True,
    state=state
)
```

## Configuration

Enable workspace isolation:

```python
# In state initialization
await state.initialize_workspace_manager(project_root=Path("/path/to/repo"))
```

## Troubleshooting

### Workspace not cleaned up

Use manual cleanup:

```python
await cleanup_workspace(task_id="T-IMPL-1", force=True, state=state)
```

### Git worktree errors

Check worktree status:

```bash
git worktree list
git worktree prune
```

## Next Steps (Week 4)

- Feature context aggregation
- Git commit tracking by feature
- `get_feature_status()` tool
```

#### Step 5.3: Run full test suite

```bash
# All workspace tests
pytest tests/unit/workspace/ -v
pytest tests/integration/test_workspace_integration.py -v
pytest tests/integration/e2e/test_workspace_e2e.py -v

# Check coverage
pytest tests/unit/workspace/ tests/integration/ --cov=src/workspace --cov-report=term-missing

# All tests
pytest tests/ -v --tb=short
```

**Success Criteria**:
- ✅ End-to-end test passes
- ✅ Parallel workspace test passes
- ✅ Documentation complete
- ✅ Coverage >= 80%
- ✅ Ready for Week 4 (Feature Context)

---
