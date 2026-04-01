#!/bin/bash
# Source shell profile to get nvm/claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

# Prevent Claude from detecting nesting and refusing to start
unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT CLAUDE_CODE_SESSION

cd /Users/lwgray/dev/marcus/experiments/dashboard-time-weather/implementation || exit 1
echo "=========================================="
echo "PROJECT CREATOR AGENT"
echo "Working Directory: $(pwd)"
echo "=========================================="
echo ""
echo "Configuring Marcus MCP..."
claude mcp add marcus -t http http://localhost:4298/mcp 2>/dev/null || true
echo ""
echo "Creating Marcus project: dashboard-time-weather"
echo ""
# Launch Claude from the implementation directory (cwd matters!)
claude --add-dir /Users/lwgray/dev/marcus/experiments/dashboard-time-weather/implementation   --dangerously-skip-permissions --print < /Users/lwgray/dev/marcus/experiments/dashboard-time-weather/prompts/project_creator.txt
echo ""
echo "=========================================="
echo "Project Creator Complete"
echo "=========================================="
