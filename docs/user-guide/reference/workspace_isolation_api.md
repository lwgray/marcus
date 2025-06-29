# Marcus Workspace Isolation API Reference

> **Type**: API  
> **Version**: 1.0.0  
> **Last Updated**: 2025-06-25

## Overview

Complete reference for the workspace isolation system that provides secure, isolated environments for worker agents.

## Synopsis

```python
from src.core.workspace_manager import WorkspaceManager

# Initialize manager
workspace_manager = WorkspaceManager(base_path="/workspaces")

# Create isolated workspace
workspace = await workspace_manager.create_workspace(
    task_id="task-123",
    worker_id="backend-dev-001"
)
```

## Description

The Workspace Isolation system provides secure, isolated file system environments for each task assignment. This prevents agents from accessing sensitive files, ensures clean environments, and enables parallel task execution without conflicts.

## Parameters

### WorkspaceManager Class

Core workspace management functionality.

| Method | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `__init__(base_path)` | constructor | Yes | - | Initialize with base directory |
| `create_workspace()` | async | Yes | - | Create isolated workspace |
| `get_workspace()` | async | Yes | - | Retrieve existing workspace |
| `cleanup_workspace()` | async | Yes | - | Remove workspace and contents |
| `list_workspaces()` | async | Yes | - | List all active workspaces |
| `validate_access()` | async | Yes | - | Check path access permissions |

### Method Details

#### __init__()

Initialize workspace manager.

```python
def __init__(self, base_path: str = "/workspaces"):
    """
    Initialize workspace manager.
    
    Parameters:
        base_path: Root directory for all workspaces
        
    Raises:
        PermissionError: If base_path is not writable
    """
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `base_path` | string | No | "/workspaces" | Root directory for workspaces |

#### create_workspace()

Create a new isolated workspace.

```python
async def create_workspace(
    self,
    task_id: str,
    worker_id: str,
    template: Optional[str] = None,
    allowed_paths: Optional[List[str]] = None,
    forbidden_paths: Optional[List[str]] = None
) -> Workspace:
    """
    Create isolated workspace for task.
    
    Parameters:
        task_id: Unique task identifier
        worker_id: Worker who will use workspace
        template: Optional template to copy
        allowed_paths: Additional allowed paths
        forbidden_paths: Explicitly forbidden paths
        
    Returns:
        Workspace object with path and metadata
    """
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_id` | string | Yes | - | Task requiring workspace |
| `worker_id` | string | Yes | - | Worker assigned to task |
| `template` | string | No | None | Template directory to copy |
| `allowed_paths` | List[string] | No | None | Extra paths agent can access |
| `forbidden_paths` | List[string] | No | None | Paths to explicitly block |

##### Return Object
```python
@dataclass
class Workspace:
    path: str                    # Absolute workspace path
    task_id: str                # Associated task
    worker_id: str              # Assigned worker
    created_at: datetime        # Creation timestamp
    allowed_paths: List[str]    # Accessible paths
    forbidden_paths: List[str]  # Blocked paths
    metadata: Dict[str, Any]    # Additional metadata
```

#### validate_access()

Check if a path is accessible from workspace.

```python
async def validate_access(
    self,
    workspace_path: str,
    target_path: str
) -> bool:
    """
    Validate path access from workspace.
    
    Parameters:
        workspace_path: Current workspace
        target_path: Path to check
        
    Returns:
        True if access allowed, False otherwise
    """
