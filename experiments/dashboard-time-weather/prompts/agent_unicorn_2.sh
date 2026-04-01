#!/bin/bash
# Source shell profile to get nvm/claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

# Prevent Claude from detecting nesting and refusing to start
unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT CLAUDE_CODE_SESSION

cd /Users/lwgray/dev/marcus/experiments/dashboard-time-weather/implementation || exit 1
echo "=========================================="
echo "UNICORN DEVELOPER 2"
echo "ID: agent_unicorn_2"
echo "Role: full-stack"
echo "Branch: main (shared)"
echo "Working Directory: $(pwd)"
echo "=========================================="
echo ""
echo "Waiting for project creation..."
while [ ! -f /Users/lwgray/dev/marcus/experiments/dashboard-time-weather/project_info.json ]; do
    sleep 2
done
echo "✓ Project found, starting agent..."
echo ""
# Launch Claude from the implementation directory (cwd matters!)
claude --add-dir /Users/lwgray/dev/marcus/experiments/dashboard-time-weather/implementation   --dangerously-skip-permissions < /Users/lwgray/dev/marcus/experiments/dashboard-time-weather/prompts/agent_unicorn_2.txt
echo ""
echo "=========================================="
echo "Unicorn Developer 2 - Work Complete"
echo "=========================================="
