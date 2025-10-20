#!/bin/bash
# Start the Marcus Visualization Backend
# This script ensures the server runs from the correct directory

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Go to Marcus root (parent of viz_backend)
cd "$SCRIPT_DIR/.." || exit 1

# Run the server
echo "Starting server from: $(pwd)"
python -m viz_backend.run_server
