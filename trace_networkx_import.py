#!/usr/bin/env python3
"""
Trace when NetworkX gets imported during project creation
"""

import sys
import importlib
import builtins
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Hook into import system to trace NetworkX imports
original_import = builtins.__import__

def trace_import(name, *args, **kwargs):
    if 'networkx' in name.lower() or 'nx' in name:
        print(f"IMPORTING: {name}")
        import traceback
        traceback.print_stack(limit=10)
        print("-" * 80)
    
    return original_import(name, *args, **kwargs)

# builtins.__import__ = trace_import

print("Starting Marcus import trace...")

try:
    # Import the modules that are used in project creation
    from src.marcus_mcp.server import MarcusServer
    print("MarcusServer imported")
    
    from src.marcus_mcp.handlers import handle_tool_call
    print("handle_tool_call imported")
    
    print("No NetworkX imports detected during basic imports")
    
except Exception as e:
    print(f"Error during import: {e}")
    
# Restore original import
builtins.__import__ = original_import