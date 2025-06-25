#!/usr/bin/env python3
"""Debug MCP initialization issue"""

import os
import sys
import inspect
from pathlib import Path

# Add to path
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

print("Debug: Checking anthropic module before any imports...")
import anthropic
print(f"Anthropic version: {anthropic.__version__}")
print(f"Init signature: {list(inspect.signature(anthropic.Anthropic.__init__).parameters.keys())}")

print("\nDebug: Checking for MCP interference...")
try:
    from mcp.server import Server
    print("MCP Server imported successfully")
    
    # Check if MCP modifies anything
    print(f"Anthropic init after MCP import: {list(inspect.signature(anthropic.Anthropic.__init__).parameters.keys())}")
    
except Exception as e:
    print(f"MCP import error: {e}")

print("\nDebug: Testing initialization with explicit parameters...")
try:
    # Test with no proxies
    client1 = anthropic.Anthropic(api_key="test")
    print("✅ Init with api_key only: SUCCESS")
except Exception as e:
    print(f"❌ Init with api_key only: {e}")

try:
    # Test with None proxies
    client2 = anthropic.Anthropic(api_key="test", proxies=None)
    print("✅ Init with proxies=None: SUCCESS")
except Exception as e:
    print(f"❌ Init with proxies=None: {e}")

print("\nDebug: Checking sys.modules for modifications...")
anthropic_modules = [m for m in sys.modules.keys() if 'anthropic' in m]
print(f"Anthropic-related modules: {anthropic_modules}")

# Now test the actual initialization
print("\nDebug: Testing PMAgentState initialization...")
from dotenv import load_dotenv
load_dotenv()

try:
    from pm_agent_mcp_server_v2 import PMAgentState
    state = PMAgentState()
    print("✅ PMAgentState initialized successfully")
except Exception as e:
    print(f"❌ PMAgentState initialization failed: {e}")
    import traceback
    traceback.print_exc()