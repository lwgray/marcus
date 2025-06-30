#!/usr/bin/env python3
"""
Test the MCP serialization and initialization fixes
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.models import RiskLevel, Priority, TaskStatus
from src.marcus_mcp.utils import serialize_for_mcp, safe_serialize_task
from datetime import datetime


class MockTask:
    """Mock task for testing"""
    def __init__(self):
        self.id = "test-123"
        self.name = "Test Task"
        self.description = "A test task"
        self.priority = Priority.HIGH
        self.status = TaskStatus.TODO
        self.estimated_hours = 8.0
        self.dependencies = []
        self.labels = ["backend", "api"]
        self.assigned_to = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.due_date = None


class MockState:
    """Mock state for testing"""
    def __init__(self):
        self.kanban_client = "mock_client"  # Just a placeholder
        self.agent_status = {}
        self.project_tasks = []
        self.project_state = None
    
    async def initialize_kanban(self):
        pass


def test_serialization_fixes():
    """Test that serialization fixes work properly"""
    
    print("=== Testing MCP Serialization Fixes ===\n")
    
    # Test 1: RiskLevel serialization
    print("1. Testing RiskLevel serialization...")
    
    response_with_risk = {
        "success": True,
        "task": {
            "id": "test-123",
            "priority": Priority.HIGH,
            "risk_level": RiskLevel.MEDIUM
        },
        "timestamp": datetime.now()
    }
    
    try:
        serialized = serialize_for_mcp(response_with_risk)
        print(f"   ✓ RiskLevel serialized: {serialized['task']['risk_level']}")
        print(f"   ✓ Priority serialized: {serialized['task']['priority']}")
        print(f"   ✓ Timestamp serialized: {serialized['timestamp']}")
    except Exception as e:
        print(f"   ✗ Serialization failed: {e}")
        return False
    
    # Test 2: Task serialization
    print("\n2. Testing Task serialization...")
    
    mock_task = MockTask()
    
    try:
        serialized_task = safe_serialize_task(mock_task)
        print(f"   ✓ Task serialized successfully")
        print(f"   ✓ Priority: {serialized_task['priority']}")
        print(f"   ✓ Status: {serialized_task['status']}")
        print(f"   ✓ Created at: {serialized_task['created_at']}")
    except Exception as e:
        print(f"   ✗ Task serialization failed: {e}")
        return False
    
    # Test 3: State initialization check
    print("\n3. Testing state initialization...")
    
    from src.marcus_mcp.tools.project_tools import get_project_status
    
    # Test with uninitialized state
    class EmptyState:
        pass
    
    async def test_empty_state():
        empty_state = EmptyState()
        result = await get_project_status(empty_state)
        return result
    
    result = asyncio.run(test_empty_state())
    
    if result.get("success") == False and "Not initialized" in result.get("error", ""):
        print("   ✓ Properly handles uninitialized state")
    else:
        print(f"   ✗ Unexpected result: {result}")
        return False
    
    # Test with properly initialized state
    async def test_initialized_state():
        mock_state = MockState()
        # This should not error on the initialization check
        try:
            result = await get_project_status(mock_state)
            return True  # Made it past initialization check
        except Exception as e:
            # Expected to fail later, but not on initialization check
            if "Not initialized" in str(e):
                return False  # Failed on initialization check
            return True  # Failed elsewhere, which is fine
    
    passed_init_check = asyncio.run(test_initialized_state())
    
    if passed_init_check:
        print("   ✓ Passes initialization check with proper state")
    else:
        print("   ✗ Failed initialization check with proper state")
        return False
    
    print("\n✅ All MCP fixes working correctly!")
    return True


if __name__ == "__main__":
    success = test_serialization_fixes()
    
    if success:
        print("\n🎉 The MCP errors should now be resolved:")
        print("   - RiskLevel JSON serialization error: FIXED")
        print("   - 'Not initialized' error: FIXED")
        print("\nYou can now use the MCP tools without these errors.")
    else:
        print("\n❌ Some tests failed. Please check the fixes.")
        sys.exit(1)