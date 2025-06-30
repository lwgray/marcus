#!/usr/bin/env python3
"""
Trace the runtime error using exception handling
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up detailed exception hook
def detailed_exception_handler(exc_type, exc_value, exc_traceback):
    """Handle exceptions with detailed information"""
    if exc_type == RuntimeError and "dictionary changed size during iteration" in str(exc_value):
        print(f"\n{'='*80}")
        print("DICTIONARY ITERATION ERROR CAUGHT!")
        print(f"Error: {exc_value}")
        print(f"{'='*80}")
        
        print("\nDETAILED TRACEBACK:")
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        
        print(f"\n{'='*80}")
        print("STACK FRAMES ANALYSIS:")
        
        tb = exc_traceback
        frame_count = 0
        while tb:
            frame = tb.tb_frame
            frame_count += 1
            filename = frame.f_code.co_filename
            line_number = tb.tb_lineno
            function_name = frame.f_code.co_name
            
            print(f"\nFrame {frame_count}:")
            print(f"  File: {filename}")
            print(f"  Line: {line_number}")
            print(f"  Function: {function_name}")
            
            # Show local variables that might be dictionaries
            local_vars = frame.f_locals
            dict_vars = {}
            for var_name, var_value in local_vars.items():
                if isinstance(var_value, dict) and len(var_value) > 0:
                    dict_vars[var_name] = len(var_value)
            
            if dict_vars:
                print(f"  Dict variables: {dict_vars}")
            
            tb = tb.tb_next
        
        print(f"{'='*80}\n")
    else:
        # Use default handler for other exceptions
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

# Install our exception handler
sys.excepthook = detailed_exception_handler

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def test_with_exception_tracing():
    """Test with detailed exception tracing"""
    print("Starting Marcus with detailed exception tracing...")
    
    server = MarcusServer()
    await server.initialize_kanban()
    
    print("\nCreating complex project...")
    
    # This should trigger the error and our detailed handler
    result = await handle_tool_call(
        'create_project',
        {
            'project_name': 'Runtime Error Trace',
            'description': '''Complex enterprise application with multiple components:
            - Microservices architecture with service mesh
            - Event-driven design with message brokers
            - CQRS and event sourcing patterns
            - Distributed caching with Redis cluster
            - Advanced authentication and authorization
            - Real-time data processing pipeline
            - Machine learning model deployment
            - Comprehensive monitoring and observability
            - Multi-region deployment with disaster recovery
            - Advanced security and compliance features''',
            'options': {
                'team_size': 10,
                'tech_stack': ['Python', 'Go', 'React', 'PostgreSQL', 'Redis', 'Kafka'],
            }
        },
        server
    )
    
    print("Success! No error occurred.")
    import json
    print(json.dumps(json.loads(result[0].text), indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(test_with_exception_tracing())
    except Exception as e:
        print(f"\nUnhandled error: {type(e).__name__}: {e}")
        traceback.print_exc()