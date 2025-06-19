#!/bin/bash
# Script to help migrate documentation to new structure

echo "Documentation Migration Helper"
echo "=============================="
echo ""
echo "The documentation has been reorganized:"
echo ""
echo "1. User documentation → docs/sphinx/source/"
echo "2. Internal documentation → docs/internal/"
echo "3. Legacy files remain in docs/ for reference"
echo ""
echo "Next steps:"
echo "1. Review the new structure in docs/sphinx/source/"
echo "2. Build the documentation: cd docs && ./build_docs.sh"
echo "3. View at: docs/sphinx/build/html/index.html"
echo "4. Remove legacy .md files from docs/ after verification"
echo ""
echo "Legacy files that can be removed after verification:"
cd /Users/lwgray/dev/pm-agent/docs
for file in *.md; do
    if [[ -f "sphinx/source/${file%.md}.md" ]] || [[ -f "sphinx/source/*/${file%.md}.md" ]]; then
        echo "  - $file (migrated to Sphinx)"
    elif [[ -f "internal/*/$file" ]]; then
        echo "  - $file (moved to internal/)"
    fi
done