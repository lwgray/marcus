#!/usr/bin/env python3
"""
Test PM Agent as an MCP server directly
This helps debug startup issues
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set environment variables
os.environ['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

# Import and run
try:
    print("Starting PM Agent test...", file=sys.stderr)
    from src.pm_agent_mvp_fixed import PMAgentMVP
    import asyncio
    
    async def test():
        agent = PMAgentMVP()
        await agent.initialize()
        
        # Run as stdio server
        from mcp.server.stdio import stdio_server
        async with stdio_server() as (read_stream, write_stream):
            await agent.server.run(
                read_stream,
                write_stream,
                agent.server.create_initialization_options()
            )
    
    asyncio.run(test())
    
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)