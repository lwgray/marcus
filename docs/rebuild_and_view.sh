#!/bin/bash
# Rebuild Marcus documentation and open in browser

echo "🔨 Cleaning previous build..."
rm -rf build

echo "📚 Building documentation..."
sphinx-build -b html source build/html

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "🌐 Opening in browser..."
    open build/html/index.html
    echo ""
    echo "📖 Documentation is ready at: build/html/index.html"
    echo ""
    echo "💡 To rebuild with live updates, run:"
    echo "   sphinx-autobuild source build/html --open-browser"
else
    echo "❌ Build failed. Check errors above."
    exit 1
fi
