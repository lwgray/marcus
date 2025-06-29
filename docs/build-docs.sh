#!/bin/bash
# Build documentation script for Marcus

echo "Building Marcus documentation..."

# Build Sphinx documentation
echo "Building Sphinx docs..."
cd developer-guide/sphinx
make clean
make html

if [ $? -eq 0 ]; then
    echo "✅ Sphinx documentation built successfully!"
    echo "View at: developer-guide/sphinx/build/html/index.html"
else
    echo "❌ Sphinx build failed!"
    exit 1
fi

# Optional: Deploy to GitHub Pages
if [ "$1" == "--deploy" ]; then
    echo "Deploying to GitHub Pages..."
    make github
    echo "✅ Documentation deployed to GitHub Pages!"
fi

echo "Documentation build complete!"