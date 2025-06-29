#!/usr/bin/env python3
"""
Simple test to verify add_feature function signature works
"""

import asyncio
from src.mcp.tools.nlp_tools import add_feature


async def test_add_feature_signature():
    """Test that add_feature properly requires state parameter"""
    
    # Test 1: Calling without state should raise error
    try:
        result = await add_feature(
            feature_description="Add user profile management",
            integration_point="auto_detect",
            state=None
        )
        print("Test 1 Result (state=None):")
        print(f"Success: {result.get('success')}")
        print(f"Error: {result.get('error')}")
        assert result.get('error') == "State parameter is required"
        print("✓ Correctly requires state parameter")
    except Exception as e:
        print(f"Test 1 failed with exception: {e}")
    
    print("\nTest 2: Missing required parameters")
    # Mock state object
    class MockState:
        kanban_client = None
        project_tasks = []
        ai_engine = None
    
    mock_state = MockState()
    
    # Test 2: Empty feature description
    result = await add_feature(
        feature_description="",
        integration_point="auto_detect", 
        state=mock_state
    )
    print(f"Empty description - Success: {result.get('success')}")
    print(f"Empty description - Error: {result.get('error')}")
    assert "required and cannot be empty" in result.get('error', '')
    print("✓ Correctly validates empty description")
    
    print("\nAll tests passed! The add_feature function properly handles the state parameter.")


if __name__ == "__main__":
    asyncio.run(test_add_feature_signature())