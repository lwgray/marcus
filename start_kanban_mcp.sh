#!/bin/bash

# Set environment variables
export PLANKA_BASE_URL=http://localhost:3333
export PLANKA_AGENT_EMAIL=demo@demo.demo
export PLANKA_AGENT_PASSWORD=demo

# Start kanban-mcp server
echo "Starting kanban-mcp server..."
cd ../kanban-mcp && node dist/index.js