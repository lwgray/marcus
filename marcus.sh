#!/bin/bash

# Marcus MCP Server Management Script
# Usage: ./marcus.sh [start|stop|restart|add|status]

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVER_SCRIPT="$SCRIPT_DIR/marcus_mcp_server.py"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/pids"

# Create directories if they don't exist
mkdir -p "$LOG_DIR" "$PID_DIR"

# Function to start a server instance
start_server() {
    local instance_id=$1
    local log_file="$LOG_DIR/marcus_server_${instance_id}.log"
    local pid_file="$PID_DIR/marcus_server_${instance_id}.pid"
    
    echo "Starting Marcus MCP Server instance $instance_id..."
    nohup python "$SERVER_SCRIPT" > "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"
    echo "Started instance $instance_id with PID: $pid"
}

# Function to get next available instance ID
get_next_instance_id() {
    local max_id=0
    for pid_file in "$PID_DIR"/marcus_server_*.pid; do
        if [ -f "$pid_file" ]; then
            # Extract instance ID from filename
            local id=$(basename "$pid_file" | sed 's/marcus_server_\([0-9]*\)\.pid/\1/')
            if [ "$id" -gt "$max_id" ]; then
                max_id=$id
            fi
        fi
    done
    echo $((max_id + 1))
}

# Function to check if a PID is running
is_running() {
    local pid=$1
    kill -0 "$pid" 2>/dev/null
}

# Function to clean up stale PID files
cleanup_pids() {
    for pid_file in "$PID_DIR"/marcus_server_*.pid; do
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if ! is_running "$pid"; then
                echo "Removing stale PID file: $pid_file"
                rm "$pid_file"
            fi
        fi
    done
}

case "$1" in
    start)
        cleanup_pids
        if ls "$PID_DIR"/marcus_server_*.pid 1> /dev/null 2>&1; then
            echo "Marcus MCP Server instances are already running:"
            for pid_file in "$PID_DIR"/marcus_server_*.pid; do
                pid=$(cat "$pid_file")
                instance_id=$(basename "$pid_file" | sed 's/marcus_server_\([0-9]*\)\.pid/\1/')
                echo "  Instance $instance_id: PID $pid"
            done
            echo "Use './marcus.sh stop' to stop them first, or './marcus.sh add' to add another instance."
        else
            start_server 1
        fi
        ;;
        
    stop)
        echo "Stopping all Marcus MCP Server instances..."
        # Kill using pkill first
        pkill -f marcus_mcp_server.py
        
        # Also kill any PIDs we have recorded
        for pid_file in "$PID_DIR"/marcus_server_*.pid; do
            if [ -f "$pid_file" ]; then
                pid=$(cat "$pid_file")
                if is_running "$pid"; then
                    kill "$pid" 2>/dev/null
                    echo "Stopped PID: $pid"
                fi
                rm "$pid_file"
            fi
        done
        
        # Double-check with a more aggressive kill
        sleep 1
        pkill -9 -f marcus_mcp_server.py 2>/dev/null
        
        echo "All Marcus MCP Server instances stopped."
        ;;
        
    restart)
        "$0" stop
        sleep 2
        "$0" start
        ;;
        
    add)
        cleanup_pids
        next_id=$(get_next_instance_id)
        start_server "$next_id"
        ;;
        
    status)
        cleanup_pids
        echo "Marcus MCP Server Status:"
        echo "========================"
        
        # Check for running processes
        running_count=$(pgrep -f marcus_mcp_server.py | wc -l | tr -d ' ')
        echo "Running processes: $running_count"
        
        # List tracked instances
        if ls "$PID_DIR"/marcus_server_*.pid 1> /dev/null 2>&1; then
            echo -e "\nTracked instances:"
            for pid_file in "$PID_DIR"/marcus_server_*.pid; do
                pid=$(cat "$pid_file")
                instance_id=$(basename "$pid_file" | sed 's/marcus_server_\([0-9]*\)\.pid/\1/')
                if is_running "$pid"; then
                    echo "  Instance $instance_id: PID $pid (running)"
                else
                    echo "  Instance $instance_id: PID $pid (not running)"
                fi
            done
        else
            echo -e "\nNo tracked instances."
        fi
        
        # Show actual running processes
        echo -e "\nActual running processes:"
        ps aux | grep marcus_mcp_server.py | grep -v grep || echo "  None found"
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|add|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start a Marcus MCP Server instance (if none running)"
        echo "  stop    - Stop all Marcus MCP Server instances"
        echo "  restart - Stop all instances and start a fresh one"
        echo "  add     - Add another Marcus MCP Server instance"
        echo "  status  - Show status of all instances"
        exit 1
        ;;
esac

exit 0