```

### Security Policies

Default security policies applied to all workspaces:

| Policy | Description | Default |
|--------|-------------|---------|
| `workspace_only` | Restrict to workspace directory | Enabled |
| `no_parent_access` | Block parent directory access | Enabled |
| `no_system_paths` | Block system directories | Enabled |
| `no_home_access` | Block home directory access | Enabled |
| `allow_tmp` | Allow /tmp access | Disabled |

#### Forbidden Paths (Default)
```python
DEFAULT_FORBIDDEN = [
    "/etc",
    "/var",
    "/usr",
    "/sys",
    "/proc",
    "/root",
    "~",
    "..",
    "/Users/*/Documents",
    "/Users/*/Desktop",
    "/home/*/Documents"
]
```

#### Allowed Paths (Default)
```python
DEFAULT_ALLOWED = [
    "/tmp/pm-agent-*",  # Temporary files
    "/usr/local/bin",   # Common tools
    "/usr/bin",         # System utilities
]
```

## Return Values

### Success Response

```python
# Workspace creation
workspace = Workspace(
    path="/workspaces/task-123-backend-dev-001",
    task_id="task-123",
    worker_id="backend-dev-001",
    created_at=datetime.now(),
    allowed_paths=["/tmp/pm-agent-123"],
    forbidden_paths=["/etc", "/var"],
    metadata={"template": "python-web-app"}
)

# Access validation
is_allowed = True  # or False
```

### Error Response

```python
# Permission errors
PermissionError("Cannot create workspace: /workspaces not writable")

# Validation errors
ValueError("Invalid task_id: cannot be empty")

# Security errors
SecurityError("Path traversal detected: ../../../etc/passwd")

# Resource errors
ResourceError("Maximum workspaces (100) reached")
```

## Examples

### Basic Example
```python
# Simple workspace creation
manager = WorkspaceManager()

workspace = await manager.create_workspace(
    task_id="task-123",
    worker_id="backend-dev-001"
)

print(f"Workspace created at: {workspace.path}")
# Output: Workspace created at: /workspaces/task-123-backend-dev-001
```

### Advanced Example
```python
# Workspace with template and custom paths
class TaskWorkspaceManager:
    def __init__(self):
        self.workspace_manager = WorkspaceManager("/opt/workspaces")
        self.templates = {
            "python-api": "/templates/python-api",
            "react-app": "/templates/react-app",
            "full-stack": "/templates/full-stack"
        }
    
    async def setup_task_workspace(
        self,
        task: Task,
        worker: WorkerStatus
    ) -> Workspace:
        # Determine template based on task labels
        template = None
        if "python" in task.labels and "api" in task.labels:
            template = self.templates["python-api"]
        elif "react" in task.labels:
            template = self.templates["react-app"]
        
        # Custom paths based on task needs
        allowed_paths = []
        if "database" in task.labels:
            allowed_paths.append("/var/lib/postgresql/data")
        
        forbidden_paths = [
            "/production",
            "/secrets",
            "/.env",
            "/config/production.json"
        ]
        
        # Create workspace
        workspace = await self.workspace_manager.create_workspace(
            task_id=task.id,
            worker_id=worker.worker_id,
            template=template,
            allowed_paths=allowed_paths,
            forbidden_paths=forbidden_paths
        )
        
        # Initialize with task-specific files
        await self._initialize_workspace(workspace, task)
        
        return workspace
    
    async def _initialize_workspace(
        self,
        workspace: Workspace,
        task: Task
    ):
        # Create task README
        readme_path = os.path.join(workspace.path, "README.md")
        with open(readme_path, "w") as f:
            f.write(f"# Task: {task.name}\n\n")
            f.write(f"{task.description}\n\n")
            f.write(f"## Instructions\n\n")
            f.write(f"See INSTRUCTIONS.md for detailed steps.\n")
