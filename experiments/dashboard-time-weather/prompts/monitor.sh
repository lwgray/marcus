#!/bin/bash
# Source shell profile to get nvm/claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

# Prevent Claude from detecting nesting and refusing to start
unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT CLAUDE_CODE_SESSION

cd /Users/lwgray/dev/marcus/experiments/dashboard-time-weather/implementation || exit 1
echo "=========================================="
echo "EXPERIMENT MONITOR"
echo "Working Directory: $(pwd)"
echo "=========================================="
echo ""
echo "Waiting for project creation..."
while [ ! -f /Users/lwgray/dev/marcus/experiments/dashboard-time-weather/project_info.json ]; do
    sleep 2
done
echo "✓ Project found, starting monitor..."
echo ""
# Launch Claude from the implementation directory (cwd matters!)
claude --add-dir /Users/lwgray/dev/marcus/experiments/dashboard-time-weather/implementation   --dangerously-skip-permissions < /Users/lwgray/dev/marcus/experiments/dashboard-time-weather/prompts/monitor.txt
echo ""
echo "=========================================="
echo "Experiment Monitor - Complete"
echo "=========================================="
