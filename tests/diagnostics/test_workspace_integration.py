#!/usr/bin/env python3
"""
Test workspace security and integration with Marcus
Verifies that workspace isolation is working correctly
"""

import json
import sys
import os
import pytest
from unittest.mock import Mock, patch

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.marcus_mcp.server import MarcusServer
from src.core.workspace_manager import WorkspaceManager, WorkspaceSecurityError


class TestWorkspaceIntegration:
    """Test workspace security and integration features"""
    
    @pytest.fixture
    def workspace_manager(self):
        """Create a workspace manager for testing"""
        return WorkspaceManager()
    
    @pytest.fixture
    def marcus_server(self):
        """Create a Marcus server instance"""
        server = MarcusServer()
        server.assignment_monitor = None  # Disable for tests
        return server
    
    def test_workspace_root_detection(self, workspace_manager):
        """Test that Marcus properly detects its root directory"""
        assert workspace_manager.marcus_state_root is not None
        assert os.path.exists(workspace_manager.marcus_state_root)
        assert len(workspace_manager.forbidden_paths) > 0
    
    def test_forbidden_path_protection(self, workspace_manager):
        """Test that forbidden paths are protected"""
        # Try to access a forbidden path
        forbidden_path = os.path.join(workspace_manager.marcus_state_root, "secrets")
        
        with pytest.raises(WorkspaceSecurityError):
            workspace_manager.validate_path(forbidden_path)
    
    def test_safe_path_access(self, workspace_manager, tmp_path):
        """Test that safe paths can be accessed"""
        # Create a safe workspace
        safe_workspace = tmp_path / "agent_workspace"
        safe_workspace.mkdir()
        
        # This should not raise an error
        try:
            workspace_manager.validate_path(str(safe_workspace))
        except WorkspaceSecurityError:
            pytest.fail("Safe path validation should not raise WorkspaceSecurityError")
    
    def test_workspace_assignment(self, workspace_manager):
        """Test workspace assignment to agents"""
        agent_id = "test-agent-001"
        
        # Assign workspace
        workspace_path = workspace_manager.assign_workspace(agent_id)
        
        assert workspace_path is not None
        assert agent_id in workspace_path
        assert os.path.exists(workspace_path)
        
        # Verify it's in the allowed workspaces
        assert agent_id in workspace_manager.agent_workspaces
        assert workspace_manager.agent_workspaces[agent_id] == workspace_path
    
    def test_workspace_isolation(self, workspace_manager):
        """Test that agents can't access each other's workspaces"""
        # Create two agents with workspaces
        agent1_id = "agent-001"
        agent2_id = "agent-002"
        
        workspace1 = workspace_manager.assign_workspace(agent1_id)
        workspace2 = workspace_manager.assign_workspace(agent2_id)
        
        # Agent 1 should not be able to access agent 2's workspace
        test_file = os.path.join(workspace2, "secret.txt")
        
        with pytest.raises(WorkspaceSecurityError):
            workspace_manager.validate_agent_path(agent1_id, test_file)
        
        # But agent 2 should be able to access their own workspace
        try:
            workspace_manager.validate_agent_path(agent2_id, test_file)
        except WorkspaceSecurityError:
            pytest.fail("Agent should be able to access their own workspace")
    
    def test_marcus_integration(self, marcus_server):
        """Test that Marcus server properly integrates workspace security"""
        # Verify workspace manager is initialized
        assert hasattr(marcus_server, 'workspace_manager') or hasattr(marcus_server, 'assignment_persistence')
        
        # Register an agent
        agent_id = "secure-agent"
        marcus_server.agent_status[agent_id] = Mock(
            worker_id=agent_id,
            name="Secure Agent",
            role="Developer"
        )
        
        # If workspace manager exists, verify it works
        if hasattr(marcus_server, 'workspace_manager'):
            workspace = marcus_server.workspace_manager.assign_workspace(agent_id)
            assert workspace is not None
            assert os.path.exists(workspace)


def test_workspace_integration():
    """Run workspace integration tests (for direct execution)"""
    print("🔍 Testing Workspace Security Integration")
    print("=" * 60)
    
    # Initialize components
    workspace_manager = WorkspaceManager()
    marcus_server = MarcusServer()
    marcus_server.assignment_monitor = None
    
    print("\n1. Marcus Root Detection:")
    print(f"   Marcus root: {workspace_manager.marcus_state_root}")
    print(f"   Forbidden paths: {len(workspace_manager.forbidden_paths)}")
    for path in list(workspace_manager.forbidden_paths)[:3]:
        print(f"   - {path}")
    
    print("\n2. Workspace Assignment:")
    agent_id = "test-agent-001"
    try:
        workspace = workspace_manager.assign_workspace(agent_id)
        print(f"   ✅ Assigned workspace to {agent_id}")
        print(f"   Path: {workspace}")
    except Exception as e:
        print(f"   ❌ Failed to assign workspace: {e}")
    
    print("\n3. Security Validation:")
    # Test forbidden path
    forbidden = os.path.join(workspace_manager.marcus_state_root, "config")
    try:
        workspace_manager.validate_path(forbidden)
        print(f"   ❌ Security breach: accessed forbidden path!")
    except WorkspaceSecurityError:
        print(f"   ✅ Correctly blocked access to forbidden path")
    
    # Test safe path
    safe_path = os.path.join(workspace, "test.py")
    try:
        workspace_manager.validate_agent_path(agent_id, safe_path)
        print(f"   ✅ Correctly allowed access to agent workspace")
    except WorkspaceSecurityError:
        print(f"   ❌ Incorrectly blocked access to safe path")
    
    print("\n✅ Workspace integration test complete")


if __name__ == "__main__":
    # Run as script
    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        pytest.main([__file__, "-v"])
    else:
        test_workspace_integration()