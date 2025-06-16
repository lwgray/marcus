#!/usr/bin/env python3
"""
Test workspace integration with PM Agent
"""

import json
import sys
sys.path.insert(0, '.')

from src.pm_agent_mvp_fixed import PMAgentMVP
from src.core.workspace_manager import WorkspaceSecurityError


def test_workspace_integration():
    """Test that PM Agent properly assigns workspaces to agents"""
    
    print("🧪 Testing Workspace Integration")
    print("=" * 60)
    
    # Initialize PM Agent
    pm_agent = PMAgentMVP()
    
    print("\n1. PM Agent Root Detection:")
    print(f"   PM Agent root: {pm_agent.workspace_manager.pm_agent_root}")
    print(f"   Forbidden paths: {len(pm_agent.workspace_manager.forbidden_paths)}")
    
    # Test workspace manager initialization
    print("\n2. WorkspaceManager Status:")
    print(f"   Config loaded: {pm_agent.workspace_manager.project_config is not None}")
    if pm_agent.workspace_manager.project_config:
        print(f"   Main workspace: {pm_agent.workspace_manager.project_config.main_workspace}")
        print(f"   Agent workspaces: {len(pm_agent.workspace_manager.project_config.agent_workspaces)}")
    
    # Test forbidden path protection
    print("\n3. Security Test - PM Agent Directory Protection:")
    try:
        pm_agent.workspace_manager.validate_path(pm_agent.workspace_manager.pm_agent_root)
        print("   ❌ FAILED: PM Agent directory was not protected!")
    except WorkspaceSecurityError:
        print("   ✅ PASSED: PM Agent directory is properly protected")
    
    # Test workspace assignment
    print("\n4. Workspace Assignment Test:")
    try:
        # Simulate agent registration and workspace assignment
        test_agent_id = "test-agent-001"
        workspace_data = pm_agent.workspace_manager.get_task_assignment_data(test_agent_id)
        
        print(f"   Agent ID: {test_agent_id}")
        print(f"   Assigned workspace: {workspace_data.get('workspace_path', 'None')}")
        print(f"   Forbidden paths count: {len(workspace_data.get('forbidden_paths', []))}")
        
        # Check that PM Agent root is in forbidden paths
        if pm_agent.workspace_manager.pm_agent_root in workspace_data.get('forbidden_paths', []):
            print("   ✅ PM Agent root is in forbidden paths")
        else:
            print("   ❌ PM Agent root is NOT in forbidden paths!")
            
    except Exception as e:
        print(f"   ⚠️  Warning: {e}")
        print("   (This is expected if no workspace config is loaded)")
    
    print("\n" + "=" * 60)
    print("✅ Workspace integration test complete")


if __name__ == "__main__":
    test_workspace_integration()