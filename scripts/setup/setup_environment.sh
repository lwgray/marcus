#!/bin/bash
# Setup script for PM Agent development environment

set -e  # Exit on error

echo "🚀 PM Agent Setup Script"
echo "======================="

# Get the absolute path to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

cd "$PROJECT_ROOT"

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "❌ Python 3.8 or higher is required. Current version: $python_version"
    exit 1
fi
echo "✅ Python $python_version"

# Check Node.js
echo "Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+"
    exit 1
fi
node_version=$(node --version)
echo "✅ Node.js $node_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# PM Agent Environment Configuration

# Anthropic API Key (required for AI features)
ANTHROPIC_API_KEY=your-api-key-here

# Planka Configuration (defaults shown)
PLANKA_BASE_URL=http://localhost:3333
PLANKA_AGENT_EMAIL=demo@demo.demo
PLANKA_AGENT_PASSWORD=demo

# Project Configuration
PM_AGENT_PROJECT_ID=
PM_AGENT_BOARD_ID=

# Development Settings
DEBUG=false
LOG_LEVEL=INFO
EOF
    echo "✅ Created .env file - Please add your ANTHROPIC_API_KEY"
else
    echo "✅ .env file exists"
fi

# Check for kanban-mcp
KANBAN_MCP_PATH="../kanban-mcp"
if [ ! -d "$KANBAN_MCP_PATH" ]; then
    echo "⚠️  kanban-mcp not found at $KANBAN_MCP_PATH"
    echo "   Please clone it from the repository"
    echo "   git clone <kanban-mcp-repo> ../kanban-mcp"
else
    echo "✅ kanban-mcp found"
fi

# Create necessary directories
echo "Creating project directories..."
mkdir -p logs data

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Add your ANTHROPIC_API_KEY to .env file"
echo "2. Ensure Planka is running at http://localhost:3333"
echo "3. Run: source venv/bin/activate"
echo "4. Run: python scripts/examples/select_task_master_board.py"
echo "5. Start PM Agent: python start_pm_agent_task_master.py"