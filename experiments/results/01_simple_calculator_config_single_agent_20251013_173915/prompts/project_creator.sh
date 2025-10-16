#!/bin/bash
# Source shell profile to get nvm/claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

cd /Users/lwgray/dev/marcus-experiments/experiments/results/01_simple_calculator_config_single_agent_20251013_173915/implementation || exit 1
echo "=========================================="
echo "PROJECT CREATOR AGENT"
echo "Working Directory: $(pwd)"
echo "=========================================="
echo ""
echo "Configuring Marcus MCP..."
claude mcp add marcus -t http http://localhost:4298/mcp
echo ""
echo "Creating Marcus project: Simple Calculator API - Single Agent"
echo ""
# Launch Claude from the implementation directory (cwd matters!)
claude --dangerously-skip-permissions --print < /Users/lwgray/dev/marcus-experiments/experiments/results/01_simple_calculator_config_single_agent_20251013_173915/prompts/project_creator.txt
echo ""
echo "=========================================="
echo "Project Creator Complete"
echo "=========================================="
echo ""
echo "Press any key to close this window..."
read -n 1
