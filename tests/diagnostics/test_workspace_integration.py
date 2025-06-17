#!/usr/bin/env python3
"""
Test workspace security and integration with PM Agent
Verifies that workspace isolation is working correctly
"""

import json
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.pm_agent_mvp_fixed import PMAgentMVP
from src.core.workspace_manager import WorkspaceSecurityError


def test_workspace_integration():
    """Test that PM Agent properly assigns and protects workspaces"""
    
    print("🔍 Testing Workspace Security Integration")
    print("=" * 60)
    
    # Initialize PM Agent
    pm_agent = PMAgentMVP()
    
    print("\n1. PM Agent Root Detection:")
    print(f"   PM Agent root: {pm_agent.workspace_manager.pm_agent_root}")
    print(f"   Forbidden paths: {len(pm_agent.workspace_manager.forbidden_paths)}")
    for path in list(pm_agent.workspace_manager.forbidden_paths)[:3]:
        print(f"     - {path}")
    
    # Test workspace manager initialization
    print("\n2. WorkspaceManager Configuration:")
    print(f"   Config loaded: {pm_agent.workspace_manager.project_config is not None}")
    if pm_agent.workspace_manager.project_config:
        print(f"   Main workspace: {pm_agent.workspace_manager.project_config.main_workspace}")
        print(f"   Agent workspaces: {len(pm_agent.workspace_manager.project_config.agent_workspaces)}")
        for agent_id, workspace in list(pm_agent.workspace_manager.project_config.agent_workspaces.items())[:3]:
            print(f"     - {agent_id}: {workspace}")
    
    # Test forbidden path protection
    print("\n3. Security Tests - Path Protection:")
    test_paths = [
        (pm_agent.workspace_manager.pm_agent_root, "PM Agent root", True),
        (os.path.join(pm_agent.workspace_manager.pm_agent_root, "src"), "PM Agent src", True),
        (os.path.join(pm_agent.workspace_manager.pm_agent_root, "config"), "PM Agent config", True),
        ("/tmp/safe_path", "External safe path", False),
        (os.path.expanduser("~/Downloads"), "User Downloads", False)
    ]
    
    for path, description, should_be_forbidden in test_paths:
        try:
            pm_agent.workspace_manager.validate_path(path)
            if should_be_forbidden:
                print(f"   ❌ FAILED: {description} was NOT protected!")
            else:
                print(f"   ✅ PASSED: {description} is accessible")
        except WorkspaceSecurityError:
            if should_be_forbidden:
                print(f"   ✅ PASSED: {description} is properly protected")
            else:
                print(f"   ❌ FAILED: {description} should be accessible!")
    
    # Test workspace assignment
    print("\n4. Workspace Assignment Test:")
    test_agents = ["test-agent-001", "test-agent-002", "test-agent-003"]
    
    for agent_id in test_agents:
        try:
            workspace_data = pm_agent.workspace_manager.get_task_assignment_data(agent_id)
            
            print(f"\n   Agent: {agent_id}")
            print(f"   Workspace: {workspace_data.get('workspace_path', 'None')}")
            print(f"   Forbidden paths: {len(workspace_data.get('forbidden_paths', []))}")
            
            # Verify PM Agent root is forbidden
            forbidden_paths = workspace_data.get('forbidden_paths', [])
            pm_root_protected = any(
                pm_agent.workspace_manager.pm_agent_root in path or 
                path in pm_agent.workspace_manager.pm_agent_root
                for path in forbidden_paths
            )
            
            if pm_root_protected:
                print("   ✅ PM Agent root is protected from this agent")
            else:
                print("   ❌ PM Agent root is NOT protected!")
                
        except Exception as e:
            print(f"   ⚠️  {agent_id}: {e}")
    
    # Test invalid workspace access attempt
    print("\n5. Invalid Access Simulation:")
    try:
        # Simulate an agent trying to access PM Agent files
        test_file = os.path.join(pm_agent.workspace_manager.pm_agent_root, "src", "core", "models.py")
        pm_agent.workspace_manager.validate_path(test_file)
        print("   ❌ SECURITY BREACH: Agent could access PM Agent source!")
    except WorkspaceSecurityError as e:
        print(f"   ✅ Access denied: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Workspace security integration test complete")
    
    # Summary
    print("\nSummary:")
    print(f"- PM Agent is installed at: {pm_agent.workspace_manager.pm_agent_root}")
    print(f"- {len(pm_agent.workspace_manager.forbidden_paths)} paths are protected")
    print("- Workspace isolation is " + 
          ("ACTIVE" if pm_agent.workspace_manager.forbidden_paths else "INACTIVE"))


if __name__ == "__main__":
    test_workspace_integration()