#!/usr/bin/env python3
"""
Trace exactly when and why NetworkX gets imported during complex project creation
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Track NetworkX usage
networkx_calls = []

def trace_networkx():
    """Hook into NetworkX to see when it's used"""
    try:
        import networkx as nx
        original_graph_init = nx.Graph.__init__
        original_digraph_init = nx.DiGraph.__init__
        original_multidigraph_init = nx.MultiDiGraph.__init__
        
        def trace_graph_init(self, *args, **kwargs):
            import inspect
            frame = inspect.currentframe()
            stack = inspect.getouterframes(frame)
            
            caller_info = []
            for frame_info in stack[1:6]:  # Get 5 levels of call stack
                caller_info.append(f"{frame_info.filename}:{frame_info.lineno} in {frame_info.function}")
            
            networkx_calls.append({
                'type': 'Graph.__init__',
                'stack': caller_info,
                'timestamp': str(sys._getframe().f_locals.get('datetime', 'unknown'))
            })
            
            print(f"NetworkX Graph created! Call stack:")
            for i, caller in enumerate(caller_info):
                print(f"  {i}: {caller}")
            print("-" * 80)
            
            return original_graph_init(self, *args, **kwargs)
        
        def trace_digraph_init(self, *args, **kwargs):
            import inspect
            frame = inspect.currentframe()
            stack = inspect.getouterframes(frame)
            
            caller_info = []
            for frame_info in stack[1:6]:
                caller_info.append(f"{frame_info.filename}:{frame_info.lineno} in {frame_info.function}")
            
            networkx_calls.append({
                'type': 'DiGraph.__init__',
                'stack': caller_info
            })
            
            print(f"NetworkX DiGraph created! Call stack:")
            for i, caller in enumerate(caller_info):
                print(f"  {i}: {caller}")
            print("-" * 80)
            
            return original_digraph_init(self, *args, **kwargs)
        
        def trace_multidigraph_init(self, *args, **kwargs):
            import inspect
            frame = inspect.currentframe()
            stack = inspect.getouterframes(frame)
            
            caller_info = []
            for frame_info in stack[1:6]:
                caller_info.append(f"{frame_info.filename}:{frame_info.lineno} in {frame_info.function}")
            
            networkx_calls.append({
                'type': 'MultiDiGraph.__init__',
                'stack': caller_info
            })
            
            print(f"NetworkX MultiDiGraph created! Call stack:")
            for i, caller in enumerate(caller_info):
                print(f"  {i}: {caller}")
            print("-" * 80)
            
            return original_multidigraph_init(self, *args, **kwargs)
        
        # Monkey patch the constructors
        nx.Graph.__init__ = trace_graph_init
        nx.DiGraph.__init__ = trace_digraph_init
        nx.MultiDiGraph.__init__ = trace_multidigraph_init
        
        print("NetworkX tracing enabled")
        
    except ImportError:
        print("NetworkX not available for tracing")


async def test_with_networkx_tracing():
    """Test complex project creation with NetworkX tracing"""
    
    # Set up tracing before importing Marcus modules
    trace_networkx()
    
    from src.marcus_mcp.server import MarcusServer
    from src.marcus_mcp.handlers import handle_tool_call
    
    print("Initializing Marcus server...")
    server = MarcusServer()
    
    # Initialize kanban
    await server.initialize_kanban()
    
    print("\nCreating complex project to trigger NetworkX usage...")
    
    try:
        result = await handle_tool_call(
            'create_project',
            {
                'project_name': 'NetworkX Trace Test',
                'description': '''Build a comprehensive application with multiple components:
                - User authentication system
                - Data processing pipeline
                - Real-time dashboard
                - API gateway
                - Microservices architecture
                - Database optimization
                - Caching layer
                - Monitoring and logging
                - CI/CD pipeline
                - Load balancing
                - Security features
                - Performance optimization''',
                'options': {
                    'team_size': 6,
                    'tech_stack': ['Python', 'React', 'PostgreSQL', 'Redis', 'Docker', 'Kubernetes'],
                    'deadline': '2025-12-31'
                }
            },
            server
        )
        
        print(f"\nTotal NetworkX graph creations: {len(networkx_calls)}")
        
        if networkx_calls:
            print("\nNetworkX usage summary:")
            for i, call in enumerate(networkx_calls):
                print(f"Call {i+1}: {call['type']}")
                print(f"  Top caller: {call['stack'][0] if call['stack'] else 'Unknown'}")
                print()
        
        print("\nResult:")
        import json
        print(json.dumps(json.loads(result[0].text), indent=2))
        
    except Exception as e:
        print(f"\nError occurred after {len(networkx_calls)} NetworkX graph creations")
        print(f"Exception: {type(e).__name__}: {e}")
        
        if networkx_calls:
            print(f"\nLast NetworkX call before error:")
            last_call = networkx_calls[-1]
            print(f"Type: {last_call['type']}")
            for caller in last_call['stack']:
                print(f"  {caller}")


if __name__ == "__main__":
    try:
        asyncio.run(test_with_networkx_tracing())
    except Exception as e:
        print(f"\nOuter error: {type(e).__name__}: {e}")
        traceback.print_exc()