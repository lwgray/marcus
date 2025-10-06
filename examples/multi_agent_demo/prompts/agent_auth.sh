cd /Users/lwgray/dev/marcus/examples/multi_agent_demo/implementation
echo "=========================================="
echo "AUTHENTICATION AGENT"
echo "ID: agent_auth"
echo "Role: backend"
echo "Branch: agent/agent_auth"
echo "=========================================="
echo ""
echo "Waiting for project creation..."
while [ ! -f /Users/lwgray/dev/marcus/examples/multi_agent_demo/project_info.json ]; do
    sleep 2
done
echo "✓ Project found, starting agent..."
echo ""
cat /Users/lwgray/dev/marcus/examples/multi_agent_demo/prompts/agent_auth.txt | claude --dangerously-skip-permissions
echo ""
echo "=========================================="
echo "Authentication Agent - Work Complete"
echo "=========================================="
