"""
Test using anyio instead of pytest-asyncio
"""

import pytest
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock
import anyio

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_ping_tool_anyio():
    """Test ping tool functionality using anyio"""
    os.environ['KANBAN_PROVIDER'] = 'planka'
    
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