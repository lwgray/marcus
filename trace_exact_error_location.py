#!/usr/bin/env python3
"""
Trace the exact location where the dictionary iteration error originates
"""

import asyncio
import sys
import traceback
import threading
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Monkey patch dict.__iter__ to catch the exact error
original_dict_iter = dict.__iter__

def debug_dict_iter(self):
    """Debug version of dict.__iter__ that catches size changes"""
    try:
        # Get current thread info
        thread_info = f"Thread-{threading.current_thread().ident}"
        
        # Store original size
        original_size = len(self)
        
        # Create iterator
        iterator = original_dict_iter(self)
        
        # Check if size changed
        current_size = len(self)
        if current_size != original_size:
            print(f"[{thread_info}] WARNING: Dict size changed during iterator creation!")
            print(f"  Original size: {original_size}, Current size: {current_size}")
            
            # Get stack trace
            stack = traceback.format_stack()
            print("  Stack trace:")
            for i, frame in enumerate(stack[-8:]):  # Show last 8 frames
                print(f"    {i}: {frame.strip()}")
        
        return iterator
        
    except RuntimeError as e:
        if "dictionary changed size during iteration" in str(e):
            print(f"\n{'='*80}")
            print(f"FOUND THE ERROR! Thread: {thread_info}")
            print(f"Dictionary size: {len(self)}")
            print(f"Dictionary type: {type(self)}")
            print(f"Error: {e}")
            
            # Print full stack trace
            print("\nFULL STACK TRACE:")
            traceback.print_exc()
            
            print(f"{'='*80}\n")
            
        raise

# Apply the monkey patch
dict.__iter__ = debug_dict_iter

from src.marcus_mcp.server import MarcusServer
from src.marcus_mcp.handlers import handle_tool_call


async def test_error_tracing():
    """Test complex project creation with detailed error tracing"""
    print("Initializing Marcus server with dict iteration debugging...")
    server = MarcusServer()
    
    # Initialize kanban
    await server.initialize_kanban()
    
    print("\nCreating complex project to trigger the error...")
    
    try:
        result = await handle_tool_call(
            'create_project',
            {
                'project_name': 'Error Trace Test',
                'description': '''Build a comprehensive e-commerce platform with advanced features:
                - Multi-tenant architecture with tenant isolation
                - Advanced user management with roles and permissions
                - Product catalog with complex categorization and filtering
                - Advanced search with Elasticsearch integration
                - Shopping cart with complex pricing rules and discounts
                - Multi-step checkout process with payment gateway integration
                - Order management system with complex workflow states
                - Inventory management with real-time tracking
                - Advanced reporting and analytics dashboard
                - Email marketing automation with campaign management
                - Customer support ticket system with escalation rules
                - API gateway with rate limiting and authentication
                - Microservices communication with message queues
                - Real-time notifications with WebSocket connections
                - File upload and management system
                - Advanced caching strategies with Redis
                - Database optimization with read replicas
                - CI/CD pipeline with automated testing and deployment
                - Monitoring and logging with alerting systems
                - Security features including audit trails and encryption''',
                'options': {
                    'team_size': 8,
                    'tech_stack': ['Python', 'React', 'PostgreSQL', 'Redis', 'Docker', 'Kubernetes', 'Elasticsearch'],
                    'deadline': '2025-12-31'
                }
            },
            server
        )
        
        print("\nSUCCESS! No error occurred")
        import json
        print(json.dumps(json.loads(result[0].text), indent=2))
        
    except Exception as e:
        print(f"\nERROR CAUGHT: {type(e).__name__}: {e}")
        print("\nThis should have been caught by our debug wrapper above.")


if __name__ == "__main__":
    try:
        asyncio.run(test_error_tracing())
    except Exception as e:
        print(f"\nOuter error: {type(e).__name__}: {e}")
        traceback.print_exc()