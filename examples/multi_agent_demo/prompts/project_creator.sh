cd /Users/lwgray/dev/marcus/examples/multi_agent_demo
echo "=========================================="
echo "PROJECT CREATOR AGENT"
echo "=========================================="
echo ""
echo "Creating Marcus project..."
echo ""
cat /Users/lwgray/dev/marcus/examples/multi_agent_demo/prompts/project_creator.txt | claude --dangerously-skip-permissions --print
echo ""
echo "=========================================="
echo "Project Creator Complete"
echo "=========================================="
echo ""
echo "Press any key to close this window..."
read -n 1
