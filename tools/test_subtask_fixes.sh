#!/bin/bash
# Test script to verify subtask and About task fixes

echo "==================================================================="
echo "Testing Marcus Subtask and About Task Fixes"
echo "==================================================================="
echo ""

# Step 1: Backup old subtasks
echo "Step 1: Backing up old subtasks..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [ -f "data/marcus_state/subtasks.json" ]; then
    mv data/marcus_state/subtasks.json "data/marcus_state/subtasks.json.backup_$TIMESTAMP"
    echo "✓ Backed up old subtasks to subtasks.json.backup_$TIMESTAMP"
else
    echo "✓ No old subtasks file found"
fi
echo ""

# Step 2: Check if Marcus is running
echo "Step 2: Checking Marcus status..."
if pgrep -f "python.*marcus.*server" > /dev/null; then
    echo "✓ Marcus is running"
    echo "  (You'll need to create a new project to test the fixes)"
else
    echo "✗ Marcus is not running"
    echo "  Please start Marcus before testing"
    exit 1
fi
echo ""

# Step 3: Instructions
echo "==================================================================="
echo "Next Steps:"
echo "==================================================================="
echo ""
echo "1. Create a NEW project using Marcus (don't reuse old projects)"
echo ""
echo "2. Verify subtask dependencies:"
echo "   - Check data/marcus_state/subtasks.json after decomposition"
echo "   - Dependencies should be actual subtask IDs like:"
echo "     \"dependencies\": [\"<parent_id>_sub_1\"]"
echo "   - NOT placeholder IDs like: \"dependencies\": [\"task_xxx_sub_1\"]"
echo ""
echo "3. Verify About task:"
echo "   - Check Planka board - About task should be in \"Done\" list"
echo "   - Check it's NOT being assigned to agents"
echo ""
echo "4. Verify subtask assignment flow:"
echo "   - Agent completes subtask 1"
echo "   - Agent should get subtask 2 (not parent task, not About task)"
echo "   - Agent should continue through all subtasks sequentially"
echo ""
echo "==================================================================="
echo ""
