#!/usr/bin/env python3
"""
Wrapper script for PM Agent MCP Server to ensure clean initialization
"""

import os
import sys
import subprocess
from pathlib import Path

# Ensure we're in the correct directory
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)

# Clean environment - remove any proxy-related vars that might interfere
env = os.environ.copy()
proxy_vars = [k for k in env.keys() if 'proxy' in k.lower() or 'PROXY' in k]
for var in proxy_vars:
    if var in env:
        del env[var]

# Run the MCP server
try:
    subprocess.run(
        [sys.executable, "pm_agent_mcp_server_v2.py"],
        env=env,
        check=True
    )
except KeyboardInterrupt:
    print("\nServer stopped by user")
except Exception as e:
    print(f"Error running server: {e}")
    sys.exit(1)