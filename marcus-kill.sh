#!/bin/bash
# Kill all Marcus processes

echo "🛑 Stopping all Marcus processes..."

# Kill Marcus Python processes
pkill -f "python.*marcus" 2>/dev/null
pkill -f "python.*src.api.app" 2>/dev/null
pkill -f "python.*src.marcus_mcp" 2>/dev/null

# Kill any marcus shell scripts
pkill -f "bash.*marcus" 2>/dev/null

# Wait a moment for processes to terminate
sleep 1

# Check if any processes are still running
if pgrep -f "python.*marcus" > /dev/null; then
    echo "⚠️  Some Marcus processes still running, force killing..."
    pkill -9 -f "python.*marcus" 2>/dev/null
fi

echo "✅ All Marcus processes stopped"