```

### Real-World Example
```python
# Production workspace isolation with monitoring
class SecureWorkspaceManager(WorkspaceManager):
    def __init__(self):
        super().__init__()
        self.monitor = WorkspaceMonitor()
        self.audit_log = AuditLogger()
    
    async def create_workspace(
        self,
        task_id: str,
        worker_id: str,
        **kwargs
    ) -> Workspace:
        # Log workspace creation
        self.audit_log.log({
            "action": "workspace_create",
            "task_id": task_id,
            "worker_id": worker_id,
            "timestamp": datetime.now()
        })
        
        # Create with monitoring
        workspace = await super().create_workspace(
            task_id, worker_id, **kwargs
        )
        
        # Set up file system monitoring
        await self.monitor.watch_workspace(workspace, {
            "on_suspicious_access": self._handle_suspicious_access,
            "on_forbidden_attempt": self._handle_forbidden_attempt,
            "on_excessive_io": self._handle_excessive_io
        })
        
        # Apply security policies
        await self._apply_security_policies(workspace)
        
        return workspace
    
    async def _apply_security_policies(self, workspace: Workspace):
        # Set directory permissions
        os.chmod(workspace.path, 0o750)
        
        # Create .gitignore to prevent secrets
        gitignore_path = os.path.join(workspace.path, ".gitignore")
        with open(gitignore_path, "w") as f:
            f.write("*.env\n")
            f.write("*.key\n")
            f.write("*.pem\n")
            f.write("secrets/\n")
            f.write("credentials/\n")
        
        # Set resource limits
        await self._set_resource_limits(workspace)
    
    async def _handle_suspicious_access(
        self,
        workspace: Workspace,
        access_info: Dict
    ):
        # Log security event
        self.audit_log.security_event({
            "type": "suspicious_access",
            "workspace": workspace.path,
            "details": access_info,
            "action": "monitored"
        })
        
        # Notify security team if critical
        if access_info.get("severity") == "high":
            await self.notify_security_team(workspace, access_info)
```

## Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `WORKSPACE_EXISTS` | Workspace already exists | Clean up or use existing |
| `PERMISSION_DENIED` | Cannot create in base path | Check directory permissions |
| `PATH_TRAVERSAL` | Detected path escape attempt | Review and fix path |
| `QUOTA_EXCEEDED` | Workspace limit reached | Clean up old workspaces |
| `TEMPLATE_NOT_FOUND` | Template directory missing | Verify template path |
| `INVALID_PATH` | Path contains invalid characters | Use valid path names |

## Notes

- Workspaces are automatically namespaced by task and worker
- Symbolic links are resolved to prevent escapes
- Hidden files are copied from templates
- Workspaces persist until explicitly cleaned
- Maximum 100 concurrent workspaces by default

## Performance Considerations

### Storage Management
- Each workspace typically uses 10-100MB
- Templates are copied, not linked
- Cleanup is async and batched
- Storage monitoring recommended

### File System Operations
| Operation | Average Time | Notes |
|-----------|--------------|-------|
| Create empty | 10-50ms | Depends on file system |
| Copy template | 100ms-2s | Based on template size |
| Validate access | <1ms | Cached after first check |
| Cleanup | 50-500ms | Recursive deletion |

### Resource Limits
```python
# Default limits per workspace
{
    "max_files": 10000,
    "max_size_mb": 1000,
    "max_processes": 10,
    "max_memory_mb": 512,
    "max_cpu_percent": 50
}
```

## Security Considerations

### Path Validation
- All paths canonicalized before checking
- Symbolic links resolved
- Unicode normalization applied
- Case-sensitive comparison

### Access Control
```python
# Example access check
def is_path_allowed(workspace_path: str, target_path: str) -> bool:
    # Resolve to absolute paths
    workspace_abs = os.path.abspath(workspace_path)
    target_abs = os.path.abspath(target_path)
    
    # Check if within workspace
    if target_abs.startswith(workspace_abs):
        return True
    
    # Check allowed list
    for allowed in workspace.allowed_paths:
        if target_abs.startswith(os.path.abspath(allowed)):
            return True
    
    # Check forbidden list
    for forbidden in workspace.forbidden_paths:
        if target_abs.startswith(os.path.abspath(forbidden)):
            return False
    
    # Default deny
    return False
```

## Version History

| Version | Changes |
|---------|---------|
| 1.0.0 | Complete workspace isolation documentation |
| 0.9.0 | Added resource limits |
| 0.8.0 | Added template support |
| 0.7.0 | Initial isolation implementation |

## See Also

- [Security Best Practices](/reference/security)
- [Task Assignment](/reference/task_assignment)
- [Worker Agent Guide](/how-to/worker_agents)
- [System Architecture](/reference/system_architecture)