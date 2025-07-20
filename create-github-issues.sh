#!/bin/bash

# Script to create GitHub issues for Marcus project
# Run this after authenticating with: gh auth login

echo "Creating GitHub issues for Marcus project..."

# Issue 1: create_project MCP tool hanging
echo "Creating issue 1..."
gh issue create \
  --repo lwgray/marcus \
  --title "create_project MCP tool doesn't send response back, causing client connection to hang" \
  --body-file github-issue-1-create-project-hang.md \
  --label "bug" \
  --label "mcp" \
  --label "high-priority"

# Issue 2: Task execution order
echo "Creating issue 2..."
gh issue create \
  --repo lwgray/marcus \
  --title "Task execution order not respecting dependencies - Tests assigned before Implementation" \
  --body-file github-issue-2-task-execution-order.md \
  --label "bug" \
  --label "task-scheduling" \
  --label "high-priority"

echo "Done! Both issues have been created."
