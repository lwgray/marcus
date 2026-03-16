#!/bin/bash
# Version bump script for Marcus
# Usage: ./scripts/bump-version.sh [patch|minor|major|<specific-version>]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)

echo -e "${BLUE}Current version: ${CURRENT_VERSION}${NC}"

# Determine new version
if [ $# -eq 0 ]; then
    echo -e "${RED}Usage: $0 [patch|minor|major|<specific-version>]${NC}"
    echo ""
    echo "Examples:"
    echo "  $0 patch      # 0.1.3 → 0.1.4"
    echo "  $0 minor      # 0.1.3 → 0.2.0"
    echo "  $0 major      # 0.1.3 → 1.0.0"
    echo "  $0 0.2.0-rc1  # Set specific version"
    exit 1
fi

BUMP_TYPE=$1

# Parse current version
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

case $BUMP_TYPE in
    patch)
        NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))"
        ;;
    minor)
        NEW_VERSION="${MAJOR}.$((MINOR + 1)).0"
        ;;
    major)
        NEW_VERSION="$((MAJOR + 1)).0.0"
        ;;
    *)
        # Custom version provided
        NEW_VERSION=$BUMP_TYPE
        ;;
esac

echo -e "${GREEN}New version: ${NEW_VERSION}${NC}"
echo ""

# Confirm
read -p "Proceed with version bump? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Aborted.${NC}"
    exit 1
fi

# Update pyproject.toml
echo -e "${BLUE}Updating pyproject.toml...${NC}"
sed -i.bak "s/^version = \".*\"/version = \"${NEW_VERSION}\"/" pyproject.toml
rm pyproject.toml.bak

# Update CHANGELOG.md
echo -e "${BLUE}Updating CHANGELOG.md...${NC}"
TODAY=$(date +%Y-%m-%d)

if grep -q "## \[Unreleased\]" CHANGELOG.md; then
    # Replace [Unreleased] with new version
    sed -i.bak "s/## \[Unreleased\]/## [Unreleased]\n\n## [${NEW_VERSION}] - ${TODAY}/" CHANGELOG.md
    rm CHANGELOG.md.bak
    echo -e "${GREEN}✓ Added release entry to CHANGELOG.md${NC}"
else
    echo -e "${YELLOW}⚠ No [Unreleased] section found in CHANGELOG.md${NC}"
    echo -e "${YELLOW}  Please manually update CHANGELOG.md${NC}"
fi

# Git operations
echo -e "${BLUE}Creating git commit and tag...${NC}"
git add pyproject.toml CHANGELOG.md

# Check if there are staged changes
if git diff --cached --quiet; then
    echo -e "${YELLOW}No changes to commit.${NC}"
else
    git commit -m "chore: bump version to ${NEW_VERSION}"
    echo -e "${GREEN}✓ Created commit${NC}"
fi

git tag -a "v${NEW_VERSION}" -m "Release version ${NEW_VERSION}"
echo -e "${GREEN}✓ Created tag v${NEW_VERSION}${NC}"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Version bump complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Next steps:"
echo "  1. Review changes: git show HEAD"
echo "  2. Push commit: git push origin $(git branch --show-current)"
echo "  3. Push tag: git push origin v${NEW_VERSION}"
echo ""
echo -e "${YELLOW}Note: Don't forget to update Cato version to match!${NC}"
