"""
Integration test that reproduces the real duplicate assignment scenario.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
import json
from pathlib import Path
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class TestRealDuplicateScenario:
    """Test the real-world duplicate assignment scenario."""
    
    @pytest.mark.asyncio
    async def test_two_workers_sequential_requests(self):
        """Test that two workers requesting tasks sequentially don't get the same task."""
        
        # Start Marcus server in a subprocess
        import subprocess
        import time
        
        # Use a temporary directory for test data
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                **os.environ,
                "MARCUS_DATA_DIR": tmpdir
            }
            
            # Start Marcus server
            marcus_process = subprocess.Popen(
                ["python", "marcus_mcp_server.py"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Give it time to start
            time.sleep(2)
            
            try:
                # Connect as first worker
                server_params1 = StdioServerParameters(
                    command='python',
                    args=['marcus_mcp_server.py'],
                    env=env
                )
                
                async with stdio_client(server_params1) as (read1, write1):
                    async with ClientSession(read1, write1) as session1:
                        await session1.initialize()
                        
                        # Register first worker
                        result = await session1.call_tool(
                            'register_agent',
                            {
                                'agent_id': 'worker-1',
                                'name': 'Worker 1',
                                'role': 'Developer',
                                'skills': ['python', 'testing']
                            }
                        )
                        
                        # Request a task
                        result = await session1.call_tool(
                            'request_next_task',
                            {'agent_id': 'worker-1'}
                        )
                        
                        task1_data = json.loads(result.content[0].text)
                        assert task1_data.get('success'), "First worker should get a task"
                        task1_id = task1_data['task']['id']
                        
                # Wait a moment to simulate real delay
                await asyncio.sleep(1)
                
                # Connect as second worker (new connection)
                server_params2 = StdioServerParameters(
                    command='python',
                    args=['marcus_mcp_server.py'],
                    env=env
                )
                
                async with stdio_client(server_params2) as (read2, write2):
                    async with ClientSession(read2, write2) as session2:
                        await session2.initialize()
                        
                        # Register second worker
                        result = await session2.call_tool(
                            'register_agent',
                            {
                                'agent_id': 'worker-2',
                                'name': 'Worker 2',
                                'role': 'Developer',
                                'skills': ['python', 'development']
                            }
                        )
                        
                        # Request a task
                        result = await session2.call_tool(
                            'request_next_task',
                            {'agent_id': 'worker-2'}
                        )
                        
                        task2_data = json.loads(result.content[0].text)
                        
                        if task2_data.get('success') and task2_data.get('task'):
                            task2_id = task2_data['task']['id']
                            # This should FAIL if duplicate assignment still exists
                            assert task2_id != task1_id, \
                                f"Worker 2 got same task as Worker 1: {task2_id}"
                        
            finally:
                # Clean up
                marcus_process.terminate()
                marcus_process.wait()


import os
if __name__ == "__main__":
    pytest.main([__file__, "-v"])