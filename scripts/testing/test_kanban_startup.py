#!/usr/bin/env python3
"""Test kanban-mcp startup directly"""

import subprocess
import threading
import time
import os

def capture_output(stream, label):
    """Capture output from a stream"""
    for line in iter(stream.readline, ''):
        if line:
            print(f"[{label}] {line.strip()}")

def test_kanban_startup():
    """Test starting kanban-mcp and capture all output"""
    print("🔍 Testing kanban-mcp startup")
    print("-" * 50)
    
    env = os.environ.copy()
    env.update({
        "PLANKA_BASE_URL": "http://localhost:3333",
        "PLANKA_AGENT_EMAIL": "demo@demo.demo",
        "PLANKA_AGENT_PASSWORD": "demo",
        "PLANKA_ADMIN_EMAIL": "demo@demo.demo",
        "DEBUG": "*"  # Enable debug logging if supported
    })
    
    cmd = ["/opt/homebrew/bin/node", "../kanban-mcp/dist/index.js"]
    
    print(f"Command: {' '.join(cmd)}")
    print(f"Environment includes: PLANKA_BASE_URL, PLANKA_AGENT_EMAIL, etc.")
    print("\nStarting process...")
    print("-" * 50)
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        bufsize=1
    )
    
    # Start threads to capture output
    stdout_thread = threading.Thread(target=capture_output, args=(proc.stdout, "STDOUT"))
    stderr_thread = threading.Thread(target=capture_output, args=(proc.stderr, "STDERR"))
    
    stdout_thread.daemon = True
    stderr_thread.daemon = True
    
    stdout_thread.start()
    stderr_thread.start()
    
    # Give it some time to start up
    print("\nWaiting for startup messages...")
    time.sleep(3)
    
    # Check if process is still running
    if proc.poll() is None:
        print("\n✅ Process is still running (PID: {})".format(proc.pid))
        
        # Try sending a simple JSON-RPC message
        print("\nSending test message...")
        test_msg = '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"1.0.0","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}\n'
        proc.stdin.write(test_msg)
        proc.stdin.flush()
        
        # Wait for response
        time.sleep(2)
        
    else:
        print(f"\n❌ Process exited with code: {proc.poll()}")
    
    # Clean up
    print("\nTerminating process...")
    proc.terminate()
    proc.wait()
    
    print("\nDone!")

if __name__ == "__main__":
    test_kanban_startup()