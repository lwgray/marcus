cd /Users/lwgray/dev/marcus/examples/multi_agent_demo/implementation
echo "=========================================="
echo "FOUNDATION AGENT"
echo "ID: agent_foundation"
echo "Role: backend"
echo "Branch: agent/agent_foundation"
echo "=========================================="
echo ""
echo "Waiting for project creation..."
while [ ! -f /Users/lwgray/dev/marcus/examples/multi_agent_demo/project_info.json ]; do
    sleep 2
done
echo "✓ Project found, starting agent..."
echo ""
cat /Users/lwgray/dev/marcus/examples/multi_agent_demo/prompts/agent_foundation.txt | claude --dangerously-skip-permissions
echo ""
echo "=========================================="
echo "Foundation Agent - Work Complete"
echo "=========================================="
