#!/bin/bash
#
# Marcus Installation Script
#
# Installs the 'marcus' command for easy system-wide access.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${GREEN}Marcus Installation${NC}"
echo "===================="
echo

# Check if running as root for /usr/local/bin
if [ "$EUID" -eq 0 ]; then
    INSTALL_DIR="/usr/local/bin"
else
    # Install to user's local bin
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"

    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        echo -e "${YELLOW}Warning: $INSTALL_DIR is not in your PATH${NC}"
        echo "Add this to your shell profile (.bashrc, .zshrc, etc.):"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo
    fi
fi

# Create symlink
echo "Installing marcus command to $INSTALL_DIR..."
ln -sf "$SCRIPT_DIR/marcus" "$INSTALL_DIR/marcus"

# Check Python dependencies
echo
echo "Checking dependencies..."
if ! python3 -c "import mcp" 2>/dev/null; then
    echo -e "${YELLOW}Warning: MCP package not found${NC}"
    echo "Install with: pip install mcp"
fi

# Create directories
mkdir -p "$HOME/.marcus/services"
mkdir -p "$HOME/.marcus/logs"

echo
echo -e "${GREEN}✅ Marcus installed successfully!${NC}"
echo
echo "Usage:"
echo "  marcus start       # Start Marcus server"
echo "  marcus status      # Check if running"
echo "  marcus stop        # Stop server"
echo "  marcus --help      # Show all commands"
echo
echo "Quick start:"
echo "  marcus start --http    # Start with HTTP transport"
echo "  marcus start --stdio   # Start with stdio transport"
echo
