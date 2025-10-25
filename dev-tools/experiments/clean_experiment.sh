#!/bin/bash
# Clean Marcus experiment directory
# Usage: ./clean_experiment.sh ~/experiments/test3

set -e  # Exit on error

# Check if directory argument provided
if [ -z "$1" ]; then
    echo "Error: No experiment directory provided"
    echo "Usage: $0 <experiment_directory>"
    echo "Example: $0 ~/experiments/test3"
    exit 1
fi

EXPERIMENT_DIR="$1"

# Expand tilde to home directory
EXPERIMENT_DIR="${EXPERIMENT_DIR/#\~/$HOME}"

# Check if directory exists
if [ ! -d "$EXPERIMENT_DIR" ]; then
    echo "Error: Directory does not exist: $EXPERIMENT_DIR"
    exit 1
fi

echo "=========================================="
echo "Marcus Experiment Cleanup"
echo "=========================================="
echo "Target directory: $EXPERIMENT_DIR"
echo ""
echo "This will DELETE:"
echo "  - All contents of prompts/"
echo "  - project_info.json file"
echo "  - All contents of implementation/ (including .git)"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."

# Clean prompts directory
if [ -d "$EXPERIMENT_DIR/prompts" ]; then
    echo "✓ Cleaning prompts/"
    rm -rf "$EXPERIMENT_DIR/prompts"/*
else
    echo "⚠ prompts/ directory not found, skipping"
fi

# Delete project_info.json
if [ -f "$EXPERIMENT_DIR/project_info.json" ]; then
    echo "✓ Deleting project_info.json"
    rm -f "$EXPERIMENT_DIR/project_info.json"
else
    echo "⚠ project_info.json not found, skipping"
fi

# Clean implementation directory
if [ -d "$EXPERIMENT_DIR/implementation" ]; then
    echo "✓ Cleaning implementation/ (including .git)"
    rm -rf "$EXPERIMENT_DIR/implementation"/*
    rm -rf "$EXPERIMENT_DIR/implementation"/.git
    rm -rf "$EXPERIMENT_DIR/implementation"/.* 2>/dev/null || true
else
    echo "⚠ implementation/ directory not found, skipping"
fi

echo ""
echo "=========================================="
echo "Cleanup Complete!"
echo "=========================================="
echo ""
echo "The experiment directory is now clean and ready for a new run."
echo "Run: python run_experiment.py $EXPERIMENT_DIR"
