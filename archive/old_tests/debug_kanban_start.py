#!/usr/bin/env python3
"""
Debug kanban-mcp startup issues
"""

import subprocess
import os
import sys
import time

print("🔍 Debugging kanban-mcp startup...")
print("=" * 60)

# Check environment
env = os.environ.copy()
env.update({
    'PLANKA_BASE_URL': 'http://localhost:3333',
    'PLANKA_AGENT_EMAIL': 'demo@demo.demo',
    'PLANKA_AGENT_PASSWORD': 'demo',
    'DEBUG': 'true',
    'NODE_ENV': 'development'
})

print("\n1. Environment variables:")
for key in ['PLANKA_BASE_URL', 'PLANKA_AGENT_EMAIL', 'PLANKA_AGENT_PASSWORD']:
    print(f"   {key}: {env.get(key)}")

# Check Node.js
print("\n2. Node.js version:")
try:
    result = subprocess.run(['node', '--version'], capture_output=True, text=True)
    print(f"   {result.stdout.strip()}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check if Planka is accessible
print("\n3. Checking Planka connection:")
try:
    import requests
    response = requests.get(env['PLANKA_BASE_URL'], timeout=2)
    print(f"   ✅ Planka is accessible (status: {response.status_code})")
except Exception as e:
    print(f"   ❌ Cannot reach Planka: {e}")

# Try to start kanban-mcp with immediate output
print("\n4. Starting kanban-mcp (will show output for 5 seconds)...")
print("-" * 60)

kanban_path = os.path.abspath("../kanban-mcp")
cmd = ['node', 'dist/index.js']

try:
    # Start process
    process = subprocess.Popen(
        cmd,
        cwd=kanban_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Read output for 5 seconds
    start_time = time.time()
    while time.time() - start_time < 5:
        line = process.stdout.readline()
        if line:
            print(f"OUTPUT: {line.strip()}")
        if process.poll() is not None:
            print(f"\nProcess exited with code: {process.returncode}")
            break
        time.sleep(0.1)
    
    # Check if still running
    if process.poll() is None:
        print("\n✅ Process is still running after 5 seconds")
        print("Terminating test process...")
        process.terminate()
        process.wait()
    
except Exception as e:
    print(f"\n❌ Error starting kanban-mcp: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Debug complete. Check output above for issues.")