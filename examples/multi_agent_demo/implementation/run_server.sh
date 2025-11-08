#!/bin/bash
# Run the Task Management API server

# Set working directory to implementation folder
cd "$(dirname "$0")"

# Check if .env exists, if not copy from example
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and configure your database settings!"
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r ../requirements.txt
fi

echo "=========================================="
echo "Task Management API Server"
echo "=========================================="
echo ""
echo "Starting server at http://localhost:8000"
echo "API Documentation: http://localhost:8000/api/v1/docs"
echo "Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

# Run the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
