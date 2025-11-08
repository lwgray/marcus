#!/bin/bash
# Source shell profile to get nvm/claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

cd /Users/lwgray/dev/marcus-experiments/experiments/results/01_simple_calculator_config_single_agent_20251013_173915/implementation || exit 1
echo "=========================================="
echo "SOLO DEVELOPER AGENT"
echo "ID: agent_solo"
echo "Role: fullstack"
echo "Branch: main (shared)"
echo "Working Directory: $(pwd)"
echo "=========================================="
echo ""
echo "Waiting for project creation..."
while [ ! -f /Users/lwgray/dev/marcus-experiments/experiments/results/01_simple_calculator_config_single_agent_20251013_173915/project_info.json ]; do
    sleep 2
done
echo "✓ Project found, starting agent..."
echo ""
# Launch Claude from the implementation directory (cwd matters!)
claude --dangerously-skip-permissions < /Users/lwgray/dev/marcus-experiments/experiments/results/01_simple_calculator_config_single_agent_20251013_173915/prompts/agent_solo.txt
echo ""
echo "=========================================="
echo "Solo Developer Agent - Work Complete"
echo "=========================================="
