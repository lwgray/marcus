#!/bin/bash
# Start kanban-mcp server

KANBAN_PATH="../kanban-mcp"

# Check if kanban-mcp exists
if [ ! -f "$KANBAN_PATH/dist/index.js" ]; then
    echo "❌ kanban-mcp not found at $KANBAN_PATH"
    exit 1
fi

# Set environment
export PLANKA_BASE_URL="http://localhost:3333"
export PLANKA_AGENT_EMAIL="demo@demo.demo"
export PLANKA_AGENT_PASSWORD="demo"

echo "🚀 Starting kanban-mcp server..."
echo "  📁 Path: $KANBAN_PATH"
echo "  🔧 Planka: $PLANKA_BASE_URL"

# Start the server
node "$KANBAN_PATH/dist/index.js"