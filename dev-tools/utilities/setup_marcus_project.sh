#!/bin/bash

# setup_marcus_project.sh
# Creates a new project directory with Marcus configuration

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if directory path is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: No directory path provided${NC}"
    echo "Usage: $0 <directory_path>"
    echo "Example: $0 ~/projects/my-new-project"
    exit 1
fi

PROJECT_DIR="$1"
AGENT_PROMPT="$HOME/dev/marcus/prompts/Agent_prompt.md"

# Expand tilde and resolve path
PROJECT_DIR="${PROJECT_DIR/#\~/$HOME}"

echo -e "${YELLOW}Setting up Marcus project at: ${PROJECT_DIR}${NC}"

# Create the directory
if [ -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}Warning: Directory already exists${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
else
    echo "Creating directory: $PROJECT_DIR"
    mkdir -p "$PROJECT_DIR"
fi

# Check if source file exists
if [ ! -f "$AGENT_PROMPT" ]; then
    echo -e "${RED}Error: Source file not found: ${AGENT_PROMPT}${NC}"
    exit 1
fi

# Copy the agent prompt to CLAUDE.md
echo "Copying Agent_prompt.md to CLAUDE.md..."
cp "$AGENT_PROMPT" "$PROJECT_DIR/CLAUDE.md"

# Change to the new directory and add Marcus MCP
echo "Changing to project directory and adding Marcus MCP..."
cd "$PROJECT_DIR"

# Add Marcus MCP server
echo "Adding Marcus MCP server..."
claude mcp add marcus -t http http://localhost:4298/mcp

echo -e "${GREEN}✓ Setup complete!${NC}"
echo -e "${GREEN}Project directory: ${PROJECT_DIR}${NC}"
echo -e "${GREEN}CLAUDE.md created${NC}"
echo -e "${GREEN}Marcus MCP server configured${NC}"
echo ""
echo "To start working:"
echo "  cd $PROJECT_DIR"
echo "  claude"
