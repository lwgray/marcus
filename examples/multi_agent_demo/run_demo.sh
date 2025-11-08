#!/bin/bash
#
# Marcus Multi-Agent Demo Launcher
#
# This script launches the autonomous multi-agent demo.
#

set -e

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================================================"
echo "Marcus Multi-Agent Demo"
echo "======================================================================"
echo ""
echo "This demo will spawn 5 autonomous processes:"
echo "  - 1 project creator"
echo "  - 4 worker agents (each with 5 subagents = 20 total)"
echo ""
echo "All agents will work autonomously using Claude Code with"
echo "--dangerously-skip-permissions"
echo ""
echo "======================================================================"
echo ""

# Check for required dependencies
if ! command -v claude &> /dev/null; then
    echo "❌ Error: 'claude' command not found"
    echo ""
    echo "Please install Claude Code:"
    echo "  https://docs.claude.com/en/docs/claude-code"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    exit 1
fi

echo "✓ Dependencies found"
echo ""

# Create necessary directories
mkdir -p "$DEMO_DIR/logs"
mkdir -p "$DEMO_DIR/prompts"
mkdir -p "$DEMO_DIR/implementation"

echo "✓ Directories created"
echo ""

# Check if Marcus server is running
if ! pgrep -f "marcus_mcp.server" > /dev/null; then
    echo "⚠️  Warning: Marcus MCP server doesn't appear to be running"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Confirm before starting
echo "Ready to launch autonomous agents."
echo ""
read -p "Start the demo? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "======================================================================"
echo "Launching Autonomous Agents"
echo "======================================================================"
echo ""

# Launch the spawner
cd "$DEMO_DIR"
python3 autonomous_agent_spawner.py

echo ""
echo "======================================================================"
echo "Demo Complete"
echo "======================================================================"
echo ""
echo "Results:"
echo "  - Logs: $DEMO_DIR/logs/"
echo "  - Implementation: $DEMO_DIR/implementation/"
echo "  - Project info: $DEMO_DIR/project_info.json"
echo ""
echo "To validate results:"
echo "  python3 validate_api.py"
echo ""
