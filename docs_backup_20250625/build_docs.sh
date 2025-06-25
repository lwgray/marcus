#!/bin/bash
# Build Sphinx documentation for PM Agent

echo "Building PM Agent documentation..."

# Change to sphinx directory
cd sphinx

# Clean previous builds
echo "Cleaning previous builds..."
make clean

# Build HTML documentation
echo "Building HTML documentation..."
make html

echo "Documentation built successfully!"
echo "View locally at: file://$(pwd)/build/html/index.html"
echo ""
echo "To deploy to GitHub Pages:"
echo "1. Ensure GitHub Pages is enabled for your repository"
echo "2. Push to main branch - GitHub Actions will build and deploy automatically"