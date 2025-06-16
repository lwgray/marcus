#!/usr/bin/env python3
"""
Improved Kanban MCP Server Manager
"""

import os
import sys
import subprocess
import signal
import time
import json
from pathlib import Path

# Configuration
KANBAN_MCP_PATH = "/Users/lwgray/dev/kanban-mcp"
PID_FILE = Path.home() / ".kanban-mcp.pid"
LOG_FILE = Path.home() / ".kanban-mcp.log"

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def find_kanban_process():
    """Find running kanban-mcp process"""
    try:
        result = subprocess.run(
            ['ps', 'aux'], 
            capture_output=True, 
            text=True
        )
        
        for line in result.stdout.split('\n'):
            if '/kanban-mcp/dist/index.js' in line and 'node' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) > 1:
                    return int(parts[1])  # PID is second column
    except:
        pass
    return None


def start_server():
    """Start the kanban-mcp server"""
    print(f"{BLUE}🚀 Starting kanban-mcp server...{RESET}")
    
    # Check if already running
    existing_pid = find_kanban_process()
    if existing_pid:
        print(f"{YELLOW}⚠️  kanban-mcp is already running (PID: {existing_pid}){RESET}")
        PID_FILE.write_text(str(existing_pid))
        return
    
    # Check if kanban-mcp exists
    index_path = Path(KANBAN_MCP_PATH) / "dist" / "index.js"
    if not index_path.exists():
        print(f"{RED}❌ kanban-mcp not found at {index_path}{RESET}")
        print(f"Please ensure kanban-mcp is installed at: {KANBAN_MCP_PATH}")
        sys.exit(1)
    
    # Start the process
    try:
        env = os.environ.copy()
        env.update({
            'PLANKA_BASE_URL': 'http://localhost:3333',
            'PLANKA_AGENT_EMAIL': 'demo@demo.demo',
            'PLANKA_AGENT_PASSWORD': 'demo'
        })
        
        # Use shell=True for better compatibility
        cmd = f"cd {KANBAN_MCP_PATH} && node dist/index.js"
        
        with open(LOG_FILE, 'w') as log:
            process = subprocess.Popen(
                cmd,
                shell=True,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if sys.platform != 'win32' else None
            )
        
        time.sleep(3)  # Give it more time to start
        
        # Find the actual node process
        actual_pid = find_kanban_process()
        if actual_pid:
            PID_FILE.write_text(str(actual_pid))
            print(f"{GREEN}✅ kanban-mcp started successfully (PID: {actual_pid}){RESET}")
            print(f"  📄 Log file: {LOG_FILE}")
            print(f"  🔧 Planka URL: {env['PLANKA_BASE_URL']}")
            
            # Show first few lines of log
            with open(LOG_FILE, 'r') as log:
                lines = log.readlines()[:3]
                if lines:
                    print(f"\n{BLUE}Log output:{RESET}")
                    for line in lines:
                        print(f"  {line.strip()}")
        else:
            print(f"{RED}❌ Failed to start kanban-mcp{RESET}")
            with open(LOG_FILE, 'r') as log:
                print(f"\nError output:\n{log.read()}")
            
    except Exception as e:
        print(f"{RED}❌ Error starting kanban-mcp: {e}{RESET}")
        sys.exit(1)


def stop_server():
    """Stop the kanban-mcp server"""
    print(f"{BLUE}🛑 Stopping kanban-mcp server...{RESET}")
    
    # Try to find running process
    pid = None
    
    # First check PID file
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
        except:
            pass
    
    # If not found, search for it
    if not pid:
        pid = find_kanban_process()
    
    if not pid:
        print(f"{YELLOW}⚠️  kanban-mcp is not running{RESET}")
        PID_FILE.unlink(missing_ok=True)
        return
    
    try:
        # Try graceful shutdown first
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        
        # Check if still running
        try:
            os.kill(pid, 0)  # Check if process exists
            # Force kill if still running
            os.kill(pid, signal.SIGKILL)
            print(f"{YELLOW}⚠️  Had to force kill the process{RESET}")
        except ProcessLookupError:
            pass  # Process already terminated
        
        print(f"{GREEN}✅ kanban-mcp stopped successfully{RESET}")
        
    except ProcessLookupError:
        print(f"{YELLOW}⚠️  Process already terminated{RESET}")
    except Exception as e:
        print(f"{RED}❌ Error stopping kanban-mcp: {e}{RESET}")
    finally:
        PID_FILE.unlink(missing_ok=True)


def server_status():
    """Check the status of kanban-mcp server"""
    print(f"{BLUE}📊 kanban-mcp Status{RESET}")
    print("=" * 40)
    
    pid = find_kanban_process()
    
    if pid:
        print(f"{GREEN}✅ kanban-mcp is running{RESET}")
        print(f"  PID: {pid}")
        
        # Update PID file
        PID_FILE.write_text(str(pid))
        
        # Show process info
        try:
            result = subprocess.run(
                ['ps', '-p', str(pid), '-o', 'pid,ppid,user,comm,etime'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    print(f"  Process: {lines[1]}")
        except:
            pass
        
        # Show recent logs
        if LOG_FILE.exists():
            print(f"\n{BLUE}Recent log entries:{RESET}")
            try:
                with open(LOG_FILE, 'r') as log:
                    lines = log.readlines()
                    for line in lines[-5:]:
                        print(f"  {line.strip()}")
            except:
                print("  (Unable to read log file)")
    else:
        print(f"{RED}❌ kanban-mcp is not running{RESET}")
        PID_FILE.unlink(missing_ok=True)


def show_logs():
    """Show the kanban-mcp logs"""
    if not LOG_FILE.exists():
        print(f"{YELLOW}⚠️  No log file found{RESET}")
        return
    
    print(f"{BLUE}📜 kanban-mcp Logs (Press Ctrl+C to stop){RESET}")
    print("=" * 40)
    
    try:
        # Try using tail -f
        subprocess.run(['tail', '-f', str(LOG_FILE)])
    except KeyboardInterrupt:
        print(f"\n{BLUE}👋 Stopped watching logs{RESET}")
    except:
        # Fallback: print the whole file
        with open(LOG_FILE, 'r') as log:
            print(log.read())


def main():
    """Main entry point"""
    commands = {
        'start': start_server,
        'stop': stop_server,
        'status': server_status,
        'restart': lambda: (stop_server(), time.sleep(1), start_server()),
        'logs': show_logs
    }
    
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(f"{BLUE}Kanban MCP Server Manager{RESET}")
        print("\nUsage: ./kanban-manager.py <command>")
        print("\nCommands:")
        print("  start    - Start the kanban-mcp server")
        print("  stop     - Stop the kanban-mcp server")
        print("  status   - Check server status")
        print("  restart  - Restart the server")
        print("  logs     - Show server logs (live)")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        commands[command]()
    except KeyboardInterrupt:
        print(f"\n{BLUE}👋 Interrupted{RESET}")


if __name__ == "__main__":
    main()