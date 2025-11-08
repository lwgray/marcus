cd /Users/lwgray/dev/marcus/examples/multi_agent_demo/implementation
echo "=========================================="
echo "API DEVELOPMENT AGENT"
echo "ID: agent_api"
echo "Role: backend"
echo "Branch: agent/agent_api"
echo "=========================================="
echo ""
echo "Waiting for project creation..."
while [ ! -f /Users/lwgray/dev/marcus/examples/multi_agent_demo/project_info.json ]; do
    sleep 2
done
echo "✓ Project found, starting agent..."
echo ""
cat /Users/lwgray/dev/marcus/examples/multi_agent_demo/prompts/agent_api.txt | claude --dangerously-skip-permissions
echo ""
echo "=========================================="
echo "API Development Agent - Work Complete"
echo "=========================================="
