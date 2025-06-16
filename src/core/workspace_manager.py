"""
WorkspaceManager: Handles workspace isolation and security for autonomous agents

This module ensures that client agents only operate within their designated
project directories and cannot access the PM Agent installation.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime


class WorkspaceSecurityError(Exception):
    """Raised when a security violation is detected"""
    pass


@dataclass
class WorkspaceConfig:
    """Configuration for a single workspace"""
    workspace_id: str
    path: str
    agent_id: Optional[str] = None
    is_readonly: bool = False
    
    def __post_init__(self):
        """Expand and validate the path"""
        self.path = os.path.abspath(os.path.expanduser(self.path))
        

@dataclass 
class ProjectWorkspaces:
    """Configuration for all project workspaces"""
    main_workspace: str
    agent_workspaces: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Expand all paths"""
        self.main_workspace = os.path.abspath(os.path.expanduser(self.main_workspace))
        self.agent_workspaces = {
            agent_id: os.path.abspath(os.path.expanduser(path))
            for agent_id, path in self.agent_workspaces.items()
        }


class WorkspaceManager:
    """
    Manages workspace isolation and security boundaries for PM Agent
    
    Key responsibilities:
    1. Auto-detect PM Agent installation directory
    2. Maintain list of forbidden paths
    3. Assign and validate agent workspaces
    4. Enforce security boundaries
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize WorkspaceManager with automatic PM Agent detection"""
        # Auto-detect PM Agent installation directory
        self.pm_agent_root = self._detect_pm_agent_root()
        
        # Initialize forbidden paths - PM Agent directory is always forbidden
        self.forbidden_paths: Set[str] = {
            self.pm_agent_root,
        }
        
        # Add common Python installation paths to forbidden list
        self._add_system_paths_to_forbidden()
        
        # Workspace assignments: agent_id -> WorkspaceConfig
        self.agent_workspaces: Dict[str, WorkspaceConfig] = {}
        
        # Project workspace configuration
        self.project_config: Optional[ProjectWorkspaces] = None
        
        # Load configuration
        if config_path:
            self.load_config(config_path)
        else:
            # Try to load from default locations
            self._load_default_config()
    
    def _detect_pm_agent_root(self) -> str:
        """
        Automatically detect PM Agent installation directory
        
        This works by finding the root of the PM Agent package structure
        """
        # Get the directory of this file
        current_file = os.path.abspath(__file__)
        
        # Navigate up to find the PM Agent root
        # We're in src/core/workspace_manager.py, so go up 2 levels
        pm_agent_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        
        # Validate that we found the correct directory
        expected_markers = ['src', 'scripts', 'config_pm_agent.json']
        for marker in expected_markers:
            if not os.path.exists(os.path.join(pm_agent_root, marker)):
                # If marker is missing, we might be in a different structure
                # Try alternative detection methods
                break
        
        return pm_agent_root
    
    def _add_system_paths_to_forbidden(self):
        """Add system Python paths to forbidden list"""
        forbidden_prefixes = [
            '/usr/lib/python',
            '/usr/local/lib/python',
            '/opt/homebrew/lib/python',
            '/System/Library',
            os.path.dirname(os.__file__),  # Python installation
        ]
        
        for prefix in forbidden_prefixes:
            if os.path.exists(prefix):
                self.forbidden_paths.add(os.path.abspath(prefix))
    
    def _load_default_config(self):
        """Try to load configuration from default locations"""
        config_locations = [
            # XDG config directory (preferred)
            os.path.expanduser("~/.config/pm-agent/config.json"),
            # Local config in PM Agent root
            os.path.join(self.pm_agent_root, "config_pm_agent.json"),
            # Environment variable
            os.environ.get("PM_AGENT_CONFIG", "")
        ]
        
        for location in config_locations:
            if location and os.path.exists(location):
                try:
                    self.load_config(location)
                    print(f"Loaded workspace config from: {location}", file=sys.stderr)
                    return
                except Exception as e:
                    print(f"Failed to load config from {location}: {e}", file=sys.stderr)
                    continue
    
    def load_config(self, config_path: str):
        """Load workspace configuration from file"""
        config_path = os.path.expanduser(config_path)
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Load project workspace configuration
        if 'project' in config and 'workspaces' in config['project']:
            workspaces = config['project']['workspaces']
            self.project_config = ProjectWorkspaces(
                main_workspace=workspaces.get('main', ''),
                agent_workspaces=workspaces.get('agents', {})
            )
            
            # Validate that project workspaces don't overlap with forbidden paths
            self._validate_project_workspaces()
        
        # Load additional forbidden paths if specified
        if 'security' in config and 'additional_forbidden_paths' in config['security']:
            for path in config['security']['additional_forbidden_paths']:
                self.add_forbidden_path(path)
    
    def _validate_project_workspaces(self):
        """Ensure project workspaces don't overlap with forbidden paths"""
        if not self.project_config:
            return
        
        all_workspaces = [self.project_config.main_workspace]
        all_workspaces.extend(self.project_config.agent_workspaces.values())
        
        for workspace in all_workspaces:
            for forbidden in self.forbidden_paths:
                if workspace.startswith(forbidden) or forbidden.startswith(workspace):
                    raise WorkspaceSecurityError(
                        f"Workspace {workspace} overlaps with forbidden path {forbidden}"
                    )
    
    def assign_agent_workspace(self, agent_id: str, workspace_path: Optional[str] = None) -> WorkspaceConfig:
        """
        Assign a workspace to an agent
        
        If workspace_path is not provided, assigns from project configuration
        """
        if workspace_path:
            # Explicit workspace assignment
            workspace = WorkspaceConfig(
                workspace_id=f"{agent_id}_workspace",
                path=workspace_path,
                agent_id=agent_id
            )
        elif self.project_config and agent_id in self.project_config.agent_workspaces:
            # Use pre-configured workspace
            workspace = WorkspaceConfig(
                workspace_id=f"{agent_id}_workspace",
                path=self.project_config.agent_workspaces[agent_id],
                agent_id=agent_id
            )
        elif self.project_config:
            # Fallback to main workspace
            workspace = WorkspaceConfig(
                workspace_id=f"{agent_id}_workspace",
                path=self.project_config.main_workspace,
                agent_id=agent_id
            )
        else:
            raise ValueError(f"No workspace available for agent {agent_id}")
        
        # Validate the workspace
        self.validate_path(workspace.path)
        
        # Store the assignment
        self.agent_workspaces[agent_id] = workspace
        
        return workspace
    
    def get_agent_workspace(self, agent_id: str) -> Optional[WorkspaceConfig]:
        """Get the assigned workspace for an agent"""
        return self.agent_workspaces.get(agent_id)
    
    def validate_path(self, path: str) -> str:
        """
        Validate that a path is allowed (not in forbidden paths)
        
        Returns the absolute path if valid
        Raises WorkspaceSecurityError if forbidden
        """
        absolute_path = os.path.abspath(os.path.expanduser(path))
        
        # Check against all forbidden paths
        for forbidden in self.forbidden_paths:
            if absolute_path.startswith(forbidden):
                raise WorkspaceSecurityError(
                    f"Access denied: {path} is within forbidden path {forbidden}"
                )
        
        return absolute_path
    
    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed without raising an exception"""
        try:
            self.validate_path(path)
            return True
        except WorkspaceSecurityError:
            return False
    
    def add_forbidden_path(self, path: str):
        """Add a path to the forbidden list"""
        absolute_path = os.path.abspath(os.path.expanduser(path))
        self.forbidden_paths.add(absolute_path)
    
    def get_forbidden_paths(self) -> List[str]:
        """Get list of all forbidden paths"""
        return sorted(list(self.forbidden_paths))
    
    def get_task_assignment_data(self, agent_id: str) -> Dict[str, any]:
        """
        Get workspace data to include in task assignments
        
        This data should be sent to agents so they know where to work
        and what paths to avoid
        """
        workspace = self.get_agent_workspace(agent_id)
        if not workspace:
            workspace = self.assign_agent_workspace(agent_id)
        
        return {
            'workspace_path': workspace.path,
            'workspace_id': workspace.workspace_id,
            'forbidden_paths': self.get_forbidden_paths(),
            'is_readonly': workspace.is_readonly
        }
    
    def log_security_violation(self, agent_id: str, attempted_path: str, operation: str):
        """Log a security violation attempt"""
        violation = {
            'timestamp': datetime.now().isoformat(),
            'agent_id': agent_id,
            'attempted_path': attempted_path,
            'operation': operation,
            'pm_agent_root': self.pm_agent_root
        }
        
        # In production, this would log to a security audit file
        # For now, print to stderr
        import sys
        print(f"SECURITY VIOLATION: {json.dumps(violation)}", file=sys.stderr)