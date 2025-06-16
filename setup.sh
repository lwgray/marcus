#!/bin/bash

echo "Setting up AI Project Manager Agent..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p data

# Check for required environment variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "WARNING: ANTHROPIC_API_KEY not set!"
    echo "Please set it with: export ANTHROPIC_API_KEY='your-api-key'"
    echo ""
fi

echo ""
echo "Setup complete!"
echo ""
echo "To start the PM Agent:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Set your API key: export ANTHROPIC_API_KEY='your-api-key'"
echo "  3. Run the server: python main.py"
echo ""