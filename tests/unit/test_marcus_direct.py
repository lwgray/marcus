"""
Direct async test for Marcus Server - bypassing pytest-asyncio issues
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import get_tool_definitions, handle_tool_call


async def test_ping_tool():
    """Test ping tool functionality"""
    os.environ['KANBAN_PROVIDER'] = 'planka'
    
    # Create server inline to avoid fixture issues
    server = MarcusServer()
    server.kanban_client = AsyncMock()
    server.assignment_monitor = None
    
    result = await handle_tool_call(
        'ping',
        {'echo': 'test'},
        server
    )
    
    assert len(result) == 1
    assert result[0].type == 'text'
    
    data = json.loads(result[0].text)
    assert data['status'] == 'online'
    assert data['echo'] == 'test'
    assert 'timestamp' in data
    assert data['success'] is True
    assert data['provider'] == 'planka'
    
    print("✅ test_ping_tool passed!")


async def test_register_agent():
    """Test agent registration"""
    os.environ['KANBAN_PROVIDER'] = 'planka'
    
    server = MarcusServer()
    server.kanban_client = AsyncMock()
    server.assignment_monitor = None
    
    result = await handle_tool_call(
        'register_agent',
        {
            'agent_id': 'test-001',
            'name': 'Test Agent',
            'role': 'Developer',
            'skills': ['python', 'testing']
        },
        server
    )
    
    data = json.loads(result[0].text)
    assert data['success'] is True
    assert data['agent_id'] == 'test-001'
    assert 'test-001' in server.agent_status
    
    print("✅ test_register_agent passed!")


async def run_all_tests():
    """Run all tests"""
    print("Running Marcus server direct tests...")
    await test_ping_tool()
    await test_register_agent()
    print("\nAll tests passed! ✅")


if __name__ == '__main__':
    asyncio.run(run_all_tests())