cd /Users/lwgray/dev/marcus/examples/multi_agent_demo/implementation
echo "=========================================="
echo "INTEGRATION & QA AGENT"
echo "ID: agent_integration"
echo "Role: qa"
echo "Branch: agent/agent_integration"
echo "=========================================="
echo ""
echo "Waiting for project creation..."
while [ ! -f /Users/lwgray/dev/marcus/examples/multi_agent_demo/project_info.json ]; do
    sleep 2
done
echo "✓ Project found, starting agent..."
echo ""
cat /Users/lwgray/dev/marcus/examples/multi_agent_demo/prompts/agent_integration.txt | claude --dangerously-skip-permissions
echo ""
echo "=========================================="
echo "Integration & QA Agent - Work Complete"
echo "=========================================="
