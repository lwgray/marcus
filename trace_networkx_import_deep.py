#!/usr/bin/env python3
"""
Deep trace of NetworkX imports and usage
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Track all NetworkX related activity
networkx_activity = []

def hook_networkx_imports():
    """Hook into import system to catch NetworkX imports"""
    import builtins
    original_import = builtins.__import__
    
    def trace_import(name, *args, **kwargs):
        if 'networkx' in name.lower():
            import inspect
            frame = inspect.currentframe()
            stack = inspect.getouterframes(frame)
            
            caller_info = []
            for frame_info in stack[1:8]:  # Get more levels
                if 'importlib' not in frame_info.filename:  # Skip importlib internals
                    caller_info.append(f"{frame_info.filename}:{frame_info.lineno} in {frame_info.function}")
            
            networkx_activity.append({
                'type': 'IMPORT',
                'module': name,
                'stack': caller_info
            })
            
            print(f"IMPORTING NetworkX module: {name}")
            for i, caller in enumerate(caller_info[:5]):  # Show top 5
                print(f"  {i}: {caller}")
            print("-" * 60)
        
        return original_import(name, *args, **kwargs)
    
    builtins.__import__ = trace_import


def hook_networkx_usage():
    """Hook into NetworkX functions that might use configs"""
    try:
        # Import networkx first to set up hooks
        import networkx as nx
        
        # Hook into various NetworkX functions that might access configs
        if hasattr(nx, 'config'):
            original_config = nx.config
            
            def trace_config(*args, **kwargs):
                import inspect
                frame = inspect.currentframe()
                stack = inspect.getouterframes(frame)
                
                caller_info = []
                for frame_info in stack[1:5]:
                    caller_info.append(f"{frame_info.filename}:{frame_info.lineno} in {frame_info.function}")
                
                networkx_activity.append({
                    'type': 'CONFIG_ACCESS',
                    'stack': caller_info
                })
                
                print(f"NetworkX config accessed!")
                for i, caller in enumerate(caller_info):
                    print(f"  {i}: {caller}")
                print("-" * 60)
                
                return original_config(*args, **kwargs)
            
            nx.config = trace_config
        
        print("NetworkX usage hooks installed")
        
    except ImportError:
        print("NetworkX not available for usage tracing")


async def test_with_deep_tracing():
    """Test with comprehensive NetworkX tracing"""
    
    # Set up hooks before any imports
    hook_networkx_imports()
    
    from src.marcus_mcp.server import MarcusServer
    from src.marcus_mcp.handlers import handle_tool_call
    
    # Set up usage hooks after imports
    hook_networkx_usage()
    
    print("Starting complex project creation with deep NetworkX tracing...")
    
    server = MarcusServer()
    await server.initialize_kanban()
    
    try:
        result = await handle_tool_call(
            'create_project',
            {
                'project_name': 'Deep Trace Test',
                'description': '''Complex enterprise application with:
                - Microservices architecture
                - Event-driven design
                - CQRS pattern implementation
                - Distributed caching
                - Message queues
                - Service mesh
                - Container orchestration
                - Database sharding
                - Real-time analytics
                - Machine learning pipeline
                - API gateway
                - Security framework''',
                'options': {
                    'team_size': 8,
                    'tech_stack': ['Python', 'Java', 'React', 'PostgreSQL', 'Redis', 'Kafka', 'Docker'],
                }
            },
            server
        )
        
        print(f"\nTotal NetworkX activities: {len(networkx_activity)}")
        
        if networkx_activity:
            print("\nNetworkX activity summary:")
            for i, activity in enumerate(networkx_activity):
                print(f"{i+1}. {activity['type']}: {activity.get('module', 'N/A')}")
                if activity['stack']:
                    print(f"   Called from: {activity['stack'][0]}")
                print()
        
        print("Result:")
        import json
        print(json.dumps(json.loads(result[0].text), indent=2))
        
    except Exception as e:
        print(f"\nError after {len(networkx_activity)} NetworkX activities")
        print(f"Exception: {type(e).__name__}: {e}")
        
        if networkx_activity:
            print(f"\nLast NetworkX activity before error:")
            last_activity = networkx_activity[-1]
            print(f"Type: {last_activity['type']}")
            print(f"Module: {last_activity.get('module', 'N/A')}")
            if last_activity['stack']:
                print("Call stack:")
                for caller in last_activity['stack']:
                    print(f"  {caller}")


if __name__ == "__main__":
    try:
        asyncio.run(test_with_deep_tracing())
    except Exception as e:
        print(f"\nOuter error: {type(e).__name__}: {e}")
        traceback.print_exc()